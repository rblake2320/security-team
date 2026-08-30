from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session

from .audit import append_audit, verify_audit
from .config import Settings
from .models import (
    Agent,
    Approval,
    AuditEvent,
    Connector,
    Engagement,
    Evidence,
    Finding,
    Incident,
    Invitation,
    Membership,
    Organization,
    OutboxEvent,
    Program,
    RetentionPolicy,
    Task,
    TelemetryEvent,
    User,
    utcnow,
)
from .policies import ACTION_CATALOG, CONNECTOR_CAPABILITIES, ROLES, action_policy, require_permission
from .security import AuthenticationError, Identity, issue_secret, normalize_email, scrub, secret_digest, secret_matches
from .storage import EvidenceStore


@dataclass(frozen=True)
class RequestContext:
    identity: Identity
    user: User
    organization: Organization
    membership: Membership

    @property
    def actor(self) -> str:
        return f"user:{self.user.email}"


def iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def resolve_context(
    session: Session,
    identity: Identity,
    workspace: str | None = None,
) -> RequestContext:
    user = session.scalar(select(User).where(User.email == identity.email))
    if not user or user.status != "active":
        raise AuthenticationError("this identity has not been invited to Mission Control")
    statement = (
        select(Membership, Organization)
        .join(Organization, Organization.id == Membership.organization_id)
        .where(Membership.user_id == user.id, Organization.status == "active")
    )
    if workspace:
        statement = statement.where(
            or_(Organization.id == workspace, Organization.slug == workspace.strip().lower())
        )
    row = session.execute(statement.order_by(Membership.created_at).limit(1)).first()
    if not row:
        raise PermissionError("this identity has no access to the requested workspace")
    membership, organization = row
    user.last_login_at = utcnow()
    return RequestContext(identity, user, organization, membership)


def authenticate_connector(session: Session, token: str, settings: Settings) -> Connector:
    if not token.startswith("aegc_") or len(token) < 24:
        raise AuthenticationError("invalid connector credential")
    prefix = token[:16]
    candidates = session.scalars(
        select(Connector).where(
            Connector.token_prefix == prefix,
            Connector.revoked_at.is_(None),
        )
    )
    for connector in candidates:
        if secret_matches(token, connector.token_hash, settings.token_pepper):
            if connector.status == "revoked":
                break
            return connector
    raise AuthenticationError("invalid connector credential")


def serialize_connector(row: Connector) -> dict[str, Any]:
    return {
        "id": row.id,
        "name": row.name,
        "status": row.status,
        "version": row.version,
        "capabilities": row.capabilities,
        "lastSeenAt": iso(row.last_seen_at),
        "createdAt": iso(row.created_at),
    }


def serialize_agent(row: Agent) -> dict[str, Any]:
    return {
        "id": row.id,
        "connectorId": row.connector_id,
        "externalId": row.external_id,
        "name": row.name,
        "kind": row.kind,
        "status": row.status,
        "capabilities": row.capabilities,
        "metadata": row.metadata_json,
        "lastSeenAt": iso(row.last_seen_at),
    }


def serialize_task(row: Task) -> dict[str, Any]:
    return {
        "id": row.id,
        "programId": row.program_id,
        "connectorId": row.connector_id,
        "agentId": row.agent_id,
        "title": row.title,
        "action": row.action,
        "riskLevel": row.risk_level,
        "status": row.status,
        "payload": row.payload,
        "dryRun": row.dry_run,
        "approvalRequired": row.approval_required,
        "result": row.result,
        "error": row.error,
        "createdAt": iso(row.created_at),
        "updatedAt": iso(row.updated_at),
        "completedAt": iso(row.completed_at),
    }


def serialize_approval(row: Approval) -> dict[str, Any]:
    return {
        "id": row.id,
        "taskId": row.task_id,
        "status": row.status,
        "reason": row.reason,
        "decisionNote": row.decision_note,
        "expiresAt": iso(row.expires_at),
        "createdAt": iso(row.created_at),
        "decidedAt": iso(row.decided_at),
    }


