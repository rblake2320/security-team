# Adversarial review

This review asked how a capable insider, compromised integration, or rushed operator could make the program report success it did not earn.

## Closed in the executable core

- Plan mutation and conflicting replay.
- Lifecycle gate skipping and stale concurrent transitions.
- Purple self-authorization and plan-owner approval conflicts.
- Role-key mismatch, command tampering, long-lived approval, and nonce replay.
- Production state-changing test cases.
- High-safety cases without verified rollback.
- Evidence from an unplanned case or borrowed from another case.
- Evidence verification before all six stages are recorded.
- Operator self-review.
- Score issuance without component evidence.
- Boolean/string type confusion and Unicode key collision.
- Catastrophic automatic failures hidden by aggregation.
- Transition mutation, interior deletion, and tail deletion inside the live store.

## Intentionally unresolved external boundaries

- `[HOLD]` Independent Exercise Assurance has not been instantiated.
- `[HOLD]` Production key custody and denial of key access to Red/Purple are not verified.
- `[HOLD]` Whole-database rollback is not detectable until anchors reach an independent append-only witness.
- `[HOLD]` Windows path-containment proof remains pending where the source-link test skips without symlink privilege.
- `[HOLD]` The canonical Red implementation decision remains open.
- `[UNKNOWN]` Detection recall, false-positive rate, MTTD, MTTC, and recovery performance until representative live exercises run.

These are deployment prerequisites, not documentation defects. The code preserves the existing `NOT_ASSESSMENT_READY` state rather than manufacturing a green result.

