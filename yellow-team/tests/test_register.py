"""Findings register: the charter requirement that findings become completed work.

The two automatic failures on Yellow's scorecard are both enforced here, so these
tests are the difference between a tracker and a control.
"""
from __future__ import annotations

import pytest

from aegis_yellow.errors import ConfigurationError, RemediationError
from aegis_yellow.register import FindingsRegister

T0 = "2026-08-17T10:00:00Z"
T1 = "2026-08-18T10:00:00Z"


def reg(tmp_path) -> FindingsRegister:
    return FindingsRegister(tmp_path / "findings.jsonl")


def test_open_and_list(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-1", "SQL injection in search", "critical", T0,
                   acceptance_criteria="parameterized query + regression test")
    assert r.findings()["F-1"].state == "open"


def test_critical_finding_requires_acceptance_criteria(tmp_path):
    r = reg(tmp_path)
    with pytest.raises(ConfigurationError, match="acceptance criteria"):
        r.open_finding("F-2", "RCE in upload", "critical", T0)


def test_high_finding_cannot_be_closed_without_evidence(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-3", "Auth bypass", "high", T0, acceptance_criteria="deny by default")
    with pytest.raises(RemediationError, match="regression test"):
        r.remediate("F-3", T1)


def test_high_finding_closes_with_a_regression_test(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-4", "Auth bypass", "high", T0, acceptance_criteria="deny by default")
    r.remediate("F-4", T1, regression_test="tests/test_auth.py::test_deny_by_default")
    finding = r.findings()["F-4"]
    assert finding.state == "remediated"
    assert finding.has_durable_evidence


def test_high_finding_closes_with_a_documented_compensating_control(tmp_path):
    # The honest alternative to a fix. Allowed, but it must be written down.
    r = reg(tmp_path)
    r.open_finding("F-5", "Legacy TLS", "high", T0, acceptance_criteria="disable TLS1.0")
    r.remediate("F-5", T1, compensating_control="WAF rule blocks TLS1.0 at the edge")
    assert r.findings()["F-5"].has_durable_evidence


def test_low_severity_may_close_without_evidence(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-6", "Verbose banner", "low", T0)
    r.remediate("F-6", T1)
    assert r.findings()["F-6"].state == "remediated"


def test_open_critical_is_an_automatic_failure(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-7", "RCE", "critical", T0, acceptance_criteria="patch + test")
    assert any("open critical" in f for f in r.automatic_failures())


def test_closed_critical_is_not_an_automatic_failure(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-8", "RCE", "critical", T0, acceptance_criteria="patch + test")
    r.remediate("F-8", T1, regression_test="tests/test_rce.py::test_patched")
    assert r.automatic_failures() == []


def test_critical_cannot_be_risk_accepted(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-9", "RCE", "critical", T0, acceptance_criteria="patch")
    with pytest.raises(RemediationError, match="cannot be risk-accepted"):
        r.accept_risk("F-9", T1, accepted_by="CTO", compensating_control="none")


def test_risk_acceptance_requires_named_owner(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-10", "Weak cipher", "medium", T0)
    with pytest.raises(RemediationError):
        r.accept_risk("F-10", T1, accepted_by="  ", compensating_control="edge blocks it")


def test_finding_cannot_be_closed_twice(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-11", "Issue", "low", T0)
    r.remediate("F-11", T1)
    with pytest.raises(RemediationError, match="already"):
        r.remediate("F-11", T1)


def test_duplicate_finding_id_is_rejected(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-12", "Issue", "low", T0)
    with pytest.raises(ConfigurationError, match="already exists"):
        r.open_finding("F-12", "Different issue", "low", T0)


def test_state_is_rebuilt_from_the_ledger(tmp_path):
    r = reg(tmp_path)
    r.open_finding("F-13", "Issue", "high", T0, acceptance_criteria="fix it")
    r.remediate("F-13", T1, regression_test="tests/test_x.py::test_y")
    fresh = FindingsRegister(tmp_path / "findings.jsonl")
    assert fresh.findings()["F-13"].regression_test == "tests/test_x.py::test_y"


def test_naive_timestamp_is_rejected(tmp_path):
    r = reg(tmp_path)
    with pytest.raises(ConfigurationError, match="timezone"):
        r.open_finding("F-14", "Issue", "low", "2026-08-17T10:00:00")
