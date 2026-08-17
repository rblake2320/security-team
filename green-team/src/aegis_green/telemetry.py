"""Telemetry inventory and data-quality scoring, following DeTT&CT.

DeTT&CT (Rabobank CDC) scores every data source across five dimensions, each 0-5:

  device_completeness      - is the source present on all the systems it should be?
  data_field_completeness  - does each event carry the fields a detection needs?
  timeliness               - how quickly does the event arrive?
  consistency              - is the format stable enough to write rules against?
  retention                - how far back can it be queried?

The reason to model quality rather than a boolean "we have logs" is that a source
present on 40% of hosts, arriving an hour late, with three weeks of retention, will
be counted as coverage by a checkbox inventory and will still miss the incident.
A source is only credited as providing visibility once its quality clears a floor.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError

DIMENSIONS = (
    "device_completeness",
    "data_field_completeness",
    "timeliness",
    "consistency",
    "retention",
)
MIN_SCORE, MAX_SCORE = 0, 5

# A source scoring below this on the mean of its dimensions is inventory, not
# visibility. Chosen to match DeTT&CT guidance that low-scoring sources should not
# be relied on for detection engineering.
VISIBILITY_FLOOR = 3.0

# Device completeness is special-cased: a perfectly formatted, instant, well-retained
# log that only exists on some of the fleet leaves the rest of the fleet dark.
DEVICE_COMPLETENESS_FLOOR = 3


@dataclass(frozen=True)
class DataSource:
    name: str
    scores: dict[str, int]
    applies_to: tuple[str, ...]

    @staticmethod
    def create(name: str, scores: dict[str, Any], applies_to: list[str]) -> "DataSource":
        if not isinstance(name, str) or not name.strip():
            raise ConfigurationError("data source name is required")
        missing = sorted(set(DIMENSIONS) - set(scores))
        if missing:
            raise ConfigurationError(
                f"{name}: missing quality dimension(s): {', '.join(missing)}"
            )
        unknown = sorted(set(scores) - set(DIMENSIONS))
        if unknown:
            raise ConfigurationError(f"{name}: unknown dimension(s): {', '.join(unknown)}")
        clean: dict[str, int] = {}
        for dimension in DIMENSIONS:
            value = scores[dimension]
            if not isinstance(value, int) or isinstance(value, bool):
                raise ConfigurationError(f"{name}.{dimension} must be an integer 0-5")
            if not MIN_SCORE <= value <= MAX_SCORE:
                raise ConfigurationError(f"{name}.{dimension} must be between 0 and 5")
            clean[dimension] = value
        if not applies_to:
            raise ConfigurationError(f"{name}: must apply to at least one asset")
        return DataSource(
            name=name.strip(),
            scores=clean,
            applies_to=tuple(sorted({a.strip() for a in applies_to if str(a).strip()})),
        )

    @property
    def quality(self) -> float:
        return sum(self.scores.values()) / len(DIMENSIONS)

    @property
    def provides_visibility(self) -> bool:
        """Whether this source may be credited as real visibility."""
        return (
            self.quality >= VISIBILITY_FLOOR
            and self.scores["device_completeness"] >= DEVICE_COMPLETENESS_FLOOR
        )

    def weakest_dimensions(self) -> list[str]:
        floor = min(self.scores.values())
        return sorted(d for d, v in self.scores.items() if v == floor)

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "scores": dict(self.scores),
            "applies_to": list(self.applies_to),
            "quality": round(self.quality, 2),
            "provides_visibility": self.provides_visibility,
            "weakest_dimensions": self.weakest_dimensions(),
        }


def inventory_summary(sources: list[DataSource]) -> dict[str, Any]:
    if not sources:
        return {"sources": 0, "mean_quality": 0.0, "providing_visibility": 0, "blind_sources": []}
    crediting = [s for s in sources if s.provides_visibility]
    return {
        "sources": len(sources),
        "mean_quality": round(sum(s.quality for s in sources) / len(sources), 2),
        "providing_visibility": len(crediting),
        # Named explicitly so the gap is actionable rather than a percentage.
        "blind_sources": [
            {"name": s.name, "quality": round(s.quality, 2), "weakest": s.weakest_dimensions()}
            for s in sources if not s.provides_visibility
        ],
    }
