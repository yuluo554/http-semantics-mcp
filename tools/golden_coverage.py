"""Coverage report: the code enum versus the frozen golden cases.

The rule is a set equality in both directions (plan/04 section 4):

    set(codes.json) - set(codes used by goldens) == empty
    set(codes used by goldens) - set(codes.json)      == empty

Findings can be nested (``hops[].violations[]``), so the walk is recursive
rather than keyed on three known field names -- a flat scan would have missed
every redirect case.
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

GOLDEN = os.path.join("data", "golden")
CODES = os.path.join("src", "http_semantics_mcp", "references", "codes.json")
TOOLS = (
    "cors_evaluate",
    "cors_simulate_fetch",
    "cache_evaluate",
    "conditional_evaluate",
    "vary_match",
)


def load_codes(root):
    with open(os.path.join(root, CODES), "r", encoding="utf-8") as handle:
        return json.load(handle)["codes"]


def iter_cases(root):
    """Yield ``(tool, case_id, case)`` for every frozen golden case."""
    base = os.path.join(root, GOLDEN)
    for tool in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        directory = os.path.join(base, tool)
        if not os.path.isdir(directory):
            continue
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(directory, name)
            with open(path, "r", encoding="utf-8") as handle:
                yield tool, name[: -len(".json")], json.load(handle)


def _walk(value, found):
    if isinstance(value, dict):
        code = value.get("code")
        if isinstance(code, str) and code.isupper() and "_" in code:
            found.add(code)
        for key, item in value.items():
            # ``{"error": {"code": ...}}`` carries a tool-level error code from
            # section 4.6, not a rule code. Mixing the two namespaces would
            # make the set equality vacuous in one direction and loud in the
            # other.
            if key == "error" and isinstance(item, dict):
                continue
            _walk(item, found)
    elif isinstance(value, list):
        for item in value:
            _walk(item, found)


def coverage(root):
    """Return ``(codes, used, per_code)`` with ``per_code`` mapping code -> case ids."""
    codes = load_codes(root)
    per_code = {}
    for _tool, case_id, case in iter_cases(root):
        found = set()
        _walk(case.get("expected"), found)
        for code in found:
            per_code.setdefault(code, []).append(case_id)
    return set(codes), set(per_code), per_code


def report(root, out):
    codes, used, per_code = coverage(root)
    missing = sorted(codes - used)
    extra = sorted(used - codes)

    width = max([len(code) for code in codes] or [1])
    for code in sorted(codes):
        cases = per_code.get(code, [])
        out.write(
            "{0:<{1}}  {2:>3}  {3}\n".format(code, width, len(cases), ", ".join(cases[:3]))
        )

    out.write(
        "codes: {0} declared, {1} covered, {2} uncovered; {3} unknown code(s) in goldens\n".format(
            len(codes), len(codes & used), len(missing), len(extra)
        )
    )
    if missing:
        out.write("uncovered: " + ", ".join(missing) + "\n")
    if extra:
        out.write("unknown:   " + ", ".join(extra) + "\n")
    return 1 if (missing or extra) else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Golden coverage against the code enum.")
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    args = parser.parse_args(argv)
    return report(args.root, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
