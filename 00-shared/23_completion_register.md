# §24 — Completion Register

← [Index](../README.md) · Related → [§21 Closure Plan](20_closure_plan.md) · [§22 Readiness Gate](21_readiness_gate.md) · [§23 Claim Gate](22_assurance_claims.md)

**Compiled:** 2026-08-14, from repository state — claim registry, readiness config, `.init`
manifests, CI workflows, and code inspection. **Not from recollection.**

**Definition of "complete":** program state reaches `ASSESSMENT_ISSUED` with a signed assurance
statement over a real integrated exercise, and every claim is either `EVIDENCED` or a signed,
expiring accepted limitation. Nothing carried silently.

**Current state:** `PREREQUISITES_PENDING` · 2 of 4 gates VERIFIED · 19 of 22 claims EVIDENCED ·
151 tests green · 0 real integrated exercises run (the TEST_ONLY engineering rehearsal has run).

**Rule for this register:** every item has a falsifiable exit criterion. "Done" means the
criterion is demonstrably true, not that the work was attempted.

---

## A0 · Version control and CI — found 2026-08-14, mostly fixed

Two defects of the same class as everything else in this program: **a mechanism
asserted, never demonstrated.** Both were invisible to every existing gate.

| # | Finding | State |
|---|---|---|
| **A0-1** | **The entire program directory was UNTRACKED.** 251 files, 2.6 MB — no git history, no backup, one disk | ✅ **CLOSED** — committed and pushed to the private `pka-workspace` remote |
| **A0-2** | **CI workflows were inert.** They sat at `.github/workflows/`. GitHub Actions reads **only** `<repo-root>/.github/workflows/`, and the repo root is `PKA testing/`. They had never run and could not run. **Every claim whose evidence was "CI enforces X" was unevidenced** | ✅ **FIXED** — path-scoped workflow installed at the repo root |
| **A0-3** | **No enforcement without GitHub.** Even once reachable, the gates only run on push to a host that executes Actions | ✅ **FIXED** — `00-shared/tools/run_ci.py` runs all 9 gates locally; `--assurance` fails closed |
| **A0-4** | **Fixture private keys were unprotected.** `_fixture_private_keys.json` sat on disk with no `.gitignore`; the first commit would have written private keys into git history permanently | ✅ **FIXED** — `.gitignore` + falsification-tested detector (`PROGRAM-REPO-HYGIENE-001`) |
| **A0-5** | **Repository placement** | ✅ **DECIDED** — committed to `pka-workspace` (private, verified) on branch `agent-evolution-loop-closure`. Extraction to a dedicated repo remains available later |
| **A0-6** | **CI had never run.** First execution failed: fixture private keys are gitignored but fixture public keys were committed, so a fresh clone could not run the rehearsal | ✅ **FIXED** — trust material and engineering scaffolding are generated on demand; nothing signed is committed |
| **A0-7** | **Windows-only integrity failure.** Git LF→CRLF translation altered the raw bytes that Sentinel Blue's rule manifest hashes | ✅ **FIXED** — `.gitattributes` with `-text` on content-addressed files. Green on ubuntu **and** windows, run `31817937014` |

**Claims corrected as a result:** `PROGRAM-CI-SEPARATION-001` → v2. Its v1 asserted CI
enforcement while the workflow was at a path Actions never reads.

---

## A · External authority — nobody inside the repository can close these

These are blocked on humans with authority, not on engineering. **Attempting to satisfy any of
them from inside the repo would be forgery.**

| # | Item | Owner | Exit criterion | Blocks |
|---|---|---|---|---|
| **A1** | Enrol the **production trust store**. It is empty. Four roles required: `white_ciso`, `internal_audit`, `executive_sponsor`, `clearance_issuer` | White + CISO | 4 public keys in `exercise/config/trust/production/`, each with a custody record; `test_formal_mode_production_store_is_empty` inverts and is rewritten | B1, C1, all of C |
| **A2** | Name and COI-screen the **Exercise Assurance performer** against EA-COI-1..6 | Executive Sponsor + Internal Audit | Named individual recorded; EA-6 reporting line to Exec Sponsor + Audit Committee confirmed **in writing**; performer holds the assessment key | Gate `exercise_assurance_operational` |
| **A3** | **Key custody**: authorization key into a White-controlled HSM/secret manager; evidence key to the evidence service | White + CISO | Key never on a workstation; custody record names the holder | Gate `key_custody_verified` |
| **A4** | **IAM denial for Red**, verified by attempting access **as Red** and being denied | White + CISO | Denial demonstrated and logged; not a policy document | A3, B2 |
| **A5** | **Rotation and recovery exercised** for all five keys, including with the holder unavailable | White + CISO | Recovery performed once, evidenced | Gate `key_custody_verified` |
| **A6** | **Emergency revocation tested end to end** | Executive authority | Revocation issued, execution failed closed, evidenced | Gate `key_custody_verified`, B6 |
| **A7** | Key use logged to a store **its holders cannot alter** | White + CISO | Append-only log demonstrated | Gate `key_custody_verified` |
| **A8** | **Legal and Privacy pre-approve the RoE template** as an org standard | General Counsel + DPO | Signed once; per-exercise review then covers deltas only | C2 |
| **A9** | **System owner(s) named and signing** for the first real target | Business | Signed authorization record per in-scope system | C2 |
| **A10** | White signs a **production environment attestation** (11 boundaries). The current one is `TEST_ONLY` fixture | White | Signed, non-fixture attestation for a real exercise | C2 |

