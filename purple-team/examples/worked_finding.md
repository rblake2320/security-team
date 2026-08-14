# Worked example — FND-2026-0143

Taken from the [pilot exercise](../../00-shared/12_pilot_exercise.md), test case TC-006.
Shown filled in so the shape of a *good* finding is unambiguous.

Title:              Credential added to a workload identity produces no alert
Type:               detection_gap
Severity:           high
Severity inputs:    exploitability=moderate | impact=high | exposure=internal
                    compensating_controls=none verified | rubric_version=1.2
Exercise:           EX-2026-001
ATT&CK:             T1098.001 (Account Manipulation: Additional Cloud Credentials)
Affected assets:    ASSET-0442, ASSET-0443
System owner:       m.chen
Remediation owner:  a.smith

## Six-stage outcome
prevented:      not_blocked
logged:         full        <- the event WAS present, with actor/target/credential-type/source-IP
alerted:        no_alert    <- DETECTION GAP GAP-2026-0003
investigated:   n/a (no alert to triage)
contained:      no
reported:       no

## Evidence
EV-2026-001-021 (directory audit log export, sha256:...), EV-2026-001-022 (screenshot, redacted)

## Description
A credential can be added to an existing workload identity outside the approved provisioning
path. The directory audit log records it in full, but no detection content consumes that event,
so it reaches no queue and no human.

## Reproduction
TC-2026-001-006, verbatim. Lab tenant, synthetic service principal, exercise identity
svc-ex-2026-001-03.

## Business impact
An attacker who reaches any identity able to modify service principals gains durable access that
survives password resets and does not appear in user sign-in review. This is the persistence step
in the pilot's threat scenario.

## ACCEPTANCE CRITERIA
1. A detection fires within 15 minutes of a credential being added to a workload identity outside
   the approved provisioning path.
2. The alert routes to the SOC queue at severity >= medium with actor, target, and source IP.
3. Purple re-executes TC-2026-001-006 verbatim and observes the alert.
4. The detection is deployed to PRODUCTION and its source log is confirmed live (TC-009).

Target date:    2026-10-18 (High = 30 days)
Status:         closed  (see RT-2026-0091 — detected in 412s on retest)
Classification: INTERNAL

---
**Why this is a good finding:** it is high-fidelity and low-volume (a rare, unambiguous event),
the telemetry already existed so the fix is cheap, criterion 4 blocks lab-only closure, and the
business impact is written for the system owner rather than for another security engineer.
