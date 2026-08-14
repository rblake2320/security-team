"""ATT&CK coverage accounting that reports gaps instead of hiding them."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .detection import Rule
from .errors import ConfigurationError

ENTERPRISE_TACTICS = (
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
)


def load_coverage_target(path: str | Path) -> list[dict[str, Any]]:
    try:
        target = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("coverage target is unreadable") from exc
    if not isinstance(target, list):
        raise ConfigurationError("coverage target must be a list")
    techniques: set[str] = set()
    for item in target:
        technique = item.get("technique") if isinstance(item, dict) else None
        if not isinstance(technique, str) or technique in techniques:
            raise ConfigurationError("coverage target contains an invalid or duplicate technique")
        techniques.add(technique)
    return target


def coverage_report(rules: list[Rule], target: list[dict[str, Any]]) -> dict[str, Any]:
    enabled = [rule for rule in rules if rule.enabled]
    mapping: dict[str, list[str]] = {}
    for rule in enabled:
        for technique in rule.techniques:
            mapping.setdefault(technique, []).append(rule.rule_id)
    rows: list[dict[str, Any]] = []
    for item in target:
        technique = item.get("technique")
        if not isinstance(technique, str):
            raise ConfigurationError("coverage item lacks a technique")
        rules_for_technique = sorted(mapping.get(technique, []))
        telemetry = item.get("required_telemetry", [])
        rows.append(
            {
                "technique": technique,
                "name": item.get("name", ""),
                "priority": item.get("priority", "standard"),
                "status": "covered" if rules_for_technique else "gap",
                "rules": rules_for_technique,
                "required_telemetry": telemetry,
            }
        )
    covered = sum(row["status"] == "covered" for row in rows)
    total = len(rows)
    tactic_set = {tactic for rule in enabled for tactic in rule.tactics}
    tactic_gaps = [tactic for tactic in ENTERPRISE_TACTICS if tactic not in tactic_set]
    return {
        "covered": covered,
        "total": total,
        "coverage_percent": round(100 * covered / total, 1) if total else 0.0,
        "gaps": [row for row in rows if row["status"] == "gap"],
        "tactics_covered": sorted(tactic_set.intersection(ENTERPRISE_TACTICS)),
        "tactic_gaps": tactic_gaps,
        "techniques": rows,
        "warning": "A mapping is not effectiveness proof; validate each rule with representative telemetry.",
    }