---

## B · Engineering — can be closed inside the repository

| # | Item | Exit criterion | Claim / gap it closes |
|---|---|---|---|
| **B1 — ENGINEERING CLOSED** | **Production clearance-issuer path.** | Ephemeral production-role test issues and executes a formal clearance; wrong-role and fixture signers are refused. Real enrollment remains A1 | `EXERCISE-CLEARANCE-BINDING-001` v2 |
| **B2 — BLOCKED BY A4** | **Prove Red cannot authorize.** Application tests cannot demonstrate production custody **as Red** | Requires a real Red IAM identity attempting access to the real authorization key and receiving a logged denial | `AEGIS-SOD-AUTHZ-001` remains `MECHANISM_IDENTIFIED`; the original B/A classification was inconsistent |
| **B3 — ENGINEERING CLOSED** | **Execute Blue's audit-chain export** into White's manifest | Signed TEST_ONLY receipt recorded at `exercise/evidence/blue_anchor_receipt.json`; external immutability remains A7 | Operational claim remains pending external deployment |
| **B4 — CLOSED** | **Trust-model step 3 — execution receipt.** | Domain-separated Red execution receipt binds authorization digest, test cases, and action digest; tampering and role substitution rejected | `EXERCISE-EXECUTION-RECEIPT-001` |
| **B5 — CLOSED** | **Trust-model step 4 — assessment key wiring.** | EA/Internal Audit signature verifies only when evidence completeness is true; Red role rejected | `EXERCISE-ASSESSMENT-SIGNATURE-001` |
| **B6 — CLOSED** | **Trust-model step 5 — revocation object** | Runner rechecks at four material safety boundaries; injected mid-run revocation stops before retest | `EXERCISE-REVOCATION-BOUNDARY-001` |
| **B7 — ENGINEERING CLOSED** | **Trust-model step 6 — rotation/recovery validator** | All five purposes required; distinct rotation, recovered-current match, chronology, and holder-unavailable test enforced. Real exercise remains A5 | `EXERCISE-KEY-LIFECYCLE-001` |
| **B8 — CLOSED** | **Environment attestation signature verification.** | v2 attestation is domain-signed, trust-store and role verified; tampering and TEST_ONLY-in-formal refused | `EXERCISE-PREFLIGHT-REFUSAL-001` v2 |
| **B9 — CLOSED** | **Formal-mode runner path.** | Ephemeral production-role integration test executes formal authorization + clearance; real gates/store remain fail-closed | `EXERCISE-PREFLIGHT-REFUSAL-001` v2 |
| **B10 — CLOSED** | **Reconcile two validators.** `aegis_purple validate-program` is the canonical structural validator; `claim_check.py --allow-not-ready` is the subordinate claim/lint gate | Both run in engineering CI; claim violations fail while honest pending readiness is permitted | Closed 2026-08-14 by CI wiring |
| **B11 — CLOSED** | **why-engine and soul-system have zero code consumers.** | §16 now explicitly labels every trigger and recall point as manual practice with no runner enforcement | Closed 2026-08-14 without inventing automation |
| **B12 — CLOSED** | **Expand Aegis checks (R-7).** | `repository.posture` is fixed-registry, offline, ATT&CK T1195.002-mapped, budgeted, and covered by positive, negative, truncation, and Windows/POSIX containment tests | Closed 2026-08-14; coverage remains deliberately bounded |

---

## C · The first real exercise — gates are not an assessment

**Everything in this section has happened zero times.** The current harness runs one synthetic
IDOR scenario with single-file team artifacts. That is a rehearsal of the *mechanism*, not an
exercise.

