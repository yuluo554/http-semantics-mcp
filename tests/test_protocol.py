"""Protocol contract tests: lifecycle, dispatch, error codes."""

import json

import pytest

from http_semantics_mcp import __version__, errors, protocol
from http_semantics_mcp.registry import Tool


def _session():
    return protocol.Session()


def _request(method, params=None, request_id=1):
    message = {"jsonrpc": "2.0", "id": request_id, "method": method}
    if params is not None:
        message["params"] = params
    return message


def _initialize(session):
    responses = session.handle(_request("initialize", {"protocolVersion": "2025-06-18"}))
    assert len(responses) == 1
    return responses[0]["result"]


def test_initialize_returns_protocol_version_capabilities_and_server_info():
    result = _initialize(_session())

    assert set(result) == {"protocolVersion", "capabilities", "serverInfo"}
    assert result["protocolVersion"] == protocol.DEFAULT_PROTOCOL_VERSION
    assert result["serverInfo"] == {"name": "http-semantics-mcp", "version": __version__}
    assert "tools" in result["capabilities"]


def test_capabilities_declare_only_tools():
    """Anything not declared must answer -32601; advertising more would lie."""
    assert set(_initialize(_session())["capabilities"]) == {"tools"}


@pytest.mark.parametrize("requested", ["2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05"])
def test_supported_versions_are_echoed(requested):
    session = _session()
    result = session.handle(_request("initialize", {"protocolVersion": requested}))[0]["result"]
    assert result["protocolVersion"] == requested


def test_every_declared_version_is_echoed():
    """Driven off the constant, so adding a version cannot quietly skip a test."""
    assert protocol.SUPPORTED_PROTOCOL_VERSIONS
    for requested in protocol.SUPPORTED_PROTOCOL_VERSIONS:
        session = _session()
        result = session.handle(_request("initialize", {"protocolVersion": requested}))[0]["result"]
        assert result["protocolVersion"] == requested, requested


def test_the_default_version_is_one_of_the_supported_ones():
    assert protocol.DEFAULT_PROTOCOL_VERSION in protocol.SUPPORTED_PROTOCOL_VERSIONS


def test_unknown_version_falls_back_to_default():
    session = _session()
    result = session.handle(_request("initialize", {"protocolVersion": "1999-01-01"}))[0]["result"]
    assert result["protocolVersion"] == protocol.DEFAULT_PROTOCOL_VERSION


def test_missing_version_falls_back_to_default():
    session = _session()
    result = session.handle(_request("initialize", {}))[0]["result"]
    assert result["protocolVersion"] == protocol.DEFAULT_PROTOCOL_VERSION


def test_notifications_produce_no_response():
    session = _session()
    _initialize(session)

    assert session.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) == []
    assert session.handle({"jsonrpc": "2.0", "method": "notifications/cancelled", "params": {"requestId": 1}}) == []


def test_ping_works_before_initialize():
    """ping is explicitly pre-init safe; clients use it as a liveness probe."""
    assert _session().handle(_request("ping")) == [{"jsonrpc": "2.0", "id": 1, "result": {}}]


def test_request_before_initialize_is_rejected():
    responses = _session().handle(_request("tools/list"))
    assert responses[0]["error"]["code"] == errors.SERVER_NOT_INITIALIZED


def test_tools_list_reports_the_registered_tools_in_ascii_order():
    session = _session()
    _initialize(session)

    result = session.handle(_request("tools/list"))[0]["result"]
    names = [tool["name"] for tool in result["tools"]]
    assert names == sorted(names)
    assert names == [
        "cache_evaluate",
        "conditional_evaluate",
        "cors_evaluate",
        "cors_simulate_fetch",
        "vary_match",
    ]
    for tool in result["tools"]:
        # M5 publishes the output schema alongside the input one (decision D50).
        assert set(tool) == {"name", "description", "inputSchema", "outputSchema"}
        assert tool["outputSchema"]["properties"], tool["name"]


