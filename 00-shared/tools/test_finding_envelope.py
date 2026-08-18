"""Cross-team finding transfer: lossy is acceptable, inventing is not."""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
PROGRAM = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROGRAM / "yellow-team" / "src"))

from finding_envelope import EnvelopeError, from_orange, from_red, to_yellow  # noqa: E402

RED_DOC = {
    "engagement_id": "E1",
    "results": [{
        "check_id": "repository.posture",
        "findings": [
            {
                "title": "Dependency is not exactly pinned",
                "severity": "high",
                "description": "unpinned-dependency matched in requirements.txt:1",
                "remediation": "Pin and hash-lock the reviewed artifact.",
                "cwe": "CWE-1104",
                "attack": "T1195.002",
                "check_id": "repository.posture",
                "evidence": {"file": "requirements.txt", "line": 1, "rule_id": "unpinned-dependency"},
            },
            {
                "title": "Possible hard-coded credential",
                "severity": "high",
                "description": "generic-secret-assignment matched in src/worker.js:7960",
                "remediation": "",
                "evidence": {"file": "src/worker.js", "line": 7960, "rule_id": "generic-secret-assignment"},
            },
        ],
    }],
}

ORANGE_DOC = {
    "review_id": "R1",
    "found_paths": [
        {"path_id": "AH-01", "title": "Unbounded audit growth", "severity": "high",
         "stride_category": "denial_of_service", "entry_point": "POST /api/*",
         "impact": "storage exhaustion"},
        {"path_id": "AH-09", "title": "Minor info leak", "severity": "low",
         "stride_category": "information_disclosure", "entry_point": "GET /x",
         "impact": "banner"},
    ],
    "recommendations": [
        {"recommendation_id": "R-1", "path_id": "AH-01", "severity": "high",
         "action": "Add retention", "acceptance_criteria": "Old rows pruned, evidence kept"},
    ],
}


class TestRedAdapter(unittest.TestCase):
    def test_carries_remediation_across_as_acceptance_criteria(self):
        items = from_red(RED_DOC)
        pinned = next(i for i in items if "unpinned" in i["finding_id"])
        self.assertEqual(pinned["acceptance_criteria"], "Pin and hash-lock the reviewed artifact.")
        self.assertEqual(pinned["severity"], "high")
        self.assertEqual(pinned["location"], "requirements.txt:1")

    def test_does_not_invent_criteria_when_red_supplies_none(self):
        items = from_red(RED_DOC)
        secret = next(i for i in items if "generic-secret" in i["finding_id"])
        self.assertEqual(secret["acceptance_criteria"], "")

    def test_finding_ids_are_unique_even_for_repeated_rules(self):
        doc = {"results": [{"findings": [
            dict(RED_DOC["results"][0]["findings"][0]),
            dict(RED_DOC["results"][0]["findings"][0]),
        ]}]}
        ids = [i["finding_id"] for i in from_red(doc)]
        self.assertEqual(len(ids), len(set(ids)))

    def test_long_paths_do_not_collide_after_id_truncation(self):
        """Yellow caps finding_id at 64 chars. Truncating a long path collapsed 14
        distinct findings into one id the first time this adapter ran for real."""
        long_dir = "test-coverage-analysis/a-very-long-file-name-that-exceeds-the-limit"
        doc = {"results": [{"findings": [
            {"title": "secret", "severity": "low", "remediation": "",
             "evidence": {"file": f"{long_dir}/file.ts", "line": line,
                          "rule_id": "generic-secret-assignment"}}
            for line in (10, 20, 30, 40)
        ]}]}
        ids = [i["finding_id"] for i in from_red(doc)]
        self.assertEqual(len(ids), len(set(ids)), f"ids collided: {ids}")
        self.assertTrue(all(len(i) <= 64 for i in ids))

    def test_unknown_severity_is_refused(self):
        doc = {"results": [{"findings": [{"title": "x", "severity": "spicy", "evidence": {}}]}]}
        with self.assertRaises(EnvelopeError):
            from_red(doc)


class TestOrangeAdapter(unittest.TestCase):
    def test_matches_acceptance_criteria_to_its_attack_path(self):
        items = from_orange(ORANGE_DOC)
        first = next(i for i in items if i["finding_id"] == "AH-01")
        self.assertEqual(first["acceptance_criteria"], "Old rows pruned, evidence kept")
        self.assertEqual(first["references"]["stride_category"], "denial_of_service")

    def test_path_without_a_recommendation_gets_no_criteria(self):
        items = from_orange(ORANGE_DOC)
        orphan = next(i for i in items if i["finding_id"] == "AH-09")
        self.assertEqual(orphan["acceptance_criteria"], "")


class TestTransferToYellow(unittest.TestCase):
    def test_high_finding_without_criteria_is_refused_not_fabricated(self):
        """Yellow's contract is that a high finding carries a completion bar.
        Inventing one at the boundary would defeat the control."""
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "r.jsonl"
            result = to_yellow(from_red(RED_DOC), register, at="2026-08-18T00:00:00Z")
            opened = result["opened"]
            self.assertEqual(len(opened), 1)
            self.assertTrue(opened[0].startswith("RED-unpinned-dependency-"), opened)
            self.assertEqual(result["skipped_count"], 1)
            self.assertIn("no acceptance criteria", result["skipped"][0]["reason"])

    def test_low_finding_transfers_without_criteria(self):
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "r.jsonl"
            result = to_yellow(from_orange(ORANGE_DOC), register, at="2026-08-18T00:00:00Z")
            self.assertIn("AH-09", result["opened"])
            self.assertIn("AH-01", result["opened"])

    def test_transfer_is_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "r.jsonl"
            items = from_orange(ORANGE_DOC)
            to_yellow(items, register, at="2026-08-18T00:00:00Z")
            second = to_yellow(items, register, at="2026-08-18T01:00:00Z")
            self.assertEqual(second["opened"], [])
            self.assertEqual(second["skipped_count"], 2)

    def test_transferred_findings_land_in_a_verifiable_register(self):
        from aegis_yellow.register import FindingsRegister  # noqa: PLC0415
        with tempfile.TemporaryDirectory() as tmp:
            register = Path(tmp) / "r.jsonl"
            to_yellow(from_orange(ORANGE_DOC), register, at="2026-08-18T00:00:00Z")
            reg = FindingsRegister(register)
            self.assertEqual(reg.ledger.verify(), 2)
            self.assertEqual(reg.findings()["AH-01"].severity, "high")


if __name__ == "__main__":
    unittest.main()
