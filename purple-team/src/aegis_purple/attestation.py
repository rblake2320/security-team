from __future__ import annotations

import base64
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .authority import validate_role_trust_registry
from .canonical import canonical_bytes
from .errors import ConfigurationError

GATE_REQUIREMENTS = {
    "exercise_assurance_operational": {
        "roles": {"internal_audit", "executive_sponsor"},
        "assertions": {
            "performer_named",
            "coi_screen_ea_coi_1_through_6_passed",
            "assessment_key_custody_confirmed",
            "sealed_inject_format_signable",
            "ea6_reporting_line_confirmed",
            "permissions_exactly_ea1_through_ea6",
        },
    },
    "key_custody_verified": {
        "roles": {"white", "ciso"},
        "assertions": {
            "authorization_key_non_exportable_white_custody",
            "red_access_denial_exercised",
            "authorization_and_evidence_keys_distinct",
            "rotation_and_recovery_exercised",
            "emergency_revocation_exercised_end_to_end",
            "key_use_logs_holder_immutable",
        },
    },
}


def verify_gate_attestation(document: dict[str, Any], trust_registry: dict[str, Any]) -> dict[str, Any]:
    expected = {
        "schema", "gate_id", "subject", "issued_at", "expires_at", "assertions",
        "evidence_sha256", "signatures",
    }
    if set(document) != expected or document.get("schema") != "aegis.purple.gate-attestation/1.0":
        raise ConfigurationError("gate attestation fields or schema are invalid")
    gate_id = document.get("gate_id")
    if gate_id not in GATE_REQUIREMENTS:
        raise ConfigurationError("gate attestation is not permitted for this gate")
    subject = document.get("subject")
    if not isinstance(subject, str) or not subject.strip() or len(subject) > 200:
        raise ConfigurationError("gate attestation requires a bounded subject")
    assertions = document.get("assertions")
    if not isinstance(assertions, list) or set(assertions) != GATE_REQUIREMENTS[gate_id]["assertions"]:
        raise ConfigurationError("gate attestation assertions are not exact")
    if len(assertions) != len(set(assertions)):
        raise ConfigurationError("gate attestation assertions contain duplicates")
    evidence = document.get("evidence_sha256")
    if not isinstance(evidence, list) or not evidence or len(evidence) > 100:
        raise ConfigurationError("gate attestation requires 1-100 evidence digests")
    if any(not _is_sha256(item) for item in evidence) or len(evidence) != len(set(evidence)):
        raise ConfigurationError("gate evidence digests must be unique lowercase SHA-256 values")
    _validate_window(document.get("issued_at"), document.get("expires_at"))

    keys = validate_role_trust_registry(trust_registry)
    trusted = {item["key_id"]: item for item in keys if item["status"] == "active"}
    signatures = document.get("signatures")
    required_roles = GATE_REQUIREMENTS[gate_id]["roles"]
    if not isinstance(signatures, list) or len(signatures) != len(required_roles):
        raise ConfigurationError("gate attestation requires exactly two authority signatures")
    payload = {key: value for key, value in document.items() if key != "signatures"}
    observed_roles: set[str] = set()
    observed_keys: set[str] = set()
    for signature_record in signatures:
        if not isinstance(signature_record, dict) or set(signature_record) != {"key_id", "role", "signature"}:
            raise ConfigurationError("gate signature fields are not exact")
        key_id = signature_record["key_id"]
        key = trusted.get(key_id)
        if key is None or key["role"] != signature_record["role"]:
            raise ConfigurationError("gate signature key is untrusted or role-mismatched")
        if key_id in observed_keys:
            raise ConfigurationError("one key cannot satisfy two approval authorities")
        try:
            raw_public = base64.b64decode(key["public_key_base64"], validate=True)
            raw_signature = base64.b64decode(signature_record["signature"], validate=True)
            if len(raw_public) != 32 or len(raw_signature) != 64:
                raise ValueError
            Ed25519PublicKey.from_public_bytes(raw_public).verify(raw_signature, canonical_bytes(payload))
        except (InvalidSignature, TypeError, ValueError) as exc:
            raise ConfigurationError("gate attestation signature is invalid") from exc
        observed_keys.add(key_id)
        observed_roles.add(signature_record["role"])
    if observed_roles != required_roles:
        raise ConfigurationError("gate attestation lacks the required independent authorities")
    return {
        "valid": True,
        "gate_id": gate_id,
        "subject": subject,
        "authority_roles": sorted(observed_roles),
        "evidence_count": len(evidence),
        "expires_at": document["expires_at"],
    }


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _validate_window(issued_value: Any, expires_value: Any) -> None:
    if not isinstance(issued_value, str) or not isinstance(expires_value, str):
        raise ConfigurationError("gate attestation timestamps must be strings")
    try:
        issued = datetime.fromisoformat(issued_value.replace("Z", "+00:00"))
        expires = datetime.fromisoformat(expires_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError("gate attestation timestamp is invalid") from exc
    if issued.tzinfo is None or expires.tzinfo is None or expires <= issued:
        raise ConfigurationError("gate attestation window is invalid")
    now = datetime.now(UTC)
    if issued > now + timedelta(minutes=5) or expires <= now:
        raise ConfigurationError("gate attestation is not currently valid")
    if expires - issued > timedelta(days=90):
        raise ConfigurationError("gate attestation validity exceeds 90 days")
