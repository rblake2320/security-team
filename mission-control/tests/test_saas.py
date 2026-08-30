from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from aegis_platform.api import create_app
from aegis_platform.audit import verify_audit
from aegis_platform.config import Settings
from aegis_platform.coverage import seed_security_controls
from aegis_platform.models import (
    AIPolicy,
    AuditEvent,
    Connector,
    Membership,
    Organization,
    RetentionPolicy,
    TelemetryEvent,
    User,
)


@pytest.fixture()
def app_bundle(tmp_path: Path):
    settings = Settings(
        environment="test",
        database_url=f"sqlite:///{(tmp_path / 'platform.db').as_posix()}",
        evidence_root=tmp_path / "evidence",
        auth_mode="development",
        token_pepper="0123456789abcdef0123456789abcdef",
        bootstrap_email="owner@example.test",
        bootstrap_organization="Owner Workspace",
        bootstrap_slug="owner",
        max_evidence_bytes=1024 * 1024,
        lease_seconds=60,
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client, app, settings


def provision(client: TestClient, capabilities: list[str]) -> tuple[dict, str]:
    response = client.post(
        "/api/v1/connectors",
        json={"name": "Primary collector", "capabilities": capabilities},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    return body["connector"], body["token"]


def test_uninvited_identity_and_cross_workspace_access_fail_closed(app_bundle):
    client, app, _settings = app_bundle
    assert client.get("/api/v1/dashboard", headers={"X-Dev-User": "stranger@example.test"}).status_code == 401

    database = app.state.database
    with database.session() as session:
        other_org = Organization(slug="other", name="Other Customer")
        other_user = User(email="other@example.test", display_name="Other")
        session.add_all([other_org, other_user])
        session.flush()
        session.add_all(
            [
                Membership(organization_id=other_org.id, user_id=other_user.id, role="owner"),
                RetentionPolicy(organization_id=other_org.id),
                AIPolicy(organization_id=other_org.id),
            ]
        )
        seed_security_controls(session, other_org.id)
        other_id = other_org.id

    denied = client.get("/api/v1/dashboard", headers={"X-Workspace-ID": other_id})
    assert denied.status_code == 403
    allowed = client.get("/api/v1/dashboard", headers={"X-Dev-User": "other@example.test"})
    assert allowed.status_code == 200
    assert allowed.json()["workspace"]["id"] == other_id
    assert allowed.json()["counts"]["connectors"] == 0


def test_connector_secret_is_one_time_hashed_and_revocable(app_bundle):
    client, app, _settings = app_bundle
    connector, token = provision(client, ["observe.status", "shadow_ai.assets"])
    assert token.startswith("aegc_")

    with app.state.database.session() as session:
        row = session.get(Connector, connector["id"])
        assert row is not None
        assert row.token_hash != token
        assert token not in row.token_hash

    assert client.delete(f"/api/v1/connectors/{connector['id']}").status_code == 200
    rejected = client.post(
        "/api/v1/connector/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"version": "1.0", "agents": []},
    )
    assert rejected.status_code == 401


def test_connector_telemetry_is_idempotent_and_redacted(app_bundle):
    client, app, _settings = app_bundle
    _connector, token = provision(client, ["observe.status"])
    auth = {"Authorization": f"Bearer {token}"}
    heartbeat = client.post(
        "/api/v1/connector/heartbeat",
        headers=auth,
        json={
            "version": "1.2.3",
            "agents": [
                {
                    "externalId": "agent-1",
                    "name": "Workstation agent",
                    "kind": "endpoint",
                    "status": "online",
                    "metadata": {"apiKey": "must-not-persist", "host": "endpoint-a"},
                }
            ],
        },
    )
    assert heartbeat.status_code == 200
    payload = {
        "events": [
            {
                "idempotencyKey": "event-0001",
                "eventType": "control.observed",
                "severity": "info",
                "occurredAt": datetime.now(timezone.utc).isoformat(),
                "agentExternalId": "agent-1",
                "payload": {"authorization": "secret", "state": "healthy"},
            }
        ]
    }
    assert client.post("/api/v1/connector/events", headers=auth, json=payload).json() == {"accepted": 1, "duplicates": 0}
    assert client.post("/api/v1/connector/events", headers=auth, json=payload).json() == {"accepted": 0, "duplicates": 1}
    with app.state.database.session() as session:
        event = session.scalar(select(TelemetryEvent))
        assert event is not None
        assert event.payload["authorization"] == "[REDACTED]"


def test_high_risk_task_requires_approval_then_leases_and_completes(app_bundle):
    client, _app, _settings = app_bundle
    connector, token = provision(client, ["gate.run"])
    created = client.post(
        "/api/v1/tasks",
        json={"title": "Run release gates", "action": "gate.run", "connectorId": connector["id"]},
    )
    assert created.status_code == 201
    task = created.json()["task"]
    assert task["status"] == "awaiting_approval"
    assert client.get("/api/v1/connector/tasks/lease", headers={"Authorization": f"Bearer {token}"}).json()["task"] is None

    approved = client.post(
        f"/api/v1/tasks/{task['id']}/decision",
        json={"decision": "approved", "note": "Reviewed against the bounded gate manifest."},
    )
    assert approved.status_code == 200
    lease = client.get("/api/v1/connector/tasks/lease", headers={"Authorization": f"Bearer {token}"}).json()
    assert lease["task"]["id"] == task["id"]
    completed = client.post(
        f"/api/v1/connector/tasks/{task['id']}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"leaseToken": lease["leaseToken"], "status": "succeeded", "result": {"passed": True}},
    )
    assert completed.status_code == 200
    assert completed.json()["task"]["status"] == "succeeded"


def test_critical_actions_require_validated_dry_run_and_separate_approver(app_bundle):
    client, _app, _settings = app_bundle
    connector, _token = provision(client, ["shadow_ai.block"])
    missing_dry_run = client.post(
        "/api/v1/tasks",
        json={"title": "Block unsanctioned AI", "action": "shadow_ai.block", "connectorId": connector["id"]},
    )
    assert missing_dry_run.status_code == 403

    dry_run = client.post(
        "/api/v1/tasks",
        json={"title": "Preview AI block", "action": "shadow_ai.block", "connectorId": connector["id"], "dryRun": True},
    )
    assert dry_run.status_code == 201
    denied = client.post(
        f"/api/v1/tasks/{dry_run.json()['task']['id']}/decision",
        json={"decision": "approved", "note": "Owner attempted self approval."},
    )
    assert denied.status_code == 403


def test_shadow_ai_inventory_policy_and_sensitive_data_violation(app_bundle):
    client, app, _settings = app_bundle
    _connector, token = provision(client, ["shadow_ai.assets", "shadow_ai.usage", "telemetry.network"])
    auth = {"Authorization": f"Bearer {token}"}
    discovered = client.post(
        "/api/v1/connector/shadow-ai/assets",
        headers=auth,
        json={
            "assets": [
                {
                    "externalId": "net-chat-1",
                    "source": "network",
                    "name": "Observed chat service",
                    "destinationDomain": "chatgpt.com",
                    "userRef": "person@example.test",
                    "deviceRef": "laptop-7",
                    "models": ["unknown"],
                    "tools": ["browser"],
                    "mcpServers": [],
                    "resources": [],
                }
            ]
        },
    )
    assert discovered.status_code == 202
    usage = client.post(
        "/api/v1/connector/shadow-ai/usage",
        headers=auth,
        json={
            "usage": [
                {
                    "idempotencyKey": "ai-usage-0001",
                    "assetExternalId": "net-chat-1",
                    "source": "network",
                    "destinationDomain": "chatgpt.com",
                    "bytesSent": 840,
                    "estimatedCostMicrousd": 2500,
                    "dataLabels": ["source-code-secret"],
                    "occurredAt": datetime.now(timezone.utc).isoformat(),
                }
            ]
        },
    )
    assert usage.status_code == 202
    assert usage.json()["violations"] == 1
    posture = client.get("/api/v1/shadow-ai").json()
    assert posture["counts"]["assets"] == 1
    assert posture["counts"]["openViolations"] == 1
    assert posture["policy"]["retainPromptContent"] is False
    assert all("content" not in violation["detail"] for violation in posture["violations"])

    with app.state.database.session() as session:
        from aegis_platform.models import AIAsset

        asset = session.scalar(select(AIAsset))
        assert asset is not None
        assert asset.user_ref_hash and asset.user_ref_hash != "person@example.test"
        assert asset.device_ref_hash and asset.device_ref_hash != "laptop-7"


def test_customer_can_govern_shadow_ai_retention_and_execution_safety(app_bundle):
    client, _app, _settings = app_bundle
    policy = {
        "defaultDisposition": "require-approval",
        "sensitiveDataDisposition": "block",
        "approvedVendors": ["OpenAI"],
        "approvedDomains": ["api.openai.com"],
        "blockedDomains": ["unapproved.example"],
        "prohibitedDataLabels": ["credentials", "source-code-secret"],
        "retainPromptContent": False,
    }
    updated = client.put("/api/v1/shadow-ai/policy", json=policy)
    assert updated.status_code == 200, updated.text
    assert updated.json()["approvedDomains"] == ["api.openai.com"]
    assert updated.json()["retainPromptContent"] is False

    unsafe = policy | {"retainPromptContent": True}
    assert client.put("/api/v1/shadow-ai/policy", json=unsafe).status_code == 400
    overlap = policy | {"blockedDomains": ["api.openai.com"]}
    assert client.put("/api/v1/shadow-ai/policy", json=overlap).status_code == 400

    retention = {
        "telemetryDays": 45,
        "taskDays": 400,
        "evidenceDays": 730,
        "auditDays": 2555,
        "legalHoldDefault": True,
    }
    assert client.put("/api/v1/retention", json=retention).json() == retention
    safety = client.post(
        "/api/v1/safety",
        json={"level": "halted", "reason": "Owner activated the tested emergency stop."},
    )
    assert safety.status_code == 200
    assert safety.json() == {"safetyLevel": "halted", "killSwitchActive": True}


def test_security_coverage_exposes_team_owned_gaps_and_requires_sources(app_bundle):
    client, _app, _settings = app_bundle
    initial = client.get("/api/v1/security-coverage").json()
    assert initial["summary"]["controls"] >= 19
    assert {row["team"] for row in initial["teams"]} == {"purple", "white", "yellow", "green", "orange", "blue", "red"}
    endpoint = next(row for row in initial["controls"] if row["key"] == "blue.endpoint-ai-discovery")
    assert endpoint["status"] == "telemetry-gap"
    cannot_verify = client.put(
        f"/api/v1/security-coverage/{endpoint['id']}",
        json={"enabled": True, "ownerTeam": "blue", "status": "verified", "reason": "Trying to verify without telemetry.", "configuration": {}},
    )
    assert cannot_verify.status_code == 400

    provision(client, ["telemetry.endpoint", "shadow_ai.assets"])
    connected = client.get("/api/v1/security-coverage").json()
    endpoint = next(row for row in connected["controls"] if row["key"] == "blue.endpoint-ai-discovery")
    assert endpoint["status"] == "configured"
    verified = client.put(
        f"/api/v1/security-coverage/{endpoint['id']}",
        json={"enabled": True, "ownerTeam": "blue", "status": "verified", "reason": "Validated with bounded synthetic endpoint telemetry.", "configuration": {"scope": "managed endpoints"}},
    )
    assert verified.status_code == 200
    assert verified.json()["control"]["status"] == "verified"


def test_evidence_is_quarantined_and_audit_tampering_is_detected(app_bundle):
    client, app, _settings = app_bundle
    uploaded = client.post(
        "/api/v1/evidence",
        files={"file": ("proof.txt", b"bounded evidence", "text/plain")},
        data={"classification": "customer-confidential"},
    )
    assert uploaded.status_code == 201
    evidence = uploaded.json()["evidence"]
    assert evidence["scanStatus"] == "quarantined"
    assert len(evidence["sha256"]) == 64
    stored_files = list(app.state.evidence_store.root.rglob("*.aegis"))
    assert len(stored_files) == 1
    assert b"bounded evidence" not in stored_files[0].read_bytes()
    assert client.post(
        f"/api/v1/evidence/{evidence['id']}/scan",
        json={"status": "clean", "note": "Validated by the evidence scanner."},
    ).status_code == 200

    with app.state.database.session() as session:
        assert verify_audit(session, session.scalar(select(Organization.id)))["ok"] is True
        event = session.scalar(select(AuditEvent).order_by(AuditEvent.sequence))
        assert event is not None
        event.detail = {"tampered": True}
    ledger = client.get("/api/v1/audit").json()["ledger"]
    assert ledger["ok"] is False


def engagement_payload() -> dict:
    return {
        "name": "Staging launch review",
        "clientName": "Example Client",
        "engagementType": "pre-launch",
        "objective": "Prove the staging application is ready to launch and produce prioritized remediation.",
        "scopeRules": "Test only the listed staging URL. No denial of service, social engineering, destructive actions, or production data access.",
        "authorizationBasis": "asset-owner",
        "authorizationAttestation": "I own and control this staging target and authorize the recorded non-destructive assessment.",
        "authorizationConfirmed": True,
        "selectedTeams": ["purple", "white", "yellow", "green", "orange", "blue", "red"],
        "targets": [
            {
                "kind": "website",
                "displayName": "Staging web app",
                "locator": "https://staging.example.test/path?secret=removed#fragment",
                "environment": "staging",
            }
        ],
    }


def complete_assessment(client: TestClient, token: str, task_id: str, title: str) -> None:
    auth = {"Authorization": f"Bearer {token}"}
    lease = client.get("/api/v1/connector/tasks/lease", headers=auth)
    assert lease.status_code == 200, lease.text
    leased = lease.json()
    assert leased["task"]["id"] == task_id
    completed = client.post(
        f"/api/v1/connector/tasks/{task_id}/complete",
        headers=auth,
        json={
            "leaseToken": leased["leaseToken"],
            "status": "succeeded",
            "result": {
                "score": 82,
                "recommendations": [{"priority": "high", "title": "Tighten session controls"}],
                "findings": [
                    {
                        "title": title,
                        "description": "A reproducible synthetic test finding for the authorized staging target.",
                        "severity": "high",
                        "ownerTeam": "yellow",
                    }
                ],
            },
        },
    )
    assert completed.status_code == 200, completed.text


def test_engagement_intake_media_execution_comparison_and_export(app_bundle):
    client, _app, _settings = app_bundle
    invalid = engagement_payload() | {"authorizationConfirmed": False}
    assert client.post("/api/v1/engagements", json=invalid).status_code == 422

    created = client.post("/api/v1/engagements", json=engagement_payload())
    assert created.status_code == 201, created.text
    engagement = created.json()["engagement"]
    engagement_id = engagement["id"]
    assert engagement["targets"][0]["locator"] == "https://staging.example.test/path"
    assert engagement["authorization"]["confirmed"] is True

    upload = client.post(
        "/api/v1/evidence",
        files={"file": ("walkthrough.mp4", b"synthetic-media", "video/mp4")},
        data={"engagementId": engagement_id, "classification": "customer-confidential"},
    )
    assert upload.status_code == 201, upload.text
    assert upload.json()["asset"]["mediaKind"] == "video"
    assert upload.json()["asset"]["analysisStatus"] == "quarantined"
    evidence_id = upload.json()["evidence"]["id"]
    assert client.get(f"/api/v1/evidence/{evidence_id}/download").status_code == 403
    assert client.post(
        f"/api/v1/evidence/{evidence_id}/scan",
        json={"status": "clean", "note": "Validated by the synthetic test scanner."},
    ).status_code == 200
    assert client.get(f"/api/v1/evidence/{evidence_id}/download").content == b"synthetic-media"

    no_executor = client.post(f"/api/v1/engagements/{engagement_id}/launch", json={"mode": "safe"})
    assert no_executor.status_code == 400
    connector, token = provision(client, ["assessment.execute", "evidence.analyze"])
    asset_id = upload.json()["asset"]["id"]
    queued_analysis = client.post(
        f"/api/v1/engagements/{engagement_id}/assets/{asset_id}/analyze",
        json={"connectorId": connector["id"]},
    )
    assert queued_analysis.status_code == 202, queued_analysis.text
    analysis_task_id = queued_analysis.json()["task"]["id"]
    auth = {"Authorization": f"Bearer {token}"}
    assert client.get(f"/api/v1/connector/tasks/{analysis_task_id}/evidence", headers=auth).status_code == 403
    analysis_lease = client.get("/api/v1/connector/tasks/lease", headers=auth).json()
    assert analysis_lease["task"]["id"] == analysis_task_id
    evidence_response = client.get(
        f"/api/v1/connector/tasks/{analysis_task_id}/evidence",
        headers={**auth, "X-Task-Lease": analysis_lease["leaseToken"]},
    )
    assert evidence_response.content == b"synthetic-media"
    assert client.post(
        f"/api/v1/connector/tasks/{analysis_task_id}/complete",
        headers=auth,
        json={
            "leaseToken": analysis_lease["leaseToken"],
            "status": "succeeded",
            "result": {
                "suggestions": [{"team": "orange", "title": "Review the demonstrated workflow", "detail": "Inspect every visible authorization transition."}],
                "findings": [{"title": "Video reveals a verbose error", "description": "A synthetic media observation attached to this engagement.", "severity": "low", "ownerTeam": "blue"}],
            },
        },
    ).status_code == 200

    launched = client.post(
        f"/api/v1/engagements/{engagement_id}/launch",
        json={"mode": "safe", "connectorId": connector["id"]},
    )
    assert launched.status_code == 202, launched.text
    task = launched.json()["task"]
    first_run = launched.json()["engagement"]["runs"][0]
    assert task["status"] == "awaiting_approval"
    assert first_run["status"] == "awaiting_approval"
    assert len(first_run["teamPlan"]["teams"]) == 7
    assert client.post(
        f"/api/v1/tasks/{task['id']}/decision",
        json={"decision": "approved", "note": "Authorized staging assessment approved."},
    ).status_code == 200
    complete_assessment(client, token, task["id"], "Session cookie lacks a secure attribute")

    after_first = client.get(f"/api/v1/engagements/{engagement_id}").json()["engagement"]
    assert after_first["runs"][0]["status"] == "completed"
    assert after_first["runs"][0]["score"] == 82
    assert after_first["findings"][0]["ownerTeam"] == "yellow"
    assert after_first["assets"][0]["analysisStatus"] == "completed"
    assert any(item["title"] == "Review the demonstrated workflow" for item in after_first["assets"][0]["suggestions"])

    second = client.post(
        f"/api/v1/engagements/{engagement_id}/launch",
        json={"mode": "standard", "connectorId": connector["id"], "baselineRunId": first_run["id"]},
    )
    assert second.status_code == 202, second.text
    second_task = second.json()["task"]
    second_run = second.json()["engagement"]["runs"][0]
    assert client.post(
        f"/api/v1/tasks/{second_task['id']}/decision",
        json={"decision": "approved", "note": "Approved the authorized regression assessment."},
    ).status_code == 200
    complete_assessment(client, token, second_task["id"], "Administrative endpoint lacks step-up authentication")

    comparison = client.get(
        f"/api/v1/engagements/{engagement_id}/compare",
        params={"baselineRunId": first_run["id"], "currentRunId": second_run["id"]},
    )
    assert comparison.status_code == 200, comparison.text
    assert comparison.json()["counts"] == {"introduced": 1, "persistent": 0, "resolved": 1}

    exported = client.get(f"/api/v1/engagements/{engagement_id}/export")
    assert exported.status_code == 200
    assert exported.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(exported.content)) as archive:
        assert {"README.txt", "engagement.json", "audit-log.json", "comparison.json", "findings.csv", "asset-register.csv"} <= set(archive.namelist())
        manifest = json.loads(archive.read("engagement.json"))
        assert manifest["id"] == engagement_id
        assert len(manifest["runs"]) == 2
        assert b"synthetic-media" not in exported.content


def test_engagements_are_tenant_scoped(app_bundle):
    client, app, _settings = app_bundle
    created = client.post("/api/v1/engagements", json=engagement_payload()).json()["engagement"]
    database = app.state.database
    with database.session() as session:
        other_org = Organization(slug="engagement-other", name="Other Engagement Customer")
        other_user = User(email="engagement-other@example.test", display_name="Other")
        session.add_all([other_org, other_user])
        session.flush()
        session.add_all([
            Membership(organization_id=other_org.id, user_id=other_user.id, role="owner"),
            RetentionPolicy(organization_id=other_org.id),
            AIPolicy(organization_id=other_org.id),
        ])
    other_headers = {"X-Dev-User": "engagement-other@example.test"}
    assert client.get(f"/api/v1/engagements/{created['id']}", headers=other_headers).status_code == 400
    assert client.get(f"/api/v1/engagements/{created['id']}/export", headers=other_headers).status_code == 400


def test_production_configuration_fails_closed():
    with pytest.raises(RuntimeError, match="Unsafe production configuration"):
        Settings(environment="production").validate()
