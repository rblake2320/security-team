"""STRIDE-per-element threat modelling.

STRIDE (Kohnfelder & Garg, 1999) classifies threats as Spoofing, Tampering,
Repudiation, Information disclosure, Denial of service, and Elevation of privilege.
Applied "per element", each category is considered against every element of a data
flow diagram and against every trust boundary crossing.

The applicability matrix below is the classic Microsoft mapping. It matters because
it turns "did we think hard enough?" into a countable question: an external entity
can be spoofed and can repudiate, but it is not a thing you can elevate privilege
*on*. Scoring completeness against the full six for every element would punish
reviewers for not inventing threats that cannot exist, and would hide the elements
where a real category was genuinely skipped.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError

SPOOFING = "spoofing"
TAMPERING = "tampering"
REPUDIATION = "repudiation"
INFO_DISCLOSURE = "information_disclosure"
DENIAL_OF_SERVICE = "denial_of_service"
ELEVATION = "elevation_of_privilege"

CATEGORIES = (
    SPOOFING, TAMPERING, REPUDIATION, INFO_DISCLOSURE, DENIAL_OF_SERVICE, ELEVATION,
)

# The security property each category violates — used to explain findings to builders,
# which is the point of Orange rather than just naming the category.
VIOLATES = {
    SPOOFING: "authentication",
    TAMPERING: "integrity",
    REPUDIATION: "non-repudiation",
    INFO_DISCLOSURE: "confidentiality",
    DENIAL_OF_SERVICE: "availability",
    ELEVATION: "authorization",
}

EXTERNAL_ENTITY = "external_entity"
PROCESS = "process"
DATA_STORE = "data_store"
DATA_FLOW = "data_flow"

ELEMENT_TYPES = (EXTERNAL_ENTITY, PROCESS, DATA_STORE, DATA_FLOW)

APPLICABLE: dict[str, tuple[str, ...]] = {
    EXTERNAL_ENTITY: (SPOOFING, REPUDIATION),
    PROCESS: CATEGORIES,
    DATA_STORE: (TAMPERING, REPUDIATION, INFO_DISCLOSURE, DENIAL_OF_SERVICE),
    DATA_FLOW: (TAMPERING, INFO_DISCLOSURE, DENIAL_OF_SERVICE),
}


@dataclass(frozen=True)
class Element:
    element_id: str
    name: str
    element_type: str
    crosses_trust_boundary: bool

    @staticmethod
    def create(
        element_id: str, name: str, element_type: str, *, crosses_trust_boundary: bool = False
    ) -> "Element":
        if not element_id.strip() or not name.strip():
            raise ConfigurationError("element id and name are required")
        if element_type not in ELEMENT_TYPES:
            raise ConfigurationError(f"element_type must be one of {ELEMENT_TYPES}")
        return Element(element_id.strip(), name.strip(), element_type, crosses_trust_boundary)

    @property
    def applicable_categories(self) -> tuple[str, ...]:
        return APPLICABLE[self.element_type]

    def to_payload(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "name": self.name,
            "element_type": self.element_type,
            "crosses_trust_boundary": self.crosses_trust_boundary,
            "applicable_categories": list(self.applicable_categories),
        }


def coverage(elements: list[Element], considered: dict[str, list[str]]) -> dict[str, Any]:
    """How much of the applicable STRIDE surface was actually considered.

    `considered` maps element_id -> categories the reviewer examined. Elements that
    cross a trust boundary are reported separately: a gap there is worth more than a
    gap on an internal element, because trust boundaries are where the interesting
    threats live.
    """
    known = {e.element_id for e in elements}
    unknown = sorted(set(considered) - known)
    if unknown:
        raise ConfigurationError(f"coverage references unknown element(s): {', '.join(unknown)}")

    total_pairs = 0
    covered_pairs = 0
    gaps: list[dict[str, Any]] = []
    boundary_gaps: list[dict[str, Any]] = []

    for element in elements:
        seen = {c for c in considered.get(element.element_id, []) if c in CATEGORIES}
        invalid = set(considered.get(element.element_id, [])) - set(CATEGORIES)
        if invalid:
            raise ConfigurationError(
                f"{element.element_id}: unknown STRIDE category: {', '.join(sorted(invalid))}"
            )
        for category in element.applicable_categories:
            total_pairs += 1
            if category in seen:
                covered_pairs += 1
            else:
                gap = {
                    "element_id": element.element_id,
                    "category": category,
                    "violates": VIOLATES[category],
                }
                gaps.append(gap)
                if element.crosses_trust_boundary:
                    boundary_gaps.append(gap)

    return {
        "elements": len(elements),
        "applicable_pairs": total_pairs,
        "considered_pairs": covered_pairs,
        "coverage": (covered_pairs / total_pairs) if total_pairs else 0.0,
        "gaps": gaps,
        "trust_boundary_gaps": boundary_gaps,
    }
