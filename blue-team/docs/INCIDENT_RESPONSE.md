# Incident Response

## Severity

| Severity | Definition | Initial objective |
|---|---|---|
| Critical | Active material impact, privileged compromise, defense impairment, ransomware, or confirmed exfiltration | Immediate command, preservation, and safe containment |
| High | Credible compromise or high-risk behavior with meaningful scope | Triage and scope within the on-call window |
| Medium | Suspicious behavior requiring validation | Investigate within the business response target |
| Low | Weak signal, hygiene issue, or enrichment lead | Queue, enrich, and trend |

Severity reflects plausible business impact and confidence. It is revised as
evidence changes and never reduced solely to improve service-level metrics.

## Lifecycle

1. **Declare and assign:** create a case, severity, incident commander, scribe,
   evidence owner, and communication channel.
2. **Preserve:** record timestamps, event IDs, volatile dependencies, affected
   identities/assets, and acquisition method before destructive action.
3. **Validate:** establish what is confirmed, believed, estimated, and unknown.
4. **Scope:** search laterally across identities, hosts, cloud resources, network,
   persistence, data access, and recovery systems.
5. **Contain:** choose the least-destructive action that stops ongoing harm;
   document approvals, expected impact, success signal, and rollback.
6. **Eradicate:** remove persistence, close exposure, rotate affected secrets,
   validate control restoration, and hunt for alternate access.
7. **Recover:** restore from trusted state, monitor closely, validate service and
   data integrity, and obtain business-owner acceptance.
8. **Learn:** document causes and unknowns, add tests/detections/controls, assign
   owners and deadlines, and verify closure.

## Evidence minimum

Every material decision records who, what, when, evidence references, confidence,
approval, expected result, observed result, and rollback state. Raw secrets and
unnecessary personal data do not belong in tickets or chat.

## Communications

Use a single incident commander and a separate scribe. Provide timed factual
updates with impact, scope, actions, blockers, and next update. Legal, privacy,
insurance, customers, law enforcement, and regulators are engaged according to
the organization's approved obligations—not improvised during the incident.
