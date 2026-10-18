# schemas/tools (generated mirror)

Five JSON Schemas, one per tool, byte-identical to
`src/http_semantics_mcp/schemas/tools/<tool>.json`: `cache_evaluate.json`,
`conditional_evaluate.json`, `cors_evaluate.json`, `cors_simulate_fetch.json`,
`vary_match.json`.

Do not edit files in this directory by hand: the package path is the only
editable source, and `tools/gen_schemas.py --check` plus
`scripts/check_release.py` fail when the two diverge.
