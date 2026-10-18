"""Mirror and validate the per-tool JSON Schema descriptors.

Decision D50 (route A): the **in-package** file

    src/http_semantics_mcp/schemas/tools/<tool>.json

is the only editable source of truth for a tool's client-visible contract --
``name``, ``description``, ``inputSchema`` and ``outputSchema``. The top-level

    schemas/tools/<tool>.json

is a byte-identical mirror, and this script is its only writer.

The script does not invent schema content: it reads the package files, proves
they are well formed, and copies their bytes to the mirror. Usage::

    py tools/gen_schemas.py            # rewrite the top-level mirror
    py tools/gen_schemas.py --check    # compare only, do not write

Shape rules enforced on every object node (``plan/03`` section 6):

* every object that declares ``properties`` also sets ``additionalProperties:
  false`` (a header-name map is the one allowed object shape: it declares
  ``additionalProperties`` as a schema and no ``properties``);
* ``required`` is a subset of ``properties`` on every object;
* ``outputSchema.properties`` and ``outputSchema.required`` both equal, exactly,
  the key set frozen for that tool in ``data/README.md`` section 4.10;
* the file is stored in canonical form (sorted keys, two-space indent, LF only,
  one trailing newline) so that "regenerate and compare" is meaningful.

``--check`` names the first differing file with a byte context, so a failure
points at the fix instead of only reporting "drift".
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

if HERE not in sys.path:
    sys.path.insert(0, HERE)

import spectable  # noqa: E402

PACKAGE_SCHEMAS = os.path.join("src", "http_semantics_mcp", "schemas", "tools")
MIRROR_SCHEMAS = os.path.join("schemas", "tools")

DESCRIPTOR_KEYS = {"description", "inputSchema", "name", "outputSchema"}
# ``_time`` has output keys in section 4.10 too, but it is a data sample set,
# not a registered tool, so it has no descriptor file.
NON_TOOL_ROWS = frozenset(("_time",))


class SchemaError(Exception):
    """A descriptor is missing, malformed, or not in canonical form."""


def expected_tools(fields):
    """Return the registered tool names implied by the section 4.10 table."""
    return sorted(set(fields) - NON_TOOL_ROWS)


def _canonical(payload):
    text = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
    return (text + "\n").encode("utf-8")


def _walk_objects(node, tool, where, problems):
    """Check every object node's ``additionalProperties`` / ``required``."""
    if isinstance(node, dict):
        if "properties" in node:
            properties = node["properties"]
            if not isinstance(properties, dict) or not properties:
                problems.append(tool + ": " + where + ".properties must be a non-empty object")
                properties = {}
            if node.get("additionalProperties") is not False:
                problems.append(tool + ": " + where + " declares properties without additionalProperties: false")
            required = node.get("required")
            if required is not None:
                if not isinstance(required, list):
                    problems.append(tool + ": " + where + ".required must be an array")
                else:
                    unknown = sorted(set(required) - set(properties))
                    if unknown:
                        problems.append(tool + ": " + where + ".required names undeclared " + ", ".join(unknown))
                    if len(required) != len(set(required)):
                        problems.append(tool + ": " + where + ".required repeats a key")
        elif node.get("type") == "object" or "additionalProperties" in node:
            if "additionalProperties" not in node:
                problems.append(tool + ": " + where + " is an object without additionalProperties")
        for key, value in node.items():
            _walk_objects(value, tool, where + "." + key, problems)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _walk_objects(value, tool, where + "[" + str(index) + "]", problems)


def validate_descriptor(tool, payload, expected_keys, raw):
    """Return a list of problems; empty means the descriptor is well formed."""
    problems = []
    if not isinstance(payload, dict):
        return [tool + ": descriptor must be a JSON object"]
    if set(payload) != DESCRIPTOR_KEYS:
        problems.append(
            tool + ": top-level keys must be " + ", ".join(sorted(DESCRIPTOR_KEYS))
        )
        return problems
    if payload["name"] != tool:
        problems.append(tool + ": name field is " + repr(payload["name"]))
    if not isinstance(payload["description"], str) or not payload["description"].strip():
        problems.append(tool + ": description must be a non-empty string")

    for key in ("inputSchema", "outputSchema"):
        if not isinstance(payload[key], dict):
            problems.append(tool + ": " + key + " must be an object")
    if problems:
        return problems

    output = payload["outputSchema"]
    if set(output.get("properties", {})) != set(expected_keys):
        problems.append(
            tool + ": outputSchema.properties != section 4.10 ("
            + "missing " + str(sorted(set(expected_keys) - set(output.get("properties", {}))))
            + ", extra " + str(sorted(set(output.get("properties", {})) - set(expected_keys))) + ")"
        )
    if sorted(output.get("required", [])) != sorted(expected_keys):
        problems.append(
            tool + ": outputSchema.required must list every always-present field exactly once"
        )

    _walk_objects(payload["inputSchema"], tool, "inputSchema", problems)
    _walk_objects(payload["outputSchema"], tool, "outputSchema", problems)

    if raw != _canonical(payload):
        problems.append(tool + ": file is not in canonical form (sorted keys, indent 2, LF, one trailing newline)")
    return problems


