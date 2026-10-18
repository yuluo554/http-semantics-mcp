"""Entry point: ``python -m http_semantics_mcp`` / ``http-semantics-mcp``.

Modes (plan/02 section 1, decision D26):

* default / ``serve``  -- run the MCP stdio server
* ``--version``        -- print one version line and exit 0
* ``--selftest``       -- run in-process checks, exit 0 on pass / 1 on fail

There is deliberately **no** judgement subcommand: judgement is reachable only
through ``tools/call`` so there is exactly one contract.

Exit codes: 0 success, 1 selftest found a failure, 2 usage error.
"""

import argparse
import sys

from . import __version__
from ._utf8 import ensure_utf8_stdio
from .server import serve
from .selfcheck import main as selftest_main

__all__ = ["build_parser", "main"]


def build_parser():
    parser = argparse.ArgumentParser(
        prog="http-semantics-mcp",
        description=(
            "Deterministic HTTP semantics judgement MCP server (stdio). "
            "Run with no arguments and speak MCP on stdin/stdout."
        ),
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print the package version and exit",
    )
    parser.add_argument(
        "--selftest",
        action="store_true",
        help="run in-process self-checks and exit (0 pass / 1 fail)",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="serve",
        choices=["serve"],
        help="only 'serve' is accepted; it is the default",
    )
    return parser


def main(argv=None):
    ensure_utf8_stdio()
    args = build_parser().parse_args(argv)

    if args.version:
        sys.stdout.write(__version__ + "\n")
        sys.stdout.flush()
        return 0

    if args.selftest:
        return selftest_main(sys.stdout)

    return serve()


if __name__ == "__main__":
    sys.exit(main())
