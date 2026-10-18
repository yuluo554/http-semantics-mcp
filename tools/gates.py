"""Static gates shared by tests and the release check.

Why a separate module: the same judgement must not exist twice. Tests call
these functions directly; ``scripts/check_release.py`` imports them by path
(no pytest dependency) so the release gate can run in a clean clone.

Every gate returns a :class:`Report` that always says **how many files were
scanned**. A gate that scanned nothing must never look like a gate that found
nothing -- that is the failure mode this reporting shape exists to prevent.
"""

import ast
import json
import os
import re

__all__ = [
    "Report",
    "scan_tree",
    "text_files",
    "purity",
    "no_nondeterminism",
    "single_serialiser",
    "absolute_paths",
    "crlf",
    "oracle_independence",
    "golden_hygiene",
    "code_literals",
    "all_reports",
]

TEXT_SUFFIXES = (
    ".py",
    ".md",
    ".toml",
    ".yml",
    ".yaml",
    ".json",
    ".txt",
    ".cfg",
    ".in",
    ".gitattributes",
    ".gitignore",
)

SKIP_DIRS = (
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "build",
    "dist",
    ".eggs",
)

# Modules the judgement layer must never import (plan/02 section 2).
JUDGEMENT_FORBIDDEN = (
    "time",
    "datetime",
    "random",
    "secrets",
    "socket",
    "ssl",
    "http",
    "urllib",
    "requests",
    "os",
    "subprocess",
    "sys",
    "pathlib",
    "shutil",
    "tempfile",
    "uuid",
)

# Judgement must not reach up into transport or dispatch.
JUDGEMENT_FORBIDDEN_RELATIVE = ("server", "protocol", "registry", "selfcheck", "canonical")


# The whole runtime package must stay free of clock, randomness and network.
# The judgement layer has its own, stricter list above.
PACKAGE_FORBIDDEN = (
    "time",
    "datetime",
    "random",
    "secrets",
    "uuid",
    "socket",
    "ssl",
    "urllib",
    "requests",
)

# ``os`` is allowed outside the judgement layer (selfcheck locates
# pyproject.toml), but reading the environment is not: environment variables
# turn "same input, same output" into "same input, same machine".
ENV_CALLS = ("environ", "getenv", "putenv")


class Report(object):
    """Outcome of one gate run."""

    def __init__(self, name):
        self.name = name
        self.scanned = 0
        self.findings = []

    def add(self, path, detail):
        self.findings.append((path, detail))

    @property
    def ok(self):
        return not self.findings

    def summary(self):
        state = "PASS" if self.ok else "FAIL"
        return "{0}: {1} ({2} files scanned, {3} findings)".format(
            self.name, state, self.scanned, len(self.findings)
        )

    def __repr__(self):
        return "<Report {0}>".format(self.summary())


def _relative(root, path):
    return os.path.relpath(path, root).replace(os.sep, "/")


def scan_tree(root, suffixes=TEXT_SUFFIXES, skip_dirs=SKIP_DIRS):
    """Yield text-file paths under ``root``, skipping generated directories."""
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in skip_dirs)
        for filename in sorted(filenames):
            if filename.endswith(suffixes) or filename in (".gitattributes", ".gitignore"):
                yield os.path.join(current, filename)


def text_files(root):
    """Return ``[(relative_path, text)]`` decoded as UTF-8."""
    result = []
    for path in scan_tree(root):
        with open(path, "rb") as handle:
            raw = handle.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            result.append((_relative(root, path), None))
            continue
        result.append((_relative(root, path), text))
    return result


def _imported_modules(tree):
    """Collect absolute and relative imports, including inside functions.

    Returns both the full dotted name and each of its segments. Segment-level
    matching is what catches ``from http_semantics_mcp.server import serve``
    (the forbidden name lives in the tail, not the head) and relative imports
    such as ``from .. import server``.
    """
    modules = set()

    def add(name):
        if not name:
            return
        modules.add(name.split(".")[0])
        modules.add(name.split(".")[-1])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            add(node.module)
            for alias in node.names:
                add(alias.name)
    return modules


