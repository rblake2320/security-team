# Changelog — Purple Team

All notable changes to this team's charter, playbook, artifacts, and agent spec.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

**Change rules for this file [M]**
- A change to decision authority, separation of duties, or a gate is a **MAJOR** bump and
  requires re-approval by the charter's approver.
- A change to responsibilities, metrics, or staffing is a **MINOR** bump.
- Clarifications and corrections are **PATCH**.
- Every entry names the driver: an exercise ID, a finding ID, a lesson, or a decision.

---

## [1.8.0] — 2026-08-14 — engineering completion-register closure

### Added
- Registry- and role-verified formal/rehearsal authorizations and signed environment attestations.
- Production-role formal runner path with TEST_ONLY fixture refusal and empty-store fail-closed behavior.
- Mid-run revocation checks at four material safety boundaries.
- Domain-separated Red execution receipts, EA assessment results, and White audit-anchor receipts.
- Five-purpose rotation/recovery evidence validation, including holder-unavailable recovery.
- A fixed-registry `repository.posture` Red check mapped to ATT&CK T1195.002.

### Corrected
- `claim_check.py` is now a subordinate claim/lint CI gate; `aegis_purple validate-program`
  remains the canonical structural validator.
- Why Engine/Soul integration is explicitly a manual practice, not unimplemented automation.
- Completion-register arithmetic corrected from 42 to 44 items.

### Verified
- 151 tests pass: Purple 37, Red 21, Blue 38, exercise harness 48, shared commitment 7.
- 19 of 22 registered claims are locally evidenced; the remaining three require external facts.

---

## [1.7.0] — 2026-08-14 — integrated rehearsal and signed external gates

### Added
- Dual-authority, Ed25519-signed gate attestations with exact assertions, evidence digests,
  90-day maximum validity, distinct keys, and role/tamper rejection tests.
- Disposable first-run rehearsal mapping Orange's predicted IDOR abuse path to one bounded Red
  test, Blue detection and response evidence, Yellow remediation, Green control, and Purple retest.
- Windows/POSIX containment proof with skips forbidden and two-platform CI.
- Canonical package manifest/check and SHA-256-locked cross-platform runtime artifacts.

### Verified
- The offline rehearsal confirmed the seeded baseline weakness, triggered the expected detection,
  applied project-scope enforcement, and returned 403 on the identical retest without networking.

### Driver
Closure of every locally actionable assurance gap and first integrated engineering rehearsal.

---

## [1.6.0] — 2026-08-14 — executable assurance core

### Added
- Dependency-light `aegis_purple` package for frozen exercise plans, non-skippable lifecycle
  state, evidence binding, six-stage result completeness, diagnostic scoring, and audit anchors.
- Ed25519 role-signed transition commands with exact plan binding, five-minute validity,
  nonce replay protection, and explicit White/Purple/Exercise-Assurance separation.
- Production observation-only enforcement and verified rollback requirement for high-safety cases.
- Machine evaluation of readiness and assurance-claim registries without converting a
  configuration pass into an efficacy claim.
- 32 adversarial unit tests, CI engineering-integrity workflow, and a separate manual
  assessment-issuance workflow that fails while prerequisites remain open.
- Versioned JSON schema, threat model, architecture, operations, security limits, and
  adversarial review.

### Security posture
- Program state remains `NOT_ASSESSMENT_READY` and results remain
  `TRAINING_OR_ENGINEERING_USE_ONLY` until all external prerequisite gates are independently
  verified. The new core enforces that boundary; it does not waive it.

## [1.5.0] — 2026-08-14 — assurance claim gate

### Added — claim-mechanism-evidence discipline with an automated checker
- Shared **assurance-claim registry** ([`00-shared/config/assurance_claims.json`](../00-shared/config/assurance_claims.json)):
  every normative claim must state property, scope, mechanism, assumptions, evidence,
  **negative/falsification tests**, owner, reviewer, regression triggers, and limitations.
- **Lifecycle:** `PROPOSED -> MECHANISM_IDENTIFIED -> TESTABLE -> EVIDENCED ->
  INDEPENDENTLY_REVIEWED -> OPERATIONAL`, with `DISPUTED` / `REGRESSED`. No state skipped.
- **CI tool** ([`00-shared/tools/claim_check.py`](../00-shared/tools/claim_check.py)) enforcing
  R1-R7: normative language without a claim id · no named mechanism · no negative tests ·
  documentation-only evidence · skipped/stale evidence · OPERATIONAL while a gate is false ·
  mechanism changed without a version increment.
- **Invariant:** `CLAIM != CONTROL != MECHANISM != EVIDENCE`.
- **The rule:** *no security property is credited because it appears plausible in prose.*

### Found — by running it on our own corpus
- **3 of 10 claims are EVIDENCED.** 1 DISPUTED, 1 REGRESSED, 3 MECHANISM_IDENTIFIED, 2 TESTABLE.
- **26 unsupported claim candidates** across 93 markdown files (R1 lint).
- `AEGIS-LEDGER-TAMPER-001` **half-evidenced**: Aegis and Sentinel Blue both claim their chains
  detect *"mutation and interior deletion."* Only **mutation** is tested. No test deletes an
  interior record. Narrow the claim or add the negative test.
