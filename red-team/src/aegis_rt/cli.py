from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import replace
from pathlib import Path

from .audit import AuditLedger, seal_ledger, verify_ledger_seal
from .authorization import (
    AUTHORIZATION_KEY,
    EVIDENCE_KEY,
    generate_keypair,
    password_from_environment,
    sign_authorization,
    verify_authorization,
)
from .checks import BUILTIN_CHECKS
from .engine import build_plan, run_engagement
from .models import Authorization, load_engagement
from .report import write_reports
from .scope import ScopeError, scope_fingerprint, validate_engagement


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="aegis-rt",
        description="Authorization-first red-team assessment orchestrator",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    checks = sub.add_parser("list-checks", help="list built-in assessment checks")
    checks.set_defaults(handler=_list_checks)

    keygen = sub.add_parser("keygen", help="create an encrypted Ed25519 authorization keypair")
    keygen.add_argument("--private-key", type=Path, required=True)
    keygen.add_argument("--public-key", type=Path, required=True)
    keygen.add_argument("--password-env", required=True)
    keygen.add_argument("--purpose", choices=[AUTHORIZATION_KEY, EVIDENCE_KEY], required=True)
    keygen.set_defaults(handler=_keygen)

    fingerprint = sub.add_parser("fingerprint", help="print the scope fingerprint")
    fingerprint.add_argument("engagement", type=Path)
    fingerprint.set_defaults(handler=_fingerprint)

    authorize = sub.add_parser("authorize", help="bind an authorization receipt to exact scope")
    authorize.add_argument("engagement", type=Path)
    authorize.add_argument("--approved-by", required=True)
    authorize.add_argument("--ticket", required=True)
    authorize.add_argument("--expires-at", required=True, help="ISO-8601 UTC timestamp")
    authorize.add_argument("--allow-public-targets", action="store_true")
    authorize.add_argument("--signing-key", type=Path, required=True)
    authorize.add_argument("--password-env", required=True)
    authorize.add_argument("--ack", required=True, help='must equal "I AM AUTHORIZED"')
    authorize.set_defaults(handler=_authorize)

    validate = sub.add_parser("validate", help="validate scope, limits, and authorization")
    validate.add_argument("engagement", type=Path)
    validate.add_argument("--require-authorization", action="store_true")
    validate.add_argument("--trust-key", type=Path)
    validate.set_defaults(handler=_validate)

    plan = sub.add_parser("plan", help="show checks without executing them")
    plan.add_argument("engagement", type=Path)
    plan.set_defaults(handler=_plan)

    run = sub.add_parser("run", help="execute authorized assessment checks")
    run.add_argument("engagement", type=Path)
    run.add_argument("--state-dir", type=Path, default=Path(".aegis"))
    run.add_argument("--output-dir", type=Path, default=Path("reports"))
    run.add_argument("--trust-key", type=Path, required=True)
    run.add_argument(
        "--ack-scope",
        required=True,
        help="exact 64-character fingerprint printed by the plan command",
    )
    run.set_defaults(handler=_run)

    verify = sub.add_parser("verify-ledger", help="verify the hash-chained audit ledger")
    verify.add_argument("ledger", type=Path)
    verify.add_argument("--seal", type=Path)
    verify.add_argument("--evidence-trust-key", type=Path)
    verify.set_defaults(handler=_verify_ledger)

    seal = sub.add_parser("seal-ledger", help="cryptographically seal a completed ledger")
    seal.add_argument("ledger", type=Path)
    seal.add_argument("--seal", type=Path, required=True)
    seal.add_argument("--evidence-signing-key", type=Path, required=True)
    seal.add_argument("--password-env", required=True)
    seal.set_defaults(handler=_seal_ledger)
    return parser


def _list_checks(_: argparse.Namespace) -> int:
    for check_id, check in sorted(BUILTIN_CHECKS.items()):
        mode = "active" if check.active else "offline"
        kinds = ",".join(sorted(kind.value for kind in check.target_kinds))
        print(f"{check_id:24} {mode:7} {kinds:6} {check.description}")
    return 0


def _keygen(args: argparse.Namespace) -> int:
    password = password_from_environment(args.password_env)
    generate_keypair(args.private_key, args.public_key, password, purpose=args.purpose)
    print(f"created encrypted signing key {args.private_key} and trust key {args.public_key}")
    return 0


