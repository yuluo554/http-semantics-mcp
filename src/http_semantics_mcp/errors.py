"""JSON-RPC 2.0 error codes used on the protocol face.

These are *transport* errors. The tool-face error codes (``INVALID_INPUT``,
``INVALID_TIME_FORMAT``, ...) are defined once in ``data/README.md`` section
4.6 and will be generated into ``references/codes.json`` at M1. Do not add a
second copy of the tool-face enumeration here.
"""

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603

# MCP lifecycle error: a request arrived before ``initialize``.
SERVER_NOT_INITIALIZED = -32002

_MESSAGES = {
    PARSE_ERROR: "Parse error",
    INVALID_REQUEST: "Invalid Request",
    METHOD_NOT_FOUND: "Method not found",
    INVALID_PARAMS: "Invalid params",
    INTERNAL_ERROR: "Internal error",
    SERVER_NOT_INITIALIZED: "Server not initialized",
}


class ProtocolError(Exception):
    """Control-flow exception used by method handlers.

    It is caught by ``Session.handle`` and converted into a JSON-RPC error
    response, so a rejected request never escapes as a traceback.
    """

    def __init__(self, code, message=None, data=None):
        Exception.__init__(self, message or "")
        self.code = code
        self.message = message
        self.data = data


def error_payload(code, message=None, data=None):
    """Build a JSON-RPC ``error`` object."""
    payload = {
        "code": code,
        "message": _MESSAGES.get(code, "Error") if message is None else message,
    }
    if data is not None:
        payload["data"] = data
    return payload


def error_response(request_id, code, message=None, data=None):
    """Build a complete JSON-RPC error response."""
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": error_payload(code, message, data),
    }


def success_response(request_id, result):
    """Build a complete JSON-RPC success response."""
    return {"jsonrpc": "2.0", "id": request_id, "result": result}
