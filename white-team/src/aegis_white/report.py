"""After-action reporting.

The timeline is reconstructed from the ledger rather than typed by hand, so the
narrative cannot drift from the evidence. Anything the report asserts about what
happened is derived; only judgement sections (findings, recommendations) are
authored, and the scorecard's Q component measures whether those were supplied.
"""
from __future__ import annotations

from typing import Any

from .control import (
    EVENT_ACTIVITY,
    EVENT_AUTHORIZE,
    EVENT_COMPLETE,
    EVENT_DECISION,
    EVENT_START,
    EVENT_STOP,
    EVENT_STOP_ACK,
    ExerciseControl,
)

_HUMAN = {
    EVENT_AUTHORIZE: "exercise authorized",
    EVENT_START: "exercise started",
    EVENT_ACTIVITY: "activity adjudicated",
    EVENT_STOP: "STOP declared",
    EVENT_STOP_ACK: "stop acknowledged",
    EVENT_DECISION: "decision recorded",
    EVENT_COMPLETE: "exercise completed",
}


def build_timeline(control: ExerciseControl) -> list[dict[str, Any]]:
    timeline: list[dict[str, Any]] = []
    for record in control.ledger:
        payload = record.payload
        event = payload.get("event", "unknown")
        entry: dict[str, Any] = {
            "sequence": record.sequence,
            "event": event,
            "description": _HUMAN.get(event, event),
        }
        if "at" in payload:
            entry["at"] = payload["at"]
        if event == EVENT_ACTIVITY:
            entry["description"] = (
                f"{payload['activity']} on {payload['target']}: "
                + ("ACCEPTED" if payload["accepted"] else "REFUSED")
                + ("" if payload.get("in_scope", True) else " [out of scope]")
                + (" [after stop]" if payload.get("after_stop") else "")
                + (" [observed, not authorized by White]" if payload.get("observed") else "")
            )
        elif event == EVENT_STOP:
            entry["description"] = f"STOP declared ({payload['severity']}): {payload['reason']}"
        elif event == EVENT_DECISION:
            d = payload["decision"]
            entry["at"] = d["decided_at"]
            entry["description"] = f"decision {d['decision_id']}: {d['outcome']}"
        timeline.append(entry)
    return timeline


def build_report(
    control: ExerciseControl,
    *,
    summary: str = "",
    findings: str = "",
    recommendations: str = "",
) -> dict[str, Any]:
    state = control.state()
    timeline = build_timeline(control)
    return {
        "exercise_id": state.exercise_id,
        "summary": summary,
        "timeline": timeline,
        "findings": findings,
        "decisions": [d.to_payload() for d in state.decisions],
        "recommendations": recommendations,
        "control_metrics": {
            "activities_accepted": state.activities_accepted,
            "activities_refused": state.activities_refused,
            "out_of_scope_accepted": state.out_of_scope_accepted,
            "post_stop_activity": state.post_stop_activity,
            "stop_declared": state.stopped_at.isoformat() if state.stopped_at else None,
            "stop_acknowledged": (
                state.stop_acknowledged_at.isoformat() if state.stop_acknowledged_at else None
            ),
            "stop_latency_seconds": control.stop_latency_seconds(),
            "completed": state.completed,
        },
    }
