"""Findings register: turning security findings into completed engineering work.

The Yellow charter is specific — findings must become "completed engineering work
with verifiable acceptance criteria and evidence". This register enforces that
literally, and it is the mechanism behind the team's two automatic failures:

  * any open critical finding
  * any high-severity finding without an automated regression test OR a documented
    compensating control

A finding therefore cannot be closed by assertion. Closing one requires either a
named regression test (the durable fix — the bug cannot come back unnoticed) or an
explicitly documented compensating control (the honest alternative). "Fixed, trust
me" is refused, because that is precisely the claims/evidence divergence the whole
program exists to prevent.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .errors import ConfigurationError, RemediationError
from .ledger import Ledger

SEVERITIES = ("critical", "high", "medium", "low", "info")
# Severities where closure demands durable evidence rather than a note.
EVIDENCE_REQUIRED = ("critical", "high")
STATES = ("open", "remediated", "risk_accepted")

EVENT_OPEN = "finding.opened"
EVENT_CLOSE = "finding.remediated"
EVENT_ACCEPT = "finding.risk_accepted"


def _instant(value: str, field_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ConfigurationError(f"{field_name} is not a valid ISO-8601 instant") from exc
    if parsed.tzinfo is None:
        raise ConfigurationError(f"{field_name} must include a timezone offset")
    return parsed


@dataclass
class Finding:
    finding_id: str
    title: str
    severity: str
    state: str
    opened_at: datetime
    closed_at: datetime | None = None
    regression_test: str | None = None
    compensating_control: str | None = None
    acceptance_criteria: str | None = None
    accepted_by: str | None = None

    @property
    def age_seconds(self) -> float | None:
        if self.closed_at is None:
            return None
        return (self.closed_at - self.opened_at).total_seconds()

    @property
    def has_durable_evidence(self) -> bool:
        return bool(self.regression_test or self.compensating_control)


class FindingsRegister:
    def __init__(self, ledger_path: str | Path) -> None:
        self.ledger = Ledger(ledger_path)

    # ---- projection ----------------------------------------------------------

    def findings(self) -> dict[str, Finding]:
        result: dict[str, Finding] = {}
        for record in self.ledger:
            p = record.payload
            event = p.get("event")
            if event == EVENT_OPEN:
                result[p["finding_id"]] = Finding(
                    finding_id=p["finding_id"],
                    title=p["title"],
                    severity=p["severity"],
                    state="open",
                    opened_at=_instant(p["at"], "at"),
                    acceptance_criteria=p.get("acceptance_criteria"),
                )
            elif event in (EVENT_CLOSE, EVENT_ACCEPT):
                finding = result.get(p["finding_id"])
                if finding is None:
                    raise ConfigurationError(
                        f"{p['finding_id']} was closed without ever being opened"
                    )
                finding.state = "remediated" if event == EVENT_CLOSE else "risk_accepted"
                finding.closed_at = _instant(p["at"], "at")
                finding.regression_test = p.get("regression_test")
                finding.compensating_control = p.get("compensating_control")
                finding.accepted_by = p.get("accepted_by")
        return result

    # ---- mutation ------------------------------------------------------------

    def open_finding(
        self, finding_id: str, title: str, severity: str, at: str,
        *, acceptance_criteria: str | None = None,
    ) -> dict[str, Any]:
        if severity not in SEVERITIES:
            raise ConfigurationError(f"severity must be one of {SEVERITIES}")
        if not title.strip():
            raise ConfigurationError("title is required")
        if finding_id in self.findings():
            raise ConfigurationError(f"{finding_id} already exists")
        if severity in EVIDENCE_REQUIRED and not (acceptance_criteria or "").strip():
            # Orange's scorecard demands acceptance criteria on critical findings;
            # Yellow is where that requirement is actually enforced.
            raise ConfigurationError(
                f"{severity} findings require acceptance criteria when opened"
            )
        payload = {
            "event": EVENT_OPEN,
            "finding_id": finding_id,
            "title": title.strip(),
            "severity": severity,
            "at": _instant(at, "at").isoformat(),
            "acceptance_criteria": (acceptance_criteria or "").strip() or None,
        }
        self.ledger.append(payload)
        return payload

    def remediate(
        self, finding_id: str, at: str,
        *, regression_test: str | None = None, compensating_control: str | None = None,
    ) -> dict[str, Any]:
        finding = self.findings().get(finding_id)
        if finding is None:
            raise ConfigurationError(f"unknown finding {finding_id}")
        if finding.state != "open":
            raise RemediationError(f"{finding_id} is already {finding.state}")
        test = (regression_test or "").strip() or None
        control = (compensating_control or "").strip() or None
        if finding.severity in EVIDENCE_REQUIRED and not (test or control):
            raise RemediationError(
                f"{finding_id} is {finding.severity}: closing it requires a named automated "
                "regression test or a documented compensating control"
            )
        payload = {
            "event": EVENT_CLOSE,
            "finding_id": finding_id,
            "at": _instant(at, "at").isoformat(),
            "regression_test": test,
            "compensating_control": control,
        }
        self.ledger.append(payload)
        return payload

    def accept_risk(
        self, finding_id: str, at: str, *, accepted_by: str, compensating_control: str
    ) -> dict[str, Any]:
        """Risk acceptance is a legitimate outcome, but never for a critical finding
        and never anonymously — someone must own it by name."""
        finding = self.findings().get(finding_id)
        if finding is None:
            raise ConfigurationError(f"unknown finding {finding_id}")
        if finding.state != "open":
            raise RemediationError(f"{finding_id} is already {finding.state}")
        if finding.severity == "critical":
            raise RemediationError(
                "a critical finding cannot be risk-accepted; it must be remediated"
            )
        if not accepted_by.strip() or not compensating_control.strip():
            raise RemediationError("risk acceptance requires a named owner and a control")
        payload = {
            "event": EVENT_ACCEPT,
            "finding_id": finding_id,
            "at": _instant(at, "at").isoformat(),
            "accepted_by": accepted_by.strip(),
            "compensating_control": compensating_control.strip(),
        }
        self.ledger.append(payload)
        return payload

    # ---- assessment ----------------------------------------------------------

    def automatic_failures(self) -> list[str]:
        failures: list[str] = []
        findings = self.findings()
        open_critical = [f.finding_id for f in findings.values()
                         if f.severity == "critical" and f.state == "open"]
        if open_critical:
            failures.append(f"open critical finding(s): {', '.join(sorted(open_critical))}")
        weak_high = [
            f.finding_id for f in findings.values()
            if f.severity == "high" and f.state != "open" and not f.has_durable_evidence
        ]
        if weak_high:
            failures.append(
                "high-severity finding(s) closed without a regression test or documented "
                f"compensating control: {', '.join(sorted(weak_high))}"
            )
        return failures
