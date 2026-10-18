"""T4 against the frozen conditional golden cases, plus the branches they miss.

Same rule as the CORS and cache suites: the comparison is *byte* equality of
the canonical serialisation, not a field-by-field assertion, so an extra key or
a changed sort order fails even though every named field looks right
(``data/README.md`` section 4.5). Calls go through the registered handler,
which pins the whole path a client takes: ``tools/call`` -> registry ->
judgement -> tool result.

The 19 frozen cases cover the precedence pairs and both meanings of ``*``. The
tests after them pin the edges no case sits on -- the ``w/`` marker inside
``strong_compare``, the ``If-Modified-Since`` method gate, the exact
``<=`` / ``>`` boundaries -- because a rule without a case cannot be shown to
be doing anything (plan/06 D46 made the same choice for the swr boundary).
"""

import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "data", "golden")

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.judgement.conditional import strong_compare, weak_compare  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402

KEY_SET = {"explain", "rule_applied", "status", "weak_comparison_used"}
ERROR_KEY_SET = {"error"}

RULES = {"none", "if_match", "if_unmodified_since", "if_none_match", "if_modified_since"}
STATUSES = {200, 304, 412}

DATED = "2026-01-01T00:00:00Z"
SAME_DAY = "Thu, 01 Jan 2026 00:00:00 GMT"
BEFORE_DAY = "Wed, 31 Dec 2025 00:00:00 GMT"


def _cases():
    directory = os.path.join(GOLDEN, "conditional_evaluate")
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                yield json.load(handle)


def _all_cases():
    return list(_cases())


def _call(arguments):
    registered = build_registry().get("conditional_evaluate")
    assert registered is not None, "conditional_evaluate is not registered"
    return registered.handler(arguments)


def _judge(headers, method="GET", etag='"abc123"', modified=DATED):
    result = _call(
        {
            "method": method,
            "request_headers": headers,
            "resource": {"etag": etag, "last_modified": modified},
        }
    )
    assert result["isError"] is False, result["content"][0]["text"]
    return json.loads(result["content"][0]["text"])


def _codes(verdict):
    return [entry["code"] for entry in verdict["explain"]]


def test_golden_cases_are_present():
    assert len(_all_cases()) == 19


@pytest.mark.parametrize("case", _all_cases(), ids=[case["case_id"] for case in _all_cases()])
def test_production_output_is_byte_identical_to_the_golden(case):
    result = _call(case["input"])
    expected = case["expected"]
    assert result["isError"] is ("error" in expected), case["case_id"]
    actual = json.loads(result["content"][0]["text"])
    assert canonical.dumps(actual) == canonical.dumps(expected), case["case_id"]


def test_every_case_declares_the_frozen_key_set():
    for case in _all_cases():
        actual = json.loads(_call(case["input"])["content"][0]["text"])
        expected_keys = ERROR_KEY_SET if "error" in case["expected"] else KEY_SET
        assert set(actual) == expected_keys, case["case_id"]


def test_rule_and_status_vocabularies_are_closed():
    for case in _all_cases():
        expected = case["expected"]
        if "error" in expected:
            continue
        assert expected["rule_applied"] in RULES, case["case_id"]
        assert expected["status"] in STATUSES, case["case_id"]


def test_reruns_are_byte_identical():
    for case in _all_cases():
        first = _call(case["input"])
        second = _call(case["input"])
        assert canonical.dumps(first) == canonical.dumps(second), case["case_id"]


def test_header_insertion_order_does_not_change_the_bytes():
    first = _call(
        {
            "method": "PUT",
            "request_headers": {"If-Match": '"abc123"', "If-Unmodified-Since": BEFORE_DAY},
            "resource": {"etag": '"abc123"', "last_modified": DATED},
        }
    )
    second = _call(
        {
            "method": "PUT",
            "request_headers": {"If-Unmodified-Since": BEFORE_DAY, "If-Match": '"abc123"'},
            "resource": {"etag": '"abc123"', "last_modified": DATED},
        }
    )
    assert first["content"][0]["text"] == second["content"][0]["text"]


# -- the comparison functions themselves (plan/03 section 4.2) -------------


