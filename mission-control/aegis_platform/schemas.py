from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


RoleName = Literal["owner", "admin", "operator", "approver", "auditor", "viewer"]
Severity = Literal["info", "low", "medium", "high", "critical"]


class InvitationCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: RoleName
    expires_hours: int = Field(default=72, ge=1, le=720, alias="expiresHours")


class InvitationAccept(BaseModel):
    token: str = Field(min_length=24, max_length=256)


class ConnectorCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    capabilities: list[str] = Field(default_factory=lambda: ["observe.status"], max_length=32)

    @field_validator("capabilities")
    @classmethod
    def unique_capabilities(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(item.strip()[:80] for item in value if item.strip()))


class AgentReport(BaseModel):
    external_id: str = Field(min_length=1, max_length=160, alias="externalId")
    name: str = Field(min_length=1, max_length=160)
    kind: str = Field(default="agent", min_length=1, max_length=48)
    status: str = Field(default="online", min_length=1, max_length=24)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Heartbeat(BaseModel):
    version: str = Field(default="unknown", max_length=32)
    capabilities: list[str] = Field(default_factory=list, max_length=32)
    agents: list[AgentReport] = Field(default_factory=list, max_length=100)


class EventInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128, alias="idempotencyKey")
    event_type: str = Field(min_length=2, max_length=96, alias="eventType")
    severity: Severity = "info"
    occurred_at: datetime = Field(alias="occurredAt")
    agent_external_id: str | None = Field(default=None, max_length=160, alias="agentExternalId")
    payload: dict[str, Any] = Field(default_factory=dict)


class EventBatch(BaseModel):
    events: list[EventInput] = Field(min_length=1, max_length=500)


class TaskCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    action: str = Field(min_length=2, max_length=80)
    connector_id: str | None = Field(default=None, alias="connectorId")
    agent_id: str | None = Field(default=None, alias="agentId")
    program_id: str | None = Field(default=None, alias="programId")
    payload: dict[str, Any] = Field(default_factory=dict)
    dry_run: bool = Field(default=False, alias="dryRun")


class ApprovalDecision(BaseModel):
    decision: Literal["approved", "rejected"]
    note: str = Field(min_length=3, max_length=600)


class TaskComplete(BaseModel):
    lease_token: str = Field(min_length=24, max_length=256, alias="leaseToken")
    status: Literal["succeeded", "failed"]
    result: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None, max_length=4000)


class TaskLeaseRenew(BaseModel):
    lease_token: str = Field(min_length=24, max_length=256, alias="leaseToken")


TeamName = Literal["purple", "white", "yellow", "green", "orange", "blue", "red"]


class EngagementTargetInput(BaseModel):
    kind: Literal["website", "api", "repository", "cloud", "mobile", "network", "artifact", "media", "other"]
    display_name: str = Field(min_length=2, max_length=180, alias="displayName")
    locator: str = Field(min_length=2, max_length=2000)
    environment: Literal["development", "staging", "production", "client", "unknown"] = "unknown"
    notes: str = Field(default="", max_length=1000)


class EngagementCreate(BaseModel):
    name: str = Field(min_length=3, max_length=160)
    client_name: str | None = Field(default=None, max_length=160, alias="clientName")
    engagement_type: Literal["own-site", "pre-launch", "client-assessment", "continuous", "incident", "other"] = Field(alias="engagementType")
    objective: str = Field(min_length=10, max_length=4000)
    scope_rules: str = Field(min_length=10, max_length=10_000, alias="scopeRules")
    authorization_basis: Literal["asset-owner", "internal-approval", "written-client-authorization", "bug-bounty-scope"] = Field(alias="authorizationBasis")
    authorization_attestation: str = Field(min_length=12, max_length=600, alias="authorizationAttestation")
    authorization_confirmed: Literal[True] = Field(alias="authorizationConfirmed")
    authorization_expires_at: datetime | None = Field(default=None, alias="authorizationExpiresAt")
    selected_teams: list[TeamName] = Field(default_factory=lambda: ["purple", "white", "yellow", "green", "orange", "blue", "red"], min_length=1, max_length=7, alias="selectedTeams")
    targets: list[EngagementTargetInput] = Field(min_length=1, max_length=50)

    @field_validator("selected_teams")
    @classmethod
    def unique_teams(cls, value: list[TeamName]) -> list[TeamName]:
        return list(dict.fromkeys(value))


class EngagementLaunch(BaseModel):
    mode: Literal["safe", "standard", "deep"] = "safe"
    connector_id: str | None = Field(default=None, alias="connectorId")
    baseline_run_id: str | None = Field(default=None, alias="baselineRunId")


class EngagementAssetAnalyze(BaseModel):
    connector_id: str | None = Field(default=None, alias="connectorId")


class FindingCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    description: str = Field(min_length=3, max_length=20_000)
    severity: Literal["low", "medium", "high", "critical"]
    program_id: str | None = Field(default=None, alias="programId")
    engagement_id: str | None = Field(default=None, alias="engagementId")
    assessment_run_id: str | None = Field(default=None, alias="assessmentRunId")
    fingerprint: str | None = Field(default=None, min_length=8, max_length=64)
    owner_team: TeamName | None = Field(default=None, alias="ownerTeam")
    owner_user_id: str | None = Field(default=None, alias="ownerUserId")
    due_at: datetime | None = Field(default=None, alias="dueAt")


