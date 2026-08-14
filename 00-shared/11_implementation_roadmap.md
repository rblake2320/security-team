# §12 — Implementation Roadmap

← [Index](../README.md) · Prev → [§11 Compliance](10_compliance_crosswalk.md) · Next → [§13 Pilot](12_pilot_exercise.md)

**Baseline profile:** P2 (mid-size, regulated). P1 and P3 deltas are noted per phase.
**Effort figures are person-days, and are planning estimates, not commitments** — they assume
the staffing in each team's `CHARTER.md` and no unusual organizational friction.

**Sequencing principle:** governance before testing, telemetry before detection, detection before
validation, validation before automation. Every phase inversion in this order produces work that
has to be redone.

---

## Phase 0 — Prerequisites (before Day 1)

| Item | Owner | Blocking? |
|---|---|---|
| Close Open Decisions **O-1, O-2, O-4, O-5** | Executive Sponsor, CISO, GC | **Yes — hard blockers** |
| Executive sponsor named and committed to a quarterly review | CEO/CIO | **Yes** |
| Budget envelope confirmed (O-8) | CFO | Yes for hiring; no for pilot |
| Legal and Privacy contacts named with a 1-business-day SLA | GC | **Yes** |

**Do not start Day 1 with these open.** Every failed program of this type in practice starts
before the authorization question is answered, then discovers at week 6 that nobody can actually
approve a test.

---

## Days 1–30 — Governance and minimum viable capability

**Goal:** you can legally and safely authorize one test. Nothing more.

| # | Deliverable | Owner | Effort (pd) | Acceptance criteria |
|---|---|---|---|---|
| 1.1 | White Team constituted: Exercise Director named with an independent reporting line; deputy named | Exec Sponsor | 3 | Reporting line documented and confirmed by HR; Director's manager is not a participant manager; Internal Audit informed |
| 1.2 | Five charters adopted (this document set), edited to the org | CISO + team leads | 5 | Signed by each team's approver; open decisions marked, not silently filled |
| 1.3 | RoE template instantiated as an org standard | White + Legal + Privacy | 4 | Legal and Privacy have reviewed and approved the **template** once, so per-exercise review is fast |
| 1.4 | Emergency contact roster built and **live-tested** | White | 1 | Every required role reached by phone in a test call; out-of-band path verified |
| 1.5 | Stop conditions published and briefed to all participants incl. SOC | White | 2 | Every named participant confirms in writing they know how to call a stop |
| 1.6 | Deconfliction procedure agreed with SOC and written into the **IR plan** | White + SOC | 3 | The IR plan itself says "default on ambiguity is real incident"; SOC leads briefed |
| 1.7 | Asset inventory and system-owner mapping for the top 10 crown jewels | GRC | 5 | Each has a **named human** owner who has acknowledged the role |
| 1.8 | Artifact schemas stood up in existing systems (no new purchases) | Purple + GRC | 4 | Finding, exercise, and evidence records can be created and retrieved |
| 1.9 | Evidence store with immutability enabled | White + IT | 2 | Write-once verified by test; deletion restricted to custodian; access logged |
| 1.10 | Prioritized ATT&CK technique list v1 (40–80 techniques) | Purple + CTI | 4 | Every technique traceable to a risk-register entry or observed actor behavior |
| 1.11 | Telemetry baseline: what log sources exist, where, with what retention | Green | 5 | Inventory complete for the top 10 systems; **gaps named, not hidden** |
| 1.12 | Security Champions identified (1 per delivery team) with protected time | Eng leadership | 2 | Named, and time allocation confirmed by their managers |

**Staffing this phase:** White 0.5 FTE · Purple 0.5 · Green 0.3 · Yellow 0.2 · Orange 0.1 ·
GRC 0.3. **Total ≈ 40 person-days.**

**Dependencies:** O-1/O-2/O-4/O-5 closed · executive sponsor engaged · access to asset inventory.

**Phase acceptance gate:** *Can we authorize a test today?* Walk one hypothetical exercise
through stages 1–4 on paper and obtain all signatures. If any signature cannot be obtained, that
is the phase's real finding.

**Major risks**
| Risk | Mitigation |
|---|---|
| White independence resisted ("why can't the CISO own it?") | Frame as protecting the CISO — independent authorization is what makes a bad outcome a governed event rather than a career event |
| Asset inventory is incomplete or has no real owners | Start with 10 systems, not all. Unowned systems are themselves a finding for the risk register. |
| Charters adopted but not resourced | Charters without funded time allocations are documentation. Require named people and hours in the adoption approval. |

