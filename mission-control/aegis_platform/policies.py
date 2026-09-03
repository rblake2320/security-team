from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass


ROLES = ("owner", "admin", "operator", "approver", "auditor", "viewer")

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "owner": frozenset({"*"}),
    "admin": frozenset(
        {
            "workspace.read",
            "workspace.manage",
            "members.manage",
            "connectors.manage",
            "tasks.create",
            "tasks.read",
            "tasks.approve",
            "evidence.write",
            "evidence.read",
            "findings.write",
            "incidents.write",
            "audit.read",
            "retention.manage",
            "safety.manage",
            "shadow_ai.manage",
            "controls.manage",
            "engagements.manage",
            "engagements.read",
            "engagements.export",
        }
    ),
    "operator": frozenset(
        {
            "workspace.read",
            "tasks.create",
            "tasks.read",
            "evidence.write",
            "evidence.read",
            "findings.write",
            "incidents.write",
            "engagements.manage",
            "engagements.read",
            "engagements.export",
        }
    ),
    "approver": frozenset(
        {"workspace.read", "tasks.read", "tasks.approve", "evidence.read", "audit.read", "engagements.read", "engagements.export"}
    ),
    "auditor": frozenset({"workspace.read", "tasks.read", "evidence.read", "audit.read", "engagements.read", "engagements.export"}),
    "viewer": frozenset({"workspace.read", "tasks.read", "evidence.read", "engagements.read"}),
}


@dataclass(frozen=True)
class ActionPolicy:
    risk: str
    approval_required: bool
    dry_run_required: bool
    connector_capability: str
    reversible: bool


ACTION_CATALOG: dict[str, ActionPolicy] = {
    "observe.status": ActionPolicy("low", False, False, "observe.status", True),
    "evidence.collect": ActionPolicy("medium", False, False, "evidence.collect", True),
    "evidence.analyze": ActionPolicy("medium", False, False, "evidence.analyze", True),
    "assessment.execute": ActionPolicy("high", True, False, "assessment.execute", True),
    "gate.run": ActionPolicy("high", True, False, "gate.run", True),
    "finding.validate": ActionPolicy("high", True, False, "finding.validate", True),
    "task.execute": ActionPolicy("high", True, False, "task.execute", False),
    "incident.contain": ActionPolicy("critical", True, True, "incident.contain", True),
    "deployment.release": ActionPolicy("critical", True, True, "deployment.release", True),
    "shadow_ai.block": ActionPolicy("critical", True, True, "shadow_ai.block", True),
    "identity.access_revoke": ActionPolicy("critical", True, True, "identity.access_revoke", True),
    "endpoint.isolate": ActionPolicy("critical", True, True, "endpoint.isolate", True),
    "network.block": ActionPolicy("critical", True, True, "network.block", True),
    "cloud.quarantine": ActionPolicy("critical", True, True, "cloud.quarantine", True),
    "data.quarantine": ActionPolicy("critical", True, True, "data.quarantine", True),
    "secret.rotate": ActionPolicy("critical", True, True, "secret.rotate", False),
    "artifact.quarantine": ActionPolicy("high", True, False, "artifact.quarantine", True),
    "vulnerability.remediate": ActionPolicy("high", True, False, "vulnerability.remediate", False),
    "policy.exception": ActionPolicy("high", True, False, "policy.exception", True),
    "incident.notify": ActionPolicy("high", True, False, "incident.notify", False),
    "recovery.restore_drill": ActionPolicy("high", True, False, "recovery.restore_drill", True),
}

OBSERVATION_CAPABILITIES = frozenset(
    {
        "shadow_ai.assets",
        "shadow_ai.usage",
        "telemetry.network",
        "telemetry.endpoint",
        "telemetry.dlp",
        "telemetry.code",
        "telemetry.identity",
        "telemetry.ai-gateway",
        "telemetry.agent",
        "telemetry.cloud",
        "telemetry.saas",
        "telemetry.asset",
        "telemetry.vulnerability",
        "telemetry.email",
        "telemetry.dns",
        "telemetry.api",
        "telemetry.container",
        "telemetry.kubernetes",
        "telemetry.secrets",
        "telemetry.backup",
        "telemetry.threat-intel",
        "telemetry.third-party",
        "telemetry.privacy",
    }
)

CONNECTOR_CAPABILITIES = frozenset(ACTION_CATALOG) | OBSERVATION_CAPABILITIES

POLICY_PACKAGE_NAME = "aegis-action-catalog"
POLICY_PACKAGE_VERSION = "1.0.0"


def _catalog_material() -> dict[str, dict[str, object]]:
    return {
        action: {
            "risk": policy.risk,
            "approvalRequired": policy.approval_required,
            "dryRunRequired": policy.dry_run_required,
            "connectorCapability": policy.connector_capability,
            "reversible": policy.reversible,
        }
        for action, policy in sorted(ACTION_CATALOG.items())
    }


def action_policy_receipt(action: str, build_revision: str) -> dict[str, object]:
    """Return the immutable policy material that governed a task at creation."""
    action_policy(action)
    catalog = _catalog_material()
    catalog_sha256 = hashlib.sha256(
        json.dumps(catalog, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    revision = build_revision if re.fullmatch(r"[0-9a-f]{40}", build_revision) else "development"
    return {
        "schema": "aegis.action-policy-receipt/1.0",
        "package": {
            "name": POLICY_PACKAGE_NAME,
            "version": POLICY_PACKAGE_VERSION,
            "contentSha256": catalog_sha256,
            "buildRevision": revision,
        },
        "action": action,
        **catalog[action],
    }


def require_permission(role: str, permission: str) -> None:
    allowed = ROLE_PERMISSIONS.get(role, frozenset())
    if "*" not in allowed and permission not in allowed:
        raise PermissionError(f"role {role} does not permit {permission}")


def action_policy(action: str) -> ActionPolicy:
    try:
        return ACTION_CATALOG[action]
    except KeyError as exc:
        raise ValueError("action is not in the deny-by-default catalog") from exc
