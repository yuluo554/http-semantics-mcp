"""Registry contract: ordering, uniqueness, descriptor isolation."""

import pytest

from http_semantics_mcp.registry import Registry, Tool, build_registry


def _tool(name, description="does a thing"):
    return Tool(
        name=name,
        description=description,
        input_schema={"type": "object", "additionalProperties": False},
        handler=lambda arguments: {"ok": True},
    )


def test_m0_registry_is_empty_and_that_is_explicit():
    registry = build_registry()
    assert len(registry) == 0
    assert registry.descriptors() == []
    assert registry.names() == []


def test_names_are_sorted_regardless_of_registration_order():
    registry = Registry([_tool("vary_match"), _tool("cache_evaluate"), _tool("cors_evaluate")])
    assert registry.names() == ["cache_evaluate", "cors_evaluate", "vary_match"]
    assert [descriptor["name"] for descriptor in registry.descriptors()] == registry.names()


def test_duplicate_names_are_rejected():
    registry = Registry([_tool("cors_evaluate")])
    with pytest.raises(ValueError):
        registry.register(_tool("cors_evaluate"))


def test_non_tool_registration_is_rejected():
    with pytest.raises(TypeError):
        Registry().register({"name": "x"})


def test_descriptor_contains_mcp_required_keys():
    descriptor = Registry([_tool("cors_evaluate", "evaluates CORS")]).descriptors()[0]
    assert descriptor == {
        "name": "cors_evaluate",
        "description": "evaluates CORS",
        "inputSchema": {"type": "object", "additionalProperties": False},
    }


def test_descriptor_copies_are_isolated():
    """A client mutating a descriptor must not corrupt the registry."""
    registry = Registry([_tool("cors_evaluate")])
    first = registry.descriptors()[0]
    first["name"] = "mutated"
    first["inputSchema"]["type"] = "mutated"

    second = registry.descriptors()[0]
    assert second["name"] == "cors_evaluate"
    assert second["inputSchema"]["type"] == "object"


def test_output_schema_is_published_when_present():
    tool = Tool(
        name="cache_evaluate",
        description="cache",
        input_schema={"type": "object"},
        handler=lambda arguments: {},
        output_schema={"type": "object", "properties": {}},
    )
    descriptor = Registry([tool]).descriptors()[0]
    assert descriptor["outputSchema"] == {"type": "object", "properties": {}}


def test_get_returns_none_for_unknown_tool():
    assert Registry().get("missing") is None


def test_handlers_are_not_serialised_into_descriptors():
    descriptor = Registry([_tool("vary_match")]).descriptors()[0]
    for value in descriptor.values():
        assert not callable(value)
