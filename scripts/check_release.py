"""Release-terminal self-check.

Three modes (plan/05 M6, decision D34):

* ``--offline`` (default) -- repository-local facts only. Network items are
  reported as ``SKIP``, never as ``PASS``.
* ``--pre-tag``            -- same as offline, but every item that can only be
  true *after* a tag is reported as ``SKIP`` instead of ``FAIL``. This is what
  lets the script ship inside the tag tree and be green before the tag exists.
* ``--online``             -- additionally queries GitHub for the tag, the
  release and the attachment digests.

Two exception classes, deliberately distinct:

* ``NotAchieved``   -- the thing has not been done yet  -> counts as FAIL
* ``EnvironmentMissing`` -- this machine cannot check it -> exit code 3

Collapsing those two is how "the repository was never created" gets reported
as "gh is not logged in", so they stay separate.

Deliberately **not** wired into CI: before the tag, terminal items must be red,
and a permanently red CI job carries no information.

Exit codes: 0 all checks pass, 1 a check failed, 2 usage error, 3 environment
missing (gh absent / not authenticated).
"""

import argparse
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

DISTRIBUTION = "http-semantics-mcp"


def _declared_version():
    """The version this checkout claims, read without importing the package.

    ``pyproject.toml`` is the single declaration, so the tag name, the release
    note name and the expected asset names all derive from it. Hard-coding
    them (the v0.1.0 shape) is how a later release ships a gate that checks the
    *previous* tag.
    """
    import importlib.util

    reader = os.path.join(ROOT, "tools", "toml_lite.py")
    spec = importlib.util.spec_from_file_location("_release_toml_version", reader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    version = module.load(os.path.join(ROOT, "pyproject.toml")).get("project", {}).get("version")
    if not version:
        raise EnvironmentMissing("pyproject.toml declares no version")
    return version


def _tag():
    """``0.2.0`` -> ``v0.2.0``.

    Derived rather than frozen: a hard-coded tag is how a later release ships a
    gate that keeps happily checking the *previous* one.
    """
    return "v" + _declared_version()


# The release note name carries the *milestone* number (plan/05 numbering:
# M6 is the release milestone), which is independent of the semantic version.
# ``_release_doc()`` therefore takes the number as an argument and the caller
# passes this constant, instead of string-slicing the version into a wrong name.
RELEASE_MILESTONE = "M6"


def _release_doc(milestone=RELEASE_MILESTONE):
    return os.path.join("plan", "RELEASE-" + milestone + ".md")


class NotAchieved(Exception):
    """A release fact that has not happened yet."""


class EnvironmentMissing(Exception):
    """This machine cannot perform the check."""


class Check(object):
    def __init__(self, name, status, detail):
        self.name = name
        self.status = status
        self.detail = detail

    def line(self, width):
        return "{0:<{1}}  {2:<4}  {3}".format(self.name, width, self.status, self.detail)


# -- checks ---------------------------------------------------------------


def check_version_parity():
    """pyproject version == package __version__ == (later) tag name."""
    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from http_semantics_mcp import __version__
    finally:
        sys.path.pop(0)

    path = os.path.join(ROOT, "pyproject.toml")
    if not os.path.isfile(path):
        raise NotAchieved("pyproject.toml is missing")
    declared = _pyproject_version(path)
    if declared != __version__:
        raise NotAchieved("pyproject " + str(declared) + " != package " + __version__)
    return "pyproject and package agree on " + __version__


def _pyproject_version(path):
    """Read the version through the shared TOML subset reader."""
    import importlib.util

    reader = os.path.join(ROOT, "tools", "toml_lite.py")
    spec = importlib.util.spec_from_file_location("_release_toml", reader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.load(path).get("project", {}).get("version")


def check_license_file():
    if not os.path.isfile(os.path.join(ROOT, "LICENSE")):
        raise NotAchieved("LICENSE is missing while README claims MIT")
    return "LICENSE present"


def check_readme_named():
    """The README exists and names the distribution it ships.

    Deliberately shallow: the *content* contract (commands, flags, extras,
    file references) lives in ``tests/test_readme_gate.py``, which can use
    pytest. This check only has to run in a clean clone without pytest.
    """
    path = os.path.join(ROOT, "README.md")
    if not os.path.isfile(path):
        raise NotAchieved("README.md is missing")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    if "http-semantics-mcp" not in text:
        raise NotAchieved("README does not name the distribution")
    return "README present"


def check_gates():
    """Repository-wide purity / path / line-ending gates."""
    import importlib.util

    path = os.path.join(ROOT, "tools", "gates.py")
    spec = importlib.util.spec_from_file_location("_release_gates", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    reports = module.all_reports(ROOT)
    scanned = sum(report.scanned for report in reports)
    if scanned == 0:
        raise NotAchieved("gates scanned 0 files (coverage hole)")
    failures = []
    for report in reports:
        if not report.ok:
            failures.append(report.summary())
    if failures:
        raise NotAchieved("; ".join(failures))
    return "{0} gates green, {1} files scanned".format(len(reports), scanned)


def check_release_doc(pre_tag):
    note = _release_doc()
    path = os.path.join(ROOT, note)
    if not os.path.isfile(path):
        if pre_tag:
            raise _Skip("release note is written before the tag (expected pre-tag)")
        raise NotAchieved(note + " is missing")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    for heading in ("tag 时点事实", "tag 后追加事实"):
        if heading not in text:
            raise NotAchieved(note + " lacks the '" + heading + "' column")
    return "release note has both columns"


def check_dist_mirrors():
    """Top-level mirrors must equal the in-package sources, byte for byte."""
    pairs = [
        (os.path.join("src", "http_semantics_mcp", "references"), "references"),
        (os.path.join("src", "http_semantics_mcp", "schemas", "tools"), os.path.join("schemas", "tools")),
    ]
    compared = 0
    for source_dir, mirror_dir in pairs:
        source = os.path.join(ROOT, source_dir)
        if not os.path.isdir(source):
            continue
        for name in sorted(os.listdir(source)):
            if not name.endswith(".json"):
                continue
            mirror = os.path.join(ROOT, mirror_dir, name)
            if not os.path.isfile(mirror):
                raise NotAchieved("mirror missing: " + os.path.join(mirror_dir, name))
            with open(os.path.join(source, name), "rb") as handle:
                left = handle.read()
            with open(mirror, "rb") as handle:
                right = handle.read()
            if left != right:
                raise NotAchieved("mirror differs: " + os.path.join(mirror_dir, name))
            compared += 1
    return "{0} mirror file(s) byte-identical".format(compared)


def check_git_clean():
    try:
        output = _run(["git", "status", "--porcelain"])
    except EnvironmentMissing:
        raise
    if output.strip():
        raise NotAchieved("working tree has uncommitted changes")
    return "working tree clean"


# -- helpers --------------------------------------------------------------


class _Skip(Exception):
    pass


def _run(command):
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )
    except FileNotFoundError:
        raise EnvironmentMissing(command[0] + " is not installed")
    except subprocess.TimeoutExpired:
        raise EnvironmentMissing(command[0] + " timed out")
    if process.returncode != 0:
        raise NotAchieved(
            " ".join(command) + " exited " + str(process.returncode) + ": "
            + process.stderr.decode("utf-8", "replace").strip()
        )
    return process.stdout.decode("utf-8", "replace")


def check_gh_available():
    try:
        _run(["gh", "--version"])
    except NotAchieved as exc:
        raise EnvironmentMissing(str(exc))
    return "gh is available"


def check_tag_exists():
    tag = _tag()
    tags = _run(["git", "tag", "--list", tag]).strip()
    if not tags:
        raise NotAchieved("tag " + tag + " does not exist locally")
    return "tag " + tag + " exists"


def check_remote_tag_matches():
    tag = _tag()
    local = _run(["git", "rev-parse", tag]).strip()
    remote = _run(["gh", "api", "repos/yuluo554/" + DISTRIBUTION + "/git/ref/tags/" + tag, "--jq", ".object.sha"]).strip()
    if local != remote:
        raise NotAchieved("local tag object " + local + " != remote " + remote)
    return "tag object hashes match"


def check_release_published():
    raw = _run([
        "gh", "release", "view", _tag(),
        "--repo", "yuluo554/" + DISTRIBUTION,
        "--json", "isDraft,tagName,assets",
    ])
    payload = json.loads(raw)
    if payload.get("isDraft"):
        raise NotAchieved("release is still a draft")
    assets = payload.get("assets") or []
    if not assets:
        raise NotAchieved("release has no uploaded assets")
    for asset in assets:
        if asset.get("state") != "uploaded":
            raise NotAchieved("asset not uploaded: " + str(asset.get("name")))
    return "{0} asset(s) uploaded".format(len(assets))


def check_attachment_digests():
    """Compare the registered sha256 digests against the published assets.

    Comparing names only would let a wrong digest sit in the release note
    unnoticed (this is exactly the D2 gap), so the ``digest`` field that
    ``gh release view --json assets`` reports is compared value by value.
    A ``gh`` too old to report digests is an environment gap (exit 3), never
    a silent pass.
    """
    expected = _registered_digests()
    if not expected:
        raise NotAchieved("no sha256 digests registered in the release note")
    raw = _run([
        "gh", "release", "view", _tag(),
        "--repo", "yuluo554/" + DISTRIBUTION,
        "--json", "assets",
    ])
    published = {}
    for asset in json.loads(raw).get("assets", []):
        published[asset.get("name")] = asset
    missing = sorted(set(expected) - set(published))
    if missing:
        raise NotAchieved("registered assets not published: " + ", ".join(missing))

    mismatched = []
    for name in sorted(expected):
        reported = published[name].get("digest")
        if not reported:
            raise EnvironmentMissing(
                "gh reported no digest for " + name + "; upgrade gh to a version that supports --json assets digest"
            )
        algorithm, _, value = reported.partition(":")
        if algorithm != "sha256" or value != expected[name]:
            mismatched.append(name + " (" + reported + " != sha256:" + expected[name] + ")")
    if mismatched:
        raise NotAchieved("digest mismatch: " + ", ".join(mismatched))
    return "{0} digest(s) verified against published assets".format(len(expected))


_DIGEST_LINE = re.compile(r"^sha256:\s*([0-9a-f]{64})\s+(\S+)\s*$", re.MULTILINE)


def _registered_digests():
    path = os.path.join(ROOT, _release_doc())
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    return {name: digest for digest, name in _DIGEST_LINE.findall(text)}


# -- driver ---------------------------------------------------------------


def _checks(mode):
    pre_tag = mode == "pre-tag"
    items = [
        ("version-parity", check_version_parity, False),
        ("license-file", check_license_file, False),
        ("readme", check_readme_named, False),
        ("repo-gates", check_gates, False),
        ("dist-mirrors", check_dist_mirrors, False),
        ("release-note", lambda: check_release_doc(pre_tag), False),
        ("git-clean", check_git_clean, False),
        ("tag", check_tag_exists, True),
        ("release", check_release_published, True),
        ("attachments", check_attachment_digests, True),
    ]
    return items


def run(mode, out):
    pre_tag = mode == "pre-tag"
    online = mode == "online"

    if online:
        try:
            check_gh_available()
            check_remote_tag_matches()
        except EnvironmentMissing as exc:
            out.write("release-check  FAIL  environment missing: " + str(exc) + "\n")
            return 3
        except NotAchieved as exc:
            out.write("release-check  FAIL  " + str(exc) + "\n")
            return 1

    results = []
    for name, function, terminal in _checks(mode):
        if terminal and not online:
            # No network in this mode: report the gap instead of guessing, and
            # never let "not asked" masquerade as "passed".
            results.append(Check(name, SKIP, "network check; run with --online"))
            continue
        try:
            detail = function()
            results.append(Check(name, PASS, detail))
        except _Skip as exc:
            results.append(Check(name, SKIP, str(exc)))
        except NotAchieved as exc:
            results.append(Check(name, SKIP if (pre_tag and terminal) else FAIL, str(exc)))
        except EnvironmentMissing as exc:
            out.write("release-check  FAIL  environment missing: " + str(exc) + "\n")
            return 3
        except Exception as exc:  # noqa: BLE001 - a gate must always finish
            results.append(Check(name, FAIL, type(exc).__name__ + ": " + str(exc)))

    width = max(len(item.name) for item in results)
    for item in results:
        out.write(item.line(width) + "\n")

    passed = len([item for item in results if item.status == PASS])
    failed = len([item for item in results if item.status == FAIL])
    skipped = len([item for item in results if item.status == SKIP])
    out.write(
        "summary: {0} passed, {1} failed, {2} skipped ({3} checks)\n".format(
            passed, failed, skipped, len(results)
        )
    )
    out.flush()
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description="Release-terminal self-check (offline by default).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--offline", action="store_true", help="repository-local checks only (default)")
    group.add_argument("--pre-tag", action="store_true", help="treat post-tag items as SKIP")
    group.add_argument("--online", action="store_true", help="also query GitHub")
    args = parser.parse_args(argv)

    mode = "offline"
    if args.pre_tag:
        mode = "pre-tag"
    elif args.online:
        mode = "online"

    sys.path.insert(0, os.path.join(ROOT, "src"))
    try:
        from http_semantics_mcp._utf8 import ensure_utf8_stdio
    finally:
        sys.path.pop(0)
    ensure_utf8_stdio()

    return run(mode, sys.stdout)


if __name__ == "__main__":
    sys.exit(main())
