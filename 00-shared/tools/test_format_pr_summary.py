"""Falsification tests for format_pr_summary.py's Markdown output.

format_pr_summary.py posts gate results onto the PR itself, piped through
`gh pr comment` from a Windows terminal in this program's toolchain. That path
has broken non-ASCII punctuation before (em dashes rendering as replacement
characters on this machine's console) - the ASCII-only requirement is load-
bearing, not stylistic, so it gets its own regression test rather than being
left to a code-review comment that can silently regress.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
SCRIPT = TOOLS / "format_pr_summary.py"

sys.path.insert(0, str(TOOLS))
import format_pr_summary as fps  # noqa: E402


def sample_data(failed: int = 0) -> dict:
    results = [
        {"id": "a", "name": "gate a", "passed": True, "seconds": 1.23},
        {"id": "b", "name": "gate b", "passed": failed == 0, "seconds": 4.56},
        {"id": "c", "name": "gate c", "passed": True, "seconds": 0.12},
    ]
    return {"mode": "ENGINEERING", "gates": len(results), "failed": failed, "results": results}


class FormatSummaryTests(unittest.TestCase):

    def test_output_is_pure_ascii(self):
        """NEGATIVE. No em dashes, curly quotes, or other non-ASCII punctuation."""
        out = fps.format_summary(sample_data(failed=1))
        self.assertTrue(
            out.isascii(),
            "format_summary() emitted a non-ASCII character - this has broken "
            "rendering through gh pr comment on this toolchain before")

    def test_all_gates_passing_shows_no_failed_section(self):
        out = fps.format_summary(sample_data(failed=0))
        self.assertNotIn("Failed gates", out)
        self.assertIn(":white_check_mark: Engineering gates", out)

    def test_a_failure_is_listed_by_name(self):
        out = fps.format_summary(sample_data(failed=1))
        self.assertIn("Failed gates", out)
        self.assertIn("gate b", out)
        self.assertIn(":x: Engineering gates", out)

    def test_every_gate_appears_in_the_results_table(self):
        out = fps.format_summary(sample_data(failed=1))
        for name in ("gate a", "gate b", "gate c"):
            self.assertIn(name, out)

    def test_main_rejects_invalid_json_with_exit_1(self):
        """NEGATIVE. Malformed input must fail loudly, not print a blank comment."""
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="not json", capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1)
        self.assertEqual(proc.stdout, "")

    def test_main_end_to_end_via_stdin(self):
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=json.dumps(sample_data(failed=0)), capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("3/3 passed", proc.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