class IncidentCreate(BaseModel):
    title: str = Field(min_length=3, max_length=240)
    severity: Literal["low", "medium", "high", "critical"]
    summary: str = Field(default="", max_length=20_000)


class RetentionUpdate(BaseModel):
    telemetry_days: int = Field(ge=7, le=2555, alias="telemetryDays")
    task_days: int = Field(ge=30, le=3650, alias="taskDays")
    evidence_days: int = Field(ge=30, le=3650, alias="evidenceDays")
    audit_days: int = Field(ge=365, le=3650, alias="auditDays")
    legal_hold_default: bool = Field(alias="legalHoldDefault")


class SafetyChange(BaseModel):
    level: Literal["normal", "cautious", "restricted", "halted"]
    reason: str = Field(min_length=8, max_length=600)


class EvidenceScanUpdate(BaseModel):
    status: Literal["clean", "rejected"]
    note: str = Field(min_length=3, max_length=600)


class RetentionSweepRequest(BaseModel):
    confirmation: Literal["PURGE_EXPIRED_DATA"]


class AIAssetDiscovery(BaseModel):
    external_id: str = Field(min_length=2, max_length=180, alias="externalId")
    source: Literal["endpoint", "network", "gateway", "cloud", "manual"]
    name: str = Field(default="Unknown AI asset", min_length=2, max_length=180)
    vendor: str = Field(default="unknown", max_length=100)
    category: Literal["chat", "coding-assistant", "local-agent", "cloud-agent", "model-api", "mcp-server", "browser-extension", "unknown"] = "unknown"
    process_name: str | None = Field(default=None, max_length=180, alias="processName")
    destination_domain: str | None = Field(default=None, max_length=253, alias="destinationDomain")
    user_ref: str | None = Field(default=None, max_length=320, alias="userRef")
    device_ref: str | None = Field(default=None, max_length=320, alias="deviceRef")
    models: list[str] = Field(default_factory=list, max_length=64)
    tools: list[str] = Field(default_factory=list, max_length=128)
    mcp_servers: list[str] = Field(default_factory=list, max_length=128, alias="mcpServers")
    resources: list[str] = Field(default_factory=list, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class AIAssetBatch(BaseModel):
    assets: list[AIAssetDiscovery] = Field(min_length=1, max_length=200)


class AIUsageInput(BaseModel):
    idempotency_key: str = Field(min_length=8, max_length=128, alias="idempotencyKey")
    asset_external_id: str = Field(min_length=2, max_length=180, alias="assetExternalId")
    source: Literal["endpoint", "network", "gateway", "cloud", "manual"]
    destination_domain: str | None = Field(default=None, max_length=253, alias="destinationDomain")
    model: str | None = Field(default=None, max_length=120)
    bytes_sent: int = Field(default=0, ge=0, le=10_000_000_000, alias="bytesSent")
    bytes_received: int = Field(default=0, ge=0, le=10_000_000_000, alias="bytesReceived")
    prompt_tokens: int = Field(default=0, ge=0, le=100_000_000, alias="promptTokens")
    completion_tokens: int = Field(default=0, ge=0, le=100_000_000, alias="completionTokens")
    estimated_cost_microusd: int = Field(default=0, ge=0, le=10_000_000_000, alias="estimatedCostMicrousd")
    data_labels: list[str] = Field(default_factory=list, max_length=64, alias="dataLabels")
    occurred_at: datetime = Field(alias="occurredAt")


class AIUsageBatch(BaseModel):
    usage: list[AIUsageInput] = Field(min_length=1, max_length=500)


class AIPolicyUpdate(BaseModel):
    default_disposition: Literal["monitor", "require-approval", "block"] = Field(alias="defaultDisposition")
    sensitive_data_disposition: Literal["monitor", "require-approval", "block"] = Field(alias="sensitiveDataDisposition")
    approved_vendors: list[str] = Field(default_factory=list, max_length=100, alias="approvedVendors")
    approved_domains: list[str] = Field(default_factory=list, max_length=200, alias="approvedDomains")
    blocked_domains: list[str] = Field(default_factory=list, max_length=200, alias="blockedDomains")
    prohibited_data_labels: list[str] = Field(default_factory=list, max_length=100, alias="prohibitedDataLabels")
    retain_prompt_content: bool = Field(default=False, alias="retainPromptContent")


class AIAssetDecision(BaseModel):
    disposition: Literal["approved", "restricted", "blocked"]
    reason: str = Field(min_length=8, max_length=600)


class ViolationDecision(BaseModel):
    status: Literal["acknowledged", "resolved", "false-positive"]
    note: str = Field(min_length=3, max_length=600)


class SecurityControlUpdate(BaseModel):
    enabled: bool
    owner_team: Literal["purple", "white", "yellow", "green", "orange", "blue", "red"] = Field(alias="ownerTeam")
    status: Literal["configured", "verified", "exception"]
    reason: str = Field(min_length=8, max_length=600)
    configuration: dict[str, Any] = Field(default_factory=dict)