def create_invitation(
    session: Session,
    ctx: RequestContext,
    *,
    email: str,
    role: str,
    expires_hours: int,
    settings: Settings,
) -> tuple[Invitation, str]:
    require_permission(ctx.membership.role, "members.manage")
    if role not in ROLES or role == "owner":
        raise ValueError("invitations may grant admin, operator, approver, auditor, or viewer")
    normalized = normalize_email(email)
    token = issue_secret("aegi")
    invitation = Invitation(
        organization_id=ctx.organization.id,
        email=normalized,
        role=role,
        token_hash=secret_digest(token, settings.token_pepper),
        invited_by_user_id=ctx.user.id,
        expires_at=utcnow() + timedelta(hours=expires_hours),
    )
    session.add(invitation)
    session.flush()
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="invitation.created",
        target_type="invitation",
        target_id=invitation.id,
        detail={"email": normalized, "role": role, "expires_at": iso(invitation.expires_at)},
    )
    return invitation, token


def accept_invitation(
    session: Session,
    identity: Identity,
    token: str,
    settings: Settings,
) -> RequestContext:
    digest = secret_digest(token, settings.token_pepper)
    invitation = session.scalar(
        select(Invitation).where(Invitation.token_hash == digest).with_for_update()
    )
    if not invitation or invitation.status != "pending":
        raise PermissionError("invitation is invalid or already used")
    if invitation.expires_at.replace(tzinfo=timezone.utc) < utcnow():
        invitation.status = "expired"
        raise PermissionError("invitation has expired")
    if not secret_matches(token, invitation.token_hash, settings.token_pepper):
        raise PermissionError("invitation is invalid")
    if normalize_email(identity.email) != invitation.email:
        raise PermissionError("invitation belongs to a different identity")
    user = session.scalar(select(User).where(User.email == identity.email))
    if not user:
        user = User(email=identity.email, display_name=identity.email.split("@", 1)[0])
        session.add(user)
        session.flush()
    membership = session.scalar(
        select(Membership).where(
            Membership.organization_id == invitation.organization_id,
            Membership.user_id == user.id,
        )
    )
    if not membership:
        membership = Membership(
            organization_id=invitation.organization_id,
            user_id=user.id,
            role=invitation.role,
        )
        session.add(membership)
    invitation.status = "accepted"
    invitation.accepted_at = utcnow()
    append_audit(
        session,
        invitation.organization_id,
        actor=f"user:{identity.email}",
        action="invitation.accepted",
        target_type="membership",
        target_id=membership.id,
        detail={"role": invitation.role},
    )
    organization = session.get(Organization, invitation.organization_id)
    if not organization:
        raise ValueError("organization not found")
    return RequestContext(identity, user, organization, membership)


def create_connector(
    session: Session,
    ctx: RequestContext,
    *,
    name: str,
    capabilities: list[str],
    settings: Settings,
) -> tuple[Connector, str]:
    require_permission(ctx.membership.role, "connectors.manage")
    unknown = sorted(set(capabilities) - CONNECTOR_CAPABILITIES)
    if unknown:
        raise ValueError(f"unknown connector capabilities: {', '.join(unknown)}")
    token = issue_secret("aegc")
    connector = Connector(
        organization_id=ctx.organization.id,
        name=name.strip(),
        token_prefix=token[:16],
        token_hash=secret_digest(token, settings.token_pepper),
        capabilities=capabilities,
    )
    session.add(connector)
    session.flush()
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="connector.created",
        target_type="connector",
        target_id=connector.id,
        detail={"name": connector.name, "capabilities": capabilities},
    )
    return connector, token


def revoke_connector(session: Session, ctx: RequestContext, connector_id: str) -> Connector:
    require_permission(ctx.membership.role, "connectors.manage")
    connector = session.scalar(
        select(Connector).where(
            Connector.id == connector_id,
            Connector.organization_id == ctx.organization.id,
        )
    )
    if not connector:
        raise ValueError("connector not found")
    connector.status = "revoked"
    connector.revoked_at = utcnow()
    connector.token_hash = secret_digest(issue_secret("revoked"), connector.id)
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="connector.revoked",
        target_type="connector",
        target_id=connector.id,
        detail={"name": connector.name},
    )
    return connector