**P1 delta:** compress to ~15 person-days; Exercise Director is contracted or the GRC lead;
skip 1.8 formality and use the existing issue tracker with labels.
**P3 delta:** add CO/COR contract-authorization verification, ISSO/ISSM engagement, and
classification/marking procedures. Add ~15 person-days and expect +2–4 weeks of elapsed time.

---

## Days 31–60 — Workflows, integrations, and pilot preparation

**Goal:** the workflow is real, and the pilot is fully prepared but not yet executed.

| # | Deliverable | Owner | Effort (pd) | Acceptance criteria |
|---|---|---|---|---|
| 2.1 | Workflow stages 1–17 operational with entry/exit criteria in the tooling | Purple + White | 5 | A finding can be created, assigned, remediated, retested, and closed end to end in a **dry run with a synthetic finding** |
| 2.2 | Integration I1: findings ↔ engineering backlog, bidirectional status | Purple + Yellow | 5 | Status change in either system reflects in the other within 15 min |
| 2.3 | Integration I4: evidence capture → WORM store with hashing | White + IT | 4 | Hash recorded at capture; tamper attempt detected in test |
| 2.4 | Detection-as-code repo with CI validation (I2) | Green | 8 | Existing detections exported to Git; a change flows through review → CI → deploy |
| 2.5 | Threat models for the pilot's target systems | Orange + Yellow | 6 | Approved by system owners; instrumentation gaps handed to Green |
| 2.6 | Green defensibility gate defined | Green | 3 | Checklist exists; applied to one real release as a trial (advisory, non-blocking, this phase) |
| 2.7 | Lab / range environment usable for emulation | Green + Purple | 6 | Pilot test cases dry-run successfully in lab |
| 2.8 | Severity rubric + SLAs agreed with engineering and system owners | Purple + Yellow + GRC | 3 | Published; engineering leadership has **agreed the SLAs are achievable** (an SLA nobody agreed to is a fiction) |
| 2.9 | Pilot exercise proposal + RoE fully approved | Purple + White | 6 | All signatures present; safety assessment approved; contact roster re-tested |
| 2.10 | Metrics baseline captured (M-3, M-4, M-6, M-10, M-12 as they stand today) | Purple + Green | 4 | Baseline recorded **before** any improvement work, so improvement is provable |
| 2.11 | Tabletop of the deconfliction procedure with SOC | White + SOC | 2 | SOC correctly routes a simulated query in <5 min |

**Staffing:** White 0.5 · Purple 1.0 · Green 0.8 · Yellow 0.4 · Orange 0.4 · GRC 0.2.
**Total ≈ 52 person-days.**

**Dependencies:** Phase 1 complete · lab environment budget · engineering capacity for I1.

**Phase acceptance gate:** the pilot RoE is signed, the safety assessment is approved, the lab
dry-run passed, and the metrics baseline is recorded. **Do not execute in this phase**, even if
everything looks ready — the discipline of finishing preparation before execution is itself what
you are building.

**Major risks**
| Risk | Mitigation |
|---|---|
| Integration I1 takes longer than estimated (it usually does) | Manual sync is acceptable for the pilot; do not let integration work delay the pilot |
| Telemetry gaps discovered are larger than expected | Expected outcome, not a failure. Scope the pilot to systems where telemetry exists; the gaps become the first Green roadmap items. |
| Threat modeling reveals architecture problems bigger than the pilot | Record them, do not expand the pilot. Scope discipline in the first exercise sets the precedent for every one after. |

---

## Days 61–90 — First complete exercise and after-action cycle

**Goal:** one full cycle, stages 1–17, with evidence. **Completeness matters far more than
sophistication.**

