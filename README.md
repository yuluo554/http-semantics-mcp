# http-semantics-mcp

Deterministic HTTP semantics judgement, delivered as an MCP server over stdio.

**Status: M4 (conditional requests and Vary).** The server starts, completes
the MCP handshake and reports **five tools** — `cache_evaluate`,
`conditional_evaluate`, `cors_evaluate`, `cors_simulate_fetch` and
`vary_match`. All five are judged against frozen golden cases
(18 + 19 + 24 + 10 + 9) and produce byte-identical output. Schema generation
and the determinism sweep land in M5; the public release is M6. See
[`plan/05-里程碑.md`](plan/05-里程碑.md).

---

## What this is

An oracle for the corners of HTTP that fail silently: CORS, cache semantics,
conditional requests and `Vary`. You hand it request/response headers as
literals; it hands back a specification-derived verdict plus the rule IDs and
clause references behind it.

- **No network.** No DNS, no TCP, no HTTP. `url` is parsed for
  scheme/host/port only. There is nothing to capture, proxy or replay.
- **No capture.** Input is caller-supplied header literals, not observed
  traffic.
- **No security scoring.** No grades, no severity, no "is this site safe".
  Header security scanning is a different job and is out of scope.
- **Deterministic.** Same input → byte-identical serialised output. No clock,
  no randomness, no environment reads. Time is an argument, not a lookup.

### Tools

| Tool | Question it answers | Milestone |
| --- | --- | --- |
| `cors_evaluate` | Will the browser let this response through? | M2 ✅ |
| `cors_simulate_fetch` | What happens across redirects, hop by hop? | M2 ✅ |
| `cache_evaluate` | Can this stored response be served without revalidating? | M3 ✅ |
| `conditional_evaluate` | Which conditional-request rule decides the status? | M4 ✅ |
| `vary_match` | Does this cached entry match the incoming request? | M4 ✅ |

`tools/list` returns exactly the tools that are implemented. A stub descriptor
would tell a client a capability exists that does not, which is why the
remaining milestones add tools rather than plans.

### A cache verdict by hand

Ask whether a stored response is still fresh, and what the numbers are:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cache_evaluate","arguments":{"now":"2026-01-01T00:00:30Z","response_headers":{"Cache-Control":"max-age=60","Date":"Thu, 01 Jan 2026 00:00:00 GMT"},"stored":{"stored_at":"2026-01-01T00:00:10Z","age":"10"}}}}' \
  | python -m http_semantics_mcp
```

```json
{"action":"serve","current_age":30,"freshness_lifetime":60,"is_fresh":true,"must_revalidate":false,"reasons":[],"stale_while_revalidate_window":0}
```

`now` is an argument, not a clock read: the same call always returns the same
bytes, on any machine, at any time.

### What it is not

- Not a browser. Verdicts are spec-derived; where an implementation differs
  from the specification, the specification wins and the divergence is noted.
- Not a substitute for `mitmproxy` / `powhttp`-style capture tools. Those need
  real traffic; this needs a JSON object.
- Not a security scanner. Out of scope by design (see
  `plan/01-题目文档.md` section 6).

---

## Install

Requires Python 3.8 or newer. The runtime has **no third-party dependencies**.

```bash
git clone https://github.com/yuluo554/10-19-http-semantics-mcp.git
cd 10-19-http-semantics-mcp
python -m pip install -e ".[dev]"
```

`.[dev]` installs the test-time dependencies only (`pytest`, `PyYAML`). If you
only want to run the server, `python -m pip install -e .` is enough.

Verify the install:

```bash
python -m http_semantics_mcp --version
python -m http_semantics_mcp --selftest
```

`--selftest` prints one line per check and exits `0` on pass, `1` on failure.
It never prints a verdict — it checks the installation, not your headers.

---

## Run

The server speaks newline-delimited JSON-RPC 2.0 on stdin/stdout.

```bash
python -m http_semantics_mcp
```

Or, after installation, the console script:

```bash
http-semantics-mcp
```

### Client configuration

Claude Code (`~/.claude.json` or project `.mcp.json`):

```json
{
  "mcpServers": {
    "http-semantics": {
      "command": "python",
      "args": ["-m", "http_semantics_mcp"],
      "env": {}
    }
  }
}
```

Codex (`~/.codex/config.toml`):

```toml
[mcp_servers.http-semantics]
command = "python"
args = ["-m", "http_semantics_mcp"]
```

Any stdio MCP client works: spawn the process, write one JSON object per line,
read one JSON object per line.

### Protocol surface

| Method | Result |
| --- | --- |
| `initialize` | `protocolVersion`, `capabilities`, `serverInfo` |
| `notifications/initialized` | no response |
| `ping` | `{}` (available before `initialize`) |
| `tools/list` | registered tools, ASCII-sorted by name |
| `tools/call` | tool result, or a JSON-RPC error for an unknown tool |
| anything else | `-32601` |

Supported protocol versions: `2025-06-18`, `2025-03-26`, `2024-11-05`.
An unrecognised version is answered with `2025-06-18`, which the specification
permits; the client decides whether to continue.

Error codes: `-32700` parse error, `-32600` invalid request, `-32601` unknown
method, `-32602` invalid params, `-32002` not initialized, `-32603` internal
error. A *tool-level* bad input is not a JSON-RPC error: it returns a result
with `isError: true`.

### A handshake by hand

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18"}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/list"}' \
  | python -m http_semantics_mcp
```

### A verdict by hand

Ask whether a cross-origin response is allowed, and what to change if not:

```bash
printf '%s\n' \
  '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' \
  '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
  '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"cors_evaluate","arguments":{"method":"GET","url":"https://api.example.com/v1","origin":"https://app.example.com","credentials":"omit","request_headers":{},"response":{"status":200,"headers":{}},"is_preflight":false}}}' \
  | python -m http_semantics_mcp
```

The verdict arrives as one JSON string inside `content[0].text`:

```json
{"decision":"block","missing_headers":["access-control-allow-origin"],"notes":{"allow_credentials_null_origin":false,"max_age_capped_by_client":false,"wildcard_with_credentials":false},"recommended_headers":{"access-control-allow-origin":"https://app.example.com"},"violations":[{"code":"CORS_MISSING_ALLOW_ORIGIN","detail":"response has no Access-Control-Allow-Origin (origin=https://app.example.com)","spec_ref":["Fetch §CORS check"]}]}
```

`decision: "block"` is a successful judgement, so `isError` stays `false`. Only
a malformed *request* sets `isError: true`, and it still answers with a payload
rather than a stack trace.

---

## Development

```bash
python -m pytest
python tools/run_gates.py
python tools/mutate_check.py
python tools/smoke_stdio.py
python scripts/check_release.py --pre-tag
```

- `pytest` runs the full suite (protocol, transport framing, determinism,
  gates, packaging surface).
- `tools/run_gates.py` runs the eight static gates and names the failing one.
- `tools/mutate_check.py` breaks one behaviour per gate and asserts the gate
  goes red. A gate that cannot fail is decoration; this script is how that
  claim is kept honest rather than asserted.
- `tools/smoke_stdio.py` starts the server as a real subprocess and asserts on
  the raw bytes: every stdout line is JSON, no `\r`, response count matches
  request count.
- `scripts/check_release.py --pre-tag` is the release-terminal gate. It is
  **not** wired into CI on purpose: before a tag exists, several of its checks
  must be red, and a permanently red job carries no information.

### Repository gates

Eight static gates run in tests, in CI, and inside the release check. Each one
must be provably able to fail (`tests/test_gates.py` and `tests/test_m1_gates.py`
inject a defect for every gate, and `tools/mutate_check.py` proves it end to
end):

| Gate | Rule |
| --- | --- |
| purity | `src/http_semantics_mcp/judgement/` imports no clock, network, env, process, or filesystem module |
| no-nondeterminism | the whole runtime package imports no clock, randomness or network; no `os.environ` / `getenv` anywhere |
| single-serialiser | `json.dumps` appears exactly once, in `canonical.py` |
| absolute paths | no machine-specific path (drive letter, home directory, UNC share) in repository text |
| line endings | every text file is LF-only and `.gitattributes` declares `eol=lf` |
| oracle independence | `tools/golden_oracle/` never imports `http_semantics_mcp`, directly or dynamically |
| golden hygiene | every frozen case has the required fields and no `observed_*` key |
| code literals | no hand-written package source spells a rule code; the generated catalogue (`references/codes.json` and `rules.py`) is the only copy |

### Layout

```
src/http_semantics_mcp/   server, protocol, registry, judgement layer
schemas/tools/            generated mirror of the in-package JSON Schemas
references/               generated mirror of the in-package code table
data/golden/              frozen golden cases (input + expected output)
data/wpt/                 WPT cors/ directory index (paths + blob shas only)
data/wpt-mapping.json     WPT cors/ mapping ledger
plan/                     the project plan, milestones and release records
tools/                    gates, smoke test, generators
scripts/check_release.py  release-terminal self-check
```

The in-package copies under `src/http_semantics_mcp/` are the only editable
sources for `codes.json` and the tool schemas; the top-level copies are
byte-identical mirrors so an installed distribution and a reader both see the
same contract.

---

## Data and verification

All inputs are synthetic. Domains are reserved examples (`example.com`,
`example.org`, `example.net`, `localhost`); ETags are explicit fakes; times are
fixed literals. No real response headers, tokens, cookies, HAR or pcap files
are collected, and `.gitignore` blocks those paths.

Golden cases freeze the input *and* the expected output. Expected values are
produced by an independent oracle under `tools/golden_oracle/`, not by the
implementation under test, and a gate forbids the oracle from importing the
judgement layer — otherwise the benchmark would be comparing an implementation
with itself.

Browser behaviour is cross-checked against
[`web-platform-tests/wpt`](https://github.com/web-platform-tests/wpt)'s `cors/`
suite (index pinned to commit `850b36a5`, data day 2026-10-18), transcribed to
header-level cases in `data/golden/`. The ledger in `data/wpt-mapping.json`
accounts for all 45 files in the directory: 15 mapped, 30 listed with a reason
(real network, TLS, timing, browser-proprietary behaviour, or out of scope).
Nothing is guessed at, and no test body is copied into this repository.

---

## License

MIT. See [`LICENSE`](LICENSE).

## Project plan

- [`plan/00-README总览.md`](plan/00-README总览.md) — index, decisions, promise ledger
- [`plan/01-题目文档.md`](plan/01-题目文档.md) — the problem statement (frozen)
- [`plan/02-架构与技术选型.md`](plan/02-架构与技术选型.md) — architecture and transport contract
- [`plan/03-模块详设.md`](plan/03-模块详设.md) — T1–T5 algorithms
- [`plan/04-数据计划.md`](plan/04-数据计划.md) — golden cases, WPT mapping, oracle independence
- [`plan/05-里程碑.md`](plan/05-里程碑.md) — milestones and definition of done
- [`plan/06-交付对标与决策记录.md`](plan/06-交付对标与决策记录.md) — scoring map and decision log