def create_task(
    session: Session,
    ctx: RequestContext,
    *,
    title: str,
    action: str,
    connector_id: str | None,
    agent_id: str | None,
    program_id: str | None,
    payload: dict[str, Any],
    dry_run: bool,
) -> Task:
    require_permission(ctx.membership.role, "tasks.create")
    if ctx.organization.kill_switch_active or ctx.organization.safety_level in {"restricted", "halted"}:
        raise PermissionError("workspace safety controls currently prohibit task creation")
    policy = action_policy(action)
    clean_payload = scrub(payload)
    if policy.dry_run_required and not dry_run:
        dry_run_id = str(clean_payload.get("validatedDryRunTaskId", ""))
        prior = session.scalar(
            select(Task).where(
                Task.id == dry_run_id,
                Task.organization_id == ctx.organization.id,
                Task.action == action,
                Task.dry_run.is_(True),
                Task.status == "succeeded",
            )
        )
        if not prior:
            raise PermissionError("a successful validated dry run is required for this critical action")
    connector = None
    if connector_id:
        connector = session.scalar(
            select(Connector).where(
                Connector.id == connector_id,
                Connector.organization_id == ctx.organization.id,
                Connector.revoked_at.is_(None),
            )
        )
        if not connector:
            raise ValueError("connector not found")
        if policy.connector_capability not in connector.capabilities:
            raise PermissionError("connector is not allowlisted for this action")
    if agent_id:
        agent = session.scalar(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.organization_id == ctx.organization.id,
            )
        )
        if not agent or (connector and agent.connector_id != connector.id):
            raise ValueError("agent not found for this connector")
    if program_id and not session.scalar(
        select(Program.id).where(
            Program.id == program_id,
            Program.organization_id == ctx.organization.id,
        )
    ):
        raise ValueError("program not found")
    status = "awaiting_approval" if policy.approval_required else "queued"
    task = Task(
        organization_id=ctx.organization.id,
        program_id=program_id,
        connector_id=connector_id,
        agent_id=agent_id,
        requested_by_user_id=ctx.user.id,
        title=title.strip(),
        action=action,
        risk_level=policy.risk,
        status=status,
        payload=clean_payload,
        dry_run=dry_run,
        approval_required=policy.approval_required,
    )
    session.add(task)
    session.flush()
    if policy.approval_required:
        session.add(
            Approval(
                organization_id=ctx.organization.id,
                task_id=task.id,
                requested_by_user_id=ctx.user.id,
                reason=f"{policy.risk.upper()} action requires human authorization",
                expires_at=utcnow() + timedelta(hours=24),
            )
        )
    session.add(
        OutboxEvent(
            organization_id=ctx.organization.id,
            event_type="task.created",
            payload={"taskId": task.id, "status": status, "risk": policy.risk},
        )
    )
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="task.created",
        target_type="task",
        target_id=task.id,
        detail={
            "action": action,
            "risk": policy.risk,
            "dry_run": dry_run,
            "approval_required": policy.approval_required,
            "connector_id": connector_id,
        },
    )
    return task


def decide_task(
    session: Session,
    ctx: RequestContext,
    task_id: str,
    decision: str,
    note: str,
) -> tuple[Task, Approval]:
    require_permission(ctx.membership.role, "tasks.approve")
    task = session.scalar(
        select(Task)
        .where(Task.id == task_id, Task.organization_id == ctx.organization.id)
        .with_for_update()
    )
    if not task or task.status != "awaiting_approval":
        raise ValueError("task is not awaiting approval")
    approval = session.scalar(
        select(Approval).where(
            Approval.task_id == task.id,
            Approval.organization_id == ctx.organization.id,
            Approval.status == "pending",
        )
    )
    if not approval:
        raise ValueError("approval request not found")
    expires_at = approval.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < utcnow():
        approval.status = "expired"
        task.status = "rejected"
        raise PermissionError("approval request expired and failed closed")
    if task.risk_level == "critical" and task.requested_by_user_id == ctx.user.id:
        raise PermissionError("critical actions require a different human approver")
    approval.status = decision
    approval.decision_note = note.strip()
    approval.decided_by_user_id = ctx.user.id
    approval.decided_at = utcnow()
    task.status = "queued" if decision == "approved" else "rejected"
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action=f"task.{decision}",
        target_type="task",
        target_id=task.id,
        detail={"approval_id": approval.id, "note": note},
    )
    return task, approval


