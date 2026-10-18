"""Dispatch for the independent recomputer.

The catalog passed in is the *generated* ``codes.json``: templates and
``spec_ref`` lists live in exactly one place, so the oracle and the generated
artifact cannot disagree about wording.
"""

import json
import os

from .cache import evaluate_cache
from .conditional import evaluate_conditional
from .cors import evaluate_cors
from .errors import ToolError, invalid_input
from .fetch_sim import evaluate_fetch
from .timeparse import parse_time
from .vary import evaluate_vary

__all__ = ["evaluate", "evaluate_time", "load_catalog", "TOOLS"]

TOOLS = {
    "cors_evaluate": evaluate_cors,
    "cors_simulate_fetch": evaluate_fetch,
    "cache_evaluate": evaluate_cache,
    "conditional_evaluate": evaluate_conditional,
    "vary_match": evaluate_vary,
}


def load_catalog(root):
    """Load the generated catalog from the in-package truth source."""
    path = os.path.join(root, "src", "http_semantics_mcp", "references", "codes.json")
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def evaluate_time(arguments, catalog):
    """Time-parsing sample: returns the parsed form or a structured error."""
    if not isinstance(arguments, dict):
        raise invalid_input("input", "time sample input must be an object")
    if "value" not in arguments:
        raise invalid_input("value", "value is required")
    form, timestamp = parse_time(arguments.get("value"), "value")
    return {"form": form, "timestamp": timestamp}


def evaluate(tool, arguments, catalog):
    """Run one case. Raises :class:`ToolError` for caller mistakes."""
    if tool == "_time":
        return evaluate_time(arguments, catalog)
    function = TOOLS.get(tool)
    if function is None:
        raise ToolError("INVALID_INPUT", "tool", "unknown tool: " + str(tool))
    return function(arguments, catalog)
