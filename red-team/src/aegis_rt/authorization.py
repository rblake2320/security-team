from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .models import Authorization


class AuthorizationSignatureError(ValueError):
    pass


AUTHORIZATION_KEY = "authorization-v1"
EVIDENCE_KEY = "evidence-seal-v1"
_KEY_PURPOSES = frozenset({AUTHORIZATION_KEY, EVIDENCE_KEY})


def authorization_payload(authorization: Authorization) -> bytes:
    payload = {
        "algorithm": "Ed25519",
        "domain": "aegis.authorization.v1",
        "key_purpose": AUTHORIZATION_KEY,
        "approved_by": authorization.approved_by,
        "ticket": authorization.ticket,
        "expires_at": authorization.expires_at,
        "scope_sha256": authorization.scope_sha256,
        "allow_public_targets": authorization.allow_public_targets,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def generate_keypair(
    private_path: Path,
    public_path: Path,
    password: bytes,
    *,
    purpose: str = AUTHORIZATION_KEY,
) -> None:
    if purpose not in _KEY_PURPOSES:
        raise ValueError(f"unsupported signing-key purpose: {purpose}")
    metadata_paths = (_metadata_path(private_path), _metadata_path(public_path))
    if private_path.exists() or public_path.exists() or any(path.exists() for path in metadata_paths):
        raise FileExistsError("refusing to overwrite an authorization key")
    if len(password) < 12:
        raise ValueError("key password must be at least 12 characters")
    private = Ed25519PrivateKey.generate()
    private_bytes = private.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.BestAvailableEncryption(password),
    )
    public_bytes = private.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    key_id = hashlib.sha256(public_bytes).hexdigest()
    metadata = json.dumps(
        {"schema": "aegis-key/1.0", "algorithm": "Ed25519", "key_id": key_id, "purpose": purpose},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"
    created: list[Path] = []
    try:
        _exclusive_write(private_path, private_bytes, 0o600)
        created.append(private_path)
        _exclusive_write(public_path, public_bytes, 0o644)
        created.append(public_path)
        _exclusive_write(metadata_paths[0], metadata, 0o600)
        created.append(metadata_paths[0])
        _exclusive_write(metadata_paths[1], metadata, 0o644)
        created.append(metadata_paths[1])
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise


def sign_authorization(authorization: Authorization, private_path: Path, password: bytes) -> str:
    signature = sign_bytes(authorization_payload(authorization), private_path, password, AUTHORIZATION_KEY)
    return base64.b64encode(signature).decode("ascii")


def verify_authorization(authorization: Authorization, public_path: Path) -> None:
    try:
        signature = base64.b64decode(authorization.signature, validate=True)
    except ValueError as exc:
        raise AuthorizationSignatureError("authorization signature is invalid") from exc
    verify_bytes(authorization_payload(authorization), signature, public_path, AUTHORIZATION_KEY)


def sign_bytes(payload: bytes, private_path: Path, password: bytes, purpose: str) -> bytes:
    _assert_key_purpose(private_path, purpose)
    private = serialization.load_pem_private_key(_read_bounded_key(private_path), password=password)
    if not isinstance(private, Ed25519PrivateKey):
        raise AuthorizationSignatureError("authorization key is not Ed25519")
    return private.sign(payload)


def verify_bytes(payload: bytes, signature: bytes, public_path: Path, purpose: str) -> None:
    _assert_key_purpose(public_path, purpose)
    public = serialization.load_pem_public_key(_read_bounded_key(public_path))
    if not isinstance(public, Ed25519PublicKey):
        raise AuthorizationSignatureError("trusted authorization key is not Ed25519")
    try:
        if len(signature) != 64:
            raise AuthorizationSignatureError("authorization signature has an invalid length")
        public.verify(signature, payload)
    except (InvalidSignature, ValueError) as exc:
        raise AuthorizationSignatureError("authorization signature is invalid") from exc


def password_from_environment(name: str) -> bytes:
    value = os.environ.get(name)
    if value is None:
        raise ValueError(f"password environment variable is not set: {name}")
    return value.encode("utf-8")


def _exclusive_write(path: Path, content: bytes, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def _read_bounded_key(path: Path) -> bytes:
    if path.stat().st_size > 64_000:
        raise ValueError("authorization key exceeds the 64 KB safety limit")
    return path.read_bytes()


def _metadata_path(path: Path) -> Path:
    return path.with_name(path.name + ".metadata.json")


def _assert_key_purpose(path: Path, expected: str) -> None:
    if expected not in _KEY_PURPOSES:
        raise AuthorizationSignatureError(f"unsupported expected key purpose: {expected}")
    metadata_path = _metadata_path(path)
    if metadata_path.stat().st_size > 4_096:
        raise AuthorizationSignatureError("key metadata exceeds the 4 KB safety limit")
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise AuthorizationSignatureError("signing key has no valid purpose metadata") from exc
    if set(metadata) != {"schema", "algorithm", "key_id", "purpose"}:
        raise AuthorizationSignatureError("signing-key metadata fields are invalid")
    if metadata["schema"] != "aegis-key/1.0" or metadata["algorithm"] != "Ed25519":
        raise AuthorizationSignatureError("signing-key metadata is incompatible")
    if metadata["purpose"] != expected:
        raise AuthorizationSignatureError(
            f"key purpose {metadata['purpose']!r} cannot be used as {expected!r}"
        )
    key_bytes = _read_bounded_key(path)
    try:
        if b"PRIVATE KEY" in key_bytes:
            key = serialization.load_pem_private_key(key_bytes, password=None)
            public_bytes = key.public_key().public_bytes(
                serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
            )
        else:
            public_bytes = key_bytes
    except (TypeError, ValueError):
        # Encrypted private keys cannot be decoded here; their paired public metadata is
        # checked at generation and the private-key loader validates them during signing.
        return
    if hashlib.sha256(public_bytes).hexdigest() != metadata["key_id"]:
        raise AuthorizationSignatureError("key metadata does not match the key material")
