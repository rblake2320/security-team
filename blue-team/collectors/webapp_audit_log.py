#!/usr/bin/env python3
"""Collector: web application audit log -> Sentinel Blue events.

Blue's rule content is written against host and identity telemetry. A modern web
application's richest security signal is usually its own request audit log, which
no host collector can see: application-level authorization outcomes, moderation
decisions, and refused submissions exist only above the OS.

This collector normalizes such a log into Blue's event schema. It was written
against aihangout.ai's `activity_log` table (Cloudflare Worker + D1) and is
deliberately generic: any source producing rows with method/path/outcome/status
can be mapped by adjusting FIELD_MAP rather than rewriting the translation.

Design rule, and the reason this is worth committing rather than improvising each
time: the mapping is CONSERVATIVE. An event is only given a specific security
event_type when the mapping is semantically honest. A 401 on a login route
genuinely is an authentication failure. A 403 on an admin route genuinely is an
unauthorized privileged attempt. Everything else passes through as `api_request`,
so it still contributes to volume and coverage without being asserted as
something it is not. Detection content built on a generous mapping produces
confident alerts about events that never happened.

Usage:
    python collectors/webapp_audit_log.py --rows rows.json --output events.jsonl
    python collectors/webapp_audit_log.py --rows rows.json --host aihangout.ai --source app.activity_log
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Column names in the source rows. Override for a different application.
FIELD_MAP = {
    "id": "id",
    "occurred_at": "occurred_at",
    "method": "method",
    "path": "path",
    "action": "action",
    "username": "username",
    "outcome": "outcome",
    "http_status": "http_status",
    "reason": "reason",
    "target_type": "target_type",
    "target_id": "target_id",
    "quarantined": "quarantined",
    "ip_hash": "ip_hash",
}

AUTH_PREFIXES = ("/api/auth/login",)
REGISTER_PREFIXES = ("/api/auth/register",)
ADMIN_PREFIXES = ("/api/admin/",)

# Severity is Blue's 1-5 scale. Quarantined rows are the ones a reviewer should
# reach first, so they arrive pre-elevated rather than needing a rule to notice.
SEVERITY_QUARANTINED = 3
SEVERITY_ROUTINE = 1


def classify(row: dict[str, Any]) -> str:
    path = str(row.get("path") or "")
    status = int(row.get("http_status") or 0)
    action = str(row.get("action") or "")

    if path.startswith(AUTH_PREFIXES):
        return "authentication_failed" if status >= 400 else "authentication_succeeded"
    if path.startswith(REGISTER_PREFIXES):
        return "account_created" if status < 400 else "account_creation_failed"
    if path.startswith(ADMIN_PREFIXES) and status in (401, 403):
        return "unauthorized_privileged_attempt"
    if action.endswith(".delete"):
        return "content_deleted"
    return "api_request"


def to_event(row: dict[str, Any], *, host: str, source: str) -> dict[str, Any]:
    get = lambda key: row.get(FIELD_MAP.get(key, key))  # noqa: E731
    occurred = str(get("occurred_at") or "")
    # The source stores UTC without a zone designator; Blue wants an instant.
    timestamp = occurred.replace(" ", "T")
    if timestamp and not timestamp.endswith("Z") and "+" not in timestamp:
        timestamp += "Z"
    quarantined = bool(get("quarantined"))
    return {
        "event_id": f"{source}-{get('id')}",
        "timestamp": timestamp,
        "source": source,
        "event_type": classify(row),
        "host": host,
        # For failed auth this is the identifier that was ATTEMPTED, not a
        # confirmed account: without it a brute-force alert cannot name its target.
        "user": get("username") or None,
        "severity": SEVERITY_QUARANTINED if quarantined else SEVERITY_ROUTINE,
        "attributes": {
            "method": get("method"),
            "path": get("path"),
            "action": get("action"),
            "outcome": get("outcome"),
            "http_status": get("http_status"),
            "reason": get("reason"),
            "quarantined": quarantined,
            "target_type": get("target_type"),
            "target_id": get("target_id"),
            # Never the raw address: the source stores only a salted hash.
            "ip_hash": get("ip_hash"),
        },
    }


def collect(rows: list[dict[str, Any]], *, host: str, source: str) -> list[dict[str, Any]]:
    return [to_event(row, host=host, source=source) for row in rows]


def _extract_rows(document: Any) -> list[dict[str, Any]]:
    """Accept either a plain array of rows or a raw `wrangler d1 execute --json` payload."""
    if isinstance(document, list) and document and isinstance(document[0], dict):
        if "results" in document[0]:
            return document[0]["results"]
        return document
    if isinstance(document, dict):
        if "results" in document:
            return document["results"]
        if "result" in document:
            return document["result"][0]["results"]
    raise SystemExit("could not find rows in the supplied document")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Web application audit log -> Blue events")
    parser.add_argument("--rows", required=True, help="JSON array of rows, or wrangler d1 --json output")
    parser.add_argument("--output", help="JSONL destination (default: stdout)")
    parser.add_argument("--host", default="webapp")
    parser.add_argument("--source", default="app.activity_log")
    args = parser.parse_args(argv)

    document = json.loads(Path(args.rows).read_text(encoding="utf-8"))
    events = collect(_extract_rows(document), host=args.host, source=args.source)
    lines = "\n".join(json.dumps(e) for e in events) + ("\n" if events else "")
    if args.output:
        Path(args.output).write_text(lines, encoding="utf-8")
        print(f"wrote {len(events)} events -> {args.output}")
    else:
        sys.stdout.write(lines)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
