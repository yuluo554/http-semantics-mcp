# tests

Run the suite from the repository root:

```bash
python -m pip install -e ".[dev]"
python -m pytest
```

| File | What it pins |
| --- | --- |
| `test_protocol.py` | initialize / ping / tools-list / tools-call, lifecycle gating, every JSON-RPC error code |
| `test_server_transport.py` | newline framing, CRLF tolerance, UTF-8 errors, oversized-line recovery, no `\r` in output |
| `test_stdio_process.py` | the server as a real subprocess: launch, handshake, `--version`, `--selftest`, smoke script |
| `test_canonical.py` | single serialisation point: key order, separators, no escaping, byte-identical reruns, NaN rejection |
| `test_entry_point.py` | exit-code contract (0 / 2), no judgement subcommand, `--help` surface |
| `test_utf8_guard.py` | cp1252 stream reproduction — the guard is proven against a stream that really is not UTF-8 |
| `test_registry.py` | name ordering, duplicate rejection, descriptor isolation, no callables leaking into `tools/list` |
| `test_gates.py` | the three static gates, each with an injected defect that must turn it red |
| `test_mirrors.py` | package/top-level mirror equality, including missing and diverged cases |
| `test_readme_gate.py` | README commands/flags/extras/file references against the real parser and the real tree |
| `test_ci_workflow.py` | workflow parses, four matrix legs, required steps, no silent skips, release gate stays out |
| `test_release_gate.py` | release gate runtime shape: one row per check, offline SKIPs, missing artefact is FAIL not a crash |
| `test_packaging.py` | zero runtime dependencies, package layout resolves, no third-party runtime imports |

Every gate in this suite is written so that breaking the thing it guards turns
it red. A test that cannot fail is worse than no test: it converts "unverified"
into "verified".
