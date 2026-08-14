from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import load_json_bounded, sha256
from .errors import ConfigurationError

CLAIM_STATES = {
    "PROPOSED", "MECHANISM_IDENTIFIED", "TESTABLE", "EVIDENCED",
    "INDEPENDENTLY_REVIEWED", "OPERATIONAL", "DISPUTED", "REGRESSED",
}


def load_object(path: Path) -> dict[str, Any]:
    value = load_json_bounded(path.read_bytes())
    if not isinstance(value, dict):
        raise ConfigurationError(f"{path.name} must contain an object")
    return value


def evaluate_readiness(path: Path) -> dict[str, Any]:
    document = load_object(path)
    readiness = document.get("assessment_readiness")
    definitions = document.get("gate_definitions")
    state_model = document.get("state_model")
    if not isinstance(readiness, dict) or not isinstance(definitions, dict) or not isinstance(state_model, dict):
        raise ConfigurationError("readiness document is missing required sections")
    required = readiness.get("required_gates")
    if not isinstance(required, list) or not required or len(required) != len(set(required)):
        raise ConfigurationError("required_gates must be a unique non-empty list")
    gates: dict[str, str] = {}
    for gate in required:
        definition = definitions.get(gate)
        if not isinstance(gate, str) or not isinstance(definition, dict):
            raise ConfigurationError(f"missing required gate definition: {gate}")
        status = definition.get("status")
        if status not in {"PENDING", "VERIFIED", "FAILED", "REVOKED"}:
            raise ConfigurationError(f"invalid readiness status for {gate}")
        verification = definition.get("verification")
        if not isinstance(verification, list) or not verification:
            raise ConfigurationError(f"gate {gate} lacks verification criteria")
        evidence = definition.get("evidence", [])
        if not isinstance(evidence, list):
            raise ConfigurationError(f"gate {gate} evidence must be a list")
        if status == "VERIFIED" and not evidence:
            raise ConfigurationError(f"gate {gate} is verified without evidence references")
        gates[gate] = status
    ready = all(status == "VERIFIED" for status in gates.values())
    current_state = state_model.get("current_state")
    if ready and current_state not in {"ASSESSMENT_READY", "EXERCISE_AUTHORIZED", "EXERCISE_COMPLETE", "EVIDENCE_VERIFIED", "ASSESSMENT_ISSUED"}:
        raise ConfigurationError("all gates are verified but state model is not assessment-ready")
    if not ready and current_state not in {"DESIGN_COMPLETE", "PREREQUISITES_PENDING"}:
        raise ConfigurationError("readiness state overclaims while a gate is not verified")
    return {
        "ready": ready,
        "status": "ASSESSMENT_READY" if ready else "NOT_ASSESSMENT_READY",
        "marking": "ASSESSMENT_CANDIDATE" if ready else "TRAINING_OR_ENGINEERING_USE_ONLY",
        "gates": gates,
        "snapshot_sha256": sha256(document),
    }


def evaluate_claims(path: Path, *, readiness_ready: bool) -> dict[str, Any]:
    document = load_object(path)
    claims = document.get("claims")
    if not isinstance(claims, list) or not claims:
        raise ConfigurationError("claim registry requires claims")
    seen: set[str] = set()
    counts: dict[str, int] = {}
    failures: list[str] = []
    for claim in claims:
        if not isinstance(claim, dict):
            raise ConfigurationError("claim must be an object")
        claim_id = claim.get("claim_id")
        status = claim.get("status")
        if not isinstance(claim_id, str) or not claim_id or claim_id in seen:
            raise ConfigurationError("claim IDs must be unique non-empty strings")
        seen.add(claim_id)
        if status not in CLAIM_STATES:
            raise ConfigurationError(f"invalid claim status: {claim_id}")
        counts[status] = counts.get(status, 0) + 1
        evidence = claim.get("evidence", [])
        if not isinstance(evidence, list):
            raise ConfigurationError(f"claim evidence must be a list: {claim_id}")
        if status in {"EVIDENCED", "INDEPENDENTLY_REVIEWED", "OPERATIONAL"} and not evidence:
            failures.append(f"{claim_id}: evidenced status without evidence identifiers")
        if status in {"INDEPENDENTLY_REVIEWED", "OPERATIONAL"} and not claim.get("independent_reviewer"):
            failures.append(f"{claim_id}: independent status without reviewer")
        if status == "OPERATIONAL" and not readiness_ready:
            failures.append(f"{claim_id}: operational while readiness is false")
        triggers = claim.get("regression_triggers")
        if not isinstance(triggers, list) or not triggers:
            failures.append(f"{claim_id}: missing regression triggers")
    return {
        "valid": not failures,
        "claim_count": len(claims),
        "status_counts": counts,
        "failures": failures,
        "registry_sha256": sha256(document),
    }


def validate_program(readiness_path: Path, claims_path: Path) -> dict[str, Any]:
    readiness = evaluate_readiness(readiness_path)
    claims = evaluate_claims(claims_path, readiness_ready=readiness["ready"])
    return {
        "valid": claims["valid"],
        "assurance_permitted": readiness["ready"] and claims["valid"],
        "readiness": readiness,
        "claims": claims,
        "warning": "A passing configuration gate validates consistency, not live control efficacy.",
    }