def purity(root):
    """Judgement layer must be a pure function: no clock, network, env, disk.

    Scans every ``*.py`` under ``src/http_semantics_mcp/judgement``.

    The forbidden list is imported from this module rather than repeated in
    the test, so adding an entry protects every consumer at once.
    """
    report = Report("purity")
    base = os.path.join(root, "src", "http_semantics_mcp", "judgement")
    if not os.path.isdir(base):
        report.add("src/http_semantics_mcp/judgement", "directory is missing")
        return report

    for path in sorted(scan_tree(base, suffixes=(".py",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            report.add(relative, "syntax error: " + str(exc))
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                function = node.func
                name = getattr(function, "id", None) or getattr(function, "attr", None)
                if name in ("open", "read_text", "read_bytes", "write_text", "write_bytes"):
                    report.add(relative, "disk access via " + name)

        for module in sorted(_imported_modules(tree)):
            if module in JUDGEMENT_FORBIDDEN:
                report.add(relative, "forbidden import: " + module)
            elif module in JUDGEMENT_FORBIDDEN_RELATIVE:
                report.add(relative, "judgement must not reach " + module)
    return report


def _path_patterns():
    """Build the absolute-path probes from pieces.

    Keeping the literals out of the source means this file does not match its
    own scan, and a grep over the repository for the probe cannot be mistaken
    for a leak.

    The drive-letter probe needs the lookbehind: without it the scheme part of
    a URL becomes a false positive, because a single-letter scheme followed by
    a slash is indistinguishable from a drive letter.

    The UNC probe requires **two** components (``\\\\server\\share``). A single
    component would match ordinary source escapes such as ``\\\\r\\\\n`` in a
    Python string literal, which is not a path at all.
    """
    drive = "(?<![A-Za-z0-9])[A-Za-z]:" + "[\\\\/]"
    name = "[A-Za-z0-9._-]{2,}"
    return (
        ("windows-drive", drive),
        ("posix-user-home", "/" + "Users/"),
        ("posix-home", "/" + "home/"),
        ("unc", "\\\\\\\\" + name + "\\\\" + name),
    )


def absolute_paths(root, extra_allow=()):
    """Report machine-specific absolute paths in repository text files.

    Only machine-specific forms are probe targets: a Windows drive path, a
    POSIX home directory, or a UNC share. Repository-relative paths and URLs
    are fine.
    """
    import re

    report = Report("absolute-paths")
    patterns = [(label, re.compile(pattern)) for label, pattern in _path_patterns()]
    allow = set(extra_allow)

    for relative, text in text_files(root):
        if relative in allow:
            continue
        if text is None:
            continue
        report.scanned += 1
        for label, pattern in patterns:
            if pattern.search(text):
                report.add(relative, "machine-specific path (" + label + ")")
                break
    return report


def crlf(root):
    """Text files must be LF-only and ``.gitattributes`` must be in place."""
    report = Report("crlf")
    for relative, text in text_files(root):
        report.scanned += 1
        if text is None:
            continue
        if "\r\n" in text or "\r" in text:
            report.add(relative, "carriage return present")

    attributes = os.path.join(root, ".gitattributes")
    if not os.path.isfile(attributes):
        report.add(".gitattributes", "missing")
    else:
        with open(attributes, "rb") as handle:
            content = handle.read().decode("utf-8")
        if "eol=lf" not in content:
            report.add(".gitattributes", "does not declare eol=lf")
    return report


def no_nondeterminism(root):
    """The whole runtime package: no clock, no randomness, no network, no env.

    Stricter than it looks and intentionally so: the transport layer may read
    bytes, but it may not consult the machine it is running on. ``os`` is
    permitted for path handling (the self-check locates ``pyproject.toml``),
    but ``os.environ`` / ``getenv`` are not -- an environment variable turns
    "same input, same output" into "same input, same machine".
    """
    report = Report("no-nondeterminism")
    base = os.path.join(root, "src", "http_semantics_mcp")
    if not os.path.isdir(base):
        report.add("src/http_semantics_mcp", "directory is missing")
        return report

    for path in sorted(scan_tree(base, suffixes=(".py",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            report.add(relative, "syntax error: " + str(exc))
            continue

        for module in sorted(_imported_modules(tree)):
            if module in PACKAGE_FORBIDDEN:
                report.add(relative, "forbidden import: " + module)

        for node in ast.walk(tree):
            if isinstance(node, ast.Attribute) and node.attr in ENV_CALLS:
                report.add(relative, "environment read: " + node.attr)
            elif isinstance(node, ast.Call):
                function = node.func
                name = getattr(function, "id", None) or getattr(function, "attr", None)
                if name in ("urandom", "getrandbits", "random"):
                    report.add(relative, "randomness: " + name)
    return report


def single_serialiser(root):
    """``json.dumps`` may appear exactly once, in ``canonical.py``.

    Two serialisation sites is how a project ends up with one endpoint emitting
    sorted keys and another emitting insertion order, which quietly breaks the
    byte-identical promise.
    """
    report = Report("single-serialiser")
    base = os.path.join(root, "src", "http_semantics_mcp")
    if not os.path.isdir(base):
        report.add("src/http_semantics_mcp", "directory is missing")
        return report

    canonical_path = os.path.join(base, "canonical.py")
    allowed = os.path.normcase(os.path.abspath(canonical_path))
    sites = 0

    for path in sorted(scan_tree(base, suffixes=(".py",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            report.add(relative, "syntax error: " + str(exc))
            continue

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            function = node.func
            if getattr(function, "attr", None) != "dumps":
                continue
            owner = getattr(function, "value", None)
            if getattr(owner, "id", None) != "json":
                continue
            sites += 1
            if os.path.normcase(os.path.abspath(path)) != allowed:
                report.add(relative, "json.dumps outside canonical.py")

    if sites == 0:
        report.add("src/http_semantics_mcp/canonical.py", "no json.dumps found (probe is broken)")
    return report


ORACLE_DIR = ("tools", "golden_oracle")

# The oracle must be an independent second implementation (decision D27).
# Importing the package at all would let a production bug produce a matching
# expectation, which is the one failure mode this whole arrangement exists to
# prevent. The check is name-based, so it also catches dynamic imports.
ORACLE_FORBIDDEN = ("http_semantics_mcp",)

# A rule code may only be spelled in the generated catalog. Any other `.py` in
# the package spelling one out is a second copy waiting to drift.
CODE_LITERAL = re.compile(r"\b(?:CORS|CACHE|COND|VARY)_[A-Z0-9_]+\b")

# The generated Python form of the catalogue (decision D41): the judgement layer
# imports one constant per rule code instead of spelling it. It is the same
# generated artifact as ``references/codes.json``, so it is the one file the
# literal gate must not flag -- and it must exist, or the exemption would be a
# silent hole in a gate that then finds nothing.
GENERATED_CODE_MODULE = os.path.join("src", "http_semantics_mcp", "rules.py")

# Fields that would turn a frozen expectation into an observation.
OBSERVED_PREFIX = "observed_"


def oracle_independence(root):
    """``tools/golden_oracle/`` must not import the implementation under test.

    Scanned with the AST, not by looking for the string: a comment saying
    "do not import http_semantics_mcp" is fine, an ``import`` inside a
    function is not.
    """
    report = Report("oracle-independence")
    base = os.path.join(root, *ORACLE_DIR)
    if not os.path.isdir(base):
        report.add("/".join(ORACLE_DIR), "directory is missing")
        return report

    for path in sorted(scan_tree(base, suffixes=(".py",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            report.add(relative, "syntax error: " + str(exc))
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in ORACLE_FORBIDDEN:
                        report.add(relative, "oracle imports the implementation: " + alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.split(".")[0] in ORACLE_FORBIDDEN:
                    report.add(relative, "oracle imports the implementation: " + module)
                for alias in node.names:
                    if alias.name in ORACLE_FORBIDDEN:
                        report.add(relative, "oracle imports the implementation: " + alias.name)
            elif isinstance(node, ast.Call):
                function = node.func
                name = getattr(function, "id", None) or getattr(function, "attr", None)
                if name in ("import_module", "__import__"):
                    for argument in node.args:
                        if isinstance(argument, ast.Constant) and argument.value in ORACLE_FORBIDDEN:
                            report.add(relative, "oracle imports the implementation dynamically")
    return report


def golden_hygiene(root):
    """Golden cases carry inputs and expectations, never observations.

    Two rules (plan/04 section 3):

    * no key starting with ``observed_`` anywhere in a frozen case;
    * no key called ``expected`` inside ``tools/cases`` (the oracle owns it).

    The gate also refuses an empty ``data/golden``: scanning zero files and
    finding zero problems must not look like success.
    """
    report = Report("golden-hygiene")
    golden = os.path.join(root, "data", "golden")
    if not os.path.isdir(golden):
        report.add("data/golden", "directory is missing")
        return report

    def walk(value, relative):
        if isinstance(value, dict):
            for key in value:
                if key.startswith(OBSERVED_PREFIX):
                    report.add(relative, "observed field: " + key)
            for item in value.values():
                walk(item, relative)
        elif isinstance(value, list):
            for item in value:
                walk(item, relative)

    for path in sorted(scan_tree(golden, suffixes=(".json",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            raw = handle.read()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, ValueError):
            report.add(relative, "not valid UTF-8 JSON")
            continue
        walk(payload, relative)
        if not isinstance(payload, dict):
            report.add(relative, "case must be a JSON object")
            continue
        for key in ("case_id", "tool", "input", "expected", "spec_basis", "source"):
            if key not in payload:
                report.add(relative, "missing " + key)

    if report.scanned == 0:
        report.add("data/golden", "no golden case found")
    return report


def code_literals(root):
    """Rule codes live in the generated catalogue only, never in hand-written code.

    Templates, ``spec_ref`` and severity are read from the generated catalogue;
    a literal ``CORS_...`` in Python would be a second source of truth and the
    first thing to drift. This gate scans every ``*.py`` under ``src/``, with a
    single exempt path: the generated rule module (``rules.py``), whose whole
    purpose is to hold those literals so the judgement layer can import names.

    The exempted file must be present and non-empty -- an exemption that hides a
    missing artifact would turn this gate into a check that scans nothing.
    """
    report = Report("code-literals")
    base = os.path.join(root, "src", "http_semantics_mcp")
    if not os.path.isdir(base):
        report.add("src/http_semantics_mcp", "directory is missing")
        return report

    generated = os.path.normcase(os.path.abspath(os.path.join(root, GENERATED_CODE_MODULE)))
    if not os.path.isfile(generated):
        report.add(GENERATED_CODE_MODULE, "generated rule module is missing")
    else:
        with open(generated, "rb") as handle:
            if b"CATALOG = {" not in handle.read():
                report.add(GENERATED_CODE_MODULE, "generated rule module has no CATALOG")

    for path in sorted(scan_tree(base, suffixes=(".py",), skip_dirs=SKIP_DIRS)):
        report.scanned += 1
        if os.path.normcase(os.path.abspath(path)) == generated:
            continue
        relative = _relative(root, path)
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
        try:
            tree = ast.parse(source, filename=path)
        except SyntaxError as exc:
            report.add(relative, "syntax error: " + str(exc))
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if CODE_LITERAL.fullmatch(node.value):
                    report.add(relative, "code literal: " + node.value)
    return report


def all_reports(root):
    """Run every gate and return the list of reports."""
    return [
        purity(root),
        no_nondeterminism(root),
        single_serialiser(root),
        absolute_paths(root),
        crlf(root),
        oracle_independence(root),
        golden_hygiene(root),
        code_literals(root),
    ]
