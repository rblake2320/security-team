from __future__ import annotations

from pathlib import Path

import pytest

from aegis_green.coverage import Asset, DefensibilityModel, TechniqueControl
from aegis_green.scoring import load_scorecard, score_defensibility
from aegis_green.telemetry import DataSource

SCORECARD = Path(__file__).resolve().parents[1] / "config" / "scorecard.json"

GOOD = {"device_completeness": 5, "data_field_completeness": 5, "timeliness": 5,
        "consistency": 5, "retention": 5}
MEDIOCRE = {"device_completeness": 3, "data_field_completeness": 3, "timeliness": 3,
            "consistency": 3, "retention": 3}


@pytest.fixture
def scorecard():
    return load_scorecard(SCORECARD)


def strong_model() -> DefensibilityModel:
    return DefensibilityModel(
        [Asset.create("srv-1", "App", "critical"), Asset.create("srv-2", "DB", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1", "srv-2"])],
        [
            TechniqueControl.create("T1110", "detected", must_detect=True, evidence="BT-IDENTITY-001"),
            TechniqueControl.create("T1059", "prevented", must_detect=True, evidence="exec policy"),
        ],
    )


def test_strong_environment_passes(scorecard):
    result = score_defensibility(
        strong_model(), scorecard,
        hardening_results={"passed": 100, "total": 100, "baseline": "CIS L1"},
        response_capabilities=["runbook_documented", "runbook_exercised",
                               "backup_restore_tested", "rollback_tested"],
        lifecycle_stages=["design_review", "pre_merge_checks",
                          "pre_production_acceptance", "production_monitoring"],
    )
    assert result.auto_failures == []
    assert result.status == "PASS"


def test_critical_gap_fails_despite_everything_else_being_perfect(scorecard):
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical"), Asset.create("srv-2", "DB", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],  # srv-2 is dark
        [TechniqueControl.create("T1110", "detected", must_detect=True, evidence="rule")],
    )
    result = score_defensibility(
        model, scorecard,
        hardening_results={"passed": 100, "total": 100},
        response_capabilities=list(("runbook_documented", "runbook_exercised",
                                    "backup_restore_tested", "rollback_tested")),
        lifecycle_stages=list(("design_review", "pre_merge_checks",
                               "pre_production_acceptance", "production_monitoring")),
    )
    assert result.status == "FAILED"
    assert any("below 100%" in f for f in result.auto_failures)


def test_observability_multiplies_breadth_by_quality(scorecard):
    """Wide-but-poor and narrow-but-excellent are both weak; averaging would let one
    hide the other."""
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "standard")],
        [DataSource.create("logs", MEDIOCRE, ["srv-1"])],
        [],
    )
    o = {c.key: c.value for c in score_defensibility(model, scorecard).components}["O"]
    assert o == pytest.approx(0.6)  # 100% breadth * 3.0/5 quality


def test_undemonstrated_components_are_excluded(scorecard):
    result = score_defensibility(strong_model(), scorecard)
    by_key = {c.key: c for c in result.components}
    assert by_key["H"].value is None
    assert by_key["R"].value is None
    assert by_key["L"].value is None
    assert result.renormalized is True
    assert result.notes


def test_untested_restore_lowers_response_readiness(scorecard):
    result = score_defensibility(
        strong_model(), scorecard,
        response_capabilities=["runbook_documented"],  # written but never exercised
    )
    assert {c.key: c.value for c in result.components}["R"] == pytest.approx(0.25)


def test_bolt_on_lifecycle_scores_lower_than_design_time(scorecard):
    late = score_defensibility(strong_model(), scorecard,
                               lifecycle_stages=["production_monitoring"])
    early = score_defensibility(
        strong_model(), scorecard,
        lifecycle_stages=["design_review", "pre_merge_checks",
                          "pre_production_acceptance", "production_monitoring"],
    )
    late_l = {c.key: c.value for c in late.components}["L"]
    early_l = {c.key: c.value for c in early.components}["L"]
    assert late_l < early_l


def test_detection_effectiveness_counts_prevention(scorecard):
    d = {c.key: c.value for c in score_defensibility(strong_model(), scorecard).components}["D"]
    assert d == 1.0


def test_wrong_team_scorecard_rejected():
    from aegis_green.errors import ConfigurationError
    other = Path(__file__).resolve().parents[2] / "yellow-team" / "config" / "scorecard.json"
    with pytest.raises(ConfigurationError, match="not the Green"):
        load_scorecard(other)
