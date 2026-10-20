"""Release-terminal gate: runtime shape only.

These tests deliberately do **not** assert "currently zero failures": before a
tag exists, several checks must be red, and a test demanding green would make
every normal commit red. What is asserted is the gate's contract:

* every check produces exactly one line
* offline network items report SKIP, never PASS
* a missing artefact produces a FAIL, not a traceback
* running it twice produces the same number of lines
* ``--pre-tag`` turns post-tag items into SKIP instead of FAIL
"""

import io
import json
import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = os.path.join(ROOT, "scripts")
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import check_release  # noqa: E402


def _run(mode="offline"):
    out = io.StringIO()
    code = check_release.run(mode, out)
    return code, out.getvalue()


def _rows(output):
    return [line for line in output.splitlines() if line and not line.startswith("summary:")]


def test_every_check_produces_exactly_one_row():
    _, output = _run()
    rows = _rows(output)
    names = [row.split()[0] for row in rows]
    assert len(names) == len(set(names)), "duplicate check rows"
    for row in rows:
        assert ("PASS" in row) or ("FAIL" in row) or ("SKIP" in row), row


def test_offline_mode_never_reports_network_items_as_pass():
    _, output = _run("offline")
    rows = {row.split()[0]: row for row in _rows(output)}
    assert "SKIP" not in rows["version-parity"]
    # Online-only checks must not claim PASS without a network call.
    for name in ("tag", "release", "attachments"):
        if name in rows:
            assert "PASS" not in rows[name], rows[name]


def test_pre_tag_mode_reports_post_tag_items_as_skip():
    _, output = _run("pre-tag")
    rows = {row.split()[0]: row for row in _rows(output)}

    # The release note does not exist yet; pre-tag treats that as expected.
    assert "SKIP" in rows["release-note"] or "PASS" in rows["release-note"]
    # The tag and release cannot exist yet.
    assert "SKIP" in rows["tag"] or "FAIL" not in rows["tag"]


def test_pre_tag_is_not_stricter_than_offline_on_missing_tag():
    _, offline = _run("offline")
    _, pre_tag = _run("pre-tag")
    offline_skips = sum(1 for row in _rows(offline) if "SKIP" in row)
    pre_tag_skips = sum(1 for row in _rows(pre_tag) if "SKIP" in row)
    assert pre_tag_skips >= offline_skips


def test_running_twice_yields_the_same_row_count():
    first = len(_rows(_run()[1]))
    second = len(_rows(_run()[1]))
    assert first == second


def test_summary_counts_match_the_rows():
    output = _run()[1]
    rows = _rows(output)
    summary = [line for line in output.splitlines() if line.startswith("summary:")][0]
    passed = sum(1 for row in rows if "PASS" in row)
    failed = sum(1 for row in rows if "FAIL" in row)
    skipped = sum(1 for row in rows if "SKIP" in row)
    assert str(passed) in summary and str(failed) in summary and str(skipped) in summary


def test_missing_release_note_is_a_fail_not_a_crash(tmp_path, monkeypatch):
    """The gate must finish and report, even when a checked object is absent."""
    monkeypatch.setattr(check_release, "ROOT", str(tmp_path))
    out = io.StringIO()
    code = check_release.run("offline", out)
    assert code in (0, 1)
    assert "summary:" in out.getvalue()


def test_exit_code_is_one_when_a_check_fails(tmp_path, monkeypatch):
    monkeypatch.setattr(check_release, "ROOT", str(tmp_path))
    out = io.StringIO()
    code = check_release.run("offline", out)
    assert code == 1
    assert "FAIL" in out.getvalue()


def test_environment_missing_is_a_distinct_exit_code(monkeypatch):
    """'not done yet' and 'this machine cannot check' must not collapse."""

    def missing(*args, **kwargs):
        raise check_release.EnvironmentMissing("gh is not installed")

    monkeypatch.setattr(check_release, "check_gh_available", missing)
    out = io.StringIO()
    code = check_release.run("online", out)
    assert code == 3
    assert "environment missing" in out.getvalue()


