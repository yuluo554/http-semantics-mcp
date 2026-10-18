"""``codes.json`` is generated from ``data/README.md`` section 4 and mirrored.

Three properties, all of which can fail independently:

* the working tree equals a fresh regeneration (``--check``);
* the in-package file and the top-level mirror are byte-identical;
* the catalog's codes are exactly the table's codes -- no extra, no missing.
"""

import json
import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gen_codes  # noqa: E402
import golden_coverage  # noqa: E402
import spectable  # noqa: E402


def _read(relative):
    with open(os.path.join(ROOT, relative), "rb") as handle:
        return handle.read()


def _catalog():
    return json.loads(_read(gen_codes.PACKAGE_CODES).decode("utf-8"))


def test_check_passes_on_the_clean_tree():
    assert gen_codes.check(ROOT, _Null()) == 0


def test_mirror_is_byte_identical():
    assert _read(gen_codes.PACKAGE_CODES) == _read(gen_codes.MIRROR_CODES)


def test_every_table_code_appears_exactly_once_in_the_catalog():
    table = [record["code"] for record in spectable.read_codes(_data_readme())]
    catalog = _catalog()
    assert sorted(table) == sorted(catalog["codes"])
    assert len(table) == len(set(table))


def test_catalog_records_carry_the_required_fields():
    for code, record in _catalog()["codes"].items():
        assert set(record) == {"meaning", "prefix", "severity", "spec_ref", "template"}
        assert record["severity"] in ("decisive", "informational")
        assert record["spec_ref"] == sorted(record["spec_ref"])
        assert record["spec_ref"], code
        assert record["template"], code
        assert code.startswith(record["prefix"])


def test_generated_file_has_no_timestamp_or_machine_path():
    text = _read(gen_codes.PACKAGE_CODES).decode("utf-8")
    assert text.count("schema_version") == 1
    for marker in ("/" + "home/", "/" + "Users/", "AppData"):
        assert marker not in text


def _contract_root(tmp_path):
    """A scratch root carrying just enough of the tree for a regeneration."""
    root = str(tmp_path)
    os.makedirs(os.path.join(root, "data"), exist_ok=True)
    shutil.copy(os.path.join(ROOT, "data", "README.md"), os.path.join(root, "data", "README.md"))
    return root


def test_drift_is_detected_and_located(tmp_path, monkeypatch):
    """A corrupted mirror must make ``--check`` fail and name the file."""
    root = _contract_root(tmp_path)
    mirror = os.path.join(root, gen_codes.MIRROR_CODES)
    os.makedirs(os.path.dirname(mirror))
    payload = gen_codes.render(ROOT)[gen_codes.PACKAGE_CODES]
    with open(mirror, "wb") as handle:
        handle.write(payload.replace(b"CORS_", b"CORS_", 1) + b" ")
    package = os.path.join(root, gen_codes.PACKAGE_CODES)
    os.makedirs(os.path.dirname(package))
    with open(package, "wb") as handle:
        handle.write(payload)

    out = _Null()
    assert gen_codes.check(root, out) == 1
    assert "DRIFT" in out.text and gen_codes.MIRROR_CODES in out.text


def test_missing_file_is_reported(tmp_path):
    out = _Null()
    assert gen_codes.check(_contract_root(tmp_path), out) == 1
    assert "MISSING" in out.text


def test_malformed_table_is_a_hard_error():
    text = _data_readme().replace("| `CORS_MISSING_ALLOW_ORIGIN` |", "| broken |", 1)
    with pytest.raises(spectable.SpecTableError):
        spectable.read_codes(text)


def test_unverified_clause_blocks_generation():
    """Section 4.2 is the contract's audit trail; a used ref must be checked off."""
    text = _data_readme().replace("| `Fetch` | `§CORS check` | 4.10. CORS check | ✅ 2026-10-18 |",
                                  "| `Fetch` | `§CORS check` | 4.10. CORS check | ⬜ |", 1)
    missing, _ = spectable.unverified_refs(text)
    assert "Fetch §CORS check" in missing


def test_preflight_cache_key_contract_is_read_not_invented():
    contract = spectable.read_contract(ROOT)
    assert contract["preflight_cache_key"]["hex_prefix"] == 16
    assert contract["preflight_cache_key"]["algorithm"] == "sha256"


def _data_readme():
    with open(os.path.join(ROOT, "data", "README.md"), "r", encoding="utf-8") as handle:
        return handle.read()


class _Null(object):
    def __init__(self):
        self.text = ""

    def write(self, value):
        self.text += value


def test_every_spec_ref_in_the_table_is_verified_in_section_4_2():
    missing, _extra = spectable.unverified_refs(_data_readme())
    assert missing == [], "unverified clause used as a rule source: " + ", ".join(missing)


def test_every_spec_basis_in_goldens_and_the_ledger_is_verified():
    """A golden may only cite a clause the audit table has ticked off."""
    verified = set(spectable.read_spec_refs(_data_readme()))
    used = set()
    for _tool, _case_id, case in golden_coverage.iter_cases(ROOT):
        used.update(case["spec_basis"])
    ledger = _read_json(os.path.join("data", "wpt-mapping.json"))
    for record in ledger["records"]:
        used.update(record["spec_basis"])
    assert used, "no spec_basis found (probe is broken)"
    assert not (used - verified), "spec_basis not audited: " + ", ".join(sorted(used - verified))


def _read_json(relative):
    return json.loads(_read(relative).decode("utf-8"))