def connector_heartbeat(
    session: Session,
    connector: Connector,
    *,
    version: str,
    capabilities: list[str],
    agents: list[dict[str, Any]],
) -> list[Agent]:
    now = utcnow()
    connector.last_seen_at = now
    connector.status = "online"
    connector.version = version[:32]
    if capabilities:
        connector.capabilities = sorted(set(capabilities) & CONNECTOR_CAPABILITIES)
    rows: list[Agent] = []
    for report in agents:
        row = session.scalar(
            select(Agent).where(
                Agent.connector_id == connector.id,
                Agent.external_id == report["external_id"],
            )
        )
        if not row:
            row = Agent(
                organization_id=connector.organization_id,
                connector_id=connector.id,
                external_id=report["external_id"],
                name=report["name"],
            )
            session.add(row)
        row.name = report["name"]
        row.kind = report["kind"]
        row.status = report["status"]
        row.capabilities = report["capabilities"]
        row.metadata_json = scrub(report["metadata"])
        row.last_seen_at = now
        rows.append(row)
    session.flush()
    return rows


def ingest_events(
    session: Session,
    connector: Connector,
    events: list[dict[str, Any]],
    settings: Settings,
) -> tuple[int, int]:
    if len(events) > settings.max_event_batch:
        raise ValueError(f"event batch exceeds the {settings.max_event_batch} event limit")
    accepted = 0
    duplicates = 0
    connector.last_seen_at = utcnow()
    for event in events:
        exists = session.scalar(
            select(TelemetryEvent.id).where(
                TelemetryEvent.organization_id == connector.organization_id,
                TelemetryEvent.connector_id == connector.id,
                TelemetryEvent.idempotency_key == event["idempotency_key"],
            )
        )
        if exists:
            duplicates += 1
            continue
        agent_id = None
        external_id = event.get("agent_external_id")
        if external_id:
            agent_id = session.scalar(
                select(Agent.id).where(
                    Agent.connector_id == connector.id,
                    Agent.external_id == external_id,
                )
            )
        session.add(
            TelemetryEvent(
                organization_id=connector.organization_id,
                connector_id=connector.id,
                agent_id=agent_id,
                idempotency_key=event["idempotency_key"],
                event_type=event["event_type"],
                severity=event["severity"],
                occurred_at=event["occurred_at"],
                payload=scrub(event["payload"]),
            )
        )
        accepted += 1
    session.flush()
    return accepted, duplicates


def lease_task(session: Session, connector: Connector, settings: Settings) -> tuple[Task, str] | None:
    organization = session.get(Organization, connector.organization_id)
    if not organization or organization.kill_switch_active or organization.safety_level in {"restricted", "halted"}:
        return None
    now = utcnow()
    session.execute(
        update(Task)
        .where(
            Task.organization_id == connector.organization_id,
            Task.connector_id == connector.id,
            Task.status == "running",
            Task.locked_until < now,
        )
        .values(status="queued", lease_token_hash=None, locked_until=None)
    )
    task = session.scalar(
        select(Task)
        .where(
            Task.organization_id == connector.organization_id,
            Task.connector_id == connector.id,
            Task.status == "queued",
        )
        .order_by(Task.created_at)
        .with_for_update(skip_locked=True)
        .limit(1)
    )
    if not task:
        return None
    policy = action_policy(task.action)
    if policy.connector_capability not in connector.capabilities:
        task.status = "blocked"
        task.error = "connector capability revoked before lease"
        return None
    lease_token = issue_secret("aegl")
    task.lease_token_hash = secret_digest(lease_token, settings.token_pepper)
    task.locked_until = now + timedelta(seconds=settings.lease_seconds)
    task.status = "running"
    append_audit(
        session,
        connector.organization_id,
        actor=f"connector:{connector.id}",
        action="task.leased",
        target_type="task",
        target_id=task.id,
        detail={"connector_id": connector.id, "locked_until": iso(task.locked_until)},
    )
    return task, lease_token


def complete_task(
    session: Session,
    connector: Connector,
    task_id: str,
    *,
    lease_token: str,
    status: str,
    result: dict[str, Any],
    error: str | None,
    settings: Settings,
) -> Task:
    task = session.scalar(
        select(Task)
        .where(
            Task.id == task_id,
            Task.organization_id == connector.organization_id,
            Task.connector_id == connector.id,
        )
        .with_for_update()
    )
    if not task or task.status != "running" or not task.lease_token_hash:
        raise ValueError("task has no active lease")
    if not secret_matches(lease_token, task.lease_token_hash, settings.token_pepper):
        raise PermissionError("task lease token is invalid")
    locked_until = task.locked_until
    if locked_until and locked_until.tzinfo is None:
        locked_until = locked_until.replace(tzinfo=timezone.utc)
    if locked_until and locked_until < utcnow():
        raise PermissionError("task lease expired and failed closed")
    task.status = status
    task.result = scrub(result)
    task.error = (error or "")[:4000] or None
    task.completed_at = utcnow()
    task.locked_until = None
    task.lease_token_hash = None
    session.add(
        OutboxEvent(
            organization_id=connector.organization_id,
            event_type="task.completed",
            payload={"taskId": task.id, "status": status},
        )
    )
    append_audit(
        session,
        connector.organization_id,
        actor=f"connector:{connector.id}",
        action=f"task.{status}",
        target_type="task",
        target_id=task.id,
        detail={"connector_id": connector.id, "has_error": bool(error)},
    )
    return task


