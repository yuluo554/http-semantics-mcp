"""Entry-point contract: exit codes, argument surface, no second judgement path."""

import io

import pytest

from http_semantics_mcp import __main__ as entry
from http_semantics_mcp import __version__


def test_parser_has_no_judgement_subcommands():
    """Decision D26: judgement is reachable only through MCP tools/call."""
    parser = entry.build_parser()
    actions = parser._actions
    dests = [action.dest for action in actions]
    assert "mode" in dests
    assert "command" not in dests

    # The only positional accepts exactly one value: "serve".
    positional = [action for action in actions if action.dest == "mode"][0]
    assert list(positional.choices) == ["serve"]


def test_version_flag_prints_single_line(capsys):
    code = entry.main(["--version"])
    captured = capsys.readouterr()
    assert code == 0
    assert captured.out == __version__ + "\n"


def test_selftest_exits_zero_and_prints_every_check(capsys):
    code = entry.main(["--selftest"])
    captured = capsys.readouterr()
    assert code == 0
    assert "PASS" in captured.out
    assert "FAIL" not in captured.out
    assert "summary:" in captured.out


def test_unknown_argument_exits_with_code_two():
    """argparse answers SystemExit(2); that contract is asserted, not assumed."""
    with pytest.raises(SystemExit) as excinfo:
        entry.main(["--not-a-real-flag"])
    assert excinfo.value.code == 2


def test_unknown_mode_exits_with_code_two():
    with pytest.raises(SystemExit) as excinfo:
        entry.main(["judge"])
    assert excinfo.value.code == 2


def test_help_mentions_stdio_and_version_and_selftest(capsys):
    with pytest.raises(SystemExit) as excinfo:
        entry.main(["--help"])
    assert excinfo.value.code == 0
    text = capsys.readouterr().out
    assert "stdio" in text
    assert "--version" in text
    assert "--selftest" in text


def test_selftest_prints_summary(capsys):
    entry.main(["--selftest"])
    captured = capsys.readouterr()
    assert "summary:" in captured.out


def test_selftest_detects_a_version_mismatch(tmp_path, monkeypatch):
    """The parity check must be able to fail; otherwise it is decoration."""
    from http_semantics_mcp import selfcheck

    fake = tmp_path / "pyproject.toml"
    fake.write_text('[project]\nname = "x"\nversion = "9.9.9"\n', encoding="utf-8")
    monkeypatch.setattr(selfcheck, "_find_pyproject", lambda: str(fake))

    results = dict((name, status) for name, status, _ in selfcheck.run_checks())
    assert results["version-parity"] == "FAIL"

    stream = io.StringIO()
    assert selfcheck.main(stream) == 1
    assert "FAIL" in stream.getvalue()


def test_selftest_reports_skip_when_pyproject_is_unreachable(monkeypatch):
    """Installed form: no pyproject.toml. SKIP, never a silent PASS."""
    from http_semantics_mcp import selfcheck

    monkeypatch.setattr(selfcheck, "_find_pyproject", lambda: None)
    results = dict((name, status) for name, status, _ in selfcheck.run_checks())
    assert results["version-parity"] == "SKIP"
