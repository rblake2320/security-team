from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--tests", type=Path, required=True)
    parser.add_argument("--forbid-skips", action="store_true")
    args = parser.parse_args()
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(args.source.resolve())
    process = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(args.tests), "-v"],
        env=environment,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    output = process.stdout + process.stderr
    print(output, end="")
    if process.returncode:
        return process.returncode
    if args.forbid_skips and (" ... skipped " in output or "OK (skipped=" in output):
        print("ERROR: a security-boundary test skipped; CI treats skip as failure", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

