from __future__ import annotations

import logging
import re
import time
import uuid
from collections.abc import Iterator
from contextlib import asynccontextmanager
from datetime import timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from .audit import append_audit, verify_audit
from .config import PLATFORM_ROOT, Settings
from .db import Database
from .models import (
    Agent,
    AIAsset,
    AIPolicy,
    Approval,
    AssessmentRun,
    Connector,
    Engagement,
    EngagementAsset,
    EngagementTarget,
    Evidence,
    Finding,
    Incident,
    Membership,
    Organization,
    Program,
    PolicyViolation,
    RetentionPolicy,
    SecurityControl,
    Task,
    TelemetryEvent,
    User,
    utcnow,
)
from .policies import ACTION_CATALOG, ROLE_PERMISSIONS, require_permission
from .schemas import (
    AIAssetBatch,
    AIAssetDecision,
    AIPolicyUpdate,
    AIUsageBatch,
    ApprovalDecision,
    ConnectorCreate,
    EventBatch,
    EvidenceScanUpdate,
    EngagementCreate,
    EngagementAssetAnalyze,
    EngagementLaunch,
    FindingCreate,
    Heartbeat,
    IncidentCreate,
    InvitationAccept,
    InvitationCreate,
    RetentionSweepRequest,
    RetentionUpdate,
    SafetyChange,
    SecurityControlUpdate,
    TaskComplete,
    TaskCreate,
    ViolationDecision,
)
from .security import AccessVerifier, AuthenticationError, scrub, secret_matches
from .service import (
    RequestContext,
    accept_invitation,
    authenticate_connector,
    complete_task,
    connector_heartbeat,
    create_connector,
    create_evidence,
    create_invitation,
    create_task,
    dashboard,
    decide_task,
    ingest_events,
    iso,
    lease_task,
    recent_audit,
    resolve_context,
    retention_sweep,
    revoke_connector,
    serialize_agent,
    serialize_approval,
    serialize_connector,
    serialize_task,
    update_safety,
)
from .storage import EvidenceStore
from .engagements import (
    asset_suggestions,
    compare_runs,
    export_engagement_zip,
    list_engagements,
    media_kind,
    normalize_target,
    serialize_engagement,
    sync_asset_analysis_result,
    sync_assessment_result,
    team_plan as build_team_plan,
)
from .coverage import security_coverage
from .shadow_ai import (
    ingest_assets,
    ingest_usage,
    normalize_domain,
    policy_for,
    serialize_asset,
    serialize_violation,
    shadow_dashboard,
)


LOG = logging.getLogger("aegis.platform")
MAX_JSON_REQUEST = 1 * 1024 * 1024
TEAM_DEFAULTS = {
    "purple": ("Purple Team", "#9b7cff", "Validate", "Offense + defense integration"),
    "white": ("White Team", "#e8edf2", "Authorize", "Independent safety and exercise control"),
    "yellow": ("Yellow Team", "#f4d35e", "Build", "Secure engineering and remediation"),
    "green": ("Green Team", "#4ee29a", "Engineer", "Defensibility and detection architecture"),
    "orange": ("Orange Team", "#ff985b", "Anticipate", "Adversarial design review"),
    "blue": ("Blue Team", "#5ba8ff", "Defend", "Detection, response, and recovery"),
    "red": ("Red Team", "#ff5f67", "Prove", "Authorized adversarial assessment"),
}


def problem(status: int, title: str, detail: str, request_id: str = "") -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": title,
            "status": status,
            "detail": detail,
            "requestId": request_id,
        },
        media_type="application/problem+json",
    )


