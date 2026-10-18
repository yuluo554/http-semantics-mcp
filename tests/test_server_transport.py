"""Byte-level stdio transport tests.

These drive ``server.serve`` with in-memory bytes so framing, error recovery
and stdout hygiene can be asserted exactly, without subprocess overhead. The
real-subprocess path is covered separately by ``test_stdio_process.py``.
"""

import io

import pytest

from http_semantics_mcp import canonical, errors, protocol, server


class _Buffer(object):
    """Minimal binary stream: readline-based input, append-only output."""

    def __init__(self, data=b""):
        self._incoming = io.BytesIO(data)
        self.outgoing = b""

    def readline(self, limit=-1):
        return self._incoming.readline(limit)

    def write(self, payload):
        self.outgoing += payload

    def flush(self):
        pass


def _run(stream_bytes, limit=protocol.MAX_MESSAGE_BYTES):
    stdin = _Buffer(stream_bytes)
    stdout = _Buffer()
    code = server.serve(stdin=stdin, stdout=stdout, stderr=io.StringIO())
    return code, stdout.outgoing


def _lines(payload):
    return [line for line in payload.split(b"\n") if line]


def _decode(payload):
    return [canonical.loads(line.decode("utf-8")) for line in _lines(payload)]


INIT = b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}\n'


def test_frames_are_newline_delimited_without_carriage_returns():
    _, out = _run(INIT + b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n')
    assert b"\r" not in out
    assert out.endswith(b"\n")


def test_crlf_input_is_accepted():
    _, out = _run(INIT.replace(b"\n", b"\r\n") + b'{"jsonrpc":"2.0","id":2,"method":"ping"}\r\n')
    messages = _decode(out)
    assert [message["id"] for message in messages] == [1, 2]


def test_blank_lines_are_skipped_without_a_response():
    _, out = _run(b"\n\n" + INIT + b"\n\n")
    assert len(_lines(out)) == 1


def test_invalid_json_yields_parse_error_with_null_id():
    _, out = _run(b"{not json}\n")
    messages = _decode(out)
    assert len(messages) == 1
    assert messages[0]["error"]["code"] == errors.PARSE_ERROR
    assert messages[0]["id"] is None


def test_invalid_utf8_yields_parse_error():
    _, out = _run(b'{"jsonrpc":"2.0","id":1,"method":"\xff\xfe"}\n')
    assert _decode(out)[0]["error"]["code"] == errors.PARSE_ERROR


def test_oversized_line_is_rejected_and_stream_continues():
    huge = b'{"jsonrpc":"2.0","id":1,"method":"' + b"x" * (protocol.MAX_MESSAGE_BYTES + 16) + b'"}\n'
    _, out = _run(huge + b'{"jsonrpc":"2.0","id":9,"method":"ping"}\n')
    messages = _decode(out)
    assert len(messages) == 2
    assert messages[0]["error"]["code"] == errors.INVALID_REQUEST
    assert messages[1] == {"jsonrpc": "2.0", "id": 9, "result": {}}


def test_eof_exits_zero():
    code, out = _run(b"")
    assert code == 0
    assert out == b""


def test_multiple_requests_keep_order():
    payload = INIT
    for request_id in range(2, 6):
        payload += ('{"jsonrpc":"2.0","id":%d,"method":"ping"}\n' % request_id).encode()
    messages = _decode(_run(payload)[1])
    assert [message["id"] for message in messages] == [1, 2, 3, 4, 5]


def test_notification_produces_no_output_line():
    _, out = _run(INIT + b'{"jsonrpc":"2.0","method":"notifications/initialized"}\n')
    assert len(_lines(out)) == 1


def test_every_stdout_line_is_parseable_json():
    payload = (
        INIT
        + b'{"jsonrpc":"2.0","id":2,"method":"ping"}\n'
        + b"garbage\n"
        + b'{"jsonrpc":"2.0","id":3,"method":"tools/list"}\n'
    )
    for line in _lines(_run(payload)[1]):
        canonical.loads(line.decode("utf-8"))


def test_read_messages_helper_matches_serve_framing():
    events = server.read_messages(INIT + b"\n" + b"garbage\n")
    assert [kind for kind, _ in events] == ["message", "parse_error"]


@pytest.mark.parametrize("method", ["resources/list", "prompts/list", "logging/setLevel"])
def test_unimplemented_mcp_families_answer_method_not_found(method):
    payload = INIT + ('{"jsonrpc":"2.0","id":2,"method":"%s"}\n' % method).encode()
    messages = _decode(_run(payload)[1])
    assert messages[1]["error"]["code"] == errors.METHOD_NOT_FOUND
