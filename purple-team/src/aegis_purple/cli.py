from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import hashlib

from .assurance import load_object, validate_program
from .attestation import verify_gate_attestation
from .authority import validate_role_trust_registry, verify_transition_envelope
from .canonical import load_json_bounded, sha256
from .errors import ConfigurationError, PurpleError
from .models import ExercisePlan
from .scoring import score_assessment
from .store import ExerciseStore


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="aegis-purple", description="Fail-closed purple-team orchestration")
    commands = root.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate-program")
    validate.add_argument("--readiness", type=Path, required=True)
    validate.add_argument("--claims", type=Path, required=True)
    validate.add_argument("--require-ready", action="store_true")
    create = commands.add_parser("create")
    create.add_argument("--db", type=Path, required=True)
    create.add_argument("--plan", type=Path, required=True)
    create.add_argument("--trust-registry", type=Path, required=True)
    create.add_argument("--actor", required=True)
    transition = commands.add_parser("transition")
    transition.add_argument("--db", type=Path, required=True)
    transition.add_argument("--command", type=Path, required=True)
    transition.add_argument("--trust-registry", type=Path, required=True)
    status = commands.add_parser("status")
    status.add_argument("--db", type=Path, required=True)
    status.add_argument("--exercise", required=True)
    verify = commands.add_parser("verify-ledger")
    verify.add_argument("--db", type=Path, required=True)
    anchor = commands.add_parser("export-anchor")
    anchor.add_argument("--db", type=Path, required=True)
    score = commands.add_parser("score")
    score.add_argument("--scorecard", type=Path, required=True)
    score.add_argument("--input", type=Path, required=True)
    score.add_argument("--readiness", type=Path,

                       help="authoritative assessment_readiness.json; readiness is DERIVED from it")

    score.add_argument("--claims", type=Path,

                       help="authoritative assurance_claims.json")
    attestation = commands.add_parser("verify-gate-attestation")
    attestation.add_argument("--attestation", type=Path, required=True)
    attestation.add_argument("--trust-registry", type=Path, required=True)
    return root


CANONICAL_READINESS = "00-shared/config/assessment_readiness.json"
CANONICAL_CLAIMS = "00-shared/config/assurance_claims.json"


def _program_root() -> Path:
    """Repository root, derived from this package's own location.

    AUD-01b: the first fix replaced a caller-controlled BOOLEAN with a
    caller-controlled PATH, which is the same defect wearing a different hat. A
    self-consistent forged registry passed validate_program and produced
    ASSESSMENT_CANDIDATE. Authority must come from the program's own artifacts.
    """
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / CANONICAL_READINESS).is_file():
            return parent
    raise ConfigurationError(
        "cannot locate the canonical readiness registry; refusing to derive readiness")


def _canonical(kind: str, supplied: Path | None) -> Path:
    """Return the canonical artifact, refusing any substitute."""
    root = _program_root()
    canonical = root / (CANONICAL_READINESS if kind == "readiness" else CANONICAL_CLAIMS)
    if supplied is not None:
        try:
            same = Path(supplied).resolve() == canonical.resolve()
        except OSError:
            same = False
        if not same:
            raise ConfigurationError(
                f"refusing a non-canonical {kind} artifact: {supplied}. "
                f"Readiness is derived from {canonical}, never from a supplied path. "
                "To change readiness, change the registry in the repository, where the "
                "edit is reviewable and version-controlled.")
    return canonical


def _digest(path: Path) -> str:
    """SHA-256 of the artifact as read, so a score records exactly what permitted it."""
    return "sha256:" + hashlib.sha256(Path(path).read_bytes()).hexdigest()



def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "validate-program":
            result = validate_program(args.readiness, args.claims)
            _print(result)
            if not result["valid"]:
                return 2
            return 3 if args.require_ready and not result["assurance_permitted"] else 0
        if args.command == "create":
            raw = load_json_bounded(args.plan.read_bytes())
            plan = ExercisePlan.from_dict(raw)
            trust_registry = load_object(args.trust_registry)
            validate_role_trust_registry(trust_registry)
            if plan.role_trust_sha256 != sha256(trust_registry):
                raise PurpleError("plan does not pin the supplied role trust registry")
            with ExerciseStore(args.db) as store:
                digest = store.create_exercise(plan, actor_id=args.actor)
            _print({"created": True, "exercise_id": plan.exercise_id, "plan_sha256": digest, "state": "FROZEN"})
            return 0
        if args.command == "transition":
            trust_registry = load_object(args.trust_registry)
            command = verify_transition_envelope(load_object(args.command), trust_registry)
            with ExerciseStore(args.db) as store:
                head = store.apply_authorized_transition(command, role_trust_sha256=sha256(trust_registry))
            _print({"transitioned": True, "state": command.to_state, "audit_head": head})
            return 0
        if args.command == "status":
            with ExerciseStore(args.db) as store:
                _print(store.status(args.exercise))
            return 0
        if args.command == "verify-ledger":
            with ExerciseStore(args.db) as store:
                _print(store.verify())
            return 0
        if args.command == "export-anchor":
            with ExerciseStore(args.db) as store:
                _print(store.export_anchor())
            return 0
        if args.command == "score":
            payload = load_object(args.input)
            # AUD-01: readiness is derived from the authoritative artifacts and their
            # digests are emitted, so a score can be tied to the exact registry state
            # that permitted it. There is no caller-controlled readiness flag.
            readiness_path = _canonical("readiness", getattr(args, "readiness", None))
            claims_path = _canonical("claims", getattr(args, "claims", None))
            readiness_doc = load_object(readiness_path)
            claims_doc = load_object(claims_path)
            validate_program(readiness_path, claims_path)
            result = score_assessment(
                load_object(args.scorecard), payload["component_scores"], payload["evidence_refs"],
                triggered_auto_failures=payload.get("triggered_auto_failures", []),
                readiness=readiness_doc,
                claims=claims_doc,
                artifact_digests={
                    "assessment_readiness.json": _digest(readiness_path),
                    "assurance_claims.json": _digest(claims_path),
                },
            )
            _print(result)
            return 0
        if args.command == "verify-gate-attestation":
            result = verify_gate_attestation(load_object(args.attestation), load_object(args.trust_registry))
            _print(result)
            return 0
    except (PurpleError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 2


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, sort_keys=True))
