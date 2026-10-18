# data/golden — frozen golden cases

M1 populates this directory. Layout (plan/04 section 2):

```
data/golden/
  cors_evaluate/<case_id>.json
  cors_simulate_fetch/<case_id>.json
  cache_evaluate/<case_id>.json
  conditional_evaluate/<case_id>.json
  vary_match/<case_id>.json
  _time/<case_id>.json
```

Each file holds one case:

```json
{
  "case_id": "...",
  "tool": "...",
  "input": { },
  "expected": { },
  "spec_basis": ["..."],
  "source": "synthetic"
}
```

Rules:

- `expected` is the **complete** output object — every field from the tool
  schema, including empty arrays, empty objects and `false`.
- The file name equals `case_id`, restricted to `[a-z0-9_-]`.
- Frozen once committed. Changing an expectation means a new `case_id` plus a
  recorded reason, never an in-place edit.
- **No `observed_*` fields.** A frozen observation turns the benchmark into a
  comparison of two pre-computed answers, so the engine could be entirely
  broken and the suite would stay green.
- Expected values come from `tools/golden_oracle/`, an implementation that is
  written separately from `src/http_semantics_mcp/judgement/` and is forbidden
  from importing it.

`data/README.md` section 3 governs content: reserved example domains only,
explicit fake ETags, fixed time literals, never a real response header.

## Regenerating

Inputs live in `tools/cases/<tool>/<case_id>.json` and carry no `expected`.
`tools/gen_golden.py` recomputes every expectation with the oracle:

```bash
python tools/gen_golden.py            # rewrite data/golden/**
python tools/gen_golden.py --check    # byte compare, exit 1 on drift or orphans
python tools/golden_coverage.py       # code enum vs. golden coverage, both directions
```
