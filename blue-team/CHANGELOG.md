# Changelog — Blue Team (Sentinel Blue)

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

This changelog covers **both** the team's governance documents and the Sentinel Blue
implementation in this folder.

**Change rules for this file [M]**
- Changes to the platform boundary (no containment, no disablement, no termination, no blocking)
  or to the two-approver rule are **MAJOR** and require Director-level re-approval.
- Changes to `config/coverage_target.json` are **MINOR at minimum and always logged** — that file
  is the denominator of metric M-1, so editing it silently changes every coverage number in the
  program.
- Detection rules, sensor policy, and doc updates are **MINOR**.
- Clarifications and fixes are **PATCH**.

---

## [1.5.1] — 2026-08-14 — typed configuration failures (AUD-05)

### Fixed
- `load_trust_policy` type-checked `sources` but then called `policy.get("version")`
  unguarded, so a syntactically valid non-object policy (array, string, number, bool,
  null) raised `AttributeError` and escaped the typed `ConfigurationError` contract
  callers rely on to fail closed. The object type is now checked once, up front.
- Sensor health upsert could move `last_event_time` and `last_event_id` BACKWARDS when
  events arrived out of order, understating sensor freshness. The upsert now keeps the
  newest observation, and keeps `last_event_id` consistent with the time it belongs to
  rather than letting the two fields describe different events (AUD-04).

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
- `CHARTER.md`, `PLAYBOOK.md`, `ARTIFACTS.md`, `AI_AGENT.md` — the four standard team files the
  other five teams already had. Blue had the implementation and the internal docs but no
  charter, and therefore no defined boundary against the other teams.
- `.init` machine-readable team manifest, including the nine reconciled boundaries.
- `CHANGELOG.md` (this file).
- **Audit-chain head-hash export to White's evidence manifest** at every exercise close and
  monthly. Sentinel Blue's README correctly states that its chain detects mutation and interior
  deletion but not rollback or deletion of the whole database, and that external anchoring is
  still required. This closes that gap (conflict **C-9**, separation-of-duty rule **SoD-11**).
- Why Engine: Blue owns trigger **W-2** — a WhyCase at every incident closure, now part of the
  B14 closure gate. Calls `why.recall` (R-2) during triage of non-obvious alerts.
- Soul System: `SOUL-PAIN:` on rollbacks that did not work as documented.

### Changed
- **Folder renamed `blue team` → `blue-team`.** A space in the path breaks
  `python -m blue_team.cli` in several shells, and the other five folders use hyphens. Test suite
  re-run after the rename: **38 tests, 38 passed.**
- Removed committed `__pycache__/` and `.ruff_cache/` directories.
- Two roles in `docs/OPERATING_MODEL.md` now map to Green rather than Blue: "Detection engineer"
  (**C-1**) and the pipeline-ownership half of "Security platform engineer" (**C-4**). Staff them
  from the SOC if you like — but they deliver into Green's catalog and pipeline. **One catalog.**
- "Recovery lead" scoped to **incident-time** recovery; Green owns scheduled restore drills
  (**C-3**).
- "Vulnerability lead" scoped to exposure **triage and fix validation**; Yellow remediates
  (**C-5**).
- Coverage reporting relabeled **declared** coverage, distinct from Purple's **validated**
  coverage (**C-7**). Both are reported; the gap between them is the interesting number.

### Promoted to program standard
- **Two approvers plus a written rollback for high-risk response** — Blue specified this better
  than the original Green playbook did, so it now applies program-wide, including Green's SOAR
  playbooks (**C-8**).
- **`config/coverage_target.json` is now the single source of truth for metric M-1's
  denominator**, maintained jointly by Purple and Blue. Previously the prioritized technique list
  existed only as prose.
- `docs/ADVERSARIAL_REVIEW.md` is the model the other five teams now copy — Blue was the only
  team that had asked "how would an adversary defeat this function on purpose?"

### Verified
- Test suite executed locally on 2026-08-14: **38 tests, 38 passed**, before and after the
  rename. Not a claim taken from the README.

### Known / not fixed
- **R-1:** `Owner's Inbox/2026-08-13_sentinel-blue-defensive-platform.md` and
  `Team/tasks/20260813-sentinel-blue-defensive-platform.md` still reference
  `PKA testing\blue team` — a path that stopped existing when the folder was moved under
  ``, before this review. Editing PKA delivery records is an owner decision.
- **R-3:** `rules/` will drift from Green's future detection-as-code repo until one is declared
  canonical.
- **R-4:** Blue's severity labels are a *response* clock; the program's severity SLAs are a
  *remediation* clock. Same words, different meaning — reconcile at the first joint exercise.
- **R-5:** `coverage_target.json` is weighted toward Windows endpoint and identity; cloud
  coverage is thinner than the identity→cloud pilot needs. Extend from the threat model, not by
  padding.

### Driver
Blue Team integration review — [`00-shared/14`](../00-shared/14_blue_team_integration_review.md).

---

## [1.0.0] — 2026-08-13

### Added
- **Sentinel Blue** — local-first defensive operations core. Normalized telemetry → correlated
  alerts → auditable cases → coverage evidence → sensor-health findings → approval-gated
  response plans.
- Modules: `canonical`, `models`, `store`, `detection`, `coverage`, `health`, `response`,
  `source_auth`, `assurance`, `errors`, `cli`. 38 tests.
- Nine documents: architecture, operating model, threat model, incident response, detection
  engineering, program control matrix, adversarial review, deployment checklist, references.
- Configuration: `coverage_target.json` (22 techniques), `rule_manifest.json`,
  `sensor_policy.json`, `source_trust.example.json`.
- **Platform boundary, deliberate:** never performs containment, account disablement, process
  termination, or blocking. Emits response *plans* requiring documented approval.
- Trust boundaries: telemetry (all fields untrusted), detection (rules validated, no arbitrary
  code or regex), evidence (inserts and audit writes share a transaction), response (two
  approvers + rollback for high-risk).
- Tamper-evident hash-chained audit log, with its own limitation stated honestly: detects
  mutation and interior deletion, **not** whole-database rollback.
