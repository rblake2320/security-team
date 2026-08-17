from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .control import ExerciseControl
from .errors import WhiteError
from .models import Authorization, Decision, Scope
from .report import build_report
from .scoring import load_scorecard, score_exercise

DEFAULT_SCORECARD = Path(__file__).resolve().parents[3] / "config" / "scorecard.json"


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def cmd_authorize(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    authorization = Authorization.create(args.approved_by, args.ticket, args.expires_at)
    scope = Scope.create(args.target, args.activity)
    _emit(control.authorize(args.exercise_id, authorization, scope, args.at))
    return 0


def cmd_start(args: argparse.Namespace) -> int:
    _emit(ExerciseControl(args.ledger).start(args.at))
    return 0


def cmd_activity(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    try:
        _emit(control.request_activity(args.target, args.activity, args.at, observed=args.observed))
        return 0
    except WhiteError as exc:
        # A refusal is a successful control action, not a crash. Exit 3 distinguishes
        # "White refused this" from "the tool broke" (exit 2).
        print(json.dumps({"refused": True, "reason": str(exc)}, indent=2), file=sys.stderr)
        return 3


def cmd_stop(args: argparse.Namespace) -> int:
    _emit(ExerciseControl(args.ledger).declare_stop(args.reason, args.at, severity=args.severity))
    return 0


def cmd_ack_stop(args: argparse.Namespace) -> int:
    _emit(ExerciseControl(args.ledger).acknowledge_stop(args.at))
    return 0


def cmd_decision(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    decision = Decision.create(
        args.decision_id, args.decided_by, args.question, args.outcome,
        args.rationale, args.raised_at, args.decided_at,
    )
    _emit(control.record_decision(decision))
    return 0


def cmd_complete(args: argparse.Namespace) -> int:
    _emit(ExerciseControl(args.ledger).complete(args.at))
    return 0


def cmd_verify_ledger(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    try:
        count = control.ledger.verify()
    except WhiteError as exc:
        print(f"INVALID LEDGER: {exc}", file=sys.stderr)
        return 2
    print(f"valid ledger: {count} records")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    report = build_report(
        control,
        summary=args.summary or "",
        findings=args.findings or "",
        recommendations=args.recommendations or "",
    )
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        _emit(report)
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    control = ExerciseControl(args.ledger)
    scorecard = load_scorecard(args.scorecard)
    report = json.loads(Path(args.report).read_text(encoding="utf-8")) if args.report else None
    result = score_exercise(control, scorecard, report=report)
    _emit(result.to_payload())
    # A FAILED capability assessment must not exit 0 — CI has to be able to gate on it.
    return 0 if result.status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-white",
        description="Independent exercise control: authorization, scope, stop authority, evidence",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def with_ledger(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--ledger", required=True)
        return p

    a = with_ledger(sub.add_parser("authorize", help="authorize an exercise and freeze its scope"))
    a.add_argument("--exercise-id", required=True)
    a.add_argument("--approved-by", required=True)
    a.add_argument("--ticket", required=True)
    a.add_argument("--expires-at", required=True)
    a.add_argument("--target", action="append", required=True, help="repeatable allow-list entry")
    a.add_argument("--activity", action="append", required=True, help="repeatable allow-list entry")
    a.add_argument("--at", required=True)
    a.set_defaults(func=cmd_authorize)

    s = with_ledger(sub.add_parser("start", help="mark the exercise started"))
    s.add_argument("--at", required=True)
    s.set_defaults(func=cmd_start)

    act = with_ledger(sub.add_parser("activity", help="adjudicate a proposed activity"))
    act.add_argument("--target", required=True)
    act.add_argument("--activity", required=True)
    act.add_argument("--at", required=True)
    act.add_argument(
        "--observed",
        action="store_true",
        help="record that this happened regardless of White's decision (breach evidence)",
    )
    act.set_defaults(func=cmd_activity)

    st = with_ledger(sub.add_parser("stop", help="declare a stop condition"))
    st.add_argument("--reason", required=True)
    st.add_argument("--severity", choices=["advisory", "mandatory"], default="mandatory")
    st.add_argument("--at", required=True)
    st.set_defaults(func=cmd_stop)

    ack = with_ledger(sub.add_parser("ack-stop", help="record acknowledgement of a stop"))
    ack.add_argument("--at", required=True)
    ack.set_defaults(func=cmd_ack_stop)

    d = with_ledger(sub.add_parser("decision", help="record a governance decision"))
    d.add_argument("--decision-id", required=True)
    d.add_argument("--decided-by", required=True)
    d.add_argument("--question", required=True)
    d.add_argument("--outcome", required=True)
    d.add_argument("--rationale", required=True)
    d.add_argument("--raised-at", required=True)
    d.add_argument("--decided-at", required=True)
    d.set_defaults(func=cmd_decision)

    c = with_ledger(sub.add_parser("complete", help="mark the exercise complete"))
    c.add_argument("--at", required=True)
    c.set_defaults(func=cmd_complete)

    with_ledger(sub.add_parser("verify-ledger", help="verify the hash chain")).set_defaults(
        func=cmd_verify_ledger
    )

    r = with_ledger(sub.add_parser("report", help="build the after-action report"))
    r.add_argument("--summary")
    r.add_argument("--findings")
    r.add_argument("--recommendations")
    r.add_argument("--output")
    r.set_defaults(func=cmd_report)

    sc = with_ledger(sub.add_parser("score", help="compute S_W from the ledger"))
    sc.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    sc.add_argument("--report", help="after-action report JSON, for the Q component")
    sc.set_defaults(func=cmd_score)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except WhiteError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
