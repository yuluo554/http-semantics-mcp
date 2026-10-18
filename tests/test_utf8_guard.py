"""UTF-8 guard behaviour, including the cp1252 reproduction.

The point of the guard is that a *non-UTF-8* console cannot turn correct
output into ``UnicodeEncodeError``. The test therefore has to build a real
cp1252 stream -- asserting on the local console would prove nothing, because
this machine's console is already UTF-8-aware.
"""

import io

from http_semantics_mcp import _utf8


def _cp1252_stream():
    raw = io.BytesIO()
    stream = io.TextIOWrapper(raw, encoding="cp1252", errors="strict", newline="")
    return stream, raw


def test_cp1252_stream_fails_before_the_guard():
    stream, _ = _cp1252_stream()
    try:
        stream.write("值\n")
    except UnicodeEncodeError:
        return
    raise AssertionError("cp1252 stream unexpectedly accepted non-ASCII")


def test_guard_makes_cp1252_stream_accept_non_ascii():
    stream, raw = _cp1252_stream()
    changed = _utf8.ensure_utf8_stream(stream)
    stream.write("值\n")
    stream.flush()
    assert changed is True
    assert raw.getvalue() == "值\n".encode("utf-8")


def test_utf8_stream_is_left_untouched():
    stream = io.StringIO()
    assert _utf8.ensure_utf8_stream(stream) is False


def test_none_stream_is_tolerated():
    assert _utf8.ensure_utf8_stream(None) is False


def test_stream_without_reconfigure_is_tolerated():
    class Plain(object):
        encoding = "cp1252"

    assert _utf8.ensure_utf8_stream(Plain()) is False


def test_encoding_name_normalisation():
    assert _utf8.normalise_encoding_name("UTF-8") == "utf8"
    assert _utf8.normalise_encoding_name("utf_8") == "utf8"
    assert _utf8.normalise_encoding_name("cp1252") == "cp1252"
    assert _utf8.normalise_encoding_name(None) == ""
