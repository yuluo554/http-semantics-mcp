"""Mutation verification: break the behaviour, the gate must go red.

Run with: py tools/mutate_check.py

Each case replaces exactly one marker, runs one command, and asserts the
command failed. Three assertions guard against the classic silent no-op:
marker exists, file bytes changed, file bytes restored exactly.
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV = dict(os.environ, PYTHONPATH=os.path.join(ROOT, "src"), PYTHONDONTWRITEBYTECODE="1")

NEWLINE = 'b"\\n"'

CASES = [
    (
        "canonical framing loses its newline",
        os.path.join("src", "http_semantics_mcp", "canonical.py"),
        'return dumps(value).encode("utf-8") + ' + NEWLINE,
        'return dumps(value).encode("utf-8")',
        ["-m", "pytest", "-q", "tests/test_canonical.py"],
    ),
    (
        "registry stops sorting tool names",
        os.path.join("src", "http_semantics_mcp", "registry.py"),
        "return sorted(self._tools)",
        "return list(self._tools)",
        ["-m", "pytest", "-q", "tests/test_registry.py"],
    ),
    (
        "lifecycle gate disappears",
        os.path.join("src", "http_semantics_mcp", "protocol.py"),
        "if not is_notification and not self.initialized and method not in _PRE_INIT_METHODS:",
        "if False:",
        ["-m", "pytest", "-q", "tests/test_protocol.py"],
    ),
    (
        "utf8 guard refuses to reconfigure",
        os.path.join("src", "http_semantics_mcp", "_utf8.py"),
        'if normalise_encoding_name(getattr(stream, "encoding", None)) == "utf8":',
        "if True:",
        ["-m", "pytest", "-q", "tests/test_utf8_guard.py"],
    ),
    (
        "transport emits a carriage return",
        os.path.join("src", "http_semantics_mcp", "server.py"),
        "_write(stream, canonical.encode_message(response))",
        '_write(stream, canonical.dumps(response).encode("utf-8") + b"\\r\\n")',
        ["-m", "pytest", "-q", "tests/test_server_transport.py"],
    ),
    (
        "version parity check disabled",
        os.path.join("src", "http_semantics_mcp", "selfcheck.py"),
        "if declared != __version__:",
        "if False:",
        ["-m", "pytest", "-q", "tests/test_entry_point.py"],
    ),
    (
        "judgement layer imports the clock",
        os.path.join("src", "http_semantics_mcp", "judgement", "__init__.py"),
        "__all__ = []",
        "import time\n\n__all__ = []",
        [os.path.join("tools", "run_gates.py")],
    ),
    (
        "a second json.dumps appears",
        os.path.join("src", "http_semantics_mcp", "server.py"),
        "def write_response(stream, response):\n    \"\"\"Write one response object as a framed line.\"\"\"\n    _write(stream, canonical.encode_message(response))",
        "def write_response(stream, response):\n    \"\"\"Write one response object as a framed line.\"\"\"\n    import json\n    _write(stream, json.dumps(response).encode(\"utf-8\") + b\"\\n\")",
        [os.path.join("tools", "run_gates.py")],
    ),
    (
        "the oracle imports the implementation",
        os.path.join("tools", "golden_oracle", "engine.py"),
        "import json\nimport os\n",
        "import json\nimport os\n\nimport http_semantics_mcp\n",
        [os.path.join("tools", "run_gates.py")],
    ),
    (
        "a golden case gains an observed field",
        os.path.join("data", "golden", "vary_match", "vary-001-hit-single.json"),
        '  "case_id": "vary-001-hit-single",',
        '  "case_id": "vary-001-hit-single",\n  "observed_match": "hit",',
        [os.path.join("tools", "run_gates.py")],
    ),
    (
        "the package spells a rule code as a literal",
        os.path.join("src", "http_semantics_mcp", "judgement", "__init__.py"),
        "__all__ = []",
        '__all__ = []\n\nFIRST_CODE = "CACHE_NO_STORE"',
        [os.path.join("tools", "run_gates.py")],
    ),
    (
        "the code catalog drifts from the table",
        os.path.join("src", "http_semantics_mcp", "references", "codes.json"),
        '"CACHE_NO_STORE":{"meaning":',
        '"CACHE_NO_STORE":{"edited_by_hand":true,"meaning":',
        [os.path.join("tools", "gen_codes.py"), "--check"],
    ),
    (
        "a golden expectation drifts from the oracle",
        os.path.join("data", "golden", "vary_match", "vary-001-hit-single.json"),
        '"match": "hit"',
        '"match": "miss"',
        [os.path.join("tools", "gen_golden.py"), "--check"],
    ),
    (
        "the table renames a code behind the catalog's back",
        os.path.join("data", "README.md"),
        "| `CORS_` | `CORS_NULL_ORIGIN` |",
        "| `CORS_` | `CORS_NULL_ORIGIN_GONE` |",
        [os.path.join("tools", "gen_codes.py"), "--check"],
    ),
    (
        "the CORS check lets a wildcard cover authorization",
        os.path.join("src", "http_semantics_mcp", "judgement", "cors.py"),
        '    if name == "authorization":\n        return False',
        '    if name == "authorization":\n        return "*" in declared',
        ["-m", "pytest", "-q", "tests/test_cors_golden.py"],
    ),
    (
        "the CORS check forgets that a non-simple request needs a preflight",
        os.path.join("src", "http_semantics_mcp", "judgement", "cors.py"),
        "    return method not in SAFELISTED_METHODS or bool(unsafe_request_headers(headers))",
        "    return False",
        ["-m", "pytest", "-q", "tests/test_cors_golden.py"],
    ),
    (
        "redirect events are emitted in the wrong order",
        os.path.join("src", "http_semantics_mcp", "judgement", "fetch_sim.py"),
        '                events.append("origin_set_to_null")\n'
        '                if credentials == "include":\n'
        '                    events.append("credentials_dropped")',
        '                if credentials == "include":\n'
        '                    events.append("credentials_dropped")\n'
        '                events.append("origin_set_to_null")',
        ["-m", "pytest", "-q", "tests/test_cors_golden.py"],
    ),
    (
        "header values stop having their optional whitespace trimmed",
        os.path.join("src", "http_semantics_mcp", "judgement", "normalise.py"),
        "    return values[0].strip(OWS)",
        "    return values[0]",
        ["-m", "pytest", "-q", "tests/test_cors_golden.py"],
    ),
    (
        "a caller mistake stops being reported as a tool error",
        os.path.join("src", "http_semantics_mcp", "toolface.py"),
        "            return render(error.payload(), is_error=True)",
        "            return render(error.payload(), is_error=False)",
        ["-m", "pytest", "-q", "tests/test_cors_golden.py"],
    ),
    (
        "the registry stops declaring the implemented tools",
        os.path.join("src", "http_semantics_mcp", "registry.py"),
        "    for name in sorted(available):",
        "    for name in []:",
        ["-m", "pytest", "-q", "tests/test_registry.py"],
    ),
]


def _run(command):
    return subprocess.run(
        [sys.executable] + command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=ENV,
    )


def _mutate(description, relative, old, new, command):
    path = os.path.join(ROOT, relative)
    with open(path, "rb") as handle:
        original = handle.read()

    text = original.decode("utf-8")
    occurrences = text.count(old)
    if occurrences != 1:
        return False, "marker occurs " + str(occurrences) + " times (expected 1)"

    mutated = text.replace(old, new)
    if mutated == text.encode("utf-8").decode("utf-8"):
        return False, "replacement produced no change"

    try:
        with open(path, "wb") as handle:
            handle.write(mutated.encode("utf-8"))
        with open(path, "rb") as handle:
            if handle.read() == original:
                return False, "file did not change on disk"

        result = _run(command)
        if result.returncode == 0:
            return False, "still green -- the gate does not test this behaviour"
        return True, "red (exit " + str(result.returncode) + ")"
    finally:
        with open(path, "wb") as handle:
            handle.write(original)
        with open(path, "rb") as handle:
            if handle.read() != original:
                raise RuntimeError("restore failed for " + relative)


def main():
    failures = 0
    for description, relative, old, new, command in CASES:
        ok, detail = _mutate(description, relative, old, new, command)
        if not ok:
            failures += 1
        sys.stdout.write(("PASS  " if ok else "FAIL  ") + description + ": " + detail + "\n")

    sys.stdout.write(
        "summary: {0} mutation(s), {1} gate(s) failed to notice\n".format(len(CASES), failures)
    )
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
