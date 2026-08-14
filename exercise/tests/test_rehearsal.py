from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import base64 as _b64  # noqa: E402

import clearance as clr  # noqa: E402
sys.path.insert(0, str(ROOT / "tests" / "fixtures"))
from make_fixture_trust import ensure as _ensure_fixture_trust  # noqa: E402
_ensure_fixture_trust()   # a fresh clone has no fixture keys; generate them
from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402
from run_rehearsal import (  # noqa: E402
    AUTH_FIELDS,
    MANIFEST_PATHS,
    RUNNER_IDENTITY,
    canonical,
    load,
    run,
    verify_authorization,
)

_NOW = datetime.fromisoformat("2026-08-14T12:00:00-05:00")


def _fixture_clearance(now=_NOW):
    """Engineering-mode clearance signed with a TEST_ONLY fixture key.

    The runner requires a clearance; production authorities have not enrolled, so a
    fixture key is used. It is marked TEST_ONLY and can never satisfy formal mode.
    """
    raw = json.loads((ROOT / "tests" / "fixtures" / "trust" / "_fixture_private_keys.json")
                     .read_text(encoding="utf-8"))["keys"]["fixture-clearance-2026"]
    key = Ed25519PrivateKey.from_private_bytes(_b64.b64decode(raw))
    auth = load(ROOT / "white" / "authorization.json")
    return clr.issue(exercise_id=auth["exercise_id"], mode=auth["mode"], authorization=auth,
                     manifest_paths=MANIFEST_PATHS, scope=auth["allowed_test_ids"],
                     signing_key=key, signing_key_id="fixture-clearance-2026",
                     runner_identity=RUNNER_IDENTITY, now=now)


