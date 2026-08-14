"""Telemetry freshness and blind-spot reporting."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .errors import ConfigurationError
from .store import EvidenceStore


def load_sensor_policy(path: str | Path) -> list[dict[str, Any]]:
    try:
        records = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigurationError("sensor policy is unreadable") from exc
    if not isinstance(records, list):
        raise ConfigurationError("sensor policy must be a list")
    seen: set[tuple[str, str]] = set()
    for record in records:
        if not isinstance(record, dict) or not isinstance(record.get("source"), str):
            raise ConfigurationError("sensor policy entry is invalid")
        if not isinstance(record.get("max_age_seconds"), int) or record["max_age_seconds"] < 1:
            raise ConfigurationError("sensor freshness budget is invalid")
        key = (record["source"].casefold(), str(record.get("host", "*")).casefold())
        if key in seen:
            raise ConfigurationError("sensor policy contains a duplicate source/host contract")
        seen.add(key)
    return records


def health_report(store: EvidenceStore, policy: list[dict[str, Any]], *, now: datetime | None = None) -> dict[str, Any]:
    current = (now or datetime.now(UTC)).astimezone(UTC)
    rows = store.sensor_rows()
    findings: list[dict[str, Any]] = []
    for expected in policy:
        source = expected["source"]
        host_pattern = expected.get("host", "*")
        matching = [
            row
            for row in rows
            if row["source"].casefold() == source.casefold()
            and (host_pattern == "*" or row["host"].casefold() == str(host_pattern).casefold())
        ]
        if not matching:
            findings.append({"source": source, "host": host_pattern, "status": "missing", "age_seconds": None})
            continue
        for row in matching:
            last_seen = datetime.fromisoformat(row["last_seen"].replace("Z", "+00:00")).astimezone(UTC)
            age = max(0, int((current - last_seen).total_seconds()))
            status = "healthy" if age <= expected["max_age_seconds"] else "stale"
            findings.append({"source": source, "host": row["host"], "status": status, "age_seconds": age})
    unhealthy = [item for item in findings if item["status"] != "healthy"]
    return {
        "status": "healthy" if not unhealthy else "degraded",
        "checked_at": current.isoformat().replace("+00:00", "Z"),
        "sensors": findings,
        "blind_spots": unhealthy,
    }
