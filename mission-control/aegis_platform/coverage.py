from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Connector, SecurityControl
from .service import RequestContext, iso


CONTROL_CATALOG: tuple[dict[str, Any], ...] = (
    {"key": "purple.ai-end-to-end", "title": "AI defense validation loop", "domain": "shadow-ai", "team": "purple", "modes": ["validate", "detect", "respond"], "source": "shadow_ai.assets", "objective": "Correlate discovery, policy, enforcement, and retest evidence across the full AI path."},
    {"key": "purple.control-evidence", "title": "Control effectiveness evidence", "domain": "assurance", "team": "purple", "modes": ["validate"], "source": "platform", "objective": "Prove controls work through repeatable tests without turning engineering health into an assurance claim."},
    {"key": "white.ai-governance", "title": "AI use governance", "domain": "shadow-ai", "team": "white", "modes": ["govern", "prevent"], "source": "platform", "objective": "Own approved AI services, prohibited data classes, exceptions, retention, and independent authorization."},
    {"key": "white.execution-authority", "title": "High-impact execution authority", "domain": "agent-safety", "team": "white", "modes": ["prevent", "govern"], "source": "platform", "objective": "Require dry-run, separation of duties, approval, and kill-switch authority for consequential actions."},
    {"key": "white.audit-integrity", "title": "Independent audit integrity", "domain": "assurance", "team": "white", "modes": ["govern", "validate"], "source": "platform", "objective": "Verify tenant-scoped, append-only decision and action provenance."},
    {"key": "yellow.secure-build", "title": "Secure build and dependency chain", "domain": "application-security", "team": "yellow", "modes": ["prevent"], "source": "telemetry.code", "objective": "Prevent vulnerable dependencies, leaked secrets, unsafe defaults, and unreviewed AI-generated code from reaching production."},
    {"key": "yellow.model-supply-chain", "title": "Model and agent supply chain", "domain": "shadow-ai", "team": "yellow", "modes": ["prevent", "validate"], "source": "shadow_ai.assets", "objective": "Inventory model, tool, plugin, MCP, and agent dependencies and verify provenance before use."},
    {"key": "green.ai-architecture", "title": "AI attack-surface architecture", "domain": "shadow-ai", "team": "green", "modes": ["discover", "prevent"], "source": "shadow_ai.assets", "objective": "Map users, devices, models, tools, resources, trust boundaries, and data flows without collecting prompt content."},
    {"key": "green.data-boundaries", "title": "Tenant and data boundaries", "domain": "data-security", "team": "green", "modes": ["prevent", "validate"], "source": "platform", "objective": "Keep owner, showcase, and customer data stores, credentials, evidence, and retrieval paths separated."},
    {"key": "green.identity-surface", "title": "Human and machine identity surface", "domain": "identity", "team": "green", "modes": ["discover", "prevent"], "source": "telemetry.identity", "objective": "Inventory user, service, connector, agent, and workload identities with least-privilege paths."},
    {"key": "orange.ai-abuse-cases", "title": "AI abuse-case register", "domain": "shadow-ai", "team": "orange", "modes": ["anticipate", "prevent"], "source": "platform", "objective": "Maintain misuse cases for prompt injection, data exfiltration, tool abuse, privilege chaining, poisoning, and evasion."},
    {"key": "orange.threat-model", "title": "Living trust-boundary threat model", "domain": "risk", "team": "orange", "modes": ["anticipate", "validate"], "source": "platform", "objective": "Apply STRIDE to every connector, data flow, store, agent action, and third-party AI dependency."},
    {"key": "blue.network-ai-discovery", "title": "Network AI discovery", "domain": "shadow-ai", "team": "blue", "modes": ["discover", "detect"], "source": "telemetry.network", "objective": "Resolve AI destinations to user, device, process, volume, policy, and approved or blocked state."},
    {"key": "blue.endpoint-ai-discovery", "title": "Endpoint AI discovery", "domain": "shadow-ai", "team": "blue", "modes": ["discover", "detect"], "source": "telemetry.endpoint", "objective": "Detect local agents, coding assistants, model runtimes, browser extensions, and unsanctioned AI tools."},
    {"key": "blue.sensitive-data-egress", "title": "Sensitive data egress prevention", "domain": "data-security", "team": "blue", "modes": ["prevent", "detect"], "source": "telemetry.dlp", "objective": "Classify and block prohibited data movement to sanctioned and unsanctioned AI without retaining raw prompts."},
    {"key": "blue.ai-incident-response", "title": "AI incident response", "domain": "incident-response", "team": "blue", "modes": ["detect", "respond", "recover"], "source": "platform", "objective": "Triage policy violations, contain approved targets, preserve evidence, and track recovery."},
    {"key": "red.prompt-injection", "title": "Prompt-injection resistance", "domain": "ai-security", "team": "red", "modes": ["validate"], "source": "telemetry.ai-gateway", "objective": "Test direct, indirect, multimodal, and retrieval-borne injection against bounded test systems."},
    {"key": "red.agent-tool-abuse", "title": "Agent tool-abuse resistance", "domain": "agent-safety", "team": "red", "modes": ["validate"], "source": "telemetry.agent", "objective": "Prove tool allowlists, scopes, budgets, approvals, and isolation resist unauthorized agent actions."},
    {"key": "red.ai-evasion", "title": "Shadow AI detection evasion", "domain": "shadow-ai", "team": "red", "modes": ["validate"], "source": "shadow_ai.assets", "objective": "Test unknown domains, alternate clients, local models, tunnels, extensions, and MCP paths for discovery gaps."},
    {"key": "purple.attack-path-validation", "title": "Attack-path control validation", "domain": "exposure-management", "team": "purple", "modes": ["validate", "detect", "respond"], "source": "telemetry.vulnerability", "objective": "Combine exploitability, identity paths, detections, containment, and remediation into repeatable adversary-to-recovery evidence."},
    {"key": "purple.detection-response-loop", "title": "Detection-to-response loop", "domain": "security-operations", "team": "purple", "modes": ["validate", "detect", "respond", "recover"], "source": "telemetry.endpoint", "objective": "Prove a controlled signal becomes a correct alert, bounded response, preserved evidence, and verified recovery."},
    {"key": "purple.cloud-control-validation", "title": "Cloud control validation", "domain": "cloud-security", "team": "purple", "modes": ["validate"], "source": "telemetry.cloud", "objective": "Continuously validate cloud identity, configuration, logging, network, data, and workload controls against realistic paths."},
    {"key": "white.risk-register", "title": "Enterprise risk and exception register", "domain": "risk", "team": "white", "modes": ["govern", "prioritize"], "source": "platform", "objective": "Record owners, decisions, due dates, compensating controls, expiry, residual risk, and acceptance authority."},
    {"key": "white.privacy-compliance", "title": "Privacy and compliance obligations", "domain": "privacy", "team": "white", "modes": ["govern", "validate"], "source": "telemetry.privacy", "objective": "Map data processing, residency, consent, retention, deletion, breach duties, and customer commitments to evidence."},
    {"key": "white.third-party-risk", "title": "Third-party and vendor risk", "domain": "supply-chain", "team": "white", "modes": ["govern", "prevent"], "source": "telemetry.third-party", "objective": "Track external services, subprocessors, access, attestations, contractual duties, concentration, and exit plans."},
    {"key": "white.resilience-governance", "title": "Resilience and crisis authority", "domain": "resilience", "team": "white", "modes": ["govern", "recover"], "source": "telemetry.backup", "objective": "Define recovery objectives, crisis roles, communication authority, restore evidence, and business continuity decisions."},
    {"key": "yellow.application-security", "title": "Application and API security", "domain": "application-security", "team": "yellow", "modes": ["prevent", "validate"], "source": "telemetry.api", "objective": "Enforce threat-informed design, authentication, authorization, input/output validation, abuse controls, and API inventory."},
    {"key": "yellow.secrets-lifecycle", "title": "Secrets and key lifecycle", "domain": "secrets", "team": "yellow", "modes": ["prevent", "respond"], "source": "telemetry.secrets", "objective": "Detect committed or exposed secrets, use managed stores, rotate safely, and prove revocation without logging secret values."},
    {"key": "yellow.infrastructure-as-code", "title": "Infrastructure and policy as code", "domain": "cloud-security", "team": "yellow", "modes": ["prevent", "validate"], "source": "telemetry.code", "objective": "Scan infrastructure, container, Kubernetes, and policy changes before deployment and bind exceptions to expiry."},
    {"key": "yellow.container-supply-chain", "title": "Container and artifact supply chain", "domain": "supply-chain", "team": "yellow", "modes": ["prevent", "validate"], "source": "telemetry.container", "objective": "Generate SBOMs, verify signatures and provenance, scan artifacts, pin dependencies, and quarantine failed releases."},
    {"key": "yellow.remediation-sla", "title": "Risk-based remediation workflow", "domain": "vulnerability-management", "team": "yellow", "modes": ["prevent", "respond"], "source": "telemetry.vulnerability", "objective": "Prioritize reachable and exploitable weaknesses, assign ownership, enforce deadlines, and require retest evidence."},
    {"key": "green.asset-inventory", "title": "Authoritative asset inventory", "domain": "asset-management", "team": "green", "modes": ["discover", "govern"], "source": "telemetry.asset", "objective": "Inventory managed and unmanaged hardware, software, cloud, SaaS, data, APIs, identities, agents, and business owners."},
    {"key": "green.zero-trust-architecture", "title": "Zero-trust access architecture", "domain": "identity", "team": "green", "modes": ["prevent", "validate"], "source": "telemetry.identity", "objective": "Require strong identity, device posture, least privilege, segmented access, explicit policy, and continuous verification."},
    {"key": "green.privileged-access", "title": "Privileged access architecture", "domain": "identity", "team": "green", "modes": ["prevent", "govern"], "source": "telemetry.identity", "objective": "Separate administrative identities, remove standing privilege, vault credentials, approve elevation, and record privileged actions."},
    {"key": "green.network-segmentation", "title": "Network segmentation and egress", "domain": "network-security", "team": "green", "modes": ["prevent", "detect"], "source": "telemetry.network", "objective": "Constrain east-west and outbound paths, make policy ownership explicit, and ensure security services cannot be bypassed."},
    {"key": "green.cloud-workload-architecture", "title": "Cloud and workload architecture", "domain": "cloud-security", "team": "green", "modes": ["prevent", "discover"], "source": "telemetry.cloud", "objective": "Model accounts, subscriptions, clusters, identities, public exposure, control planes, secrets, and data services."},
    {"key": "green.data-protection", "title": "Data classification and cryptography", "domain": "data-security", "team": "green", "modes": ["discover", "prevent", "recover"], "source": "telemetry.dlp", "objective": "Classify data, minimize collection, encrypt in transit and at rest, govern keys, back up safely, and verify deletion."},
    {"key": "orange.exposure-model", "title": "External attack-surface model", "domain": "exposure-management", "team": "orange", "modes": ["discover", "anticipate"], "source": "telemetry.asset", "objective": "Continuously map domains, certificates, services, APIs, cloud edges, leaked credentials, and ownership drift."},
    {"key": "orange.threat-intelligence", "title": "Threat intelligence and horizon scan", "domain": "threat-intelligence", "team": "orange", "modes": ["anticipate", "prioritize"], "source": "telemetry.threat-intel", "objective": "Turn relevant adversary behavior, vulnerabilities, campaigns, and technology shifts into owned defensive changes."},
    {"key": "orange.human-fraud-abuse", "title": "Human, fraud, and abuse scenarios", "domain": "human-risk", "team": "orange", "modes": ["anticipate", "prevent"], "source": "telemetry.email", "objective": "Model phishing, social engineering, account recovery abuse, insider paths, payment fraud, and support-channel manipulation."},
    {"key": "blue.endpoint-detection", "title": "Endpoint prevention and detection", "domain": "endpoint-security", "team": "blue", "modes": ["prevent", "detect", "respond"], "source": "telemetry.endpoint", "objective": "Cover managed endpoints and servers with health, tamper protection, behavior detections, isolation, and recovery evidence."},
    {"key": "blue.identity-detection", "title": "Identity threat detection", "domain": "identity", "team": "blue", "modes": ["detect", "respond"], "source": "telemetry.identity", "objective": "Detect credential abuse, impossible access, privilege changes, token theft, dormant accounts, and machine-identity anomalies."},
    {"key": "blue.cloud-saas-detection", "title": "Cloud and SaaS detection", "domain": "cloud-security", "team": "blue", "modes": ["discover", "detect", "respond"], "source": "telemetry.cloud", "objective": "Collect control-plane, workload, identity, storage, and SaaS audit signals with tested detections and response paths."},
    {"key": "blue.email-web-dns", "title": "Email, web, and DNS protection", "domain": "human-risk", "team": "blue", "modes": ["prevent", "detect", "respond"], "source": "telemetry.email", "objective": "Prevent and investigate phishing, malicious links, spoofing, domain abuse, unsafe downloads, and command-and-control resolution."},
    {"key": "blue.vulnerability-exposure", "title": "Vulnerability and exposure operations", "domain": "vulnerability-management", "team": "blue", "modes": ["discover", "prioritize", "respond"], "source": "telemetry.vulnerability", "objective": "Correlate vulnerabilities with reachability, exploit evidence, asset value, identity paths, remediation, and retest state."},
    {"key": "blue.forensics-preservation", "title": "Forensics and evidence preservation", "domain": "incident-response", "team": "blue", "modes": ["respond", "recover", "validate"], "source": "platform", "objective": "Preserve scoped evidence with integrity, quarantine, custody, legal hold, retention, and documented investigation decisions."},
    {"key": "blue.backup-recovery", "title": "Backup and recovery assurance", "domain": "resilience", "team": "blue", "modes": ["prevent", "recover", "validate"], "source": "telemetry.backup", "objective": "Protect immutable backups, monitor completion, test isolated restores, measure recovery objectives, and retain receipts."},
    {"key": "red.external-internal-testing", "title": "External and internal adversarial testing", "domain": "adversary-simulation", "team": "red", "modes": ["validate"], "source": "telemetry.network", "objective": "Test authorized external, internal, assumed-breach, identity, and lateral movement paths with explicit scope and stop conditions."},
    {"key": "red.application-api-testing", "title": "Application and API adversarial testing", "domain": "application-security", "team": "red", "modes": ["validate"], "source": "telemetry.api", "objective": "Validate authorization, session, business logic, injection, file handling, rate limits, and tenant isolation with bounded tests."},
    {"key": "red.cloud-container-testing", "title": "Cloud, container, and Kubernetes testing", "domain": "cloud-security", "team": "red", "modes": ["validate"], "source": "telemetry.kubernetes", "objective": "Test identity, metadata, workload, registry, admission, secret, network, and control-plane paths in authorized environments."},
    {"key": "red.social-engineering", "title": "Authorized social engineering", "domain": "human-risk", "team": "red", "modes": ["validate"], "source": "telemetry.email", "objective": "Measure reporting and process resilience through separately authorized simulations with safety, privacy, and stop conditions."},
    {"key": "red.data-exfiltration", "title": "Data exfiltration resistance", "domain": "data-security", "team": "red", "modes": ["validate"], "source": "telemetry.dlp", "objective": "Test authorized egress channels, encoding, side channels, RAG leakage, tool misuse, and policy bypass without using real sensitive data."},
)


