"""Exercise-control behaviour: authorization, scope, and stop authority.

These map directly onto the White Team scorecard's automatic-failure conditions:
"continuing after a mandatory stop condition" and "allowing unauthorized scope
expansion". Both must be impossible through the engine and detectable when they
happen anyway.
"""
from __future__ import annotations

import pytest

from aegis_white.control import ExerciseControl
from aegis_white.errors import AuthorizationError, ConfigurationError, StopViolationError
from aegis_white.models import Authorization, Decision, Scope

T0 = "2026-08-17T10:00:00Z"
T1 = "2026-08-17T10:05:00Z"
T2 = "2026-08-17T10:10:00Z"
EXPIRY = "2026-08-18T00:00:00Z"


def make_control(tmp_path) -> ExerciseControl:
    control = ExerciseControl(tmp_path / "ledger.jsonl")
    control.authorize(
        "EX-2026-001",
        Authorization.create("Exercise Director", "TICKET-001", EXPIRY),
        Scope.create(["app.example.test"], ["passive-scan"]),
        T0,
    )
    control.start(T0)
    return control


def test_in_scope_activity_is_accepted(tmp_path):
    control = make_control(tmp_path)
    result = control.request_activity("app.example.test", "passive-scan", T1)
    assert result["accepted"] is True
    assert control.state().activities_accepted == 1


def test_out_of_scope_target_is_refused(tmp_path):
    control = make_control(tmp_path)
    with pytest.raises(AuthorizationError):
        control.request_activity("other.example.test", "passive-scan", T1)
    state = control.state()
    assert state.activities_accepted == 0
    # The refusal itself must be evidence, not just a return value.
    assert state.activities_refused == 1


def test_out_of_scope_activity_is_refused(tmp_path):
    control = make_control(tmp_path)
    with pytest.raises(AuthorizationError):
        control.request_activity("app.example.test", "exploit", T1)
    assert control.state().activities_refused == 1


def test_expired_authorization_refuses_everything(tmp_path):
    control = ExerciseControl(tmp_path / "ledger.jsonl")
    control.authorize(
        "EX-2026-002",
        Authorization.create("Exercise Director", "TICKET-002", "2026-08-17T09:00:00Z"),
        Scope.create(["app.example.test"], ["passive-scan"]),
        "2026-08-17T08:00:00Z",
    )
    control.start("2026-08-17T08:00:00Z")
    with pytest.raises(AuthorizationError):
        control.request_activity("app.example.test", "passive-scan", T1)


def test_mandatory_stop_blocks_all_further_activity(tmp_path):
    control = make_control(tmp_path)
    control.declare_stop("participant reported production impact", T1)
    with pytest.raises(StopViolationError):
        control.request_activity("app.example.test", "passive-scan", T2)
    assert control.state().activities_refused == 1


def test_advisory_stop_does_not_block(tmp_path):
    # An advisory stop is a warning, not the unconditional control. Conflating the
    # two would make directors reluctant to raise advisories.
    control = make_control(tmp_path)
    control.declare_stop("elevated error rate, monitor closely", T1, severity="advisory")
    assert control.request_activity("app.example.test", "passive-scan", T2)["accepted"] is True


def test_observed_breach_is_recorded_as_auto_failure_evidence(tmp_path):
    control = make_control(tmp_path)
    control.declare_stop("stop now", T1)
    # A participant kept going. White records reality.
    control.request_activity("app.example.test", "passive-scan", T2, observed=True)
    state = control.state()
    assert state.post_stop_activity == 1
    assert state.activities_accepted == 1


def test_observed_out_of_scope_is_recorded(tmp_path):
    control = make_control(tmp_path)
    control.request_activity("prod.example.test", "exploit", T1, observed=True)
    assert control.state().out_of_scope_accepted == 1


def test_cannot_start_after_stop(tmp_path):
    control = make_control(tmp_path)
    control.declare_stop("halt", T1)
    with pytest.raises(StopViolationError):
        control.start(T2)


def test_stop_latency_is_measured(tmp_path):
    control = make_control(tmp_path)
    control.declare_stop("halt", "2026-08-17T10:00:00Z")
    control.acknowledge_stop("2026-08-17T10:00:45Z")
    assert control.stop_latency_seconds() == 45.0


def test_stop_cannot_be_acknowledged_before_declared(tmp_path):
    control = make_control(tmp_path)
    control.declare_stop("halt", T2)
    with pytest.raises(ConfigurationError):
        control.acknowledge_stop(T1)


def test_scope_rejects_wildcards(tmp_path):
    # A wildcard in an allow-list is an unbounded authorization.
    with pytest.raises(ConfigurationError):
        Scope.create(["*.example.test"], ["passive-scan"])


def test_decision_requires_rationale(tmp_path):
    with pytest.raises(ConfigurationError):
        Decision.create("D-1", "Director", "May we continue?", "yes", "   ", T0, T1)


def test_decision_rejects_negative_latency(tmp_path):
    with pytest.raises(ConfigurationError):
        Decision.create("D-1", "Director", "May we continue?", "yes", "because", T2, T1)


def test_second_exercise_cannot_reuse_a_ledger(tmp_path):
    control = make_control(tmp_path)
    with pytest.raises(ConfigurationError):
        control.authorize(
            "EX-2026-003",
            Authorization.create("Someone Else", "TICKET-003", EXPIRY),
            Scope.create(["a.test"], ["b"]),
            T1,
        )


def test_state_is_rebuilt_from_ledger_not_memory(tmp_path):
    control = make_control(tmp_path)
    control.request_activity("app.example.test", "passive-scan", T1)
    control.declare_stop("halt", T2)
    # A completely fresh object must reach the same conclusions from the file alone.
    reloaded = ExerciseControl(tmp_path / "ledger.jsonl")
    state = reloaded.state()
    assert state.exercise_id == "EX-2026-001"
    assert state.activities_accepted == 1
    assert state.stop_reason == "halt"
