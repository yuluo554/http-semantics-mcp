"""The test count printed in the README must equal the real collected count.

Every milestone so far has drifted here in the same way: a test is added, the
README table keeps the old number, and nothing notices because no gate compares
the two. This gate closes that loop by asking pytest how many tests it collects
and comparing against the number in ``README.md``.

The count is collected in a subprocess rather than imported, because
``--collect-only`` is the number a reader sees when they run the command the
README tells them to run.
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
README = os.path.join(ROOT, "README.md")

# `| Collected tests | 389 (Python 3.12) |`
COLLECTED_ROW = re.compile(r"\|\s*Collected tests\s*\|\s*(\d+)\s*\(Python\s*([0-9.]+)\)\s*\|")


def _readme_row():
    with open(README, "r", encoding="utf-8") as handle:
        text = handle.read()
    return COLLECTED_ROW.search(text)


def _collected_count():
    process = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=300,
    )
    assert process.returncode == 0, process.stderr.decode("utf-8", "replace")
    output = process.stdout.decode("utf-8", "replace")
    found = re.search(r"^(\d+) tests? collected", output, re.MULTILINE)
    assert found, "could not read the collected count out of pytest output:\n" + output
    return int(found.group(1))


def test_the_readme_states_a_test_count():
    match = _readme_row()
    assert match, "README has no '| Collected tests | <n> (Python <ver>) |' row"


def test_readme_test_count_equals_the_collected_count():
    match = _readme_row()
    assert match, "README has no '| Collected tests | <n> (Python <ver>) |' row"
    stated = int(match.group(1))
    actual = _collected_count()
    assert stated == actual, (
        "README says " + str(stated) + " collected tests, pytest collects " + str(actual)
        + "; update the 'Measured on this build' table (and keep this gate's own row in mind)"
    )


def test_the_stated_interpreter_is_the_one_running_the_suite():
    """A count from an interpreter the matrix no longer runs is a stale claim."""
    match = _readme_row()
    assert match, "README has no '| Collected tests | <n> (Python <ver>) |' row"
    stated = match.group(2)
    running = "{0}.{1}".format(sys.version_info[0], sys.version_info[1])
    assert stated == running, "README states Python " + stated + " but the suite ran on " + running