def test_tools_call_returns_a_judgement_result_not_a_jsonrpc_error():
    session = _session()
    _initialize(session)

    response = session.handle(
        _request(
            "tools/call",
            {
                "name": "cors_evaluate",
                "arguments": {
                    "method": "GET",
                    "url": "https://api.example.com/v1",
                    "origin": "https://app.example.com",
                    "response": {
                        "status": 200,
                        "headers": {"Access-Control-Allow-Origin": "https://app.example.com"},
                    },
                    "is_preflight": False,
                },
            },
        )
    )[0]
    assert "result" in response, response
    result = response["result"]
    assert result["isError"] is False
    payload = json.loads(result["content"][0]["text"])
    assert payload["decision"] == "allow"


def test_tools_call_bad_arguments_are_a_tool_error_not_a_crash():
    session = _session()
    _initialize(session)

    response = session.handle(
        _request(
            "tools/call",
            {"name": "cors_evaluate", "arguments": {"method": "BREW"}},
        )
    )[0]
    assert "result" in response, response
    assert response["result"]["isError"] is True
    assert json.loads(response["result"]["content"][0]["text"])["error"]["code"] == "UNSUPPORTED_METHOD"


def test_unknown_tool_is_invalid_params():
    session = _session()
    _initialize(session)

    response = session.handle(_request("tools/call", {"name": "nope", "arguments": {}}))[0]
    assert response["error"]["code"] == errors.INVALID_PARAMS


def test_tools_call_requires_a_name():
    session = _session()
    _initialize(session)

    response = session.handle(_request("tools/call", {"arguments": {}}))[0]
    assert response["error"]["code"] == errors.INVALID_PARAMS


def test_tools_call_rejects_non_object_arguments():
    session = _session()
    _initialize(session)

    response = session.handle(_request("tools/call", {"name": "nope", "arguments": []}))[0]
    assert response["error"]["code"] == errors.INVALID_PARAMS


def test_unknown_method_is_method_not_found():
    session = _session()
    _initialize(session)

    response = session.handle(_request("resources/list"))[0]
    assert response["error"]["code"] == errors.METHOD_NOT_FOUND


def test_unknown_method_notification_is_silently_dropped():
    session = _session()
    _initialize(session)

    assert session.handle({"jsonrpc": "2.0", "method": "no/such/method"}) == []


def test_batch_request_is_rejected():
    response = _session().handle([_request("ping")])[0]
    assert response["error"]["code"] == errors.INVALID_REQUEST


@pytest.mark.parametrize("message", ["not an object", 42, None])
def test_non_object_message_is_invalid_request(message):
    response = _session().handle(message)[0]
    assert response["error"]["code"] == errors.INVALID_REQUEST


def test_wrong_jsonrpc_version_is_rejected():
    response = _session().handle({"jsonrpc": "1.0", "id": 1, "method": "ping"})[0]
    assert response["error"]["code"] == errors.INVALID_REQUEST


def test_params_must_be_an_object():
    session = _session()
    _initialize(session)

    response = session.handle({"jsonrpc": "2.0", "id": 9, "method": "ping", "params": []})[0]
    assert response["error"]["code"] == errors.INVALID_REQUEST


def test_handler_crash_becomes_internal_error_and_session_survives():
    """A bug in one handler must not kill the process or the session."""

    def boom(arguments):
        raise RuntimeError("kaboom")

    registry = protocol.build_registry()
    registry.register(
        Tool(
            name="boom",
            description="raises",
            input_schema={"type": "object"},
            handler=boom,
        )
    )
    session = protocol.Session(registry=registry)
    _initialize(session)

    response = session.handle(_request("tools/call", {"name": "boom", "arguments": {}}))[0]
    assert response["error"]["code"] == errors.INTERNAL_ERROR
    assert "kaboom" not in str(response)

    # the session is still usable afterwards
    assert session.handle(_request("ping"))[0]["result"] == {}


def test_response_envelope_shape():
    session = _session()
    response = session.handle(_request("initialize", {}))[0]
    assert set(response) == {"jsonrpc", "id", "result"}
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
