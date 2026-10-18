"""T3 against the frozen cache golden cases, plus the time parser they rest on.

Same rule as the CORS suite: the comparison is *byte* equality of the canonical
serialisation, not a field-by-field assertion, so an extra key or a changed sort
order fails even though every named field looks right (``data/README.md``
section 4.5). Calls go through the registered handler, which pins the whole path
a client takes: ``tools/call`` -> registry -> judgement -> tool result.

The time parser gets its own pass over ``data/golden/_time``: those cases are not
a tool (the tool list has no ``_time`` entry), they exist to lock the two
accepted formats and the refusal path.
"""

import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "data", "golden")

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.judgement.errors import ERROR_CODES, JudgementError  # noqa: E402
from http_semantics_mcp.judgement.timeparse import parse_time  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402

KEY_SET = {
    "action",
    "current_age",
    "freshness_lifetime",
    "is_fresh",
    "must_revalidate",
    "reasons",
    "stale_while_revalidate_window",
}

NUMERIC_FIELDS = ("current_age", "freshness_lifetime", "stale_while_revalidate_window")


def _cases():
    directory = os.path.join(GOLDEN, "cache_evaluate")
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                yield json.load(handle)


def _all_cases():
    return list(_cases())


def _call(arguments):
    registered = build_registry().get("cache_evaluate")
    assert registered is not None, "cache_evaluate is not registered"
    return registered.handler(arguments)


def _time_cases():
    directory = os.path.join(GOLDEN, "_time")
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                yield json.load(handle)


_TIME_CASES = list(_time_cases())


def test_golden_cases_are_present():
    assert len(_all_cases()) == 18


@pytest.mark.parametrize("case", _all_cases(), ids=[case["case_id"] for case in _all_cases()])
def test_production_output_is_byte_identical_to_the_golden(case):
    result = _call(case["input"])
    assert result["isError"] is False, case["case_id"]
    actual = json.loads(result["content"][0]["text"])
    assert canonical.dumps(actual) == canonical.dumps(case["expected"]), case["case_id"]


def test_every_case_declares_the_frozen_key_set():
    for case in _all_cases():
        actual = json.loads(_call(case["input"])["content"][0]["text"])
        assert set(actual) == KEY_SET, case["case_id"]


def test_arithmetic_stays_on_integer_seconds():
    """No float may reach the output: seconds are counted, not measured.

    A float here would not merely be untidy -- it would make the numbers
    unrepresentable in canonical JSON (``allow_nan=False``) or introduce
    rounding noise that breaks the byte-identical promise.
    """
    for case in _all_cases():
        actual = json.loads(_call(case["input"])["content"][0]["text"])
        for field in NUMERIC_FIELDS:
            value = actual[field]
            assert isinstance(value, int) and not isinstance(value, bool), case["case_id"] + " " + field


def test_reruns_are_byte_identical():
    for case in _all_cases():
        first = _call(case["input"])
        second = _call(case["input"])
        assert canonical.dumps(first) == canonical.dumps(second), case["case_id"]


def test_header_write_order_does_not_change_the_bytes():
    base = {
        "now": "2026-01-01T00:00:30Z",
        "stored": {"stored_at": "2026-01-01T00:00:00Z", "age": "0"},
    }
    first = dict(base, response_headers={"Cache-Control": "max-age=60", "Date": "Thu, 01 Jan 2026 00:00:00 GMT"})
    second = dict(base, response_headers={"Date": "Thu, 01 Jan 2026 00:00:00 GMT", "Cache-Control": "max-age=60"})
    assert _call(first)["content"][0]["text"] == _call(second)["content"][0]["text"]


def test_missing_now_is_an_input_error_never_a_clock_read():
    result = _call({"stored": {"stored_at": "2026-01-01T00:00:00Z"}})
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert payload["error"]["code"] == "INVALID_INPUT"
    assert payload["error"]["field"] == "now"


def test_missing_stored_is_an_input_error():
    result = _call({"now": "2026-01-01T00:00:00Z"})
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["error"]["code"] == "INVALID_INPUT"


def test_unparsable_now_is_a_time_format_error():
    result = _call({"now": "yesterday", "stored": {"stored_at": "2026-01-01T00:00:00Z"}})
    assert result["isError"] is True
    payload = json.loads(result["content"][0]["text"])
    assert payload["error"]["code"] == "INVALID_TIME_FORMAT"
    assert payload["error"]["code"] in ERROR_CODES


def test_stale_while_revalidate_window_boundary_is_inclusive():
    """plan/03 section 3.2: the window is ``excess <= swr``.

    No frozen case sits exactly on the boundary, so this is the one place the
    edge is pinned: the ``==`` side must serve, one second past must revalidate.
    """

    def run(swr, now):
        return json.loads(
            _call(
                {
                    "now": now,
                    "response_headers": {
                        "Cache-Control": "max-age=10, stale-while-revalidate=" + str(swr),
                        "Date": "Thu, 01 Jan 2026 00:00:00 GMT",
                    },
                    "stored": {"stored_at": "2026-01-01T00:00:00Z", "age": "0"},
                }
            )["content"][0]["text"]
        )

    on_boundary = run(5, "2026-01-01T00:00:15Z")
    assert on_boundary["current_age"] == 15
    assert on_boundary["freshness_lifetime"] == 10
    assert on_boundary["action"] == "serve"
    assert [reason["code"] for reason in on_boundary["reasons"]] == ["CACHE_STALE_WHILE_REVALIDATE"]

    outside = run(4, "2026-01-01T00:00:15Z")
    assert outside["action"] == "revalidate"
    assert [reason["code"] for reason in outside["reasons"]] == ["CACHE_AGE_EXCEEDS_LIFETIME"]


def test_request_and_stored_headers_are_optional():
    result = _call(
        {
            "now": "2026-01-01T00:00:00Z",
            "response_headers": {"Cache-Control": "max-age=0"},
            "stored": {"stored_at": "2026-01-01T00:00:00Z"},
        }
    )
    assert result["isError"] is False


@pytest.mark.parametrize("case", _TIME_CASES, ids=[case["case_id"] for case in _TIME_CASES])
def test_time_parser_matches_the_frozen_samples(case):
    try:
        form, timestamp = parse_time(case["input"]["value"], "value")
        actual = {"form": form, "timestamp": timestamp}
    except JudgementError as error:
        actual = error.payload()
    assert canonical.dumps(actual) == canonical.dumps(case["expected"]), case["case_id"]


def test_time_samples_cover_both_forms_and_the_refusal_path():
    forms = set()
    refusals = 0
    for case in _time_cases():
        expected = case["expected"]
        if "error" in expected:
            refusals += 1
            assert expected["error"]["code"] == "INVALID_TIME_FORMAT"
            assert expected["error"]["field"] == "value"
        else:
            forms.add(expected["form"])
    assert forms == {"iso8601", "http-date"}
    assert refusals >= 3, "the refusal path is thin (probe is broken)"