def create_evidence(
    session: Session,
    ctx: RequestContext,
    store: EvidenceStore,
    *,
    filename: str,
    content_type: str,
    content: bytes,
    task_id: str | None,
    classification: str,
) -> Evidence:
    require_permission(ctx.membership.role, "evidence.write")
    if task_id and not session.scalar(
        select(Task.id).where(Task.id == task_id, Task.organization_id == ctx.organization.id)
    ):
        raise ValueError("task not found")
    policy = session.get(RetentionPolicy, ctx.organization.id)
    retention_days = policy.evidence_days if policy else 365
    stored = store.put(ctx.organization.id, filename, content_type, content)
    row = Evidence(
        organization_id=ctx.organization.id,
        task_id=task_id,
        uploaded_by_user_id=ctx.user.id,
        filename=stored.filename,
        content_type=stored.content_type,
        storage_key=stored.storage_key,
        sha256=stored.sha256,
        size_bytes=stored.size_bytes,
        classification=classification,
        scan_status="quarantined",
        legal_hold=bool(policy and policy.legal_hold_default),
        retention_until=utcnow() + timedelta(days=retention_days),
    )
    session.add(row)
    session.flush()
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="evidence.uploaded",
        target_type="evidence",
        target_id=row.id,
        detail={"sha256": row.sha256, "size": row.size_bytes, "scan_status": row.scan_status},
    )
    return row


def update_safety(
    session: Session,
    ctx: RequestContext,
    *,
    level: str,
    reason: str,
) -> Organization:
    require_permission(ctx.membership.role, "safety.manage")
    organization = session.scalar(
        select(Organization).where(Organization.id == ctx.organization.id).with_for_update()
    )
    if not organization:
        raise ValueError("organization not found")
    before = organization.safety_level
    organization.safety_level = level
    organization.kill_switch_active = level == "halted"
    if level in {"restricted", "halted"}:
        session.execute(
            update(Task)
            .where(
                Task.organization_id == organization.id,
                Task.status.in_(["queued", "running"]),
            )
            .values(status="blocked", error=f"workspace entered {level} safety mode", locked_until=None)
        )
    append_audit(
        session,
        organization.id,
        actor=ctx.actor,
        action="safety.changed",
        target_type="organization",
        target_id=organization.id,
        detail={"before": before, "after": level, "reason": reason},
    )
    return organization


def retention_sweep(
    session: Session,
    ctx: RequestContext,
    store: EvidenceStore,
    *,
    confirmation: str,
) -> dict[str, int]:
    require_permission(ctx.membership.role, "retention.manage")
    if confirmation != "PURGE_EXPIRED_DATA":
        raise PermissionError("retention purge requires explicit confirmation")
    policy = session.get(RetentionPolicy, ctx.organization.id)
    if not policy:
        raise ValueError("retention policy not found")
    now = utcnow()
    telemetry_cutoff = now - timedelta(days=policy.telemetry_days)
    telemetry_count = session.scalar(
        select(func.count()).select_from(TelemetryEvent).where(
            TelemetryEvent.organization_id == ctx.organization.id,
            TelemetryEvent.received_at < telemetry_cutoff,
        )
    ) or 0
    session.execute(
        delete(TelemetryEvent).where(
            TelemetryEvent.organization_id == ctx.organization.id,
            TelemetryEvent.received_at < telemetry_cutoff,
        )
    )
    expired_evidence = list(
        session.scalars(
            select(Evidence).where(
                Evidence.organization_id == ctx.organization.id,
                Evidence.legal_hold.is_(False),
                Evidence.retention_until.is_not(None),
                Evidence.retention_until < now,
            )
        )
    )
    for row in expired_evidence:
        store.delete(row.storage_key)
        session.delete(row)
    append_audit(
        session,
        ctx.organization.id,
        actor=ctx.actor,
        action="retention.swept",
        target_type="organization",
        target_id=ctx.organization.id,
        detail={"telemetry_deleted": telemetry_count, "evidence_deleted": len(expired_evidence)},
    )
    return {"telemetryDeleted": int(telemetry_count), "evidenceDeleted": len(expired_evidence)}


