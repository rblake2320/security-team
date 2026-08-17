#!/usr/bin/env python3
"""Run one team's pytest suite as a CI gate.

Why this exists rather than `python -m pytest <dir>` inline:

  * The gate manifest requires a `command` gate's argv[0] to be a real file, and the
    drift guard matches the workflow by that filename. Routing through a script keeps
    the manifest, the workflow, and the local runner invoking one identical command,
    which is the drift the manifest exists to prevent.
  * Every sibling gate-runner in this program bounds its subprocess (claim_check.py
    300s, ci_unittest_gate.py 120s). A hung suite must fail the gate, not the run.
  * Skips are forbidden by default, matching the red-team gate. A silently skipped
    security test is indistinguishable from a passing one in a green CI log, and this
    program has already been bitten by a suite that reported green while testing a
    rule set the implementation no longer used.

Usage:
    python 00-shared/tools/run_pytest_gate.py <tests-dir> [--allow-skips] [--timeout N]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

PROGRAM = Path(__file__).resolve().parents[2]
DEFAULT_TIMEOUT = 300


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a pytest suite as a CI gate")
    parser.add_argument("tests", help="path to the tests directory, relative to the program root")
    parser.add_argument("--allow-skips", action="store_true",
                        help="permit skipped tests (default: a skip fails the gate)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
    args = parser.parse_args()

    tests_dir = PROGRAM / args.tests
    if not tests_dir.is_dir():
        print(f"PYTEST GATE: FAIL - tests directory not found: {args.tests}", file=sys.stderr)
        return 1

    # -p no:cacheprovider keeps CI runners from writing .pytest_cache into the tree,
    # which the repository-hygiene gate would then flag as an untracked artifact.
    command = [
        sys.executable, "-m", "pytest", str(tests_dir),
        "-q", "--strict-markers", "-p", "no:cacheprovider",
    ]
    if not args.allow_skips:
        # -r a reports skip reasons so a forbidden skip is actionable, not just fatal.
        command += ["-ra"]

    try:
        proc = subprocess.run(
            command, cwd=str(PROGRAM), capture_output=True, text=True, timeout=args.timeout
        )
    except subprocess.TimeoutExpired:
        print(f"PYTEST GATE: FAIL - {args.tests} exceeded {args.timeout}s", file=sys.stderr)
        return 1

    output = (proc.stdout or "") + (proc.stderr or "")
    print(output, end="" if output.endswith("\n") else "\n")

    if proc.returncode != 0:
        print(f"PYTEST GATE: FAIL - {args.tests} (exit {proc.returncode})", file=sys.stderr)
        return 1

    if not args.allow_skips:
        # pytest summarises as e.g. "31 passed, 1 skipped in 0.53s".
        for marker in (" skipped", " xfailed", " xpassed"):
            if marker in output:
                print(
                    f"PYTEST GATE: FAIL - {args.tests} reported{marker.rstrip('s')} tests; "
                    "skips are forbidden in CI (pass --allow-skips to permit)",
                    file=sys.stderr,
                )
                return 1

    print(f"PYTEST GATE: PASS - {args.tests}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
