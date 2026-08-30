from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class Base(DeclarativeBase):
    pass


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    slug: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    plan: Mapped[str] = mapped_column(String(32), nullable=False, default="beta")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    safety_level: Mapped[str] = mapped_column(String(24), nullable=False, default="normal")
    kill_switch_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    audit_head: Mapped[str] = mapped_column(String(64), nullable=False, default="GENESIS")
    audit_seq: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(160), nullable=False, default="Operator")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Membership(Base):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id", name="uq_membership_org_user"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(24), nullable=False, default="viewer")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Invitation(Base):
    __tablename__ = "invitations"
    __table_args__ = (Index("ix_invitation_org_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    role: Mapped[str] = mapped_column(String(24), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    invited_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (UniqueConstraint("organization_id", "slug", name="uq_program_org_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    slug: Mapped[str] = mapped_column(String(80), nullable=False, default="security")
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    current_state: Mapped[str] = mapped_column(String(64), nullable=False, default="DESIGN_COMPLETE")
    marking: Mapped[str] = mapped_column(String(64), nullable=False, default="CUSTOMER_CONFIDENTIAL")
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class SecurityControl(Base):
    __tablename__ = "security_controls"
    __table_args__ = (
        UniqueConstraint("organization_id", "control_key", name="uq_security_control_org_key"),
        Index("ix_security_control_org_team", "organization_id", "owner_team"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    control_key: Mapped[str] = mapped_column(String(96), nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    domain: Mapped[str] = mapped_column(String(64), nullable=False)
    owner_team: Mapped[str] = mapped_column(String(24), nullable=False)
    objective: Mapped[str] = mapped_column(String(600), nullable=False)
    modes: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_source: Mapped[str] = mapped_column(String(96), nullable=False, default="platform")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="configured")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Connector(Base):
    __tablename__ = "connectors"
    __table_args__ = (UniqueConstraint("organization_id", "name", name="uq_connector_org_name"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_prefix: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="provisioned")
    version: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("connector_id", "external_id", name="uq_agent_connector_external"),
        Index("ix_agent_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(160), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(48), nullable=False, default="agent")
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    capabilities: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_task_org_status_created", "organization_id", "status", "created_at"),
        Index("ix_task_connector_status", "connector_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    program_id: Mapped[str | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))
    connector_id: Mapped[str | None] = mapped_column(ForeignKey("connectors.id", ondelete="SET NULL"))
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    lease_token_hash: Mapped[str | None] = mapped_column(String(64))
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Approval(Base):
    __tablename__ = "approvals"
    __table_args__ = (Index("ix_approval_org_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    requested_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    decided_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    reason: Mapped[str] = mapped_column(String(600), nullable=False)
    decision_note: Mapped[str | None] = mapped_column(String(600))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TelemetryEvent(Base):
    __tablename__ = "telemetry_events"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "connector_id", "idempotency_key", name="uq_event_org_connector_key"
        ),
        Index("ix_event_org_occurred", "organization_id", "occurred_at"),
        Index("ix_event_org_type", "organization_id", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    agent_id: Mapped[str | None] = mapped_column(ForeignKey("agents.id", ondelete="SET NULL"))
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(96), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False, default="info")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class Evidence(Base):
    __tablename__ = "evidence"
    __table_args__ = (
        Index("ix_evidence_org_created", "organization_id", "created_at"),
        Index("ix_evidence_org_sha", "organization_id", "sha256"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    uploaded_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    connector_id: Mapped[str | None] = mapped_column(ForeignKey("connectors.id"))
    filename: Mapped[str] = mapped_column(String(240), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    classification: Mapped[str] = mapped_column(String(48), nullable=False, default="customer-confidential")
    scan_status: Mapped[str] = mapped_column(String(24), nullable=False, default="quarantined")
    legal_hold: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    retention_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Finding(Base):
    __tablename__ = "findings"
    __table_args__ = (
        Index("ix_finding_org_status_severity", "organization_id", "status", "severity"),
        Index("ix_finding_engagement_run", "engagement_id", "assessment_run_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    program_id: Mapped[str | None] = mapped_column(ForeignKey("programs.id", ondelete="SET NULL"))
    engagement_id: Mapped[str | None] = mapped_column(ForeignKey("engagements.id", ondelete="SET NULL"))
    assessment_run_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_runs.id", ondelete="SET NULL"))
    fingerprint: Mapped[str | None] = mapped_column(String(64), index=True)
    owner_team: Mapped[str | None] = mapped_column(String(24))
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (Index("ix_incident_org_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    commander_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIPolicy(Base):
    __tablename__ = "ai_policies"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    default_disposition: Mapped[str] = mapped_column(String(24), nullable=False, default="monitor")
    sensitive_data_disposition: Mapped[str] = mapped_column(String(24), nullable=False, default="block")
    approved_vendors: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    approved_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    blocked_domains: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    prohibited_data_labels: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: ["credentials", "regulated", "restricted", "source-code-secret"],
    )
    retain_prompt_content: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AIAsset(Base):
    __tablename__ = "ai_assets"
    __table_args__ = (
        UniqueConstraint("organization_id", "source", "external_id", name="uq_ai_asset_source_external"),
        Index("ix_ai_asset_org_disposition", "organization_id", "disposition"),
        Index("ix_ai_asset_org_last_seen", "organization_id", "last_seen_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[str | None] = mapped_column(ForeignKey("connectors.id", ondelete="SET NULL"))
    source: Mapped[str] = mapped_column(String(40), nullable=False)
    external_id: Mapped[str] = mapped_column(String(180), nullable=False)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    vendor: Mapped[str] = mapped_column(String(100), nullable=False, default="unknown")
    category: Mapped[str] = mapped_column(String(48), nullable=False, default="unknown")
    disposition: Mapped[str] = mapped_column(String(24), nullable=False, default="unknown")
    risk_score: Mapped[int] = mapped_column(Integer, nullable=False, default=50)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    user_ref_hash: Mapped[str | None] = mapped_column(String(64))
    device_ref_hash: Mapped[str | None] = mapped_column(String(64))
    models: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    tools: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    mcp_servers: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    resources: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[dict[str, Any]] = mapped_column("metadata", JSON, nullable=False, default=dict)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AIUsageEvent(Base):
    __tablename__ = "ai_usage_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "connector_id", "idempotency_key", name="uq_ai_usage_connector_key"),
        Index("ix_ai_usage_org_occurred", "organization_id", "occurred_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    connector_id: Mapped[str] = mapped_column(ForeignKey("connectors.id", ondelete="CASCADE"), nullable=False)
    asset_id: Mapped[str] = mapped_column(ForeignKey("ai_assets.id", ondelete="CASCADE"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    destination_domain: Mapped[str | None] = mapped_column(String(253))
    model: Mapped[str | None] = mapped_column(String(120))
    bytes_sent: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    bytes_received: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    estimated_cost_microusd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    data_labels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    policy_action: Mapped[str] = mapped_column(String(24), nullable=False, default="monitor")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PolicyViolation(Base):
    __tablename__ = "policy_violations"
    __table_args__ = (
        Index("ix_violation_org_status", "organization_id", "status"),
        Index("ix_violation_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    asset_id: Mapped[str] = mapped_column(ForeignKey("ai_assets.id", ondelete="CASCADE"), nullable=False)
    usage_event_id: Mapped[str | None] = mapped_column(ForeignKey("ai_usage_events.id", ondelete="SET NULL"))
    rule_id: Mapped[str] = mapped_column(String(96), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    disposition: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="open")
    summary: Mapped[str] = mapped_column(String(600), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class RetentionPolicy(Base):
    __tablename__ = "retention_policies"

    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), primary_key=True
    )
    telemetry_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    task_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    evidence_days: Mapped[int] = mapped_column(Integer, nullable=False, default=365)
    audit_days: Mapped[int] = mapped_column(Integer, nullable=False, default=2555)
    legal_hold_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (
        UniqueConstraint("organization_id", "sequence", name="uq_audit_org_sequence"),
        Index("ix_audit_org_created", "organization_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    actor: Mapped[str] = mapped_column(String(320), nullable=False)
    action: Mapped[str] = mapped_column(String(96), nullable=False)
    target_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(80), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (Index("ix_outbox_status_available", "status", "available_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(96), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Engagement(Base):
    __tablename__ = "engagements"
    __table_args__ = (
        Index("ix_engagement_org_status_updated", "organization_id", "status", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    client_name: Mapped[str | None] = mapped_column(String(160))
    engagement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ready")
    objective: Mapped[str] = mapped_column(Text, nullable=False)
    scope_rules: Mapped[str] = mapped_column(Text, nullable=False)
    authorization_basis: Mapped[str] = mapped_column(String(48), nullable=False)
    authorization_attestation: Mapped[str] = mapped_column(String(600), nullable=False)
    authorization_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    authorized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    authorization_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    selected_teams: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )


class EngagementTarget(Base):
    __tablename__ = "engagement_targets"
    __table_args__ = (
        Index("ix_engagement_target_org_engagement", "organization_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    engagement_id: Mapped[str] = mapped_column(
        ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(180), nullable=False)
    locator: Mapped[str] = mapped_column(Text, nullable=False)
    environment: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    scope_status: Mapped[str] = mapped_column(String(24), nullable=False, default="in-scope")
    notes: Mapped[str] = mapped_column(String(1000), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssessmentRun(Base):
    __tablename__ = "assessment_runs"
    __table_args__ = (
        UniqueConstraint("engagement_id", "sequence", name="uq_assessment_run_engagement_sequence"),
        Index("ix_assessment_run_org_status", "organization_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    engagement_id: Mapped[str] = mapped_column(
        ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    mode: Mapped[str] = mapped_column(String(32), nullable=False, default="safe")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    connector_id: Mapped[str | None] = mapped_column(ForeignKey("connectors.id", ondelete="SET NULL"))
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.id", ondelete="SET NULL"))
    baseline_run_id: Mapped[str | None] = mapped_column(ForeignKey("assessment_runs.id", ondelete="SET NULL"))
    team_plan: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    recommendations: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    score: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class EngagementAsset(Base):
    __tablename__ = "engagement_assets"
    __table_args__ = (
        UniqueConstraint("evidence_id", name="uq_engagement_asset_evidence"),
        Index("ix_engagement_asset_org_engagement", "organization_id", "engagement_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    engagement_id: Mapped[str] = mapped_column(
        ForeignKey("engagements.id", ondelete="CASCADE"), nullable=False
    )
    assessment_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("assessment_runs.id", ondelete="SET NULL")
    )
    evidence_id: Mapped[str] = mapped_column(ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False)
    media_kind: Mapped[str] = mapped_column(String(32), nullable=False, default="binary")
    analysis_status: Mapped[str] = mapped_column(String(32), nullable=False, default="quarantined")
    suggestions: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
