"""Tool registry: the single place where tools are declared.

M2 registered the two CORS tools, M3 added ``cache_evaluate`` and M4 the
remaining two; M5 replaces the inlined ``inputSchema`` objects with generated
ones. Until then the schemas are hand-written but honest: they list exactly the
fields the handlers read, and every field the handlers require is in
``required``.

Each tool descriptor is a plain dict with the exact keys the MCP schema
requires (``name``, ``description``, ``inputSchema``) plus an optional
``outputSchema``. The handler is stored separately so that ``tools/list`` can
never accidentally serialise a callable.
"""

import copy

from .toolface import handlers

__all__ = ["Tool", "Registry", "build_registry", "TOOL_DESCRIPTIONS", "INPUT_SCHEMAS"]


class Tool(object):
    """A registered tool: client-visible descriptor plus its handler."""

    __slots__ = ("name", "description", "input_schema", "output_schema", "handler")

    def __init__(self, name, description, input_schema, handler, output_schema=None):
        self.name = name
        self.description = description
        self.input_schema = input_schema
        self.output_schema = output_schema
        self.handler = handler

    def descriptor(self):
        """Return the client-visible descriptor (a fresh copy each call)."""
        descriptor = {
            "name": self.name,
            "description": self.description,
            "inputSchema": copy.deepcopy(self.input_schema),
        }
        if self.output_schema is not None:
            descriptor["outputSchema"] = copy.deepcopy(self.output_schema)
        return descriptor


class Registry(object):
    """Ordered-by-name registry of tools."""

    def __init__(self, tools=None):
        self._tools = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool):
        if not isinstance(tool, Tool):
            raise TypeError("registry accepts Tool instances only")
        if tool.name in self._tools:
            raise ValueError("duplicate tool name: " + tool.name)
        self._tools[tool.name] = tool

    def get(self, name):
        return self._tools.get(name)

    def names(self):
        """Tool names in ASCII ascending order (see plan/02 section 5.4)."""
        return sorted(self._tools)

    def descriptors(self):
        """Client-visible descriptors, ordered by name."""
        return [self._tools[name].descriptor() for name in self.names()]

    def __len__(self):
        return len(self._tools)


# -- declarations ---------------------------------------------------------

TOOL_DESCRIPTIONS = {
    "cache_evaluate": (
        "Decide whether a stored response may be reused without revalidating. "
        "Applies the RFC 9111 age and freshness arithmetic (Date, Age, "
        "Cache-Control, Expires, Last-Modified) and returns action "
        "serve|revalidate|miss, the age and freshness lifetime in whole "
        "seconds, and the rule IDs with their clause references. now is an "
        "argument: the cache never reads a clock."
    ),
    "conditional_evaluate": (
        "Judge one request's preconditions and report the status they decide. "
        "Evaluates If-Match, If-Unmodified-Since, If-None-Match and "
        "If-Modified-Since in the RFC 9110 section 13.2.2 precedence order, "
        "stopping at the first applicable one, and returns status 200|304|412, "
        "which rule decided it, and the rule IDs with their clause references."
    ),
    "cors_evaluate": (
        "Judge one HTTP response against the Fetch Standard CORS check. "
        "Returns decision allow|block, the violated rule IDs with their clause "
        "references, the headers that are missing, and what to send instead. "
        "No network: url is parsed for scheme/host/port only."
    ),
    "cors_simulate_fetch": (
        "Walk a redirect chain hop by hop and judge each hop with the CORS "
        "check. Reports the ordered redirect events (origin_set_to_null, "
        "credentials_dropped), the visible response headers, and the effective "
        "Access-Control-Max-Age."
    ),
    "vary_match": (
        "Decide whether a stored response can be reused for an incoming "
        "request, per RFC 9111 section 4.1. Compares the fields named by the "
        "stored Vary value under that field's normalisation policy and returns "
        "match hit|miss, the fields that differ, the normalised Vary members, "
        "and the rule IDs with their clause references."
    ),
}

_HEADER_VALUES = {
    "type": ["string", "array"],
    "items": {"type": "string"},
    "description": "one value, or an array for a repeated header",
}

_HEADERS = {
    "type": "object",
    "additionalProperties": _HEADER_VALUES,
    "description": "header name -> value",
}

_RESPONSE = {
    "type": "object",
    "properties": {"status": {"type": "integer"}, "headers": _HEADERS},
    "required": ["status"],
    "additionalProperties": False,
}

