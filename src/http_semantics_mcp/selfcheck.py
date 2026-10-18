"""Self-checks for ``--selftest``.

Each check returns ``(status, detail)`` where status is ``PASS`` / ``FAIL`` /
``SKIP``. ``SKIP`` is used when the artefact being checked is not reachable in
this installation form (for example ``pyproject.toml`` in a wheel install) --
never to hide a failure.

Checks are deliberately limited to properties that hold in *every* build
state, so M0 passes with zero tools and M5 passes with five:

1. import surface: the package imports and exposes ``__version__``
2. serialisation: canonical output is stable across two calls
3. registry: names are unique and already in ASCII order
4. descriptors: every tool descriptor has the required MCP keys
5. protocol: initialize -> ping -> tools/list round trip works
6. version parity: package version equals ``pyproject.toml`` when reachable
"""

import os

from . import __version__, canonical, protocol
from .registry import build_registry

__all__ = ["run_checks", "main"]

_PASS = "PASS"
_FAIL = "FAIL"
_SKIP = "SKIP"


def _check_import():
    if not isinstance(__version__, str) or not __version__.strip():
        return _FAIL, "package __version__ is missing"
    return _PASS, "http_semantics_mcp " + __version__


def _check_serialisation():
    sample = {"b": [1, 2, 3], "a": {"y": True, "x": "值"}}
    first = canonical.encode_message(sample)
    second = canonical.encode_message(sample)
    if first != second:
        return _FAIL, "canonical serialisation is not stable across two calls"
    if b"\r" in first:
        return _FAIL, "canonical serialisation emitted a carriage return"
    if not first.endswith(b"\n") or first.count(b"\n") != 1:
        return _FAIL, "canonical framing must be exactly one trailing newline"
    return _PASS, "canonical output stable (" + str(len(first)) + " bytes)"


def _check_registry():
    registry = build_registry()
    names = registry.names()
    if names != sorted(names):
        return _FAIL, "registry names are not sorted"
    if len(set(names)) != len(names):
        return _FAIL, "registry contains duplicate names"
    return _PASS, str(len(names)) + " tool(s) registered"


def _check_descriptors():
    registry = build_registry()
    for descriptor in registry.descriptors():
        for key in ("name", "description", "inputSchema"):
            if key not in descriptor:
                return _FAIL, "descriptor " + descriptor.get("name", "?") + " lacks " + key
        if not isinstance(descriptor["inputSchema"], dict):
            return _FAIL, "inputSchema must be an object: " + descriptor["name"]
        if descriptor.get("description", "").lower().startswith("placeholder"):
            return _FAIL, "placeholder descriptor registered: " + descriptor["name"]
    return _PASS, "descriptors well formed"


def _check_protocol():
    session = protocol.Session()
    response = session.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18"}}
    )
    if len(response) != 1 or "result" not in response[0]:
        return _FAIL, "initialize did not return a result"
    if response[0]["result"]["serverInfo"]["version"] != __version__:
        return _FAIL, "initialize reports a version different from __version__"

    if session.handle({"jsonrpc": "2.0", "id": 2, "method": "ping"}) != [
        {"jsonrpc": "2.0", "id": 2, "result": {}}
    ]:
        return _FAIL, "ping did not return an empty result"

    listed = session.handle({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    if not listed or not isinstance(listed[0].get("result", {}).get("tools"), list):
        return _FAIL, "tools/list did not return a tools array"
    return _PASS, "initialize/ping/tools-list round trip"


def _find_pyproject():
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(4):
        candidate = os.path.join(here, "pyproject.toml")
        if os.path.isfile(candidate):
            return candidate
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    return None


def _check_version_parity():
    path = _find_pyproject()
    if path is None:
        return _SKIP, "pyproject.toml not present (installed form); cannot compare"
    declared = None
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                declared = stripped.split("=", 1)[1].strip().strip('"').strip("'")
                break
    if not declared:
        return _FAIL, "pyproject.toml has no version field"
    if declared != __version__:
        return _FAIL, "pyproject version " + declared + " != package version " + __version__
    return _PASS, "version parity " + declared


_CHECKS = (
    ("import", _check_import),
    ("serialisation", _check_serialisation),
    ("registry", _check_registry),
    ("descriptors", _check_descriptors),
    ("protocol", _check_protocol),
    ("version-parity", _check_version_parity),
)


def run_checks():
    """Run every check and return ``[(name, status, detail)]``."""
    results = []
    for name, check in _CHECKS:
        try:
            status, detail = check()
        except Exception as exc:  # noqa: BLE001 - a check must never crash the run
            status, detail = _FAIL, type(exc).__name__ + ": " + str(exc)
        results.append((name, status, detail))
    return results


def main(stream):
    """Print the check table to ``stream`` and return a process exit code."""
    results = run_checks()
    width = max(len(name) for name, _, _ in results) if results else 0
    for name, status, detail in results:
        stream.write("{0:<{1}}  {2:<4}  {3}\n".format(name, width, status, detail))
    failed = [name for name, status, _ in results if status == _FAIL]
    skipped = [name for name, status, _ in results if status == _SKIP]
    stream.write(
        "summary: {0} passed, {1} failed, {2} skipped\n".format(
            len(results) - len(failed) - len(skipped), len(failed), len(skipped)
        )
    )
    stream.flush()
    return 1 if failed else 0
