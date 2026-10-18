"""Generate ``data/golden/<tool>/<case_id>.json`` from hand-written inputs.

Inputs live in ``tools/cases/<tool>/<case_id>.json`` and never contain
``expected``. Expectations come from ``tools/golden_oracle/``, which is a
second implementation written from the specifications (decision D27).

    py tools/gen_golden.py            # rewrite data/golden/**
    py tools/gen_golden.py --check    # recompute in memory, compare bytes, exit 1 on drift
    py tools/gen_golden.py --tool vary_match
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

if HERE not in sys.path:
    sys.path.insert(0, HERE)

from golden_oracle import ToolError, evaluate, load_catalog  # noqa: E402

CASES_DIR = "tools/cases"
GOLDEN_DIR = os.path.join("data", "golden")
TOOL_DIRECTORIES = (
    "_time",
    "cors_evaluate",
    "cors_simulate_fetch",
    "cache_evaluate",
    "conditional_evaluate",
    "vary_match",
)
REQUIRED_KEYS = ("case_id", "tool", "input", "spec_basis", "source")
ALLOWED_KEYS = set(REQUIRED_KEYS) | {"notes", "wpt"}


class CaseError(Exception):
    """A case file is malformed; generation stops rather than guessing."""


def _case_paths(root, tool):
    directory = os.path.join(root, CASES_DIR, tool)
    if not os.path.isdir(directory):
        return []
    return [
        os.path.join(directory, name)
        for name in sorted(os.listdir(directory))
        if name.endswith(".json")
    ]


def load_cases(root, tool=None):
    """Return ``[(tool, case_dict)]`` for every input file."""
    tools = [tool] if tool else TOOL_DIRECTORIES
    cases = []
    for name in tools:
        for path in _case_paths(root, name):
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            relative = os.path.relpath(path, root).replace(os.sep, "/")
            _validate(payload, name, relative)
            cases.append((name, payload))
    return cases


def _validate(payload, tool, relative):
    if not isinstance(payload, dict):
        raise CaseError(relative + ": top level must be an object")
    missing = [key for key in REQUIRED_KEYS if key not in payload]
    if missing:
        raise CaseError(relative + ": missing " + ", ".join(missing))
    unknown = sorted(set(payload) - ALLOWED_KEYS)
    if unknown:
        raise CaseError(relative + ": unknown keys " + ", ".join(unknown))
    if payload["tool"] != tool:
        raise CaseError(relative + ": tool field does not match its directory")
    if payload["case_id"] != os.path.splitext(os.path.basename(relative))[0]:
        raise CaseError(relative + ": case_id must equal the file name")
    if not isinstance(payload["spec_basis"], list) or not payload["spec_basis"]:
        raise CaseError(relative + ": spec_basis must be a non-empty array")
    if not isinstance(payload["source"], str) or not payload["source"]:
        raise CaseError(relative + ": source must be a string")
    if "expected" in payload:
        raise CaseError(relative + ": input cases must not carry expected (oracle owns it)")


def render_case(name, payload, catalog):
    """Return the frozen case object as it is written to ``data/golden``."""
    try:
        expected = evaluate(name, payload["input"], catalog)
    except ToolError as exc:
        expected = exc.payload()

    case = {
        "case_id": payload["case_id"],
        "tool": payload["tool"],
        "input": payload["input"],
        "expected": expected,
        "spec_basis": payload["spec_basis"],
        "source": payload["source"],
    }
    if "notes" in payload:
        case["notes"] = payload["notes"]
    if "wpt" in payload:
        case["wpt"] = payload["wpt"]
    return case


def render(root):
    """Return ``{relative_path: bytes}`` for every golden case."""
    catalog = load_catalog(root)
    rendered = {}
    for name, payload in load_cases(root):
        case = render_case(name, payload, catalog)
        text = json.dumps(case, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False)
        relative = os.path.join(GOLDEN_DIR, name, payload["case_id"] + ".json")
        rendered[relative.replace(os.sep, "/")] = (text + "\n").encode("utf-8")
    if not rendered:
        raise CaseError("no cases found under " + CASES_DIR)
    return rendered


def _first_difference(expected, actual):
    limit = min(len(expected), len(actual))
    index = limit
    for position in range(limit):
        if expected[position] != actual[position]:
            index = position
            break
    window = 60
    return (
        "first difference at byte " + str(index)
        + " (expected " + str(len(expected)) + " bytes, found " + str(len(actual)) + ")\n  expected: "
        + repr(expected[max(0, index - window) : index + window])
        + "\n  found:    "
        + repr(actual[max(0, index - window) : index + window])
    )


def _existing(root):
    found = []
    base = os.path.join(root, GOLDEN_DIR)
    for directory in TOOL_DIRECTORIES:
        path = os.path.join(base, directory)
        if not os.path.isdir(path):
            continue
        for name in sorted(os.listdir(path)):
            if name.endswith(".json") and name != "README.md":
                found.append(os.path.join(GOLDEN_DIR, directory, name).replace(os.sep, "/"))
    return sorted(found)


def check(root, out):
    generated = render(root)
    failures = 0
    for relative in sorted(generated):
        path = os.path.join(root, relative)
        if not os.path.isfile(path):
            out.write("MISSING  " + relative + "\n")
            failures += 1
            continue
        with open(path, "rb") as handle:
            on_disk = handle.read()
        if on_disk == generated[relative]:
            continue
        failures += 1
        out.write("DRIFT    " + relative + "\n  " + _first_difference(generated[relative], on_disk) + "\n")
    for relative in _existing(root):
        if relative not in generated:
            out.write("ORPHAN   " + relative + " (no matching input case)\n")
            failures += 1
    out.write(
        "golden: " + str(len(generated)) + " case(s), " + str(failures) + " problem(s)\n"
    )
    return 1 if failures else 0


def write(root, out):
    generated = render(root)
    for relative in _existing(root):
        if relative not in generated:
            os.remove(os.path.join(root, relative))
            out.write("REMOVED  " + relative + "\n")
    for relative in sorted(generated):
        path = os.path.join(root, relative)
        directory = os.path.dirname(path)
        if not os.path.isdir(directory):
            os.makedirs(directory)
        with open(path, "wb") as handle:
            handle.write(generated[relative])
        out.write("WROTE    " + relative + "\n")
    out.write("golden: " + str(len(generated)) + " case(s) written\n")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate golden cases from the independent oracle.")
    parser.add_argument("--check", action="store_true", help="compare only, do not write")
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    args = parser.parse_args(argv)

    try:
        if args.check:
            return check(args.root, sys.stdout)
        return write(args.root, sys.stdout)
    except (CaseError, ToolError) as exc:
        sys.stderr.write("case error: " + str(exc) + "\n")
        return 2


if __name__ == "__main__":
    sys.exit(main())
