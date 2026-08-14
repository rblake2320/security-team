"""Operator CLI for Sentinel Blue."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from .assurance import validate_configuration
from .canonical import MAX_EVENT_BYTES, loads_bounded
from .coverage import coverage_report, load_coverage_target
from .detection import DetectionEngine, load_rules, verify_rule_manifest
from .errors import BlueTeamError
from .health import health_report, load_sensor_policy
from .models import Event
from .response import load_playbooks, response_plan
from .source_auth import load_trust_policy, verify_envelope
from .store import EvidenceStore

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RULES = PROJECT_ROOT / "rules"
DEFAULT_COVERAGE = PROJECT_ROOT / "config" / "coverage_target.json"
DEFAULT_SENSORS = PROJECT_ROOT / "config" / "sensor_policy.json"
DEFAULT_PLAYBOOKS = PROJECT_ROOT / "playbooks" / "playbooks.json"
DEFAULT_RULE_MANIFEST = PROJECT_ROOT / "config" / "rule_manifest.json"


def emit(value: Any) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def ingest(args: argparse.Namespace) -> int:
    verify_rule_manifest(args.rules, args.rule_manifest)
    rules = load_rules(args.rules)
    trust_policy = load_trust_policy(args.trust_policy) if args.trust_policy else None
    accepted = duplicates = rejected = alert_count = 0
    with EvidenceStore(args.db) as store, Path(args.input).open("rb") as stream:
        engine = DetectionEngine(store, rules)
        for line_number, raw in enumerate(stream, start=1):
            if line_number > args.max_events:
                raise BlueTeamError(f"input exceeds the {args.max_events} event run limit")
            raw = raw.rstrip(b"\r\n")
            if not raw:
                continue
            try:
                if len(raw) > MAX_EVENT_BYTES:
                    raise BlueTeamError(f"event exceeds {MAX_EVENT_BYTES} bytes")
                payload = loads_bounded(raw)
                event_data = verify_envelope(payload, trust_policy) if trust_policy else payload
                event = Event.from_dict(event_data)
                inserted = store.add_event(event)
                if not inserted:
                    duplicates += 1
                    continue
                accepted += 1
                alert_count += len(engine.evaluate(event))
            except BlueTeamError as exc:
                rejected += 1
                print(f"line {line_number}: rejected: {exc}", file=sys.stderr)
                if args.fail_fast:
                    raise
    emit({"accepted": accepted, "duplicates": duplicates, "rejected": rejected, "alerts_created": alert_count})
    return 2 if rejected else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="sentinel-blue", description="Defensive operations evidence core")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize an evidence database")
    init.add_argument("--db", required=True)

    ingest_parser = sub.add_parser("ingest", help="ingest and evaluate JSONL telemetry")
    ingest_parser.add_argument("input")
    ingest_parser.add_argument("--db", required=True)
    ingest_parser.add_argument("--rules", default=str(DEFAULT_RULES))
    ingest_parser.add_argument("--rule-manifest", default=str(DEFAULT_RULE_MANIFEST))
    ingest_parser.add_argument(
        "--trust-policy",
        help="require authenticated collector envelopes using this source trust policy",
    )
    ingest_parser.add_argument("--max-events", type=int, default=100_000)
    ingest_parser.add_argument("--fail-fast", action="store_true")

    alerts = sub.add_parser("alerts", help="list alerts")
    alerts.add_argument("--db", required=True)
    alerts.add_argument("--limit", type=int, default=100)

    cases = sub.add_parser("cases", help="list incident cases")
    cases.add_argument("--db", required=True)
    cases.add_argument("--limit", type=int, default=100)

    case_open = sub.add_parser("case-open", help="open a case for an alert")
    case_open.add_argument("--db", required=True)
    case_open.add_argument("--alert-id", required=True)
    case_open.add_argument("--title", required=True)

    verify = sub.add_parser("verify-ledger", help="verify the tamper-evident audit chain")
    verify.add_argument("--db", required=True)

    health = sub.add_parser("health", help="report telemetry blind spots")
    health.add_argument("--db", required=True)
    health.add_argument("--policy", default=str(DEFAULT_SENSORS))

    coverage = sub.add_parser("coverage", help="report target ATT&CK coverage")
    coverage.add_argument("--rules", default=str(DEFAULT_RULES))
    coverage.add_argument("--target", default=str(DEFAULT_COVERAGE))
    coverage.add_argument("--rule-manifest", default=str(DEFAULT_RULE_MANIFEST))

    response = sub.add_parser("response-plan", help="create a non-executing response plan")
    response.add_argument("--db", required=True)
    response.add_argument("--alert-id", required=True)
    response.add_argument("--playbook", required=True)
    response.add_argument("--playbooks", default=str(DEFAULT_PLAYBOOKS))

    validate = sub.add_parser("validate", help="run the defensive configuration assurance gate")
    validate.add_argument("--rules", default=str(DEFAULT_RULES))
    validate.add_argument("--rule-manifest", default=str(DEFAULT_RULE_MANIFEST))
    validate.add_argument("--target", default=str(DEFAULT_COVERAGE))
    validate.add_argument("--sensors", default=str(DEFAULT_SENSORS))
    validate.add_argument("--playbooks", default=str(DEFAULT_PLAYBOOKS))
    return parser


def run(args: argparse.Namespace) -> int:
    if args.command == "init":
        with EvidenceStore(args.db) as store:
            emit({"initialized": True, "database": str(store.path), "schema_version": 1})
        return 0
    if args.command == "ingest":
        return ingest(args)
    if args.command == "alerts":
        with EvidenceStore(args.db) as store:
            emit(store.list_alerts(limit=args.limit))
        return 0
    if args.command == "cases":
        with EvidenceStore(args.db) as store:
            emit(store.list_cases(limit=args.limit))
        return 0
    if args.command == "case-open":
        with EvidenceStore(args.db) as store:
            emit(store.create_case(args.alert_id, args.title))
        return 0
    if args.command == "verify-ledger":
        with EvidenceStore(args.db) as store:
            emit(store.verify_audit_chain())
        return 0
    if args.command == "health":
        with EvidenceStore(args.db) as store:
            emit(health_report(store, load_sensor_policy(args.policy)))
        return 0
    if args.command == "coverage":
        verify_rule_manifest(args.rules, args.rule_manifest)
        emit(coverage_report(load_rules(args.rules), load_coverage_target(args.target)))
        return 0
    if args.command == "response-plan":
        with EvidenceStore(args.db) as store:
            alert = store.get_alert(args.alert_id)
            if not alert:
                raise BlueTeamError("alert does not exist")
            emit(response_plan(load_playbooks(args.playbooks), args.playbook, alert))
        return 0
    if args.command == "validate":
        emit(
            validate_configuration(
                rules_path=args.rules,
                manifest_path=args.rule_manifest,
                coverage_path=args.target,
                sensors_path=args.sensors,
                playbooks_path=args.playbooks,
            )
        )
        return 0
    raise BlueTeamError("unsupported command")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except (BlueTeamError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
