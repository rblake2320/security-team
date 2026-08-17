"""STRIDE modelling and adversarial design review, including Orange's three
automatic failures."""
from __future__ import annotations

import pytest

from aegis_orange.errors import ConfigurationError, UnsafeTestError
from aegis_orange.review import AttackPath, DesignReview, Recommendation, SafeTest
from aegis_orange.stride import (
    APPLICABLE,
    CATEGORIES,
    DATA_FLOW,
    DATA_STORE,
    ELEVATION,
    EXTERNAL_ENTITY,
    PROCESS,
    SPOOFING,
    Element,
    coverage,
)


# ---- STRIDE ---------------------------------------------------------------

def test_six_categories():
    assert len(CATEGORIES) == 6


def test_external_entity_cannot_be_elevated():
    # Elevation of privilege is not a threat *to* an external entity; scoring it as
    # a gap would punish reviewers for skipping an impossible threat.
    assert ELEVATION not in APPLICABLE[EXTERNAL_ENTITY]
    assert SPOOFING in APPLICABLE[EXTERNAL_ENTITY]


def test_process_carries_all_six():
    assert set(APPLICABLE[PROCESS]) == set(CATEGORIES)


def test_data_flow_excludes_spoofing_and_elevation():
    assert SPOOFING not in APPLICABLE[DATA_FLOW]
    assert ELEVATION not in APPLICABLE[DATA_FLOW]


def test_full_coverage_of_applicable_pairs():
    elements = [Element.create("E1", "User", EXTERNAL_ENTITY)]
    result = coverage(elements, {"E1": list(APPLICABLE[EXTERNAL_ENTITY])})
    assert result["coverage"] == 1.0
    assert result["gaps"] == []


def test_gaps_are_reported_with_the_property_violated():
    elements = [Element.create("E1", "User", EXTERNAL_ENTITY)]
    result = coverage(elements, {"E1": [SPOOFING]})
    assert len(result["gaps"]) == 1
    assert result["gaps"][0]["category"] == "repudiation"
    assert result["gaps"][0]["violates"] == "non-repudiation"


def test_trust_boundary_gaps_are_called_out_separately():
    elements = [
        Element.create("E1", "Public API", PROCESS, crosses_trust_boundary=True),
        Element.create("E2", "Internal cache", DATA_STORE),
    ]
    result = coverage(elements, {"E1": [SPOOFING], "E2": []})
    assert result["trust_boundary_gaps"]
    assert all(g["element_id"] == "E1" for g in result["trust_boundary_gaps"])


def test_unknown_element_in_coverage_is_rejected():
    with pytest.raises(ConfigurationError, match="unknown element"):
        coverage([Element.create("E1", "User", EXTERNAL_ENTITY)], {"E9": [SPOOFING]})


def test_unknown_category_is_rejected():
    with pytest.raises(ConfigurationError, match="unknown STRIDE category"):
        coverage([Element.create("E1", "User", EXTERNAL_ENTITY)], {"E1": ["vibes"]})


# ---- attack paths ---------------------------------------------------------

def test_attack_path_requires_entry_point_and_impact():
    with pytest.raises(ConfigurationError, match="entry point and an impact"):
        AttackPath.create("P1", "Bad thing", "critical", SPOOFING, "", "total compromise")


def test_missed_seeded_critical_is_an_automatic_failure():
    seeded = AttackPath.create("P1", "Auth bypass", "critical", SPOOFING,
                               "public login", "full account takeover", seeded=True)
    review = DesignReview(review_id="R1", seeded_paths=[seeded])
    assert review.missed_seeded(severity="critical") == ["P1"]
    assert any("seeded critical" in f for f in review.automatic_failures())


def test_discovered_seeded_path_clears_the_failure():
    seeded = AttackPath.create("P1", "Auth bypass", "critical", SPOOFING,
                               "public login", "full account takeover", seeded=True)
    found = AttackPath.create("P1", "Auth bypass", "critical", SPOOFING,
                              "public login", "full account takeover")
    review = DesignReview(review_id="R1", found_paths=[found], seeded_paths=[seeded])
    assert review.automatic_failures() == []
    assert review.discovery_rate() == 1.0


def test_missed_non_critical_seeded_path_is_not_an_auto_failure():
    seeded = AttackPath.create("P2", "Info leak", "medium", SPOOFING, "api", "minor leak", seeded=True)
    review = DesignReview(review_id="R1", seeded_paths=[seeded])
    assert review.automatic_failures() == []
    assert review.discovery_rate() == 0.0


def test_prioritization_accuracy_penalises_wrong_severity():
    seeded = AttackPath.create("P1", "Auth bypass", "critical", SPOOFING, "login", "takeover", seeded=True)
    found = AttackPath.create("P1", "Auth bypass", "low", SPOOFING, "login", "takeover")
    review = DesignReview(review_id="R1", found_paths=[found], seeded_paths=[seeded])
    assert review.discovery_rate() == 1.0       # they found it
    assert review.prioritization_accuracy() == 0.0  # but rated it wrong


# ---- recommendations and tests --------------------------------------------

def test_critical_recommendation_requires_acceptance_criteria():
    with pytest.raises(ConfigurationError, match="acceptance criteria"):
        Recommendation.create("R1", "P1", "critical", "Fix the auth check", "   ")


def test_non_critical_recommendation_may_omit_criteria():
    assert Recommendation.create("R2", "P2", "low", "Tidy the header", "").severity == "low"


def test_unsafe_test_cannot_be_recorded_as_executed():
    with pytest.raises(UnsafeTestError, match="not safe"):
        SafeTest.create("T1", "P1", "Flood the API", "denial_of_service", executed=True)


def test_unsafe_test_may_be_proposed_but_not_executed():
    # Recording that it was *considered and rejected* is legitimate.
    test = SafeTest.create("T1", "P1", "Flood the API", "denial_of_service", executed=False)
    assert test.is_safe is False
    assert DesignReview(review_id="R", tests=[test]).automatic_failures() == []


def test_safe_test_conversion_is_measured():
    found = AttackPath.create("P1", "IDOR", "high", SPOOFING, "api", "cross-tenant read")
    test = SafeTest.create("T1", "P1", "Assert 403 on other tenant id", "functional", executed=True)
    review = DesignReview(review_id="R", found_paths=[found], tests=[test])
    assert review.test_conversion() == 1.0


def test_actionable_ratio_counts_only_recommendations_with_criteria():
    found = AttackPath.create("P1", "IDOR", "high", SPOOFING, "api", "cross-tenant read")
    rec = Recommendation.create("R1", "P1", "high", "Scope the query by tenant",
                                "Request for another tenant returns 403 in tests/test_tenant.py")
    review = DesignReview(review_id="R", found_paths=[found], recommendations=[rec])
    assert review.actionable_ratio() == 1.0