def _fingerprint(args: argparse.Namespace) -> int:
    print(scope_fingerprint(load_engagement(args.engagement)))
    return 0


def _authorize(args: argparse.Namespace) -> int:
    if args.ack != "I AM AUTHORIZED":
        raise ScopeError('authorization acknowledgement must exactly equal "I AM AUTHORIZED"')
    engagement = load_engagement(args.engagement)
    fingerprint = scope_fingerprint(engagement)
    authorization = Authorization(
        approved_by=args.approved_by,
        ticket=args.ticket,
        expires_at=args.expires_at,
        scope_sha256=fingerprint,
        signature="",
        allow_public_targets=args.allow_public_targets,
    )
    authorization = replace(
        authorization,
        signature=sign_authorization(
            authorization,
            args.signing_key,
            password_from_environment(args.password_env),
        ),
    )
    candidate = replace(engagement, authorization=authorization)
    if authorization.is_expired():
        raise ScopeError("authorization expiry must be in the future")
    data = json.loads(args.engagement.read_text(encoding="utf-8"))
    data["authorization"] = {
        "approved_by": authorization.approved_by,
        "ticket": authorization.ticket,
        "expires_at": authorization.expires_at,
        "scope_sha256": authorization.scope_sha256,
        "signature": authorization.signature,
        "allow_public_targets": authorization.allow_public_targets,
    }
    temporary = args.engagement.with_name(args.engagement.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, args.engagement)
    print(f"authorized scope {scope_fingerprint(candidate)} via ticket {authorization.ticket}")
    return 0


def _validate(args: argparse.Namespace) -> int:
    engagement = load_engagement(args.engagement)
    validate_engagement(engagement, require_authorization=args.require_authorization)
    if args.require_authorization:
        if args.trust_key is None:
            raise ScopeError("--trust-key is required with --require-authorization")
        verify_authorization(engagement.authorization, args.trust_key)
    print(f"valid scope {scope_fingerprint(engagement)}")
    return 0


def _plan(args: argparse.Namespace) -> int:
    engagement = load_engagement(args.engagement)
    validate_engagement(engagement, require_authorization=False)
    fingerprint = scope_fingerprint(engagement)
    print(f"scope_sha256={fingerprint}")
    for check, target in build_plan(engagement):
        mode = "ACTIVE" if check.active else "OFFLINE"
        print(f"{mode:7} {check.check_id:24} {target.kind.value}:{target.value}")
    return 0


def _run(args: argparse.Namespace) -> int:
    engagement = load_engagement(args.engagement)
    fingerprint = scope_fingerprint(engagement)
    if args.ack_scope != fingerprint:
        raise ScopeError("--ack-scope does not exactly match the current scope fingerprint")
    summary = run_engagement(
        engagement,
        args.state_dir,
        trusted_public_key=args.trust_key,
        require_authorization=True,
    )
    json_path, markdown_path = write_reports(summary, args.output_dir)
    print(
        f"completed {len(summary.results)} checks; {summary.findings_count} findings; "
        f"{summary.requests_used} requests; {summary.files_used} files"
    )
    print(f"reports: {json_path} {markdown_path}")
    return 0


def _verify_ledger(args: argparse.Namespace) -> int:
    valid, count, error = AuditLedger(args.ledger).verify()
    if not valid:
        print(f"INVALID after {count} records: {error}", file=sys.stderr)
        return 2
    if (args.seal is None) != (args.evidence_trust_key is None):
        raise ValueError("--seal and --evidence-trust-key must be provided together")
    if args.seal is not None:
        verify_ledger_seal(args.ledger, args.seal, args.evidence_trust_key)
    print(f"valid ledger: {count} records")
    return 0


def _seal_ledger(args: argparse.Namespace) -> int:
    seal_ledger(
        args.ledger,
        args.seal,
        args.evidence_signing_key,
        password_from_environment(args.password_env),
    )
    print(f"sealed ledger: {args.seal}")
    return 0


def main(argv: list[str] | None = None) -> int:
    try:
        args = _parser().parse_args(argv)
        return int(args.handler(args))
    except (ScopeError, ValueError, KeyError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
