"""Asset registry, telemetry coverage, and must-detect technique tracking.

Green's two automatic failures live here:

  * telemetry coverage for critical assets below 100%
  * any designated must-detect technique neither detected nor prevented

Note the second one carefully: *neither detected nor prevented*. A technique that is
prevented outright does not also need a detection to pass — blocking the attack is a
better outcome than watching it. Treating prevention as non-compliance would push
teams toward alerting on things they could simply have stopped.

Coverage for an asset is only credited when a data source that actually applies to
that asset clears the DeTT&CT quality floor. An inventory row is not visibility.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError
from .telemetry import DataSource

CRITICALITIES = ("critical", "high", "standard")
# How a must-detect technique is handled. "prevented" and "detected" both satisfy
# the requirement; "none" is the automatic failure.
HANDLING = ("detected", "prevented", "none")


@dataclass(frozen=True)
class Asset:
    asset_id: str
    name: str
    criticality: str

    @staticmethod
    def create(asset_id: str, name: str, criticality: str) -> "Asset":
        if not asset_id.strip() or not name.strip():
            raise ConfigurationError("asset id and name are required")
        if criticality not in CRITICALITIES:
            raise ConfigurationError(f"criticality must be one of {CRITICALITIES}")
        return Asset(asset_id.strip(), name.strip(), criticality)


@dataclass(frozen=True)
class TechniqueControl:
    """An ATT&CK technique and how this environment handles it."""

    technique: str
    handling: str
    must_detect: bool
    evidence: str

    @staticmethod
    def create(technique: str, handling: str, *, must_detect: bool, evidence: str) -> "TechniqueControl":
        if not technique.strip():
            raise ConfigurationError("technique id is required")
        if handling not in HANDLING:
            raise ConfigurationError(f"handling must be one of {HANDLING}")
        if handling != "none" and not evidence.strip():
            raise ConfigurationError(
                f"{technique}: claiming '{handling}' requires evidence (rule id, control, or test)"
            )
        return TechniqueControl(technique.strip(), handling, must_detect, evidence.strip())

    @property
    def is_covered(self) -> bool:
        return self.handling in ("detected", "prevented")

    def to_payload(self) -> dict[str, Any]:
        return {
            "technique": self.technique,
            "handling": self.handling,
            "must_detect": self.must_detect,
            "covered": self.is_covered,
            "evidence": self.evidence,
        }


class DefensibilityModel:
    def __init__(
        self,
        assets: list[Asset],
        sources: list[DataSource],
        techniques: list[TechniqueControl],
    ) -> None:
        ids = [a.asset_id for a in assets]
        if len(ids) != len(set(ids)):
            raise ConfigurationError("duplicate asset ids")
        names = [t.technique for t in techniques]
        if len(names) != len(set(names)):
            raise ConfigurationError("duplicate technique entries")
        # A source that points at an unknown asset is almost always a typo, and it
        # would silently inflate coverage.
        known = set(ids)
        for source in sources:
            unknown = sorted(set(source.applies_to) - known)
            if unknown:
                raise ConfigurationError(
                    f"{source.name}: applies_to references unknown asset(s): {', '.join(unknown)}"
                )
        self.assets = assets
        self.sources = sources
        self.techniques = techniques

    # ---- coverage ------------------------------------------------------------

    def assets_with_visibility(self) -> set[str]:
        covered: set[str] = set()
        for source in self.sources:
            if source.provides_visibility:
                covered.update(source.applies_to)
        return covered

    def telemetry_coverage(self, criticality: str | None = None) -> dict[str, Any]:
        pool = [a for a in self.assets if criticality is None or a.criticality == criticality]
        if not pool:
            return {"assets": 0, "covered": 0, "ratio": 1.0, "uncovered": []}
        visible = self.assets_with_visibility()
        covered = [a for a in pool if a.asset_id in visible]
        uncovered = sorted(a.asset_id for a in pool if a.asset_id not in visible)
        return {
            "assets": len(pool),
            "covered": len(covered),
            "ratio": len(covered) / len(pool),
            "uncovered": uncovered,
        }

    def must_detect_status(self) -> dict[str, Any]:
        required = [t for t in self.techniques if t.must_detect]
        unhandled = sorted(t.technique for t in required if not t.is_covered)
        return {
            "must_detect": len(required),
            "handled": len(required) - len(unhandled),
            "unhandled": unhandled,
            "prevented": sorted(t.technique for t in required if t.handling == "prevented"),
        }

    def detection_effectiveness(self) -> float:
        if not self.techniques:
            return 0.0
        return sum(1 for t in self.techniques if t.is_covered) / len(self.techniques)

    # ---- automatic failures --------------------------------------------------

    def automatic_failures(self) -> list[str]:
        failures: list[str] = []
        critical = self.telemetry_coverage("critical")
        if critical["assets"] and critical["ratio"] < 1.0:
            failures.append(
                "telemetry coverage for critical assets is below 100%: "
                f"{critical['covered']}/{critical['assets']} "
                f"(uncovered: {', '.join(critical['uncovered'])})"
            )
        must = self.must_detect_status()
        if must["unhandled"]:
            failures.append(
                "designated must-detect technique(s) neither detected nor prevented: "
                + ", ".join(must["unhandled"])
            )
        return failures
