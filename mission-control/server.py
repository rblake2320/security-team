#!/usr/bin/env python3
"""AEGIS Mission Control: local-first control plane for the security-team repo.

The server intentionally uses only the Python standard library. It reads the
program's authoritative manifests, exposes a bounded API, and runs only gate
IDs already present in ci_gates.json. It binds to loopback by default.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
DEFAULT_ROOT = HERE.parent
DEFAULT_DIST = HERE / "web" / "dist"
MAX_BODY = 4 * 1024
MAX_OUTPUT = 24_000
CONTROL_WINDOW_SECONDS = 60.0
CONTROL_REQUESTS_PER_WINDOW = 10

TEAM_ORDER = ("purple", "white", "yellow", "green", "orange", "blue", "red")
TEAM_DEFAULTS = {
    "purple": ("Purple Team", "#9b7cff", "Validate", "Offense + defense integration"),
    "white": ("White Team", "#e8edf2", "Authorize", "Independent safety and exercise control"),
    "yellow": ("Yellow Team", "#f4d35e", "Build", "Secure engineering and remediation"),
    "green": ("Green Team", "#4ee29a", "Engineer", "Defensibility and detection architecture"),
    "orange": ("Orange Team", "#ff985b", "Anticipate", "Adversarial design review"),
    "blue": ("Blue Team", "#5ba8ff", "Defend", "Detection, response, and recovery"),
    "red": ("Red Team", "#ff5f67", "Prove", "Authorized adversarial assessment"),
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def load_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return fallback


def bounded(value: Any, limit: int = 1200) -> str:
    text = str(value or "").replace("\x00", "")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def run_process(argv: list[str], cwd: Path, timeout: float = 8.0) -> tuple[int, str]:
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        result = subprocess.run(
            argv,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            creationflags=flags,
            check=False,
        )
        output = (result.stdout + ("\n" if result.stdout and result.stderr else "") + result.stderr).strip()
        return result.returncode, output
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 124, bounded(exc, 2000)


class AuditLedger:
    """Small append-only hash chain for control-plane actions."""

    def __init__(self, path: Path):
        self.path = path
        self._lock = threading.Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _entries(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return rows

    def append(self, kind: str, summary: str, **detail: Any) -> dict[str, Any]:
        with self._lock:
            entries = self._entries()
            previous = entries[-1].get("hash", "GENESIS") if entries else "GENESIS"
            record = {
                "id": str(uuid.uuid4()),
                "at": utc_now(),
                "kind": bounded(kind, 48),
                "summary": bounded(summary, 320),
                "detail": {key: bounded(value, 2000) for key, value in detail.items()},
                "previous": previous,
            }
            material = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
            record["hash"] = hashlib.sha256(material).hexdigest()
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            return record

    def recent(self, limit: int = 24) -> list[dict[str, Any]]:
        with self._lock:
            return list(reversed(self._entries()[-limit:]))

    def verify(self) -> dict[str, Any]:
        with self._lock:
            entries = self._entries()
        previous = "GENESIS"
        for index, entry in enumerate(entries):
            claimed = entry.get("hash")
            material_entry = {key: value for key, value in entry.items() if key != "hash"}
            material = json.dumps(material_entry, sort_keys=True, separators=(",", ":")).encode("utf-8")
            actual = hashlib.sha256(material).hexdigest()
            if entry.get("previous") != previous or claimed != actual:
                return {"ok": False, "entries": len(entries), "failedAt": index + 1, "head": previous}
            previous = claimed
        return {"ok": True, "entries": len(entries), "head": previous}


@dataclass
class GateRun:
    id: str
    gate_id: str
    gate_name: str
    mode: str
    status: str = "queued"
    requested_at: str = field(default_factory=utc_now)
    started_at: str | None = None
    finished_at: str | None = None
    return_code: int | None = None
    output: str = ""
    elapsed_seconds: float | None = None

    def public(self) -> dict[str, Any]:
        result = asdict(self)
        result["gateId"] = result.pop("gate_id")
        result["gateName"] = result.pop("gate_name")
        result["requestedAt"] = result.pop("requested_at")
        result["startedAt"] = result.pop("started_at")
        result["finishedAt"] = result.pop("finished_at")
        result["returnCode"] = result.pop("return_code")
        result["elapsedSeconds"] = result.pop("elapsed_seconds")
        return result


class MissionControl:
    def __init__(
        self,
        root: Path = DEFAULT_ROOT,
        dist: Path = DEFAULT_DIST,
        mode: str = "operator",
        require_access_header: bool = False,
    ):
        if mode not in {"operator", "demo"}:
            raise ValueError("mode must be operator or demo")
        self.root = root.resolve()
        self.dist = dist.resolve()
        self.mode = mode
        self.require_access_header = require_access_header
        self.runtime = HERE / "runtime"
        self.audit = AuditLedger(self.runtime / "audit.jsonl")
        self.runs: dict[str, GateRun] = {}
        self._runs_lock = threading.Lock()
        self._snapshot_lock = threading.Lock()
        self._snapshot_cache: tuple[float, dict[str, Any]] | None = None
        self._rate_lock = threading.Lock()
        self._control_requests: dict[str, list[float]] = {}

    @property
    def controls_enabled(self) -> bool:
        return self.mode == "operator"

    def allow_control_request(self, identity: str) -> bool:
        now = time.monotonic()
        with self._rate_lock:
            recent = [
                instant
                for instant in self._control_requests.get(identity, [])
                if now - instant < CONTROL_WINDOW_SECONDS
            ]
            if len(recent) >= CONTROL_REQUESTS_PER_WINDOW:
                self._control_requests[identity] = recent
                return False
            recent.append(now)
            self._control_requests[identity] = recent
            return True

    @property
    def gate_manifest(self) -> dict[str, Any]:
        manifest = load_json(self.root / "00-shared" / "config" / "ci_gates.json", {})
        if manifest or self.mode != "demo":
            return manifest
        return {
            "engineering_gates": [
                {"id": team_id, "name": f"{TEAM_DEFAULTS[team_id][0]} evidence contract", "kind": "synthetic"}
                for team_id in TEAM_ORDER
            ] + [
                {"id": "application-security", "name": "Application security baseline", "kind": "synthetic"},
                {"id": "shadow-ai", "name": "Shadow AI coverage validation", "kind": "synthetic"},
            ],
            "assurance_gates": [
                {"id": "readiness", "name": "Fail-closed readiness check", "kind": "assurance"}
            ],
        }

    def _git(self) -> dict[str, Any]:
        if self.mode == "demo":
            return {
                "branch": "showcase",
                "commit": "PUBLIC",
                "committedAt": "",
                "subject": "Redacted read-only demonstration",
                "dirty": False,
                "changedCount": 0,
                "changes": [],
            }
        _, branch = run_process(["git", "branch", "--show-current"], self.root)
        _, commit_raw = run_process(
            ["git", "log", "-1", "--pretty=format:%h|%cI|%s"], self.root
        )
        _, status_raw = run_process(["git", "status", "--porcelain"], self.root)
        changes = [line for line in status_raw.splitlines() if line.strip()]
        commit_bits = commit_raw.split("|", 2)
        return {
            "branch": branch.strip() or "detached",
            "commit": commit_bits[0] if commit_bits else "unknown",
            "committedAt": commit_bits[1] if len(commit_bits) > 1 else "",
            "subject": commit_bits[2] if len(commit_bits) > 2 else "",
            "dirty": bool(changes),
            "changedCount": len(changes),
            "changes": [bounded(line, 220) for line in changes[:12]],
        }

    def _readiness(self) -> dict[str, Any]:
        doc = load_json(
            self.root / "00-shared" / "config" / "assessment_readiness.json", {}
        )
        if not doc and self.mode == "demo":
            doc = {
                "assessment_readiness": {
                    "required_gates": ["identity_boundary", "connector_evidence", "human_authority", "recovery_proof"],
                    "on_failure": {
                        "result_marking": "PUBLIC_SYNTHETIC_DEMONSTRATION",
                        "allow_exercise": False,
                        "allow_diagnostic_score": True,
                        "allow_assurance_statement": False,
                    },
                },
                "gate_definitions": {
                    "identity_boundary": {"status": "VERIFIED", "owner": "White Team", "verification": ["Synthetic tenant identity is isolated"]},
                    "connector_evidence": {"status": "VERIFIED", "owner": "Green Team", "verification": ["Synthetic connector receipts are bounded"]},
                    "human_authority": {"status": "PENDING", "owner": "Customer approver", "verification": ["Customer assigns an independent approver"]},
                    "recovery_proof": {"status": "PENDING", "owner": "Customer operator", "verification": ["Customer completes a restore drill"]},
                },
                "state_model": {
                    "current_state": "CUSTOMER_ONBOARDING",
                    "current_state_rationale": "Synthetic data shows exactly how AEGIS identifies proven controls and customer-owned prerequisites.",
                    "states": ["CUSTOMER_ONBOARDING", "CONNECTED", "OPERATIONAL", "EVIDENCE_VERIFIED"],
                },
            }
        assessment = doc.get("assessment_readiness", {})
        definitions = doc.get("gate_definitions", {})
        gates = []
        for gate_id in assessment.get("required_gates", []):
            data = definitions.get(gate_id, {})
            gates.append(
                {
                    "id": gate_id,
                    "label": gate_id.replace("_", " ").title(),
                    "status": data.get("status", "UNKNOWN"),
                    "owner": data.get("owner", "Unassigned"),
                    "closureItem": data.get("closure_item"),
                    "verification": data.get("verification", []),
                    "evidence": data.get("evidence", []),
                }
            )
        verified = sum(1 for gate in gates if gate["status"] == "VERIFIED")
        state_model = doc.get("state_model", {})
        on_failure = assessment.get("on_failure", {})
        return {
            "verified": verified,
            "total": len(gates),
            "gates": gates,
            "currentState": state_model.get("current_state", "UNKNOWN"),
            "rationale": state_model.get("current_state_rationale", ""),
            "states": state_model.get("states", []),
            "marking": on_failure.get("result_marking", "UNMARKED"),
            "allowExercise": bool(on_failure.get("allow_exercise", False)),
            "allowDiagnosticScore": bool(on_failure.get("allow_diagnostic_score", False)),
            "allowAssuranceStatement": bool(on_failure.get("allow_assurance_statement", False)),
        }

    def _latest_runs_by_gate(self) -> dict[str, GateRun]:
        latest: dict[str, GateRun] = {}
        with self._runs_lock:
            ordered = sorted(self.runs.values(), key=lambda item: item.requested_at)
        for run in ordered:
            latest[run.gate_id] = run
        return latest

    def _gates(self) -> dict[str, Any]:
        manifest = self.gate_manifest
        latest = self._latest_runs_by_gate()
        rows = []
        for gate in manifest.get("engineering_gates", []):
            run = latest.get(gate.get("id", "")) or latest.get("all")
            rows.append(
                {
                    "id": gate.get("id"),
                    "name": gate.get("name"),
                    "kind": gate.get("kind"),
                    "status": run.status if run else "not_run",
                    "lastRunId": run.id if run else None,
                    "elapsedSeconds": run.elapsed_seconds if run else None,
                }
            )
        return {
            "engineering": rows,
            "engineeringCount": len(rows),
            "assurance": [
                {"id": gate.get("id"), "name": gate.get("name"), "kind": gate.get("kind")}
                for gate in manifest.get("assurance_gates", [])
            ],
        }

    def _teams(self, gate_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        gate_lookup = {gate["id"]: gate for gate in gate_rows}
        teams = []
        for team_id in TEAM_ORDER:
            name, color, verb, purpose = TEAM_DEFAULTS[team_id]
            scorecard = load_json(
                self.root / f"{team_id}-team" / "config" / "scorecard.json", {}
            )
            if not scorecard and self.mode == "demo":
                scorecard = {
                    "pass_threshold": 0.8,
                    "program_weight_7team": round(1 / 7, 4),
                    "test": f"Synthetic {name} evidence contract for a customer-owned workspace.",
                    "automatic_failure_conditions": ["Unapproved high-impact action or missing evidence source"],
                    "components": {"evidence": {"name": "bounded evidence", "weight": 1.0}},
                }
            gate = gate_lookup.get(team_id, {})
            teams.append(
                {
                    "id": team_id,
                    "name": name,
                    "color": color,
                    "verb": verb,
                    "purpose": purpose,
                    "status": gate.get("status", "not_run"),
                    "lastRunId": gate.get("lastRunId"),
                    "passThreshold": scorecard.get("pass_threshold"),
                    "programWeight": scorecard.get("program_weight_7team"),
                    "test": scorecard.get("test", ""),
                    "automaticFailures": scorecard.get("automatic_failure_conditions", []),
                    "components": scorecard.get("components", {}),
                }
            )
        return teams

    def _observer(self) -> dict[str, Any]:
        if self.mode == "demo":
            return {
                "online": True,
                "demo": True,
                "activeCount": 3,
                "blockedCount": 0,
                "securityTeamCount": 3,
                "sessions": [
                    {
                        "agent": "Purple Validation Agent",
                        "sessionId": "sample-purple",
                        "status": "working",
                        "task": "Sample: correlate a detection gap with its authorized retest contract.",
                        "reason": "Synthetic public demonstration record.",
                        "nextAction": "Route verified evidence to the closure gate.",
                        "eventTime": utc_now(),
                    },
                    {
                        "agent": "Blue Response Agent",
                        "sessionId": "sample-blue",
                        "status": "working",
                        "task": "Sample: validate telemetry coverage for a controlled exercise.",
                        "reason": "Synthetic public demonstration record.",
                        "nextAction": "Attach the bounded validation receipt.",
                        "eventTime": utc_now(),
                    },
                    {
                        "agent": "White Control Agent",
                        "sessionId": "sample-white",
                        "status": "waiting",
                        "task": "Sample: hold exercise authorization until independent prerequisites close.",
                        "reason": "Synthetic public demonstration record.",
                        "nextAction": "Await human-controlled attestation.",
                        "eventTime": utc_now(),
                    },
                ],
                "collisions": [],
                "ledger": {"ok": True, "checked": 128, "head": "PUBLIC-DEMO-REDACTED"},
            }
        url = "http://127.0.0.1:8091/v1/status"
        try:
            with urllib.request.urlopen(url, timeout=1.5) as response:
                payload = json.loads(response.read(2_000_000).decode("utf-8"))
        except (OSError, urllib.error.URLError, json.JSONDecodeError, TimeoutError):
            return {
                "online": False,
                "activeCount": 0,
                "blockedCount": 0,
                "sessions": [],
                "ledger": {"ok": False, "checked": 0, "head": "unavailable"},
            }

        sessions = []
        candidates = payload.get("sessions") or payload.get("events") or []
        for item in candidates:
            workspace = str(item.get("workspace", "")).lower().replace("/", "\\")
            project = str(item.get("repo") or item.get("project") or "").lower()
            if "security-team" not in workspace and "security-team" not in project:
                continue
            sessions.append(
                {
                    "agent": bounded(item.get("agent", "Agent"), 80),
                    "sessionId": bounded(item.get("session_id") or item.get("sessionId"), 80),
                    "status": bounded(item.get("status", "unknown"), 24),
                    "task": bounded(item.get("task", "No task reported"), 280),
                    "reason": bounded(item.get("reason", ""), 280),
                    "nextAction": bounded(item.get("next_action") or item.get("nextAction", ""), 220),
                    "eventTime": item.get("event_time") or item.get("eventTime"),
                }
            )
        sessions = sessions[:8]
        return {
            "online": True,
            "activeCount": int(payload.get("active_count", payload.get("activeCount", 0)) or 0),
            "blockedCount": int(payload.get("blocked_count", payload.get("blockedCount", 0)) or 0),
            "securityTeamCount": len(sessions),
            "sessions": sessions,
            "collisions": payload.get("potential_collisions", [])[:4],
            "ledger": payload.get("ledger", {"ok": False, "checked": 0, "head": "unknown"}),
        }

    def snapshot(self, fresh: bool = False) -> dict[str, Any]:
        with self._snapshot_lock:
            if not fresh and self._snapshot_cache and time.monotonic() - self._snapshot_cache[0] < 2.0:
                return self._snapshot_cache[1]
            readiness = self._readiness()
            gates = self._gates()
            data = {
                "generatedAt": utc_now(),
                "deployment": {
                    "mode": self.mode,
                    "controlsEnabled": self.controls_enabled,
                    "streamingEnabled": self.mode == "operator",
                    "authentication": (
                        "cloudflare-access"
                        if self.require_access_header
                        else ("public-read-only" if self.mode == "demo" else "local-loopback")
                    ),
                    "dataClass": (
                        "redacted-manifests-and-synthetic-agent-feed"
                        if self.mode == "demo"
                        else "live-local-operational-data"
                    ),
                },
                "program": {
                    "name": "AEGIS SECURITY PROGRAM",
                    "documentVersion": "1.3",
                    **readiness,
                },
                "repo": self._git(),
                "gates": gates,
                "teams": self._teams(gates["engineering"]),
                "agents": self._observer(),
                "runs": self.list_runs(12) if self.mode == "operator" else [],
                "activity": self.audit.recent(16) if self.mode == "operator" else [],
                "controlLedger": (
                    self.audit.verify()
                    if self.mode == "operator"
                    else {"ok": True, "entries": 0, "head": "PUBLIC-DEMO-REDACTED"}
                ),
            }
            self._snapshot_cache = (time.monotonic(), data)
            return data

    def list_runs(self, limit: int = 30) -> list[dict[str, Any]]:
        with self._runs_lock:
            runs = sorted(self.runs.values(), key=lambda item: item.requested_at, reverse=True)
            return [run.public() for run in runs[:limit]]

    def start_run(
        self,
        gate_id: str,
        mode: str,
        confirmed: bool = False,
        actor: str = "local-operator",
    ) -> GateRun:
        if not self.controls_enabled:
            raise PermissionError("public demo mode is read-only")
        manifest = self.gate_manifest
        if mode not in {"engineering", "assurance"}:
            raise ValueError("mode must be engineering or assurance")

        allowed = manifest.get("engineering_gates" if mode == "engineering" else "assurance_gates", [])
        gate_map = {str(gate.get("id")): gate for gate in allowed}
        if mode == "engineering" and gate_id == "all":
            gate_name = "All engineering gates"
        elif gate_id in gate_map:
            gate_name = str(gate_map[gate_id].get("name", gate_id))
        else:
            raise ValueError("gate ID is not present in the authoritative manifest")
        if mode == "assurance" and not confirmed:
            raise PermissionError("assurance checks require explicit confirmation")

        with self._runs_lock:
            if any(run.status in {"queued", "running"} for run in self.runs.values()):
                raise RuntimeError("a gate run is already active")
            run = GateRun(str(uuid.uuid4()), gate_id, gate_name, mode)
            self.runs[run.id] = run

        self.audit.append(
            "run.requested",
            f"Requested {gate_name}",
            gate_id=gate_id,
            mode=mode,
            actor=actor,
        )
        threading.Thread(target=self._execute, args=(run,), daemon=True, name=f"gate-{run.id[:8]}").start()
        return run

    def _execute(self, run: GateRun) -> None:
        started = time.monotonic()
        run.started_at = utc_now()
        run.status = "running"
        argv = [sys.executable, "00-shared/tools/run_ci.py", "--json"]
        if run.mode == "assurance":
            argv.append("--assurance")
        elif run.gate_id != "all":
            argv.extend(["--gate", run.gate_id])
        code, output = run_process(argv, self.root, timeout=900.0)
        run.return_code = code
        run.output = bounded(output, MAX_OUTPUT)
        run.elapsed_seconds = round(time.monotonic() - started, 2)
        run.finished_at = utc_now()
        run.status = "passed" if code == 0 else "failed"
        self.audit.append(
            "run.completed",
            f"{run.gate_name}: {run.status}",
            gate_id=run.gate_id,
            mode=run.mode,
            return_code=code,
            elapsed_seconds=run.elapsed_seconds,
        )
        with self._snapshot_lock:
            self._snapshot_cache = None


class Handler(BaseHTTPRequestHandler):
    control: MissionControl
    server_version = "AEGIS-Mission-Control/1.0"

    def handle(self) -> None:
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            # Browsers cancel their long-lived SSE socket during navigation or close.
            # That is a normal disconnect, not a server fault worth a traceback.
            return

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stderr.write(f"[{self.log_date_time_string()}] {fmt % args}\n")

    def _security_headers(self) -> None:
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
            "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
            "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
        )
        self.send_header("Strict-Transport-Security", "max-age=31536000; includeSubDomains")

    def _json(self, status: int, payload: Any) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)

    def _same_origin(self) -> bool:
        origin = self.headers.get("Origin")
        if not origin:
            return True
        parsed = urllib.parse.urlparse(origin)
        host = self.headers.get("Host", "").lower()
        return parsed.scheme in {"http", "https"} and parsed.netloc.lower() == host

    def _access_authorized(self) -> bool:
        if not self.control.require_access_header:
            return True
        return bool(self.headers.get("Cf-Access-Jwt-Assertion", "").strip())

    def _identity(self) -> str:
        email = bounded(self.headers.get("Cf-Access-Authenticated-User-Email"), 160)
        if email:
            return f"access:{email}"
        address = bounded(self.headers.get("CF-Connecting-IP") or self.client_address[0], 80)
        return f"network:{address}"

    def _body(self) -> dict[str, Any]:
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if size <= 0 or size > MAX_BODY:
            raise ValueError("request body must be between 1 and 4096 bytes")
        try:
            value = json.loads(self.rfile.read(size).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("request body must be valid JSON") from exc
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if path == "/api/health":
            return self._json(
                200,
                {
                    "status": "ok",
                    "service": "aegis-mission-control",
                    "mode": self.control.mode,
                    "accessHeaderRequired": self.control.require_access_header,
                    "at": utc_now(),
                },
            )
        if path.startswith("/api/") and not self._access_authorized():
            return self._json(401, {"error": "a validated Cloudflare Access assertion is required"})
        if path == "/api/snapshot":
            return self._json(200, self.control.snapshot())
        if path == "/api/runs":
            return self._json(200, {"runs": self.control.list_runs()})
        if path == "/api/activity":
            return self._json(
                200,
                {"activity": self.control.audit.recent(50), "ledger": self.control.audit.verify()},
            )
        if path == "/api/stream":
            return self._stream()
        return self._static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = urllib.parse.urlparse(self.path).path
        if not self._access_authorized():
            return self._json(401, {"error": "a validated Cloudflare Access assertion is required"})
        if not self._same_origin():
            return self._json(403, {"error": "cross-origin control requests are forbidden"})
        if path != "/api/runs":
            return self._json(404, {"error": "not found"})
        identity = self._identity()
        if not self.control.allow_control_request(identity):
            return self._json(429, {"error": "control request rate limit exceeded"})
        try:
            data = self._body()
            run = self.control.start_run(
                bounded(data.get("gateId"), 64),
                bounded(data.get("mode", "engineering"), 24),
                data.get("confirmation") == "RUN_FAIL_CLOSED_READINESS_CHECK",
                actor=identity,
            )
            return self._json(202, {"run": run.public()})
        except PermissionError as exc:
            return self._json(403, {"error": str(exc)})
        except RuntimeError as exc:
            return self._json(409, {"error": str(exc)})
        except ValueError as exc:
            return self._json(400, {"error": str(exc)})

    def _stream(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()
        try:
            for _ in range(180):
                payload = json.dumps(self.control.snapshot(), separators=(",", ":"), ensure_ascii=False)
                self.wfile.write(f"event: snapshot\ndata: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
                time.sleep(4)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            return

    def _static(self, request_path: str) -> None:
        if not self.control.dist.exists():
            return self._json(
                503,
                {"error": "web build is missing", "action": "run npm install && npm run build in mission-control/web"},
            )
        relative = "index.html" if request_path in {"", "/"} else request_path.lstrip("/")
        candidate = (self.control.dist / relative).resolve()
        try:
            candidate.relative_to(self.control.dist)
        except ValueError:
            return self._json(404, {"error": "not found"})
        if not candidate.is_file():
            candidate = self.control.dist / "index.html"
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header(
            "Cache-Control",
            "no-cache, no-transform" if candidate.name == "index.html" else "public, max-age=31536000, immutable",
        )
        self._security_headers()
        self.end_headers()
        self.wfile.write(body)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AEGIS Mission Control")
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default: loopback)")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--dist", type=Path, default=DEFAULT_DIST)
    parser.add_argument(
        "--mode",
        choices=("operator", "demo"),
        default="operator",
        help="operator enables controls; demo redacts data and is read-only",
    )
    parser.add_argument(
        "--require-access-header",
        action="store_true",
        help="require Cf-Access-Jwt-Assertion on API requests (use with cloudflared Protect with Access)",
    )
    args = parser.parse_args(argv)

    allow_demo_container = args.mode == "demo" and os.getenv("AEGIS_ALLOW_DEMO_BIND") == "1"
    if args.host not in {"127.0.0.1", "localhost", "::1"} and not allow_demo_container:
        print("Refusing non-loopback bind. Add authentication before exposing this control plane.", file=sys.stderr)
        return 2
    control = MissionControl(
        args.root,
        args.dist,
        mode=args.mode,
        require_access_header=args.require_access_header,
    )
    Handler.control = control
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"AEGIS Mission Control ready: http://{args.host}:{args.port}")
    print(f"Mode: {args.mode}. Access header required: {args.require_access_header}.")
    print("Local-only origin. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
