from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import timezone
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .models import (
    AssessmentRun,
    Engagement,
    EngagementAsset,
    EngagementTarget,
    Evidence,
    Finding,
    Task,
    utcnow,
)
from .security import scrub
from .service import iso


TEAM_PLAYBOOKS: dict[str, dict[str, Any]] = {
    "purple": {
        "verb": "Validate",
        "checks": ["Correlate cross-team findings", "Replay fixes", "Measure detection and prevention together"],
    },
    "white": {
        "verb": "Authorize",
        "checks": ["Verify written authority and scope", "Enforce stop conditions", "Review evidence and claims independently"],
    },
    "yellow": {
        "verb": "Build",
        "checks": ["Review source and configuration", "Scan dependencies and secrets", "Produce fix-ready engineering guidance"],
    },
    "green": {
        "verb": "Engineer",
        "checks": ["Map trust boundaries and attack paths", "Review defensive architecture", "Identify missing telemetry"],
    },
    "orange": {
        "verb": "Anticipate",
        "checks": ["Model misuse and business-logic abuse", "Review privacy and human harms", "Challenge launch assumptions"],
    },
    "blue": {
        "verb": "Defend",
        "checks": ["Review exposure and hardening", "Validate logging and alerting", "Prepare response and recovery actions"],
    },
    "red": {
        "verb": "Prove",
        "checks": ["Run only authorized target tests", "Validate access-control and API boundaries", "Capture reproducible proof without destructive impact"],
    },
}


def normalize_target(kind: str, raw_locator: str) -> str:
    locator = raw_locator.replace("\x00", "").strip()
    if not locator:
        raise ValueError("target locator is required")
    if kind in {"website", "api"}:
        parsed = urlsplit(locator)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("website and API targets require a complete http or https URL")
        if parsed.username or parsed.password:
            raise ValueError("target URLs must not contain embedded credentials")
        locator = urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), parsed.path or "/", "", ""))
    elif kind == "repository" and "://" in locator:
        parsed = urlsplit(locator)
        if parsed.scheme not in {"https", "ssh"} or not parsed.hostname:
            raise ValueError("repository targets require an https or ssh URL")
        if parsed.password:
            raise ValueError("repository URLs must not contain embedded credentials")
    return locator[:2000]


def media_kind(content_type: str, filename: str) -> str:
    major = content_type.split("/", 1)[0].lower()
    if major in {"image", "audio", "video", "text"}:
        return major
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix in {"doc", "docx", "pdf", "rtf", "odt", "ppt", "pptx", "odp", "xls", "xlsx", "ods"}:
        return "document"
    if suffix in {"zip", "7z", "rar", "tar", "gz"}:
        return "archive"
    if suffix in {"json", "yaml", "yml", "xml", "csv"}:
        return "structured-data"
    return "binary"


def asset_suggestions(kind: str) -> list[dict[str, str]]:
    shared = {"team": "white", "title": "Preserve provenance", "detail": "Keep the encrypted original, hash, classification, retention, and scan state attached to this engagement."}
    suggestions: dict[str, list[dict[str, str]]] = {
        "image": [
            {"team": "orange", "title": "Review exposed interface states", "detail": "Inspect screenshots for unsafe defaults, privacy leaks, misleading trust signals, and abuse paths."},
            {"team": "blue", "title": "Extract observable indicators", "detail": "Record visible domains, errors, headers, identities, and control states for follow-up validation."},
        ],
        "audio": [
            {"team": "orange", "title": "Review social and voice abuse", "detail": "Assess impersonation, consent, disclosure, prompt-injection, and support-workflow risks."},
            {"team": "white", "title": "Confirm handling authority", "detail": "Validate consent, privacy, retention, and client authorization before transcription or analysis."},
        ],
        "video": [
            {"team": "purple", "title": "Turn the recording into a test path", "detail": "Map the demonstrated workflow to repeatable controls, evidence checkpoints, and regression steps."},
            {"team": "orange", "title": "Inspect workflow abuse cases", "detail": "Review the visible user journey for bypasses, unsafe transitions, and sensitive information exposure."},
        ],
        "document": [
            {"team": "green", "title": "Map architecture and trust boundaries", "detail": "Extract systems, identities, data paths, dependencies, and unstated defensive assumptions."},
            {"team": "yellow", "title": "Convert requirements into build gates", "detail": "Turn technical claims into testable engineering, dependency, configuration, and release checks."},
        ],
        "text": [
            {"team": "yellow", "title": "Review code and configuration safely", "detail": "Run secrets, dependency, static-analysis, and configuration checks in the authorized workspace."},
        ],
        "structured-data": [
            {"team": "blue", "title": "Normalize into telemetry", "detail": "Map records to assets, events, findings, severity, time, and evidence provenance."},
        ],
        "archive": [
            {"team": "yellow", "title": "Scan before extraction", "detail": "Keep the archive quarantined until malware, path traversal, size, and content-type checks pass."},
        ],
        "binary": [
            {"team": "yellow", "title": "Identify before analysis", "detail": "Verify actual type, signatures, malware state, and safe analysis tooling before opening the file."},
        ],
    }
    return [shared, *suggestions.get(kind, suggestions["binary"])]


