"""Falsification tests for EXERCISE-PREFLIGHT-REFUSAL-001.

One negative test per refusal path. Uses EPHEMERAL keys generated at test time;
no production authorization is forged and no White private key exists in the repo.
"""

from __future__ import annotations

import base64
import json
import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

HERE = Path(__file__).resolve().parent
EX = HERE.parent
sys.path.insert(0, str(EX))

import preflight  # noqa: E402
import run_rehearsal  # noqa: E402

NOW = datetime(2026, 8, 14, 12, 0, 0, tzinfo=UTC)


def signed_auth(key: Ed25519PrivateKey, **over) -> dict:
    doc = {
        "schema": "purple.rehearsal-authorization/1.0",
        "exercise_id": "EX-TEST-001",
        "mode": "ENGINEERING_REHEARSAL",
        "assessment_state": "PREREQUISITES_PENDING",
        "result_marking": "TRAINING_OR_ENGINEERING_USE_ONLY",
        "target": "exercise/target",
        "synthetic_data_only": True,
        "network_egress": "blocked",
        "allowed_test_ids": ["TC-IDOR-001"],
        "valid_from": "2026-08-01T00:00:00+00:00",
        "expires_at": "2026-12-31T00:00:00+00:00",
        "key_id": "fixture-white-2026",
    }
    doc.update(over)
    payload = {k: v for k, v in doc.items() if k != "signature"}
    doc["signature"] = base64.b64encode(key.sign(run_rehearsal.canonical(payload))).decode()
    return doc


def fixture_key(key_id: str = "fixture-white-2026") -> Ed25519PrivateKey:
    keys = json.loads((HERE / "fixtures" / "trust" / "_fixture_private_keys.json").read_text(encoding="utf-8"))["keys"]
    return Ed25519PrivateKey.from_private_bytes(base64.b64decode(keys[key_id]))


def full_attestation(**over) -> dict:
    att = {
        "schema": "exercise.environment-attestation/2.0",
        "exercise_id": "EX-TEST-001",
        "environment": "TEST_ONLY",
        "attested_by": "fixture-white-2026",
        "attested_at": NOW.isoformat(),
    }
    for b in json.loads((EX / "config" / "safety_boundaries.json").read_text(encoding="utf-8"))["boundaries"]:
        v = b["required_value"]
        att[b["authorization_field"]] = ["deconflict://IR-DECON-001"] if v == "__non_empty__" else v
    att.update(over)
    body = {key: value for key, value in att.items() if key != "signature"}
    att["signature"] = base64.b64encode(
        fixture_key().sign(b"exercise.environment-attestation.v2" + run_rehearsal.canonical(body))
    ).decode()
    return att


