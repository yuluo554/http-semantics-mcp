"""Real-subprocess stdio handshake smoke test.

Purpose: prove the server works as a *process*, not only as imported
functions. This is the shape CI and the release check use.

Usage::

    py tools/smoke_stdio.py                 # run against this checkout
    py tools/smoke_stdio.py --python 3.8    # pick a launcher argument

Exit codes: 0 pass, 1 protocol failure, 2 usage / launch failure.

The script asserts on the *bytes* the server wrote:

* every stdout line parses as JSON
* no line contains ``\\r``
* the response count matches the request count
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "ping"},
    {"jsonrpc": "2.0", "id": 3, "method": "tools/list"},
    {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "does_not_exist", "arguments": {}}},
    {"jsonrpc": "2.0", "id": 5, "method": "no/such/method"},
]

EXPECTED_IDS = [1, 2, 3, 4, 5]


def _payload():
    stream = b""
    for request in REQUESTS:
        stream += json.dumps(request, ensure_ascii=False).encode("utf-8") + b"\n"
    return stream


def _python_command(python):
    if python:
        return [python]
    return [sys.executable]


def run_smoke(python=None, verbose=False):
    command = _python_command(python) + ["-m", "http_semantics_mcp"]
    environment = dict(os.environ)
    environment["PYTHONPATH"] = os.pathsep.join(
        [os.path.join(ROOT, "src")] + ([environment["PYTHONPATH"]] if environment.get("PYTHONPATH") else [])
    )
    environment["PYTHONIOENCODING"] = "utf-8"

    handle = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=environment,
    )
    try:
        stdout, stderr = handle.communicate(_payload(), timeout=60)
    except subprocess.TimeoutExpired:
        handle.kill()
        handle.communicate()
        return 1, "server did not answer within 60s", b""

    if handle.returncode != 0:
        return 1, "server exited with " + str(handle.returncode) + ": " + stderr.decode("utf-8", "replace"), stdout

    lines = stdout.split(b"\n")
    if lines and lines[-1] == b"":
        lines = lines[:-1]

    messages = []
    for index, line in enumerate(lines):
        if b"\r" in line:
            return 1, "stdout line " + str(index + 1) + " contains a carriage return", stdout
        try:
            messages.append(json.loads(line.decode("utf-8")))
        except (UnicodeDecodeError, ValueError) as exc:
            return 1, "stdout line " + str(index + 1) + " is not JSON: " + str(exc), stdout

    ids = [message.get("id") for message in messages]
    if ids != EXPECTED_IDS:
        return 1, "response ids " + repr(ids) + " != expected " + repr(EXPECTED_IDS), stdout

    if messages[0].get("result", {}).get("serverInfo", {}).get("name") != "http-semantics-mcp":
        return 1, "initialize did not report this server", stdout
    if messages[1] != {"jsonrpc": "2.0", "id": 2, "result": {}}:
        return 1, "ping response is not the empty result", stdout
    tools = messages[2].get("result", {}).get("tools")
    if not isinstance(tools, list):
        return 1, "tools/list did not return an array", stdout
    if messages[3].get("error", {}).get("code") != -32602:
        return 1, "unknown tool did not answer -32602", stdout
    if messages[4].get("error", {}).get("code") != -32601:
        return 1, "unknown method did not answer -32601", stdout

    detail = "ok: {0} responses, {1} tool(s) listed, {2} stdout bytes".format(len(messages), len(tools), len(stdout))
    if verbose:
        detail += "\n" + stdout.decode("utf-8", "replace")
    return 0, detail, stdout


def main(argv=None):
    parser = argparse.ArgumentParser(description="Smoke-test the MCP stdio server in a real subprocess.")
    parser.add_argument("--python", default=None, help="interpreter to launch (default: current)")
    parser.add_argument("--verbose", action="store_true", help="print the raw stdout stream")
    args = parser.parse_args(argv)

    try:
        code, detail, _ = run_smoke(args.python, args.verbose)
    except OSError as exc:
        sys.stderr.write("launch failed: " + str(exc) + "\n")
        return 2
    sys.stdout.write(detail + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
