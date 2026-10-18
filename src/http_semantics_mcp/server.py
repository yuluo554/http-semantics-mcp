"""Byte-level stdio transport.

Design decisions that matter for determinism and cross-platform behaviour
(see plan/02 section 4):

* Read and write **binary** streams. Text-mode stdin on Windows applies code
  page decoding and newline translation, which would make the same session
  produce different bytes on different machines.
* One message per line, ``\\n`` terminated. A trailing ``\\r`` on input is
  stripped; output never contains ``\\r``.
* Empty lines are skipped without a response (clients sometimes send blank
  padding).
* An oversized line is drained and rejected with ``-32600``; the process keeps
  serving instead of dying.
* stdout carries protocol messages only. Diagnostics go to stderr.
"""

import sys

from . import canonical, errors
from .protocol import MAX_MESSAGE_BYTES, Session

__all__ = ["serve", "read_messages", "write_response"]


def _write(stream, payload):
    stream.write(payload)
    stream.flush()


def write_response(stream, response):
    """Write one response object as a framed line."""
    _write(stream, canonical.encode_message(response))


def _reject(stream, code, message=None):
    write_response(stream, errors.error_response(None, code, message))


def _drain(stream):
    """Consume bytes up to and including the next newline."""
    while True:
        chunk = stream.readline()
        if not chunk or chunk.endswith(b"\n"):
            return


def serve(stdin=None, stdout=None, stderr=None, session=None):
    """Run the stdio loop until EOF.

    Returns the process exit code (always ``0``: a malformed request is a
    protocol error, not a process failure).
    """
    stdin = sys.stdin.buffer if stdin is None else stdin
    stdout = sys.stdout.buffer if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    session = Session() if session is None else session

    while True:
        raw = stdin.readline(MAX_MESSAGE_BYTES + 2)
        if not raw:
            break

        if not raw.endswith(b"\n") and len(raw) > MAX_MESSAGE_BYTES:
            _drain(stdin)
            _reject(stdout, errors.INVALID_REQUEST, "message exceeds " + str(MAX_MESSAGE_BYTES) + " bytes")
            continue

        line = raw.rstrip(b"\r\n")
        if not line.strip():
            continue

        try:
            text = line.decode("utf-8")
        except UnicodeDecodeError:
            _reject(stdout, errors.PARSE_ERROR, "message is not valid UTF-8")
            continue

        try:
            message = canonical.loads(text)
        except ValueError:
            _reject(stdout, errors.PARSE_ERROR)
            continue

        for response in session.handle(message):
            write_response(stdout, response)

    return 0


def read_messages(data):
    """Split a byte blob into decoded request objects (test helper).

    Mirrors the framing rules used by :func:`serve`, but returns diagnostics
    instead of writing them, so tests can assert on both sides.
    """
    events = []
    for raw in data.splitlines():
        if not raw.strip():
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            events.append(("decode_error", raw))
            continue
        try:
            events.append(("message", canonical.loads(text)))
        except ValueError:
            events.append(("parse_error", text))
    return events