def seed_security_controls(session: Session, organization_id: str) -> None:
    existing = set(
        session.scalars(
            select(SecurityControl.control_key).where(SecurityControl.organization_id == organization_id)
        )
    )
    for item in CONTROL_CATALOG:
        if item["key"] in existing:
            continue
        session.add(
            SecurityControl(
                organization_id=organization_id,
                control_key=item["key"],
                title=item["title"],
                domain=item["domain"],
                owner_team=item["team"],
                objective=item["objective"],
                modes=item["modes"],
                required_source=item["source"],
            )
        )


def security_coverage(session: Session, ctx: RequestContext) -> dict[str, Any]:
    controls = list(
        session.scalars(
            select(SecurityControl)
            .where(SecurityControl.organization_id == ctx.organization.id)
            .order_by(SecurityControl.owner_team, SecurityControl.control_key)
        )
    )
    connectors = list(
        session.scalars(
            select(Connector).where(
                Connector.organization_id == ctx.organization.id,
                Connector.revoked_at.is_(None),
            )
        )
    )
    capabilities = {capability for connector in connectors for capability in connector.capabilities}
    teams: dict[str, dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    for control in controls:
        observable = control.required_source == "platform" or control.required_source in capabilities
        effective_status = "disabled" if not control.enabled else (
            "exception" if control.status == "exception" else (
                "verified" if control.status == "verified" and observable else (
                    "configured" if observable else "telemetry-gap"
                )
            )
        )
        row = {
            "id": control.id,
            "key": control.control_key,
            "title": control.title,
            "domain": control.domain,
            "ownerTeam": control.owner_team,
            "objective": control.objective,
            "modes": control.modes,
            "requiredSource": control.required_source,
            "status": effective_status,
            "configuredStatus": control.status,
            "enabled": control.enabled,
            "configuration": control.configuration,
            "updatedAt": iso(control.updated_at),
        }
        rows.append(row)
        team = teams.setdefault(control.owner_team, {"team": control.owner_team, "controls": 0, "verified": 0, "gaps": 0})
        team["controls"] += 1
        team["verified"] += int(effective_status == "verified")
        team["gaps"] += int(effective_status == "telemetry-gap")
    enabled = [row for row in rows if row["enabled"]]
    observable = [row for row in enabled if row["status"] in {"configured", "verified"}]
    return {
        "summary": {
            "controls": len(rows),
            "enabled": len(enabled),
            "observable": len(observable),
            "verified": len([row for row in enabled if row["status"] == "verified"]),
            "telemetryGaps": len([row for row in enabled if row["status"] == "telemetry-gap"]),
            "exceptions": len([row for row in enabled if row["status"] == "exception"]),
            "coveragePercent": round((len(observable) / len(enabled) * 100), 1) if enabled else 0,
        },
        "sources": sorted(capabilities),
        "teams": list(teams.values()),
        "controls": rows,
    }
