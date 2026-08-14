# Aegis Purple hardening delivery — 2026-08-14

## Outcome

`[CONFIRMED]` The Purple Team folder now contains a runnable, fail-closed assurance core rather than documentation alone. Local engineering-integrity gates pass. The implementation does not execute offensive actions and did not start a service, scheduled task, collector, or background workload.

`[CONFIRMED]` Two of four readiness gates are now verified: canonical implementation selection and Windows/Linux containment. The program remains `NOT_ASSESSMENT_READY` until the two genuinely external authority/custody gates are signed. All exercise output remains `TRAINING_OR_ENGINEERING_USE_ONLY`.

## Material controls delivered

- Strict, bounded, Unicode-normalized JSON handling and exact schema fields.
- Content-addressed frozen plans that bind scope, cases, telemetry, detections, rollback, readiness, rubric, and role trust.
- Plan-pinned Ed25519 role registry; short-lived signed commands; key-role checks; nonce replay defense.
- Non-skippable compare-and-set lifecycle with White authorization/stop/close and independent evidence verification.
- Production observation-only policy and high-safety rollback requirement.
- Evidence/test-case binding and mandatory six-stage outcomes before verification.
- Diagnostic scoring with exact evidence, strict numeric types, and automatic failures evaluated before aggregation.
- Transition audit chain plus a canonical state root for exercise, evidence, results, and replay state.
- External anchor export with an explicit independent-publication limitation.
- Versioned JSON schema, SBOM, exact runtime/CI version pins, immutable CI action pins, vulnerability audit, and a separate assessment-issuance workflow.
- Registered assurance claims for every new material mechanism.
- Dual-authority signed attestations for the Exercise Assurance and production-key-custody gates.
- A fully offline first-run rehearsal connecting Orange predictions to Red, Blue, Yellow, Green, White, and Purple evidence and retest.
- Normative-claim lint reduced from the inherited candidate set to zero unsupported candidates across 103 Markdown files.

## Verification evidence

- `[CONFIRMED]` Aegis Purple: 37/37 tests passed.
- `[CONFIRMED]` Sentinel Blue: 38/38 tests passed.
- `[CONFIRMED]` Aegis Red: 21/21 tests passed on Windows; no skips.
- `[CONFIRMED]` Exercise harness: 48/48 tests passed, including formal-role separation, signed attestations, receipts, lifecycle validation, and mid-run revocation.
- `[CONFIRMED]` Shared commitment construction: 7/7 tests passed.
- `[CONFIRMED]` Ruff passed across Purple, Red, Blue, shared tools, and CI tools.
- `[CONFIRMED]` Python compilation passed across the same scope.
- `[CONFIRMED]` 40 JSON documents and two workflow YAML documents parsed successfully.
- `[CONFIRMED]` Runtime dependency audit reported no known vulnerabilities for the exact pinned baseline.
- `[CONFIRMED]` Claim registry: 22 claims; 19 `EVIDENCED`, three `MECHANISM_IDENTIFIED`, zero `DISPUTED`, zero `REGRESSED`; zero blocking registry violations.
- `[CONFIRMED]` Readiness and issuance gates return the expected hold for two external prerequisites.

## Remaining production boundaries

1. `[EXTERNAL ACTION REQUIRED]` Internal Audit and the Executive Sponsor name and COI-screen the Exercise Assurance performer, then sign the exact gate attestation.
2. `[EXTERNAL ACTION REQUIRED]` White and the CISO deploy distinct non-exportable keys, exercise denial/rotation/recovery/revocation/logging, hash the evidence, then sign the exact gate attestation.
3. `[EXTERNAL ACTION REQUIRED]` Publish audit/state anchors to a separately administered append-only witness and exercise rollback detection.
4. `[UNKNOWN]` Production detection recall, false-positive rate, MTTD, MTTC, recovery performance, and staffing effectiveness until representative authorized exercises run.

## Decision

- Local engineering use and controlled rehearsal: **GO**, with mandatory training marking.
- Assurance issuance, production authorization, customer/regulator/board claims: **HOLD**.
