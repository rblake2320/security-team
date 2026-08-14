"""Fail-closed response planning; this module never executes containment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, ValidationError

HIGH_RISK_ACTIONS = {"isolate_host", "disable_account", "block_indicator", "revoke_sessions", "restore_system"}
ALLOWED_ACTIONS = HIGH_RISK_ACTIONS | {
    "preserve_evidence",
    "validate_change",
    "restore_control",
    "hunt_related",
    "reset_credentials",
    "review_privilege",
    "protect_backups",
    "scope_impact",
    "classify_data",
}


def load_playbooks(path: str | Path) -> dict[str, Any]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("playbook file is unreadable") from exc
    if not isinstance(data, dict):
        raise ConfigurationError("playbook file must be an object")
    return data


def response_plan(playbooks: dict[str, Any], playbook_id: str, alert: dict[str, Any]) -> dict[str, Any]:
    raw = playbooks.get(playbook_id)
    if not isinstance(raw, dict):
        raise ValidationError("unknown playbook")
    steps = raw.get("steps")
    if not isinstance(steps, list) or not steps:
        raise ConfigurationError("playbook contains no response steps")
    planned: list[dict[str, Any]] = []
    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or not isinstance(step.get("action"), str):
            raise ConfigurationError("playbook step is invalid")
        action = step["action"]
        if action not in ALLOWED_ACTIONS:
            raise ConfigurationError(f"playbook contains an unknown action: {action}")
        high_risk = action in HIGH_RISK_ACTIONS
        planned.append(
            {
                "sequence": index,
                "action": action,
                "description": step.get("description", ""),
                "mode": "recommendation_only",
                "approval_required": high_risk or bool(step.get("approval_required", False)),
                "minimum_approvers": 2 if high_risk else (1 if step.get("approval_required") else 0),
                "rollback": step.get("rollback"),
            }
        )
    return {
        "playbook_id": playbook_id,
        "alert_id": alert.get("alert_id"),
        "severity": alert.get("severity"),
        "execution_enabled": False,
        "steps": planned,
        "operator_notice": (
            "Review evidence, preserve forensics, obtain approvals, and execute through authorized tooling."
        ),
    }
