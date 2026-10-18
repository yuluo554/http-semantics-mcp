"""Text-stream UTF-8 guard for every human-facing entry point.

The protocol path reads and writes raw bytes and therefore does not depend on
the process encoding. This guard exists for the human-facing commands
(``--version``, ``--selftest``) and for tool scripts, so that a cp1252 / cp936
console cannot turn a correct build into a ``UnicodeEncodeError``.

Behaviour: only reconfigure when the stream is *not* already UTF-8, so a user's
console that already reports UTF-8 is left untouched.
"""

import sys

__all__ = ["ensure_utf8_stream", "ensure_utf8_stdio", "normalise_encoding_name"]

_UTF8_NAMES = frozenset(("utf8", "utf_8"))


def normalise_encoding_name(encoding):
    """Map ``utf-8`` / ``UTF_8`` / ``utf8`` onto a single comparison key."""
    return (encoding or "").strip().lower().replace("-", "").replace("_", "")


def ensure_utf8_stream(stream):
    """Reconfigure ``stream`` to UTF-8 with LF newlines when needed.

    Returns ``True`` when the stream was reconfigured, ``False`` otherwise
    (already UTF-8, not a text stream, or reconfigure is unavailable).
    """
    if stream is None:
        return False
    if normalise_encoding_name(getattr(stream, "encoding", None)) == "utf8":
        return False
    reconfigure = getattr(stream, "reconfigure", None)
    if reconfigure is None:
        return False
    try:
        reconfigure(encoding="utf-8", errors="replace", newline="\n")
    except (ValueError, OSError):
        return False
    return True


def ensure_utf8_stdio():
    """Apply :func:`ensure_utf8_stream` to stdin, stdout and stderr.

    Returns the names of the streams that were reconfigured.
    """
    changed = []
    for name in ("stdin", "stdout", "stderr"):
        if ensure_utf8_stream(getattr(sys, name, None)):
            changed.append(name)
    return changed
