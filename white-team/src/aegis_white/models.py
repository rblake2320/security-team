"""Validated value objects for exercise control.

Timestamps are supplied explicitly rather than read from the wall clock. White Team
records are evidence: a reviewer must be able to replay a ledger and get identical
results, and tests must not depend on how fast the machine is.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .errors import ConfigurationError

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{2,63}$")

# Severity of a stop condition. A MANDATORY stop is the unconditional control:
# nothing may proceed after it, and continuing is an automatic scorecard failure.
STOP_SEVERITIES = ("advisory", "mandatory")


def parse_instant(value: str, *, field_name: str = "timestamp") -> datetime:
    """Parse a strict UTC ISO-8601 instant."""
    if not isinstance(value, str) or not value:
        raise ConfigurationError(f"{field_name} must be a non-empty ISO-8601 string")
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ConfigurationError(f"{field_name} is not a valid ISO-8601 instant: {value}") from exc
    if parsed.tzinfo is None:
        raise ConfigurationError(f"{field_name} must include a timezone offset")
    return parsed.astimezone(timezone.utc)


def _require_id(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not _ID.match(value):
        raise ConfigurationError(
            f"{field_name} must be 3-64 chars of [A-Za-z0-9._:-] and start alphanumeric"
        )
    return value


def _require_text(value: str, field_name: str, *, max_len: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field_name} must be non-empty text")
    if len(value) > max_len:
        raise ConfigurationError(f"{field_name} exceeds {max_len} characters")
    return value.strip()


@dataclass(frozen=True)
class Authorization:
    """Who approved this exercise, under what ticket, and until when."""

    approved_by: str
    ticket: str
    expires_at: datetime

    @staticmethod
    def create(approved_by: str, ticket: str, expires_at: str) -> "Authorization":
        return Authorization(
            approved_by=_require_text(approved_by, "approved_by", max_len=200),
            ticket=_require_id(ticket, "ticket"),
            expires_at=parse_instant(expires_at, field_name="expires_at"),
        )

    def is_valid_at(self, moment: datetime) -> bool:
        return moment <= self.expires_at

    def to_payload(self) -> dict[str, Any]:
        return {
            "approved_by": self.approved_by,
            "ticket": self.ticket,
            "expires_at": self.expires_at.isoformat(),
        }


@dataclass(frozen=True)
class Scope:
    """The allow-list. Absent an explicit entry, an action is out of scope.

    Fail-closed by construction: there is no wildcard and no deny-list, because a
    deny-list silently authorizes everything nobody thought to forbid.
    """

    targets: tuple[str, ...]
    activities: tuple[str, ...]

    @staticmethod
    def create(targets: list[str], activities: list[str]) -> "Scope":
        if not targets:
            raise ConfigurationError("scope requires at least one target")
        if not activities:
            raise ConfigurationError("scope requires at least one activity")
        for value in targets:
            if not isinstance(value, str) or not value.strip():
                raise ConfigurationError("scope targets must be non-empty strings")
            if "*" in value:
                raise ConfigurationError("wildcards are not permitted in scope targets")
        for value in activities:
            if not isinstance(value, str) or not value.strip():
                raise ConfigurationError("scope activities must be non-empty strings")
            if "*" in value:
                raise ConfigurationError("wildcards are not permitted in scope activities")
        return Scope(
            targets=tuple(sorted({v.strip() for v in targets})),
            activities=tuple(sorted({v.strip() for v in activities})),
        )

    def permits(self, target: str, activity: str) -> bool:
        return target in self.targets and activity in self.activities

    def to_payload(self) -> dict[str, Any]:
        return {"targets": list(self.targets), "activities": list(self.activities)}


@dataclass(frozen=True)
class Decision:
    """A governance decision. Rationale is mandatory — an unexplained ruling is not
    reviewable, and the scorecard's G component measures exactly that."""

    decision_id: str
    decided_by: str
    question: str
    outcome: str
    rationale: str
    decided_at: datetime
    raised_at: datetime

    @staticmethod
    def create(
        decision_id: str,
        decided_by: str,
        question: str,
        outcome: str,
        rationale: str,
        raised_at: str,
        decided_at: str,
    ) -> "Decision":
        raised = parse_instant(raised_at, field_name="raised_at")
        decided = parse_instant(decided_at, field_name="decided_at")
        if decided < raised:
            raise ConfigurationError("decided_at precedes raised_at")
        return Decision(
            decision_id=_require_id(decision_id, "decision_id"),
            decided_by=_require_text(decided_by, "decided_by", max_len=200),
            question=_require_text(question, "question"),
            outcome=_require_text(outcome, "outcome", max_len=200),
            rationale=_require_text(rationale, "rationale"),
            raised_at=raised,
            decided_at=decided,
        )

    @property
    def latency_seconds(self) -> float:
        return (self.decided_at - self.raised_at).total_seconds()

    def to_payload(self) -> dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decided_by": self.decided_by,
            "question": self.question,
            "outcome": self.outcome,
            "rationale": self.rationale,
            "raised_at": self.raised_at.isoformat(),
            "decided_at": self.decided_at.isoformat(),
            "latency_seconds": self.latency_seconds,
        }


@dataclass
class ExerciseState:
    """Mutable in-memory projection rebuilt from the ledger."""

    exercise_id: str
    authorization: Authorization | None = None
    scope: Scope | None = None
    started: bool = False
    stopped_at: datetime | None = None
    stop_reason: str | None = None
    stop_severity: str | None = None
    stop_acknowledged_at: datetime | None = None
    completed: bool = False
    activities_accepted: int = 0
    activities_refused: int = 0
    out_of_scope_accepted: int = 0
    post_stop_activity: int = 0
    decisions: list[Decision] = field(default_factory=list)