_CREDENTIALS = {
    "type": "string",
    "enum": ["omit", "include"],
    "description": "credentials mode of the request",
}

_ORIGIN = {
    "type": ["string", "null"],
    "description": "request Origin; omit or null for a same-origin request",
}

_CORS_REQUEST_PROPERTIES = {
    "method": {"type": "string", "description": "HTTP request method"},
    "url": {"type": "string", "description": "target URL; only its origin is used"},
    "origin": _ORIGIN,
    "credentials": _CREDENTIALS,
    "request_headers": _HEADERS,
    "response": _RESPONSE,
    "is_preflight": {"type": "boolean", "description": "is this the preflight response?"},
}

_STORED = {
    "type": "object",
    "properties": {
        "stored_at": {
            "type": "string",
            "description": "instant the response was stored (YYYY-MM-DDTHH:MM:SSZ or an HTTP-date)",
        },
        "age": {
            "type": ["string", "integer"],
            "description": "Age as recorded at store time; wins over a response Age header",
        },
        "headers": _HEADERS,
    },
    "required": ["stored_at"],
    "additionalProperties": False,
}

_CACHE_DIRECTIVES = {
    "now": {
        "type": "string",
        "description": "evaluation instant (YYYY-MM-DDTHH:MM:SSZ or an HTTP-date)",
    },
    "request_headers": _HEADERS,
    "response_headers": _HEADERS,
    "stored": _STORED,
}

# The current representation, as the server knows it. Both fields are optional:
# a resource with no entity tag cannot satisfy ``If-Match`` at all, which is a
# verdict rather than a caller mistake.
_RESOURCE = {
    "type": "object",
    "properties": {
        "etag": {
            "type": ["string", "null"],
            "description": "current entity tag, quotes (and any W/ marker) included",
        },
        "last_modified": {
            "type": ["string", "null"],
            "description": "current Last-Modified (YYYY-MM-DDTHH:MM:SSZ or an HTTP-date)",
        },
    },
    "additionalProperties": False,
}

_CACHED_ENTRY = {
    "type": "object",
    "properties": {
        "vary": {
            "type": ["string", "array"],
            "items": {"type": "string"},
            "description": "the stored response's Vary field value",
        },
        "request_headers_at_store": _HEADERS,
    },
    "additionalProperties": False,
}

INPUT_SCHEMAS = {
    "cache_evaluate": {
        "type": "object",
        "properties": dict(_CACHE_DIRECTIVES),
        "required": ["now", "stored"],
        "additionalProperties": False,
    },
    "conditional_evaluate": {
        "type": "object",
        "properties": {
            "method": {"type": "string", "description": "HTTP request method"},
            "request_headers": _HEADERS,
            "resource": _RESOURCE,
        },
        "required": ["method", "request_headers", "resource"],
        "additionalProperties": False,
    },
    "cors_evaluate": {
        "type": "object",
        "properties": dict(_CORS_REQUEST_PROPERTIES),
        "required": ["method", "url", "response", "is_preflight"],
        "additionalProperties": False,
    },
    "cors_simulate_fetch": {
        "type": "object",
        "properties": dict(
            _CORS_REQUEST_PROPERTIES,
            mode={
                "type": "string",
                "enum": ["cors", "no-cors", "same-origin"],
                "description": "fetch mode; defaults to cors",
            },
            redirects={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string"},
                        "status": {"type": "integer", "enum": [301, 302, 303, 307, 308]},
                        "headers": _HEADERS,
                    },
                    "required": ["url", "status"],
                    "additionalProperties": False,
                },
            },
        ),
        "required": ["method", "url", "response"],
        "additionalProperties": False,
    },
    "vary_match": {
        "type": "object",
        "properties": {
            "cached": _CACHED_ENTRY,
            "incoming": {
                "type": "object",
                "properties": {"request_headers": _HEADERS},
                "additionalProperties": False,
            },
        },
        "required": ["cached", "incoming"],
        "additionalProperties": False,
    },
}


def build_registry():
    """Build the registry for this build: one Tool per declared handler."""
    available = handlers()
    registry = Registry()
    for name in sorted(available):
        registry.register(
            Tool(
                name=name,
                description=TOOL_DESCRIPTIONS[name],
                input_schema=INPUT_SCHEMAS[name],
                handler=available[name],
            )
        )
    return registry
