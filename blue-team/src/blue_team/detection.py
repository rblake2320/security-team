"""Bounded detection-as-code and temporal correlation engine."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .canonical import digest
from .errors import ConfigurationError
from .models import Alert, Event, require_identifier
from .store import EvidenceStore

ALLOWED_OPERATORS = {"eq", "ne", "in", "contains", "startswith", "endswith", "exists", "gte", "lte"}
SEVERITIES = {"low", "medium", "high", "critical"}
TACTICS = {
    "Reconnaissance",
    "Resource Development",
    "Initial Access",
    "Execution",
    "Persistence",
    "Privilege Escalation",
    "Stealth",
    "Defense Impairment",
    "Credential Access",
    "Discovery",
    "Lateral Movement",
    "Collection",
    "Command and Control",
    "Exfiltration",
    "Impact",
}


@dataclass(frozen=True, slots=True)
class Condition:
    field: str
    operator: str
    value: Any = None
    case_sensitive: bool = False


@dataclass(frozen=True, slots=True)
class Threshold:
    count: int
    within_seconds: int
    group_by: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Rule:
    rule_id: str
    title: str
    severity: str
    conditions: tuple[Condition, ...]
    techniques: tuple[str, ...]
    tactics: tuple[str, ...]
    group_by: tuple[str, ...]
    threshold: Threshold | None
    suppression_seconds: int
    allow_suppression: bool
    enabled: bool
    rationale: str


def _require_text(name: str, value: Any, *, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ConfigurationError(f"{name} must be non-empty text no longer than {maximum} characters")
    return value.strip()


def parse_rule(data: dict[str, Any]) -> Rule:
    if not isinstance(data, dict):
        raise ConfigurationError("rule must be an object")
    allowed_rule_fields = {
        "id",
        "title",
        "severity",
        "enabled",
        "allow_suppression",
        "suppression_seconds",
        "conditions",
        "techniques",
        "tactics",
        "threshold",
        "group_by",
        "rationale",
    }
    if set(data) - allowed_rule_fields:
        raise ConfigurationError("rule contains unknown fields")
    try:
        rule_id = require_identifier("rule_id", data.get("id"))
    except Exception as exc:
        raise ConfigurationError("rule ID is invalid") from exc
    title = _require_text("title", data.get("title"), maximum=200)
    severity = data.get("severity")
    if severity not in SEVERITIES:
        raise ConfigurationError("rule severity is invalid")
    raw_conditions = data.get("conditions")
    if not isinstance(raw_conditions, list) or not 1 <= len(raw_conditions) <= 32:
        raise ConfigurationError("rule must contain between 1 and 32 conditions")
    conditions: list[Condition] = []
    for raw in raw_conditions:
        if not isinstance(raw, dict):
            raise ConfigurationError("condition must be an object")
        if set(raw) - {"field", "operator", "value", "case_sensitive"}:
            raise ConfigurationError("condition contains unknown fields")
        field = _require_text("condition field", raw.get("field"), maximum=128)
        operator = raw.get("operator")
        if operator not in ALLOWED_OPERATORS:
            raise ConfigurationError(f"unsafe condition operator: {operator}")
        case_sensitive = raw.get("case_sensitive", False)
        if not isinstance(case_sensitive, bool):
            raise ConfigurationError("condition case_sensitive must be a boolean")
        conditions.append(Condition(field, operator, raw.get("value"), case_sensitive))
    techniques = tuple(_require_text("technique", item, maximum=32) for item in data.get("techniques", []))
    tactics = tuple(_require_text("tactic", item, maximum=64) for item in data.get("tactics", []))
    if not techniques or any(not re.fullmatch(r"T\d{4}(?:\.\d{3})?", item) for item in techniques):
        raise ConfigurationError("rule must contain valid ATT&CK technique IDs")
    if not tactics or any(tactic not in TACTICS for tactic in tactics):
        raise ConfigurationError("rule must contain current Enterprise tactics")
    raw_group_by = data.get("group_by", ["host", "user"])
    if not isinstance(raw_group_by, list) or not 1 <= len(raw_group_by) <= 4:
        raise ConfigurationError("rule group_by must contain one through four fields")
    group_by = tuple(_require_text("group_by", item, maximum=128) for item in raw_group_by)
    raw_threshold = data.get("threshold")
    threshold = None
    if raw_threshold is not None:
        if not isinstance(raw_threshold, dict):
            raise ConfigurationError("threshold must be an object")
        if set(raw_threshold) - {"count", "within_seconds", "group_by"}:
            raise ConfigurationError("threshold contains unknown fields")
        count = raw_threshold.get("count")
        within = raw_threshold.get("within_seconds")
        group_by = raw_threshold.get("group_by", ["host"])
        if not isinstance(count, int) or not 2 <= count <= 10_000:
            raise ConfigurationError("threshold count must be between 2 and 10000")
        if not isinstance(within, int) or not 1 <= within <= 86_400:
            raise ConfigurationError("threshold window must be between 1 second and 24 hours")
        if not isinstance(group_by, list) or not 1 <= len(group_by) <= 4:
            raise ConfigurationError("threshold group_by must contain one through four fields")
        threshold = Threshold(count, within, tuple(_require_text("group_by", item, maximum=128) for item in group_by))
    suppression_seconds = data.get("suppression_seconds", 0)
    if not isinstance(suppression_seconds, int) or not 0 <= suppression_seconds <= 86_400:
        raise ConfigurationError("suppression_seconds must be between 0 and 86400")
    allow_suppression = data.get("allow_suppression", True)
    enabled = data.get("enabled", True)
    if not isinstance(allow_suppression, bool) or not isinstance(enabled, bool):
        raise ConfigurationError("enabled and allow_suppression must be booleans")
    if severity == "critical" and allow_suppression:
        raise ConfigurationError("critical rules must explicitly disable suppression")
    return Rule(
        rule_id=rule_id,
        title=title,
        severity=severity,
        conditions=tuple(conditions),
        techniques=techniques,
        tactics=tactics,
        group_by=group_by,
        threshold=threshold,
        suppression_seconds=suppression_seconds,
        allow_suppression=allow_suppression,
        enabled=enabled,
        rationale=_require_text("rationale", data.get("rationale"), maximum=1000),
    )


def load_rules(path: str | Path) -> list[Rule]:
    root = Path(path)
    files = sorted(root.glob("*.json")) if root.is_dir() else [root]
    rules: list[Rule] = []
    seen: set[str] = set()
    for file in files:
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ConfigurationError(f"cannot load rule file: {file.name}") from exc
        records = payload if isinstance(payload, list) else [payload]
        for record in records:
            rule = parse_rule(record)
            if rule.rule_id in seen:
                raise ConfigurationError(f"duplicate rule ID: {rule.rule_id}")
            seen.add(rule.rule_id)
            rules.append(rule)
    if not rules:
        raise ConfigurationError("no detection rules were loaded")
    return rules


def verify_rule_manifest(path: str | Path, manifest_path: str | Path) -> dict[str, Any]:
    root = Path(path)
    if not root.is_dir():
        raise ConfigurationError("manifest verification requires a rule directory")
    try:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("rule manifest is unreadable") from exc
    expected = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(expected, dict) or not expected:
        raise ConfigurationError("rule manifest contains no file hashes")
    actual_names = {file.name for file in root.glob("*.json")}
    expected_names = set(expected)
    if actual_names != expected_names:
        raise ConfigurationError("rule directory does not match the manifest file set")
    verified: list[str] = []
    for name, expected_hash in sorted(expected.items()):
        if not isinstance(expected_hash, str) or len(expected_hash) != 64:
            raise ConfigurationError("rule manifest contains an invalid hash")
        actual_hash = hashlib.sha256((root / name).read_bytes()).hexdigest()
        if actual_hash != expected_hash.casefold():
            raise ConfigurationError(f"rule integrity check failed: {name}")
        verified.append(name)
    return {"valid": True, "files": verified}


def field_value(event: Event, field: str) -> Any:
    if field.startswith("attributes."):
        value: Any = event.attributes
        parts = field.split(".")[1:]
        if len(parts) > 6:
            return None
        for part in parts:
            if not isinstance(value, dict) or part not in value:
                return None
            value = value[part]
        return value
    return getattr(event, field, None)


def _fold(value: Any, case_sensitive: bool) -> Any:
    return value if case_sensitive or not isinstance(value, str) else value.casefold()


def condition_matches(event: Event, condition: Condition) -> bool:
    actual = field_value(event, condition.field)
    expected = condition.value
    if condition.operator == "exists":
        return (actual is not None) is bool(expected)
    actual = _fold(actual, condition.case_sensitive)
    expected = _fold(expected, condition.case_sensitive)
    if condition.operator == "eq":
        return actual == expected
    if condition.operator == "ne":
        return actual != expected
    if condition.operator == "in":
        if not isinstance(expected, list):
            return False
        return actual in [_fold(item, condition.case_sensitive) for item in expected]
    if condition.operator == "contains":
        if isinstance(actual, str) and isinstance(expected, str):
            return expected in actual
        if isinstance(actual, list):
            return expected in [_fold(item, condition.case_sensitive) for item in actual]
        return False
    if condition.operator == "startswith":
        return isinstance(actual, str) and isinstance(expected, str) and actual.startswith(expected)
    if condition.operator == "endswith":
        return isinstance(actual, str) and isinstance(expected, str) and actual.endswith(expected)
    if condition.operator in {"gte", "lte"}:
        if isinstance(actual, bool) or isinstance(expected, bool):
            return False
        if not isinstance(actual, int | float) or not isinstance(expected, int | float):
            return False
        return actual >= expected if condition.operator == "gte" else actual <= expected
    return False


def rule_matches(event: Event, rule: Rule) -> bool:
    return all(condition_matches(event, condition) for condition in rule.conditions)


def _group_key(event: Event, fields: tuple[str, ...]) -> str:
    values = {field: field_value(event, field) for field in fields}
    return digest(values)


class DetectionEngine:
    def __init__(self, store: EvidenceStore, rules: list[Rule]):
        self.store = store
        self.rules = rules

    def evaluate(self, event: Event) -> list[Alert]:
        alerts: list[Alert] = []
        for rule in self.rules:
            if not rule.enabled or not rule_matches(event, rule):
                continue
            group_fields = rule.threshold.group_by if rule.threshold else rule.group_by
            group_key = _group_key(event, group_fields)
            if rule.threshold:
                rule_key = digest(asdict(rule))
                evidence_ids = self.store.record_correlation_hit(
                    rule_key=rule_key,
                    group_key=group_key,
                    event=event,
                    within_seconds=rule.threshold.within_seconds,
                    maximum=max(rule.threshold.count, 100),
                )
                if len(evidence_ids) < rule.threshold.count:
                    continue
            else:
                evidence_ids = [event.event_id]
            suppression = rule.suppression_seconds if rule.allow_suppression else 0
            # Suppression is based on trusted ingestion time, never attacker-controlled event time.
            if self.store.suppression_active(rule.rule_id, group_key, datetime.now(UTC), suppression):
                continue
            alert = Alert.create(
                rule_id=rule.rule_id,
                title=rule.title,
                severity=rule.severity,
                event_ids=evidence_ids[-100:],
                host=event.host,
                user=event.user,
                techniques=list(rule.techniques),
                evidence={
                    "event_count": len(evidence_ids),
                    "group_key": group_key,
                    "rationale": rule.rationale,
                    "tactics": list(rule.tactics),
                },
            )
            self.store.add_alert(alert, group_key)
            alerts.append(alert)
        return alerts
