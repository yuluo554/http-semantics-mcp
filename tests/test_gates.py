"""Static gates, each with a mutation that must turn it red.

A gate that cannot be made to fail is not a gate. Every test here therefore has
two halves: the clean tree passes, and an injected defect fails.
"""

import os
import shutil
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gates  # noqa: E402

JUDGEMENT = os.path.join("src", "http_semantics_mcp", "judgement")


def _copy_repo(tmp_path):
    """Copy the parts the gates look at into a scratch tree."""
    target = tmp_path / "repo"
    target.mkdir()
    shutil.copytree(os.path.join(ROOT, "src"), target / "src")
    shutil.copytree(os.path.join(ROOT, "tools"), target / "tools")
    shutil.copytree(os.path.join(ROOT, "data"), target / "data")
    shutil.copy(os.path.join(ROOT, ".gitattributes"), target / ".gitattributes")
    shutil.copy(os.path.join(ROOT, "pyproject.toml"), target / "pyproject.toml")
    return str(target)


# -- purity ---------------------------------------------------------------


def test_purity_passes_on_the_clean_tree():
    report = gates.purity(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0, "purity gate scanned nothing"


def test_purity_catches_a_clock_read(tmp_path):
    root = _copy_repo(tmp_path)
    module = os.path.join(root, JUDGEMENT, "leaky.py")
    with open(module, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("import time\n\ndef now():\n    return time.time()\n")

    report = gates.purity(root)
    assert not report.ok
    assert any("time" in detail for _, detail in report.findings)


@pytest.mark.parametrize(
    "source,needle",
    [
        ("import socket\n", "socket"),
        ("import random\n", "random"),
        ("import os\n", "os"),
        ("from urllib.parse import urlparse\n", "urllib"),
        ("def f():\n    return open('x').read()\n", "open"),
        ("from datetime import datetime\n", "datetime"),
    ],
)
def test_purity_catches_each_forbidden_form(tmp_path, source, needle):
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, JUDGEMENT, "leaky.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write(source)

    report = gates.purity(root)
    assert not report.ok
    assert any(needle in detail for _, detail in report.findings), report.findings


def test_purity_catches_reaching_into_transport(tmp_path):
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, JUDGEMENT, "leaky.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("from http_semantics_mcp.server import serve\n")

    report = gates.purity(root)
    assert not report.ok
    assert any("server" in detail for _, detail in report.findings)


def test_purity_reports_a_missing_layer_instead_of_passing(tmp_path):
    root = _copy_repo(tmp_path)
    shutil.rmtree(os.path.join(root, JUDGEMENT))

    report = gates.purity(root)
    assert not report.ok
    assert report.scanned == 0


# -- absolute paths -------------------------------------------------------


def test_absolute_path_gate_passes_on_the_clean_tree():
    report = gates.absolute_paths(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0


def test_absolute_path_gate_catches_a_windows_drive_path(tmp_path):
    root = _copy_repo(tmp_path)
    # The probe is assembled at runtime so this test file does not match it.
    probe = "C:" + "\\" + "Users" + "\\" + "someone" + "\\" + "notes.md"
    with open(os.path.join(root, "leak.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("see " + probe + "\n")

    report = gates.absolute_paths(root)
    assert not report.ok


def test_absolute_path_gate_catches_a_posix_home_path(tmp_path):
    root = _copy_repo(tmp_path)
    probe = "/" + "home" + "/" + "someone" + "/" + "notes.md"
    with open(os.path.join(root, "leak.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("see " + probe + "\n")

    assert not gates.absolute_paths(root).ok


def test_absolute_path_gate_does_not_flag_urls(tmp_path):
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, "ok.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("https://example.com/a/b and https://example.org:8080/x\n")

    report = gates.absolute_paths(root)
    assert report.ok, report.findings


def test_absolute_path_gate_does_not_flag_source_escapes(tmp_path):
    """``\\\\r\\\\n`` in a Python literal is an escape, not a UNC share."""
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, "ok.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write('SEPARATOR = b"\\r\\n"\nTAB = "\\t"\n')

    report = gates.absolute_paths(root)
    assert report.ok, report.findings


def test_absolute_path_gate_catches_a_unc_share(tmp_path):
    root = _copy_repo(tmp_path)
    probe = "\\\\" + "fileserver" + "\\" + "share" + "\\" + "notes.md"
    with open(os.path.join(root, "leak.md"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("see " + probe + "\n")

    assert not gates.absolute_paths(root).ok


# -- line endings ---------------------------------------------------------


def test_crlf_gate_passes_on_the_clean_tree():
    report = gates.crlf(ROOT)
    assert report.ok, report.findings


def test_crlf_gate_catches_a_carriage_return(tmp_path):
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, "bad.md"), "wb") as handle:
        handle.write(b"line one\r\nline two\r\n")

    report = gates.crlf(root)
    assert not report.ok
    assert any("bad.md" in path for path, _ in report.findings)


def test_crlf_gate_requires_gitattributes(tmp_path):
    root = _copy_repo(tmp_path)
    os.remove(os.path.join(root, ".gitattributes"))

    report = gates.crlf(root)
    assert not report.ok
    assert any(path == ".gitattributes" for path, _ in report.findings)


def test_every_report_says_how_many_files_it_scanned():
    for report in gates.all_reports(ROOT):
        assert report.scanned > 0, report.name + " scanned nothing"
        assert report.summary().startswith(report.name + ":")


# -- package-wide determinism --------------------------------------------


def test_no_nondeterminism_passes_on_the_clean_tree():
    report = gates.no_nondeterminism(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0


@pytest.mark.parametrize(
    "source,needle",
    [
        ("import time\n", "time"),
        ("import random\n", "random"),
        ("import socket\n", "socket"),
        ("import os\n\ndef f():\n    return os.environ.get('X')\n", "environment read"),
        ("import os\n\ndef f():\n    return os.getenv('X')\n", "environment read"),
    ],
)
def test_no_nondeterminism_catches_runtime_leaks(tmp_path, source, needle):
    root = _copy_repo(tmp_path)
    target = os.path.join(root, "src", "http_semantics_mcp", "leaky.py")
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(source)

    report = gates.no_nondeterminism(root)
    assert not report.ok
    assert any(needle in detail for _, detail in report.findings), report.findings


def test_single_serialiser_passes_on_the_clean_tree():
    report = gates.single_serialiser(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0


def test_single_serialiser_catches_a_second_writer(tmp_path):
    root = _copy_repo(tmp_path)
    target = os.path.join(root, "src", "http_semantics_mcp", "extra.py")
    with open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("import json\n\n\ndef render(value):\n    return json.dumps(value)\n")

    report = gates.single_serialiser(root)
    assert not report.ok
    assert any("outside canonical.py" in detail for _, detail in report.findings)


def test_single_serialiser_reports_a_broken_probe(tmp_path):
    """If canonical.py stops calling json.dumps, the gate must say so."""
    root = _copy_repo(tmp_path)
    with open(os.path.join(root, "src", "http_semantics_mcp", "canonical.py"), "w", encoding="utf-8", newline="\n") as handle:
        handle.write("def dumps(value):\n    return str(value)\n")

    report = gates.single_serialiser(root)
    assert not report.ok
    assert any("probe is broken" in detail for _, detail in report.findings)

