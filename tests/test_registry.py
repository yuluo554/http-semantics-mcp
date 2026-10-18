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


def test_build_registry_declares_the_shipped_tools():
    registry = build_registry()
    assert registry.names() == [
        "cache_evaluate",
        "conditional_evaluate",
        "cors_evaluate",
        "cors_simulate_fetch",
        "vary_match",
    ]
    assert [descriptor["name"] for descriptor in registry.descriptors()] == registry.names()


def test_every_shipped_tool_has_an_object_schema_and_a_handler():
    registry = build_registry()
    for name in registry.names():
        tool = registry.get(name)
        assert tool.description.strip(), name
        assert tool.input_schema["type"] == "object", name
        assert tool.input_schema["additionalProperties"] is False, name
        assert callable(tool.handler), name


def test_declared_required_fields_are_the_ones_the_handler_rejects():
    """A schema that promises less than the handler enforces is a lie."""
    registry = build_registry()
    for name in registry.names():
        tool = registry.get(name)
        required = set(tool.input_schema["required"])
        complete = _minimal_arguments(name)
        assert set(complete) >= required, name
        assert tool.handler(complete)["isError"] is False, name
        for field in sorted(required):
            incomplete = {key: value for key, value in complete.items() if key != field}
            assert tool.handler(incomplete)["isError"] is True, name + " ignores " + field


def _minimal_arguments(name):
    common = {
        "method": "GET",
        "url": "https://api.example.com/a",
        "origin": "https://app.example.com",
        "response": {"status": 200, "headers": {"Access-Control-Allow-Origin": "https://app.example.com"}},
    }
    if name == "cache_evaluate":
        return {
            "now": "2026-01-01T00:00:00Z",
            "response_headers": {"Cache-Control": "max-age=60"},
            "stored": {"stored_at": "2026-01-01T00:00:00Z"},
        }
    if name == "conditional_evaluate":
        return {
            "method": "GET",
            "request_headers": {},
            "resource": {"etag": '"abc123"', "last_modified": "2026-01-01T00:00:00Z"},
        }
    if name == "vary_match":
        return {
            "cached": {"vary": "Accept", "request_headers_at_store": {"Accept": "text/html"}},
            "incoming": {"request_headers": {"Accept": "text/html"}},
        }
    if name == "cors_evaluate":
        return dict(common, is_preflight=False)
    if name == "cors_simulate_fetch":
        return dict(common, mode="cors", redirects=[])
    raise AssertionError("no minimal arguments declared for " + name)


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