| # | Item | Exit criterion |
|---|---|---|
| **C1** | Sealed **inject package + v2 commitment** issued for a real exercise | Commitment published before start; opened at reveal; all 12 verification steps pass |
| **C2** | **Signed RoE** for a real, non-synthetic target | All signatures per §5.18; conditions cleared |
| **C3** | **The §18 integrated exercise**, all 12 steps, all 7 teams | Each step evidenced; no step skipped |
| **C4** | **Blind phase** exercised, including **automatic expiry** | Phase expires at `end` without anyone ending it; safety never blinded |
| **C5** | **Deconfliction** exercised against a real SOC | Every query answered ≤5 min; ambiguity resolved as REAL |
| **C6** | **Safety injects** delivered by EA; White scored against the frozen rubric | White scorecard signed by EA with the assessment key |
| **C7** | **Restore drill** with measured RTO/RPO | Restored to isolated environment; data verified usable |
| **C8** | **Real finding** through discovery → fix → verbatim retest → regression test | One finding completes all eight steps with evidence |
| **C9** | **Evidence manifest + chain of custody** produced and verified | Retrievable by control ID; hashes verified |
| **C10** | **AAR published** within 10 business days, participants correcting facts only | Published; conclusions unaltered by participants |
| **C11** | **Scorecard calibration**: ≥3 exercises under `baseline-v1`, distribution reviewed | `baseline-v1` reaffirmed or `baseline-v2` ratified with rationale |
| **C12** | **Adversarial reviews for the 5 remaining teams** (White, Green, Orange, Yellow, Red). Only Blue and Purple have one | Orange produces each; White first |

---

## D · Organizational instantiation

| # | Item | Exit criterion |
|---|---|---|
| **D1** | **All 16 Open Decisions (O-1..O-16) are open.** The model is parameterized against P2 defaults and describes no real organization | Each closed by its named owner, recorded in README §0.4 |
| **D2** | **No role is filled by a named human.** 11 blank primary/backup slots in §3.4; every charter's staffing table is unpopulated | Named primary **and** backup for every `[M]` role; backup exercised within 12 months |
| **D3** | **Per-system control applicability determinations.** None made. CA-2(1)/CA-8(1)/SA-11(5) each demand a different relationship | A recorded determination per system, not inherited globally |
| **D4** | `PROGRAM-RED-INDEPENDENCE-001` has no organizational chart to verify against | Reporting lines exist and are verifiable → claim EVIDENCED |

---

## E · Accepted limitations — must be signed, not silently carried

These are **not defects**. They are residual risks that a named owner must accept with an expiry,
or close. Carrying them without a signature is how a limitation becomes an assumed capability.

| # | Limitation | Options |
|---|---|---|
| **E1** | The commitment **does not conceal package length** unless padded | Accept, or add padding |
| **E2** | Clearance **does not defend against host-level access** to the signing key | Accept (custody is the control), or add HSM-backed signing |
| **E3** | Neither the scorer nor the readiness gate **can stop a human copying a number into a slide** | Accept; mitigate by marking and training |
| **E4** | Blue's chain **does not detect whole-store rollback** | Closed by B3 (external anchor), or accept |
| **E5** | Aegis **excludes** credential theft, persistence, evasion, malware, destructive payloads, uncontrolled scanning | Accept as scope, and state that Red's coverage is correspondingly narrow |
| **E6** | Engineering-mode results are **fixture-signed** and can never be assurance | Accept; enforced by the trust-store split |

---

## Dependency order

```
A1 A2 A3 A4 A5 A6 A7        (external authority - START HERE, longest lead time)
      |
      +--> gates: exercise_assurance_operational + key_custody_verified VERIFIED
      |
      +--> B1 B2 (production issuer, Red-denial proof)
      |
      v
   ASSESSMENT_READY
      |
      +--> A8 A9 A10 + C1 C2        (authorize a real exercise)
      |
      v
   EXERCISE_AUTHORIZED --> C3..C10 --> EVIDENCE_VERIFIED --> ASSESSMENT_ISSUED
                                          |
                                          +--> C11 (calibration, 3 exercises)

B3..B12  parallel, not blocking readiness
D1..D4   parallel, but D1 blocks any claim about a real organization
E1..E6   sign before ASSESSMENT_ISSUED
```

**The critical path is A1–A7.** Every one of them requires a human with authority to act, and
none can be advanced from inside the repository. Everything in B can proceed in parallel today.

---

## What "no gaps" means here

This register is complete against **what the repository can currently see**: the claim registry,
the readiness config, the `.init` manifests, the CI workflows, and the code. It cannot enumerate
requirements arising from an organization that has not been instantiated (**D1**) — those will
add items, and that is expected rather than a defect in this list.

**Total: 44 items.** The earlier total of 42 was an arithmetic defect: 10 external + 12
engineering + 12 first-exercise + 4 organizational + 6 limitations = 44.
