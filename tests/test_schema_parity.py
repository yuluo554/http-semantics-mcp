"""Schema parity: the published contract equals the tool's actual output.

Three surfaces must agree for every tool (plan/03 section 6):

* the in-package descriptor at
  ``src/http_semantics_mcp/schemas/tools/<tool>.json``,
* the key set frozen in ``data/README.md`` section 4.10,
* the keys (and value shapes) the judgement layer actually returns for every
  frozen golden case.

The comparison is a **set equality in both directions**: a field missing from
the schema and a field missing from the output both fail. And the gate proves
it looked at something: a tool with no case is a failure, not a pass.
"""

import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gen_schemas  # noqa: E402
import golden_coverage  # noqa: E402
import spectable  # noqa: E402

from http_semantics_mcp.registry import build_registry  # noqa: E402

NON_TOOL = "_time"
PACKAGE_SCHEMAS = os.path.join("src", "http_semantics_mcp", "schemas", "tools")


def _contract_fields():
    with open(os.path.join(ROOT, "data", "README.md"), "r", encoding="utf-8") as handle:
        return spectable.read_output_fields(handle.read())


def _tool_names():
    return gen_schemas.expected_tools(_contract_fields())


def _tool_cases():
    """``[(tool, case_id, case)]`` for the five judgement tools only."""
    return [
        (tool, case_id, case)
        for tool, case_id, case in golden_coverage.iter_cases(ROOT)
        if tool != NON_TOOL
    ]


def _call(tool, arguments):
    registered = build_registry().get(tool)
    assert registered is not None, "tool is not registered: " + tool
    result = registered.handler(arguments)
    return result, json.loads(result["content"][0]["text"])


