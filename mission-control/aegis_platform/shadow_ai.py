from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .audit import append_audit
from .config import Settings
from .models import AIAsset, AIPolicy, AIUsageEvent, Connector, PolicyViolation, utcnow
from .policies import require_permission
from .security import scrub, secret_digest
from .service import RequestContext, iso


KNOWN_DOMAINS: dict[str, tuple[str, str]] = {
    "openai.com": ("OpenAI", "chat"),
    "chatgpt.com": ("OpenAI", "chat"),
    "anthropic.com": ("Anthropic", "chat"),
    "claude.ai": ("Anthropic", "chat"),
    "perplexity.ai": ("Perplexity", "chat"),
    "cursor.com": ("Cursor", "coding-assistant"),
    "githubcopilot.com": ("GitHub", "coding-assistant"),
    "generativelanguage.googleapis.com": ("Google", "model-api"),
    "deepseek.com": ("DeepSeek", "chat"),
    "huggingface.co": ("Hugging Face", "model-api"),
    "cohere.com": ("Cohere", "model-api"),
    "mistral.ai": ("Mistral", "model-api"),
    "x.ai": ("xAI", "chat"),
}

KNOWN_PROCESSES: dict[str, tuple[str, str]] = {
    "claude": ("Anthropic Claude Code", "coding-assistant"),
    "codex": ("OpenAI Codex", "coding-assistant"),
    "cursor": ("Cursor", "coding-assistant"),
    "copilot": ("GitHub Copilot", "coding-assistant"),
    "ollama": ("Ollama", "local-agent"),
    "lmstudio": ("LM Studio", "local-agent"),
    "openclaw": ("OpenClaw", "local-agent"),
}


def normalize_domain(value: str | None) -> str:
    domain = (value or "").strip().lower().rstrip(".")
    domain = domain.split(":", 1)[0]
    if not domain or len(domain) > 253 or not re.fullmatch(r"[a-z0-9.-]+", domain):
        return ""
    return domain


def domain_matches(domain: str, patterns: list[str]) -> bool:
    return any(domain == item or domain.endswith("." + item) for item in patterns)


def inferred_identity(domain: str, process_name: str | None) -> tuple[str, str]:
    for known, result in KNOWN_DOMAINS.items():
        if domain == known or domain.endswith("." + known):
            return result
    process = (process_name or "").lower().replace(".exe", "")
    for known, result in KNOWN_PROCESSES.items():
        if known in process:
            return result
    return "unknown", "unknown"


def policy_for(session: Session, organization_id: str) -> AIPolicy:
    policy = session.get(AIPolicy, organization_id)
    if not policy:
        policy = AIPolicy(organization_id=organization_id)
        session.add(policy)
        session.flush()
    return policy


def asset_disposition(policy: AIPolicy, vendor: str, domain: str) -> str:
    blocked = [normalize_domain(item) for item in policy.blocked_domains]
    approved = [normalize_domain(item) for item in policy.approved_domains]
    if domain and domain_matches(domain, blocked):
        return "blocked"
    if vendor.lower() in {item.lower() for item in policy.approved_vendors}:
        return "approved"
    if domain and domain_matches(domain, approved):
        return "approved"
    return "unknown"


def risk_score(disposition: str, category: str, tools: list[str], resources: list[str]) -> int:
    score = {"approved": 20, "restricted": 65, "blocked": 95}.get(disposition, 55)
    if category in {"local-agent", "cloud-agent", "mcp-server"}:
        score += 15
    if tools:
        score += min(10, len(tools))
    if resources:
        score += min(10, len(resources))
    return min(100, score)


