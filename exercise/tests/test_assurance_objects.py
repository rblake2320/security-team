from __future__ import annotations

import base64
import json
import sys
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from assurance_objects import sign, validate_rotation_recovery, verify  # noqa: E402


class AssuranceObjectTests(unittest.TestCase):
    def setUp(self) -> None:
        self.keys = {role: Ed25519PrivateKey.generate() for role in ("red_execution", "internal_audit", "white_evidence")}
        self.trust = {}
        for role, private in self.keys.items():
            public = private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            self.trust[f"{role}-key"] = {
                "role": role,
                "status": "active",
                "public_key": base64.b64encode(public).decode("ascii"),
            }
        self.now = datetime.now(UTC)

    def test_red_execution_receipt_is_separate_and_bound_to_authorization(self) -> None:
        body = {
            "schema": "exercise.execution-receipt/1.0",
            "exercise_id": "EX-1",
            "authorization_sha256": "a" * 64,
            "test_case_ids": ["TC-1"],
            "actions_sha256": "b" * 64,
            "started_at": self.now.isoformat(),
            "finished_at": (self.now + timedelta(seconds=1)).isoformat(),
            "key_id": "red_execution-key",
        }
        receipt = sign(body, self.keys["red_execution"])
        self.assertEqual(verify(receipt, self.trust)["authorization_sha256"], "a" * 64)
        receipt["authorization_sha256"] = "c" * 64
        with self.assertRaisesRegex(ValueError, "signature"):
            verify(receipt, self.trust)

    def test_red_key_cannot_sign_assessment(self) -> None:
        body = self._assessment("red_execution-key")
        result = sign(body, self.keys["red_execution"])
        with self.assertRaisesRegex(ValueError, "role"):
            verify(result, self.trust)

    def test_exercise_assurance_signs_complete_assessment(self) -> None:
        body = self._assessment("internal_audit-key")
        result = sign(body, self.keys["internal_audit"])
        self.assertTrue(verify(result, self.trust)["evidence_complete"])
        body["evidence_complete"] = False
        with self.assertRaisesRegex(ValueError, "incomplete"):
            verify(sign(body, self.keys["internal_audit"]), self.trust)

    def test_white_receives_blue_anchor_and_detects_tampering(self) -> None:
        body = {
            "schema": "exercise.audit-anchor-receipt/1.0",
            "source": "sentinel-blue",
            "audit_head": "d" * 64,
            "audit_entries": 3,
            "previous_receipt_sha256": "0" * 64,
            "received_at": self.now.isoformat(),
            "key_id": "white_evidence-key",
        }
        receipt = sign(body, self.keys["white_evidence"])
        self.assertEqual(verify(receipt, self.trust)["audit_head"], "d" * 64)
        receipt["audit_entries"] = 2
        with self.assertRaisesRegex(ValueError, "signature"):
            verify(receipt, self.trust)

    def test_recorded_blue_anchor_receipt_verifies(self) -> None:
        receipt = json.loads((ROOT / "evidence" / "blue_anchor_receipt.json").read_text(encoding="utf-8"))
        record = json.loads(
            (ROOT / "tests" / "fixtures" / "trust" / "fixture-audit-2026.json").read_text(encoding="utf-8")
        )
        trust = {record["key_id"]: {**record, "status": "active"}}
        self.assertEqual(verify(receipt, trust)["source"], "sentinel-blue-engineering-rehearsal")

    def test_rotation_and_holder_unavailable_recovery_for_all_five_keys(self) -> None:
        records = []
        for index, purpose in enumerate(
            ("authorization", "execution", "evidence", "assessment", "emergency_revocation"), start=1
        ):
            records.append({
                "purpose": purpose,
                "old_key_sha256": f"{index:x}" * 64,
                "new_key_sha256": f"{index + 5:x}" * 64,
                "recovered_key_sha256": f"{index + 5:x}" * 64,
                "rotated_at": self.now.isoformat(),
                "recovered_at": (self.now + timedelta(minutes=1)).isoformat(),
                "holder_unavailable_tested": True,
            })
        validate_rotation_recovery(records)
        records[0]["recovered_key_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "reproduce"):
            validate_rotation_recovery(records)

    def _assessment(self, key_id: str) -> dict:
        return {
            "schema": "exercise.assessment-result/1.0",
            "exercise_id": "EX-1",
            "scorecard_sha256": "a" * 64,
            "evidence_manifest_sha256": "b" * 64,
            "evidence_complete": True,
            "scores": {"purple": 0.9},
            "result_marking": "TRAINING_OR_ENGINEERING_USE_ONLY",
            "issued_at": self.now.isoformat(),
            "key_id": key_id,
        }


if __name__ == "__main__":
    unittest.main()