def dashboard(session: Session, ctx: RequestContext) -> dict[str, Any]:
    org_id = ctx.organization.id
    counts = {
        "connectors": session.scalar(select(func.count()).select_from(Connector).where(Connector.organization_id == org_id)) or 0,
        "agents": session.scalar(select(func.count()).select_from(Agent).where(Agent.organization_id == org_id)) or 0,
        "tasks": session.scalar(select(func.count()).select_from(Task).where(Task.organization_id == org_id)) or 0,
        "pendingApprovals": session.scalar(
            select(func.count()).select_from(Approval).where(
                Approval.organization_id == org_id, Approval.status == "pending"
            )
        ) or 0,
        "evidence": session.scalar(select(func.count()).select_from(Evidence).where(Evidence.organization_id == org_id)) or 0,
        "openFindings": session.scalar(
            select(func.count()).select_from(Finding).where(
                Finding.organization_id == org_id, Finding.status != "closed"
            )
        ) or 0,
        "openIncidents": session.scalar(
            select(func.count()).select_from(Incident).where(
                Incident.organization_id == org_id, Incident.status != "resolved"
            )
        ) or 0,
        "events": session.scalar(select(func.count()).select_from(TelemetryEvent).where(TelemetryEvent.organization_id == org_id)) or 0,
        "engagements": session.scalar(select(func.count()).select_from(Engagement).where(Engagement.organization_id == org_id)) or 0,
    }
    connectors = list(
        session.scalars(
            select(Connector).where(Connector.organization_id == org_id).order_by(Connector.created_at.desc()).limit(12)
        )
    )
    agents = list(
        session.scalars(
            select(Agent).where(Agent.organization_id == org_id).order_by(Agent.last_seen_at.desc()).limit(20)
        )
    )
    tasks = list(
        session.scalars(select(Task).where(Task.organization_id == org_id).order_by(Task.created_at.desc()).limit(20))
    )
    approvals = list(
        session.scalars(
            select(Approval).where(Approval.organization_id == org_id).order_by(Approval.created_at.desc()).limit(20)
        )
    )
    policy = session.get(RetentionPolicy, org_id)
    ledger = verify_audit(session, org_id)
    return {
        "workspace": {
            "id": ctx.organization.id,
            "slug": ctx.organization.slug,
            "name": ctx.organization.name,
            "plan": ctx.organization.plan,
            "status": ctx.organization.status,
            "safetyLevel": ctx.organization.safety_level,
            "killSwitchActive": ctx.organization.kill_switch_active,
        },
        "user": {
            "id": ctx.user.id,
            "email": ctx.user.email,
            "displayName": ctx.user.display_name,
            "role": ctx.membership.role,
        },
        "counts": {key: int(value) for key, value in counts.items()},
        "connectors": [serialize_connector(row) for row in connectors],
        "agents": [serialize_agent(row) for row in agents],
        "tasks": [serialize_task(row) for row in tasks],
        "approvals": [serialize_approval(row) for row in approvals],
        "retention": {
            "telemetryDays": policy.telemetry_days if policy else 90,
            "taskDays": policy.task_days if policy else 365,
            "evidenceDays": policy.evidence_days if policy else 365,
            "auditDays": policy.audit_days if policy else 2555,
            "legalHoldDefault": policy.legal_hold_default if policy else False,
        },
        "ledger": ledger,
    }


def recent_audit(session: Session, organization_id: str, limit: int = 30) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(AuditEvent)
            .where(AuditEvent.organization_id == organization_id)
            .order_by(AuditEvent.sequence.desc())
            .limit(limit)
        )
    )
    return [
        {
            "id": row.id,
            "at": iso(row.created_at),
            "kind": row.action,
            "summary": f"{row.action} · {row.target_type}",
            "targetType": row.target_type,
            "targetId": row.target_id,
            "detail": row.detail,
            "hash": row.event_hash,
            "previous": row.previous_hash,
        }
        for row in rows
    ]
