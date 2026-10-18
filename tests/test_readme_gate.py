"""README surface parity: every claim in the README has a real object.

Checks three surfaces against each other:

* README commands and flags  <->  the CLI parser (by reflection)
* README extras              <->  ``pyproject.toml``
* README file references     <->  existing files

This is the gate that catches "the README tells the reader to run something the
code cannot do" — the failure mode that stays green through every milestone
because no test reads the documentation.
"""

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")
PYPROJECT = os.path.join(ROOT, "pyproject.toml")

FLAG = re.compile(r"--[a-z][a-z0-9-]+")

# Repository-relative path claims: only tokens that name a *file* are checked.
# Method names such as `tools/list` share the prefix but are not paths.
FILE_EXTENSIONS = (".py", ".md", ".json", ".toml", ".yml", ".yaml", ".txt")


def _readme():
    with open(README, "r", encoding="utf-8") as handle:
        return handle.read()


def _fenced_lines(text):
    """Yield lines inside ``` blocks, which is where commands live."""
    inside = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            inside = not inside
            continue
        if inside:
            yield line


def _flags_for(program):
    sys.path.insert(0, os.path.join(ROOT, "src"))
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    sys.path.insert(0, os.path.join(ROOT, "tools"))
    try:
        if program == "entry":
            from http_semantics_mcp.__main__ import build_parser

            return {option for action in build_parser()._actions for option in action.option_strings}
        if program == "release":
            import check_release

            return _parser_flags_of(check_release.main)
        if program == "smoke":
            import smoke_stdio

            return _parser_flags_of(smoke_stdio.main)
    finally:
        for _ in range(3):
            sys.path.pop(0)
    raise AssertionError("unknown program " + program)


def _parser_flags_of(main):
    """Read the flags a module's argparse surface accepts, by calling it."""
    import argparse
    import contextlib
    import io

    captured = {}
    original = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["parser"] = self
        raise SystemExit(0)

    argparse.ArgumentParser.parse_args = spy
    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            main(["--help"])
    except SystemExit:
        pass
    finally:
        argparse.ArgumentParser.parse_args = original

    parser = captured.get("parser")
    assert parser is not None, "could not introspect the parser"
    return {option for action in parser._actions for option in action.option_strings}


def _documented_flags_by_program(text):
    """Associate each documented flag with the program its line invokes.

    Scanning the whole README for flags and comparing against one parser is
    the mistake this function exists to avoid: it would flag a valid
    ``check_release.py --pre-tag`` as an unknown entry-point flag.
    """
    found = {"entry": set(), "release": set(), "smoke": set()}
    for line in _fenced_lines(text):
        if "check_release.py" in line:
            key = "release"
        elif "smoke_stdio.py" in line:
            key = "smoke"
        elif "http_semantics_mcp" in line or "http-semantics-mcp" in line:
            key = "entry"
        else:
            continue
        found[key].update(FLAG.findall(line))
    for flags in found.values():
        flags.discard("--help")
    return found


def test_every_readme_flag_exists_in_the_program_it_invokes():
    documented = _documented_flags_by_program(_readme())
    problems = []
    for program, flags in sorted(documented.items()):
        known = _flags_for(program)
        unknown = sorted(flags - known)
        if unknown:
            problems.append(program + ": " + ", ".join(unknown))
    assert problems == [], "README documents flags the program does not accept: " + "; ".join(problems)


def test_every_entry_flag_is_documented():
    """A flag a reader cannot discover is a flag that does not exist for them."""
    documented = _documented_flags_by_program(_readme())["entry"]
    missing = sorted(_flags_for("entry") - documented - {"-h", "--help"})
    assert missing == [], "CLI flags missing from README: " + ", ".join(missing)


def test_readme_install_line_matches_pyproject_extras():
    text = _readme()
    extras = set(re.findall(r'\.\[([a-z,]+)\]', text))
    declared = set()
    in_optional = False
    with open(PYPROJECT, "r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped.startswith("[project.optional-dependencies]"):
                in_optional = True
                continue
            if stripped.startswith("[") and in_optional:
                in_optional = False
            if in_optional and "=" in stripped and not stripped.startswith("#"):
                declared.add(stripped.split("=", 1)[0].strip())
    if extras:
        assert extras <= declared, "README uses undeclared extras: " + str(sorted(extras - declared))


def test_readme_referenced_repo_files_exist():
    """Only *file* claims are checked; protocol method names are not paths."""
    text = _readme()
    candidates = set(re.findall(r"`((?:plan|data|schemas|references|tools|scripts|src)/[^`]+)`", text))
    candidates |= set(re.findall(r"\]\(((?:plan|data|schemas|references|tools|scripts|src)/[^)]+)\)", text))

    checked = 0
    missing = []
    for candidate in sorted(candidates):
        token = candidate.split("#")[0].split()[0].rstrip("/")
        if not token.endswith(FILE_EXTENSIONS):
            continue
        checked += 1
        if not os.path.exists(os.path.join(ROOT, token)):
            missing.append(token)

    assert checked > 0, "README gate found no file claims to check (probe is broken)"
    assert missing == [], "README points at files that do not exist: " + ", ".join(missing)


def test_readme_state_matches_the_registry():
    """The README must describe the tools that actually exist, in both directions.

    While the registry was empty the README had to say so; now that tools are
    registered it must name them and must not still claim an empty list.
    """
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from http_semantics_mcp.registry import build_registry
    finally:
        sys.path.pop(0)

    registry = build_registry()
    text = _readme()
    if len(registry) == 0:
        assert "zero tools" in text.lower()
        assert "returns `[]`" in text
        return

    assert "zero tools" not in text.lower()
    assert "returns `[]`" not in text
    for name in registry.names():
        assert "`" + name + "`" in text, "README does not name registered tool " + name


def test_readme_does_not_describe_a_cli_judgement_command():
    """Decision D26: judgement is reachable only through MCP."""
    text = _readme().lower()
    for forbidden in ("cors-eval", "cache-eval", "judge ", "--headers"):
        assert forbidden not in text


def test_readme_claims_mit_and_license_exists():
    text = _readme()
    assert "MIT" in text
    assert os.path.isfile(os.path.join(ROOT, "LICENSE"))
