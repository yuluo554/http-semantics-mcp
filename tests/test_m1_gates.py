"""M1 gates, each with a mutation that must turn it red.

Split from ``test_gates.py`` because these three gates were added with the data
layer and they check different things: an independent oracle, frozen-case
hygiene, and "the code enum exists once".
"""

import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS = os.path.join(ROOT, "tools")
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import gates  # noqa: E402

ORACLE = os.path.join("tools", "golden_oracle")
CASE = os.path.join("data", "golden", "vary_match", "vary-001-hit-single.json")


def _copy_repo(tmp_path):
    target = tmp_path / "repo"
    target.mkdir()
    shutil.copytree(os.path.join(ROOT, "src"), target / "src")
    shutil.copytree(os.path.join(ROOT, "tools"), target / "tools")
    shutil.copytree(os.path.join(ROOT, "data"), target / "data")
    shutil.copy(os.path.join(ROOT, ".gitattributes"), target / ".gitattributes")
    return str(target)


def _write(path, text):
    directory = os.path.dirname(path)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


# -- oracle independence ---------------------------------------------------


def test_oracle_independence_passes_on_the_clean_tree():
    report = gates.oracle_independence(ROOT)
    assert report.ok, report.findings
    assert report.scanned >= 5, "the oracle is smaller than expected"


def test_oracle_independence_catches_a_direct_import(tmp_path):
    root = _copy_repo(tmp_path)
    _write(os.path.join(root, ORACLE, "cheat.py"), "from http_semantics_mcp.judgement import cache\n")

    report = gates.oracle_independence(root)
    assert not report.ok
    assert any("implementation" in detail for _, detail in report.findings)


def test_oracle_independence_catches_a_function_local_import(tmp_path):
    root = _copy_repo(tmp_path)
    _write(
        os.path.join(root, ORACLE, "cheat.py"),
        "def run():\n    import http_semantics_mcp\n    return http_semantics_mcp\n",
    )

    assert not gates.oracle_independence(root).ok


def test_oracle_independence_catches_a_dynamic_import(tmp_path):
    root = _copy_repo(tmp_path)
    _write(
        os.path.join(root, ORACLE, "cheat.py"),
        "import importlib\nimportlib.import_module('http_semantics_mcp')\n",
    )

    assert not gates.oracle_independence(root).ok


def test_oracle_independence_reports_a_missing_directory(tmp_path):
    root = _copy_repo(tmp_path)
    shutil.rmtree(os.path.join(root, ORACLE))

    report = gates.oracle_independence(root)
    assert not report.ok
    assert report.scanned == 0


# -- golden hygiene --------------------------------------------------------


def test_golden_hygiene_passes_on_the_clean_tree():
    report = gates.golden_hygiene(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0


def test_golden_hygiene_catches_an_observed_field(tmp_path):
    root = _copy_repo(tmp_path)
    target = os.path.join(root, CASE)
    with open(target, "r", encoding="utf-8") as handle:
        payload = handle.read()
    _write(target, payload.replace('"expected":', '"observed_match": "hit",\n  "expected":', 1))

    report = gates.golden_hygiene(root)
    assert not report.ok
    assert any("observed field" in detail for _, detail in report.findings)


def test_golden_hygiene_catches_a_missing_field(tmp_path):
    root = _copy_repo(tmp_path)
    _write(os.path.join(root, CASE), '{"case_id": "vary-001-hit-single"}\n')

    report = gates.golden_hygiene(root)
    assert not report.ok
    assert any("missing expected" in detail for _, detail in report.findings)


def test_golden_hygiene_refuses_an_empty_directory(tmp_path):
    root = _copy_repo(tmp_path)
    shutil.rmtree(os.path.join(root, "data", "golden"))
    os.makedirs(os.path.join(root, "data", "golden"))

    report = gates.golden_hygiene(root)
    assert not report.ok
    assert report.scanned == 0


# -- code literals ---------------------------------------------------------


def test_code_literals_passes_on_the_clean_tree():
    report = gates.code_literals(ROOT)
    assert report.ok, report.findings
    assert report.scanned > 0


def test_code_literals_catches_a_second_copy(tmp_path):
    root = _copy_repo(tmp_path)
    _write(
        os.path.join(root, "src", "http_semantics_mcp", "judgement", "leaky.py"),
        'CODE = "CACHE_NO_STORE"\n',
    )

    report = gates.code_literals(root)
    assert not report.ok
    assert any("code literal" in detail for _, detail in report.findings)


def test_code_literals_ignores_substrings(tmp_path):
    """A prefix such as ``CORS_`` alone is not a code."""
    root = _copy_repo(tmp_path)
    _write(
        os.path.join(root, "src", "http_semantics_mcp", "judgement", "ok.py"),
        'PREFIX = "CORS_"\nNAME = "cors_evaluate"\n',
    )

    assert gates.code_literals(root).ok


# -- the one exempt path ---------------------------------------------------


def test_code_literals_exempts_the_generated_rule_module(tmp_path):
    """The exemption must be exercised, not just declared.

    If ``rules.py`` were empty the gate would pass for the wrong reason: no
    literals anywhere because there are no literals at all.
    """
    root = _copy_repo(tmp_path)
    module = os.path.join(root, gates.GENERATED_CODE_MODULE)
    with open(module, "r", encoding="utf-8") as handle:
        assert "CACHE_NO_STORE" in handle.read()
    assert gates.code_literals(root).ok


def test_code_literals_refuses_a_missing_rule_module(tmp_path):
    """An exemption without its artifact would be a hole, not a rule."""
    root = _copy_repo(tmp_path)
    os.remove(os.path.join(root, gates.GENERATED_CODE_MODULE))

    report = gates.code_literals(root)
    assert not report.ok
    assert any("generated rule module is missing" in detail for _, detail in report.findings)


def test_code_literals_still_catches_a_copy_next_to_the_generated_module(tmp_path):
    """Exempting one path must not exempt the package around it."""
    root = _copy_repo(tmp_path)
    _write(
        os.path.join(root, "src", "http_semantics_mcp", "handy.py"),
        'ALIAS = "CACHE_NO_STORE"\n',
    )

    report = gates.code_literals(root)
    assert not report.ok
    assert any("code literal" in detail for _, detail in report.findings)
