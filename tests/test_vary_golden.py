"""T5 against the frozen vary golden cases, plus the branches they miss.

Byte equality of the canonical serialisation again (``data/README.md`` section
4.5), through the registered handler so the whole client path is covered.

Two things the nine frozen cases cannot show, and which therefore get their own
tests here:

* **the policy table is the source of truth**, not a branch in the code -- the
  test swaps one row of ``catalog["vary_normalization"]`` and watches the
  verdict flip;
* **a repeat is reported once, in source order**, and the ``Vary: *`` short
  circuit suppresses that notice entirely.
"""

import copy
import json
import os

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GOLDEN = os.path.join(ROOT, "data", "golden")

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.judgement.vary import evaluate_vary  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402
from http_semantics_mcp.rules import CATALOG  # noqa: E402

KEY_SET = {"differing_headers", "match", "normalized_vary", "reasons"}
MATCHES = {"hit", "miss"}


def _cases():
    directory = os.path.join(GOLDEN, "vary_match")
    for name in sorted(os.listdir(directory)):
        if name.endswith(".json"):
            with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                yield json.load(handle)


def _all_cases():
    return list(_cases())


def _call(arguments):
    registered = build_registry().get("vary_match")
    assert registered is not None, "vary_match is not registered"
    return registered.handler(arguments)


def _judge(vary, stored, incoming):
    result = _call(
        {
            "cached": {"vary": vary, "request_headers_at_store": stored},
            "incoming": {"request_headers": incoming},
        }
    )
    assert result["isError"] is False, result["content"][0]["text"]
    return json.loads(result["content"][0]["text"])


def _codes(verdict):
    return [entry["code"] for entry in verdict["reasons"]]


def test_golden_cases_are_present():
    assert len(_all_cases()) == 9


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


def test_match_vocabulary_is_closed():
    for case in _all_cases():
        assert case["expected"]["match"] in MATCHES, case["case_id"]


def test_reruns_are_byte_identical():
    for case in _all_cases():
        first = _call(case["input"])
        second = _call(case["input"])
        assert canonical.dumps(first) == canonical.dumps(second), case["case_id"]


def test_header_insertion_order_does_not_change_the_bytes():
    first = _call(
        {
            "cached": {
                "vary": "Accept-Encoding, Accept-Language",
                "request_headers_at_store": {"Accept-Encoding": "gzip", "Accept-Language": "en"},
            },
            "incoming": {"request_headers": {"Accept-Language": "en", "Accept-Encoding": "gzip"}},
        }
    )
    second = _call(
        {
            "cached": {
                "vary": "Accept-Language, Accept-Encoding",
                "request_headers_at_store": {"Accept-Language": "en", "Accept-Encoding": "gzip"},
            },
            "incoming": {"request_headers": {"Accept-Encoding": "gzip", "Accept-Language": "en"}},
        }
    )
    assert first["content"][0]["text"] == second["content"][0]["text"]


# -- the policy table is data (plan/03 section 5.2) -----------------------


def test_the_normalisation_policy_is_read_from_the_catalog():
    """Prove the per-field policy is a table lookup, not a code branch."""
    arguments = {
        "cached": {"vary": "Accept", "request_headers_at_store": {"Accept": "text/HTML"}},
        "incoming": {"request_headers": {"Accept": "text/html"}},
    }
    registered = build_registry().get("vary_match")
    assert registered.handler(arguments)["content"][0]["text"] == canonical.dumps(
        {"differing_headers": [], "match": "hit", "normalized_vary": ["accept"], "reasons": []}
    )

    strict = copy.deepcopy(CATALOG)
    strict["vary_normalization"]["fields"]["accept"]["case_sensitive"] = True
    assert evaluate_vary(arguments, strict)["match"] == "miss"

    loose = copy.deepcopy(CATALOG)
    loose["vary_normalization"]["fields"]["x-mode"] = {
        "case_sensitive": False,
        "fold_whitespace": True,
        "sort_comma_segments": False,
        "trim": True,
    }
    flipped = {
        "cached": {"vary": "X-Mode", "request_headers_at_store": {"X-Mode": "Fast"}},
        "incoming": {"request_headers": {"X-Mode": "fast"}},
    }
    assert evaluate_vary(flipped, CATALOG)["match"] == "miss"
    assert evaluate_vary(flipped, loose)["match"] == "hit"


def test_the_field_policies_match_the_table_rows():
    # accept: case-insensitive, order-blind, whitespace-folded.
    assert _judge(
        "Accept",
        {"Accept": "Text/HTML,  Application/JSON"},
        {"Accept": "application/json,text/html"},
    )["match"] == "hit"
    # accept-encoding: same policy row.
    assert _judge(
        "Accept-Encoding",
        {"Accept-Encoding": "gzip, br"},
        {"Accept-Encoding": "br,gzip"},
    )["match"] == "hit"
    # user-agent: case-sensitive and no whitespace folding.
    assert _judge("User-Agent", {"User-Agent": "A  B"}, {"User-Agent": "a b"})["match"] == "miss"
    # the default row: whitespace folded, case sensitive, order significant.
    assert _judge("X-Mode", {"X-Mode": "  fast   path  "}, {"X-Mode": "fast path"})["match"] == "hit"
    assert _judge("X-Mode", {"X-Mode": "fast  path"}, {"X-Mode": "fast path"})["match"] == "hit"
    assert _judge("X-Mode", {"X-Mode": "a, b"}, {"X-Mode": "b, a"})["match"] == "miss"


