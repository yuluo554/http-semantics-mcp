# schemas/tools (in-package source of truth)

JSON Schemas for the five tools land here in **M5**, one file per tool:
`cors_evaluate.json`, `cors_simulate_fetch.json`, `cache_evaluate.json`,
`conditional_evaluate.json`, `vary_match.json`.

Until then `registry.py` carries an inlined `inputSchema` per implemented tool
(decision D43): the client-visible surface is honest at every milestone, and the
generated schema files arrive once all five tools exist.

`schemas/tools/` at the repository root is a byte-identical mirror.

The schema is not documentation: it is the contract `tools/list` serves to the
client. Two gates keep it honest (M5):

1. **Mirror equality** — root copy equals package copy, byte for byte.
2. **Field-set equality** — for every golden case, the set of keys in the
   actual output equals the set of keys in `outputSchema.properties`. Not a
   subset: a missing field and an extra field both fail.

`additionalProperties: false` is mandatory on every object schema, and every
field that always appears is listed in `required`.
