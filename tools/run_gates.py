"""Run the repository gates and exit non-zero on any finding.

Used by CI as its own step so the failure names the gate, and callable locally:

    py tools/run_gates.py
    py tools/run_gates.py --verbose

Each gate prints how many files it scanned. A gate that scanned zero files is
reported as a failure, not as a pass: "found nothing" and "looked at nothing"
must not be indistinguishable in the output.
"""

import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gates  # noqa: E402


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run purity / absolute-path / line-ending gates.")
    parser.add_argument("--root", default=ROOT, help="repository root (default: this checkout)")
    parser.add_argument("--verbose", action="store_true", help="print each finding")
    args = parser.parse_args(argv)

    failures = 0
    reports = gates.all_reports(args.root)
    for report in reports:
        if report.scanned == 0:
            sys.stdout.write(report.name + ": FAIL (0 files scanned)\n")
            failures += 1
            continue
        sys.stdout.write(report.summary() + "\n")
        if not report.ok:
            failures += 1
            if args.verbose:
                for path, detail in report.findings:
                    sys.stdout.write("    " + path + ": " + detail + "\n")

    sys.stdout.write("summary: {0} gate(s), {1} failing\n".format(len(reports), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
