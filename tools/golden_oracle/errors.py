"""Structured tool-level errors (data/README.md section 4.6)."""

__all__ = ["ToolError", "invalid_input", "invalid_time", "invalid_header_name", "invalid_header_value", "unsupported_method"]

ERROR_CODES = (
    "INVALID_INPUT",
    "INVALID_TIME_FORMAT",
    "INVALID_HEADER_NAME",
    "INVALID_HEADER_VALUE",
    "UNSUPPORTED_METHOD",
)


class ToolError(Exception):
    """A caller mistake that becomes ``{"error": {...}}``, never an exception."""

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
    return ToolError("INVALID_INPUT", field, detail)


def invalid_time(field, value):
    return ToolError(
        "INVALID_TIME_FORMAT",
        field,
        "expected YYYY-MM-DDTHH:MM:SSZ or an HTTP-date, got " + repr(value),
    )


def invalid_header_name(field, name):
    return ToolError("INVALID_HEADER_NAME", field, "not an RFC 9110 token: " + repr(name))


def invalid_header_value(field, detail):
    return ToolError("INVALID_HEADER_VALUE", field, detail)


def unsupported_method(field, method):
    return ToolError("UNSUPPORTED_METHOD", field, "method not in the accepted set: " + repr(method))