class RehearsalTests(unittest.TestCase):
    def test_orange_prediction_becomes_actionable_test_and_retest(self) -> None:
        path = ROOT / "evidence" / "_test_clearance.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(_fixture_clearance()), encoding="utf-8")
        try:
            result = run(write_evidence=False, now=_NOW, clearance_path=path, consume_nonce=False)
        finally:
            path.unlink(missing_ok=True)
        self.assertTrue(result["orange_prediction_confirmed"])
        self.assertTrue(result["remediation_effective"])
        self.assertTrue(result["all_stages_evidenced"])
        self.assertFalse(result["network_activity"])

    def test_authorization_tampering_is_rejected(self) -> None:
        authorization = load(ROOT / "white" / "authorization.json")
        tampered = copy.deepcopy(authorization)
        tampered["network_egress"] = "allowed"
        with self.assertRaises(ValueError):
            verify_authorization(tampered)

    def test_formal_mode_runner_accepts_only_production_roles_when_gates_are_clear(self) -> None:
        white_key = Ed25519PrivateKey.generate()
        clearance_key = Ed25519PrivateKey.generate()
        auth = {
            "schema": "purple.rehearsal-authorization/1.0",
            "exercise_id": "EX-FORMAL-PATH-001",
            "mode": "FORMAL_INTEGRATED_ASSESSMENT",
            "assessment_state": "ASSESSMENT_READY",
            "result_marking": "ASSESSMENT_EVIDENCE",
            "target": "exercise/target",
            "synthetic_data_only": True,
            "network_egress": "blocked",
            "allowed_test_ids": ["TC-IDOR-001"],
            "valid_from": "2026-08-01T00:00:00+00:00",
            "expires_at": "2026-12-31T00:00:00+00:00",
            "key_id": "prod-white-ciso-test",
        }
        auth["signature"] = _b64.b64encode(white_key.sign(canonical(auth))).decode()
        self.assertEqual(set(auth), AUTH_FIELDS)
        original_store = clr.PROD_TRUST
        nonce_backup = clr.NONCE_LEDGER.read_bytes() if clr.NONCE_LEDGER.exists() else None
        try:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                clr.PROD_TRUST = root / "trust"
                clr.PROD_TRUST.mkdir()
                for key_id, role, private in (
                    ("prod-white-ciso-test", "white_ciso", white_key),
                    ("prod-clearance-test", "clearance_issuer", clearance_key),
                ):
                    public = private.public_key().public_bytes(
                        serialization.Encoding.Raw, serialization.PublicFormat.Raw
                    )
                    record = {
                        "key_id": key_id,
                        "role": role,
                        "environment": "PRODUCTION",
                        "public_key": _b64.b64encode(public).decode(),
                    }
                    (clr.PROD_TRUST / f"{key_id}.json").write_text(json.dumps(record), encoding="utf-8")
                auth_path = root / "authorization.json"
                auth_path.write_text(json.dumps(auth), encoding="utf-8")
                signed_clearance = clr.issue(
                    exercise_id=auth["exercise_id"],
                    mode=auth["mode"],
                    authorization=auth,
                    manifest_paths=MANIFEST_PATHS,
                    scope=auth["allowed_test_ids"],
                    signing_key=clearance_key,
                    signing_key_id="prod-clearance-test",
                    runner_identity=RUNNER_IDENTITY,
                    now=_NOW,
                )
                clearance_path = root / "clearance.json"
                clearance_path.write_text(json.dumps(signed_clearance), encoding="utf-8")
                result = run(
                    write_evidence=False,
                    now=_NOW,
                    clearance_path=clearance_path,
                    authorization_path=auth_path,
                    allow_fixtures=False,
                    consume_nonce=False,
                )
                self.assertEqual(result["result_marking"], "ASSESSMENT_EVIDENCE")
        finally:
            clr.PROD_TRUST = original_store
            if nonce_backup is None:
                clr.NONCE_LEDGER.unlink(missing_ok=True)
            else:
                clr.NONCE_LEDGER.write_bytes(nonce_backup)

    def test_every_orange_path_maps_to_red_blue_fix_control_and_retest(self) -> None:
        abuse_cases = json.loads((ROOT / "orange" / "abuse_cases.json").read_text(encoding="utf-8"))
        for case in abuse_cases:
            self.assertTrue(case["red_test_id"].startswith("TC-"))
            self.assertTrue(case["blue_detection_id"].startswith("DET-"))
            self.assertTrue(case["yellow_fix_id"].startswith("FIX-"))
            self.assertTrue(case["green_control_id"].startswith("CTRL-"))
            self.assertTrue(case["retest_id"].startswith("RT-"))

    def test_revocation_halts_running_exercise_at_next_safety_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            revocations = root / "revocations.json"
            revocations.write_text(json.dumps({"schema": "exercise.revocations/1.0", "revocations": []}))
            auth = load(ROOT / "white" / "authorization.json")
            raw = json.loads(
                (ROOT / "tests" / "fixtures" / "trust" / "_fixture_private_keys.json").read_text()
            )["keys"]["fixture-clearance-2026"]
            key = Ed25519PrivateKey.from_private_bytes(_b64.b64decode(raw))
            signed_clearance = clr.issue(
                exercise_id=auth["exercise_id"],
                mode=auth["mode"],
                authorization=auth,
                manifest_paths=MANIFEST_PATHS,
                scope=auth["allowed_test_ids"],
                signing_key=key,
                signing_key_id="fixture-clearance-2026",
                runner_identity=RUNNER_IDENTITY,
                now=_NOW,
                revocations_path=revocations,
            )
            clearance_path = root / "clearance.json"
            clearance_path.write_text(json.dumps(signed_clearance))

            def revoke(boundary: str) -> None:
                if boundary == "after_baseline":
                    revocations.write_text(json.dumps({
                        "schema": "exercise.revocations/1.0",
                        "revocations": [{
                            "revocation_id": "REV-RUNNING-001",
                            "exercise_id": auth["exercise_id"],
                            "key_id": auth["key_id"],
                            "effective_from": "2026-08-14T00:00:00+00:00",
                            "reason": "test emergency stop",
                        }],
                    }))

            with self.assertRaisesRegex(clr.ClearanceError, "REVOKED.*after_baseline"):
                run(
                    write_evidence=False,
                    now=_NOW,
                    clearance_path=clearance_path,
                    revocations_path=revocations,
                    boundary_hook=revoke,
                    consume_nonce=False,
                )


if __name__ == "__main__":
    unittest.main()
