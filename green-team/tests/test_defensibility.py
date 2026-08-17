"""Telemetry quality, coverage, and Green's two automatic failures."""
from __future__ import annotations

import pytest

from aegis_green.coverage import Asset, DefensibilityModel, TechniqueControl
from aegis_green.errors import ConfigurationError
from aegis_green.telemetry import DataSource, inventory_summary

GOOD = {"device_completeness": 5, "data_field_completeness": 5, "timeliness": 5,
        "consistency": 5, "retention": 4}
WEAK = {"device_completeness": 1, "data_field_completeness": 2, "timeliness": 2,
        "consistency": 2, "retention": 1}
# High quality everywhere except it only exists on part of the fleet.
PARTIAL_FLEET = {"device_completeness": 1, "data_field_completeness": 5, "timeliness": 5,
                 "consistency": 5, "retention": 5}


def test_high_quality_source_provides_visibility():
    assert DataSource.create("edr", GOOD, ["srv-1"]).provides_visibility is True


def test_low_quality_source_is_inventory_not_visibility():
    assert DataSource.create("syslog", WEAK, ["srv-1"]).provides_visibility is False


def test_source_on_part_of_the_fleet_does_not_count():
    # This is the case a checkbox inventory gets wrong: the log is excellent, but
    # most hosts do not emit it.
    source = DataSource.create("edr", PARTIAL_FLEET, ["srv-1"])
    assert source.quality >= 4.0
    assert source.provides_visibility is False


def test_missing_dimension_is_rejected():
    with pytest.raises(ConfigurationError, match="missing quality dimension"):
        DataSource.create("edr", {"device_completeness": 5}, ["srv-1"])


def test_out_of_range_score_is_rejected():
    bad = dict(GOOD, timeliness=9)
    with pytest.raises(ConfigurationError, match="between 0 and 5"):
        DataSource.create("edr", bad, ["srv-1"])


def test_bool_is_not_an_integer_score():
    bad = dict(GOOD, timeliness=True)
    with pytest.raises(ConfigurationError):
        DataSource.create("edr", bad, ["srv-1"])


def test_weakest_dimensions_are_named():
    assert "device_completeness" in DataSource.create("edr", PARTIAL_FLEET, ["a"]).weakest_dimensions()


def test_source_referencing_unknown_asset_is_rejected():
    # Otherwise a typo silently inflates coverage.
    with pytest.raises(ConfigurationError, match="unknown asset"):
        DefensibilityModel(
            [Asset.create("srv-1", "App server", "critical")],
            [DataSource.create("edr", GOOD, ["srv-typo"])],
            [],
        )


def test_full_critical_coverage_has_no_auto_failure():
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],
        [TechniqueControl.create("T1110", "detected", must_detect=True, evidence="BT-IDENTITY-001")],
    )
    assert model.automatic_failures() == []
    assert model.telemetry_coverage("critical")["ratio"] == 1.0


def test_partial_critical_coverage_is_an_auto_failure():
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical"), Asset.create("srv-2", "DB", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],
        [],
    )
    failures = model.automatic_failures()
    assert any("below 100%" in f for f in failures)
    assert "srv-2" in failures[0]


def test_weak_source_does_not_rescue_critical_coverage():
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical")],
        [DataSource.create("syslog", WEAK, ["srv-1"])],
        [],
    )
    assert any("below 100%" in f for f in model.automatic_failures())


def test_unhandled_must_detect_technique_is_an_auto_failure():
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],
        [TechniqueControl.create("T1059", "none", must_detect=True, evidence="")],
    )
    assert any("must-detect" in f for f in model.automatic_failures())


def test_prevention_satisfies_a_must_detect_requirement():
    # Blocking the technique is a better outcome than alerting on it; requiring a
    # detection anyway would push teams to alert on things they could have stopped.
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],
        [TechniqueControl.create("T1059", "prevented", must_detect=True,
                                 evidence="execution policy blocks unsigned scripts")],
    )
    assert model.automatic_failures() == []
    assert model.must_detect_status()["prevented"] == ["T1059"]


def test_non_must_detect_gap_is_not_an_auto_failure():
    model = DefensibilityModel(
        [Asset.create("srv-1", "App", "critical")],
        [DataSource.create("edr", GOOD, ["srv-1"])],
        [TechniqueControl.create("T1595", "none", must_detect=False, evidence="")],
    )
    assert model.automatic_failures() == []
    assert model.detection_effectiveness() == 0.0


def test_coverage_claim_requires_evidence():
    with pytest.raises(ConfigurationError, match="requires evidence"):
        TechniqueControl.create("T1110", "detected", must_detect=True, evidence="  ")


def test_standard_assets_do_not_trigger_the_critical_gate():
    model = DefensibilityModel(
        [Asset.create("srv-9", "Lab box", "standard")],
        [DataSource.create("edr", GOOD, ["srv-9"])],
        [],
    )
    assert model.automatic_failures() == []


def test_inventory_summary_names_blind_sources():
    summary = inventory_summary([
        DataSource.create("edr", GOOD, ["a"]),
        DataSource.create("syslog", WEAK, ["a"]),
    ])
    assert summary["providing_visibility"] == 1
    assert summary["blind_sources"][0]["name"] == "syslog"


def test_duplicate_asset_ids_rejected():
    with pytest.raises(ConfigurationError, match="duplicate asset"):
        DefensibilityModel(
            [Asset.create("srv-1", "A", "critical"), Asset.create("srv-1", "B", "critical")],
            [], [],
        )
