# tools/golden_oracle — independent expectation generator

Written in M1 from the specifications, not from the implementation.

Why it exists: a golden case whose expected output is produced by the code
under test proves nothing. If the implementation is wrong, the expectation is
wrong in the same way, and the suite stays green. So the expectations are
computed by a **second implementation** of the same specifications, written
separately.

Hard rules (enforced by an AST gate, `tools/gates.py:oracle_independence`):

- `tools/golden_oracle/` must not import `http_semantics_mcp` at all — not the
  judgement layer, not a helper, and not through `importlib.import_module`.
- `tools/gen_golden.py` writes `data/golden/**` and supports `--check`, which
  recomputes in memory and compares byte-for-byte with what is on disk.
- The only link between the two implementations is a byte-comparison test:
  run the oracle, run the engine, compare. Never a shared helper.

If a full second implementation is not justified for some tool, the downgrade
must be recorded in `data/README.md` section 3: which quantities are computed
independently and which are derived from the rule table. It must not silently
collapse into one source.

## Layout

| Module | Covers |
| --- | --- |
| `inputs.py` | header/method/URL normalisation shared by the tools |
| `timeparse.py` | `YYYY-MM-DDTHH:MM:SSZ` and IMF-fixdate → integer UTC seconds |
| `cors.py` | T1 `cors_evaluate` |
| `fetch_sim.py` | T2 `cors_simulate_fetch` (redirect hops, events, preflight cache key) |
| `cache.py` | T3 `cache_evaluate` (RFC 9111 age / freshness arithmetic) |
| `conditional.py` | T4 `conditional_evaluate` (RFC 9110 §13.2.2 precedence plus the two comparison functions) |
| `vary.py` | T5 `vary_match` (RFC 9111 §4.1) |
| `engine.py` | dispatch + catalog loading |

The catalog (`codes.json`) is passed in rather than duplicated, so wording and
`spec_ref` lists exist in exactly one place. The oracle supplies the algorithm;
the table supplies the text.
