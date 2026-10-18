# tools/golden_oracle — independent expectation generator

M1 populates this directory.

Why it exists: a golden case whose expected output is produced by the code
under test proves nothing. If the implementation is wrong, the expectation is
wrong in the same way, and the suite stays green. So the expectations are
computed by a **second implementation** of the same specifications, written
separately.

Hard rules (enforced by an AST gate):

- `tools/golden_oracle/` must not import `http_semantics_mcp.judgement` or any
  module that re-exports it. Expected values must be independent of the engine.
- `tools/gen_golden.py` writes `data/golden/**` and supports `--check`, which
  recomputes in memory and compares byte-for-byte with what is on disk.
- The only link between the two implementations is a byte-comparison test:
  run the oracle, run the engine, compare. Never a shared helper.

If a full second implementation is not justified for some tool, the downgrade
must be recorded in `data/README.md` section 3: which quantities are computed
independently and which are derived from the rule table. It must not silently
collapse into one source.
