"""Capability scoring, including the program's two hard rules:
auto-failures are evaluated before aggregation, and undemonstrated components are
excluded rather than assumed.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from aegis_white.control import ExerciseControl
from aegis_white.errors import StopViolationError
from aegis_white.models import Authorization, Decision, Scope
from aegis_white.report import build_report
from aegis_white.scoring import load_scorecard, score_exercise

SCORECARD = Path(__file__).resolve().parents[1] / "config" / "scorecard.json"
EXPIRY = "2026-08-18T00:00:00Z"


@pytest.fixture
def scorecard():
    return load_scorecard(SCORECARD)


def clean_exercise(tmp_path) -> ExerciseControl:
    control = ExerciseControl(tmp_path / "l.jsonl")
    control.authorize(
        "EX-CLEAN",
        Authorization.create("Director", "TICKET-CLEAN", EXPIRY),
        Scope.create(["app.test"], ["passive-scan"]),
        "2026-08-17T10:00:00Z",
    )
    control.start("2026-08-17T10:00:00Z")
    control.request_activity("app.test", "passive-scan", "2026-08-17T10:01:00Z")
    try:
        control.request_activity("prod.test", "exploit", "2026-08-17T10:02:00Z")
    except Exception:
        pass  # refusal is the point
    control.record_decision(
        Decision.create(
            "D-1", "Director", "Continue after error spike?", "continue with monitoring",
            "Error rate returned to baseline within two minutes.",
            "2026-08-17T10:03:00Z", "2026-08-17T10:04:00Z",
        )
    )
    control.declare_stop("scheduled safety inject", "2026-08-17T10:10:00Z")
    control.acknowledge_stop("2026-08-17T10:10:30Z")
    control.complete("2026-08-17T10:15:00Z")
    return control


def full_report(control) -> dict:
    return build_report(
        control,
        summary="Exercise ran to plan.",
        findings="One out-of-scope attempt was refused.",
        recommendations="Retain the current scope allow-list.",
    )


def test_clean_exercise_passes(tmp_path, scorecard):
    control = clean_exercise(tmp_path)
    result = score_exercise(control, scorecard, report=full_report(control))
    assert result.auto_failures == []
    assert result.status == "PASS"
    assert result.weighted_score >= scorecard["pass_threshold"]


def test_post_stop_activity_is_an_automatic_failure(tmp_path, scorecard):
    control = clean_exercise(tmp_path)
    control.request_activity("app.test", "passive-scan", "2026-08-17T10:12:00Z", observed=True)
    result = score_exercise(control, scorecard, report=full_report(control))
    assert result.status == "FAILED"
    assert any("mandatory stop" in f for f in result.auto_failures)


def test_scope_expansion_is_an_automatic_failure(tmp_path, scorecard):
    control = clean_exercise(tmp_path)
    control.request_activity("prod.test", "exploit", "2026-08-17T10:05:00Z", observed=True)
    result = score_exercise(control, scorecard, report=full_report(control))
    assert result.status == "FAILED"
    assert any("scope expansion" in f for f in result.auto_failures)


def test_auto_failure_beats_a_high_weighted_score(tmp_path, scorecard):
    """The program rule is explicit: auto-fail is evaluated BEFORE aggregation and
    the weighted score is retained for diagnostics only."""
    control = clean_exercise(tmp_path)
    control.request_activity("app.test", "passive-scan", "2026-08-17T10:12:00Z", observed=True)
    result = score_exercise(control, scorecard, report=full_report(control))
    assert result.weighted_score > 0.5  # would otherwise look healthy
    assert result.status == "FAILED"


def test_undemonstrated_component_is_excluded_not_assumed(tmp_path, scorecard):
    control = ExerciseControl(tmp_path / "l.jsonl")
    control.authorize(
        "EX-QUIET",
        Authorization.create("Director", "TICKET-Q", EXPIRY),
        Scope.create(["app.test"], ["passive-scan"]),
        "2026-08-17T10:00:00Z",
    )
    control.start("2026-08-17T10:00:00Z")
    result = score_exercise(control, scorecard, report=None)
    by_key = {c.key: c for c in result.components}
    assert by_key["S"].value is None  # no stop was ever declared
    assert by_key["Q"].value is None  # no report supplied
    assert result.renormalized is True
    assert result.notes


def test_unacknowledged_stop_scores_zero_for_safety(tmp_path, scorecard):
    control = ExerciseControl(tmp_path / "l.jsonl")
    control.authorize(
        "EX-NOACK",
        Authorization.create("Director", "TICKET-N", EXPIRY),
        Scope.create(["app.test"], ["passive-scan"]),
        "2026-08-17T10:00:00Z",
    )
    control.start("2026-08-17T10:00:00Z")
    control.declare_stop("halt", "2026-08-17T10:01:00Z")
    result = score_exercise(control, scorecard, report=None)
    assert {c.key: c.value for c in result.components}["S"] == 0.0


def test_slow_stop_acknowledgement_lowers_safety_score(tmp_path, scorecard):
    control = ExerciseControl(tmp_path / "l.jsonl")
    control.authorize(
        "EX-SLOW",
        Authorization.create("Director", "TICKET-S", EXPIRY),
        Scope.create(["app.test"], ["passive-scan"]),
        "2026-08-17T10:00:00Z",
    )
    control.start("2026-08-17T10:00:00Z")
    control.declare_stop("halt", "2026-08-17T10:00:00Z")
    control.acknowledge_stop("2026-08-17T10:03:00Z")  # 180s against a 60s target
    value = {c.key: c.value for c in score_exercise(control, scorecard).components}["S"]
    assert 0.0 < value < 1.0


def test_tampered_ledger_fails_evidence_and_auto_fails(tmp_path, scorecard):
    control = clean_exercise(tmp_path)
    path = tmp_path / "l.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[1])
    record["payload"]["event"] = "rewritten"
    lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    fresh = ExerciseControl(path)
    result = score_exercise(fresh, scorecard, report=None)
    assert {c.key: c.value for c in result.components}["E"] == 0.0
    assert result.status == "FAILED"


def test_incomplete_report_lowers_reporting_quality(tmp_path, scorecard):
    control = clean_exercise(tmp_path)
    report = full_report(control)
    report["recommendations"] = ""
    result = score_exercise(control, scorecard, report=report)
    q = {c.key: c.value for c in result.components}["Q"]
    assert 0.0 < q < 1.0
