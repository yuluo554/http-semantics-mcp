"""Tool registry: the single place where tools are declared.

M2 registered the two CORS tools, M3 added ``cache_evaluate`` and M4 the
remaining two. M5 moves the client-visible contract out of this module: each
tool is now described by one JSON Schema file under
``src/http_semantics_mcp/schemas/tools/<tool>.json`` (decision D50, route A).
That file is the **only editable source** for the descriptor -- name,
description, ``inputSchema`` and ``outputSchema`` -- and the top-level
``schemas/tools/`` copy is a byte-identical mirror written by
``tools/gen_schemas.py``.

The registry reads the package JSON here, one file per registered handler, and
stores the handler separately so that ``tools/list`` can never accidentally
serialise a callable.
"""

import copy
import json
import os

from .toolface import handlers

__all__ = ["Tool", "Registry", "build_registry", "descriptor_names"]

# The in-package schema directory is the source of truth (decision D24). A
# plain path relative to this module works for a source checkout and for an
# installed distribution alike: ``pip install`` unpacks package data onto disk,
# so ``__file__`` is a real path, and the distribution never ships as a zip.
_SCHEMA_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schemas", "tools")

REQUIRED_DESCRIPTOR_KEYS = ("name", "description", "inputSchema", "outputSchema")

_DESCRIPTOR_CACHE = {}


class DescriptorError(Exception):
    """A tool descriptor is missing or does not carry the MCP contract."""


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


# -- descriptors ----------------------------------------------------------


def descriptor_names():
    """Return the tool names carried by the in-package schema directory."""
    return sorted(
        name[: -len(".json")]
        for name in os.listdir(_SCHEMA_DIRECTORY)
        if name.endswith(".json")
    )


def _read_descriptor(name):
    """Load and validate one tool descriptor from the package schema file.

    A missing or malformed descriptor is a hard error rather than an empty
    contract: a client asking ``tools/list`` must never be told a tool exists
    without the schema that defines it, nor silently get a tool with no schema.
    """
    cached = _DESCRIPTOR_CACHE.get(name)
    if cached is not None:
        return cached

    path = os.path.join(_SCHEMA_DIRECTORY, name + ".json")
    if not os.path.isfile(path):
        raise DescriptorError("missing descriptor for " + name + ": " + path)
    with open(path, "r", encoding="utf-8") as handle:
        payload = json.loads(handle.read())

    if not isinstance(payload, dict):
        raise DescriptorError("descriptor for " + name + " must be a JSON object")
    missing = [key for key in REQUIRED_DESCRIPTOR_KEYS if key not in payload]
    if missing:
        raise DescriptorError("descriptor for " + name + " lacks " + ", ".join(missing))
    if payload["name"] != name:
        raise DescriptorError("descriptor name " + str(payload["name"]) + " != " + name)
    if not isinstance(payload["description"], str) or not payload["description"].strip():
        raise DescriptorError("descriptor for " + name + " has no description")
    for key in ("inputSchema", "outputSchema"):
        if not isinstance(payload[key], dict):
            raise DescriptorError("descriptor for " + name + " has a non-object " + key)

    _DESCRIPTOR_CACHE[name] = payload
    return payload


def build_registry():
    """Build the registry for this build: one Tool per declared handler."""
    available = handlers()
    registry = Registry()
    for name in sorted(available):
        descriptor = _read_descriptor(name)
        registry.register(
            Tool(
                name=name,
                description=descriptor["description"],
                input_schema=descriptor["inputSchema"],
                output_schema=descriptor["outputSchema"],
                handler=available[name],
            )
        )
    return registry
