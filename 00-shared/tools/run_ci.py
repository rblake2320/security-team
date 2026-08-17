#!/usr/bin/env python3
"""Local CI runner. Executes every gate without depending on GitHub.

    python 00-shared/tools/run_ci.py              # engineering gates (hold permitted)
    python 00-shared/tools/run_ci.py --assurance  # assurance gate (fails closed)
    python 00-shared/tools/run_ci.py --json       # machine-readable result

Exit 0 = all gates pass. Exit 1 = a gate failed.

WHY THIS EXISTS
    On 2026-08-14 the program's CI workflows were found at
    `.github/workflows/`. GitHub Actions reads only
    `<repo-root>/.github/workflows/`, so they were inert and had never run. Every
    claim whose evidence was "CI enforces X" was unevidenced.

    A root-level workflow now exists, but it runs only when the repository is pushed
    to a host that executes Actions. This runner makes the same gates enforceable on
    the machine, today, with no external dependency.

SINGLE SOURCE OF TRUTH
    The gate list lives in 00-shared/config/ci_gates.json. This runner and the root
    workflow both derive from it, and test_gate_manifest.py fails if they drift.
    Two hand-maintained gate lists always diverge eventually.

Claim: PROGRAM-CI-REACHABLE-001
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import job_guard  # noqa: E402

PROGRAM = Path(__file__).resolve().parents[2]
MANIFEST = PROGRAM / "00-shared" / "config" / "ci_gates.json"

# Explicit, matching the value this file already used before job_guard was wired in
# (see the comment this replaced) - not job_guard's own default, so the budget stays
# a visible constant here rather than an implicit value a future caller could rely
# on without knowing it.
GATE_TIMEOUT_SECONDS = 1200


def load_gates(assurance: bool) -> list[dict]:
    doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
    return doc["assurance_gates" if assurance else "engineering_gates"]


def build_command(gate: dict) -> list[str]:
    if gate["kind"] == "unittest":
        return [sys.executable, "-m", "unittest", "discover",
                "-s", gate["path"], "-p", gate["pattern"]]
    if gate["kind"] == "command":
        return [sys.executable, *gate["argv"]]
    raise ValueError(f"unknown gate kind: {gate['kind']}")


def run_gate(gate: dict) -> tuple[bool, float, str]:
    env = dict(os.environ)
    if gate.get("pythonpath"):
        env["PYTHONPATH"] = str(PROGRAM / gate["pythonpath"])
    t0 = time.time()
    # Kernel-enforced process/memory ceiling, not just a subprocess timeout. Built in
    # direct response to the 2026-08-15 incident this exact gate sequence caused: a
    # recursive spawn produced 100+ processes before the host became unresponsive.
    # A plain subprocess timeout bounds WALL TIME but nothing stops a runaway process
    # tree from exhausting memory or the process table well before the timeout fires.
    # job_guard wraps the whole tree the gate spawns - not just its direct child - in
    # a Windows Job Object / POSIX RLIMIT_NPROC ceiling enforced by the OS at
    # process-creation time.
    #
    # Output capture is file-based, not pipe-based (2026-08-17 fix): a pipe deadlocks
    # here whenever a gate's own descendants spawn further subprocesses (confirmed on
    # two gates - the multiprocessing-based nonce-race test, and claim_check.py's own
    # pytest sub-spawn) because Windows inherits the pipe write-handle into every
    # descendant, and Python's close_fds=True does not protect stdin/stdout/stderr by
    # design. See job_guard.py's own comment for the full mechanism.
    result = job_guard.run_guarded(
        build_command(gate), cwd=str(PROGRAM), env=env, timeout=GATE_TIMEOUT_SECONDS,
    )
    if result.timed_out:
        output = (result.stdout + result.stderr).strip()
        return False, time.time() - t0, (
            output + f"\nTIMED OUT / RESOURCE-CAPPED after {GATE_TIMEOUT_SECONDS}s"
        ).strip()
    return result.returncode == 0, time.time() - t0, (result.stdout + result.stderr).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--assurance", action="store_true",
                    help="run the assurance gate, which fails closed while gates are pending")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    gates = load_gates(args.assurance)
    label = "ASSURANCE" if args.assurance else "ENGINEERING"
    width = max(len(g["name"]) for g in gates)
    results, failures = [], []

    if not args.json:
        print(f"local CI - {label} gates - {PROGRAM.name}")

    for gate in gates:
        ok, elapsed, output = run_gate(gate)
        results.append({"id": gate["id"], "name": gate["name"],
                        "passed": ok, "seconds": round(elapsed, 2)})
        if not ok:
            failures.append(gate["name"])
        if args.json:
            continue
        print(f"  [{'PASS' if ok else 'FAIL'}] {gate['name']:<{width}}  {elapsed:5.2f}s")
        if not ok:
            for line in output.splitlines()[-6:]:
                print(f"         | {line}")
        elif args.verbose:
            for line in output.splitlines()[-2:]:
                print(f"         | {line}")

    summary = {"mode": label, "gates": len(gates), "failed": len(failures), "results": results}
    if args.json:
        print(json.dumps(summary, indent=2))
        return 1 if failures else 0

    print()
    if failures:
        print(f"RESULT: FAIL - {len(failures)} gate(s) failed")
        return 1
    if args.assurance:
        print("RESULT: assurance gate PASSED - all readiness gates are VERIFIED")
    else:
        print("RESULT: engineering gates PASSED")
        print("        Assurance remains prohibited while readiness gates are pending.")
        print("        Run with --assurance to check the fail-closed path.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
