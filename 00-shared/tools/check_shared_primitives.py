#!/usr/bin/env python3
"""Guard: shared primitives copied across team packages must not drift.

`canonical.py` and `ledger.py` are byte-identical copies in several team packages.
That duplication is deliberate - each team ships as an independently installable
package with its own canonical identity, and a shared runtime dependency would
complicate that - but a copy nobody checks is a copy that diverges.

This program already learned that lesson expensively: `crucible_tests.js` inlined a
copy of `scanForInjection` and silently fell one detection pattern behind the
implementation, so the suite was green while testing rules the code no longer used.
The fix there was a CI guard, not a refactor. This is the same guard for the same
failure class.

A file is only compared where it exists in more than one package; a package that
legitimately has no `ledger.py` is not a violation.

Usage:
    python 00-shared/tools/check_shared_primitives.py
"""
from __future__ import annotations

import hashlib
import sys
from collections import defaultdict
from pathlib import Path

PROGRAM = Path(__file__).resolve().parents[2]

# Primitives that are copied rather than shared. Add to this list whenever another
# file is duplicated across packages, or the guard will not know to watch it.
SHARED_PRIMITIVES = ("canonical.py", "ledger.py")

PACKAGES = {
    "purple": "purple-team/src/aegis_purple",
    "white": "white-team/src/aegis_white",
    "yellow": "yellow-team/src/aegis_yellow",
    "green": "green-team/src/aegis_green",
    "orange": "orange-team/src/aegis_orange",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    violations: list[str] = []
    checked = 0

    for filename in SHARED_PRIMITIVES:
        by_hash: dict[str, list[str]] = defaultdict(list)
        for team, package in PACKAGES.items():
            candidate = PROGRAM / package / filename
            if not candidate.is_file():
                continue
            by_hash[digest(candidate)].append(f"{team} ({package}/{filename})")

        copies = sum(len(v) for v in by_hash.values())
        if copies < 2:
            continue
        checked += 1
        if len(by_hash) > 1:
            detail = "; ".join(
                f"[{h[:12]}] " + ", ".join(sorted(owners)) for h, owners in sorted(by_hash.items())
            )
            violations.append(f"{filename} has diverged across packages: {detail}")

    if violations:
        print("SHARED PRIMITIVE CHECK: FAIL", file=sys.stderr)
        for violation in violations:
            print(f"  {violation}", file=sys.stderr)
        print(
            "  Copies must stay byte-identical. Update every copy together, or move the "
            "file into a single shared module and delete the duplicates.",
            file=sys.stderr,
        )
        return 1

    print(f"SHARED PRIMITIVE CHECK: PASS ({checked} primitive(s) identical across packages)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
