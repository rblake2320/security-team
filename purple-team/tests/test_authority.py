from __future__ import annotations

import base64
import secrets
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from aegis_purple.authority import verify_transition_envelope
from aegis_purple.canonical import canonical_bytes, sha256
from aegis_purple.errors import TransitionError
from aegis_purple.models import ExercisePlan
from aegis_purple.store import ExerciseStore
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from test_models import plan_data


class AuthorityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private = Ed25519PrivateKey.generate()
        public = self.private.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw,
        )
        self.registry = {
            "schema": "aegis.purple.role-trust/1.0",
            "keys": [{
                "key_id": "white-2026-01",
                "role": "white",
                "status": "active",
                "public_key_base64": base64.b64encode(public).decode("ascii"),
            }],
        }
        data = plan_data()
        data["role_trust_sha256"] = sha256(self.registry)
        self.plan = ExercisePlan.from_dict(data)

    def envelope(self) -> dict:
        now = datetime.now(UTC)
        payload = {
            "schema": "aegis.purple.transition/1.0",
            "exercise_id": self.plan.exercise_id,
            "plan_sha256": self.plan.digest,
            "from_state": "FROZEN",
            "to_state": "AUTHORIZED",
            "actor_id": "white-director",
            "actor_role": "white",
            "reason": "approved under signed rules of engagement",
            "nonce": secrets.token_hex(16),
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=2)).isoformat(),
            "key_id": "white-2026-01",
        }
        signature = self.private.sign(canonical_bytes(payload))
        return {**payload, "signature": base64.b64encode(signature).decode("ascii")}

    def test_valid_signed_transition_and_replay_rejection(self) -> None:
        command = verify_transition_envelope(self.envelope(), self.registry)
        with tempfile.TemporaryDirectory() as directory, ExerciseStore(Path(directory) / "purple.db") as store:
            store.create_exercise(self.plan, actor_id="purple-lead")
            store.apply_authorized_transition(command, role_trust_sha256=sha256(self.registry))
            self.assertEqual(store.status(self.plan.exercise_id)["state"], "AUTHORIZED")
            self.assertTrue(store.verify()["valid"])
            with self.assertRaises(TransitionError):
                store.apply_authorized_transition(command, role_trust_sha256=sha256(self.registry))

    def test_unpinned_role_registry_is_rejected(self) -> None:
        command = verify_transition_envelope(self.envelope(), self.registry)
        with tempfile.TemporaryDirectory() as directory, ExerciseStore(Path(directory) / "purple.db") as store:
            store.create_exercise(self.plan, actor_id="purple-lead")
            with self.assertRaises(TransitionError):
                store.apply_authorized_transition(command, role_trust_sha256="0" * 64)

    def test_tampered_transition_is_rejected(self) -> None:
        envelope = self.envelope()
        envelope["to_state"] = "STOPPED"
        with self.assertRaises(TransitionError):
            verify_transition_envelope(envelope, self.registry)

    def test_role_key_mismatch_is_rejected(self) -> None:
        envelope = self.envelope()
        self.registry["keys"][0]["role"] = "purple"
        with self.assertRaises(TransitionError):
            verify_transition_envelope(envelope, self.registry)

    def test_long_lived_command_is_rejected(self) -> None:
        envelope = self.envelope()
        envelope["expires_at"] = (datetime.now(UTC) + timedelta(hours=1)).isoformat()
        payload = {key: value for key, value in envelope.items() if key != "signature"}
        envelope["signature"] = base64.b64encode(self.private.sign(canonical_bytes(payload))).decode("ascii")
        with self.assertRaises(TransitionError):
            verify_transition_envelope(envelope, self.registry)


if __name__ == "__main__":
    unittest.main()