def team_plan(selected_teams: list[str], targets: list[EngagementTarget]) -> dict[str, Any]:
    target_kinds = sorted({target.kind for target in targets})
    return {
        "targetKinds": target_kinds,
        "teams": [
            {"id": team, **TEAM_PLAYBOOKS[team]}
            for team in selected_teams
            if team in TEAM_PLAYBOOKS
        ],
        "rules": [
            "Stop on scope ambiguity or authorization expiry",
            "Do not run destructive checks without a separately approved dry run",
            "Preserve reproducible evidence and separate observation from verified proof",
            "Keep client and tenant data inside the assigned workspace",
        ],
    }


def finding_fingerprint(title: str, owner_team: str | None) -> str:
    normalized = re.sub(r"\W+", " ", title.lower()).strip()
    return hashlib.sha256(f"{owner_team or 'unassigned'}:{normalized}".encode("utf-8")).hexdigest()


def _engagement(session: Session, organization_id: str, engagement_id: str) -> Engagement:
    row = session.scalar(
        select(Engagement).where(
            Engagement.id == engagement_id,
            Engagement.organization_id == organization_id,
        )
    )
    if not row:
        raise ValueError("engagement not found")
    return row


def serialize_engagement(session: Session, row: Engagement) -> dict[str, Any]:
    targets = list(
        session.scalars(
            select(EngagementTarget)
            .where(EngagementTarget.engagement_id == row.id, EngagementTarget.organization_id == row.organization_id)
            .order_by(EngagementTarget.created_at)
        )
    )
    runs = list(
        session.scalars(
            select(AssessmentRun)
            .where(AssessmentRun.engagement_id == row.id, AssessmentRun.organization_id == row.organization_id)
            .order_by(AssessmentRun.sequence.desc())
        )
    )
    asset_rows = session.execute(
        select(EngagementAsset, Evidence)
        .join(Evidence, Evidence.id == EngagementAsset.evidence_id)
        .where(EngagementAsset.engagement_id == row.id, EngagementAsset.organization_id == row.organization_id)
        .order_by(EngagementAsset.created_at.desc())
    ).all()
    findings = list(
        session.scalars(
            select(Finding)
            .where(Finding.engagement_id == row.id, Finding.organization_id == row.organization_id)
            .order_by(Finding.created_at.desc())
        )
    )
    return {
        "id": row.id,
        "name": row.name,
        "clientName": row.client_name,
        "engagementType": row.engagement_type,
        "status": row.status,
        "objective": row.objective,
        "scopeRules": row.scope_rules,
        "authorization": {
            "basis": row.authorization_basis,
            "confirmed": row.authorization_confirmed,
            "attestation": row.authorization_attestation,
            "authorizedAt": iso(row.authorized_at),
            "expiresAt": iso(row.authorization_expires_at),
        },
        "selectedTeams": row.selected_teams,
        "targets": [
            {
                "id": target.id,
                "kind": target.kind,
                "displayName": target.display_name,
                "locator": target.locator,
                "environment": target.environment,
                "scopeStatus": target.scope_status,
                "notes": target.notes,
            }
            for target in targets
        ],
        "runs": [
            {
                "id": run.id,
                "sequence": run.sequence,
                "mode": run.mode,
                "status": run.status,
                "connectorId": run.connector_id,
                "taskId": run.task_id,
                "baselineRunId": run.baseline_run_id,
                "teamPlan": run.team_plan,
                "summary": run.summary,
                "recommendations": run.recommendations,
                "score": run.score,
                "createdAt": iso(run.created_at),
                "startedAt": iso(run.started_at),
                "completedAt": iso(run.completed_at),
            }
            for run in runs
        ],
        "assets": [
            {
                "id": asset.id,
                "evidenceId": evidence.id,
                "assessmentRunId": asset.assessment_run_id,
                "filename": evidence.filename,
                "contentType": evidence.content_type,
                "sizeBytes": evidence.size_bytes,
                "sha256": evidence.sha256,
                "classification": evidence.classification,
                "scanStatus": evidence.scan_status,
                "mediaKind": asset.media_kind,
                "analysisStatus": asset.analysis_status,
                "suggestions": asset.suggestions,
                "createdAt": iso(asset.created_at),
            }
            for asset, evidence in asset_rows
        ],
        "findings": [
            {
                "id": finding.id,
                "assessmentRunId": finding.assessment_run_id,
                "fingerprint": finding.fingerprint,
                "ownerTeam": finding.owner_team,
                "title": finding.title,
                "description": finding.description,
                "severity": finding.severity,
                "status": finding.status,
                "createdAt": iso(finding.created_at),
            }
            for finding in findings
        ],
        "createdAt": iso(row.created_at),
        "updatedAt": iso(row.updated_at),
    }


