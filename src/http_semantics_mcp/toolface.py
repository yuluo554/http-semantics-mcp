"""The tool face: judgement output, rendered as an MCP tool result.

Two rules from ``data/README.md`` section 4.6 meet here:

* a *tool-level* bad input is a result with ``isError: true`` whose payload is
  ``{"error": {"code", "field", "detail"}}`` -- not a JSON-RPC error, and never
  a traceback that would end the session;
* ``decision: "block"`` is a successful judgement, so it keeps ``isError: false``.

The judgement layer never serialises and never writes: it returns an object.
This module owns the single rendering step (``canonical.dumps``) and the one
place where a caller mistake becomes a payload.
"""

from . import canonical
from .judgement import errors as judgement_errors
from .judgement.cache import evaluate_cache
from .judgement.conditional import evaluate_conditional
from .judgement.cors import evaluate_cors
from .judgement.fetch_sim import evaluate_fetch
from .judgement.vary import evaluate_vary
from .rules import CATALOG

__all__ = ["FUNCTIONS", "handlers", "render"]

# Tool name -> pure judgement function. Names are data here, not dispatch
# logic; the registry is the single place that declares the client-visible
# descriptors.
FUNCTIONS = {
    "cache_evaluate": evaluate_cache,
    "conditional_evaluate": evaluate_conditional,
    "cors_evaluate": evaluate_cors,
    "cors_simulate_fetch": evaluate_fetch,
    "vary_match": evaluate_vary,
}


def render(payload, is_error=False):
    """Wrap a judgement object (or an error payload) as an MCP tool result.

    The same object is handed over twice: serialised once as the compatibility
    ``text`` part, and once as ``structuredContent``. Every published tool
    carries an ``outputSchema``, and the specification says a server that
    publishes one **MUST** also return structured results conforming to it.

    Reusing ``payload`` (not a copy, and certainly not a second
    ``json.dumps``) keeps one serialiser in the package and makes "the text
    and the structured value never drift" true by construction; the test suite
    still asserts the byte equality.

    On the error branch ``payload`` is already ``{"error": {...}}``, which is
    what ``isError: true`` clients expect; the schema does not apply there.
    """
    return {
        "content": [{"type": "text", "text": canonical.dumps(payload)}],
        "structuredContent": payload,
        "isError": is_error,
    }


def _handler(function):
    def call(arguments):
        try:
            return render(function(arguments, CATALOG))
        except judgement_errors.JudgementError as error:
            return render(error.payload(), is_error=True)

    return call


def handlers():
    """Return ``{tool_name: callable(arguments) -> tool result}``."""
    return {name: _handler(function) for name, function in FUNCTIONS.items()}
