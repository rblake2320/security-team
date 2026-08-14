"""Transactional evidence store and tamper-evident audit chain."""

from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from .canonical import canonical_json, digest, normalize
from .errors import IntegrityError, ValidationError
from .models import Alert, Event

SCHEMA_VERSION = 1


class EvidenceStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.connection.execute("PRAGMA synchronous = FULL")
        self.connection.execute("PRAGMA busy_timeout = 10000")
        self._initialize()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> EvidenceStore:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    @contextmanager
    def transaction(self) -> Iterator[None]:
        self.connection.execute("BEGIN IMMEDIATE")
        try:
            yield
        except Exception:
            self.connection.execute("ROLLBACK")
            raise
        else:
            self.connection.execute("COMMIT")

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS events (
                event_id TEXT PRIMARY KEY,
                event_time TEXT NOT NULL,
                ingested_at TEXT NOT NULL,
                source TEXT NOT NULL,
                event_type TEXT NOT NULL,
                host TEXT NOT NULL,
                user_name TEXT,
                event_json TEXT NOT NULL,
                event_hash TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS events_time_idx ON events(event_time);
            CREATE INDEX IF NOT EXISTS events_source_host_idx ON events(source, host, event_time);
            CREATE TABLE IF NOT EXISTS alerts (
                alert_id TEXT PRIMARY KEY,
                rule_id TEXT NOT NULL,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                created_at TEXT NOT NULL,
                host TEXT NOT NULL,
                user_name TEXT,
                event_ids_json TEXT NOT NULL,
                techniques_json TEXT NOT NULL,
                evidence_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','triaged','contained','closed'))
            );
            CREATE INDEX IF NOT EXISTS alerts_status_idx ON alerts(status, created_at);
            CREATE TABLE IF NOT EXISTS suppressions (
                rule_id TEXT NOT NULL,
                group_key TEXT NOT NULL,
                last_alert_at TEXT NOT NULL,
                PRIMARY KEY(rule_id, group_key)
            );
            CREATE TABLE IF NOT EXISTS sensor_health (
                sensor_key TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                host TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                last_event_time TEXT NOT NULL,
                last_event_id TEXT NOT NULL REFERENCES events(event_id)
            );
            CREATE TABLE IF NOT EXISTS correlation_hits (
                rule_key TEXT NOT NULL,
                group_key TEXT NOT NULL,
                event_time TEXT NOT NULL,
                event_id TEXT NOT NULL REFERENCES events(event_id),
                PRIMARY KEY(rule_key, group_key, event_id)
            );
            CREATE INDEX IF NOT EXISTS correlation_window_idx
                ON correlation_hits(rule_key, group_key, event_time);
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('open','investigating','contained','recovered','closed')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS case_alerts (
                case_id TEXT NOT NULL REFERENCES cases(case_id),
                alert_id TEXT NOT NULL REFERENCES alerts(alert_id),
                PRIMARY KEY(case_id, alert_id)
            );
            CREATE TABLE IF NOT EXISTS audit_chain (
                sequence INTEGER PRIMARY KEY,
                recorded_at TEXT NOT NULL,
                kind TEXT NOT NULL,
                subject TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL UNIQUE
            );
            """
        )
        row = self.connection.execute("SELECT value FROM metadata WHERE key = 'schema_version'").fetchone()
        if row and int(row["value"]) != SCHEMA_VERSION:
            raise IntegrityError("database schema version is unsupported")
        self.connection.execute(
            "INSERT OR IGNORE INTO metadata(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),)
        )
        self.connection.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES ('audit_count', '0')")
        self.connection.execute("INSERT OR IGNORE INTO metadata(key, value) VALUES ('audit_head', ?)", ("0" * 64,))

    def _append_audit(self, kind: str, subject: str, payload: dict[str, Any]) -> str:
        prior = self.connection.execute(
            "SELECT sequence, entry_hash FROM audit_chain ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        sequence = int(prior["sequence"]) + 1 if prior else 1
        previous_hash = prior["entry_hash"] if prior else "0" * 64
        recorded_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        payload_json = canonical_json(payload)
        entry = {
            "sequence": sequence,
            "recorded_at": recorded_at,
            "kind": kind,
            "subject": subject,
            "payload": json.loads(payload_json),
            "previous_hash": previous_hash,
        }
        entry_hash = digest(entry)
        self.connection.execute(
            """INSERT INTO audit_chain(
                sequence, recorded_at, kind, subject, payload_json, previous_hash, entry_hash
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sequence, recorded_at, kind, subject, payload_json, previous_hash, entry_hash),
        )
        self.connection.execute("UPDATE metadata SET value = ? WHERE key = 'audit_count'", (str(sequence),))
        self.connection.execute("UPDATE metadata SET value = ? WHERE key = 'audit_head'", (entry_hash,))
        return entry_hash

    def add_event(self, event: Event) -> bool:
        record = event.as_record()
        event_json = canonical_json(record)
        event_hash = digest(record)
        with self.transaction():
            existing = self.connection.execute(
                "SELECT event_hash FROM events WHERE event_id = ?", (event.event_id,)
            ).fetchone()
            if existing:
                if existing["event_hash"] != event_hash:
                    raise IntegrityError("event ID was replayed with different content")
                return False
            now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            event_time = record["timestamp"]
            self.connection.execute(
                """INSERT INTO events(
                    event_id, event_time, ingested_at, source, event_type, host,
                    user_name, event_json, event_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    event.event_id,
                    event_time,
                    now,
                    event.source,
                    event.event_type,
                    event.host,
                    event.user,
                    event_json,
                    event_hash,
                ),
            )
            sensor_key = f"{event.source.casefold()}::{event.host.casefold()}"
            self.connection.execute(
                """INSERT INTO sensor_health(sensor_key, source, host, last_seen, last_event_time, last_event_id)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(sensor_key) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    -- AUD-04: time and id must move as ONE pair. Updating the id
                    -- unconditionally let a late, older event overwrite the id while
                    -- the timestamp kept the newer value, pairing a timestamp with
                    -- the wrong event.
                    last_event_time = CASE WHEN excluded.last_event_time > sensor_health.last_event_time
                                           THEN excluded.last_event_time ELSE sensor_health.last_event_time END,
                    last_event_id = CASE WHEN excluded.last_event_time > sensor_health.last_event_time
                                         THEN excluded.last_event_id ELSE sensor_health.last_event_id END""",
                (sensor_key, event.source, event.host, now, event_time, event.event_id),
            )
            self._append_audit("event_ingested", event.event_id, {"event_hash": event_hash})
        return True

    def recent_events(self, start: datetime, end: datetime) -> list[Event]:
        rows = self.connection.execute(
            "SELECT event_json FROM events WHERE event_time >= ? AND event_time <= ? ORDER BY event_time, event_id",
            (
                start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
                end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            ),
        ).fetchall()
        return [Event.from_dict(json.loads(row["event_json"])) for row in rows]

    def suppression_active(self, rule_id: str, group_key: str, now: datetime, seconds: int) -> bool:
        if seconds <= 0:
            return False
        row = self.connection.execute(
            "SELECT last_alert_at FROM suppressions WHERE rule_id = ? AND group_key = ?", (rule_id, group_key)
        ).fetchone()
        if not row:
            return False
        prior = datetime.fromisoformat(row["last_alert_at"].replace("Z", "+00:00"))
        return now - prior < timedelta(seconds=seconds)

    def record_correlation_hit(
        self,
        *,
        rule_key: str,
        group_key: str,
        event: Event,
        within_seconds: int,
        maximum: int = 10_000,
    ) -> list[str]:
        start = (event.timestamp - timedelta(seconds=within_seconds)).isoformat().replace("+00:00", "Z")
        end = event.timestamp.isoformat().replace("+00:00", "Z")
        with self.transaction():
            self.connection.execute(
                "INSERT OR IGNORE INTO correlation_hits(rule_key, group_key, event_time, event_id) VALUES (?, ?, ?, ?)",
                (rule_key, group_key, end, event.event_id),
            )
            self.connection.execute(
                "DELETE FROM correlation_hits WHERE rule_key = ? AND group_key = ? AND event_time < ?",
                (rule_key, group_key, start),
            )
            rows = self.connection.execute(
                """SELECT event_id FROM correlation_hits
                   WHERE rule_key = ? AND group_key = ? AND event_time >= ? AND event_time <= ?
                   ORDER BY event_time DESC, event_id DESC LIMIT ?""",
                (rule_key, group_key, start, end, max(1, min(maximum, 10_000))),
            ).fetchall()
        return [row["event_id"] for row in reversed(rows)]

    def add_alert(self, alert: Alert, group_key: str) -> None:
        with self.transaction():
            self.connection.execute(
                """INSERT INTO alerts(
                    alert_id, rule_id, title, severity, created_at, host, user_name,
                    event_ids_json, techniques_json, evidence_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    alert.alert_id,
                    alert.rule_id,
                    alert.title,
                    alert.severity,
                    alert.created_at.isoformat().replace("+00:00", "Z"),
                    alert.host,
                    alert.user,
                    canonical_json(list(alert.event_ids)),
                    canonical_json(list(alert.techniques)),
                    canonical_json(alert.evidence),
                ),
            )
            self.connection.execute(
                """INSERT INTO suppressions(rule_id, group_key, last_alert_at) VALUES (?, ?, ?)
                ON CONFLICT(rule_id, group_key) DO UPDATE SET last_alert_at = excluded.last_alert_at""",
                (alert.rule_id, group_key, alert.created_at.isoformat().replace("+00:00", "Z")),
            )
            self._append_audit(
                "alert_created",
                alert.alert_id,
                {"rule_id": alert.rule_id, "event_ids": list(alert.event_ids), "severity": alert.severity},
            )

    def list_alerts(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self.connection.execute(
            """SELECT alert_id, rule_id, title, severity, created_at, host, user_name,
                      event_ids_json, techniques_json, evidence_json, status
               FROM alerts ORDER BY created_at DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
        return [
            {
                "alert_id": row["alert_id"],
                "rule_id": row["rule_id"],
                "title": row["title"],
                "severity": row["severity"],
                "created_at": row["created_at"],
                "host": row["host"],
                "user": row["user_name"],
                "event_ids": json.loads(row["event_ids_json"]),
                "techniques": json.loads(row["techniques_json"]),
                "evidence": json.loads(row["evidence_json"]),
                "status": row["status"],
            }
            for row in rows
        ]

    def get_alert(self, alert_id: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            """SELECT alert_id, rule_id, title, severity, created_at, host, user_name,
                      event_ids_json, techniques_json, evidence_json, status
               FROM alerts WHERE alert_id = ?""",
            (alert_id,),
        ).fetchone()
        if not row:
            return None
        return {
            "alert_id": row["alert_id"],
            "rule_id": row["rule_id"],
            "title": row["title"],
            "severity": row["severity"],
            "created_at": row["created_at"],
            "host": row["host"],
            "user": row["user_name"],
            "event_ids": json.loads(row["event_ids_json"]),
            "techniques": json.loads(row["techniques_json"]),
            "evidence": json.loads(row["evidence_json"]),
            "status": row["status"],
        }

    def create_case(self, alert_id: str, title: str) -> dict[str, Any]:
        alert = self.get_alert(alert_id)
        if not alert:
            raise IntegrityError("alert does not exist")
        clean_title = normalize(title)
        if not isinstance(clean_title, str) or not clean_title.strip() or len(clean_title) > 200:
            raise ValidationError("case title must contain 1 through 200 characters")
        clean_title = clean_title.strip()
        case_id = str(uuid.uuid4())
        now = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        with self.transaction():
            self.connection.execute(
                """INSERT INTO cases(case_id, title, severity, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'open', ?, ?)""",
                (case_id, clean_title, alert["severity"], now, now),
            )
            self.connection.execute(
                "INSERT INTO case_alerts(case_id, alert_id) VALUES (?, ?)", (case_id, alert_id)
            )
            self._append_audit("case_created", case_id, {"alert_id": alert_id, "severity": alert["severity"]})
        return {
            "case_id": case_id,
            "title": clean_title,
            "severity": alert["severity"],
            "status": "open",
            "alert_id": alert_id,
        }

    def list_cases(self, *, limit: int = 100) -> list[dict[str, Any]]:
        safe_limit = max(1, min(int(limit), 1000))
        rows = self.connection.execute(
            """SELECT c.case_id, c.title, c.severity, c.status, c.created_at, c.updated_at,
                      GROUP_CONCAT(ca.alert_id) AS alert_ids
               FROM cases c LEFT JOIN case_alerts ca ON ca.case_id = c.case_id
               GROUP BY c.case_id ORDER BY c.updated_at DESC LIMIT ?""",
            (safe_limit,),
        ).fetchall()
        return [
            {
                "case_id": row["case_id"],
                "title": row["title"],
                "severity": row["severity"],
                "status": row["status"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                "alert_ids": row["alert_ids"].split(",") if row["alert_ids"] else [],
            }
            for row in rows
        ]

    def sensor_rows(self) -> list[dict[str, str]]:
        rows = self.connection.execute(
            "SELECT source, host, last_seen, last_event_time, last_event_id FROM sensor_health ORDER BY source, host"
        ).fetchall()
        return [dict(row) for row in rows]

    def verify_audit_chain(self) -> dict[str, Any]:
        rows = self.connection.execute(
            """SELECT sequence, recorded_at, kind, subject, payload_json, previous_hash, entry_hash
               FROM audit_chain ORDER BY sequence"""
        ).fetchall()
        previous_hash = "0" * 64
        for expected_sequence, row in enumerate(rows, start=1):
            if row["sequence"] != expected_sequence:
                raise IntegrityError(f"audit sequence gap at {expected_sequence}")
            if row["previous_hash"] != previous_hash:
                raise IntegrityError(f"audit predecessor mismatch at {expected_sequence}")
            entry = {
                "sequence": row["sequence"],
                "recorded_at": row["recorded_at"],
                "kind": row["kind"],
                "subject": row["subject"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
            }
            calculated = digest(entry)
            if calculated != row["entry_hash"]:
                raise IntegrityError(f"audit entry hash mismatch at {expected_sequence}")
            previous_hash = calculated
        metadata = dict(
            self.connection.execute(
                "SELECT key, value FROM metadata WHERE key IN ('audit_count', 'audit_head')"
            ).fetchall()
        )
        if int(metadata.get("audit_count", -1)) != len(rows):
            raise IntegrityError("audit entry count disagrees with the remembered head")
        if metadata.get("audit_head") != previous_hash:
            raise IntegrityError("audit head disagrees with the remembered head")
        return {"valid": True, "entries": len(rows), "head": previous_hash}