def list_engagements(session: Session, organization_id: str) -> list[dict[str, Any]]:
    rows = list(
        session.scalars(
            select(Engagement)
            .where(Engagement.organization_id == organization_id)
            .order_by(Engagement.updated_at.desc())
            .limit(50)
        )
    )
    return [serialize_engagement(session, row) for row in rows]


def compare_runs(
    session: Session,
    organization_id: str,
    engagement_id: str,
    baseline_run_id: str,
    current_run_id: str,
) -> dict[str, Any]:
    _engagement(session, organization_id, engagement_id)
    runs = list(
        session.scalars(
            select(AssessmentRun).where(
                AssessmentRun.organization_id == organization_id,
                AssessmentRun.engagement_id == engagement_id,
                AssessmentRun.id.in_([baseline_run_id, current_run_id]),
            )
        )
    )
    if len({run.id for run in runs}) != 2:
        raise ValueError("both comparison runs must belong to this engagement")

    def indexed(run_id: str) -> dict[str, Finding]:
        rows = session.scalars(
            select(Finding).where(
                Finding.organization_id == organization_id,
                Finding.engagement_id == engagement_id,
                Finding.assessment_run_id == run_id,
            )
        )
        return {
            row.fingerprint or finding_fingerprint(row.title, row.owner_team): row
            for row in rows
        }

    before = indexed(baseline_run_id)
    after = indexed(current_run_id)
    persistent = sorted(set(before) & set(after))
    introduced = sorted(set(after) - set(before))
    resolved = sorted(set(before) - set(after))

    def brief(row: Finding) -> dict[str, Any]:
        return {"fingerprint": row.fingerprint, "title": row.title, "severity": row.severity, "status": row.status, "ownerTeam": row.owner_team}

    return {
        "engagementId": engagement_id,
        "baselineRunId": baseline_run_id,
        "currentRunId": current_run_id,
        "counts": {"introduced": len(introduced), "persistent": len(persistent), "resolved": len(resolved)},
        "introduced": [brief(after[key]) for key in introduced],
        "persistent": [brief(after[key]) for key in persistent],
        "resolved": [brief(before[key]) for key in resolved],
        "generatedAt": iso(utcnow()),
    }