class PreflightTests(unittest.TestCase):

    def setUp(self) -> None:
        self.key = fixture_key()
        self.tmp = EX / "white" / "_test_attestation.json"

    def tearDown(self) -> None:
        if self.tmp.exists():
            self.tmp.unlink()

    def _run(self, auth, attestation=None, mode="ENGINEERING_REHEARSAL", gates=None):
        """Exercise preflight against in-memory objects."""
        preflight.verify_authorization(auth, now=NOW)
        g = gates if gates is not None else preflight.failed_gates()
        spec = preflight.check_mode(auth, mode, g, preflight._load(preflight.MODES))
        preflight.check_revocation(auth, preflight._load(preflight.REVOCATIONS), NOW)
        if attestation is None:
            raise preflight.Refused("SB-MISSING-ATTESTATION", "no signed environment attestation")
        if attestation.get("exercise_id") != auth["exercise_id"]:
            raise preflight.Refused("SB-ATTESTATION-MISMATCH", "exercise mismatch")
        preflight.verify_environment_attestation(
            attestation, mode=mode, exercise_id=auth["exercise_id"], allow_fixtures=True
        )
        preflight.check_boundaries(attestation, preflight._load(preflight.BOUNDARIES))
        return spec

    # ---------- POSITIVE ----------
    def test_clears_when_everything_holds(self):
        spec = self._run(signed_auth(self.key), full_attestation(), gates=[])
        self.assertFalse(spec["assurance_statement_allowed"])
        self.assertEqual(spec["result_marking"], "TRAINING_OR_ENGINEERING_USE_ONLY")

    # ---------- NEGATIVE: authorization ----------
    def test_refuses_invalid_signature(self):
        auth = signed_auth(self.key)
        auth["allowed_test_ids"] = ["TC-SOMETHING-ELSE"]      # payload changed after signing
        with self.assertRaises(ValueError):
            self._run(auth, full_attestation(), gates=[])

    def test_refuses_wrong_signing_key(self):
        with self.assertRaises(ValueError):
            self._run(signed_auth(Ed25519PrivateKey.generate()), full_attestation(), gates=[])

    def test_refuses_tampered_environment_attestation_signature(self):
        attestation = full_attestation()
        attestation["network_egress"] = "allowed"
        with self.assertRaises(preflight.Refused) as ctx:
            self._run(signed_auth(self.key), attestation, gates=[])
        self.assertEqual(ctx.exception.rule, "SB-ATTESTATION-SIGNATURE")

    def test_refuses_expired_authorization(self):
        auth = signed_auth(self.key, expires_at="2026-08-01T00:00:00+00:00")
        with self.assertRaises(ValueError):
            self._run(auth, full_attestation(), gates=[])

    def test_refuses_not_yet_valid_authorization(self):
        auth = signed_auth(self.key, valid_from="2026-12-01T00:00:00+00:00")
        with self.assertRaises(ValueError):
            self._run(auth, full_attestation(), gates=[])

    # ---------- NEGATIVE: revocation ----------
    def test_refuses_when_revoked(self):
        auth = signed_auth(self.key)
        revs = {"revocations": [{"revocation_id": "REV-001", "exercise_id": "EX-TEST-001",
                                 "key_id": "fixture-white-2026", "effective_from": "2026-08-10T00:00:00+00:00",
                                 "reason": "executive revocation"}]}
        with self.assertRaises(preflight.Refused) as ctx:
            preflight.check_revocation(auth, revs, NOW)
        self.assertEqual(ctx.exception.rule, "REVOKED")

    def test_revocation_not_yet_effective_does_not_refuse(self):
        auth = signed_auth(self.key)
        revs = {"revocations": [{"revocation_id": "REV-002", "exercise_id": "EX-TEST-001",
                                 "key_id": "white-rehearsal-2026-01", "effective_from": "2027-01-01T00:00:00+00:00",
                                 "reason": "future"}]}
        preflight.check_revocation(auth, revs, NOW)   # must not raise

    # ---------- NEGATIVE: mode gating ----------
    def test_formal_authorization_refuses_fixture_trust(self):
        auth = signed_auth(
            self.key,
            mode="FORMAL_INTEGRATED_ASSESSMENT",
            assessment_state="ASSESSMENT_READY",
            result_marking="ASSESSMENT_EVIDENCE",
        )
        with self.assertRaises(ValueError):
            preflight.verify_authorization(auth, now=NOW)

    def test_refuses_formal_mode_while_gates_pending(self):
        auth = {"mode": "FORMAL_INTEGRATED_ASSESSMENT", "exercise_id": "EX-TEST-001"}
        with self.assertRaises(preflight.Refused) as ctx:
            preflight.check_mode(auth, "FORMAL_INTEGRATED_ASSESSMENT",
                                 ["key_custody_verified"], preflight._load(preflight.MODES))
        self.assertEqual(ctx.exception.rule, "MODE-NOT-READY")

    def test_refuses_mode_mismatch(self):
        auth = {"mode": "ENGINEERING_REHEARSAL", "exercise_id": "EX-TEST-001"}
        with self.assertRaises(preflight.Refused) as ctx:
            preflight.check_mode(auth, "FORMAL_INTEGRATED_ASSESSMENT", [],
                                 preflight._load(preflight.MODES))
        self.assertEqual(ctx.exception.rule, "MODE-MISMATCH")

    def test_refuses_unknown_mode(self):
        auth = {"mode": "MADE_UP", "exercise_id": "EX-TEST-001"}
        with self.assertRaises(preflight.Refused) as ctx:
            preflight.check_mode(auth, "MADE_UP", [], preflight._load(preflight.MODES))
        self.assertEqual(ctx.exception.rule, "MODE-UNKNOWN")

    def test_formal_mode_gating_clears_only_when_all_gates_verified(self):
        auth = {"mode": "FORMAL_INTEGRATED_ASSESSMENT", "exercise_id": "EX-TEST-001"}
        spec = preflight.check_mode(auth, "FORMAL_INTEGRATED_ASSESSMENT", [],
                                    preflight._load(preflight.MODES))
        self.assertTrue(spec["assurance_statement_allowed"])

    # ---------- NEGATIVE: attestation ----------
    def test_refuses_missing_attestation(self):
        with self.assertRaises(preflight.Refused) as ctx:
            self._run(signed_auth(self.key), None, gates=[])
        self.assertEqual(ctx.exception.rule, "SB-MISSING-ATTESTATION")

    def test_refuses_attestation_for_a_different_exercise(self):
        with self.assertRaises(preflight.Refused) as ctx:
            self._run(signed_auth(self.key), full_attestation(exercise_id="EX-OTHER"), gates=[])
        self.assertEqual(ctx.exception.rule, "SB-ATTESTATION-MISMATCH")

    # ---------- NEGATIVE: every safety boundary, individually ----------
    def test_refuses_each_safety_boundary_independently(self):
        boundaries = json.loads((EX / "config" / "safety_boundaries.json").read_text(encoding="utf-8"))["boundaries"]
        self.assertEqual(len(boundaries), 11, "all eleven boundaries must be enforced")
        for b in boundaries:
            with self.subTest(boundary=b["id"]):
                bad = full_attestation(**{b["authorization_field"]: None})
                with self.assertRaises(preflight.Refused) as ctx:
                    self._run(signed_auth(self.key), bad, gates=[])
                self.assertEqual(ctx.exception.rule, b["id"],
                                 "refusal must name the specific boundary")


if __name__ == "__main__":
    unittest.main(verbosity=2)
