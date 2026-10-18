"""WPT index and mapping ledger: shape, set partition, and case references.

The ledger's honesty rules (plan/04 section 5.3):

* ``converted + unmappable == total`` is a partition, not a rounded ratio;
* every ``mapped=true`` row points at golden cases that exist;
* every unmapped row carries a reason from the fixed enum;
* the index and the ledger describe the same directory at the same commit.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import golden_coverage  # noqa: E402

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402

INDEX = os.path.join("data", "wpt", "cors-index.json")
LEDGER = os.path.join("data", "wpt-mapping.json")

REASONS = {
    "requires_real_network",
    "requires_tls",
    "requires_timing",
    "browser_proprietary",
    "not_header_observable",
    "out_of_scope",
}


def _load(relative):
    with open(os.path.join(ROOT, relative), "r", encoding="utf-8") as handle:
        return json.load(handle)


def test_index_records_the_commit_and_data_day():
    index = _load(INDEX)
    assert index["wpt_commit"] == "850b36a56cfc15b9117a9d222d32a63104662f49"
    assert index["fetched_at"] == "2026-10-18"
    assert index["directory"] == "cors"
    assert index["total"] == len(index["files"]) == 45


def test_index_carries_paths_and_blob_shas_only():
    index = _load(INDEX)
    for entry in index["files"]:
        assert set(entry) == {"path", "type", "blob_sha", "size"}
        assert entry["path"].startswith("cors/")
        assert len(entry["blob_sha"]) == 40
        assert entry["size"] > 0


def test_ledger_covers_every_index_entry():
    index = _load(INDEX)
    ledger = _load(LEDGER)
    indexed = {entry["path"] for entry in index["files"]}
    recorded = {row["wpt_path"] for row in ledger["records"]}
    assert recorded == indexed
    assert ledger["total"] == index["total"]
    assert ledger["wpt_commit"] == index["wpt_commit"]
    assert ledger["fetched_at"] == index["fetched_at"]


def test_partition_holds():
    ledger = _load(LEDGER)
    assert ledger["converted"] + ledger["unmappable"] == ledger["total"]
    assert ledger["converted"] == sum(1 for row in ledger["records"] if row["mapped"])
    assert ledger["unmappable"] == sum(1 for row in ledger["records"] if not row["mapped"])


def test_unmapped_rows_carry_an_enum_reason():
    ledger = _load(LEDGER)
    for row in ledger["records"]:
        if row["mapped"]:
            assert row["reason"] is None, row["wpt_path"]
            assert row["case_ids"], row["wpt_path"]
        else:
            assert row["reason"] in REASONS, row["wpt_path"]
            assert row["case_ids"] == [], row["wpt_path"]


def test_mapped_rows_point_at_real_golden_cases():
    ledger = _load(LEDGER)
    known = {case_id for _tool, case_id, _case in golden_coverage.iter_cases(ROOT)}
    referenced = set()
    for row in ledger["records"]:
        for case_id in row["case_ids"]:
            assert case_id in known, row["wpt_path"] + " -> " + case_id
            referenced.add(case_id)
    assert len(referenced) >= 15


def test_no_duplicate_case_reference_within_one_row():
    for row in _load(LEDGER)["records"]:
        assert len(row["case_ids"]) == len(set(row["case_ids"])), row["wpt_path"]


def test_mapped_rows_reconcile_with_the_production_output():
    """The ledger is not just a list of names: every mapped row is executed.

    For each ``mapped=true`` row, the golden cases it points at are run through
    the production handler and compared byte for byte with the frozen
    expectation (``data/README.md`` section 3.4, final bullet). The row count is
    asserted against the ledger's own ``converted`` counter, and the case count
    is asserted to be non-zero, so a ledger that mapped nothing cannot pass.
    """
    ledger = _load(LEDGER)
    golden = {case_id: (tool, case) for tool, case_id, case in golden_coverage.iter_cases(ROOT)}

    reconciled_rows = 0
    reconciled_cases = 0
    for row in ledger["records"]:
        if not row["mapped"]:
            assert row["reason"] in REASONS, row["wpt_path"]
            continue
        for case_id in row["case_ids"]:
            tool, case = golden[case_id]
            result = build_registry().get(tool).handler(case["input"])
            actual = json.loads(result["content"][0]["text"])
            assert canonical.dumps(actual) == canonical.dumps(case["expected"]), (
                row["wpt_path"] + " -> " + case_id
            )
            reconciled_cases += 1
        reconciled_rows += 1

    assert reconciled_rows == ledger["converted"] == 15
    assert reconciled_cases >= reconciled_rows
    sys.stdout.write(
        "WPT: {0}/{1} mapped row(s) reconcile with the production output "
        "({2} golden case reference(s))\n".format(
            reconciled_rows, ledger["converted"], reconciled_cases
        )
    )


def test_ledger_does_not_ship_wpt_source_text():
    """Only paths, shas and verdicts may be committed (plan/04 section 5.1)."""
    ledger = _load(LEDGER)
    blob = json.dumps(ledger)
    for marker in ("<script", "function(", "promise_test(", "assert_equals("):
        assert marker not in blob


@pytest.mark.parametrize(
    "relative,key",
    [(INDEX, "total"), (LEDGER, "converted"), (LEDGER, "unmappable")],
)
def test_counts_are_integers(relative, key):
    value = _load(relative)[key]
    assert isinstance(value, int) and not isinstance(value, bool)
