from __future__ import annotations

from typing import Any

from .errors import ConfigurationError


def score_assessment(
    scorecard: dict[str, Any],
    component_scores: dict[str, float],
    evidence_refs: dict[str, list[str]],
    *,
    triggered_auto_failures: list[str],
    assessment_ready: bool,
) -> dict[str, Any]:
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
    return {
        "diagnostic_score": round(diagnostic, 6),
        "final_score": round(final, 6),
        "passed": passed,
        "auto_failed": auto_failed,
        "triggered_auto_failures": triggered_auto_failures,
        "marking": "ASSESSMENT_CANDIDATE" if assessment_ready else "TRAINING_OR_ENGINEERING_USE_ONLY",
        "assurance_statement_permitted": assessment_ready,
    }

