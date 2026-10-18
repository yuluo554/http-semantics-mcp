"""Mirror equality between the in-package sources and the top-level copies.

Why this exists: the task document names top-level ``schemas/`` and
``references/`` as deliverables, while an installed distribution can only read
the in-package copies. Two locations, one contract -- so the gate compares
bytes, and the test proves the gate can fail.
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import check_release  # noqa: E402

PACKAGE_REFERENCES = os.path.join("src", "http_semantics_mcp", "references")
PACKAGE_SCHEMAS = os.path.join("src", "http_semantics_mcp", "schemas", "tools")


def test_mirrors_are_equal_on_the_clean_tree():
    detail = check_release.check_dist_mirrors()
    assert "byte-identical" in detail
    # M1 lands the first generated mirror; a clean tree must compare at least one.
    assert not detail.startswith("0 mirror")


def _write(path, payload):
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)


def test_missing_mirror_is_reported(tmp_path, monkeypatch):
    _write(os.path.join(str(tmp_path), PACKAGE_REFERENCES, "codes.json"), '{"version":1}\n')
    monkeypatch.setattr(check_release, "ROOT", str(tmp_path))

    try:
        check_release.check_dist_mirrors()
    except check_release.NotAchieved as exc:
        assert "mirror missing" in str(exc)
        return
    raise AssertionError("missing mirror was not reported")


def test_diverged_mirror_is_reported(tmp_path, monkeypatch):
    _write(os.path.join(str(tmp_path), PACKAGE_SCHEMAS, "cors_evaluate.json"), '{"a":1}\n')
    _write(os.path.join(str(tmp_path), "schemas", "tools", "cors_evaluate.json"), '{"a":2}\n')
    monkeypatch.setattr(check_release, "ROOT", str(tmp_path))

    try:
        check_release.check_dist_mirrors()
    except check_release.NotAchieved as exc:
        assert "mirror differs" in str(exc)
        return
    raise AssertionError("diverged mirror was not reported")


def test_identical_pair_is_accepted(tmp_path, monkeypatch):
    payload = json.dumps({"type": "object"}, sort_keys=True) + "\n"
    _write(os.path.join(str(tmp_path), PACKAGE_SCHEMAS, "vary_match.json"), payload)
    _write(os.path.join(str(tmp_path), "schemas", "tools", "vary_match.json"), payload)
    monkeypatch.setattr(check_release, "ROOT", str(tmp_path))

    assert check_release.check_dist_mirrors().startswith("1 mirror")