def test_online_not_achieved_is_a_failure_not_an_environment_problem(monkeypatch):
    def not_achieved(*args, **kwargs):
        raise check_release.NotAchieved("HTTP 404")

    monkeypatch.setattr(check_release, "check_gh_available", lambda: "gh available")
    monkeypatch.setattr(check_release, "check_remote_tag_matches", not_achieved)
    out = io.StringIO()
    code = check_release.run("online", out)
    assert code == 1
    assert "environment missing" not in out.getvalue()


def test_registered_digest_parser_reads_the_documented_line_form():
    sample = "sha256: " + "a" * 64 + "  http-semantics-mcp-0.1.0.tar.gz\n"
    found = check_release._DIGEST_LINE.findall(sample)
    assert found == [("a" * 64, "http-semantics-mcp-0.1.0.tar.gz")]


# -- attachment digests: matching names is not enough ---------------------

TARBALL = "http-semantics-mcp-0.1.0.tar.gz"
SUMS = "SHA256SUMS"
TARBALL_DIGEST = "8cc8892c20f1d37f175c8005a0cdd41993b90b58b6aaeef357bda2e647cef8b2"
SUMS_DIGEST = "3fa920e376b4870f34975db75f45dd4fef15609eca5d4ff977128eaeb8fab805"


def _assets_payload(digests, omit_digest_for=()):
    assets = []
    for name, digest in sorted(digests.items()):
        asset = {"name": name, "state": "uploaded", "digest": "sha256:" + digest}
        if name in omit_digest_for:
            del asset["digest"]
        assets.append(asset)
    return json.dumps({"assets": assets})


def _stub_published(monkeypatch, registered, published, omit_digest_for=()):
    monkeypatch.setattr(check_release, "_registered_digests", lambda: dict(registered))
    monkeypatch.setattr(
        check_release,
        "_run",
        lambda command: _assets_payload(published, omit_digest_for),
    )


def test_attachment_check_verifies_digest_values(monkeypatch):
    published = {TARBALL: TARBALL_DIGEST, SUMS: SUMS_DIGEST}
    _stub_published(monkeypatch, published, published)

    detail = check_release.check_attachment_digests()
    assert detail == "2 digest(s) verified against published assets"


def test_attachment_check_fails_when_one_registered_digest_is_wrong(monkeypatch):
    """The D2 negative control: one changed character must turn the check red."""
    published = {TARBALL: TARBALL_DIGEST, SUMS: SUMS_DIGEST}
    tampered = dict(published)
    tampered[TARBALL] = ("0" if TARBALL_DIGEST[0] != "0" else "1") + TARBALL_DIGEST[1:]
    _stub_published(monkeypatch, tampered, published)

    with pytest.raises(check_release.NotAchieved) as caught:
        check_release.check_attachment_digests()
    assert "digest mismatch" in str(caught.value)
    assert TARBALL in str(caught.value)


def test_attachment_check_still_reports_a_missing_asset(monkeypatch):
    _stub_published(
        monkeypatch, {TARBALL: TARBALL_DIGEST, SUMS: SUMS_DIGEST}, {TARBALL: TARBALL_DIGEST}
    )

    with pytest.raises(check_release.NotAchieved) as caught:
        check_release.check_attachment_digests()
    assert "not published" in str(caught.value)


def test_attachment_check_treats_a_missing_digest_field_as_environment(monkeypatch):
    """An old gh that reports no digest must be exit 3, not a silent PASS."""
    published = {TARBALL: TARBALL_DIGEST}
    _stub_published(monkeypatch, published, published, omit_digest_for=(TARBALL,))

    with pytest.raises(check_release.EnvironmentMissing):
        check_release.check_attachment_digests()


def test_attachment_check_rejects_a_non_sha256_digest(monkeypatch):
    monkeypatch.setattr(check_release, "_registered_digests", lambda: {TARBALL: TARBALL_DIGEST})
    monkeypatch.setattr(
        check_release,
        "_run",
        lambda command: json.dumps(
            {
                "assets": [
                    {"name": TARBALL, "state": "uploaded", "digest": "md5:" + TARBALL_DIGEST}
                ]
            }
        ),
    )

    with pytest.raises(check_release.NotAchieved):
        check_release.check_attachment_digests()
