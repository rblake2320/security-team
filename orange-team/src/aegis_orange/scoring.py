"""Capability scoring for the Orange Team.

    S_O = 0.25X + 0.20P + 0.20E + 0.20T + 0.15N

X is measured against seeded attack paths the reviewer was not told about, which is
the only honest way to score discovery: counting findings rewards volume, while
counting *seeded* findings rewards actually looking where it matters.

Same program rules as the other teams: automatic failures before aggregation, and
undemonstrated components excluded with renormalization.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError
from .review import DesignReview
from .stride import Element, coverage


@dataclass
class ComponentScore:
    key: str
    name: str
    weight: float
    value: float | None
    detail: str

    @property
    def demonstrated(self) -> bool:
        return self.value is not None


@dataclass
class ScoreResult:
    components: list[ComponentScore]
    auto_failures: list[str]
    weighted_score: float
    pass_threshold: float
    marking: str
    renormalized: bool = False
    notes: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.auto_failures:
            return "FAILED"
        return "PASS" if self.weighted_score >= self.pass_threshold else "BELOW_THRESHOLD"

    def to_payload(self) -> dict[str, Any]:
        return {
            "team": "orange",
            "formula": "S_O = 0.25X + 0.20P + 0.20E + 0.20T + 0.15N",
            "status": self.status,
            "weighted_score": round(self.weighted_score, 4),
            "pass_threshold": self.pass_threshold,
            "auto_failures": self.auto_failures,
            "renormalized_for_undemonstrated_components": self.renormalized,
            "marking": self.marking,
            "notes": self.notes,
            "components": [
                {
                    "key": c.key, "name": c.name, "weight": c.weight,
                    "value": None if c.value is None else round(c.value, 4),
                    "status": "scored" if c.demonstrated else "not_demonstrated",
                    "detail": c.detail,
                }
                for c in self.components
            ],
        }


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def load_scorecard(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("team") != "orange":
        raise ConfigurationError("scorecard is not the Orange Team scorecard")
    return data


def score_review(
    review: DesignReview,
    scorecard: dict[str, Any],
    *,
    elements: list[Element] | None = None,
    stride_considered: dict[str, list[str]] | None = None,
    marking: str = "TRAINING_OR_ENGINEERING_USE_ONLY",
) -> ScoreResult:
    weights = {k: v["weight"] for k, v in scorecard["components"].items()}
    notes: list[str] = []
    auto_failures = list(review.automatic_failures())

    # --- X: attack-path discovery -------------------------------------------
    discovery = review.discovery_rate()
    if discovery is None:
        x_value: float | None = None
        x_detail = "no seeded attack paths; discovery could not be measured objectively"
    else:
        x_value = _clamp(discovery)
        missed = review.missed_seeded()
        x_detail = (
            f"{int(discovery * len(review.seeded_paths))}/{len(review.seeded_paths)} "
            "seeded paths discovered"
            + (f"; missed: {', '.join(missed)}" if missed else "")
        )
        # STRIDE coverage is reported alongside discovery, because a high hit rate on
        # a shallow model is a weaker result than the number suggests.
        if elements and stride_considered is not None:
            cov = coverage(elements, stride_considered)
            notes.append(
                f"STRIDE coverage {cov['considered_pairs']}/{cov['applicable_pairs']} "
                f"element-category pairs"
                + (f"; {len(cov['trust_boundary_gaps'])} gap(s) on trust boundaries"
                   if cov["trust_boundary_gaps"] else "")
            )

    # --- P: prioritization accuracy -----------------------------------------
    accuracy = review.prioritization_accuracy()
    if accuracy is None:
        p_value: float | None = None
        p_detail = "no seeded paths were rediscovered, so severity accuracy is unmeasurable"
    else:
        p_value = _clamp(accuracy)
        p_detail = f"{accuracy:.0%} of rediscovered seeded paths were rated at the seeded severity"

    # --- E: engineering usefulness ------------------------------------------
    actionable = review.actionable_ratio()
    if actionable is None:
        e_value: float | None = None
        e_detail = "no findings were recorded"
    else:
        e_value = _clamp(actionable)
        e_detail = f"{actionable:.0%} of findings carry a recommendation with acceptance criteria"

    # --- T: conversion into safe tests ---------------------------------------
    conversion = review.test_conversion()
    if conversion is None:
        t_value: float | None = None
        t_detail = "no findings were recorded"
    else:
        t_value = _clamp(conversion)
        unsafe = [t.test_id for t in review.tests if not t.is_safe]
        t_detail = f"{conversion:.0%} of findings converted into a safe executed test" + (
            f"; {len(unsafe)} proposed test(s) flagged unsafe" if unsafe else ""
        )

    # --- N: developer knowledge transfer -------------------------------------
    if not review.knowledge_transfer:
        n_value: float | None = None
        n_detail = "no knowledge-transfer activity recorded"
    else:
        # Teaching builders to recognise their own decisions becoming exploitable is
        # the charter's stated purpose, so this is measured per finding rather than
        # as a single "we ran a session" checkbox.
        covered = len({k for k in review.knowledge_transfer if k})
        target = max(len(review.found_paths), 1)
        n_value = _clamp(covered / target)
        n_detail = f"{covered} knowledge-transfer item(s) against {target} finding(s)"

    components = [
        ComponentScore("X", "attack-path discovery", weights["X"], x_value, x_detail),
        ComponentScore("P", "prioritization accuracy", weights["P"], p_value, p_detail),
        ComponentScore("E", "engineering usefulness", weights["E"], e_value, e_detail),
        ComponentScore("T", "conversion into safe tests", weights["T"], t_value, t_detail),
        ComponentScore("N", "developer knowledge transfer", weights["N"], n_value, n_detail),
    ]

    demonstrated = [c for c in components if c.demonstrated]
    if not demonstrated:
        raise ConfigurationError("no component could be scored; nothing was demonstrated")
    total_weight = sum(c.weight for c in demonstrated)
    weighted = sum(c.weight * float(c.value) for c in demonstrated) / total_weight
    renormalized = len(demonstrated) != len(components)
    if renormalized:
        skipped = ", ".join(c.key for c in components if not c.demonstrated)
        notes.append(
            f"components {skipped} were not demonstrated and are excluded; "
            "remaining weights renormalized rather than assumed"
        )

    return ScoreResult(
        components=components,
        auto_failures=auto_failures,
        weighted_score=weighted,
        pass_threshold=float(scorecard.get("pass_threshold", 0.8)),
        marking=marking,
        renormalized=renormalized,
        notes=notes,
    )
