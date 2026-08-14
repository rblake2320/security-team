# Architecture

## Boundary

Aegis Purple is a control plane, not an offensive executor. Red performs separately authorized emulation; Blue produces defensive observations; Green owns detection content; White controls safety and authorization; Exercise Assurance independently evaluates evidence. Purple binds those facts into a reproducible lifecycle without inheriting their authorities.

```text
external role signer -> signed transition envelope -> verifier -> state machine
                                                        |
frozen plan --------------------------------------------+
                                                        |
Red/Blue evidence -> content hash + provenance -> evidence/result store
                                                        |
readiness + claims + frozen rubric -> diagnostic scorer -> marked output
                                                        |
hash-chained audit -> exported head -> independent append-only witness
```

## Durability model

- Every external artifact declares a namespaced schema and major version.
- Unknown fields fail closed at authorization boundaries.
- Plans are canonicalized and SHA-256 addressed.
- Transitions use compare-and-set semantics through `expected_state`.
- SQLite uses WAL, foreign keys, `synchronous=FULL`, and immediate transactions. A second canonical root covers exercise, evidence, result, and replay state beyond the transition chain.
- Lifecycle roles are explicit and non-interchangeable.
- Terminal stops are irreversible; a restart is a new plan version.
- Compatibility is additive within a major schema. Breaking changes require a new schema, migration, dual-read period, and fixture tests.
- Cryptographic algorithms are identifiers in the schema, not assumptions hidden in code. Algorithm replacement requires a new version and overlapping verification period.
- CI actions are pinned to immutable commits and CI dependencies are exact-version pinned; upgrades require the same assurance gates before adoption.

## State invariants

- No transition can skip a gate.
- White is the only role that authorizes, stops, and closes.
- Exercise Assurance is the only role that marks evidence verified.
- Purple operates but cannot approve or independently attest its own execution.
- Every transition command is short-lived, signed, role-bound, plan-bound, and replay protected.
- Evidence becomes immutable after independent verification.
- Every test case must have six-stage outcomes before verification.

## Availability and recovery

Back up the SQLite database, WAL state, role-trust registry, frozen source artifacts, and externally published anchors as one recovery set. Restore into an isolated path, verify the ledger and anchors before reopening, and never overwrite the only known-good copy. Exercise restoration quarterly and record RTO/RPO as measured results rather than targets.
