"""Golden cases: frozen, complete, deterministic and fully covering the code enum.

The coverage rule is a **set equality in both directions**. A one-directional
check would pass with a catalogue full of unused codes; the other direction
would pass with cases inventing codes the implementation cannot emit.
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

import golden_coverage  # noqa: E402
import gen_golden  # noqa: E402
from golden_oracle import ToolError, evaluate, load_catalog  # noqa: E402

OUTPUT_KEYS = {
    "_time": {"form", "timestamp"},
    "cors_evaluate": {"decision", "violations", "missing_headers", "recommended_headers", "notes"},
    "cors_simulate_fetch": {
        "decision",
        "events",
        "final_type",
        "hops",
        "max_age_effective",
        "preflight_cache_key",
        "preflight_occurred",
        "visible_headers",
    },
    "cache_evaluate": {
        "action",
        "current_age",
        "freshness_lifetime",
        "is_fresh",
        "must_revalidate",
        "reasons",
        "stale_while_revalidate_window",
    },
    "conditional_evaluate": {"explain", "rule_applied", "status", "weak_comparison_used"},
    "vary_match": {"differing_headers", "match", "normalized_vary", "reasons"},
}

ERROR_KEYS = {"error"}


def _cases():
    return list(golden_coverage.iter_cases(ROOT))


def test_every_code_has_at_least_one_case_both_directions():
    codes, used, per_code = golden_coverage.coverage(ROOT)
    assert codes, "codes.json is empty"
    assert not (codes - used), "codes without a golden case: " + ", ".join(sorted(codes - used))
    assert not (used - codes), "goldens use unknown codes: " + ", ".join(sorted(used - codes))
    assert all(per_code[code] for code in codes)


def test_coverage_report_exits_zero():
    assert golden_coverage.main(["--root", ROOT]) == 0


def test_check_mode_is_clean():
    out = _Null()
    assert gen_golden.check(ROOT, out) == 0, out.text


def test_generated_golden_matches_reserialisation():
    """Re-rendering from the inputs must reproduce the file bytes exactly."""
    rendered = gen_golden.render(ROOT)
    for relative, payload in rendered.items():
        path = os.path.join(ROOT, relative)
        with open(path, "rb") as handle:
            assert handle.read() == payload, relative


def test_expected_matches_the_oracle():
    catalog = load_catalog(ROOT)
    for tool, case_id, case in _cases():
        try:
            expected = evaluate(tool, case["input"], catalog)
        except ToolError as exc:
            expected = exc.payload()
        assert case["expected"] == expected, case_id


def test_expected_key_sets_are_exact():
    for tool, case_id, case in _cases():
        expected = case["expected"]
        if "error" in expected:
            assert set(expected) == ERROR_KEYS, case_id
            assert set(expected["error"]) == {"code", "field", "detail"}
            continue
        assert set(expected) == OUTPUT_KEYS[tool], case_id


def test_error_cases_use_the_frozen_error_codes():
    catalog = load_catalog(ROOT)
    allowed = set(catalog["error_codes"])
    seen = set()
    for _tool, case_id, case in _cases():
        if "error" in case["expected"]:
            code = case["expected"]["error"]["code"]
            assert code in allowed, case_id
            seen.add(code)
    assert "UNSUPPORTED_METHOD" in seen
    assert "INVALID_HEADER_VALUE" in seen
    assert "INVALID_TIME_FORMAT" in seen


def test_cases_are_ordered_and_named_consistently():
    for tool, case_id, case in _cases():
        assert case["case_id"] == case_id
        assert case["tool"] == tool
        assert case["source"] == "synthetic" or case["source"].startswith("wpt:")
        assert case["spec_basis"]


def test_no_observed_fields_anywhere():
    for tool, case_id, case in _cases():
        def walk(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    assert not key.startswith("observed_"), case_id + " has " + key
                    walk(item)
            elif isinstance(value, list):
                for item in value:
                    walk(item)

        walk(case)


def test_header_name_lists_are_lowercase_sorted():
    for tool, case_id, case in _cases():
        expected = case["expected"]
        for key in ("missing_headers", "visible_headers", "differing_headers", "normalized_vary"):
            if key in expected:
                names = expected[key]
                assert names == sorted(names), case_id
                assert all(name == name.lower() for name in names), case_id


def test_findings_are_sorted_by_code():
    for tool, case_id, case in _cases():
        expected = case["expected"]
        for key in ("violations", "reasons", "explain"):
            items = expected.get(key)
            if items is None:
                continue
            keys = [(item["code"], item["detail"]) for item in items]
            assert keys == sorted(keys), case_id


def test_rerun_is_byte_identical():
    """The determinism promise starts at the data layer: same input, same bytes."""
    rendered = gen_golden.render(ROOT)
    again = gen_golden.render(ROOT)
    assert rendered == again
    for relative in rendered:
        assert rendered[relative] == again[relative]


def test_drift_and_orphans_are_detected(tmp_path):
    project = tmp_path / "repo"
    (project / "tools").mkdir(parents=True)
    shutil.copytree(os.path.join(ROOT, "tools", "cases"), project / "tools" / "cases")
    shutil.copytree(
        os.path.join(ROOT, "src", "http_semantics_mcp", "references"),
        project / "src" / "http_semantics_mcp" / "references",
    )
    shutil.copytree(os.path.join(ROOT, "data", "golden"), project / "data" / "golden")

    out = _Null()
    assert gen_golden.check(str(project), out) == 0, out.text

    target = project / "data" / "golden" / "vary_match" / "vary-001-hit-single.json"
    payload = target.read_text(encoding="utf-8")
    with open(str(target), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload.replace('"hit"', '"miss"', 1))
    out = _Null()
    assert gen_golden.check(str(project), out) == 1
    assert "DRIFT" in out.text


def test_orphan_golden_is_reported(tmp_path):
    project = tmp_path / "repo"
    (project / "tools").mkdir(parents=True)
    shutil.copytree(os.path.join(ROOT, "tools", "cases"), project / "tools" / "cases")
    shutil.copytree(
        os.path.join(ROOT, "src", "http_semantics_mcp", "references"),
        project / "src" / "http_semantics_mcp" / "references",
    )
    shutil.copytree(os.path.join(ROOT, "data", "golden"), project / "data" / "golden")
    (project / "data" / "golden" / "vary_match" / "vary-999-orphan.json").write_text(
        "{}\n", encoding="utf-8"
    )

    out = _Null()
    assert gen_golden.check(str(project), out) == 1
    assert "ORPHAN" in out.text


def test_oracle_must_not_import_the_implementation():
    for path in _oracle_sources():
        text = open(path, "r", encoding="utf-8").read()
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")):
                assert "http_semantics_mcp" not in stripped, path


def test_input_cases_must_not_carry_expected(tmp_path):
    project = tmp_path / "repo"
    (project / "tools" / "cases" / "vary_match").mkdir(parents=True)
    shutil.copytree(
        os.path.join(ROOT, "src", "http_semantics_mcp", "references"),
        project / "src" / "http_semantics_mcp" / "references",
    )
    with open(
        str(project / "tools" / "cases" / "vary_match" / "vary-x.json"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as handle:
        handle.write(
            json.dumps(
                {
                    "case_id": "vary-x",
                    "tool": "vary_match",
                    "input": {},
                    "expected": {},
                    "spec_basis": ["RFC9111 §4.1"],
                    "source": "synthetic",
                }
            )
        )
    with pytest.raises(gen_golden.CaseError):
        gen_golden.load_cases(str(project))


def _oracle_sources():
    base = os.path.join(ROOT, "tools", "golden_oracle")
    return [
        os.path.join(base, name)
        for name in sorted(os.listdir(base))
        if name.endswith(".py")
    ]


class _Null(object):
    def __init__(self):
        self.text = ""

    def write(self, value):
        self.text += value
