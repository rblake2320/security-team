from __future__ import annotations

from typing import Any

from .errors import ConfigurationError


def score_assessment(
    scorecard: dict[str, Any],
    component_scores: dict[str, float],
    evidence_refs: dict[str, list[str]],
    *,
    triggered_auto_failures: list[str],
    readiness: dict[str, Any],
    claims: dict[str, Any],
    artifact_digests: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Score an exercise.

    AUD-01: assessment readiness is DERIVED from the authoritative readiness
    registry, never supplied by the caller. The previous signature took an
    `assessment_ready: bool` straight from a CLI flag, so
    `aegis-purple score --assessment-ready` produced an ASSESSMENT_CANDIDATE
    marking with `assurance_statement_permitted: true` while the program state
    was NOT_ASSESSMENT_READY. A caller-controlled boolean is not a control.
    """
    components = scorecard.get("components")
    if not isinstance(components, dict) or not components:
        raise ConfigurationError("scorecard requires components")
    weights: dict[str, float] = {}
    for name, definition in components.items():
        if not isinstance(definition, dict):
            raise ConfigurationError(f"invalid component: {name}")
        weight = definition.get("weight")
        if isinstance(weight, bool) or not isinstance(weight, (int, float)) or not 0 < float(weight) <= 1:
            raise ConfigurationError(f"invalid weight: {name}")
        weights[name] = float(weight)
    if abs(sum(weights.values()) - 1.0) > 1e-9:
        raise ConfigurationError("component weights must sum to 1.0")
    if set(component_scores) != set(weights) or set(evidence_refs) != set(weights):
        raise ConfigurationError("scores and evidence must exactly match scorecard components")
    for name, value in component_scores.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= float(value) <= 1:
            raise ConfigurationError(f"score must be 0..1: {name}")
        refs = evidence_refs[name]
        if not isinstance(refs, list) or not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise ConfigurationError(f"component requires evidence references: {name}")
    configured_auto_failures = scorecard.get("automatic_failure_conditions")
    if not isinstance(configured_auto_failures, list):
        raise ConfigurationError("automatic_failure_conditions must be a list")
    unknown = set(triggered_auto_failures) - set(configured_auto_failures)
    if unknown:
        raise ConfigurationError(f"unknown automatic failure: {sorted(unknown)}")
    diagnostic = sum(float(component_scores[name]) * weights[name] for name in weights)
    auto_failed = bool(triggered_auto_failures)
    final = 0.0 if auto_failed else diagnostic
    threshold = scorecard.get("pass_threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not 0 <= float(threshold) <= 1:
        raise ConfigurationError("invalid pass_threshold")
    passed = not auto_failed and final >= float(threshold)

    # Derived, not supplied. Every required gate must be VERIFIED.
    assessment_ready, pending = _readiness_state(readiness)
    return {
        "diagnostic_score": round(diagnostic, 6),
        "final_score": round(final, 6),
        "passed": passed,
        "auto_failed": auto_failed,
        "triggered_auto_failures": triggered_auto_failures,
        "marking": "ASSESSMENT_CANDIDATE" if assessment_ready else "TRAINING_OR_ENGINEERING_USE_ONLY",
        "assurance_statement_permitted": assessment_ready,
        "readiness_derived_from": "assessment_readiness.json",
        "pending_readiness_gates": pending,
        "artifact_digests": artifact_digests or {},
    }


def _readiness_state(readiness: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (ready, pending_gates) derived from EVERY defined gate. Fails closed.

    L3-F1 (external review, reproduced): this iterated `required_gates`, an
    author-editable list, instead of `gate_definitions`, the record ground truth sits
    in. PoC: drop the two PENDING gates from `required_gates` without touching their
    status - `gate_definitions` still reads PENDING for both - and this returned
    ready=True. That is the exact falsification of PROGRAM-READINESS-GATE-001 that
    AUD-01/AUD-01b/claim_check-F6 each closed in a different module. This is the
    fourth independent instance of the same pattern (trusting a self-declared summary
    field instead of the record it summarises), surviving here specifically because
    this file had no owner when the earlier fixes landed.

    `required_gates` is now an ASSERTION about `gate_definitions`, validated rather
    than obeyed: omitting a defined gate from it is itself a readiness failure, so
    shrinking the list can never buy readiness.
    """
    block = readiness.get("assessment_readiness")
    definitions = readiness.get("gate_definitions")
    if not isinstance(block, dict) or not isinstance(definitions, dict):
        raise ConfigurationError("readiness registry is malformed; refusing to derive readiness")
    required = block.get("required_gates")
    if not isinstance(required, list) or not required:
        raise ConfigurationError("readiness registry declares no required gates")

    pending = []
    for name, definition in definitions.items():
        if not isinstance(definition, dict):
            raise ConfigurationError(f"readiness gate definition is malformed: {name}")
        if definition.get("status") != "VERIFIED":
            pending.append(name)

    for gate in required:
        if gate not in definitions:
            raise ConfigurationError(f"readiness gate is undefined: {gate}")
    omitted = sorted(set(definitions) - set(required))
    for name in omitted:
        if name not in pending:
            pending.append(name)

    return (not pending), sorted(pending)

