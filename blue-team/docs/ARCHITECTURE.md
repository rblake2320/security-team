# Architecture

## Security objective

Produce timely, explainable, reviewable defensive findings while continuing to
surface what the team cannot currently see. Availability and integrity of the
defensive pipeline are security properties, not operational afterthoughts.

## Data flow

```text
Sensors -> bounded JSONL -> strict normalization -> evidence store
                                              |-> detection rules
                                              |-> temporal correlation
                                              |-> alerts -> cases -> response plans
                                              |-> sensor health / coverage reports
                                              `-> tamper-evident audit chain
```

## Trust boundaries

1. **Telemetry boundary:** all event fields are untrusted. Unknown top-level
   fields, malformed UTF-8, oversized objects, excessive nesting, duplicate-key
   collisions after Unicode normalization, and unsafe identifiers are rejected.
2. **Detection boundary:** rule files are trusted configuration but still
   validated. Rules cannot execute code or arbitrary regular expressions.
3. **Evidence boundary:** inserts and audit writes share a transaction. Event IDs
   are idempotent only when content hashes agree.
4. **Response boundary:** the platform only produces response recommendations.
   High-risk actions require two approvers and a rollback statement.
5. **Operator boundary:** a local administrator can still replace the database
   or code. Production needs separate storage, identity, key custody, immutable
   backup, and an external signed audit-head anchor.

## Availability controls

- Per-event and per-run limits prevent accidental unbounded ingestion.
- SQLite uses WAL, full synchronous writes, foreign keys, and a busy timeout.
- Correlation evidence is capped in alerts while counts remain explicit.
- Sensor freshness has an independent policy and produces visible blind spots.
- Critical defense-impairment detections cannot be suppressed.

## Production evolution

The local core is designed to migrate behind an authenticated ingestion API and
durable queue. Before that transition, require tenant isolation, mutual TLS,
schema versioning, queue backpressure, dead-letter review, external audit
anchoring, time synchronization monitoring, backup restore proof, and disaster
recovery exercises.