def _descriptor(tool):
    path = os.path.join(ROOT, PACKAGE_SCHEMAS, tool + ".json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# -- the descriptor set ------------------------------------------------


def test_every_registered_tool_has_exactly_one_descriptor_file():
    registered = set(build_registry().names())
    declared = set(_tool_names())
    on_disk = {
        name[: -len(".json")]
        for name in os.listdir(os.path.join(ROOT, PACKAGE_SCHEMAS))
        if name.endswith(".json")
    }
    assert registered, "no tool is registered"
    assert registered == declared == on_disk


def test_descriptors_carry_the_whole_mcp_contract():
    for tool in _tool_names():
        descriptor = _descriptor(tool)
        assert set(descriptor) == {"name", "description", "inputSchema", "outputSchema"}
        assert descriptor["name"] == tool
        assert descriptor["description"].strip()
        assert descriptor["inputSchema"]["type"] == "object"
        assert descriptor["outputSchema"]["type"] == "object"
        assert not gen_schemas.validate_descriptor(
            tool, descriptor, _contract_fields()[tool], _canonical_bytes(descriptor)
        )


def _canonical_bytes(payload):
    return gen_schemas._canonical(payload)


# -- the contract gate -------------------------------------------------


@pytest.mark.parametrize("tool", _tool_names())
def test_output_schema_keys_equal_the_frozen_contract(tool):
    output = _descriptor(tool)["outputSchema"]
    assert set(output["properties"]) == set(_contract_fields()[tool])
    assert sorted(output["required"]) == sorted(output["properties"])
    assert output["additionalProperties"] is False


@pytest.mark.parametrize("tool", _tool_names())
def test_actual_output_keys_and_shapes_match_the_schema(tool):
    cases = [case for name, case in _cases_for(tool)]
    assert cases, "no golden case for " + tool

    schema = _descriptor(tool)["outputSchema"]
    successes = 0
    for case in cases:
        result, payload = _call(tool, case["input"])
        if set(payload) == {"error"}:
            assert result["isError"] is True, case["case_id"]
            assert set(payload["error"]) == {"code", "field", "detail"}, case["case_id"]
            continue
        assert result["isError"] is False, case["case_id"]
        assert set(payload) == set(schema["properties"]), case["case_id"]
        problems = []
        _validate(payload, schema, case["case_id"], problems)
        assert problems == [], "; ".join(problems)
        successes += 1
    assert successes > 0, "no successful case for " + tool


def test_the_gate_compared_every_tool_and_enough_cases():
    """A green gate that scanned nothing is the failure this asserts against."""
    per_tool = {tool: 0 for tool in _tool_names()}
    total = 0
    for tool, _case_id, _case in _tool_cases():
        per_tool[tool] += 1
        total += 1
    assert total >= 80, "expected the full frozen set minus the _time samples"
    for tool, count in per_tool.items():
        assert count > 0, "no case exercises " + tool


# -- mirrors -----------------------------------------------------------


def test_generated_mirror_is_clean():
    out = _Null()
    assert gen_schemas.check(ROOT, out) == 0, out.text
    assert "5 tool(s)" in out.text


def test_mirror_drift_and_orphans_are_detected(tmp_path):
    import shutil

    project = tmp_path / "repo"
    shutil.copytree(os.path.join(ROOT, PACKAGE_SCHEMAS), project / PACKAGE_SCHEMAS)
    shutil.copytree(os.path.join(ROOT, "schemas", "tools"), project / "schemas" / "tools")
    (project / "data").mkdir()
    shutil.copy(
        os.path.join(ROOT, "data", "README.md"),
        project / "data" / "README.md",
    )

    out = _Null()
    assert gen_schemas.check(str(project), out) == 0, out.text

    target = project / "schemas" / "tools" / "cors_evaluate.json"
    payload = target.read_text(encoding="utf-8")
    with open(str(target), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload.replace('"block"', '"blocked"', 1))
    out = _Null()
    assert gen_schemas.check(str(project), out) == 1
    assert "DRIFT" in out.text

    with open(str(target), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(payload)
    (project / "schemas" / "tools" / "orphan.json").write_text("{}\n", encoding="utf-8")
    out = _Null()
    assert gen_schemas.check(str(project), out) == 1
    assert "ORPHAN" in out.text


def test_a_descriptor_missing_an_output_key_is_rejected():
    descriptor = _descriptor("cache_evaluate")
    del descriptor["outputSchema"]["properties"]["action"]
    problems = gen_schemas.validate_descriptor(
        "cache_evaluate", descriptor, _contract_fields()["cache_evaluate"], _canonical_bytes(descriptor)
    )
    assert any("outputSchema.properties" in problem for problem in problems)


def test_a_descriptor_that_allows_extra_keys_is_rejected():
    descriptor = _descriptor("vary_match")
    descriptor["outputSchema"]["additionalProperties"] = True
    problems = gen_schemas.validate_descriptor(
        "vary_match", descriptor, _contract_fields()["vary_match"], _canonical_bytes(descriptor)
    )
    assert any("additionalProperties" in problem for problem in problems)


# -- a small JSON-Schema shape checker --------------------------------


def _cases_for(tool):
    return [(case_id, case) for name, case_id, case in _tool_cases() if name == tool]


_TYPE_OF = {bool: "boolean", int: "integer", str: "string", list: "array", dict: "object"}


def _validate(value, schema, where, problems):
    """Check ``value`` against a subset of JSON Schema: type, enum, objects, arrays."""
    if not isinstance(schema, dict):
        return
    declared = schema.get("type")
    allowed = declared if isinstance(declared, list) else ([declared] if declared else [])
    if value is None:
        if "null" not in allowed and allowed:
            problems.append(where + ": null is not allowed")
        return
    kind = _TYPE_OF.get(type(value))
    if allowed and kind not in allowed:
        problems.append(where + ": " + str(kind) + " is not one of " + str(allowed))
        return
    if "enum" in schema and value not in schema["enum"]:
        problems.append(where + ": " + repr(value) + " is not in " + repr(schema["enum"]))

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        if "properties" in schema:
            extra = sorted(set(value) - set(properties))
            if extra:
                problems.append(where + ": undeclared key(s) " + ", ".join(extra))
            missing = sorted(set(schema.get("required", [])) - set(value))
            if missing:
                problems.append(where + ": missing required key(s) " + ", ".join(missing))
            for key, item in value.items():
                if key in properties:
                    _validate(item, properties[key], where + "." + key, problems)
        else:
            additional = schema.get("additionalProperties", True)
            if additional is False and value:
                problems.append(where + ": additionalProperties is false but keys are present")
            elif isinstance(additional, dict):
                for key, item in value.items():
                    _validate(item, additional, where + "." + key, problems)
    elif isinstance(value, list) and isinstance(schema.get("items"), dict):
        for index, item in enumerate(value):
            _validate(item, schema["items"], where + "[" + str(index) + "]", problems)


class _Null(object):
    def __init__(self):
        self.text = ""

    def write(self, value):
        self.text += value
