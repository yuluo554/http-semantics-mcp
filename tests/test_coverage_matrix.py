"""Coverage matrix (plan/04 §四): every named shape has a case.

The per-code set equality in ``test_golden.py`` proves the enum is exhausted.
This file proves the *shapes* are: the boundary cases the plan calls out by
name are the ones that tend to be missed, and a code can be "covered" by a
case that never exercises its interesting branch.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import golden_coverage  # noqa: E402

MATRIX = {
    "cors": [
        "cors-eval-013-null-origin",
        "cors-eval-004-wildcard-with-credentials",
        "cors-eval-024-allow-credentials-with-wildcard",
        "cors-eval-008-preflight-missing-methods",
        "cors-eval-023-allow-origin-whitespace",
        "cors-eval-015-authorization-not-wildcard",
        "cors-eval-010-preflight-allow",
    ],
    "redirect": [
        "cors-sim-001-same-origin-hop",
        "cors-sim-002-cross-origin-credentials-dropped",
        "cors-sim-006-cross-to-cross",
        "cors-sim-004-no-cors-opaque",
        "cors-sim-005-same-origin-mode-blocked",
        "cors-sim-007-preflight-cache-key",
        "cors-sim-009-max-age-effective",
        "cors-sim-010-redirect-after-preflight",
    ],
    "cache": [
        "cache-001-fresh",
        "cache-002-age-exceeds-lifetime",
        "cache-003-no-store",
        "cache-005-must-revalidate-stale",
        "cache-006-stale-while-revalidate",
        "cache-009-heuristic",
        "cache-014-age-exceeds-freshness",
        "cache-011-max-age-zero",
        "cache-015-boundary-equal",
        "cache-018-expires-without-date",
    ],
    "conditional": [
        "cond-001-no-condition",
        "cond-002-if-match-pass",
        "cond-003-if-match-failed",
        "cond-005-if-unmodified-since-failed",
        "cond-007-if-none-match-weak-304",
        "cond-009-if-none-match-star",
        "cond-010-if-modified-since-304",
        "cond-013-both-preconditions",
        "cond-015-if-match-with-unmodified-since",
        "cond-016-unmodified-since-with-none-match",
        "cond-017-none-match-with-modified-since",
        "cond-018-unmodified-since-with-modified-since",
        "cond-019-if-match-with-modified-since",
        "cond-012-invalid-date-ignored",
    ],
    "vary": [
        "vary-001-hit-single",
        "vary-008-multi-field",
        "vary-003-star",
        "vary-004-field-missing",
        "vary-005-accept-case-insensitive",
        "vary-006-whitespace",
        "vary-007-duplicate",
        "vary-009-accept-order",
    ],
    "time": [
        "time-001-iso",
        "time-002-http-date",
        "time-003-subsecond-truncated",
        "time-007-subsecond-truncates-not-rounds",
        "time-004-invalid",
        "time-005-wrong-weekday",
        "time-006-missing-zone",
    ],
}

# plan/04 §四 minimum counts, per dimension.
MINIMUM = {"cors": 6, "redirect": 4, "cache": 8, "conditional": 6, "vary": 6}


def _known():
    return {case_id for _tool, case_id, _case in golden_coverage.iter_cases(ROOT)}


def test_every_named_case_exists():
    known = _known()
    missing = []
    for dimension, case_ids in sorted(MATRIX.items()):
        for case_id in case_ids:
            if case_id not in known:
                missing.append(dimension + ":" + case_id)
    assert missing == [], "coverage matrix points at missing cases: " + ", ".join(missing)


def test_each_dimension_meets_the_planned_minimum():
    for dimension, minimum in sorted(MINIMUM.items()):
        assert len(MATRIX[dimension]) >= minimum, dimension


def test_redirect_events_are_locked_by_goldens():
    """Events are the one field where the order *is* the contract."""
    expected = {
        "cors-sim-001-same-origin-hop": [],
        "cors-sim-002-cross-origin-credentials-dropped": [
            "origin_set_to_null",
            "credentials_dropped",
        ],
        "cors-sim-003-cross-origin-omit": ["origin_set_to_null"],
        "cors-sim-006-cross-to-cross": [
            "origin_set_to_null",
            "credentials_dropped",
            "origin_set_to_null",
            "credentials_dropped",
        ],
    }
    actual = {}
    for _tool, case_id, case in golden_coverage.iter_cases(ROOT):
        if case_id in expected:
            actual[case_id] = case["expected"]["events"]
    assert actual == expected


def test_cache_arithmetic_is_auditable_from_the_notes():
    """Every numeric cache case must explain its arithmetic in ``notes``."""
    for tool, case_id, case in golden_coverage.iter_cases(ROOT):
        if tool != "cache_evaluate":
            continue
        if "error" in case["expected"]:
            continue
        notes = case.get("notes", "")
        assert notes, case_id + " has no arithmetic note"
        assert "=" in notes or "->" in notes, case_id
