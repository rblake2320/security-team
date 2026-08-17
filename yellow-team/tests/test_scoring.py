from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis_yellow.register import FindingsRegister
from aegis_yellow.scoring import load_scorecard, score_delivery
from aegis_yellow.slsa import BuildEvidence
from aegis_yellow.ssdf import PRACTICES, Attestation

SCORECARD = Path(__file__).resolve().parents[1] / "config" / "scorecard.json"
T0 = "2026-08-17T10:00:00Z"
T1 = "2026-08-18T10:00:00Z"


@pytest.fixture
def scorecard():
    return load_scorecard(SCORECARD)


def all_practices_implemented() -> list[Attestation]:
    return [Attestation.create(p, "implemented", f"evidence for {p}") for p in PRACTICES]


def full_slsa3() -> BuildEvidence:
    return BuildEvidence.create({
        k: {"met": True, "note": "verified in CI"}
        for k in (
            "consistent_build_process", "provenance_exists", "provenance_distributed",
            "hosted_build_platform", "provenance_signed", "provenance_verified",
            "isolated_builds", "signing_key_unreachable",
        )
    })


def healthy_register(tmp_path) -> FindingsRegister:
    r = FindingsRegister(tmp_path / "f.jsonl")
    r.open_finding("F-1", "XSS in profile", "high", T0, acceptance_criteria="escape output")
    r.remediate("F-1", T1, regression_test="tests/test_xss.py::test_escaped")
    return r


def test_strong_delivery_passes(tmp_path, scorecard):
    result = score_delivery(
        healthy_register(tmp_path), scorecard,
        attestations=all_practices_implemented(),
        build_evidence=full_slsa3(),
        test_metrics={"passed": 100, "total": 100, "coverage": 0.95},
        docs_present=["readme", "architecture", "runbook", "threat_model"],
    )
    assert result.auto_failures == []
    assert result.status == "PASS"


def test_open_critical_finding_fails_regardless_of_score(tmp_path, scorecard):
    r = healthy_register(tmp_path)
    r.open_finding("F-2", "RCE", "critical", T0, acceptance_criteria="patch")
    result = score_delivery(
        r, scorecard,
        attestations=all_practices_implemented(),
        build_evidence=full_slsa3(),
        test_metrics={"passed": 100, "total": 100, "coverage": 0.95},
        docs_present=["readme", "architecture", "runbook", "threat_model"],
    )
    assert result.weighted_score > 0.8  # would otherwise pass comfortably
    assert result.status == "FAILED"
    assert any("open critical" in f for f in result.auto_failures)


def test_undemonstrated_components_are_excluded(tmp_path, scorecard):
    result = score_delivery(healthy_register(tmp_path), scorecard,
                            test_metrics={"passed": 10, "total": 10})
    by_key = {c.key: c for c in result.components}
    assert by_key["B"].value is None and by_key["P"].value is None
    assert by_key["M"].value is None
    assert result.renormalized is True


def test_slsa_level_drives_pipeline_component(tmp_path, scorecard):
    l1 = BuildEvidence.create({
        k: {"met": True, "note": "n"}
        for k in ("consistent_build_process", "provenance_exists", "provenance_distributed")
    })
    result = score_delivery(healthy_register(tmp_path), scorecard, build_evidence=l1)
    assert {c.key: c.value for c in result.components}["P"] == pytest.approx(1 / 3)


def test_coverage_caps_the_testing_component(tmp_path, scorecard):
    # A green suite that exercises 20% of the code is not 100% testing evidence.
    result = score_delivery(healthy_register(tmp_path), scorecard,
                            test_metrics={"passed": 50, "total": 50, "coverage": 0.2})
    assert {c.key: c.value for c in result.components}["T"] == pytest.approx(0.2)


def test_tampered_register_is_an_automatic_failure(tmp_path, scorecard):
    r = healthy_register(tmp_path)
    path = tmp_path / "f.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    record["payload"]["severity"] = "low"  # downgrade the finding after the fact
    lines[0] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = score_delivery(FindingsRegister(path), scorecard,
                            test_metrics={"passed": 1, "total": 1})
    assert result.status == "FAILED"
    assert any("integrity" in f for f in result.auto_failures)


def test_missing_documentation_lowers_maintainability(tmp_path, scorecard):
    result = score_delivery(healthy_register(tmp_path), scorecard,
                            docs_present=["readme", "runbook"])
    assert {c.key: c.value for c in result.components}["M"] == pytest.approx(0.5)


def test_wrong_team_scorecard_is_rejected(tmp_path):
    from aegis_yellow.errors import ConfigurationError
    other = Path(__file__).resolve().parents[2] / "white-team" / "config" / "scorecard.json"
    with pytest.raises(ConfigurationError, match="not the Yellow"):
        load_scorecard(other)
