"""T1/T2 against the frozen CORS golden cases.

The comparison is *byte* equality of the canonical serialisation, not a
field-by-field assertion: a test that checks only the fields it knows about
would stay green while the implementation grew an extra key or changed a sort
order (``data/README.md`` section 4.5).

Everything runs through the registered tool handler, so this pins the whole
path a client takes: ``tools/call`` -> registry -> judgement -> tool result.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "data", "golden")

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.judgement.errors import ERROR_CODES  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402

TOOLS = ("cors_evaluate", "cors_simulate_fetch")


def _cases():
    for tool in TOOLS:
        directory = os.path.join(GOLDEN, tool)
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                case = json.load(handle)
            yield tool, case


def _all_cases():
    return list(_cases())


def _call(tool, arguments):
    registry = build_registry()
    registered = registry.get(tool)
    assert registered is not None, "tool is not registered: " + tool
    return registered.handler(arguments)


def test_golden_cases_are_present():
    assert len(_all_cases()) == 34


@pytest.mark.parametrize(
    "tool,case", _all_cases(), ids=[case["case_id"] for _tool, case in _all_cases()]
)
def test_production_output_is_byte_identical_to_the_golden(tool, case):
    result = _call(tool, case["input"])
    text = result["content"][0]["text"]
    actual = json.loads(text)

    expected = case["expected"]
    if "error" in expected:
        assert result["isError"] is True, case["case_id"]
        assert actual["error"]["code"] in ERROR_CODES
    else:
        assert result["isError"] is False, case["case_id"]

    # Both directions: the serialisation of the parsed output must equal the
    # canonical form of the frozen expectation, exactly.
    assert canonical.dumps(actual) == canonical.dumps(expected), case["case_id"]


def test_every_successful_case_declares_the_frozen_key_set():
    seen = set()
    for tool, case in _all_cases():
        expected = case["expected"]
        if "error" in expected:
            continue
        actual = json.loads(_call(tool, case["input"])["content"][0]["text"])
        assert set(actual) == set(expected), case["case_id"]
        seen.add(tool)
    assert seen == set(TOOLS)


def test_error_cases_report_iserror_and_keep_the_process_alive():
    """A caller mistake is a payload, not an exception and not a crash."""
    errors_seen = 0
    for tool, case in _all_cases():
        if "error" not in case["expected"]:
            continue
        errors_seen += 1
        result = _call(tool, case["input"])
        assert result["isError"] is True, case["case_id"]
        assert set(json.loads(result["content"][0]["text"])) == {"error"}
    assert errors_seen >= 1, "no error case is exercised (probe is broken)"

    # The registry is still usable after a rejected call.
    assert build_registry().get("cors_evaluate") is not None


def test_header_order_does_not_change_the_bytes():
    """cors-eval-018/019 differ only in header writing order."""
    order_a = None
    order_b = None
    for _tool, case in _all_cases():
        if case["case_id"] == "cors-eval-018-header-order-invariance-a":
            order_a = case["input"]
        if case["case_id"] == "cors-eval-019-header-order-invariance-b":
            order_b = case["input"]
    assert order_a is not None and order_b is not None

    first = _call("cors_evaluate", order_a)["content"][0]["text"]
    second = _call("cors_evaluate", order_b)["content"][0]["text"]
    assert first == second


def test_redirect_events_are_ordered_and_not_sorted():
    """The one field where order is the contract (plan/03 section 2.3)."""
    events = {}
    for _tool, case in _all_cases():
        if "events" in case["expected"]:
            events[case["case_id"]] = case["expected"]["events"]
    assert events["cors-sim-002-cross-origin-credentials-dropped"] == [
        "origin_set_to_null",
        "credentials_dropped",
    ]
    assert events["cors-sim-006-cross-to-cross"] == [
        "origin_set_to_null",
        "credentials_dropped",
        "origin_set_to_null",
        "credentials_dropped",
    ]

    for case_id in (
        "cors-sim-002-cross-origin-credentials-dropped",
        "cors-sim-006-cross-to-cross",
    ):
        case = _case(case_id)
        actual = json.loads(_call("cors_simulate_fetch", case["input"])["content"][0]["text"])
        assert actual["events"] == case["expected"]["events"], case_id


def _case(case_id):
    for _tool, case in _all_cases():
        if case["case_id"] == case_id:
            return case
    raise AssertionError("unknown case: " + case_id)


def test_reruns_are_byte_identical():
    """Same input, same bytes -- measured, not assumed."""
    for tool, case in _all_cases():
        first = _call(tool, case["input"])
        second = _call(tool, case["input"])
        assert canonical.dumps(first) == canonical.dumps(second), case["case_id"]
