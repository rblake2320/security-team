from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import sys

import pytest

from aegis_connector.analyzers import analyze_evidence, inspect_repository
from aegis_connector.config import ConnectorConfig
from aegis_connector.worker import ConnectorWorker


def execution_grant(task_id: str, action: str, capability: str) -> dict:
    material = {
        "schema": "aegis.execution-grant/1.0",
        "taskId": task_id,
        "connectorId": "connector-1",
        "agentId": None,
        "action": action,
        "effectiveCapabilities": [capability],
        "risk": "high",
        "approvalRequired": True,
        "dryRun": False,
        "reversible": True,
        "issuedAt": "2026-09-01T00:00:00+00:00",
        "expiresAt": "2026-09-01T00:02:00+00:00",
        "policy": {
            "schema": "aegis.action-policy-receipt/1.0",
            "package": {
                "name": "aegis-action-catalog",
                "version": "1.0.0",
                "contentSha256": "a" * 64,
                "buildRevision": "development",
            },
            "action": action,
            "connectorCapability": capability,
        },
    }
    return {
        **material,
        "sha256": hashlib.sha256(
            json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        ).hexdigest(),
    }


def test_connector_runtime_is_model_independent():
    connector_root = Path(__file__).parents[1] / "aegis_connector"
    imported_modules: set[str] = set()
    for source_path in connector_root.glob("*.py"):
        tree = ast.parse(source_path.read_text(encoding="utf-8"), filename=str(source_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name.split(".", 1)[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                imported_modules.add(node.module.split(".", 1)[0])

    assert imported_modules <= sys.stdlib_module_names
    assert not imported_modules & {"anthropic", "google", "langchain", "litellm", "ollama", "openai"}


def connector_config(root: Path) -> ConnectorConfig:
    return ConnectorConfig(
        api_url="http://127.0.0.1:8780",
        token="aegc_abcdefghijklmnopqrstuvwxyz012345",
        program_root=root,
        allowed_roots=(root,),
        allowed_hosts=(),
    )


def test_repository_analyzer_produces_real_findings_without_returning_secret(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name":"sample"}', encoding="utf-8")
    (tmp_path / "app.py").write_text('password = "this-is-a-real-looking-secret"\n', encoding="utf-8")

    result = inspect_repository(tmp_path)

    titles = {item["title"] for item in result["findings"]}
    assert "package.json is not paired with a lockfile" in titles
    assert "Potential secret material detected" in titles
    assert result["automaticFailure"] is True
    assert result["score"] < 100
    assert len(result["teamResults"]) == 7
    rendered = json.dumps(result)
    assert "this-is-a-real-looking-secret" not in rendered
    assert "app.py:1" in rendered


def test_connector_rejects_repository_outside_local_allowlist(tmp_path: Path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    config = connector_config(allowed)

    assert config.resolve_allowed_path(str(allowed)) == allowed.resolve()
    with pytest.raises(PermissionError, match="outside"):
        config.resolve_allowed_path(str(outside))


def test_evidence_analysis_is_bounded_and_does_not_echo_secret():
    content = b'api_key = "abcdefghijklmnopqrstuvwxyz"\n'
    result = analyze_evidence(content, "configuration.txt", "text")

    assert result["bytesAnalyzed"] == len(content)
    assert len(result["sha256"]) == 64
    assert result["findings"][0]["severity"] == "critical"
    assert "abcdefghijklmnopqrstuvwxyz" not in json.dumps(result)


class FakeAPI:
    def __init__(self, root: Path):
        self.completed: dict | None = None
        self.heartbeats = 0
        self.leased = False
        self.root = root

    def heartbeat(self, agents):  # type: ignore[no-untyped-def]
        self.heartbeats += 1
        assert len(agents) == 7
        return {"accepted": True}

    def lease(self):  # type: ignore[no-untyped-def]
        if self.leased:
            return {"task": None}
        self.leased = True
        return {
            "task": {
                "id": "task-1",
                "title": "Assess authorized repository",
                "action": "assessment.execute",
                "executionGrant": execution_grant("task-1", "assessment.execute", "assessment.execute"),
                "payload": {
                    "mode": "safe",
                    "targets": [{"id": "target-1", "kind": "repository", "locator": str(self.root)}],
                },
            },
            "leaseToken": "aegl_abcdefghijklmnopqrstuvwxyz012345",
        }

    def complete(self, task_id, lease_token, **payload):  # type: ignore[no-untyped-def]
        self.completed = {"taskId": task_id, "leaseToken": lease_token, **payload}
        return {"task": {"id": task_id}}


def test_worker_executes_assessment_and_returns_findings(tmp_path: Path):
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / "SECURITY.md").write_text("# Reporting\n", encoding="utf-8")
    api = FakeAPI(tmp_path)
    worker = ConnectorWorker(connector_config(tmp_path), api=api)  # type: ignore[arg-type]

    assert worker.run_once() is True
    assert api.heartbeats == 2
    assert api.completed is not None
    assert api.completed["status"] == "succeeded"
    result = api.completed["result"]
    assert result["engine"] == "aegis-customer-edge/1.0"
    assert result["targetResults"][0]["kind"] == "repository"
    assert result["targetResults"][0]["status"] == "completed"
    assert len(result["teamResults"]) == 7
    assert result["diagnosticOnly"] is True
    assert result["executionReceipt"]["executionGrantSha256"] == execution_grant(
        "task-1", "assessment.execute", "assessment.execute"
    )["sha256"]


class UnsupportedTargetAPI(FakeAPI):
    def lease(self):  # type: ignore[no-untyped-def]
        leased = super().lease()
        if leased.get("task"):
            leased["task"]["payload"]["targets"] = [
                {"id": "target-1", "kind": "cloud", "locator": "tenant-a"}
            ]
        return leased


def test_worker_does_not_count_unsupported_target_as_success(tmp_path: Path):
    api = UnsupportedTargetAPI(tmp_path)
    worker = ConnectorWorker(connector_config(tmp_path), api=api)  # type: ignore[arg-type]

    assert worker.run_once() is True
    assert api.completed is not None
    assert api.completed["status"] == "failed"
    assert "could not be executed" in api.completed["error"]
    assert api.completed["result"]["assessmentStatus"] == "incomplete"
    assert api.completed["result"]["targetResults"][0]["status"] == "blocked"


def test_worker_rejects_tampered_effective_grant(tmp_path: Path):
    api = FakeAPI(tmp_path)
    leased = api.lease()
    leased["task"]["executionGrant"]["effectiveCapabilities"] = ["network.block"]
    api.leased = False
    api.lease = lambda: leased  # type: ignore[method-assign]
    worker = ConnectorWorker(connector_config(tmp_path), api=api)  # type: ignore[arg-type]

    assert worker.run_once() is True
    assert api.completed is not None
    assert api.completed["status"] == "failed"
    assert "integrity check" in api.completed["error"]
