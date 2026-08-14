# Detection Engineering Standard

## Rule lifecycle

`idea -> telemetry proof -> rule -> fixtures -> peer review -> adversarial test -> staged deployment -> monitored -> retired`

Each rule must name its behavior, owner, severity, telemetry, rationale, ATT&CK
mapping, response path, tuning assumptions, suppression policy, and validation
date. A critical rule is never suppressible.

## Validation matrix

- Representative true positive
- Legitimate administrative look-alike
- Case changes and normalized Unicode
- Missing and null fields
- Boundary values immediately below and at a threshold
- Split bursts across ordering and ingestion boundaries
- Duplicate exact event and conflicting replay
- Sensor delay, out-of-order event time, and clock skew
- High-volume noise and evidence caps
- Rule/configuration corruption

## Tuning rules

Tune known benign activity with narrow, named, expiring exceptions. Never tune by
excluding an entire administrator group, security product, host class, or source.
Every exception has an owner, reason, expiration, and test proving malicious
variants still alert.

## Coverage

Coverage is the intersection of telemetry, analytic logic, validation evidence,
triage capability, and response readiness. An ATT&CK tag alone proves none of
those. The CLI therefore reports mapping gaps and sensor health separately.

## Hunt conversion

A hunt finding becomes durable only after telemetry requirements, a repeatable
query or rule, positive/negative fixtures, a runbook, ownership, and monitoring
are committed. One-off query output is evidence, not a control.
