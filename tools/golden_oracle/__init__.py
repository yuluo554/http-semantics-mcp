"""Independent recomputer used to produce golden expectations.

This package is deliberately **not** the implementation under test. It is
written from the specifications in ``data/README.md`` section 4 and the
algorithms in ``plan/03``, and it must never import
``http_semantics_mcp`` (decision D27, gate ``oracle_independence``).

The production judgement layer is written separately in M2-M4; the only link
between the two is the byte-exact comparison of golden files.
"""

from .engine import evaluate, evaluate_time, load_catalog, TOOLS  # noqa: F401
from .errors import ToolError  # noqa: F401
