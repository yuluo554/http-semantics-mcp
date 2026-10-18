"""Determinism guard: same input, same bytes -- and nothing from the machine.

``data/README.md`` section 4.5 freezes the promise: two consecutive calls on the
same input must serialise to the same sha256, and the output must not carry a
timestamp, a random value or an absolute path.

The double-run assertion is the core one. The content assertions are written so
they cannot pass vacuously and cannot fail on legitimate caller data:

* machine-specific path probes come from ``tools/gates.py`` (one definition,
  reused rather than re-spelled);
* a date-like token is allowed only when the caller's *input* contains it too --
  templates echo input values, and an echoed ``Expires`` is not a clock read.
"""

import hashlib
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gates  # noqa: E402
import golden_coverage  # noqa: E402

from http_semantics_mcp import canonical  # noqa: E402
from http_semantics_mcp.registry import build_registry  # noqa: E402

NON_TOOL = "_time"
DATE_TOKEN = re.compile(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?)?")


def _cases():
    return [
        (tool, case_id, case)
        for tool, case_id, case in golden_coverage.iter_cases(ROOT)
        if tool != NON_TOOL
    ]


def _digest(tool, arguments):
    registered = build_registry().get(tool)
    assert registered is not None, tool
    result = registered.handler(arguments)
    payload = json.loads(result["content"][0]["text"])
    text = canonical.dumps(payload)
    return hashlib.sha256(text.encode("utf-8")).hexdigest(), text


def test_two_runs_serialise_to_the_same_sha256():
    cases = _cases()
    assert cases, "no golden case found for the judgement tools"

    per_tool = {}
    for tool, case_id, case in cases:
        first, text = _digest(tool, case["input"])
        second, again = _digest(tool, case["input"])
        assert first == second, case_id
        assert text == again, case_id
        per_tool[tool] = per_tool.get(tool, 0) + 1

    # The gate must have covered each tool, not just one.
    for tool in build_registry().names():
        assert per_tool.get(tool, 0) > 0, "no case exercised " + tool


def test_output_carries_no_machine_specific_path():
    patterns = [(label, re.compile(pattern)) for label, pattern in gates._path_patterns()]
    for tool, case_id, case in _cases():
        _digest_value, text = _digest(tool, case["input"])
        for label, pattern in patterns:
            assert not pattern.search(text), case_id + " leaked a " + label + " path"


def test_output_holds_no_date_the_caller_did_not_supply():
    """A date the input never contained could only have come from a clock."""
    for tool, case_id, case in _cases():
        _digest_value, text = _digest(tool, case["input"])
        supplied = canonical.dumps(case["input"])
        for token in DATE_TOKEN.findall(text):
            assert token in supplied, case_id + " produced a date from nowhere: " + token


def test_serialisation_is_lf_only_and_unframed():
    for tool, case_id, case in _cases():
        _digest_value, text = _digest(tool, case["input"])
        assert "\r" not in text, case_id
        assert not text.endswith("\n"), case_id
