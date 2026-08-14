from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .canonical import canonical_bytes
from .errors import TransitionError
from .models import ExerciseState


@dataclass(frozen=True)
class AuthorizedTransition:
    exercise_id: str
    plan_sha256: str
    from_state: ExerciseState
    to_state: ExerciseState
    actor_id: str
    actor_role: str
    reason: str
    nonce: str
    issued_at: str
    expires_at: str
    key_id: str


def verify_transition_envelope(envelope: dict[str, Any], trust_registry: dict[str, Any]) -> AuthorizedTransition:
    expected = {
        "schema", "exercise_id", "plan_sha256", "from_state", "to_state", "actor_id",
        "actor_role", "reason", "nonce", "issued_at", "expires_at", "key_id", "signature",
    }
    if set(envelope) != expected:
        raise TransitionError("transition envelope fields are not exact")
    if envelope["schema"] != "aegis.purple.transition/1.0":
        raise TransitionError("unsupported transition envelope schema")
    keys = validate_role_trust_registry(trust_registry)
    matches = [item for item in keys if isinstance(item, dict) and item.get("key_id") == envelope["key_id"]]
    if len(matches) != 1:
        raise TransitionError("transition key is not uniquely trusted")
    key = matches[0]
    if key.get("status") != "active" or key.get("role") != envelope["actor_role"]:
        raise TransitionError("transition key is inactive or role-mismatched")
    _validate_window(envelope["issued_at"], envelope["expires_at"])
    nonce = envelope["nonce"]
    if not isinstance(nonce, str) or len(nonce) != 32 or any(char not in "0123456789abcdef" for char in nonce):
        raise TransitionError("nonce must be 128-bit lowercase hex")
    payload = {key: value for key, value in envelope.items() if key != "signature"}
    try:
        public_raw = base64.b64decode(key["public_key_base64"], validate=True)
        signature = base64.b64decode(envelope["signature"], validate=True)
        if len(public_raw) != 32 or len(signature) != 64:
            raise ValueError
        Ed25519PublicKey.from_public_bytes(public_raw).verify(signature, canonical_bytes(payload))
    except (KeyError, ValueError, InvalidSignature) as exc:
        raise TransitionError("transition signature is invalid") from exc
    try:
        source = ExerciseState(envelope["from_state"])
        target = ExerciseState(envelope["to_state"])
    except ValueError as exc:
        raise TransitionError("invalid transition state") from exc
    return AuthorizedTransition(
        exercise_id=str(envelope["exercise_id"]), plan_sha256=str(envelope["plan_sha256"]),
        from_state=source, to_state=target, actor_id=str(envelope["actor_id"]),
        actor_role=str(envelope["actor_role"]), reason=str(envelope["reason"]), nonce=nonce,
        issued_at=str(envelope["issued_at"]), expires_at=str(envelope["expires_at"]),
        key_id=str(envelope["key_id"]),
    )


def validate_role_trust_registry(trust_registry: dict[str, Any]) -> list[dict[str, Any]]:
    if set(trust_registry) != {"schema", "keys"} or trust_registry.get("schema") != "aegis.purple.role-trust/1.0":
        raise TransitionError("invalid role trust registry")
    keys = trust_registry.get("keys")
    if not isinstance(keys, list) or not keys or len(keys) > 50:
        raise TransitionError("role trust registry requires 1-50 keys")
    seen: set[str] = set()
    roles = {
        "white", "purple", "exercise_assurance", "internal_audit", "executive_sponsor", "ciso",
    }
    for key in keys:
        if not isinstance(key, dict) or set(key) != {"key_id", "role", "status", "public_key_base64"}:
            raise TransitionError("role trust key fields are not exact")
        key_id = key["key_id"]
        if not isinstance(key_id, str) or not key_id or len(key_id) > 120 or key_id in seen:
            raise TransitionError("role trust key IDs must be unique bounded strings")
        seen.add(key_id)
        if key["role"] not in roles or key["status"] not in {"active", "revoked"}:
            raise TransitionError("role trust key has invalid role or status")
        try:
            public_raw = base64.b64decode(key["public_key_base64"], validate=True)
        except (ValueError, TypeError) as exc:
            raise TransitionError("role trust public key is invalid") from exc
        if len(public_raw) != 32:
            raise TransitionError("role trust public key must be raw Ed25519")
    return keys


def _validate_window(issued_value: Any, expires_value: Any) -> None:
    if not isinstance(issued_value, str) or not isinstance(expires_value, str):
        raise TransitionError("transition timestamps must be strings")
    try:
        issued = datetime.fromisoformat(issued_value.replace("Z", "+00:00"))
        expires = datetime.fromisoformat(expires_value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransitionError("transition timestamp is invalid") from exc
    if issued.tzinfo is None or expires.tzinfo is None:
        raise TransitionError("transition timestamps require timezones")
    now = datetime.now(UTC)
    if issued > now + timedelta(seconds=30) or expires <= now:
        raise TransitionError("transition authorization is not currently valid")
    if expires - issued > timedelta(minutes=5) or expires <= issued:
        raise TransitionError("transition authorization window exceeds five minutes")
