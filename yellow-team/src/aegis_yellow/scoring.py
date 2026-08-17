"""Capability scoring for the Yellow Team.

    S_Y = 0.25B + 0.20T + 0.20P + 0.20F + 0.15M

B is anchored in NIST SSDF v1.1 practice coverage, P in the SLSA v1.0 Build track,
and F in whether findings were actually closed with durable evidence. Nothing here
is a self-assessment slider: every component reads from the register, the
attestations, or the build evidence.

Same two program rules as every other team: auto-failures are evaluated before
aggregation, and a component that was never demonstrated is excluded and the
remaining weights renormalized rather than being scored as 0 or 1.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, IntegrityError
from .register import EVIDENCE_REQUIRED, FindingsRegister
from .slsa import BuildEvidence, determine_level
from .ssdf import Attestation, coverage

DEFAULT_REMEDIATION_TARGET_SECONDS = 7 * 24 * 3600.0  # one week for high/critical

REQUIRED_DOCS = ("readme", "architecture", "runbook", "threat_model")


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
            "team": "yellow",
            "formula": "S_Y = 0.25B + 0.20T + 0.20P + 0.20F + 0.15M",
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
    if data.get("team") != "yellow":
        raise ConfigurationError("scorecard is not the Yellow Team scorecard")
    return data


def score_delivery(
    register: FindingsRegister,
    scorecard: dict[str, Any],
    *,
    attestations: list[Attestation] | None = None,
    build_evidence: BuildEvidence | None = None,
    test_metrics: dict[str, Any] | None = None,
    docs_present: list[str] | None = None,
    remediation_target_seconds: float = DEFAULT_REMEDIATION_TARGET_SECONDS,
    marking: str = "TRAINING_OR_ENGINEERING_USE_ONLY",
) -> ScoreResult:
    weights = {k: v["weight"] for k, v in scorecard["components"].items()}
    notes: list[str] = []
    auto_failures = list(register.automatic_failures())

    findings = register.findings()

    # --- B: secure design and build quality (SSDF practice coverage) --------
    if not attestations:
        b_value: float | None = None
        b_detail = "no SSDF attestations supplied"
    else:
        cov = coverage(attestations)
        b_value = _clamp(cov["coverage"])
        b_detail = (
            f"{cov['implemented']}/{cov['total_practices']} SSDF {cov['ssdf_version']} "
            f"practices implemented"
            + (f"; unattested: {', '.join(cov['unattested'])}" if cov["unattested"] else "")
        )

    # --- T: automated testing ----------------------------------------------
    if not test_metrics:
        t_value: float | None = None
        t_detail = "no test metrics supplied"
    else:
        passed = int(test_metrics.get("passed", 0))
        total = int(test_metrics.get("total", 0))
        if total <= 0:
            raise ConfigurationError("test_metrics.total must be positive")
        pass_rate = passed / total
        # A suite that passes but covers nothing is not evidence, so coverage caps
        # the component when supplied.
        cov_ratio = test_metrics.get("coverage")
        if cov_ratio is None:
            t_value = _clamp(pass_rate)
            t_detail = f"{passed}/{total} tests passing (no coverage figure supplied)"
        else:
            t_value = _clamp(pass_rate) * _clamp(float(cov_ratio))
            t_detail = f"{passed}/{total} tests passing at {float(cov_ratio):.0%} coverage"

    # --- P: pipeline and supply-chain controls (SLSA build track) ----------
    if build_evidence is None:
        p_value: float | None = None
        p_detail = "no SLSA build evidence supplied"
    else:
        slsa = determine_level(build_evidence)
        p_value = slsa["level"] / 3.0
        p_detail = f"SLSA {slsa['level_name']}" + (
            f"; blocking next level: {', '.join(slsa['blocking_next_level'])}"
            if slsa["blocking_next_level"] else ""
        )

    # --- F: remediation quality --------------------------------------------
    serious = [f for f in findings.values() if f.severity in EVIDENCE_REQUIRED]
    if not serious:
        f_value: float | None = None
        f_detail = "no critical or high findings were recorded"
    else:
        closed = [f for f in serious if f.state != "open"]
        with_evidence = [f for f in closed if f.has_durable_evidence]
        closure = len(closed) / len(serious)
        evidence_rate = (len(with_evidence) / len(closed)) if closed else 0.0
        ages = [f.age_seconds for f in closed if f.age_seconds is not None]
        if ages:
            timeliness = sum(
                1.0 if a <= remediation_target_seconds else _clamp(remediation_target_seconds / a)
                for a in ages
            ) / len(ages)
        else:
            timeliness = 0.0
        f_value = _clamp((closure + evidence_rate + timeliness) / 3)
        f_detail = (
            f"{len(closed)}/{len(serious)} serious findings closed; "
            f"{len(with_evidence)}/{max(len(closed),1)} with durable evidence"
        )

    # --- M: maintainability and documentation ------------------------------
    if docs_present is None:
        m_value: float | None = None
        m_detail = "no documentation inventory supplied"
    else:
        have = {d.strip().lower() for d in docs_present if str(d).strip()}
        present = [d for d in REQUIRED_DOCS if d in have]
        m_value = len(present) / len(REQUIRED_DOCS)
        missing = sorted(set(REQUIRED_DOCS) - set(present))
        m_detail = f"{len(present)}/{len(REQUIRED_DOCS)} required documents" + (
            f"; missing: {', '.join(missing)}" if missing else ""
        )

    # Evidence integrity is not a scored component for Yellow, but a corrupt
    # register invalidates every number above it, so it is an automatic failure.
    try:
        register.ledger.verify()
    except IntegrityError as exc:
        auto_failures.append(f"findings register failed integrity verification: {exc}")

    components = [
        ComponentScore("B", "secure design and build quality", weights["B"], b_value, b_detail),
        ComponentScore("T", "automated testing", weights["T"], t_value, t_detail),
        ComponentScore("P", "pipeline and supply-chain controls", weights["P"], p_value, p_detail),
        ComponentScore("F", "remediation quality", weights["F"], f_value, f_detail),
        ComponentScore("M", "maintainability and documentation", weights["M"], m_value, m_detail),
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
