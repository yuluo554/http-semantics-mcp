"""Real subprocess, real bytes.

The in-process transport tests cannot see a launch failure, a missing
``__main__``, or a swallowed traceback. This test starts the actual server the
way a client would.
"""

import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")

REQUESTS = [
    {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}},
    {"jsonrpc": "2.0", "method": "notifications/initialized"},
    {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
]


def _env():
    environment = dict(os.environ)
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = SRC + ((os.pathsep + existing) if existing else "")
    environment["PYTHONIOENCODING"] = "utf-8"
    return environment


def _run_server(requests, timeout=60):
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
    stdout, stderr = process.communicate(payload, timeout=timeout)
    return process.returncode, stdout, stderr


def test_server_starts_and_answers_the_handshake():
    code, stdout, stderr = _run_server(REQUESTS)
    assert code == 0, stderr.decode("utf-8", "replace")

    lines = [line for line in stdout.split(b"\n") if line]
    assert len(lines) == 2  # notification produces no line

    messages = [json.loads(line.decode("utf-8")) for line in lines]
    assert [message["id"] for message in messages] == [1, 2]

    init = messages[0]["result"]
    assert init["protocolVersion"] == "2025-06-18"
    assert init["serverInfo"]["name"] == "http-semantics-mcp"
    assert messages[1]["result"] == {"tools": []}


def test_stdout_carries_protocol_only_no_banner_no_carriage_return():
    _, stdout, _ = _run_server(REQUESTS)
    assert b"\r" not in stdout
    for line in [line for line in stdout.split(b"\n") if line]:
        json.loads(line.decode("utf-8"))


def test_version_flag_via_process():
    process = subprocess.run(
        [sys.executable, "-m", "http_semantics_mcp", "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=_env(),
        timeout=60,
    )
    assert process.returncode == 0
    assert process.stdout.decode("utf-8").strip()
    assert process.stdout.count(b"\n") == 1


def test_selftest_via_process():
    process = subprocess.run(
        [sys.executable, "-m", "http_semantics_mcp", "--selftest"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=_env(),
        timeout=60,
    )
    output = process.stdout.decode("utf-8")
    assert process.returncode == 0, output + process.stderr.decode("utf-8", "replace")
    assert "summary:" in output
    assert "FAIL" not in output


def test_eof_terminates_the_process_cleanly():
    code, stdout, _ = _run_server([])
    assert code == 0
    assert stdout == b""


def test_smoke_script_runs():
    """The CI step and the release check both call this script."""
    process = subprocess.run(
        [sys.executable, os.path.join(ROOT, "tools", "smoke_stdio.py")],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=ROOT,
        env=_env(),
        timeout=120,
    )
    assert process.returncode == 0, process.stdout.decode("utf-8", "replace") + process.stderr.decode(
        "utf-8", "replace"
    )
    assert "ok:" in process.stdout.decode("utf-8")
