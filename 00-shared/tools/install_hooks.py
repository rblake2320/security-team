#!/usr/bin/env python3
"""Install (or chain) the pre-commit gate into this repository's hooks directory.

    python 00-shared/tools/install_hooks.py            # install or report
    python 00-shared/tools/install_hooks.py --force    # chain onto an existing hook

Enforcement that depends on a human remembering is not enforcement. This makes the
engineering gates run automatically whenever program files are staged.

CHAINING, NOT CLOBBERING
    This repository already carries a PKA workspace hook. Overwriting a shared hook
    to install your own is a destructive act dressed up as setup. When a hook exists,
    the program's block is inserted BEFORE its final `exit 0` - appending after it
    would never execute - and the existing checks continue to run first.
"""

from __future__ import annotations

import argparse
import re
import shutil
import stat
import subprocess
from pathlib import Path

PROGRAM = Path(__file__).resolve().parents[2]
SRC = Path(__file__).resolve().parent / "hooks" / "pre-commit"
MARK = '# --- purple-team gate (managed by "Purple team/00-shared/tools/install_hooks.py") ---'
END = "# --- end purple-team gate ---"


def gate_block() -> str:
    """The program's block, extracted from the standalone hook template."""
    text = SRC.read_text(encoding="utf-8")
    start = text.index("if git diff --cached")
    return f"\n{MARK}\n" + text[start:].rstrip() + f"\n{END}\n"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true",
                    help="chain the gate onto an existing hook")
    args = ap.parse_args()

    proc = subprocess.run(["git", "rev-parse", "--git-path", "hooks"],
                          cwd=str(PROGRAM), capture_output=True, text=True)
    if proc.returncode != 0:
        print("not a git repository; nothing to install")
        return 1

    hooks = (PROGRAM / proc.stdout.strip()).resolve()
    hooks.mkdir(parents=True, exist_ok=True)
    dest = hooks / "pre-commit"

    if dest.exists():
        existing = dest.read_text(encoding="utf-8")
        if MARK in existing:
            print(f"purple-team gate already chained onto {dest}")
            return 0
        if not args.force:
            print(f"a pre-commit hook already exists at {dest}")
            print("CHAINING is the correct action - never clobber a shared workspace hook.")
            print("Re-run with --force to insert the purple-team gate into it.")
            return 1

        # Insert before the final `exit 0`; appending after it would never run.
        m = list(re.finditer(r"^exit 0\s*$", existing, re.M))
        if m:
            cut = m[-1].start()
            merged = existing[:cut] + gate_block() + "\n" + existing[cut:]
        else:
            merged = existing.rstrip() + "\n" + gate_block()
        dest.write_text(merged, encoding="utf-8")
        print(f"chained purple-team gate onto the existing hook at {dest}")
        print("the pre-existing checks still run first and are untouched")
        return 0

    shutil.copyfile(SRC, dest)
    dest.chmod(dest.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"installed pre-commit gate -> {dest}")
    print("staged program changes will now run the engineering gates automatically")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
