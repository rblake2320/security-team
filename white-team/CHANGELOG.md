# Changelog — White Team

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) · Versioning: [SemVer](https://semver.org/)

**Change rules for this file [M]**
- **Any change touching independence, stop authority, or the authorization chain is a MAJOR bump
  and requires Executive Sponsor + General Counsel re-approval.** These are the load-bearing
  controls of the entire operating model; they do not change quietly.
- Changes to scoring, evidence handling, or artifacts are **MINOR**.
- Clarifications are **PATCH**.
- Every entry names its driver.

---

## [1.5.0] — 2026-08-14 — assurance claim gate

### Fixed — 'salt registry' guidance was wrong
- Superseded by a controlled **opening-material vault**
  ([schema](config/opening_material_vault.schema.json)). A broadly accessible list of
  **unrevealed** salts is a high-value disclosure point whose compromise would destroy hiding for
  every open commitment simultaneously.
- Uniqueness is checked **inside the vault at creation**; White receives an *attestation that the
  check ran*, never the corpus. Disclosed salts move to a historical register **after** reveal.
- Reuse detection is primarily **CSPRNG-health evidence** — with correct 256-bit+ salts a
  collision indicates a broken generator, not an ordinary duplicate.
- Backups encrypted under keys **distinct from all five program keys**; dual control or threshold
  recovery; recovery tested **without exposing the material**; backup loss = **readiness regression**.
- **The backup must protect confidentiality before reveal AND availability at reveal.** The
  earlier advice solved availability and ignored confidentiality; solving one property alone
  breaks the process in the other direction.

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

### Fixed — commitment scheme did not provide HIDING (`v1` deprecated)
- **`aegis.inject-commitment.v1` is DEPRECATED and must not be used.** Its `nonce` was published
  in the signed object, so it provided uniqueness but **no hiding** — randomness only defeats
  enumeration when the attacker does not already know it.
- **The defect was worse than that:** the nonce was **not in the digest preimage at all**.
  `package_digest` was SHA-384 over the canonical package alone, so the nonce contributed nothing
  to hiding *or* binding — while its field description asserted that it "blocks a low-entropy
  package being brute-forced." A security claim with no mechanism behind it.
- Inject packages are short and structurally predictable, so this was exploitable in practice,
  not only in theory.
- **v1 was never used in production.** The program has been `NOT_ASSESSMENT_READY` throughout and
  no exercise has been authorized.

### Added — `aegis.inject-commitment.v2`, proper commit/reveal
- `c = H(domain ‖ canonical_package ‖ opening_salt)`, where `opening_salt` is fresh, high-entropy,
  and **withheld until reveal**. At reveal EA publishes the package *and* the salt; White
  recomputes.
- Field disposition made explicit: `commitment_id` and `commitment_digest` **published**;
  `opening_salt` and `inject_package` **withheld**; `public_nonce` optional and **for
  replay/correlation uniqueness only — never relied on for hiding**.
- **Length-framed preimage**, `u64be(len) ‖ value` per field — raw concatenation admits
  boundary-shifting between adjacent fields. Domain string is `aegis.inject-commitment.v2`.
- **JCS (RFC 8785)** canonicalization, declared in the object rather than left to convention.
- **Constant-time compare** on digest verification.
- Verification grew from 9 steps to **12**, adding: opening uses the expected package schema ·
  salt has not appeared in another commitment · commitment, opening, package, and verification
  result preserved as evidence.
- New schema: [`config/inject_opening.schema.json`](config/inject_opening.schema.json) for the
  secret half.

### Added — operational consequences of a secret salt
- **Salt registry required** — verification step 11 is unanswerable without one.
- **Opening material must be backed up.** Losing the salt makes the commitment permanently
  unopenable, which is **indistinguishable from refusing to reveal**.
- Opening retained *after* reveal — it is what proves the commitment was honoured.

### Note
Program state remains **`PREREQUISITES_PENDING` / `NOT_ASSESSMENT_READY`**. This change corrects a
cryptographic construction before first use; it does not advance readiness.

### Driver
Program owner cryptographic correction, 2026-08-14.

---

## [1.3.0] — 2026-08-14 — readiness gate

### Changed — inject commitment is now a SIGNED OBJECT, not a bare hash
- A published hash authenticates nothing about **origin**, **purpose**, or **validity window**,
  and an uncontextualised signature can be replayed across object types. Replaced with
  `aegis.inject-commitment.v1`:
  [schema](config/inject_commitment.schema.json) · [template](templates/inject_commitment.json).
- Signed payload binds `type` (**domain separation — context inside the signature, never
  alongside it**), `exercise_id`, digest, `package_version`, validity window, signer key id,
  `nonce`, and `previous_commitment`.
- **SHA-384** over a **canonical serialization** fixed before first use.
- `nonce` is not decoration: inject lists are short and guessable, so without it a low-entropy
  package can be brute-forced from its digest before reveal.
- Key status is evaluated **as at `created_at`**, not at reveal — otherwise a later key rotation
  retroactively invalidates a legitimate commitment.
- **Nine verification steps at reveal**, all performed by White; any failure invalidates the
  package and is reported under EA-6.
- **Supersession:** a changed package requires a new signed commitment with an explicit
  `supersession_reason`. **Never overwrite the original** — both stay published and chained.
  A supersession created after exercise start is itself a finding.

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

### Added — Exercise Assurance Authority
- **White no longer scores itself.** SoD-4 forbids holding the inject list, controlling the
  exercise, and grading the result. See [§19](../00-shared/18_exercise_assurance.md).
- A **role, not an eighth colour team**: Internal Audit (internal), an external facilitator
  (higher assurance), or a 3PAO / C3PAO / QSA (framework-mandated).
- **White still controls the exercise. Exercise Assurance assesses how White performed that
  control.** EA cannot approve, deny, resume, direct, or countermand a stop in flight.
- Six permissions, exhaustive: hold sealed injects · observe · validate evidence · score White ·
  sign the result · report interference. EA-6 reports direct to Executive Sponsor and Audit
  Committee, bypassing everyone.
- Sealed inject package: **seal hash published to White before the exercise, contents withheld** —
  so White can verify afterwards that the list was not edited to match what happened.

### Added — blind-phase schema, with automatic expiry
- [RoE §5.10.1](../00-shared/04_rules_of_engagement_template.md) now requires a signed objective,
  named blinded participants, enumerated withheld information, a bounded window, a
  declassification trigger, named safety observers, and live deconfliction.
- **A blind phase expires automatically at `end`. It must not continue merely because nobody
  ended it.** Extension requires a new signature, not silence.
- **Safety is never blind** — observers, deconfliction, stop conditions, and the contact roster
  run at full visibility throughout.

### Added — assessment key
- White holds the **authorization key**; Exercise Assurance holds the **assessment key**; the
  evidence service holds the **evidence key**. See [§20](../00-shared/19_aegis_trust_model.md).

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
- `.init` machine-readable team manifest, with `independence: LOAD_BEARING` recorded explicitly.
- `CHANGELOG.md` (this file).
- **SoD-11** — White receives Sentinel Blue's audit-chain head hash as an external anchor, at
  every exercise close and monthly.
- Why Engine obligation: verify a WhyCase exists before an exercise is formally closed
  (RoE §5.19 closure checklist).
- Soul System: White owns the `SOUL-DECISION:` marker — **as a copy for learning only.** The
  Decision Log remains the system of record (constraint S-2).

### Changed
- Blue named as a first-class team in the org chart and RACI, rather than "SOC/Blue".

### Rationale for SoD-11
Sentinel Blue's own README states that its hash chain detects mutation and interior deletion but
**not** rollback or deletion of the entire database, and that external anchoring is still
required. Exporting the head hash into White's WORM evidence manifest closes exactly the gap the
implementation honestly named about itself.

### Driver
Blue Team integration review — [`00-shared/14`](../00-shared/14_blue_team_integration_review.md),
conflict **C-9**.

---

## [1.0.0] — 2026-08-13

### Added
- Initial charter, playbook, artifact templates (A4, A10, A11, A12, plus RoE, authorization
  record, answer key, decision log, scoring rubric, destruction certificate), and the optional
  policy-validation agent specification — deployed **last of all agents, or not at all**.
- Reusable Rules of Engagement template — [`00-shared/04`](../00-shared/04_rules_of_engagement_template.md).
- Gates **G1** (no signature, no scope), **G2** (conditional approval is denial), **G3** (no-go
  means no-go).
- Unconditional stop authority, with the no-retaliation clause for unnecessary stops.
