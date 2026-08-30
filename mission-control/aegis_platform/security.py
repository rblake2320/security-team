from __future__ import annotations

import hashlib
import hmac
import json
import re
import secrets
from dataclasses import dataclass
from typing import Any, Mapping

import jwt
from jwt import PyJWKClient

from .config import Settings


SECRET_KEY_PATTERN = re.compile(
    r"(^|_)(password|passwd|secret|token|api_?key|authorization|cookie|private_?key)($|_)",
    re.IGNORECASE,
)


def normalize_email(value: str) -> str:
    email = value.strip().lower()
    if len(email) > 320 or "@" not in email or email.startswith("@") or email.endswith("@"):
        raise ValueError("a valid email address is required")
    return email


def issue_secret(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def secret_digest(secret: str, pepper: str) -> str:
    return hmac.new(pepper.encode("utf-8"), secret.encode("utf-8"), hashlib.sha256).hexdigest()


def secret_matches(secret: str, digest: str, pepper: str) -> bool:
    return hmac.compare_digest(secret_digest(secret, pepper), digest)


def scrub(value: Any, depth: int = 0) -> Any:
    """Bound log payloads and remove credential-shaped fields before persistence."""
    if depth > 6:
        return "[MAX_DEPTH]"
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for raw_key, raw_value in list(value.items())[:100]:
            key = str(raw_key)[:120]
            result[key] = "[REDACTED]" if SECRET_KEY_PATTERN.search(key) else scrub(raw_value, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        return [scrub(item, depth + 1) for item in list(value)[:100]]
    if isinstance(value, str):
        return value.replace("\x00", "")[:4000]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value)[:1000]


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


@dataclass(frozen=True)
class Identity:
    email: str
    subject: str


class AuthenticationError(PermissionError):
    """The caller did not present a valid admitted human or connector identity."""


class AccessVerifier:
    def __init__(self, settings: Settings):
        self.settings = settings
        self._jwks: PyJWKClient | None = None
        if settings.auth_mode == "cloudflare":
            team = settings.cloudflare_team_domain.removeprefix("https://").rstrip("/")
            self._issuer = f"https://{team}"
            self._jwks = PyJWKClient(f"{self._issuer}/cdn-cgi/access/certs", cache_jwk_set=True)
        else:
            self._issuer = ""

    def verify(self, headers: Mapping[str, str], client_host: str) -> Identity:
        if self.settings.auth_mode == "development":
            if self.settings.environment != "test" and client_host not in {"127.0.0.1", "::1", "localhost"}:
                raise AuthenticationError("development identity headers are accepted only from loopback")
            email = normalize_email(headers.get("x-dev-user", self.settings.bootstrap_email))
            return Identity(email=email, subject=f"development:{email}")

        assertion = headers.get("cf-access-jwt-assertion", "").strip()
        if not assertion or not self._jwks:
            raise AuthenticationError("a Cloudflare Access assertion is required")
        try:
            signing_key = self._jwks.get_signing_key_from_jwt(assertion)
            claims = jwt.decode(
                assertion,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.settings.cloudflare_audience,
                issuer=self._issuer,
                options={"require": ["exp", "iat", "sub", "aud"]},
            )
        except jwt.PyJWTError as exc:
            raise AuthenticationError("the Cloudflare Access assertion is invalid") from exc
        email = normalize_email(str(claims.get("email", "")))
        supplied_email = headers.get("cf-access-authenticated-user-email", "").strip().lower()
        if supplied_email and not hmac.compare_digest(email, supplied_email):
            raise AuthenticationError("Cloudflare identity headers do not agree")
        return Identity(email=email, subject=str(claims["sub"])[:160])
