#!/usr/bin/env python3
"""Static analysis + compile gate. Mirrors the CI step so local runs match.

Added 2026-08-14: ruff and compileall ran in CI but were absent from the gate
manifest, so run_ci.py never executed them and a lint error reached CI. The
manifest must be a SUPERSET of the workflow.
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ["purple-team/src", "purple-team/tests", "red-team/src", "red-team/tests",
           "blue-team/src", "blue-team/tests", "00-shared/tools", "tools", "exercise"]

def main() -> int:
    for cmd in ([sys.executable, "-m", "ruff", "check", *TARGETS],
                [sys.executable, "-m", "compileall", "-q", *TARGETS]):
        p = subprocess.run(cmd, cwd=str(ROOT))
        if p.returncode != 0:
            return p.returncode
    print("static analysis + compile: PASS")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