def ingest_assets(
    session: Session,
    connector: Connector,
    reports: list[dict[str, Any]],
    settings: Settings,
) -> tuple[int, int]:
    policy = policy_for(session, connector.organization_id)
    created = 0
    updated = 0
    for report in reports:
        domain = normalize_domain(report.get("destination_domain"))
        inferred_vendor, inferred_category = inferred_identity(domain, report.get("process_name"))
        vendor = report.get("vendor", "unknown").strip() or inferred_vendor
        if vendor.lower() == "unknown" and inferred_vendor != "unknown":
            vendor = inferred_vendor
        category = report.get("category", "unknown")
        if category == "unknown" and inferred_category != "unknown":
            category = inferred_category
        row = session.scalar(
            select(AIAsset).where(
                AIAsset.organization_id == connector.organization_id,
                AIAsset.source == report["source"],
                AIAsset.external_id == report["external_id"],
            )
        )
        disposition = asset_disposition(policy, vendor, domain)
        if not row:
            row = AIAsset(
                organization_id=connector.organization_id,
                connector_id=connector.id,
                source=report["source"],
                external_id=report["external_id"],
                name=report["name"],
            )
            session.add(row)
            created += 1
        else:
            updated += 1
        row.connector_id = connector.id
        row.name = report["name"]
        row.vendor = vendor[:100]
        row.category = category
        if row.disposition == "unknown":
            row.disposition = disposition
        row.user_ref_hash = secret_digest(report["user_ref"], settings.token_pepper + connector.organization_id) if report.get("user_ref") else None
        row.device_ref_hash = secret_digest(report["device_ref"], settings.token_pepper + connector.organization_id) if report.get("device_ref") else None
        row.models = list(dict.fromkeys(report.get("models", [])))[:64]
        row.tools = list(dict.fromkeys(report.get("tools", [])))[:128]
        row.mcp_servers = list(dict.fromkeys(report.get("mcp_servers", [])))[:128]
        row.resources = list(dict.fromkeys(report.get("resources", [])))[:128]
        row.metadata_json = scrub({**report.get("metadata", {}), "destinationDomain": domain})
        row.risk_score = risk_score(row.disposition, row.category, row.tools, row.resources)
        row.last_seen_at = utcnow()
    connector.last_seen_at = utcnow()
    session.flush()
    append_audit(
        session,
        connector.organization_id,
        actor=f"connector:{connector.id}",
        action="shadow_ai.assets_ingested",
        target_type="connector",
        target_id=connector.id,
        detail={"created": created, "updated": updated},
    )
    return created, updated


def ingest_usage(
    session: Session,
    connector: Connector,
    reports: list[dict[str, Any]],
) -> tuple[int, int, int]:
    policy = policy_for(session, connector.organization_id)
    accepted = 0
    duplicates = 0
    violations = 0
    approved_domains = [normalize_domain(item) for item in policy.approved_domains]
    blocked_domains = [normalize_domain(item) for item in policy.blocked_domains]
    prohibited = {item.lower() for item in policy.prohibited_data_labels}
    for report in reports:
        if session.scalar(
            select(AIUsageEvent.id).where(
                AIUsageEvent.organization_id == connector.organization_id,
                AIUsageEvent.connector_id == connector.id,
                AIUsageEvent.idempotency_key == report["idempotency_key"],
            )
        ):
            duplicates += 1
            continue
        asset = session.scalar(
            select(AIAsset).where(
                AIAsset.organization_id == connector.organization_id,
                AIAsset.source == report["source"],
                AIAsset.external_id == report["asset_external_id"],
            )
        )
        if not asset:
            raise ValueError("usage references an undiscovered AI asset")
        domain = normalize_domain(report.get("destination_domain"))
        labels = sorted({item.lower()[:80] for item in report.get("data_labels", [])})
        matching_sensitive = sorted(set(labels) & prohibited)
        disposition = policy.default_disposition
        rule_id = "shadow-ai.unsanctioned"
        severity = "medium"
        summary = f"Unsanctioned AI usage detected for {asset.name}"
        if asset.disposition == "approved" or (domain and domain_matches(domain, approved_domains)):
            disposition = "monitor"
            rule_id = "shadow-ai.approved-usage"
        if asset.disposition == "blocked" or (domain and domain_matches(domain, blocked_domains)):
            disposition = "block"
            rule_id = "shadow-ai.blocked-destination"
            severity = "critical"
            summary = f"Blocked AI destination used by {asset.name}"
        if matching_sensitive:
            disposition = policy.sensitive_data_disposition
            rule_id = "shadow-ai.sensitive-data"
            severity = "high" if disposition != "block" else "critical"
            summary = f"Sensitive data labels observed in traffic to {asset.name}"
        usage = AIUsageEvent(
            organization_id=connector.organization_id,
            connector_id=connector.id,
            asset_id=asset.id,
            idempotency_key=report["idempotency_key"],
            destination_domain=domain or None,
            model=report.get("model"),
            bytes_sent=report.get("bytes_sent", 0),
            bytes_received=report.get("bytes_received", 0),
            prompt_tokens=report.get("prompt_tokens", 0),
            completion_tokens=report.get("completion_tokens", 0),
            estimated_cost_microusd=report.get("estimated_cost_microusd", 0),
            data_labels=labels,
            policy_action=disposition,
            occurred_at=report["occurred_at"],
        )
        session.add(usage)
        session.flush()
        if rule_id != "shadow-ai.approved-usage" and (asset.disposition != "approved" or matching_sensitive):
            session.add(
                PolicyViolation(
                    organization_id=connector.organization_id,
                    asset_id=asset.id,
                    usage_event_id=usage.id,
                    rule_id=rule_id,
                    severity=severity,
                    disposition=disposition,
                    summary=summary,
                    detail={"domain": domain, "dataLabels": matching_sensitive, "bytesSent": usage.bytes_sent},
                )
            )
            violations += 1
        accepted += 1
    session.flush()
    return accepted, duplicates, violations


