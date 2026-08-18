"""Program history: tamper evidence, comparability, and honest drift."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from program_history import HistoryError, read_history, record, trend, verify_history  # noqa: E402


def rollup(score: float, coverage: float, *, digest="d0", status="SCORED", teams=None):
    return {
        "program_status": status,
        "program_score": score,
        "coverage": coverage,
        "weight_digest": digest,
        "readiness_state": "PREREQUISITES_PENDING",
        "auto_failed_teams": [],
        "teams": teams or [
            {"team": "red", "score": score, "state": "scored", "evidence_completeness": 1.0}
        ],
    }


class TestHistoryIntegrity(unittest.TestCase):
    def test_chain_links_and_verifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.5, 1.0), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.6, 1.0), recorded_at="2026-08-08T00:00:00Z")
            self.assertEqual(verify_history(read_history(path)), 2)

    def test_edited_entry_is_detected(self):
        """A trend line that can be edited after the fact is a story, not evidence."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.4, 1.0), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.5, 1.0), recorded_at="2026-08-08T00:00:00Z")
            lines = path.read_text(encoding="utf-8").splitlines()
            doc = json.loads(lines[0])
            doc["payload"]["program_score"] = 0.1  # flatter the starting point
            lines[0] = json.dumps(doc, sort_keys=True, separators=(",", ":"))
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            with self.assertRaises(HistoryError):
                verify_history(read_history(path))

    def test_reordering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.4, 1.0), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.5, 1.0), recorded_at="2026-08-08T00:00:00Z")
            lines = path.read_text(encoding="utf-8").splitlines()
            path.write_text("\n".join([lines[1], lines[0]]) + "\n", encoding="utf-8")
            with self.assertRaises(HistoryError):
                verify_history(read_history(path))

    def test_recording_onto_a_broken_history_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            path.write_text('{"sequence":0,"prev_hash":"x","entry_hash":"y","payload":{}}\n',
                            encoding="utf-8")
            with self.assertRaises(HistoryError):
                record(path, rollup(0.5, 1.0), recorded_at="2026-08-01T00:00:00Z")


class TestComparability(unittest.TestCase):
    def test_a_weight_change_makes_two_rollups_incomparable(self):
        """Rule 5 allows weights to change via governance. Plotting movement across
        that change would be inventing a trend."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.5, 1.0, digest="old"), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.9, 1.0, digest="new"), recorded_at="2026-08-08T00:00:00Z")
            result = trend(read_history(path))
            self.assertFalse(result["movements"][0]["comparable"])
            self.assertIsNone(result["movements"][0]["score_delta"])
            self.assertIsNone(result["overall_score_delta"])
            self.assertTrue(any("NOT comparable" in n for n in result["notes"]))


class TestHonestDrift(unittest.TestCase):
    def test_rising_score_with_falling_coverage_is_called_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.60, 1.00), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.95, 0.30), recorded_at="2026-08-08T00:00:00Z")
            notes = trend(read_history(path))["notes"]
            self.assertTrue(any("narrower assessment" in n for n in notes), notes)

    def test_per_team_regression_is_surfaced_under_a_rising_total(self):
        """The headline improving while a team gets worse is the case a single
        number hides."""
        before = [
            {"team": "red", "score": 0.9, "state": "scored", "evidence_completeness": 1.0},
            {"team": "blue", "score": 0.5, "state": "scored", "evidence_completeness": 1.0},
        ]
        after = [
            {"team": "red", "score": 0.4, "state": "scored", "evidence_completeness": 1.0},
            {"team": "blue", "score": 1.0, "state": "scored", "evidence_completeness": 1.0},
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.70, 1.0, teams=before), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.75, 1.0, teams=after), recorded_at="2026-08-08T00:00:00Z")
            result = trend(read_history(path))
            self.assertGreater(result["overall_score_delta"], 0)
            self.assertIn("red -0.5", result["movements"][0]["team_regressions"])

    def test_empty_history_reports_nothing_rather_than_zero(self):
        self.assertEqual(trend([])["entries"], 0)

    def test_overall_delta_across_a_stable_weight_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "h.jsonl"
            record(path, rollup(0.40, 1.0), recorded_at="2026-08-01T00:00:00Z")
            record(path, rollup(0.55, 1.0), recorded_at="2026-08-08T00:00:00Z")
            self.assertAlmostEqual(trend(read_history(path))["overall_score_delta"], 0.15, places=6)


if __name__ == "__main__":
    unittest.main()
