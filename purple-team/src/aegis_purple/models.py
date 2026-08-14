from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from .canonical import sha256
from .errors import ConfigurationError

ID = re.compile(r"^[A-Z][A-Z0-9-]{2,63}$")
ATTACK = re.compile(r"^T\d{4}(?:\.\d{3})?$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ExerciseState(StrEnum):
    FROZEN = "FROZEN"
    AUTHORIZED = "AUTHORIZED"
    EXECUTING = "EXECUTING"
    EXECUTED = "EXECUTED"
    EVIDENCE_VERIFIED = "EVIDENCE_VERIFIED"
    RETESTED = "RETESTED"
    CLOSED = "CLOSED"
    STOPPED = "STOPPED"


ALLOWED_TRANSITIONS = {
    ExerciseState.FROZEN: {ExerciseState.AUTHORIZED, ExerciseState.STOPPED},
    ExerciseState.AUTHORIZED: {ExerciseState.EXECUTING, ExerciseState.STOPPED},
    ExerciseState.EXECUTING: {ExerciseState.EXECUTED, ExerciseState.STOPPED},
    ExerciseState.EXECUTED: {ExerciseState.EVIDENCE_VERIFIED, ExerciseState.STOPPED},
    ExerciseState.EVIDENCE_VERIFIED: {ExerciseState.RETESTED, ExerciseState.STOPPED},
    ExerciseState.RETESTED: {ExerciseState.CLOSED, ExerciseState.STOPPED},
    ExerciseState.CLOSED: set(),
    ExerciseState.STOPPED: set(),
}

ROLE_TRANSITIONS = {
    ExerciseState.AUTHORIZED: {"white"},
    ExerciseState.EXECUTING: {"purple"},
    ExerciseState.EXECUTED: {"purple"},
    ExerciseState.EVIDENCE_VERIFIED: {"exercise_assurance"},
    ExerciseState.RETESTED: {"purple"},
    ExerciseState.CLOSED: {"white"},
    ExerciseState.STOPPED: {"white"},
}


@dataclass(frozen=True)
class TestCase:
    test_case_id: str
    technique: str
    procedure_sha256: str
    expected_telemetry: tuple[str, ...]
    expected_detections: tuple[str, ...]
    safety_class: str
    rollback_verified: bool
    observe_only: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TestCase:
        _exact_keys(
            data,
            {
                "test_case_id", "technique", "procedure_sha256", "expected_telemetry",
                "expected_detections", "safety_class", "rollback_verified", "observe_only",
            },
            "test case",
        )
        test_case_id = _identifier(data["test_case_id"], "test_case_id")
        technique = str(data["technique"])
        if not ATTACK.fullmatch(technique):
            raise ConfigurationError("invalid ATT&CK technique ID")
        procedure_sha256 = _hash(data["procedure_sha256"], "procedure_sha256")
        telemetry = _nonempty_strings(data["expected_telemetry"], "expected_telemetry")
        detections = _nonempty_strings(data["expected_detections"], "expected_detections")
        safety_class = str(data["safety_class"])
        if safety_class not in {"low", "medium", "high"}:
            raise ConfigurationError("invalid safety_class")
        rollback_verified = _boolean(data["rollback_verified"], "rollback_verified")
        observe_only = _boolean(data["observe_only"], "observe_only")
        if safety_class == "high" and not rollback_verified:
            raise ConfigurationError("high-safety test case requires verified rollback")
        return cls(
            test_case_id, technique, procedure_sha256, telemetry, detections,
            safety_class, rollback_verified, observe_only,
        )


@dataclass(frozen=True)
class ExercisePlan:
    schema: str
    exercise_id: str
    version: int
    title: str
    owner: str
    environment: str
    expires_at: str
    authorization_receipt_sha256: str
    readiness_snapshot_sha256: str
    rubric_sha256: str
    role_trust_sha256: str
    test_cases: tuple[TestCase, ...]
    stop_conditions: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExercisePlan:
        _exact_keys(
            data,
            {
                "schema", "exercise_id", "version", "title", "owner", "environment",
                "expires_at", "authorization_receipt_sha256", "readiness_snapshot_sha256",
                "rubric_sha256", "role_trust_sha256", "test_cases", "stop_conditions",
            },
            "exercise plan",
        )
        if data["schema"] != "aegis.purple.exercise-plan/1.0":
            raise ConfigurationError("unsupported exercise-plan schema")
        exercise_id = _identifier(data["exercise_id"], "exercise_id")
        if isinstance(data["version"], bool) or not isinstance(data["version"], int) or data["version"] < 1:
            raise ConfigurationError("version must be a positive integer")
        title = _bounded_text(data["title"], "title", 200)
        owner = _bounded_text(data["owner"], "owner", 120)
        environment = str(data["environment"])
        if environment not in {"lab", "dev", "pre-prod", "prod"}:
            raise ConfigurationError("invalid environment")
        expires_at = _timestamp(data["expires_at"])
        test_cases = tuple(TestCase.from_dict(item) for item in _list(data["test_cases"], "test_cases"))
        if not test_cases or len(test_cases) > 500:
            raise ConfigurationError("exercise requires 1-500 test cases")
        ids = [item.test_case_id for item in test_cases]
        if len(ids) != len(set(ids)):
            raise ConfigurationError("duplicate test_case_id")
        if environment == "prod" and any(not item.observe_only for item in test_cases):
            raise ConfigurationError("production test cases must be observe-only")
        return cls(
            str(data["schema"]), exercise_id, data["version"], title, owner, environment,
            expires_at, _hash(data["authorization_receipt_sha256"], "authorization_receipt_sha256"),
            _hash(data["readiness_snapshot_sha256"], "readiness_snapshot_sha256"),
            _hash(data["rubric_sha256"], "rubric_sha256"),
            _hash(data["role_trust_sha256"], "role_trust_sha256"), test_cases,
            _nonempty_strings(data["stop_conditions"], "stop_conditions"),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def digest(self) -> str:
        return sha256(self.to_dict())


def _exact_keys(data: Any, expected: set[str], label: str) -> None:
    if not isinstance(data, dict):
        raise ConfigurationError(f"{label} must be an object")
    unknown = set(data) - expected
    missing = expected - set(data)
    if unknown or missing:
        raise ConfigurationError(f"{label} keys invalid; missing={sorted(missing)} unknown={sorted(unknown)}")


def _identifier(value: Any, label: str) -> str:
    text = str(value)
    if not ID.fullmatch(text):
        raise ConfigurationError(f"invalid {label}")
    return text


def _hash(value: Any, label: str) -> str:
    text = str(value)
    if not HEX64.fullmatch(text):
        raise ConfigurationError(f"{label} must be lowercase SHA-256")
    return text


def _bounded_text(value: Any, label: str, limit: int) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ConfigurationError(f"invalid {label}")
    return value


def _list(value: Any, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise ConfigurationError(f"{label} must be a list")
    return value


def _nonempty_strings(value: Any, label: str) -> tuple[str, ...]:
    items = _list(value, label)
    if not items or len(items) > 100 or any(not isinstance(item, str) or not item.strip() or len(item) > 500 for item in items):
        raise ConfigurationError(f"{label} must contain 1-100 bounded strings")
    return tuple(items)


def _boolean(value: Any, label: str) -> bool:
    if type(value) is not bool:
        raise ConfigurationError(f"{label} must be boolean")
    return value


def _timestamp(value: Any) -> str:
    if not isinstance(value, str):
        raise ConfigurationError("expires_at must be an ISO timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError("expires_at must be an ISO timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ConfigurationError("expires_at must include a timezone")
    return value
