"""Capability scoring for the Green Team.

    S_G = 0.20H + 0.25O + 0.25D + 0.15R + 0.15L

O (observability) is driven by DeTT&CT-scored telemetry quality rather than a source
count, and D (detection effectiveness) by ATT&CK technique handling. Both automatic
failures are evaluated before aggregation, per the program scorecard rules, and
undemonstrated components are excluded rather than assumed.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .coverage import DefensibilityModel
from .errors import ConfigurationError
from .telemetry import MAX_SCORE, inventory_summary

# What a response capability must be able to show. Having a runbook nobody has ever
# executed is the standard failure mode, so an untested restore does not count.
RESPONSE_CAPABILITIES = (
    "runbook_documented",
    "runbook_exercised",
    "backup_restore_tested",
    "rollback_tested",
)

# Green's charter is "defensible BEFORE production", so lifecycle integration asks
# whether defensive work happens at design time or gets bolted on afterwards.
LIFECYCLE_STAGES = (
    "design_review",
    "pre_merge_checks",
    "pre_production_acceptance",
    "production_monitoring",
)


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
            "team": "green",
            "formula": "S_G = 0.20H + 0.25O + 0.25D + 0.15R + 0.15L",
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
    if data.get("team") != "green":
        raise ConfigurationError("scorecard is not the Green Team scorecard")
    return data


def score_defensibility(
    model: DefensibilityModel,
    scorecard: dict[str, Any],
    *,
    hardening_results: dict[str, Any] | None = None,
    response_capabilities: list[str] | None = None,
    lifecycle_stages: list[str] | None = None,
    marking: str = "TRAINING_OR_ENGINEERING_USE_ONLY",
) -> ScoreResult:
    weights = {k: v["weight"] for k, v in scorecard["components"].items()}
    notes: list[str] = []
    auto_failures = list(model.automatic_failures())

    # --- H: hardening -------------------------------------------------------
    if not hardening_results:
        h_value: float | None = None
        h_detail = "no hardening baseline results supplied"
    else:
        passed = int(hardening_results.get("passed", 0))
        total = int(hardening_results.get("total", 0))
        if total <= 0:
            raise ConfigurationError("hardening_results.total must be positive")
        h_value = _clamp(passed / total)
        baseline = hardening_results.get("baseline", "unnamed baseline")
        h_detail = f"{passed}/{total} checks passing against {baseline}"

    # --- O: observability ---------------------------------------------------
    if not model.sources:
        o_value: float | None = None
        o_detail = "no telemetry sources recorded"
    else:
        summary = inventory_summary(model.sources)
        all_assets = model.telemetry_coverage()
        # Coverage breadth and source quality are multiplied: wide-but-poor and
        # narrow-but-excellent are both weak observability, and averaging them
        # would let one hide the other.
        quality_ratio = summary["mean_quality"] / MAX_SCORE
        o_value = _clamp(all_assets["ratio"] * quality_ratio)
        o_detail = (
            f"{all_assets['covered']}/{all_assets['assets']} assets have qualifying visibility; "
            f"mean source quality {summary['mean_quality']}/{MAX_SCORE}"
            + (f"; below the quality floor: {len(summary['blind_sources'])}"
               if summary["blind_sources"] else "")
        )

    # --- D: detection effectiveness -----------------------------------------
    if not model.techniques:
        d_value: float | None = None
        d_detail = "no ATT&CK techniques were assessed"
    else:
        d_value = _clamp(model.detection_effectiveness())
        must = model.must_detect_status()
        d_detail = (
            f"{int(d_value * len(model.techniques))}/{len(model.techniques)} techniques "
            f"detected or prevented; must-detect handled {must['handled']}/{must['must_detect']}"
        )

    # --- R: response and recovery readiness ---------------------------------
    if response_capabilities is None:
        r_value: float | None = None
        r_detail = "no response capabilities supplied"
    else:
        have = {c.strip().lower() for c in response_capabilities if str(c).strip()}
        present = [c for c in RESPONSE_CAPABILITIES if c in have]
        r_value = len(present) / len(RESPONSE_CAPABILITIES)
        missing = sorted(set(RESPONSE_CAPABILITIES) - set(present))
        r_detail = f"{len(present)}/{len(RESPONSE_CAPABILITIES)} capabilities" + (
            f"; missing: {', '.join(missing)}" if missing else ""
        )

    # --- L: lifecycle integration -------------------------------------------
    if lifecycle_stages is None:
        l_value: float | None = None
        l_detail = "no lifecycle integration points supplied"
    else:
        have = {s.strip().lower() for s in lifecycle_stages if str(s).strip()}
        present = [s for s in LIFECYCLE_STAGES if s in have]
        l_value = len(present) / len(LIFECYCLE_STAGES)
        missing = sorted(set(LIFECYCLE_STAGES) - set(present))
        l_detail = f"{len(present)}/{len(LIFECYCLE_STAGES)} stages integrated" + (
            f"; missing: {', '.join(missing)}" if missing else ""
        )

    components = [
        ComponentScore("H", "hardening", weights["H"], h_value, h_detail),
        ComponentScore("O", "observability", weights["O"], o_value, o_detail),
        ComponentScore("D", "detection effectiveness", weights["D"], d_value, d_detail),
        ComponentScore("R", "response and recovery readiness", weights["R"], r_value, r_detail),
        ComponentScore("L", "lifecycle integration", weights["L"], l_value, l_detail),
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
        pass_threshold=float(scorecard.get("pass_threshold", 0.85)),
        marking=marking,
        renormalized=renormalized,
        notes=notes,
    )
