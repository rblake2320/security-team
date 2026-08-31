from __future__ import annotations

import json
import signal
import socket
import time
from datetime import datetime, timezone
from typing import Any

from .analyzers import TEAMS, analyze_evidence, inspect_http_target, inspect_repository, run_gate
from .client import ConnectorAPI, ConnectorAPIError
from .config import ConnectorConfig


TEAM_NAMES = {
    "purple": "Purple Validation",
    "white": "White Authority",
    "yellow": "Yellow Secure Build",
    "green": "Green Defensibility",
    "orange": "Orange Adversarial Design",
    "blue": "Blue Defense",
    "red": "Red Validation",
}


def _log(event: str, **detail: Any) -> None:
    safe = {key: value for key, value in detail.items() if key.lower() not in {"token", "leasetoken", "authorization"}}
    print(json.dumps({"at": datetime.now(timezone.utc).isoformat(), "event": event, **safe}, separators=(",", ":")), flush=True)


class ConnectorWorker:
    def __init__(self, config: ConnectorConfig, api: ConnectorAPI | None = None):
        self.config = config
        self.api = api or ConnectorAPI(config)
        self.stopping = False
        self._active_task = ""

    def agents(self) -> list[dict[str, Any]]:
        status = "working" if self._active_task else "online"
        host_ref = socket.gethostname()[:80]
        return [
            {
                "externalId": f"aegis-{team}",
                "name": f"{TEAM_NAMES[team]} Agent",
                "kind": "security-team",
                "status": status,
                "capabilities": ["assessment.execute", "evidence.analyze", "gate.run"],
                "metadata": {"team": team, "runtime": "customer-edge", "hostRef": host_ref},
            }
            for team in TEAMS
        ]

    def heartbeat(self) -> None:
        self.api.heartbeat(self.agents())

    def _renew(self, task_id: str, lease_token: str) -> None:
        self.api.renew(task_id, lease_token)
        _log("task.lease.renewed", taskId=task_id)

    def _execute_assessment(self, task: dict[str, Any]) -> dict[str, Any]:
        payload = task.get("payload") or {}
        mode = str(payload.get("mode", "safe"))
        if mode not in {"safe", "standard", "deep"}:
            raise ValueError("assessment mode is invalid")
        target_results: list[dict[str, Any]] = []
        all_findings: list[dict[str, Any]] = []
        all_recommendations: list[dict[str, Any]] = []
        all_team_results: list[dict[str, Any]] = []
        for target in payload.get("targets", [])[:50]:
            kind = str(target.get("kind", "other"))
            locator = str(target.get("locator", ""))
            target_id = str(target.get("id", ""))
            if kind in {"website", "api"}:
                result = inspect_http_target(locator, self.config)
            elif kind == "repository":
                result = inspect_repository(self.config.resolve_allowed_path(locator))
            else:
                result = {
                    "kind": kind,
                    "metrics": {"analyzerInstalled": False},
                    "findings": [
                        {
                            "title": f"No {kind} analyzer is installed at this connector",
                            "description": "The target remained in scope but was not contacted or treated as tested. Install and explicitly allowlist a compatible collector before rerunning.",
                            "severity": "medium",
                            "ownerTeam": "green",
                        }
                    ],
                    "teamResults": [{"team": "white", "status": "blocked", "check": "Unsupported targets fail visibly instead of being counted as tested."}],
                    "recommendations": [],
                    "score": 93,
                    "automaticFailure": False,
                }
            findings = list(result.get("findings", []))
            all_findings.extend(findings)
            all_recommendations.extend(result.get("recommendations", []))
            all_team_results.extend(result.get("teamResults", []))
            target_results.append(
                {
                    "targetId": target_id,
                    "kind": kind,
                    "metrics": result.get("metrics", {}),
                    "findingCount": len(findings),
                    "automaticFailure": bool(result.get("automaticFailure")),
                }
            )
        if not target_results:
            raise ValueError("assessment work order contained no targets")
        severity_cost = {"critical": 35, "high": 15, "medium": 7, "low": 2}
        score = max(0, 100 - sum(severity_cost.get(str(item.get("severity")), 7) for item in all_findings))
        automatic_failure = any(item.get("severity") == "critical" for item in all_findings)
        return {
            "engine": "aegis-customer-edge/1.0",
            "executionMode": mode,
            "executionBoundary": "allowlisted-customer-edge",
            "targetResults": target_results,
            "teamResults": all_team_results[:100],
            "findings": all_findings[:200],
            "recommendations": all_recommendations[:100],
            "score": score,
            "automaticFailure": automatic_failure,
            "diagnosticOnly": True,
        }

    def execute(self, task: dict[str, Any], lease_token: str) -> tuple[str, dict[str, Any], str | None]:
        task_id = str(task.get("id", ""))
        action = str(task.get("action", ""))
        payload = task.get("payload") or {}
        if action == "assessment.execute":
            return "succeeded", self._execute_assessment(task), None
        if action == "evidence.analyze":
            content = self.api.download_evidence(task_id, lease_token)
            result = analyze_evidence(content, str(payload.get("filename", "artifact")), str(payload.get("mediaKind", "binary")))
            return "succeeded", result, None
        if action == "gate.run":
            gate_id = str(payload.get("gateId", ""))
            result = run_gate(self.config, gate_id, renew=lambda: self._renew(task_id, lease_token))
            return ("succeeded" if result["passed"] else "failed"), result, (None if result["passed"] else "engineering gate failed")
        raise PermissionError(f"connector refuses unsupported action: {action}")

    def run_once(self) -> bool:
        self.heartbeat()
        lease = self.api.lease()
        task = lease.get("task")
        if not task:
            return False
        lease_token = str(lease.get("leaseToken", ""))
        task_id = str(task.get("id", ""))
        self._active_task = task_id
        _log("task.started", taskId=task_id, action=task.get("action"), title=task.get("title"))
        try:
            status, result, error = self.execute(task, lease_token)
        except Exception as exc:  # the server receives a bounded failure instead of a lost lease
            status, result, error = "failed", {}, f"{type(exc).__name__}: {exc}"
            _log("task.failed", taskId=task_id, error=error)
        try:
            self.api.complete(task_id, lease_token, status=status, result=result, error=error)
            _log("task.completed", taskId=task_id, status=status, findings=len(result.get("findings", [])))
        finally:
            self._active_task = ""
            self.heartbeat()
        return True

    def serve_forever(self) -> None:
        _log("connector.started", **self.config.public_summary())

        def stop(_signum, _frame):  # type: ignore[no-untyped-def]
            self.stopping = True

        for name in ("SIGINT", "SIGTERM"):
            if hasattr(signal, name):
                signal.signal(getattr(signal, name), stop)
        failures = 0
        while not self.stopping:
            try:
                worked = self.run_once()
                failures = 0
                if not worked:
                    time.sleep(self.config.poll_seconds)
            except ConnectorAPIError as exc:
                failures += 1
                delay = min(60, max(self.config.poll_seconds, 2**min(failures, 5)))
                _log("connector.api_error", status=exc.status, error=str(exc), retrySeconds=delay)
                time.sleep(delay)
            except Exception as exc:
                failures += 1
                delay = min(60, max(self.config.poll_seconds, 2**min(failures, 5)))
                _log("connector.error", error=f"{type(exc).__name__}: {exc}", retrySeconds=delay)
                time.sleep(delay)
        _log("connector.stopped")
