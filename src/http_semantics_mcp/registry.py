"""Tool registry: the single place where tools are declared.

M0 ships **no tools**. ``tools/list`` therefore returns an empty list, and the
README says so. That is intentional: a placeholder descriptor would make an
MCP client believe a capability exists that does not.

Each tool descriptor is a plain dict with the exact keys the MCP schema
requires (``name``, ``description``, ``inputSchema``) plus an optional
``outputSchema``. The handler is stored separately so that ``tools/list`` can
never accidentally serialise a callable.
"""

import copy

__all__ = ["Tool", "Registry", "build_registry"]


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


def build_registry():
    """Build the registry for this build.

    M2-M4 register ``cors_evaluate``, ``cors_simulate_fetch``,
    ``cache_evaluate``, ``conditional_evaluate`` and ``vary_match`` here.
    """
    return Registry()
