"""End-to-end stdio: a real client starts the server and calls every tool.

``tests/test_stdio_process.py`` proves the process starts and lists tools. This
test goes further: it drives the whole client path over real pipes -- handshake,
``tools/list``, one successful ``tools/call`` per tool, and the unknown-tool
error -- and validates each result against the ``outputSchema`` the server
itself published in the same session.

The interpreter is ``sys.executable`` on purpose: the suite is run under both
Python 3.8 and 3.12, so this test is exercised on both without hard-coding a
launcher that may not exist on the machine.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

from http_semantics_mcp import canonical  # noqa: E402

TOOL_NAMES = [
    "cache_evaluate",
    "conditional_evaluate",
    "cors_evaluate",
    "cors_simulate_fetch",
    "vary_match",
]

# Minimal but complete arguments, one per tool. Kept here (rather than imported
# from another test module) so this file is a self-contained client.
MINIMAL_ARGUMENTS = {
    "cache_evaluate": {
        "now": "2026-01-01T00:00:00Z",
        "response_headers": {"Cache-Control": "max-age=60"},
        "stored": {"stored_at": "2026-01-01T00:00:00Z"},
    },
    "conditional_evaluate": {
        "method": "GET",
        "request_headers": {},
        "resource": {"etag": '"abc123"', "last_modified": "2026-01-01T00:00:00Z"},
    },
    "cors_evaluate": {
        "method": "GET",
        "url": "https://api.example.com/a",
        "origin": "https://app.example.com",
        "response": {"status": 200, "headers": {"Access-Control-Allow-Origin": "https://app.example.com"}},
        "is_preflight": False,
    },
    "cors_simulate_fetch": {
        "method": "GET",
        "url": "https://api.example.com/a",
        "origin": "https://app.example.com",
        "response": {"status": 200, "headers": {"Access-Control-Allow-Origin": "https://app.example.com"}},
        "mode": "cors",
        "redirects": [],
    },
    "vary_match": {
        "cached": {"vary": "Accept", "request_headers_at_store": {"Accept": "text/html"}},
        "incoming": {"request_headers": {"Accept": "text/html"}},
    },
}


def _env():
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = SRC + ((os.pathsep + existing) if existing else "")
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _requests():
    stream = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
    ]
    for offset, name in enumerate(TOOL_NAMES):
        stream.append(
            {
                "jsonrpc": "2.0",
                "id": 3 + offset,
                "method": "tools/call",
                "params": {"name": name, "arguments": MINIMAL_ARGUMENTS[name]},
            }
        )
    stream.append(
        {
            "jsonrpc": "2.0",
            "id": 3 + len(TOOL_NAMES),
            "method": "tools/call",
            "params": {"name": "does_not_exist", "arguments": {}},
        }
    )
    return stream


def _run(requests):
    payload = b"".join(
        json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n" for request in requests
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "http_semantics_mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=_env(),
    )
    stdout, stderr = process.communicate(payload, timeout=120)
    assert process.returncode == 0, stderr.decode("utf-8", "replace")
    assert b"\r" not in stdout
    return [json.loads(line.decode("utf-8")) for line in stdout.split(b"\n") if line]


def test_a_client_can_list_and_call_every_tool_then_hits_the_unknown_tool_error():
    requests = _requests()
    messages = _run(requests)

    expected_ids = [request["id"] for request in requests if "id" in request]
    assert [message["id"] for message in messages] == expected_ids

    init = messages[0]["result"]
    assert init["serverInfo"]["name"] == "http-semantics-mcp"

    tools = messages[1]["result"]["tools"]
    assert [tool["name"] for tool in tools] == TOOL_NAMES
    schemas = {tool["name"]: tool["outputSchema"] for tool in tools}

    for offset, name in enumerate(TOOL_NAMES):
        result = messages[2 + offset]["result"]
        assert result["isError"] is False, name
        assert len(result["content"]) == 1 and result["content"][0]["type"] == "text"
        payload = json.loads(result["content"][0]["text"])
        # The server's own published schema is the expected key set.
        assert set(payload) == set(schemas[name]["properties"]), name
        # Publishing an outputSchema obliges the server to also send
        # structuredContent (specification: "Servers MUST provide structured
        # results that conform to this schema").
        structured = result["structuredContent"]
        assert set(structured) == set(schemas[name]["properties"]), name
        assert set(schemas[name]["required"]) <= set(structured), name
        # ... and the two faces must carry the same value, byte for byte.
        assert canonical.dumps(structured) == result["content"][0]["text"], name
        assert structured == payload, name

    unknown = messages[2 + len(TOOL_NAMES)]
    assert "error" in unknown, unknown
    assert unknown["error"]["code"] == -32602


def test_an_error_result_also_carries_structured_content():
    """``isError: true`` keeps the same envelope; the payload is the error object."""
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "vary_match", "arguments": {}},
        },
    ]
    messages = _run(requests)
    result = messages[1]["result"]
    assert result["isError"] is True
    assert set(result["structuredContent"]) == {"error"}
    assert result["structuredContent"]["error"]["code"] == "INVALID_INPUT"
    assert canonical.dumps(result["structuredContent"]) == result["content"][0]["text"]


def test_the_same_call_returns_the_same_bytes_over_the_wire():
    """Determinism survives the process boundary, not just the import."""
    name = "cache_evaluate"
    requests = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": name, "arguments": MINIMAL_ARGUMENTS[name]}},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": name, "arguments": MINIMAL_ARGUMENTS[name]}},
    ]
    messages = _run(requests)
    assert messages[1]["result"] == messages[2]["result"]
