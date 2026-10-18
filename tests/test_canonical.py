"""Serialisation and transport-framing determinism."""

import hashlib

import pytest

from http_semantics_mcp import canonical


def _digest(payload):
    return hashlib.sha256(payload).hexdigest()


def test_key_order_is_ascii_sorted():
    assert canonical.dumps({"b": 1, "a": 2}) == '{"a":2,"b":1}'


def test_no_whitespace_is_emitted():
    assert canonical.dumps({"a": [1, 2]}) == '{"a":[1,2]}'


def test_non_ascii_is_not_escaped():
    assert canonical.dumps({"k": "值"}) == '{"k":"值"}'


def test_frame_is_exactly_one_trailing_newline():
    payload = canonical.encode_message({"a": 1})
    assert payload == b'{"a":1}\n'
    assert payload.count(b"\n") == 1
    assert b"\r" not in payload


def test_two_calls_are_byte_identical():
    value = {"violations": [{"code": "CORS_X"}, {"code": "CORS_A"}], "notes": {"z": False, "a": True}}
    assert _digest(canonical.encode_message(value)) == _digest(canonical.encode_message(value))


def test_input_key_order_does_not_change_output_bytes():
    left = {"b": 1, "a": {"d": 4, "c": 3}}
    right = {"a": {"c": 3, "d": 4}, "b": 1}
    assert canonical.encode_message(left) == canonical.encode_message(right)


def test_nan_and_infinity_are_rejected():
    with pytest.raises(ValueError):
        canonical.dumps({"x": float("nan")})
    with pytest.raises(ValueError):
        canonical.dumps({"x": float("inf")})


def test_loads_rejects_nan_literal_input():
    with pytest.raises(ValueError):
        canonical.loads('{"x": NaN}')


def test_no_timestamp_or_process_fields_leak():
    """Guard against the three usual determinism leaks appearing in output."""
    payload = canonical.dumps({"a": 1}).lower()
    for token in ("timestamp", "pid", "elapsed", "hostname"):
        assert token not in payload