| # | Deliverable | Owner | Effort (pd) | Acceptance criteria |
|---|---|---|---|---|
| 3.1 | Pre-exercise brief; contacts re-verified | Purple + White | 1 | All roles confirmed reachable on the day |
| 3.2 | Pilot executed ([§13](12_pilot_exercise.md)) | Purple + Red | 6 | All test cases executed or formally deferred; no scope deviation without written White approval |
| 3.3 | Collaborative validation session | Purple + Blue + Green | 3 | Six-stage outcome recorded for every test case, with evidence |
| 3.4 | Findings classified with acceptance criteria | Purple + White | 3 | Every finding has evidence, testable acceptance criteria, and a **named** owner |
| 3.5 | Remediation executed for Critical/High | Yellow + Green | 10 | Deployed with fix evidence attached |
| 3.6 | Retest completed | Purple | 2 | Retest records with verdicts; original procedures re-run verbatim |
| 3.7 | Risk acceptance for anything not remediated | System Owner + White | 1 | Signed, with expiry dates |
| 3.8 | AAR published within 10 business days | White | 4 | Independent; scored against pre-declared criteria; participants corrected facts only |
| 3.9 | Evidence preserved and mapped to controls | GRC + White | 3 | Retrievable by control ID; hashes verified; destruction scheduled |
| 3.10 | Lessons learned → backlog with owners and dates | All | 2 | Every lesson is a work item, not a sentiment |
| 3.11 | First regression tests added to CI | Yellow + Orange | 4 | ≥1 finding converted to an automated test; the pipeline runs it |
| 3.12 | Metrics pack v1 published; compared to the day-60 baseline | Purple | 3 | Includes denominators and data-quality caveats |

**Staffing:** White 0.7 · Purple 1.0 · Green 0.8 · Yellow 0.6 · Orange 0.3 · SOC 0.4.
**Total ≈ 42 person-days.**

**Phase acceptance gate — the honest test:** *Did a finding go all the way from discovery to a
verified fix to a regression test, with evidence at every step?* **One finding completing the
full loop is worth more than fifty findings sitting in a report.** If zero findings completed
the loop, the problem is remediation capacity or acceptance criteria, and running a second
exercise will not help.

**Major risks**
| Risk | Mitigation |
|---|---|
| Exercise causes an unintended impact | Safety assessment, lab-first, stop conditions, rehearsed rollback. Accept that this risk is never zero — that is why White exists. |
| Findings are not remediated inside 90 days | Scope the pilot small enough that Critical/High fixes are genuinely achievable in ~4 weeks |
| The AAR becomes a blame exercise | White writes it; it is about systems, never people; name what worked first |
| Team declares victory and stops | Phase 4 is scheduled and staffed **before** the pilot ends |

---

## Months 4–6 — Automation and expanded coverage

**Goal:** cadence, breadth, and the compounding mechanisms.

| # | Deliverable | Owner | Effort (pd) | Acceptance criteria |
|---|---|---|---|---|
| 4.1 | Exercise cadence at 1–2/month, running reliably | Purple | 30 | 6+ exercises completed with full artifact sets |
| 4.2 | Emulation library in Git; ≥50% of test cases automated | Purple | 12 | Re-runnable from CI or a controlled runner |
| 4.3 | Integration I5: regression tests in CI (M-13 ≥40%) | Purple + Yellow | 10 | Findings automatically become regression candidates |
| 4.4 | Integration I3: exercise events → SIEM, MTTD computed automatically | Purple + Green | 6 | M-4 produced without manual timestamp collection |
| 4.5 | Green defensibility gate **enforced** (blocking) for new production services | Green + Eng leadership | 5 | ≥90% of new services pass the gate before release; waivers require signed risk acceptance |
| 4.6 | Paved roads v1 for the top 3 recurring finding classes | Green + Yellow | 15 | Adoption measured; recurrence (M-9) for those classes drops |
| 4.7 | Threat models for all above-threshold systems (M-14 ≥70%) | Orange + Yellow | 20 | Approved and current |
| 4.8 | SOAR enrichment playbooks for the top 5 alert types | Green | 8 | MTTI (M-5) improves measurably |
| 4.9 | Metrics & Reporting AI agent (if pursuing §10) | Purple | 6 | Read-only; kill switch tested; accuracy measured vs. manual |
| 4.10 | Restore drills for critical systems | Green | 8 | Measured RTO/RPO vs. target for ≥3 systems |
| 4.11 | Quarterly executive metrics review established | CISO | 2 | Two reviews held; each produced at least one decision |

**Staffing:** approaching the mature model — Purple 1.5–2.0 · Green 2.0 · White 0.7 ·
Orange 0.75 · Yellow allocations. **Total ≈ 120 person-days over 3 months.**

**Phase acceptance gate:** M-13 ≥40%, M-9 measurable and not rising, M-10 ≥98%, exercise cadence
sustained without heroics, and the intake:closure ratio (M-12) ≤1.2.

