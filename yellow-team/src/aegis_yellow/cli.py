from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .errors import YellowError
from .register import FindingsRegister
from .scoring import load_scorecard, score_delivery
from .slsa import BuildEvidence, determine_level
from .ssdf import PRACTICES, Attestation, coverage

DEFAULT_SCORECARD = Path(__file__).resolve().parents[3] / "config" / "scorecard.json"


def _emit(payload: object) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _load(path: str | None) -> Any:  # noqa: ANN401
    return json.loads(Path(path).read_text(encoding="utf-8")) if path else None


def cmd_list_practices(_: argparse.Namespace) -> int:
    _emit({"ssdf_version": "SP 800-218 v1.1", "practices": PRACTICES})
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    _emit(register.open_finding(
        args.finding_id, args.title, args.severity, args.at,
        acceptance_criteria=args.acceptance_criteria,
    ))
    return 0


def cmd_remediate(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    _emit(register.remediate(
        args.finding_id, args.at,
        regression_test=args.regression_test,
        compensating_control=args.compensating_control,
    ))
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    _emit(register.accept_risk(
        args.finding_id, args.at,
        accepted_by=args.accepted_by, compensating_control=args.compensating_control,
    ))
    return 0


def cmd_findings(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    _emit({
        "findings": [
            {
                "finding_id": f.finding_id, "title": f.title, "severity": f.severity,
                "state": f.state, "regression_test": f.regression_test,
                "compensating_control": f.compensating_control,
                "age_seconds": f.age_seconds,
            }
            for f in sorted(register.findings().values(), key=lambda f: f.finding_id)
        ],
        "automatic_failures": register.automatic_failures(),
    })
    return 0


def cmd_ssdf_coverage(args: argparse.Namespace) -> int:
    raw = _load(args.attestations) or []
    attestations = [Attestation.create(a["practice"], a["state"], a["evidence"]) for a in raw]
    _emit(coverage(attestations))
    return 0


def cmd_slsa(args: argparse.Namespace) -> int:
    _emit(determine_level(BuildEvidence.create(_load(args.evidence) or {})))
    return 0


def cmd_verify_register(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    try:
        count = register.ledger.verify()
    except YellowError as exc:
        print(f"INVALID REGISTER: {exc}", file=sys.stderr)
        return 2
    print(f"valid register: {count} records")
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    register = FindingsRegister(args.register)
    raw_attestations = _load(args.attestations)
    attestations = (
        [Attestation.create(a["practice"], a["state"], a["evidence"]) for a in raw_attestations]
        if raw_attestations else None
    )
    raw_build = _load(args.build_evidence)
    result = score_delivery(
        register,
        load_scorecard(args.scorecard),
        attestations=attestations,
        build_evidence=BuildEvidence.create(raw_build) if raw_build else None,
        test_metrics=_load(args.test_metrics),
        docs_present=_load(args.docs),
    )
    _emit(result.to_payload())
    return 0 if result.status == "PASS" else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-yellow",
        description="Secure-build evidence: findings to completed work, SSDF coverage, SLSA level",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list-practices", help="print the SSDF v1.1 practice catalogue").set_defaults(
        func=cmd_list_practices
    )

    def with_register(p: argparse.ArgumentParser) -> argparse.ArgumentParser:
        p.add_argument("--register", required=True)
        return p

    o = with_register(sub.add_parser("open", help="open a finding"))
    o.add_argument("--finding-id", required=True)
    o.add_argument("--title", required=True)
    o.add_argument("--severity", required=True, choices=["critical", "high", "medium", "low", "info"])
    o.add_argument("--at", required=True)
    o.add_argument("--acceptance-criteria")
    o.set_defaults(func=cmd_open)

    r = with_register(sub.add_parser("remediate", help="close a finding with evidence"))
    r.add_argument("--finding-id", required=True)
    r.add_argument("--at", required=True)
    r.add_argument("--regression-test", help="name of the automated test that pins the fix")
    r.add_argument("--compensating-control")
    r.set_defaults(func=cmd_remediate)

    a = with_register(sub.add_parser("accept-risk", help="record a named risk acceptance"))
    a.add_argument("--finding-id", required=True)
    a.add_argument("--at", required=True)
    a.add_argument("--accepted-by", required=True)
    a.add_argument("--compensating-control", required=True)
    a.set_defaults(func=cmd_accept)

    with_register(sub.add_parser("findings", help="list findings and automatic failures")).set_defaults(
        func=cmd_findings
    )
    with_register(sub.add_parser("verify-register", help="verify the hash chain")).set_defaults(
        func=cmd_verify_register
    )

    c = sub.add_parser("ssdf-coverage", help="compute SSDF practice coverage")
    c.add_argument("--attestations", required=True)
    c.set_defaults(func=cmd_ssdf_coverage)

    s = sub.add_parser("slsa-level", help="determine the SLSA build level from evidence")
    s.add_argument("--evidence", required=True)
    s.set_defaults(func=cmd_slsa)

    sc = with_register(sub.add_parser("score", help="compute S_Y"))
    sc.add_argument("--scorecard", default=str(DEFAULT_SCORECARD))
    sc.add_argument("--attestations")
    sc.add_argument("--build-evidence")
    sc.add_argument("--test-metrics")
    sc.add_argument("--docs")
    sc.set_defaults(func=cmd_score)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return int(args.func(args))
    except YellowError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