def test_strong_and_weak_comparison_are_different_relations():
    strong = {"weak": False, "tag": '"abc123"'}
    weak = {"weak": True, "tag": '"abc123"'}
    other = {"weak": False, "tag": '"other"'}

    assert strong_compare(strong, strong) is True
    assert weak_compare(weak, strong) is True
    assert weak_compare(weak, weak) is True
    # The whole point of the split: a weak tag never satisfies If-Match.
    assert strong_compare(weak, strong) is False
    assert strong_compare(strong, weak) is False
    assert strong_compare(strong, other) is False
    assert weak_compare(strong, other) is False


def test_if_match_never_accepts_a_weak_tag():
    assert _judge({"If-Match": 'W/"abc123"'}, method="PUT")["status"] == 412
    # ... while the same value under If-None-Match is a match: 304 on GET.
    verdict = _judge({"If-None-Match": 'W/"abc123"'})
    assert verdict["status"] == 304
    assert verdict["weak_comparison_used"] is True
    assert _codes(verdict) == ["COND_IF_NONE_MATCH_MATCHED", "COND_WEAK_COMPARISON_USED"]


def test_any_tag_in_the_list_may_match():
    assert _judge({"If-Match": '"other", "abc123"'}, method="PUT")["status"] == 200
    assert _judge({"If-Match": '"other", "third"'}, method="PUT")["status"] == 412
    assert _judge({"If-None-Match": '"other", "abc123"'})["status"] == 304


# -- precedence and short-circuit (RFC 9110 section 13.2.2) ----------------


def test_a_passing_if_match_hides_every_later_precondition():
    verdict = _judge(
        {
            "If-Match": '"abc123"',
            "If-Unmodified-Since": BEFORE_DAY,
            "If-None-Match": '"abc123"',
            "If-Modified-Since": BEFORE_DAY,
        }
    )
    assert verdict["status"] == 200
    assert verdict["rule_applied"] == "if_match"
    assert verdict["explain"] == []


def test_a_failing_if_match_hides_every_later_precondition():
    verdict = _judge(
        {
            "If-Match": '"other"',
            "If-Unmodified-Since": "not a date",
            "If-Modified-Since": "not a date",
        },
        method="PUT",
    )
    assert verdict["status"] == 412
    assert verdict["rule_applied"] == "if_match"
    assert _codes(verdict) == ["COND_IF_MATCH_FAILED"]


def test_if_unmodified_since_decides_before_if_none_match():
    verdict = _judge(
        {"If-Unmodified-Since": BEFORE_DAY, "If-None-Match": '"other"'},
        method="PUT",
    )
    assert verdict["rule_applied"] == "if_unmodified_since"
    assert verdict["status"] == 412


def test_if_none_match_decides_before_if_modified_since():
    verdict = _judge({"If-None-Match": '"other"', "If-Modified-Since": BEFORE_DAY})
    assert verdict["rule_applied"] == "if_none_match"
    # The tags did not match, so nothing else is consulted either: 200.
    assert verdict["status"] == 200
    assert verdict["weak_comparison_used"] is True
    assert _codes(verdict) == ["COND_WEAK_COMPARISON_USED"]


# -- the two meanings of ``*`` -------------------------------------------


def test_if_match_star_needs_a_current_representation():
    assert _judge({"If-Match": "*"}, method="PUT", etag='"abc123"')["status"] == 200
    assert _judge({"If-Match": "*"}, method="PUT", etag=None)["status"] == 412


def test_if_none_match_star_splits_on_the_method():
    assert _judge({"If-None-Match": "*"}, method="GET")["status"] == 304
    assert _judge({"If-None-Match": "*"}, method="HEAD")["status"] == 304
    assert _judge({"If-None-Match": "*"}, method="PUT")["status"] == 412
    # A representation must exist for ``*`` to match anything.
    assert _judge({"If-None-Match": "*"}, method="GET", etag=None)["status"] == 200


# -- dates: strict on the resource, forgiving in the request --------------


def test_if_modified_since_is_ignored_for_methods_that_are_not_retrieval():
    verdict = _judge({"If-Modified-Since": SAME_DAY}, method="PUT")
    assert verdict["status"] == 200
    assert verdict["rule_applied"] == "none"
    assert verdict["explain"] == []