**Major risks**
| Risk | Mitigation |
|---|---|
| **Findings outpace remediation capacity** (the most common month-4 failure) | Watch the intake:closure ratio weekly. If >1.0 sustained, **slow the exercise cadence** and move effort to Green/Yellow. Say this out loud to leadership — it reads as discipline, not weakness. |
| Automation before process stability | Gate 4.9 behind a stable manual process; §10.8 sequencing |
| Defensibility gate becomes a bottleneck and is routinely waived | Publish waiver counts monthly. A gate waived >20% of the time is not a gate; either resource it or lower it deliberately. |
| Purple burnout from cadence | Cadence is a ceiling, not a target. Cancel exercises when the backlog is saturated. |

---

## Months 7–12 — Maturity, metrics, continuous validation

**Goal:** the model runs as normal operations and produces compliance evidence as a byproduct.

| # | Deliverable | Owner | Effort (pd) | Acceptance criteria |
|---|---|---|---|---|
| 5.1 | Continuous validation: top-20 techniques auto-validated monthly | Purple + Green | 15 | Automated runs; failures create findings without human transcription |
| 5.2 | Full metric set (M-1..M-16) produced automatically on cadence | Purple | 10 | Two consecutive quarters, no manual assembly |
| 5.3 | Compliance evidence mapped and current (M-16 = 100% of the mappable subset) | GRC | 12 | An assessor can retrieve evidence by control ID without asking a person |
| 5.4 | Independent assessment / penetration test using this model's readiness | External | — | Findings from the independent test are **new**, not repeats of known-unremediated items |
| 5.5 | Real-incident conversion pipeline operating (workflow Variant A) | Purple + CSIRT | 8 | ≥80% of closed incidents reviewed for emulation conversion within 30 days |
| 5.6 | Additional AI agents per §10.8 sequence, if pursued | Team leads | 15 | Each with ≥30 days of measured accuracy before the next |
| 5.7 | Orange integrated at the design gate; shift-left ratio measured and rising | Orange | 10 | Orange invited pre-architecture-freeze on ≥80% of above-threshold changes |
| 5.8 | White independence audit completed | Internal Audit | 3 | Attestation issued; findings remediated |
| 5.9 | Program review and next-year roadmap | CISO + all leads | 5 | Trend evidence for M-3, M-6, M-9, M-13; resourcing ask supported by data |
| 5.10 | Full-disaster rehearsal: run one exercise cycle with **all AI agents disabled** | Purple + White | 4 | Cycle completes manually; confirms no workflow depends on an agent (§10.9) |

**Staffing:** mature model per charters — P2 ≈ 8–10 FTE-equivalents total across all five
functions, of which ~4 are dedicated. **Total ≈ 82 person-days over 6 months** beyond
steady-state operations.

**Phase acceptance gate (12-month definition of "mature"):**
- All §8 metrics produced automatically, on cadence, with named owners, for two consecutive quarters
- M-3 detection rate ≥70% on prioritized techniques
- M-9 recurrence <5%
- M-13 regression conversion ≥60%
- M-14 threat model coverage ≥90%
- M-15 safety stop rate inside the healthy 5–20% band
- Zero exercises executed without complete prior authorization
- Independent assessment findings are new, not known repeats

---

## 12.6 Cumulative effort and cost summary (P2)

| Phase | Person-days | Elapsed | Net-new headcount | Indicative incremental tooling |
|---|---|---|---|---|
| Days 1–30 | ~40 | 1 month | 0 | ~$5K (evidence storage) |
| Days 31–60 | ~52 | 1 month | 0–1 | ~$20K (lab/range, retention) |
| Days 61–90 | ~42 | 1 month | 1 | — |
| Months 4–6 | ~120 | 3 months | 1–2 | ~$60K–$150K |
| Months 7–12 | ~82 | 6 months | 0–1 | ~$40K–$100K |
| **Total year 1** | **~336 pd (~1.6 FTE-years of project effort)** | 12 months | **~2 net-new FTE** | **~$125K–$275K** |

Plus steady-state operations from month 4 onward. **Cross-check against O-8 before committing.**

> **The honest summary for a budget conversation:** roughly **2 net-new FTE and ~$150K–$275K of
> tooling in year one**, layered on top of existing security and engineering staff who
> reallocate 10–25% of their time. Programs that try to do this with zero net-new headcount
> produce documentation and no measured improvement — the coordination role in particular is
> real, sustained work that cannot be absorbed as a side duty.
