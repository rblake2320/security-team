"""NIST SSDF (SP 800-218 v1.1) practice catalogue and attestation.

Source: NIST SP 800-218, Secure Software Development Framework v1.1 — 19 practices
across four groups. PW.3 is deliberately absent: it was retired during the v1.1
revision and the identifier was NOT renumbered, so that references to PW.4-PW.9
stayed stable. A catalogue that "helpfully" inserts PW.3 is wrong and will not
reconcile against an auditor's copy.

Attestation is three-state on purpose. `not_applicable` must be justified, because
"N/A" with no reason is the most common way a control matrix is quietly defeated.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .errors import ConfigurationError

SSDF_VERSION = "SP 800-218 v1.1"

PRACTICES: dict[str, str] = {
    # Prepare the Organization
    "PO.1": "Define Security Requirements for Software Development",
    "PO.2": "Implement Roles and Responsibilities",
    "PO.3": "Implement Supporting Toolchains",
    "PO.4": "Define and Use Criteria for Software Security Checks",
    "PO.5": "Implement and Maintain Secure Environments for Software Development",
    # Protect the Software
    "PS.1": "Protect All Forms of Code from Unauthorized Access and Tampering",
    "PS.2": "Provide a Mechanism for Verifying Software Release Integrity",
    "PS.3": "Archive and Protect Each Software Release",
    # Produce Well-Secured Software  (PW.3 retired in v1.1 — not a gap)
    "PW.1": "Design Software to Meet Security Requirements and Mitigate Security Risks",
    "PW.2": "Review the Software Design to Verify Compliance with Security Requirements",
    "PW.4": "Reuse Existing, Well-Secured Software When Feasible",
    "PW.5": "Create Source Code by Adhering to Secure Coding Practices",
    "PW.6": "Configure the Compilation, Interpreter, and Build Processes",
    "PW.7": "Review and/or Analyze Human-Readable Code",
    "PW.8": "Test Executable Code to Identify Vulnerabilities and Verify Compliance",
    "PW.9": "Configure Software to Have Secure Settings by Default",
    # Respond to Vulnerabilities
    "RV.1": "Identify and Confirm Vulnerabilities on an Ongoing Basis",
    "RV.2": "Assess, Prioritize, and Remediate Vulnerabilities",
    "RV.3": "Analyze Vulnerabilities to Identify Their Root Causes",
}

GROUPS = {"PO": "Prepare the Organization", "PS": "Protect the Software",
          "PW": "Produce Well-Secured Software", "RV": "Respond to Vulnerabilities"}

STATES = ("implemented", "not_implemented", "not_applicable")


@dataclass(frozen=True)
class Attestation:
    practice: str
    state: str
    evidence: str

    @staticmethod
    def create(practice: str, state: str, evidence: str) -> "Attestation":
        if practice not in PRACTICES:
            raise ConfigurationError(
                f"unknown SSDF practice {practice!r} (v1.1 has no such identifier)"
            )
        if state not in STATES:
            raise ConfigurationError(f"state must be one of {STATES}")
        if not isinstance(evidence, str) or not evidence.strip():
            # Applies to every state, including not_applicable: an unexplained
            # exemption is indistinguishable from an unimplemented control.
            raise ConfigurationError(
                f"{practice}: evidence is required, including for not_applicable"
            )
        return Attestation(practice=practice, state=state, evidence=evidence.strip())

    def to_payload(self) -> dict[str, Any]:
        return {"practice": self.practice, "state": self.state, "evidence": self.evidence}


def coverage(attestations: list[Attestation]) -> dict[str, Any]:
    """Fraction of *applicable* practices that are implemented.

    Practices marked not_applicable leave the denominator, which is why they require
    justification — otherwise coverage could be driven to 1.0 by exempting everything.
    """
    by_practice = {a.practice: a for a in attestations}
    applicable = [p for p in PRACTICES if by_practice.get(p) and by_practice[p].state != "not_applicable"]
    implemented = [p for p in applicable if by_practice[p].state == "implemented"]
    unattested = sorted(set(PRACTICES) - set(by_practice))
    return {
        "ssdf_version": SSDF_VERSION,
        "total_practices": len(PRACTICES),
        "attested": len(by_practice),
        "unattested": unattested,
        "applicable": len(applicable),
        "implemented": len(implemented),
        "not_applicable": sorted(p for p, a in by_practice.items() if a.state == "not_applicable"),
        # Unattested practices count against coverage: silence is not compliance.
        "coverage": (len(implemented) / len(PRACTICES)) if PRACTICES else 0.0,
        "applicable_coverage": (len(implemented) / len(applicable)) if applicable else 0.0,
    }
