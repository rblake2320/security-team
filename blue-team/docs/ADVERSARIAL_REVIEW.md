# Adversarial Review

## Question

If I wanted to defeat this blue team without using a noisy exploit, where would
I attack its assumptions, attention, evidence, and authority?

## Findings and defenses

| Attack on the defender | Initial weakness | Hardened result |
|---|---|---|
| Forge a future heartbeat to hide a dead sensor | Freshness used event time | Freshness now uses trusted ingestion time; event time is retained separately |
| Flood unrelated events to make correlation scan-heavy or crowd out a group | Window rescans could grow with event volume | Durable rule-fingerprint/group correlation counters avoid broad rescans |
| Delete the newest audit records | Hash links alone cannot see clean tail deletion | Remembered local head and count detect tail deletion; external anchor still required for rollback resistance |
| Alter a rule quietly | Rules were validated but not pinned | SHA-256 manifest fails closed on altered, added, or removed rule files |
| Suppress the alert that shows defenses were disabled | Generic suppression policy | Critical rules must set suppression off and are rejected otherwise |
| Replay a trusted event ID with different content | Duplicate semantics were undefined | Event ID is bound to canonical content hash; conflicting replay is rejected |
| Change case or Unicode representation to evade a text rule | Field normalization was implicit | NFKC normalization and case-folded operators; normalized-key collision rejection |
| Use catastrophic pattern matching to exhaust the engine | Arbitrary detection syntax could be dangerous | No code or regular-expression operator; bounded comparisons only |
| Trick an analyst into isolating or restoring the wrong asset | Response plan could be mistaken for authorization | Plans never execute; high-risk steps require two approvers and rollback |
| Forge telemetry at the collector boundary | Unsigned JSONL has no origin proof | Optional source-specific HMAC envelopes fail closed; production requires mTLS/asymmetric identity |
| Hide in legitimate tools and admin accounts | Static indicators are insufficient | Cross-domain rules, change validation, behavioral hunts, JIT privilege, and session evidence |
| Destroy the entire local database or roll it back | Local admin controls code and storage | Explicit production blocker: immutable backup plus externally witnessed signed head |

## Residual attack paths

1. Compromise a trusted collector before it signs false data.
2. Compromise the same account that controls code, manifest, database, and keys.
3. Use low-and-slow behavior that remains individually legitimate.
4. Exploit telemetry fields the deployed adapters fail to populate accurately.
5. Exhaust human attention with high-quality benign look-alikes.
6. Attack suppliers, recovery credentials, or identity providers outside local visibility.
7. Use a new technique outside the current priority target.

These risks are addressed through independent telemetry, least privilege,
separate custody, continuous hunts, representative validation, threat-informed
updates, immutable recovery, and external evidence anchoring. They cannot be
truthfully eliminated by adding more local rules.
