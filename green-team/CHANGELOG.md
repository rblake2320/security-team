# Changelog — Green Team

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

**Change rules for this file [M]**
- Changes to the defensibility gate criteria or to destructive-automation approval are **MAJOR**.
- Changes to detection standards, telemetry policy, or metrics are **MINOR**.
- Clarifications are **PATCH**.
- Every entry names its driver.

---

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
- `.init` machine-readable team manifest, with the Blue boundary reconciliations recorded as
  structured fields.
- `CHANGELOG.md` (this file).
- Why Engine obligation: supply the `whyNotCaught` telemetry/detection detail; use
  `why-engine stats` recurring clusters to prioritize paved-road work.
- Soul System: `SOUL-PAIN:` on silent-telemetry events and on detections that were deployed but
  did not fire.

### Changed
- **Destructive automated response now requires TWO approvers plus a written rollback** — adopted
  from Sentinel Blue, which specified this control better than the original Green playbook did
  (System Owner approval alone). The stricter rule wins, and it now applies to Green's SOAR
  playbooks as well as Blue's response plans.
- Ownership boundaries with Blue made explicit: Green authors and deploys detection content
  (**C-1**); Green owns scheduled restore drills while Blue owns incident-time recovery
  (**C-3**); Green owns the telemetry pipeline while Blue owns noticing it is broken (**C-4**).

### Noted
- `blue-team/rules/` is the reference rule *format*. Production detection content will live in
  Green's detection-as-code repo. **Until that repo exists (roadmap Phase 2, deliverable 2.4),
  the two will drift** — tracked as residual **R-3**.

### Driver
Blue Team integration review — [`00-shared/14`](../00-shared/14_blue_team_integration_review.md),
conflicts **C-1, C-3, C-4, C-8**.

---

## [1.0.0] — 2026-08-13

### Added
- Initial charter, playbook, artifacts (detection-as-code standard, telemetry inventory,
  hardening baselines, paved-road catalog, defensibility gate, SOAR playbooks, restore drills),
  and the optional detection-recommendation agent specification.
- **Defensibility gate** with blocking authority for production release.
- Detection lifecycle standard: a detection never observed to fire is a hypothesis, not a
  detection.
- M-10 (telemetry availability) established as the foundation metric — every detection metric is
  conditional on it, and coverage claims computed over dead sources are how dashboards lie.
