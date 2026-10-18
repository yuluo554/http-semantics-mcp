"""Tool-face errors raised by the judgement layer (data/README.md section 4.6).

A caller mistake is a *result* with ``isError: true``, never a traceback: the
tool face catches :class:`JudgementError` and renders it (plan/03 section 7).
The five codes are the frozen enumeration; ``detail`` is a fixed template, not
free text, so it can be regression-tested.

This is deliberately not ``http_semantics_mcp.errors``: that module carries the
JSON-RPC *transport* codes, and mixing the two faces is how a protocol error
ends up looking like a rule violation.
"""

__all__ = [
    "JudgementError",
    "invalid_input",
    "invalid_header_name",
    "invalid_header_value",
    "invalid_time_format",
    "unsupported_method",
]

ERROR_CODES = (
    "INVALID_INPUT",
    "INVALID_TIME_FORMAT",
    "INVALID_HEADER_NAME",
    "INVALID_HEADER_VALUE",
    "UNSUPPORTED_METHOD",
)


class JudgementError(Exception):
    """A caller mistake, rendered as ``{"error": {"code", "field", "detail"}}``."""

    def __init__(self, code, field, detail):
        if code not in ERROR_CODES:
            raise ValueError("unknown error code: " + code)
        Exception.__init__(self, code + ": " + detail)
        self.code = code
        self.field = field
        self.detail = detail

    def payload(self):
        return {"error": {"code": self.code, "field": self.field, "detail": self.detail}}


def invalid_input(field, detail):
    return JudgementError("INVALID_INPUT", field, detail)


def invalid_header_name(field, name):
    return JudgementError("INVALID_HEADER_NAME", field, "not an RFC 9110 token: " + repr(name))


def invalid_header_value(field, detail):
    return JudgementError("INVALID_HEADER_VALUE", field, detail)


def invalid_time_format(field, value):
    return JudgementError(
        "INVALID_TIME_FORMAT",
        field,
        "expected YYYY-MM-DDTHH:MM:SSZ or an HTTP-date, got " + repr(value),
    )


def unsupported_method(field, method):
    return JudgementError("UNSUPPORTED_METHOD", field, "method not in the accepted set: " + repr(method))