def sync_assessment_result(session: Session, task: Task) -> None:
    if task.action != "assessment.execute":
        return
    run = session.scalar(
        select(AssessmentRun).where(
            AssessmentRun.task_id == task.id,
            AssessmentRun.organization_id == task.organization_id,
        )
    )
    if not run:
        return
    result = scrub(task.result)
    run.status = "completed" if task.status == "succeeded" else "failed"
    run.completed_at = task.completed_at or utcnow()
    run.summary = result if isinstance(result, dict) else {"result": result}
    score = result.get("score") if isinstance(result, dict) else None
    run.score = max(0, min(100, int(score))) if isinstance(score, (int, float)) else None
    raw_recommendations = result.get("recommendations", []) if isinstance(result, dict) else []
    run.recommendations = [item for item in raw_recommendations[:100] if isinstance(item, dict)]

    allowed_severity = {"low", "medium", "high", "critical"}
    allowed_teams = set(TEAM_PLAYBOOKS)
    raw_findings = result.get("findings", []) if isinstance(result, dict) else []
    for raw in raw_findings[:200]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "")).strip()[:240]
        description = str(raw.get("description", "")).strip()[:20_000]
        severity = str(raw.get("severity", "medium")).lower()
        owner_team = str(raw.get("ownerTeam", "")).lower() or None
        if len(title) < 3 or len(description) < 3 or severity not in allowed_severity:
            continue
        if owner_team not in allowed_teams:
            owner_team = None
        fingerprint = str(raw.get("fingerprint", ""))[:64]
        if not re.fullmatch(r"[a-fA-F0-9]{32,64}", fingerprint):
            fingerprint = finding_fingerprint(title, owner_team)
        exists = session.scalar(
            select(Finding.id).where(
                Finding.organization_id == task.organization_id,
                Finding.assessment_run_id == run.id,
                Finding.fingerprint == fingerprint,
            )
        )
        if not exists:
            session.add(
                Finding(
                    organization_id=task.organization_id,
                    engagement_id=run.engagement_id,
                    assessment_run_id=run.id,
                    fingerprint=fingerprint,
                    owner_team=owner_team,
                    title=title,
                    description=description,
                    severity=severity,
                )
            )
    engagement = session.get(Engagement, run.engagement_id)
    if engagement:
        engagement.status = "review" if task.status == "succeeded" else "attention"


def sync_asset_analysis_result(session: Session, task: Task) -> None:
    if task.action != "evidence.analyze":
        return
    asset_id = str(task.payload.get("assetId", ""))
    asset = session.scalar(
        select(EngagementAsset).where(
            EngagementAsset.id == asset_id,
            EngagementAsset.organization_id == task.organization_id,
        )
    )
    if not asset:
        return
    asset.analysis_status = "completed" if task.status == "succeeded" else "failed"
    result = scrub(task.result)
    raw_suggestions = result.get("suggestions", []) if isinstance(result, dict) else []
    accepted: list[dict[str, str]] = []
    for raw in raw_suggestions[:50]:
        if not isinstance(raw, dict):
            continue
        team = str(raw.get("team", "")).lower()
        title = str(raw.get("title", "")).strip()[:180]
        detail = str(raw.get("detail", "")).strip()[:1000]
        if team in TEAM_PLAYBOOKS and len(title) >= 3 and len(detail) >= 3:
            accepted.append({"team": team, "title": title, "detail": detail})
    if accepted:
        asset.suggestions = [*asset.suggestions, *accepted][:100]

    allowed_severity = {"low", "medium", "high", "critical"}
    raw_findings = result.get("findings", []) if isinstance(result, dict) else []
    for raw in raw_findings[:100]:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title", "")).strip()[:240]
        description = str(raw.get("description", "")).strip()[:20_000]
        severity = str(raw.get("severity", "medium")).lower()
        owner_team = str(raw.get("ownerTeam", "")).lower() or None
        if len(title) < 3 or len(description) < 3 or severity not in allowed_severity:
            continue
        if owner_team not in TEAM_PLAYBOOKS:
            owner_team = None
        fingerprint = finding_fingerprint(title, owner_team)
        exists = session.scalar(
            select(Finding.id).where(
                Finding.organization_id == task.organization_id,
                Finding.engagement_id == asset.engagement_id,
                Finding.fingerprint == fingerprint,
                Finding.assessment_run_id == asset.assessment_run_id,
            )
        )
        if not exists:
            session.add(
                Finding(
                    organization_id=task.organization_id,
                    engagement_id=asset.engagement_id,
                    assessment_run_id=asset.assessment_run_id,
                    fingerprint=fingerprint,
                    owner_team=owner_team,
                    title=title,
                    description=description,
                    severity=severity,
                )
            )


