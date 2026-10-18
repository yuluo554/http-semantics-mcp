"""Package layout and installation-surface parity.

Four surfaces, checked together because checking them one at a time is how a
package ends up importable from the repository root but not from the installed
distribution:

1. declared runtime dependencies are empty
2. ``package-dir`` resolves to a directory that really exists
3. every declared package directory contains an ``__init__.py``
4. the console script target is importable and callable
"""

import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src")
TOOLS = os.path.join(ROOT, "tools")
PYPROJECT = os.path.join(ROOT, "pyproject.toml")

if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import toml_lite  # noqa: E402


def _read_pyproject():
    # A single reader for both interpreters: tomllib is 3.11+, and the project
    # floor is 3.8. The test uses the same parser CI's gates would.
    return toml_lite.load(PYPROJECT)


def test_runtime_dependencies_are_empty():
    data = _read_pyproject()
    dependencies = data.get("project", {}).get("dependencies", [])
    if isinstance(dependencies, str):
        assert dependencies.strip() == ""
    else:
        assert dependencies == [], dependencies


def test_dev_extra_declares_test_dependencies():
    data = _read_pyproject()
    optional = data.get("project", {}).get("optional-dependencies", {})
    dev = optional.get("dev", "")
    text = dev if isinstance(dev, str) else " ".join(dev)
    assert "pytest" in text
    assert "PyYAML" in text


def test_package_dir_resolves_to_an_existing_directory():
    data = _read_pyproject()
    package_dir = data.get("tool", {}).get("setuptools", {}).get("package-dir", {})
    root = package_dir.get("", "") if isinstance(package_dir, dict) else ""
    assert root, "package-dir is not declared"
    resolved = os.path.join(ROOT, root)
    assert os.path.isdir(resolved), resolved
    assert os.path.isdir(os.path.join(resolved, "http_semantics_mcp"))


def test_every_package_directory_has_an_init():
    base = os.path.join(SRC, "http_semantics_mcp")
    for current, dirnames, _ in os.walk(base):
        dirnames[:] = [name for name in dirnames if name not in ("__pycache__",)]
        for name in dirnames:
            # A directory of data files (schemas/, references/) is not a package.
            candidate = os.path.join(current, name)
            has_python = any(entry.endswith(".py") for entry in os.listdir(candidate))
            if has_python:
                assert os.path.isfile(os.path.join(candidate, "__init__.py")), candidate


def test_console_script_target_is_callable():
    sys.path.insert(0, SRC)
    try:
        from http_semantics_mcp.__main__ import main
    finally:
        sys.path.pop(0)
    assert callable(main)


def test_no_third_party_imports_in_runtime_package():
    """The runtime package must import only the standard library and itself."""
    allowed_third_party = set()
    stdlib = _stdlib_names()
    base = os.path.join(SRC, "http_semantics_mcp")

    for current, dirnames, filenames in os.walk(base):
        dirnames[:] = [name for name in dirnames if name != "__pycache__"]
        for filename in sorted(filenames):
            if not filename.endswith(".py"):
                continue
            path = os.path.join(current, filename)
            with open(path, "r", encoding="utf-8") as handle:
                tree = ast.parse(handle.read(), filename=path)
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name.split(".")[0] for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                    names = [node.module.split(".")[0]]
                for name in names:
                    if name in ("http_semantics_mcp",):
                        continue
                    assert name in stdlib or name in allowed_third_party, (
                        os.path.relpath(path, ROOT) + " imports " + name
                    )


def _stdlib_names():
    try:
        return set(sys.stdlib_module_names)  # Python 3.10+
    except AttributeError:
        # Frozen list: sys.stdlib_module_names does not exist on 3.8, and an
        # empty set there would classify every standard module as third party.
        return frozenset(
            """
            __future__ _thread abc argparse ast base64 binascii bisect builtins
            calendar codecs collections concurrent contextlib copy csv ctypes
            dataclasses datetime decimal difflib email encodings enum errno
            fnmatch fractions functools gc getpass gettext glob gzip hashlib
            heapq hmac html http importlib inspect io ipaddress itertools json
            keyword linecache locale logging math mimetypes numbers operator
            os pathlib pickle platform pprint pwd queue random re readline
            secrets select shlex shutil signal socket ssl stat string struct
            subprocess sys sysconfig tempfile textwrap threading time token
            tokenize traceback types typing unicodedata unittest urllib uuid
            warnings weakref xml zipfile zlib
            """.split()
        )
