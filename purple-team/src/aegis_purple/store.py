from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .authority import AuthorizedTransition
from .canonical import canonical_bytes, sha256
from .errors import IntegrityError, TransitionError
from .models import ALLOWED_TRANSITIONS, ROLE_TRANSITIONS, ExercisePlan, ExerciseState

SCHEMA_VERSION = 1
GENESIS = "0" * 64

DDL = """
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exercises (
    exercise_id TEXT PRIMARY KEY,
    plan_version INTEGER NOT NULL,
    plan_json TEXT NOT NULL,
    plan_sha256 TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS transitions (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    exercise_id TEXT NOT NULL REFERENCES exercises(exercise_id),
    from_state TEXT,
    to_state TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_role TEXT NOT NULL,
    reason TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    previous_sha256 TEXT NOT NULL,
    sha256 TEXT NOT NULL UNIQUE
);
CREATE TABLE IF NOT EXISTS evidence (
    evidence_id TEXT PRIMARY KEY,
    exercise_id TEXT NOT NULL REFERENCES exercises(exercise_id),
    test_case_id TEXT NOT NULL,
    artifact_sha256 TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    producer_role TEXT NOT NULL,
    media_type TEXT NOT NULL,
    collected_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS results (
    exercise_id TEXT NOT NULL REFERENCES exercises(exercise_id),
    test_case_id TEXT NOT NULL,
    stage TEXT NOT NULL CHECK(stage IN ('prevented','logged','alerted','investigated','contained','reported')),
    outcome TEXT NOT NULL CHECK(outcome IN ('pass','fail','not_applicable')),
    evidence_id TEXT NOT NULL REFERENCES evidence(evidence_id),
    observed_at TEXT NOT NULL,
    PRIMARY KEY(exercise_id, test_case_id, stage)
);
CREATE TABLE IF NOT EXISTS consumed_nonces (
    nonce TEXT PRIMARY KEY,
    key_id TEXT NOT NULL,
    exercise_id TEXT NOT NULL,
    consumed_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_evidence_exercise ON evidence(exercise_id);
CREATE INDEX IF NOT EXISTS idx_results_exercise ON results(exercise_id);
"""


class ExerciseStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, timeout=5.0)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute("PRAGMA synchronous=FULL")
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.execute("PRAGMA busy_timeout=5000")
        self.connection.executescript(DDL)
        self._initialize_meta()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> ExerciseStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _initialize_meta(self) -> None:
        with self.transaction():
            self.connection.execute("INSERT OR IGNORE INTO meta VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
            self.connection.execute("INSERT OR IGNORE INTO meta VALUES ('audit_head', ?)", (GENESIS,))
            self.connection.execute("INSERT OR IGNORE INTO meta VALUES ('audit_count', '0')")
            self.connection.execute("INSERT OR IGNORE INTO meta VALUES ('state_root', ?)", (self._state_root(),))
        version = self._meta("schema_version")
        if version != str(SCHEMA_VERSION):
            raise IntegrityError(f"unsupported database schema version: {version}")

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            yield
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def create_exercise(self, plan: ExercisePlan, *, actor_id: str) -> str:
        now = datetime.now(UTC).isoformat()
        payload = canonical_bytes(plan.to_dict()).decode("utf-8")
        with self.transaction():
            try:
                self.connection.execute(
                    "INSERT INTO exercises VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (plan.exercise_id, plan.version, payload, plan.digest, ExerciseState.FROZEN, now, now),
                )
            except sqlite3.IntegrityError as exc:
                existing = self.connection.execute(
                    "SELECT plan_sha256 FROM exercises WHERE exercise_id = ?", (plan.exercise_id,)
                ).fetchone()
                if existing and existing["plan_sha256"] == plan.digest:
                    return plan.digest
                raise TransitionError("exercise ID already exists with different frozen content") from exc
            self._append_transition(plan.exercise_id, None, ExerciseState.FROZEN, actor_id, "purple", "plan frozen")
        return plan.digest

    def transition(
        self,
        exercise_id: str,
        target: ExerciseState,
        *,
        actor_id: str,
        actor_role: str,
        reason: str,
        expected_state: ExerciseState,
    ) -> str:
        if not actor_id.strip() or len(actor_id) > 120 or not reason.strip() or len(reason) > 500:
            raise TransitionError("actor and bounded reason are required")
        with self.transaction():
            row = self.connection.execute(
                "SELECT state, plan_json, plan_sha256 FROM exercises WHERE exercise_id = ?", (exercise_id,)
            ).fetchone()
            if row is None:
                raise TransitionError("unknown exercise")
            current = ExerciseState(row["state"])
            if current != expected_state:
                raise TransitionError(f"stale transition: expected {expected_state}, found {current}")
            plan = self._verify_plan_row(row)
            if target not in ALLOWED_TRANSITIONS[current]:
                raise TransitionError(f"transition {current} -> {target} is forbidden")
            if actor_role not in ROLE_TRANSITIONS[target]:
                raise TransitionError(f"role {actor_role!r} cannot transition to {target}")
            if actor_id == plan.owner and target in {ExerciseState.AUTHORIZED, ExerciseState.EVIDENCE_VERIFIED, ExerciseState.CLOSED}:
                raise TransitionError("plan owner cannot authorize, independently verify, or close the exercise")
            if target in {ExerciseState.AUTHORIZED, ExerciseState.EXECUTING}:
                expiry = datetime.fromisoformat(plan.expires_at.replace("Z", "+00:00"))
                if expiry <= datetime.now(UTC):
                    raise TransitionError("frozen exercise plan has expired")
            if target is ExerciseState.EVIDENCE_VERIFIED:
                operators = {
                    item["actor_id"]
                    for item in self.connection.execute(
                        "SELECT actor_id FROM transitions WHERE exercise_id = ? AND to_state IN ('EXECUTING','EXECUTED')",
                        (exercise_id,),
                    )
                }
                if actor_id in operators:
                    raise TransitionError("exercise operator cannot independently verify evidence")
                self._require_complete_evidence(exercise_id)
            now = datetime.now(UTC).isoformat()
            self.connection.execute(
                "UPDATE exercises SET state = ?, updated_at = ? WHERE exercise_id = ? AND state = ?",
                (target, now, exercise_id, current),
            )
            return self._append_transition(exercise_id, current, target, actor_id, actor_role, reason)

    def apply_authorized_transition(self, command: AuthorizedTransition, *, role_trust_sha256: str) -> str:
        row = self.connection.execute(
            "SELECT plan_sha256, plan_json FROM exercises WHERE exercise_id = ?", (command.exercise_id,)
        ).fetchone()
        if row is None or row["plan_sha256"] != command.plan_sha256:
            raise TransitionError("signed transition is not bound to the frozen plan")
        plan = ExercisePlan.from_dict(json.loads(row["plan_json"]))
        if plan.role_trust_sha256 != role_trust_sha256:
            raise TransitionError("role trust registry does not match the registry pinned in the frozen plan")
        if self.connection.execute("SELECT 1 FROM consumed_nonces WHERE nonce = ?", (command.nonce,)).fetchone():
            raise TransitionError("transition authorization nonce was already consumed")
        digest = self.transition(
            command.exercise_id, command.to_state, actor_id=command.actor_id,
            actor_role=command.actor_role, reason=command.reason, expected_state=command.from_state,
        )
        try:
            with self.transaction():
                self.connection.execute(
                    "INSERT INTO consumed_nonces VALUES (?, ?, ?, ?)",
                    (command.nonce, command.key_id, command.exercise_id, datetime.now(UTC).isoformat()),
                )
                self._update_state_root()
        except sqlite3.IntegrityError as exc:
            raise TransitionError("transition authorization nonce was already consumed") from exc
        return digest

    def add_evidence(
        self,
        exercise_id: str,
        *,
        evidence_id: str,
        test_case_id: str,
        artifact_sha256: str,
        producer_id: str,
        producer_role: str,
        media_type: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if not artifact_sha256 or len(artifact_sha256) != 64 or any(c not in "0123456789abcdef" for c in artifact_sha256):
            raise IntegrityError("artifact_sha256 must be lowercase SHA-256")
        if producer_role not in {"red", "blue", "green", "purple", "white", "exercise_assurance", "system"}:
            raise IntegrityError("unknown evidence producer role")
        with self.transaction():
            row = self.connection.execute(
                "SELECT state, plan_json, plan_sha256 FROM exercises WHERE exercise_id = ?", (exercise_id,)
            ).fetchone()
            if row is None:
                raise IntegrityError("unknown exercise")
            state = ExerciseState(row["state"])
            if state not in {ExerciseState.EXECUTING, ExerciseState.EXECUTED}:
                raise IntegrityError("evidence can only be added during or immediately after execution")
            plan = self._verify_plan_row(row)
            if test_case_id not in {item.test_case_id for item in plan.test_cases}:
                raise IntegrityError("evidence references a test case outside the frozen plan")
            try:
                self.connection.execute(
                    "INSERT INTO evidence VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        evidence_id, exercise_id, test_case_id, artifact_sha256, producer_id,
                        producer_role, media_type, datetime.now(UTC).isoformat(),
                        canonical_bytes(metadata or {}).decode("utf-8"),
                    ),
                )
                self._update_state_root()
            except sqlite3.IntegrityError as exc:
                raise IntegrityError("duplicate or invalid evidence record") from exc

    def record_result(
        self,
        exercise_id: str,
        *,
        test_case_id: str,
        stage: str,
        outcome: str,
        evidence_id: str,
    ) -> None:
        with self.transaction():
            row = self.connection.execute("SELECT state FROM exercises WHERE exercise_id = ?", (exercise_id,)).fetchone()
            if row is None or ExerciseState(row["state"]) not in {ExerciseState.EXECUTING, ExerciseState.EXECUTED}:
                raise IntegrityError("results can only be recorded during or immediately after execution")
            evidence = self.connection.execute(
                "SELECT test_case_id FROM evidence WHERE evidence_id = ? AND exercise_id = ?",
                (evidence_id, exercise_id),
            ).fetchone()
            if evidence is None or evidence["test_case_id"] != test_case_id:
                raise IntegrityError("result evidence must belong to the same exercise and test case")
            try:
                self.connection.execute(
                    "INSERT INTO results VALUES (?, ?, ?, ?, ?, ?)",
                    (exercise_id, test_case_id, stage, outcome, evidence_id, datetime.now(UTC).isoformat()),
                )
                self._update_state_root()
            except sqlite3.IntegrityError as exc:
                raise IntegrityError("duplicate or invalid six-stage result") from exc

    def verify(self) -> dict[str, Any]:
        rows = self.connection.execute("SELECT * FROM transitions ORDER BY sequence").fetchall()
        previous = GENESIS
        for expected_sequence, row in enumerate(rows, 1):
            if row["sequence"] != expected_sequence or row["previous_sha256"] != previous:
                raise IntegrityError(f"audit chain broken at sequence {expected_sequence}")
            payload = {key: row[key] for key in row.keys() if key not in {"sha256"}}
            actual = sha256(payload)
            if actual != row["sha256"]:
                raise IntegrityError(f"audit hash mismatch at sequence {expected_sequence}")
            previous = actual
        if self._meta("audit_head") != previous or int(self._meta("audit_count")) != len(rows):
            raise IntegrityError("audit tail deletion or head rollback detected")
        for row in self.connection.execute("SELECT plan_json, plan_sha256 FROM exercises"):
            self._verify_plan_row(row)
        state_root = self._state_root()
        if self._meta("state_root") != state_root:
            raise IntegrityError("exercise, evidence, result, or replay state was modified")
        return {
            "valid": True, "entries": len(rows), "head": previous,
            "state_root": state_root, "schema_version": SCHEMA_VERSION,
        }

    def export_anchor(self) -> dict[str, Any]:
        verified = self.verify()
        return {
            "schema": "aegis.purple.audit-anchor/1.0",
            "audit_head": verified["head"],
            "audit_entries": verified["entries"],
            "state_root": verified["state_root"],
            "exported_at": datetime.now(UTC).isoformat(),
            "limitation": "This anchor is independent only after publication to a separately administered append-only store.",
        }

    def status(self, exercise_id: str) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT exercise_id, plan_version, plan_sha256, state, created_at, updated_at FROM exercises WHERE exercise_id = ?",
            (exercise_id,),
        ).fetchone()
        if row is None:
            raise TransitionError("unknown exercise")
        result = dict(row)
        result["evidence_count"] = self.connection.execute(
            "SELECT COUNT(*) FROM evidence WHERE exercise_id = ?", (exercise_id,)
        ).fetchone()[0]
        result["result_count"] = self.connection.execute(
            "SELECT COUNT(*) FROM results WHERE exercise_id = ?", (exercise_id,)
        ).fetchone()[0]
        return result

    def _require_complete_evidence(self, exercise_id: str) -> None:
        row = self.connection.execute("SELECT plan_json FROM exercises WHERE exercise_id = ?", (exercise_id,)).fetchone()
        plan = ExercisePlan.from_dict(json.loads(row["plan_json"]))
        stages = {"prevented", "logged", "alerted", "investigated", "contained", "reported"}
        for test_case in plan.test_cases:
            observed = {
                item["stage"]
                for item in self.connection.execute(
                    "SELECT stage FROM results WHERE exercise_id = ? AND test_case_id = ?",
                    (exercise_id, test_case.test_case_id),
                )
            }
            if observed != stages:
                raise TransitionError(f"incomplete six-stage evidence for {test_case.test_case_id}")

    def _verify_plan_row(self, row: sqlite3.Row) -> ExercisePlan:
        try:
            raw = json.loads(row["plan_json"])
            plan = ExercisePlan.from_dict(raw)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise IntegrityError("stored frozen plan is malformed") from exc
        if plan.digest != row["plan_sha256"]:
            raise IntegrityError("stored frozen plan was modified")
        return plan

    def _append_transition(
        self,
        exercise_id: str,
        from_state: ExerciseState | None,
        to_state: ExerciseState,
        actor_id: str,
        actor_role: str,
        reason: str,
    ) -> str:
        previous = self._meta("audit_head")
        sequence = int(self._meta("audit_count")) + 1
        payload = {
            "sequence": sequence,
            "exercise_id": exercise_id,
            "from_state": None if from_state is None else str(from_state),
            "to_state": str(to_state),
            "actor_id": actor_id,
            "actor_role": actor_role,
            "reason": reason,
            "timestamp": datetime.now(UTC).isoformat(),
            "previous_sha256": previous,
        }
        digest = sha256(payload)
        self.connection.execute(
            "INSERT INTO transitions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                sequence, exercise_id, payload["from_state"], payload["to_state"], actor_id,
                actor_role, reason, payload["timestamp"], previous, digest,
            ),
        )
        self.connection.execute("UPDATE meta SET value = ? WHERE key = 'audit_head'", (digest,))
        self.connection.execute("UPDATE meta SET value = ? WHERE key = 'audit_count'", (str(sequence),))
        self._update_state_root()
        return digest

    def _state_root(self) -> str:
        tables = {
            "exercises": ("exercise_id",),
            "evidence": ("evidence_id",),
            "results": ("exercise_id", "test_case_id", "stage"),
            "consumed_nonces": ("nonce",),
        }
        snapshot: dict[str, list[dict[str, Any]]] = {}
        for table, order in tables.items():
            ordering = ", ".join(order)
            snapshot[table] = [dict(row) for row in self.connection.execute(f"SELECT * FROM {table} ORDER BY {ordering}")]
        return sha256(snapshot)

    def _update_state_root(self) -> None:
        root = self._state_root()
        self.connection.execute(
            "INSERT INTO meta(key, value) VALUES ('state_root', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (root,),
        )

    def _meta(self, key: str) -> str:
        row = self.connection.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if row is None:
            raise IntegrityError(f"missing store metadata: {key}")
        return str(row["value"])
