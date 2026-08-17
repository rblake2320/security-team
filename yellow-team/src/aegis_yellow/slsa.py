"""SLSA Build Track level determination (SLSA v1.0).

Levels are *derived from evidence*, never declared. Each level is cumulative and a
claim is refused unless every requirement of that level and all lower levels holds:

  Build L0 — no guarantees.
  Build L1 — a consistent build process, and provenance exists and is distributed
             to consumers. Provenance may be unsigned.
  Build L2 — L1, plus the build runs on a hosted platform (not a workstation) and
             the provenance is signed, tying it to that platform.
  Build L3 — L2, plus the platform isolates builds from one another and prevents
             user-defined build steps from reaching the provenance signing key.

Deliberately conservative: `determine_level` returns the highest level for which
ALL requirements are satisfied, and stops at the first unmet requirement rather
than awarding a level because most of it was met.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError

# Requirement key -> the lowest level at which it becomes mandatory.
REQUIREMENTS: dict[str, tuple[int, str]] = {
    "consistent_build_process": (1, "the producer follows a consistent build process"),
    "provenance_exists": (1, "provenance describing platform, process and inputs exists"),
    "provenance_distributed": (1, "provenance is distributed to consumers"),
    "hosted_build_platform": (2, "builds run on dedicated infrastructure, not a workstation"),
    "provenance_signed": (2, "provenance is signed, tying it to the build platform"),
    "provenance_verified": (2, "consumers verify provenance authenticity"),
    "isolated_builds": (3, "builds cannot influence one another"),
    "signing_key_unreachable": (3, "user-defined build steps cannot reach the signing key"),
}

MAX_LEVEL = 3


@dataclass(frozen=True)
class BuildEvidence:
    """Which SLSA requirements are demonstrated, with a note for each."""

    satisfied: frozenset[str]
    notes: dict[str, str]

    @staticmethod
    def create(evidence: dict[str, Any]) -> "BuildEvidence":
        unknown = sorted(set(evidence) - set(REQUIREMENTS))
        if unknown:
            raise ConfigurationError(f"unknown SLSA requirement key(s): {', '.join(unknown)}")
        satisfied, notes = set(), {}
        for key, value in evidence.items():
            if isinstance(value, bool):
                if value:
                    satisfied.add(key)
                notes[key] = "asserted without a note" if value else "not satisfied"
                continue
            if isinstance(value, dict):
                met = bool(value.get("met"))
                note = str(value.get("note", "")).strip()
                if met and not note:
                    raise ConfigurationError(f"{key}: a satisfied requirement needs a note")
                if met:
                    satisfied.add(key)
                notes[key] = note or "not satisfied"
                continue
            raise ConfigurationError(f"{key}: expected a bool or an object with met/note")
        return BuildEvidence(satisfied=frozenset(satisfied), notes=notes)


def unmet_for_level(evidence: BuildEvidence, level: int) -> list[str]:
    """Requirements still missing for a given level (cumulative)."""
    if not 0 <= level <= MAX_LEVEL:
        raise ConfigurationError(f"level must be between 0 and {MAX_LEVEL}")
    required = [k for k, (lvl, _) in REQUIREMENTS.items() if lvl <= level]
    return sorted(k for k in required if k not in evidence.satisfied)


def determine_level(evidence: BuildEvidence) -> dict[str, Any]:
    achieved = 0
    for level in range(1, MAX_LEVEL + 1):
        if unmet_for_level(evidence, level):
            break
        achieved = level
    next_level = min(achieved + 1, MAX_LEVEL)
    return {
        "slsa_version": "v1.0",
        "track": "build",
        "level": achieved,
        "level_name": f"Build L{achieved}",
        "blocking_next_level": unmet_for_level(evidence, next_level) if achieved < MAX_LEVEL else [],
        "requirement_notes": evidence.notes,
    }
