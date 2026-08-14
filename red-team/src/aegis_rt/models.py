from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class Severity(StrEnum):
    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TargetKind(StrEnum):
    PATH = "path"
    URL = "url"


@dataclass(frozen=True)
class Target:
    kind: TargetKind
    value: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Target:
        return cls(TargetKind(data["kind"]), str(data["value"]))


@dataclass(frozen=True)
class Limits:
    max_requests: int = 25
    max_concurrency: int = 2
    requests_per_second: float = 2.0
    timeout_seconds: float = 8.0
    max_files: int = 20_000
    max_findings: int = 5_000

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Limits:
        return cls(**(data or {}))


@dataclass(frozen=True)
class Authorization:
    approved_by: str
    ticket: str
    expires_at: str
    scope_sha256: str
    signature: str
    allow_public_targets: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> Authorization | None:
        if not data:
            return None
        try:
            return cls(**data)
        except TypeError as exc:
            raise ValueError("authorization receipt is malformed") from exc

    def is_expired(self) -> bool:
        expiry = datetime.fromisoformat(self.expires_at.replace("Z", "+00:00"))
        if expiry.tzinfo is None or expiry.utcoffset() is None:
            raise ValueError("authorization expiry must include a timezone")
        return expiry <= datetime.now(UTC)


@dataclass(frozen=True)
class Engagement:
    engagement_id: str
    owner: str
    targets: tuple[Target, ...]
    allowed_checks: tuple[str, ...]
    limits: Limits = field(default_factory=Limits)
    authorization: Authorization | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Engagement:
        return cls(
            engagement_id=str(data["engagement_id"]),
            owner=str(data["owner"]),
            targets=tuple(Target.from_dict(item) for item in data["targets"]),
            allowed_checks=tuple(str(item) for item in data["allowed_checks"]),
            limits=Limits.from_dict(data.get("limits")),
            authorization=Authorization.from_dict(data.get("authorization")),
        )


@dataclass(frozen=True)
class Finding:
    check_id: str
    severity: Severity
    title: str
    target: str
    description: str
    remediation: str
    evidence: dict[str, Any] = field(default_factory=dict)
    cwe: str | None = None
    attack: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    target: str
    status: str
    findings: tuple[Finding, ...] = ()
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "target": self.target,
            "status": self.status,
            "findings": [item.to_dict() for item in self.findings],
            "error": self.error,
        }


def load_engagement(path: Path) -> Engagement:
    import json

    if path.stat().st_size > 1_000_000:
        raise ValueError("engagement file exceeds the 1 MB safety limit")
    return Engagement.from_dict(json.loads(path.read_text(encoding="utf-8")))
