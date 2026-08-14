"""Configuration quality gate used before operator deployment."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .coverage import coverage_report, load_coverage_target
from .detection import load_rules, verify_rule_manifest
from .errors import ConfigurationError
from .health import load_sensor_policy
from .response import HIGH_RISK_ACTIONS, load_playbooks, response_plan


def validate_configuration(
    *,
    rules_path: str | Path,
    manifest_path: str | Path,
    coverage_path: str | Path,
    sensors_path: str | Path,
    playbooks_path: str | Path,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    manifest = verify_rule_manifest(rules_path, manifest_path)
    checks.append({"name": "rule_manifest", "passed": manifest["valid"], "detail": manifest})

    rules = load_rules(rules_path)
    checks.append({"name": "rules_loaded", "passed": len(rules) >= 20, "detail": {"count": len(rules)}})

    target = load_coverage_target(coverage_path)
    coverage = coverage_report(rules, target)
    checks.append(
        {
            "name": "target_technique_coverage",
            "passed": not coverage["gaps"],
            "detail": {"covered": coverage["covered"], "total": coverage["total"], "gaps": coverage["gaps"]},
        }
    )
    checks.append(
        {
            "name": "enterprise_tactic_coverage",
            "passed": not coverage["tactic_gaps"],
            "detail": {"gaps": coverage["tactic_gaps"]},
        }
    )

    sensor_policy = load_sensor_policy(sensors_path)
    configured_sources = {item["source"] for item in sensor_policy}
    required_sources = {
        source
        for technique in target
        for source in technique.get("required_telemetry", [])
        if isinstance(source, str)
    }
    missing_sources = sorted(required_sources - configured_sources)
    checks.append(
        {
            "name": "telemetry_freshness_contracts",
            "passed": not missing_sources,
            "detail": {"missing_sources": missing_sources},
        }
    )

    playbooks = load_playbooks(playbooks_path)
    missing_rollbacks: list[str] = []
    for playbook_id, playbook in playbooks.items():
        response_plan(playbooks, playbook_id, {"alert_id": "assurance-check", "severity": "critical"})
        for step in playbook.get("steps", []):
            if step.get("action") in HIGH_RISK_ACTIONS and not step.get("rollback"):
                missing_rollbacks.append(f"{playbook_id}:{step.get('action')}")
    checks.append(
        {
            "name": "high_risk_response_rollbacks",
            "passed": not missing_rollbacks,
            "detail": {"missing": missing_rollbacks},
        }
    )

    failures = [check for check in checks if not check["passed"]]
    if failures:
        names = ", ".join(check["name"] for check in failures)
        raise ConfigurationError(f"configuration assurance failed: {names}")
    return {
        "valid": True,
        "checks": checks,
        "rules": len(rules),
        "coverage_percent": coverage["coverage_percent"],
        "warning": "Configuration validation does not replace live telemetry and detection efficacy tests.",
    }
