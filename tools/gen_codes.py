"""Generate the rule catalogue from ``data/README.md`` §4.

The README table is the single editable source (decision K9). This script is
the only writer of three files:

    src/http_semantics_mcp/references/codes.json   (in-package truth, JSON)
    references/codes.json                          (byte-identical mirror)
    src/http_semantics_mcp/rules.py                (same catalogue as a Python
                                                    literal module + one named
                                                    constant per rule code)

The Python module exists because the judgement layer must *name* the rule it
emits while being forbidden to spell a code literal (decision K17). It is a
generated artifact exactly like ``codes.json``: hand edits are caught by
``--check``. Usage:

    py tools/gen_codes.py            # rewrite both files
    py tools/gen_codes.py --check    # recompute in memory, compare bytes, exit 1 on drift

``--check`` prints the first differing file, the byte offset and a short
context, so a failure names the fix instead of just reporting "differs".
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

PACKAGE_CODES = os.path.join("src", "http_semantics_mcp", "references", "codes.json")
MIRROR_CODES = os.path.join("references", "codes.json")
PACKAGE_RULES = os.path.join("src", "http_semantics_mcp", "rules.py")
TARGETS = (PACKAGE_CODES, MIRROR_CODES, PACKAGE_RULES)

SCHEMA_VERSION = 1

RULES_HEADER = '''"""Generated rule catalogue -- do not edit.

Rendered by ``tools/gen_codes.py`` from ``data/README.md`` section 4, and
compared byte for byte by ``gen_codes --check``. ``CATALOG`` is the same object
as ``references/codes.json``; the constants below are the rule codes, so the
judgement layer can name a rule it emits without spelling a code literal
(decisions D41/D42). ``tools/gates.py:code_literals`` exempts this file and
only this file.

``data/README.md`` section 4 is the single editable source: change the table
and re-run the generator, never edit this module.
"""

CATALOG = '''


class GenerationError(Exception):
    """The contract cannot be rendered faithfully."""


def _literal(value, indent=0):
    """Render a JSON-shaped value as deterministic Python source.

    ``repr`` on a dict/list would depend on insertion order, so the nesting is
    walked here with keys always sorted. Only the types the contract can
    produce are accepted; anything else is a hard error rather than a guess.
    """
    pad = " " * indent
    inner = " " * (indent + 4)
    if isinstance(value, dict):
        if not value:
            return "{}"
        lines = []
        for key in sorted(value):
            lines.append(inner + repr(key) + ": " + _literal(value[key], indent + 4) + ",")
        return "{\n" + "\n".join(lines) + "\n" + pad + "}"
    if isinstance(value, list):
        if not value:
            return "[]"
        lines = [inner + _literal(item, indent + 4) + "," for item in value]
        return "[\n" + "\n".join(lines) + "\n" + pad + "]"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return repr(value)
    raise GenerationError("cannot render " + type(value).__name__ + " as a Python literal")


def render_rules(payload):
    """Return ``rules.py`` bytes for a rendered catalogue payload."""
    lines = [RULES_HEADER + _literal(payload, 0), "", "# One constant per rule code."]
    for code in sorted(payload["codes"]):
        lines.append(code + " = " + repr(code))
    return ("\n".join(lines) + "\n").encode("utf-8")


def render(root):
    """Return ``{relative_path: bytes}`` for every generated file."""
    contract = spectable.read_contract(root)
    codes = {}
    for record in contract["codes"]:
        codes[record["code"]] = {
            "prefix": record["prefix"],
            "severity": record["severity"],
            "spec_ref": record["spec_ref"],
            "template": record["template"],
            "meaning": record["meaning"],
        }

    payload = {
        "schema_version": SCHEMA_VERSION,
        "source": "data/README.md section 4",
        "codes": codes,
        "error_codes": contract["error_codes"],
        "notes": contract["notes"],
        "preflight_cache_key": contract["preflight_cache_key"],
        "vary_normalization": contract["vary_normalization"],
        "verified_spec_refs": contract["verified_spec_refs"],
    }
    text = json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    )
    data = (text + "\n").encode("utf-8")
    files = {relative: data for relative in (PACKAGE_CODES, MIRROR_CODES)}
    files[PACKAGE_RULES] = render_rules(payload)
    return files


def _first_difference(expected, actual):
    """Describe the first byte that differs, with a readable neighbourhood."""
    limit = min(len(expected), len(actual))
    index = limit
    for position in range(limit):
        if expected[position] != actual[position]:
            index = position
            break
    window = 60
    left = expected[max(0, index - window) : index + window]
    right = actual[max(0, index - window) : index + window]
    return (
        "first difference at byte "
        + str(index)
        + " (expected "
        + str(len(expected))
        + " bytes, found "
        + str(len(actual))
        + ")\n  expected: "
        + repr(left)
        + "\n  found:    "
        + repr(right)
    )


def check(root, out):
    """Compare regenerated bytes with the working tree. Return an exit code."""
    generated = render(root)
    failures = 0
    for relative in TARGETS:
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            out.write("MISSING  " + relative + " (regenerate with py tools/gen_codes.py)\n")
            failures += 1
            continue
        with open(path, "rb") as handle:
            on_disk = handle.read()
        if on_disk == generated[relative]:
            out.write("OK       " + relative + " (" + str(len(on_disk)) + " bytes)\n")
            continue
        failures += 1
        out.write("DRIFT    " + relative + "\n  " + _first_difference(generated[relative], on_disk) + "\n")
    return 1 if failures else 0


def write(root, out):
    generated = render(root)
    for relative in TARGETS:
        path = os.path.join(root, relative)
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path, "wb") as handle:
            handle.write(generated[relative])
        out.write("WROTE    " + relative + " (" + str(len(generated[relative])) + " bytes)\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate codes.json from data/README.md section 4.")
    parser.add_argument("--check", action="store_true", help="compare only, do not write")
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    args = parser.parse_args(argv)

    try:
        if args.check:
            return check(args.root, sys.stdout)
        return write(args.root, sys.stdout)
    except spectable.SpecTableError as exc:
        sys.stderr.write("spec table error: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
