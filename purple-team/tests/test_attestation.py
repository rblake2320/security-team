from __future__ import annotations

import base64
import unittest
from datetime import UTC, datetime, timedelta

from aegis_purple.attestation import GATE_REQUIREMENTS, verify_gate_attestation
from aegis_purple.canonical import canonical_bytes
from aegis_purple.errors import ConfigurationError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


class GateAttestationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.private: dict[str, Ed25519PrivateKey] = {}
        keys = []
        for role in ("white", "ciso", "internal_audit", "executive_sponsor"):
            private = Ed25519PrivateKey.generate()
            self.private[role] = private
            public = private.public_key().public_bytes(
                serialization.Encoding.Raw, serialization.PublicFormat.Raw
            )
            keys.append({
                "key_id": f"{role}-key",
                "role": role,
                "status": "active",
                "public_key_base64": base64.b64encode(public).decode("ascii"),
            })
        self.registry = {"schema": "aegis.purple.role-trust/1.0", "keys": keys}

    def attestation(self, gate_id: str) -> dict:
        now = datetime.now(UTC)
        payload = {
            "schema": "aegis.purple.gate-attestation/1.0",
            "gate_id": gate_id,
            "subject": "production control deployment",
            "issued_at": now.isoformat(),
            "expires_at": (now + timedelta(days=30)).isoformat(),
            "assertions": sorted(GATE_REQUIREMENTS[gate_id]["assertions"]),
            "evidence_sha256": ["a" * 64],
        }
        signatures = []
        for role in sorted(GATE_REQUIREMENTS[gate_id]["roles"]):
            signature = self.private[role].sign(canonical_bytes(payload))
            signatures.append({
                "key_id": f"{role}-key",
                "role": role,
                "signature": base64.b64encode(signature).decode("ascii"),
            })
        return {**payload, "signatures": signatures}

    def test_dual_authority_attestations_verify(self) -> None:
        for gate in GATE_REQUIREMENTS:
            with self.subTest(gate=gate):
                self.assertTrue(verify_gate_attestation(self.attestation(gate), self.registry)["valid"])

    def test_tampered_assertion_is_rejected(self) -> None:
        document = self.attestation("key_custody_verified")
        document["subject"] = "different deployment"
        with self.assertRaisesRegex(ConfigurationError, "signature is invalid"):
            verify_gate_attestation(document, self.registry)

    def test_wrong_role_cannot_replace_required_authority(self) -> None:
        document = self.attestation("key_custody_verified")
        document["signatures"][1]["role"] = "internal_audit"
        with self.assertRaisesRegex(ConfigurationError, "role-mismatched"):
            verify_gate_attestation(document, self.registry)

    def test_missing_required_assertion_is_rejected(self) -> None:
        document = self.attestation("exercise_assurance_operational")
        document["assertions"].pop()
        with self.assertRaisesRegex(ConfigurationError, "assertions are not exact"):
            verify_gate_attestation(document, self.registry)


if __name__ == "__main__":
    unittest.main()