- `AEGIS-SOD-AUTHZ-001` **has no evidence**: nobody has attempted to authorize as Red and been
  denied. The model's strongest control is asserted, not demonstrated.

### Driver
Program owner assurance-claim decision, 2026-08-14. See [`00-shared/23`](../00-shared/22_assurance_claims.md).

---

## [1.4.0] — 2026-08-14 — commitment hiding fix

### Note
Program state remains **`PREREQUISITES_PENDING` / `NOT_ASSESSMENT_READY`**. This change corrects a
cryptographic construction before first use; it does not advance readiness.

### Driver
Program owner cryptographic correction, 2026-08-14.

---

## [1.3.0] — 2026-08-14 — readiness gate

### Added — automated assessment readiness gate (`PROGRAM-READINESS-GATE-001`)
- Program state is now **`PREREQUISITES_PENDING` / `NOT_ASSESSMENT_READY`**, enforced by
  [`00-shared/config/assessment_readiness.json`](../00-shared/config/assessment_readiness.json),
  not by a paragraph of prose.
- While not ready: exercises **may** run, diagnostic scores **may** be computed, **no assurance
  statement may be issued**, and every artifact carries `TRAINING_OR_ENGINEERING_USE_ONLY`.
- **Removing that marking requires a state transition, not an editorial decision.**
- Seven-state model added, with the rule: **no state may be skipped merely because test suites
  are green.** A passing suite is evidence about code; a transition is a claim about the program.
- Regression triggers defined — the program returns to `PREREQUISITES_PENDING` automatically if a
  gate ceases to hold, a signing key leaves custody, canonical ambiguity returns, or the Exercise
  Assurance performer becomes unavailable or conflicted.

### Driver
Program owner final review, 2026-08-14. See [`00-shared/22`](../00-shared/21_readiness_gate.md).

---

## [1.2.0] — 2026-08-14 — governance review

### Changed — assessment weights ratified as `baseline-v1`
- Program weight for this team is now exact: see [`config/scorecard.json`](config/scorecard.json).
  Purple 18.75 · White 18.75 · Blue 15.00 · Yellow 15.00 · Green 11.25 · Orange 11.25 · Red 10.00
  (= 100.00%).
- Labelled **governance defaults, not empirically validated.** Revise only through a versioned
  governance change after several exercises produce a score distribution — never per exercise,
  and never after seeing results.

### Added — auto-fail applied BEFORE aggregation
```
if any(team.auto_fail): program_status = "FAILED"   # weighted score kept for diagnostics only
elif evidence_completeness < threshold: program_status = "INSUFFICIENT_EVIDENCE"
else: program_status = score_to_readiness(weighted_score)
```
A weighted mean is not a safety property. Without this ordering, a catastrophic Red or White
failure is averaged away by strong performance elsewhere.

### Added — 95-100% triggers a mandatory challenge review
Four hypotheses must be examined: genuine maturity · insufficient test difficulty · scenario
leakage via telemetry or process · permissive scoring. **It never means "no more testing needed."**

### Driver
Program owner governance review, 2026-08-14. Full record: [`00-shared/21`](../00-shared/20_closure_plan.md), [`00-shared/19`](../00-shared/18_exercise_assurance.md), [`00-shared/20`](../00-shared/19_aegis_trust_model.md).

---

## [1.1.0] — 2026-08-14

### Added
- `.init` machine-readable team manifest.
- `CHANGELOG.md` (this file).
- Why Engine obligations: owns triggers **W-1** (WhyCase at retest closure) and **W-3**
  (systemic lesson); calls `why.recall` at **R-3** before scenario selection; runs
  `why-engine doctor` weekly and `stats` monthly.
- Soul System markers: `SOUL-OUTCOME:` on retest verdicts, `SOUL-PAIN:` on failed retests.

### Changed
- **M-1's denominator is now bound to `blue-team/config/coverage_target.json`** — a
  version-controlled, machine-readable list maintained jointly with Blue. Previously the
  prioritized technique list existed only as prose, which is the most common way coverage
  metrics get fudged.
- Blue elevated from "SOC/Blue" to a peer team. Purple's validation partner is now named, and
  the six-stage chain is explicitly split: stages 1–3 grade Green, stages 4–6 grade Blue.

### Driver
Blue Team integration review — [`00-shared/14`](../00-shared/14_blue_team_integration_review.md),
conflicts **C-6** (hunt findings as scenario source) and **C-7** (declared vs. validated coverage).

---

## [1.0.0] — 2026-08-13

### Added
- Initial charter, playbook, artifact templates (A1, A2, A3, A5, A6, A7, A9, A13), and the
  optional coordination agent specification.
- Six-stage outcome chain as the scoring model: prevented / logged / alerted / investigated /
  contained / reported.
- Gates **G4** (no evidence, no finding) and **G6** (verbatim retest).
