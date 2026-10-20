"""CI workflow file: parses, has the expected shape, and cannot silently skip.

A workflow that fails to parse creates no jobs at all, and the run still shows
``failure`` -- so "the file exists" is not evidence. These tests parse the YAML
locally and assert structure.
"""

import os
import sys

import pytest
import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "ci.yml")
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import toml_lite  # noqa: E402


def _workflow():
    with open(WORKFLOW, "r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _requires_python():
    """The floor as a bare version, e.g. ``>=3.12`` -> ``3.12``."""
    declared = toml_lite.load(os.path.join(ROOT, "pyproject.toml"))["project"]["requires-python"]
    return declared.lstrip("=>= ").strip()


def test_workflow_parses():
    assert isinstance(_workflow(), dict)


def test_workflow_has_one_test_job_across_both_operating_systems():
    data = _workflow()
    jobs = data["jobs"]
    assert list(jobs) == ["test"]

    job = jobs["test"]
    matrix = job["strategy"]["matrix"]
    assert set(matrix["os"]) == {"ubuntu-latest", "windows-latest"}
    assert job["strategy"]["fail-fast"] is False


def test_the_matrix_python_floor_matches_requires_python():
    """Two places state the supported interpreter; they must not drift.

    A matrix leg older than ``requires-python`` cannot install the package, and
    a floor newer than every leg means CI never exercises the declared range.
    """
    matrix = set(_workflow()["jobs"]["test"]["strategy"]["matrix"]["python"])
    floor = _requires_python()
    assert matrix == {floor}, "matrix " + str(sorted(matrix)) + " != floor " + floor


def test_every_step_has_a_name():
    """Step names must be quoted scalars in the file; asserting on parsed
    names catches the "unquoted ': ' broke the whole workflow" failure mode."""
    for step in _workflow()["jobs"]["test"]["steps"]:
        assert isinstance(step.get("name"), str) and step["name"].strip()


def test_required_steps_are_present():
    names = [step["name"] for step in _workflow()["jobs"]["test"]["steps"]]
    required = [
        "Checkout",
        "Set up Python",
        "Install (runtime + dev extras)",
        "Version and self-test",
        "Console script smoke",
        "Repository gates",
        "Generated data is reproducible",
        "Mutation verification",
        "stdio handshake smoke",
        "Full test suite",
    ]
    for expected in required:
        assert expected in names, "missing CI step: " + expected


def test_step_names_do_not_use_unquoted_colons():
    """Belt and braces: the parse above would fail, but name the cause."""
    with open(WORKFLOW, "r", encoding="utf-8") as handle:
        for number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped.startswith("name:"):
                continue
            value = stripped[len("name:"):].strip()
            quoted = value.startswith('"') or value.startswith("'")
            if not quoted:
                assert ": " not in value, "unquoted colon in step name at line " + str(number)


def test_no_continue_on_error_on_a_verification_step():
    """A verification step allowed to fail is a green matrix that proves nothing."""
    for step in _workflow()["jobs"]["test"]["steps"]:
        assert step.get("continue-on-error") is not True, step.get("name")


def test_ci_does_not_run_the_release_terminal_gate():
    """Decision D34: before a tag it is legitimately red, so it stays out."""
    with open(WORKFLOW, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert "check_release" not in text


def test_ci_installs_the_same_extras_the_readme_documents():
    with open(WORKFLOW, "r", encoding="utf-8") as handle:
        text = handle.read()
    assert 'pip install -e ".[dev]"' in text


def test_ci_sets_utf8_environment():
    data = _workflow()
    environment = data["jobs"]["test"].get("env", {})
    assert environment.get("PYTHONUTF8") == "1"
    assert str(environment.get("PYTHONIOENCODING")).lower() == "utf-8"
