# Blue-Team Operating Model

## Mission

Know the environment, maintain visibility, detect material behavior, investigate
with evidence, contain proportionately, recover safely, and continuously improve.

## Team topology

| Function | Primary responsibility | Independent check |
|---|---|---|
| Duty lead | Severity, ownership, escalation, executive coordination | Incident commander for major incidents |
| Monitoring analyst | Queue review, evidence preservation, initial scope | Detection engineer samples closed alerts |
| Incident responder | Investigation, containment recommendation, eradication | Recovery lead validates safe restoration |
| Threat hunter | Hypothesis-led searches across identity, endpoint, cloud, network | Detection engineer converts durable findings |
| Detection engineer | Rule quality, telemetry contracts, ATT&CK coverage, testing | Peer review plus adversarial validation |
| Cloud and identity defender | Identity, SaaS, control-plane and token abuse | Incident responder correlates endpoint evidence |
| Forensics lead | Evidence handling, timeline, acquisition quality | Legal/privacy review when required |
| Vulnerability lead | Exposure triage, remediation validation, compensating controls | Asset owner and change management |
| Recovery lead | Backup integrity, rebuild, restoration and monitoring | Incident commander accepts recovery evidence |
| Security platform engineer | Pipeline health, access, retention, integrations | Sensor-health and audit-integrity gates |

Small teams combine roles but must preserve independent approval for destructive
response and independent review for critical detection changes.

## Shift cadence

- **Continuous:** critical queue, sensor blind spots, audit integrity, active incidents.
- **Daily:** stale alerts, identity/control changes, exposed assets, backup failures.
- **Weekly:** threat hunts, rule tuning, false-negative review, case aging, coverage gaps.
- **Monthly:** tabletop exercise, restore sample, privileged-access review, telemetry cost.
- **Quarterly:** full incident exercise, crown-jewel threat model, supplier exercise,
  retention/legal review, and disaster recovery proof.

## Quality gates

No detection is production-ready without representative positive and negative
fixtures, known data dependencies, owner, severity rationale, runbook, ATT&CK
mapping, false-positive assumptions, and rollback. No incident is closed without
scope, cause or declared unknown, containment evidence, recovery validation,
lessons, and detection/prevention follow-up.

## Metrics that resist gaming

- Median time to acknowledge, investigate, contain, and recover, by severity.
- Percentage of critical telemetry within freshness budget.
- Detection validation pass rate and age of last validation.
- False-negative discoveries and time to add durable coverage.
- Reopened incidents and recurrence rate.
- Recovery-point and recovery-time objective test results.
- High-risk actions with complete approval and rollback evidence.

Alert volume and closure count are workload measures, not success measures.