def serialize_asset(row: AIAsset) -> dict[str, Any]:
    return {
        "id": row.id,
        "source": row.source,
        "externalId": row.external_id,
        "name": row.name,
        "vendor": row.vendor,
        "category": row.category,
        "disposition": row.disposition,
        "riskScore": row.risk_score,
        "models": row.models,
        "tools": row.tools,
        "mcpServers": row.mcp_servers,
        "resources": row.resources,
        "firstSeenAt": iso(row.first_seen_at),
        "lastSeenAt": iso(row.last_seen_at),
    }


def serialize_violation(row: PolicyViolation) -> dict[str, Any]:
    return {
        "id": row.id,
        "assetId": row.asset_id,
        "ruleId": row.rule_id,
        "severity": row.severity,
        "disposition": row.disposition,
        "status": row.status,
        "summary": row.summary,
        "detail": row.detail,
        "createdAt": iso(row.created_at),
        "resolvedAt": iso(row.resolved_at),
    }


def shadow_dashboard(session: Session, ctx: RequestContext) -> dict[str, Any]:
    require_permission(ctx.membership.role, "workspace.read")
    org_id = ctx.organization.id
    assets = list(
        session.scalars(
            select(AIAsset).where(AIAsset.organization_id == org_id).order_by(AIAsset.risk_score.desc(), AIAsset.last_seen_at.desc()).limit(200)
        )
    )
    violations = list(
        session.scalars(
            select(PolicyViolation).where(PolicyViolation.organization_id == org_id).order_by(PolicyViolation.created_at.desc()).limit(200)
        )
    )
    usage = session.execute(
        select(
            func.count(AIUsageEvent.id),
            func.coalesce(func.sum(AIUsageEvent.bytes_sent), 0),
            func.coalesce(func.sum(AIUsageEvent.estimated_cost_microusd), 0),
        ).where(AIUsageEvent.organization_id == org_id)
    ).one()
    policy = policy_for(session, org_id)
    return {
        "counts": {
            "assets": len(assets),
            "unsanctioned": len([row for row in assets if row.disposition == "unknown"]),
            "blocked": len([row for row in assets if row.disposition == "blocked"]),
            "openViolations": len([row for row in violations if row.status == "open"]),
            "usageEvents": int(usage[0]),
            "bytesSent": int(usage[1]),
            "estimatedCostMicrousd": int(usage[2]),
        },
        "assets": [serialize_asset(row) for row in assets],
        "violations": [serialize_violation(row) for row in violations],
        "policy": {
            "defaultDisposition": policy.default_disposition,
            "sensitiveDataDisposition": policy.sensitive_data_disposition,
            "approvedVendors": policy.approved_vendors,
            "approvedDomains": policy.approved_domains,
            "blockedDomains": policy.blocked_domains,
            "prohibitedDataLabels": policy.prohibited_data_labels,
            "retainPromptContent": policy.retain_prompt_content,
            "updatedAt": iso(policy.updated_at),
        },
    }
