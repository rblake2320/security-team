"""Capability scoring for the White Team.

    S_W = 0.25A + 0.25G + 0.20S + 0.15E + 0.15Q

Every component is *derived from the ledger*, never self-asserted. Weights and
thresholds are read from config/scorecard.json, which the program requires to be
published before execution and frozen at execution start.

Two rules from the program scorecard are implemented literally:

  1. Automatic-failure conditions are evaluated BEFORE aggregation. Any auto-fail
     sets status=FAILED; the weighted score is retained for diagnostics only.
  2. A component that was never exercised is reported as `not_demonstrated` and
     excluded from the weighted mean, with the remaining weights renormalized.
     Scoring an untested capability as either 0 or 1 would be a fabrication.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .control import ExerciseControl
from .errors import ConfigurationError, IntegrityError

# Defaults used when the caller does not supply operational targets.
DEFAULT_STOP_TARGET_SECONDS = 60.0
DEFAULT_DECISION_TARGET_SECONDS = 900.0

REQUIRED_REPORT_SECTIONS = (
    "summary",
    "timeline",
    "findings",
    "decisions",
    "recommendations",
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
            "team": "white",
            "formula": "S_W = 0.25A + 0.25G + 0.20S + 0.15E + 0.15Q",
            "status": self.status,
            "weighted_score": round(self.weighted_score, 4),
            "pass_threshold": self.pass_threshold,
            "auto_failures": self.auto_failures,
            "renormalized_for_undemonstrated_components": self.renormalized,
            "marking": self.marking,
            "notes": self.notes,
            "components": [
                {
                    "key": c.key,
                    "name": c.name,
                    "weight": c.weight,
                    "value": None if c.value is None else round(c.value, 4),
                    "status": "scored" if c.demonstrated else "not_demonstrated",
                    "detail": c.detail,
                }
                for c in self.components
            ],
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _latency_score(actual: float, target: float) -> float:
    """1.0 at or under target, decaying linearly to 0.0 at four times target."""
    if actual <= target:
        return 1.0
    if actual >= target * 4:
        return 0.0
    return _clamp(1.0 - (actual - target) / (target * 3))


def load_scorecard(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("team") != "white":
        raise ConfigurationError("scorecard is not the White Team scorecard")
    return data


def score_exercise(
    control: ExerciseControl,
    scorecard: dict[str, Any],
    *,
    report: dict[str, Any] | None = None,
    stop_target_seconds: float = DEFAULT_STOP_TARGET_SECONDS,
    decision_target_seconds: float = DEFAULT_DECISION_TARGET_SECONDS,
    marking: str = "TRAINING_OR_ENGINEERING_USE_ONLY",
) -> ScoreResult:
    state = control.state()
    weights = {k: v["weight"] for k, v in scorecard["components"].items()}
    notes: list[str] = []

    # --- automatic failures, evaluated first -------------------------------
    auto_failures: list[str] = []
    if state.post_stop_activity > 0:
        auto_failures.append(
            f"continuing after a mandatory stop condition ({state.post_stop_activity} activities)"
        )
    if state.out_of_scope_accepted > 0:
        auto_failures.append(
            f"allowing unauthorized scope expansion ({state.out_of_scope_accepted} activities)"
        )

    # --- A: authorization and scope control --------------------------------
    adversarial = state.activities_refused + state.out_of_scope_accepted + state.post_stop_activity
    if adversarial == 0:
        a_value: float | None = None
        a_detail = "no out-of-scope or post-stop activity was attempted; control never tested"
    else:
        a_value = _clamp(state.activities_refused / adversarial)
        a_detail = (
            f"{state.activities_refused} of {adversarial} improper attempts were refused"
        )

    # --- G: governance and decision quality --------------------------------
    if not state.decisions:
        g_value: float | None = None
        g_detail = "no governance decisions were recorded"
    else:
        latencies = [_latency_score(d.latency_seconds, decision_target_seconds) for d in state.decisions]
        g_value = sum(latencies) / len(latencies)
        g_detail = (
            f"{len(state.decisions)} decisions, all with recorded rationale; "
            f"mean latency score {g_value:.2f} against a {decision_target_seconds:.0f}s target"
        )

    # --- S: safety and stop-response performance ---------------------------
    latency = control.stop_latency_seconds()
    if state.stopped_at is None:
        s_value: float | None = None
        s_detail = "no stop condition was declared; stop response was never demonstrated"
    elif latency is None:
        s_value = 0.0
        s_detail = "a stop was declared but never acknowledged"
    else:
        s_value = _latency_score(latency, stop_target_seconds)
        s_detail = f"stop acknowledged in {latency:.0f}s against a {stop_target_seconds:.0f}s target"

    # --- E: evidence integrity ---------------------------------------------
    try:
        count = control.ledger.verify()
        e_value: float | None = 1.0
        e_detail = f"hash chain verified across {count} records"
    except IntegrityError as exc:
        e_value = 0.0
        e_detail = f"ledger integrity FAILED: {exc}"
        auto_failures.append(f"evidence ledger failed verification: {exc}")

    # --- Q: reporting quality ----------------------------------------------
    if report is None:
        q_value: float | None = None
        q_detail = "no after-action report was supplied"
    else:
        present = [s for s in REQUIRED_REPORT_SECTIONS if str(report.get(s, "")).strip()]
        q_value = len(present) / len(REQUIRED_REPORT_SECTIONS)
        missing = sorted(set(REQUIRED_REPORT_SECTIONS) - set(present))
        q_detail = (
            f"{len(present)}/{len(REQUIRED_REPORT_SECTIONS)} required sections present"
            + (f"; missing: {', '.join(missing)}" if missing else "")
        )

    components = [
        ComponentScore("A", "authorization and scope control", weights["A"], a_value, a_detail),
        ComponentScore("G", "governance and decision quality", weights["G"], g_value, g_detail),
        ComponentScore("S", "safety and stop-response performance", weights["S"], s_value, s_detail),
        ComponentScore("E", "evidence integrity", weights["E"], e_value, e_detail),
        ComponentScore("Q", "reporting quality", weights["Q"], q_value, q_detail),
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
        pass_threshold=float(scorecard.get("pass_threshold", 0.9)),
        marking=marking,
        renormalized=renormalized,
        notes=notes,
    )
