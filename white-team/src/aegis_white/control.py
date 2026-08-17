"""Exercise control: authorization, scope enforcement, and stop authority.

The engine is fail-closed. An activity is refused unless an unexpired authorization
exists AND the activity is explicitly in scope AND no mandatory stop has been
declared. Refusals are recorded, not merely returned: an exercise where White
silently declined things leaves no evidence that control was exercised.

`observed=True` exists because White records reality, not intentions. If a
participant performs an action anyway — after a stop, or outside scope — that fact
must be recordable, and the scorecard treats it as an automatic failure. A control
plane that can only record its own well-behaved decisions cannot detect a breach.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import AuthorizationError, ConfigurationError, StopViolationError
from .ledger import Ledger
from .models import (
    Authorization,
    Decision,
    ExerciseState,
    STOP_SEVERITIES,
    Scope,
    parse_instant,
)

EVENT_AUTHORIZE = "exercise.authorized"
EVENT_START = "exercise.started"
EVENT_ACTIVITY = "activity.requested"
EVENT_STOP = "stop.declared"
EVENT_STOP_ACK = "stop.acknowledged"
EVENT_DECISION = "decision.recorded"
EVENT_COMPLETE = "exercise.completed"


class ExerciseControl:
    def __init__(self, ledger_path: str | Path) -> None:
        self.ledger = Ledger(ledger_path)

    # ---- state ---------------------------------------------------------------

    def state(self) -> ExerciseState:
        """Rebuild the exercise projection by replaying the ledger.

        State is never held authoritatively in memory: the ledger is the record, and
        an after-action reviewer replaying it must reach the same conclusions.
        """
        state: ExerciseState | None = None
        for record in self.ledger:
            payload = record.payload
            event = payload.get("event")
            if event == EVENT_AUTHORIZE:
                state = ExerciseState(exercise_id=payload["exercise_id"])
                state.authorization = Authorization.create(
                    payload["authorization"]["approved_by"],
                    payload["authorization"]["ticket"],
                    payload["authorization"]["expires_at"],
                )
                state.scope = Scope.create(
                    list(payload["scope"]["targets"]), list(payload["scope"]["activities"])
                )
                continue
            if state is None:
                raise ConfigurationError("ledger begins with an event before authorization")
            if event == EVENT_START:
                state.started = True
            elif event == EVENT_ACTIVITY:
                if payload["accepted"]:
                    state.activities_accepted += 1
                    if payload.get("after_stop"):
                        state.post_stop_activity += 1
                    if not payload.get("in_scope", True):
                        state.out_of_scope_accepted += 1
                else:
                    state.activities_refused += 1
            elif event == EVENT_STOP:
                state.stopped_at = parse_instant(payload["at"])
                state.stop_reason = payload["reason"]
                state.stop_severity = payload["severity"]
            elif event == EVENT_STOP_ACK:
                state.stop_acknowledged_at = parse_instant(payload["at"])
            elif event == EVENT_DECISION:
                d = payload["decision"]
                state.decisions.append(
                    Decision.create(
                        d["decision_id"], d["decided_by"], d["question"], d["outcome"],
                        d["rationale"], d["raised_at"], d["decided_at"],
                    )
                )
            elif event == EVENT_COMPLETE:
                state.completed = True
        if state is None:
            raise ConfigurationError("no authorized exercise found in ledger")
        return state

    def _require_state(self) -> ExerciseState:
        return self.state()

    # ---- lifecycle -----------------------------------------------------------

    def authorize(
        self, exercise_id: str, authorization: Authorization, scope: Scope, at: str
    ) -> dict[str, Any]:
        if self.ledger.path.exists() and self.ledger.path.stat().st_size > 0:
            raise ConfigurationError("this ledger already holds an exercise")
        payload = {
            "event": EVENT_AUTHORIZE,
            "exercise_id": exercise_id,
            "authorization": authorization.to_payload(),
            "scope": scope.to_payload(),
            "at": parse_instant(at).isoformat(),
        }
        self.ledger.append(payload)
        return payload

    def start(self, at: str) -> dict[str, Any]:
        state = self._require_state()
        if state.stopped_at:
            raise StopViolationError("cannot start: a stop condition is in force")
        payload = {"event": EVENT_START, "at": parse_instant(at).isoformat()}
        self.ledger.append(payload)
        return payload

    # ---- the control itself --------------------------------------------------

    def request_activity(
        self, target: str, activity: str, at: str, *, observed: bool = False
    ) -> dict[str, Any]:
        """Adjudicate one proposed activity.

        Returns the recorded payload when permitted. Raises when refused — after
        writing the refusal to the ledger, so the refusal is evidence.
        """
        state = self._require_state()
        moment = parse_instant(at)
        after_stop = state.stopped_at is not None and state.stop_severity == "mandatory"
        in_scope = bool(state.scope and state.scope.permits(target, activity))
        authorized = bool(state.authorization and state.authorization.is_valid_at(moment))

        permitted = in_scope and authorized and not after_stop
        accepted = permitted or observed

        payload = {
            "event": EVENT_ACTIVITY,
            "target": target,
            "activity": activity,
            "at": moment.isoformat(),
            "accepted": accepted,
            "in_scope": in_scope,
            "authorized": authorized,
            "after_stop": after_stop,
            "observed": observed,
        }
        self.ledger.append(payload)

        if permitted or observed:
            return payload
        if after_stop:
            raise StopViolationError(
                f"refused: mandatory stop in force ({state.stop_reason})"
            )
        if not authorized:
            raise AuthorizationError("refused: authorization is absent or expired")
        raise AuthorizationError(f"refused: {activity} on {target} is out of scope")

    def declare_stop(self, reason: str, at: str, *, severity: str = "mandatory") -> dict[str, Any]:
        """Declare a stop condition. This authority is unconditional and needs no
        counter-signature — that is the point of an independent White Team."""
        if severity not in STOP_SEVERITIES:
            raise ConfigurationError(f"severity must be one of {STOP_SEVERITIES}")
        self._require_state()
        payload = {
            "event": EVENT_STOP,
            "reason": reason,
            "severity": severity,
            "at": parse_instant(at).isoformat(),
        }
        self.ledger.append(payload)
        return payload

    def acknowledge_stop(self, at: str) -> dict[str, Any]:
        state = self._require_state()
        if state.stopped_at is None:
            raise ConfigurationError("no stop has been declared")
        moment = parse_instant(at)
        if moment < state.stopped_at:
            raise ConfigurationError("stop acknowledged before it was declared")
        payload = {"event": EVENT_STOP_ACK, "at": moment.isoformat()}
        self.ledger.append(payload)
        return payload

    def record_decision(self, decision: Decision) -> dict[str, Any]:
        self._require_state()
        payload = {"event": EVENT_DECISION, "decision": decision.to_payload()}
        self.ledger.append(payload)
        return payload

    def complete(self, at: str) -> dict[str, Any]:
        self._require_state()
        payload = {"event": EVENT_COMPLETE, "at": parse_instant(at).isoformat()}
        self.ledger.append(payload)
        return payload

    # ---- derived metrics -----------------------------------------------------

    def stop_latency_seconds(self) -> float | None:
        state = self.state()
        if state.stopped_at is None or state.stop_acknowledged_at is None:
            return None
        return (state.stop_acknowledged_at - state.stopped_at).total_seconds()
