"""Adversarial design review: attack paths, recommendations, and safe tests.

Orange's scorecard test is "a pre-production adversarial design review of a nearly
finished architecture, known findings withheld" — so the model has a first-class
notion of *seeded* attack paths that the reviewer was not told about. Missing a
seeded critical path is an automatic failure; that is how attack-path discovery
gets measured instead of asserted.

Two other automatic failures are enforced at the point of definition:
  * a critical recommendation without actionable acceptance criteria is refused
  * an unsafe test cannot be marked as executed
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .errors import ConfigurationError, UnsafeTestError
from .stride import CATEGORIES

SEVERITIES = ("critical", "high", "medium", "low")

# A test proposed during design review runs against pre-production systems next to
# builders. Anything that destroys data, degrades availability, or touches
# production is out of bounds for this activity regardless of intent.
UNSAFE_KINDS = ("destructive", "denial_of_service", "production_data", "unbounded_load")


@dataclass(frozen=True)
class AttackPath:
    path_id: str
    title: str
    severity: str
    stride_category: str
    entry_point: str
    impact: str
    seeded: bool = False

    @staticmethod
    def create(
        path_id: str, title: str, severity: str, stride_category: str,
        entry_point: str, impact: str, *, seeded: bool = False,
    ) -> "AttackPath":
        if not path_id.strip() or not title.strip():
            raise ConfigurationError("path id and title are required")
        if severity not in SEVERITIES:
            raise ConfigurationError(f"severity must be one of {SEVERITIES}")
        if stride_category not in CATEGORIES:
            raise ConfigurationError(f"stride_category must be one of {CATEGORIES}")
        if not entry_point.strip() or not impact.strip():
            raise ConfigurationError(
                f"{path_id}: an attack path needs both an entry point and an impact; "
                "without them a builder cannot act on it"
            )
        return AttackPath(
            path_id.strip(), title.strip(), severity, stride_category,
            entry_point.strip(), impact.strip(), seeded,
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "path_id": self.path_id, "title": self.title, "severity": self.severity,
            "stride_category": self.stride_category, "entry_point": self.entry_point,
            "impact": self.impact, "seeded": self.seeded,
        }


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    path_id: str
    severity: str
    action: str
    acceptance_criteria: str

    @staticmethod
    def create(
        recommendation_id: str, path_id: str, severity: str, action: str,
        acceptance_criteria: str,
    ) -> "Recommendation":
        if severity not in SEVERITIES:
            raise ConfigurationError(f"severity must be one of {SEVERITIES}")
        if not action.strip():
            raise ConfigurationError("recommendation action is required")
        if severity == "critical" and not acceptance_criteria.strip():
            # Scorecard auto-failure: "any critical recommendation without actionable
            # acceptance criteria". Refused here so it cannot reach a report.
            raise ConfigurationError(
                f"{recommendation_id}: a critical recommendation requires actionable "
                "acceptance criteria — otherwise nobody can tell when it is done"
            )
        return Recommendation(
            recommendation_id.strip(), path_id.strip(), severity,
            action.strip(), acceptance_criteria.strip(),
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "recommendation_id": self.recommendation_id, "path_id": self.path_id,
            "severity": self.severity, "action": self.action,
            "acceptance_criteria": self.acceptance_criteria,
        }


@dataclass(frozen=True)
class SafeTest:
    test_id: str
    path_id: str
    description: str
    kind: str
    executed: bool

    @staticmethod
    def create(
        test_id: str, path_id: str, description: str, kind: str, *, executed: bool = False
    ) -> "SafeTest":
        if not test_id.strip() or not description.strip():
            raise ConfigurationError("test id and description are required")
        if kind in UNSAFE_KINDS and executed:
            raise UnsafeTestError(
                f"{test_id}: '{kind}' testing is not safe during a pre-production design "
                "review and must not be recorded as executed"
            )
        return SafeTest(test_id.strip(), path_id.strip(), description.strip(), kind, executed)

    @property
    def is_safe(self) -> bool:
        return self.kind not in UNSAFE_KINDS

    def to_payload(self) -> dict[str, Any]:
        return {
            "test_id": self.test_id, "path_id": self.path_id, "kind": self.kind,
            "description": self.description, "executed": self.executed, "safe": self.is_safe,
        }


@dataclass
class DesignReview:
    """A completed adversarial design review."""

    review_id: str
    found_paths: list[AttackPath] = field(default_factory=list)
    seeded_paths: list[AttackPath] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    tests: list[SafeTest] = field(default_factory=list)
    knowledge_transfer: list[str] = field(default_factory=list)

    # ---- discovery ----------------------------------------------------------

    def missed_seeded(self, *, severity: str | None = None) -> list[str]:
        found = {p.path_id for p in self.found_paths}
        return sorted(
            p.path_id for p in self.seeded_paths
            if p.path_id not in found and (severity is None or p.severity == severity)
        )

    def discovery_rate(self) -> float | None:
        if not self.seeded_paths:
            return None
        found = {p.path_id for p in self.found_paths}
        hits = sum(1 for p in self.seeded_paths if p.path_id in found)
        return hits / len(self.seeded_paths)

    def prioritization_accuracy(self) -> float | None:
        """Did the reviewer rate the seeded paths at the severity they were seeded at?

        Finding a critical path and calling it low is a prioritization failure even
        though discovery succeeded — builders triage by severity.
        """
        seeded_by_id = {p.path_id: p for p in self.seeded_paths}
        matched = [p for p in self.found_paths if p.path_id in seeded_by_id]
        if not matched:
            return None
        correct = sum(1 for p in matched if p.severity == seeded_by_id[p.path_id].severity)
        return correct / len(matched)

    # ---- usefulness ---------------------------------------------------------

    def actionable_ratio(self) -> float | None:
        """Fraction of findings that came with a recommendation carrying criteria."""
        if not self.found_paths:
            return None
        by_path = {r.path_id for r in self.recommendations if r.acceptance_criteria}
        return sum(1 for p in self.found_paths if p.path_id in by_path) / len(self.found_paths)

    def test_conversion(self) -> float | None:
        """Fraction of findings converted into a safe, executed test."""
        if not self.found_paths:
            return None
        tested = {t.path_id for t in self.tests if t.is_safe and t.executed}
        return sum(1 for p in self.found_paths if p.path_id in tested) / len(self.found_paths)

    # ---- automatic failures --------------------------------------------------

    def automatic_failures(self) -> list[str]:
        failures: list[str] = []
        missed_critical = self.missed_seeded(severity="critical")
        if missed_critical:
            failures.append(
                "seeded critical attack path(s) missed: " + ", ".join(missed_critical)
            )
        unsafe_executed = [t.test_id for t in self.tests if t.executed and not t.is_safe]
        if unsafe_executed:
            failures.append("unsafe testing performed: " + ", ".join(sorted(unsafe_executed)))
        weak_criticals = [
            r.recommendation_id for r in self.recommendations
            if r.severity == "critical" and not r.acceptance_criteria.strip()
        ]
        if weak_criticals:
            failures.append(
                "critical recommendation(s) without acceptance criteria: "
                + ", ".join(sorted(weak_criticals))
            )
        return failures
