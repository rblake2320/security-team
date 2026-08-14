# §21 — Closure Plan

← [Index](../README.md) · Related → [§19 Exercise Assurance](18_exercise_assurance.md) · [§20 Trust Model](19_aegis_trust_model.md) · [§18 Assessment](17_capability_assessment.md)

**Authority:** program owner decision, 2026-08-14. **Order is prescribed — work it top to bottom.**

The sequence is not arbitrary. Items 1 and 2 are prerequisites for trustworthy evidence; item 3
is a prerequisite for a trustworthy score; item 4 is a prerequisite for trusting a containment
claim. Doing item 7 first would calibrate against numbers that are not yet meaningful.

---

## 1 · R-8 — Select the canonical implementation

| | |
|---|---|
| **Problem** | `PKA testing\Red Team (1)` and `Purple team\red-team\` both exist and now diverge. The original was left in place because it was locked; the copy has since gained six governance files |
| **Actions** | Freeze both copies · compare them · designate one canonical path · archive or remove the other from active development · **add CI that rejects duplicate package identities** |
| **Owner** | Owner / ATLAS |
| **Exit criteria** | One path declared canonical in writing · the other archived or deleted · CI fails on a duplicate `aegis-red-team` package identity · [red-team/CHANGELOG.md](../red-team/CHANGELOG.md) records the decision |
| **Blocks** | Everything downstream — you cannot establish key custody for an implementation whose location is ambiguous |
| **Effort** | Hours |

**Also stale, same root cause:** `Owner's Inbox/2026-08-13_sentinel-blue-defensive-platform.md`
and `Team/tasks/20260813-sentinel-blue-defensive-platform.md` still reference
`PKA testing\blue team`, a path that no longer exists. Fix in the same pass.

---

## 2 · R-10 — Establish key custody

| | |
|---|---|
| **Problem** | The model's strongest control — Red can execute but cannot authorize — is currently **procedural**. No named holder, no HSM, no IAM denial, no tested revocation |
| **Actions** | Authorization keys into a **White-controlled HSM or secret manager** · **prohibit Red access through policy AND IAM** · document recovery and rotation · **test emergency revocation** |
| **Owner** | White + CISO |
| **Exit criteria** | Named holder recorded · key in an HSM/secret manager, never on a workstation · IAM policy explicitly denying Red identities, **verified by attempting access as Red and being denied** · rotation and recovery documented and **exercised once** · emergency revocation tested end to end · use of the key logged to a store its holder cannot alter |
| **Effort** | 1–2 weeks including procurement of custody |

> **Migration step 1 is complete in Aegis v0.2.0.** Authorization and evidence operations use
> distinct domains, purpose-bound keys, CLI arguments, and bidirectional rejection tests. This
> does not replace the HSM/IAM custody evidence required by this closure item.

---

## 3 · White assessor separation

| | |
|---|---|
| **Problem** | White cannot hold the inject list, control the exercise, and grade itself (SoD-4) |
| **Actions** | Create the **[Exercise Assurance](18_exercise_assurance.md)** role · define the sealed inject format · set evidence permissions · establish the independent score signature |
| **Owner** | Executive Sponsor + Internal Audit |
| **Exit criteria** | Performer named and COI-screened (EA-COI-1..6) · sealed inject package format agreed, with the **seal hash published to White before the exercise and contents withheld** · EA holds the assessment key · EA-6 reporting line to Executive Sponsor and Audit Committee confirmed in writing · EA permissions limited to the six in §19.3 and **nothing else** |
| **Effort** | Days, plus scheduling |

**Do not skip because it feels bureaucratic.** Until this exists, the single most important
number in the program — how well the authorization and safety function performed — is
self-reported.

---

## 4 · R-6 — Prove containment

| | |
|---|---|
| **Problem — RESOLVED 2026-08-14** | `test_source_link_escape_is_rejected` now exercises an NTFS junction on Windows and a symbolic link on POSIX; CI forbids skips |
| **Actions** | Complete: Windows junction test and POSIX symbolic-link test run in the CI matrix with skips forbidden |
| **Owner** | Red Lead |
| **Exit criteria** | Test passes in **both** supported execution environments · CI enforces it · a skip in CI is treated as a failure, not a pass |
| **Rule** | A future skip or platform removal regresses the readiness gate automatically |
| **Effort** | Hours |

