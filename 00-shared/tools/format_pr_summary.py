#!/usr/bin/env python3
"""Format `run_ci.py --json` output as a Markdown PR comment.

    python 00-shared/tools/run_ci.py --json | python 00-shared/tools/format_pr_summary.py

Closes a real gap this program had: every gate result was visible only in the
Actions logs/checks tab, never on the PR itself where a reviewer is actually
looking. This posts what a generic code-review bot cannot - this program's own
specific assurance model (R1-R7 claim verification, readiness-gate state), not
generic style/security commentary.

ASCII-only output by design: this gets piped through Windows terminals and
`gh pr comment`, and non-ASCII punctuation (em dashes, curly quotes) has broken
rendering in that path before - plain hyphens throughout, no exceptions.

Reads JSON from stdin (matches `run_ci.py --json`'s exact shape) so this stays
decoupled from run_ci.py and testable without invoking a real CI run. Prints
Markdown to stdout; the caller pipes it into `gh pr comment` or the GitHub API.
"""
from __future__ import annotations

import json
import sys


def format_summary(data: dict) -> str:
    gates = data.get("results", [])
    failed = data.get("failed", 0)
    mode = data.get("mode", "ENGINEERING")
    total = data.get("gates", len(gates))

    status_emoji = ":white_check_mark:" if failed == 0 else ":x:"
    lines = [
        f"## {status_emoji} Engineering gates - {mode}",
        "",
        f"**{total - failed}/{total} passed** in "
        f"{sum(g.get('seconds', 0) for g in gates):.1f}s total.",
        "",
    ]

    if failed:
        lines += ["### Failed gates", ""]
        for g in gates:
            if not g.get("passed", True):
                lines.append(f"- :x: **{g['name']}** ({g.get('seconds', 0):.2f}s)")
        lines.append("")

    lines += ["<details><summary>All gate results</summary>", "", "| Gate | Result | Time |",
               "|---|---|---|"]
    for g in gates:
        mark = ":white_check_mark:" if g.get("passed", True) else ":x:"
        lines.append(f"| {g['name']} | {mark} | {g.get('seconds', 0):.2f}s |")
    lines += ["", "</details>", ""]

    lines += [
        "---",
        "*Posted automatically by this repo's own gate suite - the "
        "R1-R7 assurance-claim model, readiness-gate state, and resource-safety "
        "checks are specific to this program, not a generic linter.*",
    ]
    return "\n".join(lines)


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"format_pr_summary: could not parse input as JSON: {exc}", file=sys.stderr)
        return 1
    print(format_summary(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
