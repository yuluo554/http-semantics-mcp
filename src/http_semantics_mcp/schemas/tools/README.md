# schemas/tools (in-package source of truth)

One JSON Schema descriptor per tool lives here (M5, decision D50):
`name`, `description`, `inputSchema` and `outputSchema` in a single file --
`cache_evaluate.json`, `conditional_evaluate.json`, `cors_evaluate.json`,
`cors_simulate_fetch.json`, `vary_match.json`.

This file is the *only* editable copy of the client-visible contract.
`registry.build_registry()` reads it at runtime (a missing descriptor raises
`registry.DescriptorError` rather than serving a tool with no schema), and
`tools/gen_schemas.py` mirrors it byte for byte to `schemas/tools/` at the
repository root.

The schema is not documentation: it is the contract `tools/list` serves to the
client. Three checks keep it honest:

1. **Mirror equality** — root copy equals package copy, byte for byte.
2. **Field-set equality** — for every golden case, the set of keys in the
   actual output equals the set of keys in `outputSchema.properties` (and
   `required` lists exactly those keys). Not a subset: a missing field and an
   extra field both fail.
3. **Value shape** — the published schema also constrains types and enums, and
   every frozen case's real output is validated against it.

`additionalProperties: false` is mandatory on every object that declares
`properties`. A header-name map is the one other object shape: it declares
`additionalProperties` as a schema and no `properties`.