def create_app(settings: Settings | None = None, *, create_schema: bool = True) -> FastAPI:
    settings = settings or Settings.from_env()
    database = Database(settings)
    if create_schema and settings.environment != "production":
        database.create_schema()
    database.bootstrap()
    verifier = AccessVerifier(settings)
    evidence_store = EvidenceStore(settings.evidence_root, settings.max_evidence_bytes, settings.evidence_master_key)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        LOG.info("AEGIS platform starting environment=%s auth=%s", settings.environment, settings.auth_mode)
        yield
        database.engine.dispose()

    app = FastAPI(
        title="AEGIS Mission Control API",
        version="2.0.0",
        docs_url="/api/docs" if settings.environment != "production" else None,
        redoc_url=None,
        openapi_url="/api/openapi.json" if settings.environment != "production" else None,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.database = database
    app.state.evidence_store = evidence_store
    if settings.environment == "production":
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=[settings.public_hostname, "localhost", "127.0.0.1"],
        )

    @app.middleware("http")
    async def security_boundary(request: Request, call_next):  # type: ignore[no-untyped-def]
        supplied_request_id = request.headers.get("x-request-id", "")[:80]
        request_id = supplied_request_id if re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", supplied_request_id) else str(uuid.uuid4())
        request.state.request_id = request_id
        content_length = request.headers.get("content-length")
        if content_length and request.url.path != "/api/v1/evidence":
            try:
                if int(content_length) > MAX_JSON_REQUEST:
                    return problem(413, "Payload Too Large", "request body exceeds 1 MiB", request_id)
            except ValueError:
                return problem(400, "Bad Request", "invalid Content-Length", request_id)
        started = time.monotonic()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
        )
        if settings.environment == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Server-Timing"] = f"app;dur={(time.monotonic() - started) * 1000:.1f}"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        elif response.headers.get("content-type", "").lower().startswith("text/html"):
            response.headers["Cache-Control"] = "no-cache, no-transform"
        return response

    @app.exception_handler(AuthenticationError)
    async def authentication_error(request: Request, exc: AuthenticationError) -> JSONResponse:
        return problem(401, "Unauthorized", str(exc), request.state.request_id)

    @app.exception_handler(PermissionError)
    async def permission_error(request: Request, exc: PermissionError) -> JSONResponse:
        return problem(403, "Forbidden", str(exc), request.state.request_id)

    @app.exception_handler(ValueError)
    async def value_error(request: Request, exc: ValueError) -> JSONResponse:
        return problem(400, "Bad Request", str(exc), request.state.request_id)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        return problem(422, "Validation Error", "request fields failed validation", request.state.request_id)

    def get_session() -> Iterator[Session]:
        session = database.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def identity_for(request: Request):  # type: ignore[no-untyped-def]
        return verifier.verify(request.headers, request.client.host if request.client else "")

    def request_context(
        request: Request,
        session: Session = Depends(get_session),
        workspace: str | None = Header(default=None, alias="X-Workspace-ID"),
    ) -> RequestContext:
        return resolve_context(session, identity_for(request), workspace)

    def connector_context(
        authorization: str = Header(default="", alias="Authorization"),
        session: Session = Depends(get_session),
    ) -> Connector:
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token:
            raise PermissionError("connector bearer credential is required")
        return authenticate_connector(session, token.strip(), settings)

    def same_origin(request: Request) -> None:
        origin = request.headers.get("origin")
        if not origin:
            return
        parsed = urlparse(origin)
        if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != request.headers.get("host", "").lower():
            raise PermissionError("cross-origin control requests are forbidden")

    @app.get("/api/health")
    def health(session: Session = Depends(get_session)) -> dict[str, Any]:
        session.execute(text("SELECT 1"))
        return {
            "status": "ok",
            "service": "aegis-mission-control",
            "version": "2.0.0",
            "environment": settings.environment,
            "authMode": settings.auth_mode,
            "at": iso(utcnow()),
        }

    @app.get("/api/ready")
    def ready(session: Session = Depends(get_session)) -> dict[str, Any]:
        session.execute(text("SELECT 1"))
        writable = settings.evidence_root.exists() and settings.evidence_root.is_dir()
        if not writable:
            raise HTTPException(status_code=503, detail="evidence store unavailable")
        return {"status": "ready", "database": "ok", "evidenceStore": "ok"}

    @app.get("/api/v1/me")
    def me(ctx: RequestContext = Depends(request_context)) -> dict[str, Any]:
        return {
            "user": {"id": ctx.user.id, "email": ctx.user.email, "displayName": ctx.user.display_name},
            "workspace": {
                "id": ctx.organization.id,
                "slug": ctx.organization.slug,
                "name": ctx.organization.name,
            },
            "role": ctx.membership.role,
            "permissions": sorted(ROLE_PERMISSIONS[ctx.membership.role]),
        }

    @app.get("/api/v1/dashboard")
    def platform_dashboard(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        data = dashboard(session, ctx)
        data["securityCoverage"] = security_coverage(session, ctx)
        data["shadowAI"] = shadow_dashboard(session, ctx)
        return data

    @app.post("/api/v1/invitations", status_code=201)
    def invite(
        body: InvitationCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        row, token = create_invitation(
            session,
            ctx,
            email=body.email,
            role=body.role,
            expires_hours=body.expires_hours,
            settings=settings,
        )
        return {
            "invitation": {
                "id": row.id,
                "email": row.email,
                "role": row.role,
                "expiresAt": iso(row.expires_at),
            },
            "token": token,
            "warning": "This invitation token is shown once. Deliver it through an approved channel.",
        }

    @app.post("/api/v1/invitations/accept")
    def accept(
        body: InvitationAccept,
        request: Request,
        session: Session = Depends(get_session),
    ) -> dict[str, Any]:
        same_origin(request)
        ctx = accept_invitation(session, identity_for(request), body.token, settings)
        return {"accepted": True, "workspaceId": ctx.organization.id, "role": ctx.membership.role}

    @app.get("/api/v1/connectors")
    def list_connectors(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        rows = session.scalars(
            select(Connector).where(Connector.organization_id == ctx.organization.id).order_by(Connector.created_at.desc())
        )
        return {"connectors": [serialize_connector(row) for row in rows]}

    @app.post("/api/v1/connectors", status_code=201)
    def provision_connector(
        body: ConnectorCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        connector, token = create_connector(
            session,
            ctx,
            name=body.name,
            capabilities=body.capabilities,
            settings=settings,
        )
        return {
            "connector": serialize_connector(connector),
            "token": token,
            "warning": "This credential is shown once. Store it in the connector secret store.",
        }

    @app.delete("/api/v1/connectors/{connector_id}")
    def delete_connector(
        connector_id: str,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        return {"connector": serialize_connector(revoke_connector(session, ctx, connector_id))}

    @app.post("/api/v1/connector/heartbeat")
    def heartbeat(
        body: Heartbeat,
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        rows = connector_heartbeat(
            session,
            connector,
            version=body.version,
            capabilities=body.capabilities,
            agents=[item.model_dump(by_alias=False) for item in body.agents],
        )
        return {"accepted": True, "serverTime": iso(utcnow()), "agents": [serialize_agent(row) for row in rows]}

    @app.post("/api/v1/connector/events", status_code=202)
    def events(
        body: EventBatch,
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        rows = [item.model_dump(by_alias=False) for item in body.events]
        accepted_count, duplicate_count = ingest_events(session, connector, rows, settings)
        return {"accepted": accepted_count, "duplicates": duplicate_count}

    @app.post("/api/v1/connector/shadow-ai/assets", status_code=202)
    def discover_ai_assets(
        body: AIAssetBatch,
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        if "shadow_ai.assets" not in connector.capabilities:
            raise PermissionError("connector is not allowlisted for AI asset discovery")
        reports = [item.model_dump(by_alias=False) for item in body.assets]
        created, updated = ingest_assets(session, connector, reports, settings)
        return {"created": created, "updated": updated}

    @app.post("/api/v1/connector/shadow-ai/usage", status_code=202)
    def report_ai_usage(
        body: AIUsageBatch,
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        if "shadow_ai.usage" not in connector.capabilities:
            raise PermissionError("connector is not allowlisted for AI usage reporting")
        reports = [item.model_dump(by_alias=False) for item in body.usage]
        accepted, duplicates, violations = ingest_usage(session, connector, reports)
        return {"accepted": accepted, "duplicates": duplicates, "violations": violations}

    @app.get("/api/v1/tasks")
    def list_tasks(
        status: str | None = None,
        limit: int = 50,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "tasks.read")
        limit = max(1, min(limit, 200))
        statement = select(Task).where(Task.organization_id == ctx.organization.id)
        if status:
            statement = statement.where(Task.status == status)
        rows = session.scalars(statement.order_by(Task.created_at.desc()).limit(limit))
        return {"tasks": [serialize_task(row) for row in rows]}

    @app.post("/api/v1/tasks", status_code=201)
    def add_task(
        body: TaskCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        task = create_task(
            session,
            ctx,
            title=body.title,
            action=body.action,
            connector_id=body.connector_id,
            agent_id=body.agent_id,
            program_id=body.program_id,
            payload=body.payload,
            dry_run=body.dry_run,
        )
        return {"task": serialize_task(task)}

    @app.post("/api/v1/tasks/{task_id}/decision")
    def task_decision(
        task_id: str,
        body: ApprovalDecision,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        task, approval = decide_task(session, ctx, task_id, body.decision, body.note)
        if task.action == "assessment.execute":
            assessment = session.scalar(
                select(AssessmentRun).where(
                    AssessmentRun.task_id == task.id,
                    AssessmentRun.organization_id == ctx.organization.id,
                )
            )
            if assessment:
                assessment.status = "queued" if body.decision == "approved" else "rejected"
                if body.decision == "rejected":
                    engagement = session.get(Engagement, assessment.engagement_id)
                    if engagement:
                        engagement.status = "attention"
        return {"task": serialize_task(task), "approval": serialize_approval(approval)}

    @app.get("/api/v1/connector/tasks/lease")
    def task_lease(
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        leased = lease_task(session, connector, settings)
        if not leased:
            return {"task": None, "retryAfterSeconds": 15}
        task, lease_token = leased
        if task.action == "assessment.execute":
            assessment = session.scalar(
                select(AssessmentRun).where(
                    AssessmentRun.task_id == task.id,
                    AssessmentRun.organization_id == connector.organization_id,
                )
            )
            if assessment:
                assessment.status = "running"
                assessment.started_at = utcnow()
                engagement = session.get(Engagement, assessment.engagement_id)
                if engagement:
                    engagement.status = "running"
        return {"task": serialize_task(task), "leaseToken": lease_token, "leaseSeconds": settings.lease_seconds}

    @app.post("/api/v1/connector/tasks/{task_id}/complete")
    def task_complete(
        task_id: str,
        body: TaskComplete,
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> dict[str, Any]:
        task = complete_task(
            session,
            connector,
            task_id,
            lease_token=body.lease_token,
            status=body.status,
            result=body.result,
            error=body.error,
            settings=settings,
        )
        sync_assessment_result(session, task)
        sync_asset_analysis_result(session, task)
        return {"task": serialize_task(task)}

    @app.get("/api/v1/connector/tasks/{task_id}/evidence")
    def connector_task_evidence(
        task_id: str,
        task_lease: str = Header(default="", alias="X-Task-Lease"),
        session: Session = Depends(get_session),
        connector: Connector = Depends(connector_context),
    ) -> Response:
        task = session.scalar(
            select(Task).where(
                Task.id == task_id,
                Task.organization_id == connector.organization_id,
                Task.connector_id == connector.id,
                Task.action == "evidence.analyze",
                Task.status == "running",
            )
        )
        if not task or not task.lease_token_hash or not task_lease:
            raise PermissionError("an active evidence-analysis task lease is required")
        if not secret_matches(task_lease, task.lease_token_hash, settings.token_pepper):
            raise PermissionError("task lease token is invalid")
        locked_until = task.locked_until
        if locked_until and locked_until.tzinfo is None:
            locked_until = locked_until.replace(tzinfo=timezone.utc)
        if not locked_until or locked_until <= utcnow():
            raise PermissionError("task lease expired and failed closed")
        evidence_id = str(task.payload.get("evidenceId", ""))
        asset_id = str(task.payload.get("assetId", ""))
        row = session.scalar(
            select(Evidence)
            .join(EngagementAsset, EngagementAsset.evidence_id == Evidence.id)
            .where(
                Evidence.id == evidence_id,
                Evidence.organization_id == connector.organization_id,
                Evidence.scan_status == "clean",
                EngagementAsset.id == asset_id,
                EngagementAsset.organization_id == connector.organization_id,
            )
        )
        if not row:
            raise PermissionError("leased evidence is unavailable or not clean")
        append_audit(
            session,
            connector.organization_id,
            actor=f"connector:{connector.id}",
            action="engagement.asset.analysis.read",
            target_type="evidence",
            target_id=row.id,
            detail={"engagement_id": task.payload.get("engagementId"), "task_id": task.id, "sha256": row.sha256},
        )
        return Response(
            content=evidence_store.get(connector.organization_id, row.storage_key),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
        )

    @app.get("/api/v1/approvals")
    def list_approvals(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "tasks.read")
        rows = session.scalars(
            select(Approval).where(Approval.organization_id == ctx.organization.id).order_by(Approval.created_at.desc()).limit(100)
        )
        return {"approvals": [serialize_approval(row) for row in rows]}

    @app.get("/api/v1/engagements")
    def engagement_register(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "engagements.read")
        return {"engagements": list_engagements(session, ctx.organization.id)}

    @app.post("/api/v1/engagements", status_code=201)
    def create_engagement(
        body: EngagementCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "engagements.manage")
        expires_at = body.authorization_expires_at
        if expires_at:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            if expires_at <= utcnow():
                raise ValueError("authorization expiry must be in the future")
        row = Engagement(
            organization_id=ctx.organization.id,
            created_by_user_id=ctx.user.id,
            name=body.name.strip(),
            client_name=(body.client_name or "").strip() or None,
            engagement_type=body.engagement_type,
            status="ready",
            objective=body.objective.strip(),
            scope_rules=body.scope_rules.strip(),
            authorization_basis=body.authorization_basis,
            authorization_attestation=body.authorization_attestation.strip(),
            authorization_confirmed=True,
            authorized_at=utcnow(),
            authorization_expires_at=expires_at,
            selected_teams=body.selected_teams,
        )
        session.add(row)
        session.flush()
        for target in body.targets:
            session.add(
                EngagementTarget(
                    organization_id=ctx.organization.id,
                    engagement_id=row.id,
                    kind=target.kind,
                    display_name=target.display_name.strip(),
                    locator=normalize_target(target.kind, target.locator),
                    environment=target.environment,
                    scope_status="in-scope",
                    notes=target.notes.strip(),
                )
            )
        session.flush()
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="engagement.created",
            target_type="engagement",
            target_id=row.id,
            detail={
                "engagement_id": row.id,
                "type": row.engagement_type,
                "authorization_basis": row.authorization_basis,
                "target_count": len(body.targets),
                "teams": row.selected_teams,
            },
        )
        return {"engagement": serialize_engagement(session, row)}

    @app.get("/api/v1/engagements/{engagement_id}")
    def engagement_detail(
        engagement_id: str,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "engagements.read")
        row = session.scalar(
            select(Engagement).where(
                Engagement.id == engagement_id,
                Engagement.organization_id == ctx.organization.id,
            )
        )
        if not row:
            raise ValueError("engagement not found")
        return {"engagement": serialize_engagement(session, row)}

    @app.post("/api/v1/engagements/{engagement_id}/launch", status_code=202)
    def launch_engagement(
        engagement_id: str,
        body: EngagementLaunch,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "engagements.manage")
        engagement = session.scalar(
            select(Engagement).where(
                Engagement.id == engagement_id,
                Engagement.organization_id == ctx.organization.id,
            ).with_for_update()
        )
        if not engagement:
            raise ValueError("engagement not found")
        if not engagement.authorization_confirmed or not engagement.authorized_at:
            raise PermissionError("the engagement has no recorded authorization")
        expires_at = engagement.authorization_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at <= utcnow():
            raise PermissionError("the recorded authorization has expired")
        targets = list(
            session.scalars(
                select(EngagementTarget).where(
                    EngagementTarget.engagement_id == engagement.id,
                    EngagementTarget.organization_id == ctx.organization.id,
                    EngagementTarget.scope_status == "in-scope",
                )
            )
        )
        if not targets:
            raise ValueError("at least one in-scope target is required")
        baseline = None
        if body.baseline_run_id:
            baseline = session.scalar(
                select(AssessmentRun).where(
                    AssessmentRun.id == body.baseline_run_id,
                    AssessmentRun.engagement_id == engagement.id,
                    AssessmentRun.organization_id == ctx.organization.id,
                )
            )
            if not baseline:
                raise ValueError("baseline run does not belong to this engagement")
        connectors = list(
            session.scalars(
                select(Connector).where(
                    Connector.organization_id == ctx.organization.id,
                    Connector.revoked_at.is_(None),
                ).order_by(Connector.last_seen_at.desc().nullslast(), Connector.created_at)
            )
        )
        connector = next(
            (
                item
                for item in connectors
                if "assessment.execute" in item.capabilities
                and (body.connector_id is None or item.id == body.connector_id)
            ),
            None,
        )
        if not connector:
            raise ValueError("no connector is allowlisted for assessment.execute; provision an assessment executor first")
        sequence = int(
            session.scalar(
                select(func.count()).select_from(AssessmentRun).where(
                    AssessmentRun.engagement_id == engagement.id,
                    AssessmentRun.organization_id == ctx.organization.id,
                )
            )
            or 0
        ) + 1
        plan = build_team_plan(engagement.selected_teams, targets)
        run = AssessmentRun(
            organization_id=ctx.organization.id,
            engagement_id=engagement.id,
            sequence=sequence,
            mode=body.mode,
            status="awaiting_approval",
            connector_id=connector.id,
            baseline_run_id=baseline.id if baseline else None,
            team_plan=plan,
        )
        session.add(run)
        session.flush()
        program_id = session.scalar(
            select(Program.id).where(Program.organization_id == ctx.organization.id).order_by(Program.created_at).limit(1)
        )
        task = create_task(
            session,
            ctx,
            title=f"{engagement.name} · assessment {sequence}",
            action="assessment.execute",
            connector_id=connector.id,
            agent_id=None,
            program_id=program_id,
            payload={
                "engagementId": engagement.id,
                "assessmentRunId": run.id,
                "mode": body.mode,
                "objective": engagement.objective,
                "scopeRules": engagement.scope_rules,
                "authorization": {
                    "basis": engagement.authorization_basis,
                    "authorizedAt": iso(engagement.authorized_at),
                    "expiresAt": iso(engagement.authorization_expires_at),
                },
                "targets": [
                    {"id": target.id, "kind": target.kind, "locator": target.locator, "environment": target.environment}
                    for target in targets
                ],
                "teamPlan": plan,
            },
            dry_run=False,
        )
        run.task_id = task.id
        engagement.status = "scheduled"
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="engagement.assessment.requested",
            target_type="engagement",
            target_id=engagement.id,
            detail={"engagement_id": engagement.id, "run_id": run.id, "task_id": task.id, "mode": body.mode},
        )
        return {"engagement": serialize_engagement(session, engagement), "task": serialize_task(task)}

    @app.get("/api/v1/engagements/{engagement_id}/compare")
    def compare_engagement_runs(
        engagement_id: str,
        baseline_run_id: str = Query(alias="baselineRunId"),
        current_run_id: str = Query(alias="currentRunId"),
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "engagements.read")
        return compare_runs(session, ctx.organization.id, engagement_id, baseline_run_id, current_run_id)

    @app.get("/api/v1/engagements/{engagement_id}/export")
    def export_engagement(
        engagement_id: str,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> Response:
        require_permission(ctx.membership.role, "engagements.export")
        relevant_audit = [
            item
            for item in recent_audit(session, ctx.organization.id, 500)
            if item.get("targetId") == engagement_id or item.get("detail", {}).get("engagement_id") == engagement_id
        ]
        payload = export_engagement_zip(session, ctx.organization.id, engagement_id, relevant_audit)
        return Response(
            content=payload,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="aegis-engagement-{engagement_id[:8]}.zip"'},
        )

    @app.post("/api/v1/engagements/{engagement_id}/assets/{asset_id}/analyze", status_code=202)
    def analyze_engagement_asset(
        engagement_id: str,
        asset_id: str,
        body: EngagementAssetAnalyze,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "engagements.manage")
        asset, evidence = session.execute(
            select(EngagementAsset, Evidence)
            .join(Evidence, Evidence.id == EngagementAsset.evidence_id)
            .where(
                EngagementAsset.id == asset_id,
                EngagementAsset.engagement_id == engagement_id,
                EngagementAsset.organization_id == ctx.organization.id,
                Evidence.organization_id == ctx.organization.id,
            )
        ).one_or_none() or (None, None)
        if not asset or not evidence:
            raise ValueError("engagement asset not found")
        if evidence.scan_status != "clean":
            raise PermissionError("the asset must pass malware/content scanning before analysis")
        connectors = list(
            session.scalars(
                select(Connector).where(
                    Connector.organization_id == ctx.organization.id,
                    Connector.revoked_at.is_(None),
                ).order_by(Connector.last_seen_at.desc().nullslast(), Connector.created_at)
            )
        )
        connector = next(
            (
                item for item in connectors
                if "evidence.analyze" in item.capabilities
                and (body.connector_id is None or item.id == body.connector_id)
            ),
            None,
        )
        if not connector:
            raise ValueError("no connector is allowlisted for evidence.analyze")
        program_id = session.scalar(
            select(Program.id).where(Program.organization_id == ctx.organization.id).order_by(Program.created_at).limit(1)
        )
        task = create_task(
            session,
            ctx,
            title=f"Analyze {evidence.filename}",
            action="evidence.analyze",
            connector_id=connector.id,
            agent_id=None,
            program_id=program_id,
            payload={
                "engagementId": engagement_id,
                "assetId": asset.id,
                "evidenceId": evidence.id,
                "filename": evidence.filename,
                "contentType": evidence.content_type,
                "mediaKind": asset.media_kind,
                "sha256": evidence.sha256,
            },
            dry_run=False,
        )
        asset.analysis_status = "queued"
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="engagement.asset.analysis.queued",
            target_type="engagement_asset",
            target_id=asset.id,
            detail={"engagement_id": engagement_id, "task_id": task.id, "evidence_id": evidence.id},
        )
        return {"task": serialize_task(task), "assetId": asset.id, "analysisStatus": asset.analysis_status}

    @app.post("/api/v1/evidence", status_code=201)
    async def upload_evidence(
        request: Request,
        file: UploadFile = File(...),
        task_id: str | None = Form(default=None, alias="taskId"),
        engagement_id: str | None = Form(default=None, alias="engagementId"),
        assessment_run_id: str | None = Form(default=None, alias="assessmentRunId"),
        classification: str = Form(default="customer-confidential"),
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        engagement = None
        assessment_run = None
        if engagement_id:
            engagement = session.scalar(
                select(Engagement).where(
                    Engagement.id == engagement_id,
                    Engagement.organization_id == ctx.organization.id,
                )
            )
            if not engagement:
                raise ValueError("engagement not found")
        if assessment_run_id:
            if not engagement:
                raise ValueError("assessmentRunId requires engagementId")
            assessment_run = session.scalar(
                select(AssessmentRun).where(
                    AssessmentRun.id == assessment_run_id,
                    AssessmentRun.engagement_id == engagement.id,
                    AssessmentRun.organization_id == ctx.organization.id,
                )
            )
            if not assessment_run:
                raise ValueError("assessment run does not belong to this engagement")
        content = await file.read(settings.max_evidence_bytes + 1)
        content_type = (file.content_type or "application/octet-stream").lower().split(";", 1)[0].strip()
        row = create_evidence(
            session,
            ctx,
            evidence_store,
            filename=file.filename or "evidence.bin",
            content_type=content_type,
            content=content,
            task_id=task_id,
            classification=classification[:48],
        )
        asset = None
        if engagement:
            kind = media_kind(row.content_type, row.filename)
            asset = EngagementAsset(
                organization_id=ctx.organization.id,
                engagement_id=engagement.id,
                assessment_run_id=assessment_run.id if assessment_run else None,
                evidence_id=row.id,
                media_kind=kind,
                analysis_status="quarantined",
                suggestions=asset_suggestions(kind),
            )
            session.add(asset)
            session.flush()
            append_audit(
                session,
                ctx.organization.id,
                actor=ctx.actor,
                action="engagement.asset.attached",
                target_type="engagement_asset",
                target_id=asset.id,
                detail={"engagement_id": engagement.id, "evidence_id": row.id, "media_kind": kind},
            )
        return {
            "evidence": {
                "id": row.id,
                "filename": row.filename,
                "contentType": row.content_type,
                "sha256": row.sha256,
                "sizeBytes": row.size_bytes,
                "scanStatus": row.scan_status,
                "legalHold": row.legal_hold,
                "retentionUntil": iso(row.retention_until),
                "createdAt": iso(row.created_at),
            },
            "asset": {
                "id": asset.id,
                "engagementId": asset.engagement_id,
                "mediaKind": asset.media_kind,
                "analysisStatus": asset.analysis_status,
                "suggestions": asset.suggestions,
            } if asset else None,
        }

    @app.get("/api/v1/evidence")
    def list_evidence(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "evidence.read")
        rows = session.scalars(
            select(Evidence).where(Evidence.organization_id == ctx.organization.id).order_by(Evidence.created_at.desc()).limit(200)
        )
        return {
            "evidence": [
                {
                    "id": row.id,
                    "taskId": row.task_id,
                    "filename": row.filename,
                    "contentType": row.content_type,
                    "sha256": row.sha256,
                    "sizeBytes": row.size_bytes,
                    "classification": row.classification,
                    "scanStatus": row.scan_status,
                    "legalHold": row.legal_hold,
                    "retentionUntil": iso(row.retention_until),
                    "createdAt": iso(row.created_at),
                }
                for row in rows
            ]
        }

    @app.post("/api/v1/evidence/{evidence_id}/scan")
    def record_scan(
        evidence_id: str,
        body: EvidenceScanUpdate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "evidence.write")
        row = session.scalar(
            select(Evidence).where(Evidence.id == evidence_id, Evidence.organization_id == ctx.organization.id)
        )
        if not row:
            raise ValueError("evidence not found")
        row.scan_status = body.status
        asset = session.scalar(
            select(EngagementAsset).where(
                EngagementAsset.evidence_id == row.id,
                EngagementAsset.organization_id == ctx.organization.id,
            )
        )
        if asset:
            asset.analysis_status = "ready" if body.status == "clean" else "rejected"
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action=f"evidence.scan.{body.status}",
            target_type="evidence",
            target_id=row.id,
            detail={"note": body.note, "sha256": row.sha256},
        )
        return {"id": row.id, "scanStatus": row.scan_status}

    @app.get("/api/v1/evidence/{evidence_id}/download")
    def download_evidence(
        evidence_id: str,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> Response:
        require_permission(ctx.membership.role, "evidence.read")
        row = session.scalar(
            select(Evidence).where(Evidence.id == evidence_id, Evidence.organization_id == ctx.organization.id)
        )
        if not row:
            raise ValueError("evidence not found")
        if row.scan_status != "clean":
            raise PermissionError("evidence remains quarantined until it passes malware/content scanning")
        return Response(
            content=evidence_store.get(ctx.organization.id, row.storage_key),
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{row.filename}"'},
        )

    @app.get("/api/v1/findings")
    def list_findings(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        rows = session.scalars(
            select(Finding).where(Finding.organization_id == ctx.organization.id).order_by(Finding.created_at.desc()).limit(200)
        )
        return {
            "findings": [
                {
                    "id": row.id,
                    "engagementId": row.engagement_id,
                    "assessmentRunId": row.assessment_run_id,
                    "fingerprint": row.fingerprint,
                    "ownerTeam": row.owner_team,
                    "title": row.title,
                    "description": row.description,
                    "severity": row.severity,
                    "status": row.status,
                    "ownerUserId": row.owner_user_id,
                    "dueAt": iso(row.due_at),
                    "createdAt": iso(row.created_at),
                }
                for row in rows
            ]
        }

    @app.post("/api/v1/findings", status_code=201)
    def add_finding(
        body: FindingCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "findings.write")
        engagement = None
        assessment_run = None
        if body.engagement_id:
            engagement = session.scalar(
                select(Engagement).where(
                    Engagement.id == body.engagement_id,
                    Engagement.organization_id == ctx.organization.id,
                )
            )
            if not engagement:
                raise ValueError("engagement not found")
        if body.assessment_run_id:
            if not engagement:
                raise ValueError("assessmentRunId requires engagementId")
            assessment_run = session.scalar(
                select(AssessmentRun).where(
                    AssessmentRun.id == body.assessment_run_id,
                    AssessmentRun.engagement_id == engagement.id,
                    AssessmentRun.organization_id == ctx.organization.id,
                )
            )
            if not assessment_run:
                raise ValueError("assessment run does not belong to this engagement")
        row = Finding(
            organization_id=ctx.organization.id,
            program_id=body.program_id,
            engagement_id=engagement.id if engagement else None,
            assessment_run_id=assessment_run.id if assessment_run else None,
            fingerprint=body.fingerprint,
            owner_team=body.owner_team,
            title=body.title,
            description=body.description,
            severity=body.severity,
            owner_user_id=body.owner_user_id,
            due_at=body.due_at,
        )
        session.add(row)
        session.flush()
        append_audit(session, ctx.organization.id, actor=ctx.actor, action="finding.created", target_type="finding", target_id=row.id, detail={"severity": row.severity, "engagement_id": row.engagement_id, "run_id": row.assessment_run_id})
        return {"finding": {"id": row.id, "title": row.title, "severity": row.severity, "status": row.status}}

    @app.get("/api/v1/incidents")
    def list_incidents(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        rows = session.scalars(
            select(Incident).where(Incident.organization_id == ctx.organization.id).order_by(Incident.opened_at.desc()).limit(200)
        )
        return {
            "incidents": [
                {"id": row.id, "title": row.title, "severity": row.severity, "status": row.status, "summary": row.summary, "openedAt": iso(row.opened_at), "resolvedAt": iso(row.resolved_at)}
                for row in rows
            ]
        }

    @app.post("/api/v1/incidents", status_code=201)
    def add_incident(
        body: IncidentCreate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "incidents.write")
        row = Incident(
            organization_id=ctx.organization.id,
            title=body.title,
            severity=body.severity,
            summary=body.summary,
            commander_user_id=ctx.user.id,
        )
        session.add(row)
        session.flush()
        append_audit(session, ctx.organization.id, actor=ctx.actor, action="incident.created", target_type="incident", target_id=row.id, detail={"severity": row.severity})
        return {"incident": {"id": row.id, "title": row.title, "severity": row.severity, "status": row.status}}

    @app.get("/api/v1/retention")
    def get_retention(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        row = session.get(RetentionPolicy, ctx.organization.id)
        if not row:
            raise ValueError("retention policy not found")
        return {"telemetryDays": row.telemetry_days, "taskDays": row.task_days, "evidenceDays": row.evidence_days, "auditDays": row.audit_days, "legalHoldDefault": row.legal_hold_default}

    @app.put("/api/v1/retention")
    def set_retention(
        body: RetentionUpdate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "retention.manage")
        row = session.get(RetentionPolicy, ctx.organization.id)
        if not row:
            raise ValueError("retention policy not found")
        before = {"telemetry": row.telemetry_days, "tasks": row.task_days, "evidence": row.evidence_days, "audit": row.audit_days, "hold": row.legal_hold_default}
        row.telemetry_days = body.telemetry_days
        row.task_days = body.task_days
        row.evidence_days = body.evidence_days
        row.audit_days = body.audit_days
        row.legal_hold_default = body.legal_hold_default
        append_audit(session, ctx.organization.id, actor=ctx.actor, action="retention.updated", target_type="retention_policy", target_id=ctx.organization.id, detail={"before": before, "after": body.model_dump()})
        return body.model_dump(by_alias=True)

    @app.post("/api/v1/retention/sweep")
    def sweep_retention(
        body: RetentionSweepRequest,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        return retention_sweep(session, ctx, evidence_store, confirmation=body.confirmation)

    @app.post("/api/v1/safety")
    def change_safety(
        body: SafetyChange,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        row = update_safety(session, ctx, level=body.level, reason=body.reason)
        return {"safetyLevel": row.safety_level, "killSwitchActive": row.kill_switch_active}

    @app.get("/api/v1/security-coverage")
    def get_security_coverage(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        return security_coverage(session, ctx)

    @app.put("/api/v1/security-coverage/{control_id}")
    def update_security_control(
        control_id: str,
        body: SecurityControlUpdate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "controls.manage")
        row = session.scalar(
            select(SecurityControl).where(
                SecurityControl.id == control_id,
                SecurityControl.organization_id == ctx.organization.id,
            )
        )
        if not row:
            raise ValueError("security control not found")
        current = security_coverage(session, ctx)
        current_row = next(item for item in current["controls"] if item["id"] == row.id)
        if body.status == "verified" and current_row["status"] == "telemetry-gap":
            raise ValueError(f"control cannot be verified until {row.required_source} telemetry is connected")
        before = {
            "enabled": row.enabled,
            "ownerTeam": row.owner_team,
            "status": row.status,
            "configuration": row.configuration,
        }
        row.enabled = body.enabled
        row.owner_team = body.owner_team
        row.status = body.status
        row.configuration = scrub(body.configuration)
        row.updated_by_user_id = ctx.user.id
        row.updated_at = utcnow()
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="security_control.updated",
            target_type="security_control",
            target_id=row.id,
            detail={
                "before": before,
                "after": body.model_dump(by_alias=True),
                "reason": body.reason,
            },
        )
        session.flush()
        return {"control": next(item for item in security_coverage(session, ctx)["controls"] if item["id"] == row.id)}

    @app.get("/api/v1/shadow-ai")
    def shadow_ai_posture(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        return shadow_dashboard(session, ctx)

    @app.put("/api/v1/shadow-ai/policy")
    def update_shadow_ai_policy(
        body: AIPolicyUpdate,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "shadow_ai.manage")
        if body.retain_prompt_content:
            raise ValueError("raw AI prompt retention is disabled by the platform privacy boundary")

        approved_domains = sorted({normalize_domain(item) for item in body.approved_domains})
        blocked_domains = sorted({normalize_domain(item) for item in body.blocked_domains})
        if "" in approved_domains or "" in blocked_domains:
            raise ValueError("AI policy contains an invalid domain")
        overlap = set(approved_domains) & set(blocked_domains)
        if overlap:
            raise ValueError("a domain cannot be both approved and blocked")

        row = policy_for(session, ctx.organization.id)
        before = {
            "defaultDisposition": row.default_disposition,
            "sensitiveDataDisposition": row.sensitive_data_disposition,
            "approvedVendors": row.approved_vendors,
            "approvedDomains": row.approved_domains,
            "blockedDomains": row.blocked_domains,
            "prohibitedDataLabels": row.prohibited_data_labels,
        }
        row.default_disposition = body.default_disposition
        row.sensitive_data_disposition = body.sensitive_data_disposition
        row.approved_vendors = sorted({item.strip()[:100] for item in body.approved_vendors if item.strip()})
        row.approved_domains = approved_domains
        row.blocked_domains = blocked_domains
        row.prohibited_data_labels = sorted({item.strip().lower()[:80] for item in body.prohibited_data_labels if item.strip()})
        row.retain_prompt_content = False
        row.updated_by_user_id = ctx.user.id
        row.updated_at = utcnow()
        session.flush()
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="shadow_ai.policy_updated",
            target_type="ai_policy",
            target_id=ctx.organization.id,
            detail={"before": before, "after": body.model_dump(by_alias=True) | {"retainPromptContent": False}},
        )
        return shadow_dashboard(session, ctx)["policy"]

    @app.post("/api/v1/shadow-ai/assets/{asset_id}/decision")
    def decide_ai_asset(
        asset_id: str,
        body: AIAssetDecision,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "shadow_ai.manage")
        row = session.scalar(
            select(AIAsset).where(
                AIAsset.id == asset_id,
                AIAsset.organization_id == ctx.organization.id,
            )
        )
        if not row:
            raise ValueError("AI asset not found")
        before = row.disposition
        row.disposition = body.disposition
        row.owner_user_id = ctx.user.id
        row.risk_score = {"approved": 20, "restricted": 65, "blocked": 95}[body.disposition]
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="shadow_ai.asset_decided",
            target_type="ai_asset",
            target_id=row.id,
            detail={"before": before, "after": body.disposition, "reason": body.reason},
        )
        return {
            "asset": serialize_asset(row),
            "enforcement": "policy-only" if body.disposition == "blocked" else "not-required",
            "note": "Network or endpoint blocking requires an approved shadow_ai.block task.",
        }

    @app.post("/api/v1/shadow-ai/violations/{violation_id}/decision")
    def decide_ai_violation(
        violation_id: str,
        body: ViolationDecision,
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        require_permission(ctx.membership.role, "shadow_ai.manage")
        row = session.scalar(
            select(PolicyViolation).where(
                PolicyViolation.id == violation_id,
                PolicyViolation.organization_id == ctx.organization.id,
            )
        )
        if not row:
            raise ValueError("policy violation not found")
        before = row.status
        row.status = body.status
        row.resolved_at = utcnow() if body.status in {"resolved", "false-positive"} else None
        append_audit(
            session,
            ctx.organization.id,
            actor=ctx.actor,
            action="shadow_ai.violation_decided",
            target_type="policy_violation",
            target_id=row.id,
            detail={"before": before, "after": body.status, "note": body.note},
        )
        return {"violation": serialize_violation(row)}

    @app.get("/api/v1/audit")
    def audit_log(
        limit: int = 100,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "audit.read")
        return {"events": recent_audit(session, ctx.organization.id, max(1, min(limit, 500))), "ledger": verify_audit(session, ctx.organization.id)}

    @app.get("/api/v1/export")
    def export_workspace(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "audit.read")
        data = dashboard(session, ctx)
        data["exportedAt"] = iso(utcnow())
        data["audit"] = recent_audit(session, ctx.organization.id, 500)
        data["evidence"] = list_evidence(session=session, ctx=ctx)["evidence"]
        data["findings"] = list_findings(session=session, ctx=ctx)["findings"]
        data["incidents"] = list_incidents(session=session, ctx=ctx)["incidents"]
        data["shadowAI"] = shadow_dashboard(session, ctx)
        data["securityCoverage"] = security_coverage(session, ctx)
        return data

    def compatibility_snapshot(session: Session, ctx: RequestContext) -> dict[str, Any]:
        platform = dashboard(session, ctx)
        platform["shadowAI"] = shadow_dashboard(session, ctx)
        platform["securityCoverage"] = security_coverage(session, ctx)
        program = session.scalar(
            select(Program).where(Program.organization_id == ctx.organization.id).order_by(Program.created_at).limit(1)
        )
        ledger = platform["ledger"]
        readiness = [
            ("identity_boundary", "Identity Boundary", True, "Workspace owner"),
            ("connector_online", "Connector Online", any(row["status"] == "online" for row in platform["connectors"]), "Platform operator"),
            ("retention_policy", "Retention Policy", bool(platform["retention"]), "Data owner"),
            ("audit_chain", "Audit Chain", bool(ledger["ok"]), "Independent auditor"),
        ]
        gates = [
            {"id": item_id, "label": label, "status": "VERIFIED" if ok else "PENDING", "owner": owner, "closureItem": index + 1, "verification": [f"{label} is independently observable"], "evidence": []}
            for index, (item_id, label, ok, owner) in enumerate(readiness)
        ]
        latest_by_action = {row["action"]: row for row in reversed(platform["tasks"])}
        status_map = {"succeeded": "passed", "awaiting_approval": "queued", "rejected": "failed", "blocked": "failed"}
        gate_rows = []
        for action, policy in ACTION_CATALOG.items():
            task = latest_by_action.get(action)
            gate_rows.append({"id": action, "name": action.replace(".", " ").title(), "kind": policy.risk, "status": status_map.get(task["status"], task["status"]) if task else "not_run", "lastRunId": task["id"] if task else None, "elapsedSeconds": None})
        teams = [
            {"id": team_id, "name": values[0], "color": values[1], "verb": values[2], "purpose": values[3], "status": "not_run", "lastRunId": None, "passThreshold": 0.8, "programWeight": round(1 / 7, 4), "test": "Customer-defined evidence-backed control contract", "automaticFailures": ["Unapproved high-risk execution", "Evidence integrity failure"], "components": {"T": {"name": "trust evidence", "weight": 1.0}}}
            for team_id, values in TEAM_DEFAULTS.items()
        ]
        run_rows = [
            {"id": row["id"], "gateId": row["action"], "gateName": row["title"], "mode": "engineering", "status": status_map.get(row["status"], row["status"]), "requestedAt": row["createdAt"], "startedAt": None, "finishedAt": row["completedAt"], "returnCode": 0 if row["status"] == "succeeded" else (1 if row["status"] == "failed" else None), "output": str(row["result"] or row["error"] or "Task recorded in the durable command queue."), "elapsedSeconds": None}
            for row in platform["tasks"][:12]
        ]
        return {
            "generatedAt": iso(utcnow()),
            "deployment": {"mode": "saas", "controlsEnabled": ctx.membership.role in {"owner", "admin", "operator"}, "streamingEnabled": False, "authentication": "cloudflare-access" if settings.auth_mode == "cloudflare" else "development", "dataClass": "tenant-isolated-durable-operational-data"},
            "program": {"name": program.name if program else "AEGIS Security Program", "documentVersion": "2.0", "verified": sum(1 for gate in gates if gate["status"] == "VERIFIED"), "total": len(gates), "gates": gates, "currentState": "OPERATIONAL" if all(gate["status"] == "VERIFIED" for gate in gates) else "CUSTOMER_ONBOARDING", "rationale": "State is derived from identity, connector, retention, and audit evidence.", "states": ["CUSTOMER_ONBOARDING", "CONNECTED", "OPERATIONAL", "EVIDENCE_VERIFIED"], "marking": program.marking if program else "CUSTOMER_CONFIDENTIAL", "allowExercise": True, "allowDiagnosticScore": True, "allowAssuranceStatement": bool(ledger["ok"])},
            "repo": {"branch": ctx.organization.slug, "commit": ctx.organization.plan.upper(), "committedAt": iso(ctx.organization.updated_at), "subject": "Standalone tenant workspace", "dirty": False, "changedCount": 0, "changes": []},
            "gates": {"engineering": gate_rows, "engineeringCount": len(gate_rows), "assurance": [{"id": "audit.verify", "name": "Verify tenant audit ledger", "kind": "assurance"}]},
            "teams": teams,
            "agents": {"online": any(row["status"] == "online" for row in platform["connectors"]), "activeCount": len([row for row in platform["agents"] if row["status"] in {"online", "working", "active"}]), "blockedCount": len([row for row in platform["tasks"] if row["status"] == "blocked"]), "securityTeamCount": len(platform["agents"]), "sessions": [{"agent": row["name"], "sessionId": row["externalId"], "status": row["status"], "task": row["kind"], "reason": "Tenant connector telemetry", "nextAction": "", "eventTime": row["lastSeenAt"]} for row in platform["agents"][:8]], "collisions": [], "ledger": ledger},
            "runs": run_rows,
            "activity": recent_audit(session, ctx.organization.id, 16),
            "controlLedger": ledger,
            "platform": platform,
        }

    @app.get("/api/snapshot")
    def snapshot(
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        require_permission(ctx.membership.role, "workspace.read")
        return compatibility_snapshot(session, ctx)

    @app.post("/api/runs", status_code=202)
    def compatibility_run(
        body: dict[str, Any],
        request: Request,
        session: Session = Depends(get_session),
        ctx: RequestContext = Depends(request_context),
    ) -> dict[str, Any]:
        same_origin(request)
        gate_id = str(body.get("gateId", ""))[:80]
        connector_id = session.scalar(
            select(Connector.id).where(
                Connector.organization_id == ctx.organization.id,
                Connector.revoked_at.is_(None),
            ).order_by(Connector.created_at).limit(1)
        )
        task = create_task(session, ctx, title=f"Run {gate_id}", action="gate.run", connector_id=connector_id, agent_id=None, program_id=None, payload={"gateId": gate_id, "mode": str(body.get("mode", "engineering"))[:24]}, dry_run=False)
        return {"run": {"id": task.id, "gateId": gate_id, "gateName": task.title, "mode": "engineering", "status": "queued", "requestedAt": iso(task.created_at), "startedAt": None, "finishedAt": None, "returnCode": None, "output": "Task captured. High-risk execution awaits approval.", "elapsedSeconds": None}}

    dist = PLATFORM_ROOT / "web" / "dist"
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")

    return app