def export_engagement_zip(
    session: Session,
    organization_id: str,
    engagement_id: str,
    audit: list[dict[str, Any]],
    audit_receipt: dict[str, Any],
) -> bytes:
    row = _engagement(session, organization_id, engagement_id)
    payload = serialize_engagement(session, row)
    runs = payload["runs"]
    comparison = None
    if len(runs) >= 2:
        comparison = compare_runs(session, organization_id, engagement_id, runs[1]["id"], runs[0]["id"])

    execution_receipts: list[dict[str, Any]] = []
    tasks = session.scalars(select(Task).where(Task.organization_id == organization_id).order_by(Task.created_at))
    for task in tasks:
        if not isinstance(task.payload, dict) or task.payload.get("engagementId") != engagement_id:
            continue
        result_receipt = task.result.get("executionReceipt") if isinstance(task.result, dict) else None
        execution_receipts.append(
            {
                "taskId": task.id,
                "action": task.action,
                "status": task.status,
                "policy": task.payload.get("_executionPolicy"),
                "executionGrantSha256": task.payload.get("_executionGrant", {}).get("sha256"),
                "executionReceipt": result_receipt,
                "completedAt": iso(task.completed_at),
            }
        )

    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("engagement.json", json.dumps(payload, indent=2, ensure_ascii=False))
        archive.writestr("audit-log.json", json.dumps(audit, indent=2, ensure_ascii=False))
        archive.writestr(
            "audit-verification.json",
            json.dumps(
                {
                    "schema": "aegis.audit-verification-receipt/1.0",
                    "engagementId": engagement_id,
                    "verifiedAt": iso(utcnow()),
                    "workspaceLedger": audit_receipt,
                    "includedEvents": len(audit),
                    "note": "The workspace ledger receipt is authoritative. The included events are an engagement-scoped view and are not a replacement chain.",
                },
                indent=2,
                ensure_ascii=False,
            ),
        )
        archive.writestr("execution-receipts.json", json.dumps(execution_receipts, indent=2, ensure_ascii=False))
        archive.writestr("comparison.json", json.dumps(comparison or {"status": "A second completed run is required for comparison."}, indent=2))

        findings_csv = io.StringIO(newline="")
        writer = csv.DictWriter(findings_csv, fieldnames=["severity", "status", "team", "title", "fingerprint", "run"])
        writer.writeheader()
        for finding in payload["findings"]:
            writer.writerow({
                "severity": finding["severity"],
                "status": finding["status"],
                "team": finding["ownerTeam"] or "",
                "title": finding["title"],
                "fingerprint": finding["fingerprint"] or "",
                "run": finding["assessmentRunId"] or "",
            })
        archive.writestr("findings.csv", findings_csv.getvalue())

        assets_csv = io.StringIO(newline="")
        writer = csv.DictWriter(assets_csv, fieldnames=["filename", "media_kind", "content_type", "size_bytes", "sha256", "scan_status", "analysis_status"])
        writer.writeheader()
        for asset in payload["assets"]:
            writer.writerow({
                "filename": asset["filename"],
                "media_kind": asset["mediaKind"],
                "content_type": asset["contentType"],
                "size_bytes": asset["sizeBytes"],
                "sha256": asset["sha256"],
                "scan_status": asset["scanStatus"],
                "analysis_status": asset["analysisStatus"],
            })
        archive.writestr("asset-register.csv", assets_csv.getvalue())
        archive.writestr(
            "README.txt",
            "AEGIS engagement export\n\nThis package contains tenant-scoped metadata, findings, run history, comparison, execution-policy receipts, and an audit verification receipt. The hash-chained workspace ledger is authoritative; narrative summaries are not proof of execution. Uploaded source files remain encrypted in the evidence store and are not duplicated into this portable package.\n",
        )
    return output.getvalue()