# -- absent vs empty, repeats, and ``*`` ---------------------------------


def test_a_field_absent_on_both_sides_is_not_a_difference():
    verdict = _judge("X-Mode", {}, {})
    assert verdict["match"] == "hit"
    assert verdict["reasons"] == []
    assert verdict["differing_headers"] == []


def test_present_but_empty_is_reported_though_it_compares_equal():
    verdict = _judge("X-Mode", {"X-Mode": "   "}, {})
    assert verdict["match"] == "hit"
    assert verdict["differing_headers"] == []
    assert _codes(verdict) == ["VARY_FIELD_MISSING"]


def test_a_repeat_is_reported_once_in_source_order():
    verdict = _judge("X-Mode, X-Mode, Accept, Accept", {"X-Mode": "a"}, {"X-Mode": "a"})
    assert verdict["normalized_vary"] == ["accept", "x-mode"]
    assert _codes(verdict) == ["VARY_DUPLICATE_FIELD"]
    assert verdict["reasons"][0]["detail"] == "Vary lists x-mode more than once; duplicates removed"


def test_a_duplicate_rides_along_with_a_mismatch():
    verdict = _judge("Accept, Accept", {"Accept": "a"}, {"Accept": "b"})
    assert verdict["match"] == "miss"
    assert _codes(verdict) == ["VARY_DUPLICATE_FIELD", "VARY_FIELD_MISMATCH"]


def test_vary_star_decides_alone():
    verdict = _judge("*", {"X-Mode": "a"}, {"X-Mode": "b"})
    assert verdict["match"] == "miss"
    assert verdict["normalized_vary"] == ["*"]
    assert verdict["differing_headers"] == []
    assert _codes(verdict) == ["VARY_STAR_NEVER_MATCHES"]

    # Inside a list it still short-circuits, and the repeat notice stays out of
    # the answer: the verdict was already decided by "everything".
    both = _judge("Accept, *, Accept", {"Accept": "a"}, {"Accept": "a"})
    assert both["match"] == "miss"
    assert both["normalized_vary"] == ["*", "accept"]
    assert _codes(both) == ["VARY_STAR_NEVER_MATCHES"]


def test_an_empty_vary_value_varies_on_nothing():
    for value in ("", "   ", ",", None):
        verdict = _judge(value, {"Accept": "a"}, {"Accept": "b"})
        assert verdict["match"] == "hit", value
        assert verdict["normalized_vary"] == [], value


def test_multi_value_headers_compare_on_the_first_value():
    assert _judge("X-Mode", {"X-Mode": ["a", "b"]}, {"X-Mode": "a"})["match"] == "hit"
    assert _judge("X-Mode", {"X-Mode": ["a", "b"]}, {"X-Mode": "b"})["match"] == "miss"


def test_members_are_lowercased_sorted_and_deduplicated():
    verdict = _judge("ACCEPT-ENCODING, Accept , x-mode", {}, {})
    assert verdict["normalized_vary"] == ["accept", "accept-encoding", "x-mode"]


# -- error paths ---------------------------------------------------------


def test_missing_or_malformed_inputs_are_tool_errors():
    cases = [
        ({"incoming": {"request_headers": {}}}, "cached"),
        ({"cached": "x", "incoming": {"request_headers": {}}}, "cached"),
        ({"cached": {"vary": "Accept"}}, "incoming"),
        ({"cached": {"vary": 7}, "incoming": {"request_headers": {}}}, "cached.vary"),
        ({"cached": {"vary": ["Accept", 7]}, "incoming": {"request_headers": {}}}, "cached.vary"),
    ]
    for arguments, field in cases:
        result = _call(arguments)
        assert result["isError"] is True, field
        payload = json.loads(result["content"][0]["text"])
        assert payload["error"]["code"] == "INVALID_INPUT", field
        assert payload["error"]["field"] == field, field


def test_a_malformed_header_name_is_rejected_on_either_side():
    for arguments in (
        {"cached": {"vary": "Accept", "request_headers_at_store": {"Bad Name": "x"}},
         "incoming": {"request_headers": {}}},
        {"cached": {"vary": "Accept", "request_headers_at_store": {}},
         "incoming": {"request_headers": {"Bad Name": "x"}}},
    ):
        result = _call(arguments)
        assert result["isError"] is True
        assert json.loads(result["content"][0]["text"])["error"]["code"] == "INVALID_HEADER_NAME"


def test_headers_are_validated_even_when_vary_star_decides_the_verdict():
    result = _call(
        {
            "cached": {"vary": "*", "request_headers_at_store": {"Bad Name": "x"}},
            "incoming": {"request_headers": {}},
        }
    )
    assert result["isError"] is True
    assert json.loads(result["content"][0]["text"])["error"]["code"] == "INVALID_HEADER_NAME"
