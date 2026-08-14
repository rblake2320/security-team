"""Strict data models without runtime framework dependencies."""

from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any

from .canonical import normalize
from .errors import ValidationError

IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_CLOCK_SKEW = timedelta(days=7)


def parse_timestamp(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("timestamp must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValidationError("timestamp must be ISO-8601") from exc
    if parsed.tzinfo is None:
        raise ValidationError("timestamp must include a timezone")
    parsed = parsed.astimezone(UTC)
    if parsed > datetime.now(UTC) + MAX_CLOCK_SKEW:
        raise ValidationError("timestamp is implausibly far in the future")
    return parsed


def require_identifier(name: str, value: Any) -> str:
    if not isinstance(value, str) or not IDENTIFIER.fullmatch(value):
        raise ValidationError(f"{name} is not a safe identifier")
    return value


@dataclass(frozen=True, slots=True)
class Event:
    event_id: str
    timestamp: datetime
    source: str
    event_type: str
    host: str
    user: str | None = None
    severity: int = 0
    attributes: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Event:
        if not isinstance(data, dict):
            raise ValidationError("event must be an object")
        allowed = {"event_id", "timestamp", "source", "event_type", "host", "user", "severity", "attributes"}
        unknown = set(data) - allowed
        if unknown:
            raise ValidationError(f"unknown event fields: {', '.join(sorted(unknown))}")
        event_id = require_identifier("event_id", data.get("event_id"))
        source = require_identifier("source", data.get("source"))
        event_type = require_identifier("event_type", data.get("event_type"))
        host = require_identifier("host", data.get("host"))
        user = data.get("user")
        if user is not None:
            user = require_identifier("user", user)
        severity = data.get("severity", 0)
        if isinstance(severity, bool) or not isinstance(severity, int) or not 0 <= severity <= 10:
            raise ValidationError("severity must be an integer from 0 through 10")
        attributes = normalize(data.get("attributes", {}))
        if not isinstance(attributes, dict):
            raise ValidationError("attributes must be an object")
        return cls(
            event_id=event_id,
            timestamp=parse_timestamp(data.get("timestamp")),
            source=source,
            event_type=event_type,
            host=host,
            user=user,
            severity=severity,
            attributes=attributes,
        )

    def as_record(self) -> dict[str, Any]:
        record = asdict(self)
        record["timestamp"] = self.timestamp.isoformat().replace("+00:00", "Z")
        return record


@dataclass(frozen=True, slots=True)
class Alert:
    alert_id: str
    rule_id: str
    title: str
    severity: str
    created_at: datetime
    event_ids: tuple[str, ...]
    host: str
    user: str | None
    techniques: tuple[str, ...]
    evidence: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        rule_id: str,
        title: str,
        severity: str,
        event_ids: list[str],
        host: str,
        user: str | None,
        techniques: list[str],
        evidence: dict[str, Any],
    ) -> Alert:
        return cls(
            alert_id=str(uuid.uuid4()),
            rule_id=rule_id,
            title=title,
            severity=severity,
            created_at=datetime.now(UTC),
            event_ids=tuple(event_ids),
            host=host,
            user=user,
            techniques=tuple(techniques),
            evidence=normalize(evidence),
        )