def _read_package(root, tool, expected_keys):
    path = os.path.join(root, PACKAGE_SCHEMAS, tool + ".json")
    if not os.path.isfile(path):
        raise SchemaError("missing package descriptor: " + os.path.join(PACKAGE_SCHEMAS, tool + ".json"))
    with open(path, "rb") as handle:
        raw = handle.read()
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SchemaError(tool + ": not valid UTF-8 JSON: " + str(exc))
    problems = validate_descriptor(tool, payload, expected_keys, raw)
    if problems:
        raise SchemaError("; ".join(problems))
    return raw


def render(root):
    """Return ``{mirror_relative_path: bytes}`` for every tool descriptor."""
    contract = spectable.read_contract(root)
    fields = contract["output_fields"]
    tools = expected_tools(fields)
    if not tools:
        raise SchemaError("section 4.10 declares no tool rows")

    generated = {}
    for tool in tools:
        raw = _read_package(root, tool, fields[tool])
        generated[os.path.join(MIRROR_SCHEMAS, tool + ".json").replace(os.sep, "/")] = raw

    package_present = _json_names(os.path.join(root, PACKAGE_SCHEMAS))
    extra_package = sorted(package_present - {tool + ".json" for tool in tools})
    if extra_package:
        raise SchemaError("package schema files with no section 4.10 row: " + ", ".join(extra_package))
    return generated


def _json_names(directory):
    if not os.path.isdir(directory):
        return set()
    return {name for name in os.listdir(directory) if name.endswith(".json")}


def _first_difference(expected, actual):
    limit = min(len(expected), len(actual))
    index = limit
    for position in range(limit):
        if expected[position] != actual[position]:
            index = position
            break
    window = 60
    return (
        "first difference at byte "
        + str(index)
        + " (expected "
        + str(len(expected))
        + " bytes, found "
        + str(len(actual))
        + ")\n  expected: "
        + repr(expected[max(0, index - window) : index + window])
        + "\n  found:    "
        + repr(actual[max(0, index - window) : index + window])
    )


def check(root, out):
    generated = render(root)
    failures = 0
    for relative in sorted(generated):
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            out.write("MISSING  " + relative + " (regenerate with py tools/gen_schemas.py)\n")
            failures += 1
            continue
        with open(path, "rb") as handle:
            on_disk = handle.read()
        if on_disk == generated[relative]:
            out.write("OK       " + relative + " (" + str(len(on_disk)) + " bytes)\n")
            continue
        failures += 1
        out.write("DRIFT    " + relative + "\n  " + _first_difference(generated[relative], on_disk) + "\n")

    expected_names = set(os.path.basename(relative) for relative in generated)
    for name in sorted(_json_names(os.path.join(root, MIRROR_SCHEMAS)) - expected_names):
        out.write("ORPHAN   " + os.path.join(MIRROR_SCHEMAS, name) + " (no section 4.10 row)\n")
        failures += 1
    out.write("schemas: " + str(len(generated)) + " tool(s), " + str(failures) + " problem(s)\n")
    return 1 if failures else 0


def write(root, out):
    generated = render(root)
    expected_names = set(os.path.basename(relative) for relative in generated)
    for name in sorted(_json_names(os.path.join(root, MIRROR_SCHEMAS)) - expected_names):
        os.remove(os.path.join(root, MIRROR_SCHEMAS, name))
        out.write("REMOVED  " + os.path.join(MIRROR_SCHEMAS, name) + "\n")
    for relative in sorted(generated):
        path = os.path.join(root, relative)
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path, "wb") as handle:
            handle.write(generated[relative])
        out.write("WROTE    " + relative + " (" + str(len(generated[relative])) + " bytes)\n")
    out.write("schemas: " + str(len(generated)) + " tool(s) written\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Mirror the in-package tool schemas to schemas/tools/.")
    parser.add_argument("--check", action="store_true", help="compare only, do not write")
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    args = parser.parse_args(argv)

    try:
        if args.check:
            return check(args.root, sys.stdout)
        return write(args.root, sys.stdout)
    except (spectable.SpecTableError, SchemaError) as exc:
        sys.stderr.write("schema error: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
