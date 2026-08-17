"""SSDF v1.1 catalogue and SLSA v1.0 build-level determination.

These encode published standards, so the tests assert conformance to the standard
rather than to our convenience — including the awkward parts (PW.3's absence, and
SLSA levels being strictly cumulative).
"""
from __future__ import annotations

import pytest

from aegis_yellow.errors import ConfigurationError
from aegis_yellow.slsa import BuildEvidence, determine_level, unmet_for_level
from aegis_yellow.ssdf import PRACTICES, Attestation, coverage


# ---- SSDF -----------------------------------------------------------------

def test_catalogue_has_nineteen_practices():
    assert len(PRACTICES) == 19


def test_pw3_is_absent_because_it_was_retired_in_v11():
    # Inserting PW.3 to "complete" the sequence would break reconciliation with an
    # auditor's copy of SP 800-218 v1.1.
    assert "PW.3" not in PRACTICES
    assert "PW.2" in PRACTICES and "PW.4" in PRACTICES


def test_all_four_groups_present():
    assert {p.split(".")[0] for p in PRACTICES} == {"PO", "PS", "PW", "RV"}


def test_unknown_practice_is_rejected():
    with pytest.raises(ConfigurationError, match="unknown SSDF practice"):
        Attestation.create("PW.3", "implemented", "we did it")


def test_not_applicable_still_requires_justification():
    with pytest.raises(ConfigurationError, match="evidence is required"):
        Attestation.create("PO.5", "not_applicable", "   ")


def test_unattested_practices_count_against_coverage():
    a = [Attestation.create("PO.1", "implemented", "requirements doc")]
    result = coverage(a)
    assert result["implemented"] == 1
    assert result["coverage"] == pytest.approx(1 / 19)
    assert len(result["unattested"]) == 18


def test_not_applicable_leaves_the_applicable_denominator():
    a = [
        Attestation.create("PO.1", "implemented", "requirements doc"),
        Attestation.create("PO.2", "not_applicable", "no third-party developers"),
    ]
    result = coverage(a)
    assert result["applicable"] == 1
    assert result["applicable_coverage"] == 1.0
    # ...but overall coverage still reflects the 17 practices nobody attested.
    assert result["coverage"] < 0.2


# ---- SLSA -----------------------------------------------------------------

def _evidence(**kwargs) -> BuildEvidence:
    return BuildEvidence.create({k: {"met": True, "note": "n"} for k in kwargs if kwargs[k]})


def test_no_evidence_is_level_zero():
    assert determine_level(BuildEvidence.create({}))["level"] == 0


def test_level_one_requires_provenance_that_exists_and_is_distributed():
    partial = _evidence(consistent_build_process=True, provenance_exists=True)
    assert determine_level(partial)["level"] == 0
    full = _evidence(consistent_build_process=True, provenance_exists=True,
                     provenance_distributed=True)
    assert determine_level(full)["level"] == 1


def test_level_two_requires_hosted_platform_and_signed_provenance():
    l2 = _evidence(consistent_build_process=True, provenance_exists=True,
                   provenance_distributed=True, hosted_build_platform=True,
                   provenance_signed=True, provenance_verified=True)
    assert determine_level(l2)["level"] == 2


def test_levels_are_cumulative_not_a_pick_list():
    # L3 controls without the L1 basics is not L3 — it is L0.
    skipping = _evidence(isolated_builds=True, signing_key_unreachable=True)
    assert determine_level(skipping)["level"] == 0


def test_level_three_requires_isolation_and_key_protection():
    l3 = _evidence(consistent_build_process=True, provenance_exists=True,
                   provenance_distributed=True, hosted_build_platform=True,
                   provenance_signed=True, provenance_verified=True,
                   isolated_builds=True, signing_key_unreachable=True)
    result = determine_level(l3)
    assert result["level"] == 3
    assert result["blocking_next_level"] == []


def test_blocking_requirements_are_reported():
    l1 = _evidence(consistent_build_process=True, provenance_exists=True,
                   provenance_distributed=True)
    blocking = determine_level(l1)["blocking_next_level"]
    assert "hosted_build_platform" in blocking and "provenance_signed" in blocking


def test_satisfied_requirement_needs_a_note():
    with pytest.raises(ConfigurationError, match="needs a note"):
        BuildEvidence.create({"provenance_exists": {"met": True}})


def test_unknown_requirement_key_is_rejected():
    with pytest.raises(ConfigurationError, match="unknown SLSA requirement"):
        BuildEvidence.create({"provenance_is_vibes": True})


def test_unmet_for_level_is_cumulative():
    assert set(unmet_for_level(BuildEvidence.create({}), 1)) == {
        "consistent_build_process", "provenance_exists", "provenance_distributed"
    }