---

## 5 · Blind-phase authorization

| | |
|---|---|
| **Problem** | Blind phases needed a signed objective, a bounded window, disclosure rules, and automatic expiry |
| **Status** | **Schema added** — [RoE §5.10.1](04_rules_of_engagement_template.md) |
| **Remaining** | Adopt it in the org-standard RoE; brief White and Purple; confirm the tooling can enforce expiry rather than relying on someone remembering |
| **Owner** | White Exercise Director |
| **Exit criteria** | §5.10.1 present in the org-standard RoE · one blind phase run under it and correctly **auto-expired at `end` without anyone ending it manually** · safety observers confirmed never blinded · deconfliction confirmed live throughout |
| **Effort** | Hours |

---

## 6 · R-7 — Expand Red coverage

| | |
|---|---|
| **Problem** | Only two checks ship (`source.static`, `http.headers`). Red's ATT&CK contribution is narrow |
| **Actions** | Add checks based on **prioritized mission threats**, not raw ATT&CK technique count |
| **Owner** | Purple + Red |
| **Exit criteria** | Each new check traces to a named mission threat and a risk-register entry · registered in the **fixed** registry with declared target kinds and active-request flag · positive, negative, boundary, and containment tests · peer reviewed |
| **Anti-goal** | **Maximizing technique count.** Coverage counted rather than achieved is the exact failure metric M-1 was designed to expose |
| **Effort** | Ongoing |

---

## 7 · Calibrate scores

| | |
|---|---|
| **Problem** | `baseline-v1` weights are governance defaults, not empirically validated |
| **Actions** | Run several exercises · examine the score distribution · adjust weights **only through a versioned governance change** |
| **Owner** | Program owner + Exercise Assurance |
| **Exit criteria** | ≥3 exercises scored under `baseline-v1` · distribution reviewed · either `baseline-v1` reaffirmed or `baseline-v2` ratified with recorded rationale |
| **Watch for** | Clustering at the top (test too easy — trigger the [challenge review](17_capability_assessment.md)) · a component nobody ever loses points on (not discriminating) · a component nobody ever scores well on (unrealistic, or a genuine capability gap — determine which) |
| **Rule** | **Never tune weights per exercise, and never after seeing results.** That converts a rubric into a narrative |
| **Effort** | 2–3 exercise cycles |

---

## Sequencing summary

```
1. R-8  canonical implementation      -> unblocks everything (ambiguous path = no custody)
2. R-10 key custody  (+ evidence-key split)  -> makes evidence trustworthy
3. Exercise Assurance                 -> makes the SCORE trustworthy
4. R-6  containment proof             -> makes a containment CLAIM trustworthy
5. Blind-phase adoption               -> makes baseline measurement legitimate
6. R-7  Red coverage                  -> makes coverage meaningful
7. Calibration                        -> only meaningful once 1-6 hold
```

**Items 1–4 are prerequisites for a defensible first assessment.** Running the
[§18 integrated exercise](17_capability_assessment.md) before item 3 produces a score nobody
should rely on; before item 2, evidence that is attested by a single party; before item 4, a
containment property that has never been demonstrated on the platform it runs on.

> **This has an automated issuance gate, not merely a warning (`PROGRAM-READINESS-GATE-001`).** Items 1–4 are the four required gates
> in [`config/assessment_readiness.json`](config/assessment_readiness.json). Until all four hold,
> program status is **`NOT_ASSESSMENT_READY`**: exercises may run and diagnostic scores may be
> computed, but **no assurance statement may be issued** and every artifact carries
> `TRAINING_OR_ENGINEERING_USE_ONLY`. See [§22](21_readiness_gate.md).
>
> Item 5 (blind-phase adoption), 6 (Red coverage), and 7 (calibration) are **not** readiness
> gates — they improve assessment quality rather than assessment legitimacy, and can proceed in
> parallel.
