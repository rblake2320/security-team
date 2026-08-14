# Operations

## Before an exercise

1. Evaluate the readiness and claim registries.
2. Snapshot their hashes and the frozen scorecard hash into the plan.
3. Validate every test case has expected telemetry, expected detection, stop conditions, blast radius, and rollback evidence.
4. For production, use observation-only cases. Run state-changing emulation in lab or pre-production.
5. Freeze the plan, then obtain an externally signed White authorization command.
6. Confirm kill/deconfliction contacts through an independent channel.

## During execution

- Use the signed transition boundary; never edit SQLite directly.
- Stop on scope ambiguity, telemetry loss, unexpected production impact, identity mismatch, authorization expiry, or evidence-integrity failure.
- Store evidence by content hash and keep sensitive bytes in the approved evidence repository, not in command arguments or logs.
- Record all six outcomes for every case even when the outcome is `not_applicable`.

## Close and retest

- Exercise Assurance verifies completeness and provenance before changing state.
- Re-execute the identical frozen procedure. If the original is no longer possible, create a new version and do not call it a verbatim retest.
- White closes only after the retest record and unresolved critical-gap check.
- Export the audit anchor to a separately administered append-only service.
- Convert recurring failures into regression tests and versioned claim updates.

## Key rotation

Add the new public key as active, issue test commands with both old and new signers during a bounded overlap, then mark the old key revoked. Never delete historical public keys needed to verify prior commands. Authorization, evidence, and assessment keys must not be the same key.

## Upgrade policy

Every schema or algorithm change requires: threat-model update, claim-version increment, backward fixture, forward rejection test, migration dry run, rollback rehearsal, and independent review. Do not silently reinterpret stored bytes.

