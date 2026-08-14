from __future__ import annotations

import hashlib
import ipaddress
import json
import re
import socket
from pathlib import Path
from urllib.parse import urlsplit

from .models import Engagement, Target, TargetKind


class ScopeError(ValueError):
    """Raised when a target or engagement violates scope policy."""


def scope_payload(engagement: Engagement) -> dict[str, object]:
    """Return the immutable portion bound to an authorization receipt."""
    return {
        "engagement_id": engagement.engagement_id,
        "owner": engagement.owner,
        "targets": [
            {
                "kind": target.kind.value,
                "value": (
                    str(Path(target.value).expanduser().resolve()) if target.kind == TargetKind.PATH else target.value
                ),
            }
            for target in engagement.targets
        ],
        "allowed_checks": sorted(engagement.allowed_checks),
        "limits": {
            "max_requests": engagement.limits.max_requests,
            "max_concurrency": engagement.limits.max_concurrency,
            "requests_per_second": engagement.limits.requests_per_second,
            "timeout_seconds": engagement.limits.timeout_seconds,
            "max_files": engagement.limits.max_files,
            "max_findings": engagement.limits.max_findings,
        },
    }


def scope_fingerprint(engagement: Engagement) -> str:
    encoded = json.dumps(scope_payload(engagement), sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def resolve_url_target(value: str) -> tuple[str, int, tuple[str, ...]]:
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise ScopeError("URL target contains a control character")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"}:
        raise ScopeError("only http and https URL targets are supported")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ScopeError("URL must have a hostname and must not contain credentials")
    if parsed.query or parsed.fragment:
        raise ScopeError("URL targets must not contain query strings or fragments")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if not 1 <= port <= 65535:
        raise ScopeError("URL port is outside the valid range")
    try:
        records = socket.getaddrinfo(parsed.hostname, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ScopeError(f"hostname could not be resolved: {parsed.hostname}") from exc
    addresses = tuple(sorted({record[4][0] for record in records}))
    if not addresses:
        raise ScopeError("hostname resolved to no addresses")
    return parsed.hostname, port, addresses


def is_public_address(value: str) -> bool:
    address = ipaddress.ip_address(value)
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def validate_target(target: Target, allow_public: bool = False) -> None:
    if target.kind == TargetKind.PATH:
        path = Path(target.value).expanduser().resolve()
        if not path.exists():
            raise ScopeError(f"path target does not exist: {path}")
        if not path.is_dir() and not path.is_file():
            raise ScopeError(f"path target is not a regular file or directory: {path}")
        return

    _, _, addresses = resolve_url_target(target.value)
    public = [address for address in addresses if is_public_address(address)]
    if public and not allow_public:
        raise ScopeError(
            "public target denied by default; authorization must explicitly allow it: " + ", ".join(public)
        )


def validate_engagement(engagement: Engagement, require_authorization: bool) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", engagement.engagement_id):
        raise ScopeError("engagement_id must be a safe 1-128 character identifier")
    if not _safe_text(engagement.owner, 200):
        raise ScopeError("owner must be printable text of 1-200 characters")
    if not engagement.targets or not engagement.allowed_checks:
        raise ScopeError("at least one target and one allowed check are required")
    limits = engagement.limits
    if type(limits.max_requests) is not int or type(limits.max_concurrency) is not int:
        raise ScopeError("request and concurrency limits must be integers")
    if type(limits.max_files) is not int or type(limits.max_findings) is not int:
        raise ScopeError("file and finding limits must be integers")
    if isinstance(limits.requests_per_second, bool) or not isinstance(limits.requests_per_second, (int, float)):
        raise ScopeError("requests_per_second must be numeric")
    if isinstance(limits.timeout_seconds, bool) or not isinstance(limits.timeout_seconds, (int, float)):
        raise ScopeError("timeout_seconds must be numeric")
    if not 1 <= limits.max_requests <= 500:
        raise ScopeError("max_requests must be between 1 and 500")
    if not 1 <= limits.max_concurrency <= 8:
        raise ScopeError("max_concurrency must be between 1 and 8")
    if not 0.1 <= limits.requests_per_second <= 20:
        raise ScopeError("requests_per_second must be between 0.1 and 20")
    if not 1 <= limits.timeout_seconds <= 30:
        raise ScopeError("timeout_seconds must be between 1 and 30")
    if not 1 <= limits.max_files <= 100_000:
        raise ScopeError("max_files must be between 1 and 100000")
    if not 1 <= limits.max_findings <= 20_000:
        raise ScopeError("max_findings must be between 1 and 20000")
    if len(set(engagement.allowed_checks)) != len(engagement.allowed_checks):
        raise ScopeError("allowed_checks must not contain duplicates")
    target_keys = {(target.kind.value, target.value) for target in engagement.targets}
    if len(target_keys) != len(engagement.targets):
        raise ScopeError("targets must not contain duplicates")

    auth = engagement.authorization
    if require_authorization:
        if auth is None:
            raise ScopeError("live execution requires an authorization receipt")
        if not auth.approved_by.strip() or not auth.ticket.strip() or not auth.signature.strip():
            raise ScopeError("authorization approver, ticket, and signature are required")
        if not _safe_text(auth.approved_by, 200) or not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,127}", auth.ticket
        ):
            raise ScopeError("authorization approver or ticket has an unsafe format")
        if auth.is_expired():
            raise ScopeError("authorization receipt is expired")
        expected = scope_fingerprint(engagement)
        if auth.scope_sha256 != expected:
            raise ScopeError("authorization does not match the current scope")

    allow_public = bool(auth and auth.allow_public_targets)
    for target in engagement.targets:
        validate_target(target, allow_public=allow_public)


def _safe_text(value: str, maximum: int) -> bool:
    return (
        bool(value)
        and len(value) <= maximum
        and all(character.isprintable() and character not in "\r\n" for character in value)
    )
