"""Optional authenticated collector envelopes for production-style ingestion."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from .canonical import canonical_json
from .errors import ConfigurationError, ValidationError


def load_trust_policy(path: str | Path) -> dict[str, Any]:
    try:
        policy = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("source trust policy is unreadable") from exc
    sources = policy.get("sources") if isinstance(policy, dict) else None
    if policy.get("version") != 1 or not isinstance(sources, dict) or not sources:
        raise ConfigurationError("source trust policy is invalid")
    return policy


def _source_config(policy: dict[str, Any], source: Any) -> dict[str, str]:
    config = policy["sources"].get(source)
    if not isinstance(config, dict):
        raise ValidationError("event source is not trusted")
    key_id = config.get("key_id")
    secret_env = config.get("secret_env")
    if not isinstance(key_id, str) or not isinstance(secret_env, str):
        raise ConfigurationError("trusted source configuration is invalid")
    return {"key_id": key_id, "secret_env": secret_env}


def sign_event(event: dict[str, Any], *, key_id: str, secret: str) -> dict[str, Any]:
    if len(secret.encode("utf-8")) < 32:
        raise ConfigurationError("collector authentication key must be at least 32 bytes")
    signature = hmac.new(secret.encode("utf-8"), canonical_json(event).encode("utf-8"), hashlib.sha256).hexdigest()
    return {
        "event": event,
        "auth": {"algorithm": "hmac-sha256", "key_id": key_id, "signature": signature},
    }


def verify_envelope(
    envelope: Any,
    policy: dict[str, Any],
    *,
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    if not isinstance(envelope, dict) or set(envelope) != {"event", "auth"}:
        raise ValidationError("signed ingestion requires an event/auth envelope")
    event = envelope["event"]
    auth = envelope["auth"]
    if not isinstance(event, dict) or not isinstance(auth, dict):
        raise ValidationError("signed event envelope is invalid")
    config = _source_config(policy, event.get("source"))
    if auth.get("algorithm") != "hmac-sha256" or auth.get("key_id") != config["key_id"]:
        raise ValidationError("collector authentication metadata is invalid")
    signature = auth.get("signature")
    if not isinstance(signature, str) or len(signature) != 64:
        raise ValidationError("collector signature is invalid")
    env = environment if environment is not None else os.environ
    secret = env.get(config["secret_env"])
    if not secret or len(secret.encode("utf-8")) < 32:
        raise ConfigurationError("collector authentication key is unavailable or too short")
    expected = hmac.new(secret.encode("utf-8"), canonical_json(event).encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature.casefold(), expected):
        raise ValidationError("collector signature verification failed")
    return event