def test_unparsable_request_dates_are_ignored_not_an_error():
    # If-Modified-Since is only read for retrieval methods; If-Unmodified-Since
    # is read for every method.
    for header, method in (("If-Modified-Since", "GET"), ("If-Unmodified-Since", "PUT")):
        verdict = _judge({header: "not a date"}, method=method)
        assert verdict["status"] == 200, header
        assert verdict["rule_applied"] == "none", header
        assert _codes(verdict) == ["COND_IGNORED_INVALID_DATE"], header
        assert verdict["explain"][0]["detail"].startswith(header.lower() + " is not"), header


def test_a_missing_last_modified_decides_nothing():
    unmodified = _judge({"If-Unmodified-Since": SAME_DAY}, method="PUT", modified=None)
    assert unmodified["status"] == 200
    assert unmodified["rule_applied"] == "if_unmodified_since"
    assert unmodified["explain"] == []

    modified = _judge({"If-Modified-Since": SAME_DAY}, modified=None)
    assert modified["status"] == 200
    assert modified["rule_applied"] == "if_modified_since"
    assert modified["explain"] == []


def test_second_granular_boundaries():
    """``>`` for If-Unmodified-Since, ``<=`` for If-Modified-Since."""
    equal = _judge({"If-Unmodified-Since": SAME_DAY}, method="PUT")
    assert equal["status"] == 200

    one_second_early = _judge({"If-Unmodified-Since": "Wed, 31 Dec 2025 23:59:59 GMT"}, method="PUT")
    assert one_second_early["status"] == 412

    not_modified = _judge({"If-Modified-Since": SAME_DAY})
    assert not_modified["status"] == 304

    one_second_early = _judge({"If-Modified-Since": "Wed, 31 Dec 2025 23:59:59 GMT"})
    assert one_second_early["status"] == 200


def test_resource_dates_accept_both_literal_forms():
    verdict = _judge({"If-Modified-Since": SAME_DAY}, modified=SAME_DAY)
    assert verdict["status"] == 304


# -- error paths ---------------------------------------------------------


def test_a_malformed_entity_tag_is_a_header_value_error():
    for header in ("If-Match", "If-None-Match"):
        result = _call({"method": "GET", "request_headers": {header: "abc123"}, "resource": {}})
        assert result["isError"] is True, header
        payload = json.loads(result["content"][0]["text"])
        assert payload["error"]["code"] == "INVALID_HEADER_VALUE", header
        assert payload["error"]["field"] == "request_headers." + header.lower(), header


def test_a_wildcard_may_not_ride_inside_a_tag_list():
    for header in ("If-Match", "If-None-Match"):
        result = _call(
            {"method": "GET", "request_headers": {header: '*, "abc123"'}, "resource": {}}
        )
        assert result["isError"] is True, header
        assert json.loads(result["content"][0]["text"])["error"]["code"] == "INVALID_HEADER_VALUE"


def test_resource_fields_are_validated_before_any_rule_runs():
    bad_etag = _call({"method": "GET", "request_headers": {}, "resource": {"etag": "plain"}})
    assert bad_etag["isError"] is True
    payload = json.loads(bad_etag["content"][0]["text"])
    assert payload["error"]["code"] == "INVALID_HEADER_VALUE"
    assert payload["error"]["field"] == "resource.etag"

    bad_date = _call(
        {"method": "GET", "request_headers": {}, "resource": {"last_modified": "yesterday"}}
    )
    assert bad_date["isError"] is True
    payload = json.loads(bad_date["content"][0]["text"])
    # The resource date is a time literal, so section 4.6 maps it to the time
    # code -- not to the "ignored condition" path, which belongs to the
    # request-header dates.
    assert payload["error"]["code"] == "INVALID_TIME_FORMAT"
    assert payload["error"]["field"] == "resource.last_modified"


def test_missing_required_fields_are_input_errors():
    complete = {
        "method": "GET",
        "request_headers": {},
        "resource": {"etag": '"abc123"', "last_modified": DATED},
    }
    for field in ("method", "request_headers", "resource"):
        incomplete = {key: value for key, value in complete.items() if key != field}
        result = _call(incomplete)
        assert result["isError"] is True, field
        assert json.loads(result["content"][0]["text"])["error"]["field"] == field


def test_an_unknown_method_is_rejected_rather_than_guessed():
    result = _call(
        {"method": "BREW", "request_headers": {}, "resource": {"etag": '"abc123"'}}
    )
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["error"]["code"] == "UNSUPPORTED_METHOD"

    # Method names are case-insensitive.
    assert _judge({"If-Match": '"abc123"'}, method="put")["status"] == 200
