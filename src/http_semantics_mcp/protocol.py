"""MCP protocol subset over JSON-RPC 2.0.

Supported methods (see plan/02 section 5.3):

* ``initialize``                  -> server info + declared capabilities
* ``notifications/initialized``   -> accepted, no response
* ``notifications/cancelled``     -> accepted, ignored
* ``ping``                        -> ``{}``, available before initialize
* ``tools/list``                  -> registered tool descriptors
* ``tools/call``                  -> dispatch to a tool handler

Everything else answers ``-32601``. ``resources`` / ``prompts`` / ``logging``
are not implemented and are not advertised in ``capabilities``.

The module performs no I/O: it consumes parsed objects and returns response
objects, which keeps it directly testable and keeps transport concerns in
``server.py``.
"""

from . import __version__, errors
from .registry import build_registry

__all__ = [
    "SUPPORTED_PROTOCOL_VERSIONS",
    "DEFAULT_PROTOCOL_VERSION",
    "MAX_MESSAGE_BYTES",
    "Session",
]

# Frozen constant. Changing it is a protocol-behaviour change and must be
# recorded in plan/06 (D22).
SUPPORTED_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL_VERSION = "2025-06-18"

# Upper bound for a single newline-delimited message (D31).
MAX_MESSAGE_BYTES = 8 * 1024 * 1024

SERVER_NAME = "http-semantics-mcp"


def _negotiate_version(requested):
    if requested in SUPPORTED_PROTOCOL_VERSIONS:
        return requested
    return DEFAULT_PROTOCOL_VERSION


def _server_info():
    return {"name": SERVER_NAME, "version": __version__}


def _capabilities():
    # Only ``tools`` is declared: anything not declared answers -32601.
    return {"tools": {"listChanged": False}}


class Session(object):
    """Protocol state for one stdio connection.

    One ``Session`` per process. ``handle`` is pure with respect to the
    message: the only state it mutates is ``initialized``.
    """

    def __init__(self, registry=None):
        self.registry = build_registry() if registry is None else registry
        self.initialized = False

    # -- entry point -----------------------------------------------------

    def handle(self, message):
        """Handle one parsed JSON-RPC message.

        Returns a list with either zero responses (notification / cancelled)
        or exactly one response object.
        """
        if isinstance(message, list):
            return self._reject(None, errors.INVALID_REQUEST, "batch requests are not supported")
        if not isinstance(message, dict):
            return self._reject(None, errors.INVALID_REQUEST, "message must be a JSON object")

        is_notification = "id" not in message
        request_id = message.get("id")

        if message.get("jsonrpc") != "2.0":
            return self._reject(request_id, errors.INVALID_REQUEST, "jsonrpc must be \"2.0\"")

        method = message.get("method")
        if not isinstance(method, str) or not method:
            return self._reject(request_id, errors.INVALID_REQUEST, "method must be a non-empty string")

        params = message.get("params")
        if params is not None and not isinstance(params, dict):
            return self._reject(request_id, errors.INVALID_REQUEST, "params must be an object")

        handler = self._resolve(method)
        if handler is None:
            if is_notification:
                return []
            return self._reject(request_id, errors.METHOD_NOT_FOUND, "unknown method: " + method)

        if not is_notification and not self.initialized and method not in _PRE_INIT_METHODS:
            return self._reject(request_id, errors.SERVER_NOT_INITIALIZED)

        try:
            result = handler(params or {})
        except errors.ProtocolError as exc:
            if is_notification:
                return []
            return self._reject(request_id, exc.code, exc.message, data=exc.data)
        except Exception as exc:  # noqa: BLE001 - protocol must never crash
            if is_notification:
                return []
            return self._reject(
                request_id,
                errors.INTERNAL_ERROR,
                "internal error",
                data={"exception": type(exc).__name__},
            )

        if is_notification:
            return []
        return [errors.success_response(request_id, result)]

    # -- method table ----------------------------------------------------

    def _resolve(self, method):
        attribute = _METHODS.get(method)
        if attribute is None:
            return None
        return getattr(self, attribute)

    def _reject(self, request_id, code, message=None, data=None):
        return [errors.error_response(request_id, code, message, data)]

    def _initialize(self, params):
        self.initialized = True
        return {
            "protocolVersion": _negotiate_version(params.get("protocolVersion")),
            "capabilities": _capabilities(),
            "serverInfo": _server_info(),
        }

    def _noop(self, params):
        return {}

    def _ping(self, params):
        return {}

    def _tools_list(self, params):
        return {"tools": self.registry.descriptors()}

    def _tools_call(self, params):
        name = params.get("name")
        if not isinstance(name, str) or not name:
            raise errors.ProtocolError(errors.INVALID_PARAMS, "tools/call requires a tool name")
        tool = self.registry.get(name)
        if tool is None:
            raise errors.ProtocolError(errors.INVALID_PARAMS, "unknown tool: " + name)

        arguments = params.get("arguments")
        if arguments is None:
            arguments = {}
        if not isinstance(arguments, dict):
            raise errors.ProtocolError(errors.INVALID_PARAMS, "arguments must be an object")

        # Tool-face failures (bad input) are results with isError=true, not
        # JSON-RPC errors (data/README.md section 4.6).
        return tool.handler(arguments)


# Dispatch is by method name -> Session attribute name. Storing functions
# instead would lose the bound ``self`` and break every call.
_METHODS = {
    "initialize": "_initialize",
    "notifications/initialized": "_noop",
    "notifications/cancelled": "_noop",
    "ping": "_ping",
    "tools/list": "_tools_list",
    "tools/call": "_tools_call",
}

_PRE_INIT_METHODS = frozenset(("initialize", "ping"))
