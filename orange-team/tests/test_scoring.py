from __future__ import annotations

from pathlib import Path

import pytest

from aegis_orange.review import AttackPath, DesignReview, Recommendation, SafeTest
from aegis_orange.scoring import load_scorecard, score_review
from aegis_orange.stride import PROCESS, SPOOFING, TAMPERING, Element

SCORECARD = Path(__file__).resolve().parents[1] / "config" / "scorecard.json"


@pytest.fixture
def scorecard():
    return load_scorecard(SCORECARD)


def seeded_pair():
    seeded = [
        AttackPath.create("P1", "Auth bypass", "critical", SPOOFING,
                          "public login", "account takeover", seeded=True),
        AttackPath.create("P2", "Config tamper", "high", TAMPERING,
                          "admin panel", "persistence", seeded=True),
    ]
    found = [
        AttackPath.create("P1", "Auth bypass", "critical", SPOOFING,
                          "public login", "account takeover"),
        AttackPath.create("P2", "Config tamper", "high", TAMPERING,
                          "admin panel", "persistence"),
    ]
    return seeded, found


def strong_review() -> DesignReview:
    seeded, found = seeded_pair()
    return DesignReview(
        review_id="R-STRONG",
        found_paths=found,
        seeded_paths=seeded,
        recommendations=[
            Recommendation.create("R1", "P1", "critical", "Verify signature server-side",
                                  "Forged token returns 401 in tests/test_auth.py"),
            Recommendation.create("R2", "P2", "high", "Sign config bundles",
                                  "Unsigned bundle is rejected in tests/test_config.py"),
        ],
        tests=[
            SafeTest.create("T1", "P1", "Forged token returns 401", "functional", executed=True),
            SafeTest.create("T2", "P2", "Unsigned bundle rejected", "functional", executed=True),
        ],
        knowledge_transfer=["walkthrough with auth team", "config signing brown-bag"],
    )


def test_strong_review_passes(scorecard):
    result = score_review(strong_review(), scorecard)
    assert result.auto_failures == []
    assert result.status == "PASS"


def test_missed_critical_path_fails_regardless_of_other_scores(scorecard):
    review = strong_review()
    review.found_paths = [p for p in review.found_paths if p.path_id != "P1"]
    result = score_review(review, scorecard)
    assert result.status == "FAILED"
    assert any("seeded critical" in f for f in result.auto_failures)


def test_discovery_is_measured_against_seeded_paths(scorecard):
    review = strong_review()
    review.found_paths = [p for p in review.found_paths if p.path_id != "P2"]
    x = {c.key: c.value for c in score_review(review, scorecard).components}["X"]
    assert x == pytest.approx(0.5)


def test_volume_of_findings_does_not_inflate_discovery(scorecard):
    """Counting findings would reward noise; only seeded hits move X."""
    review = strong_review()
    review.found_paths = review.found_paths + [
        AttackPath.create(f"N{i}", f"Noise {i}", "low", SPOOFING, "somewhere", "little")
        for i in range(10)
    ]
    x = {c.key: c.value for c in score_review(review, scorecard).components}["X"]
    assert x == 1.0  # not more than 1, and not boosted by the noise


def test_no_seeded_paths_means_discovery_is_not_demonstrated(scorecard):
    review = DesignReview(
        review_id="R",
        found_paths=[AttackPath.create("P9", "Thing", "low", SPOOFING, "a", "b")],
    )
    result = score_review(review, scorecard)
    by_key = {c.key: c for c in result.components}
    assert by_key["X"].value is None
    assert result.renormalized is True


def test_stride_coverage_is_reported_alongside_discovery(scorecard):
    elements = [Element.create("E1", "API", PROCESS, crosses_trust_boundary=True)]
    result = score_review(
        strong_review(), scorecard,
        elements=elements,
        stride_considered={"E1": [SPOOFING, TAMPERING]},
    )
    assert any("STRIDE coverage" in n for n in result.notes)
    assert any("trust boundaries" in n for n in result.notes)


def test_unsafe_executed_test_fails_the_review(scorecard):
    review = strong_review()
    # Construct the unsafe record directly: SafeTest.create refuses to build it,
    # which is the guard under test elsewhere.
    review.tests = review.tests + [
        SafeTest("T9", "P1", "Take the service down", "denial_of_service", True)
    ]
    result = score_review(review, scorecard)
    assert result.status == "FAILED"
    assert any("unsafe testing" in f for f in result.auto_failures)


def test_findings_without_acceptance_criteria_lower_usefulness(scorecard):
    review = strong_review()
    review.recommendations = []
    e = {c.key: c.value for c in score_review(review, scorecard).components}["E"]
    assert e == 0.0


def test_wrong_team_scorecard_rejected():
    from aegis_orange.errors import ConfigurationError
    other = Path(__file__).resolve().parents[2] / "green-team" / "config" / "scorecard.json"
    with pytest.raises(ConfigurationError, match="not the Orange"):
        load_scorecard(other)
