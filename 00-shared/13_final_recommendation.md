# §14 — Final Recommendation

← [Index](../README.md) · Prev → [§13 Pilot](12_pilot_exercise.md)

---

## 14.1 Minimum viable operating model

**The smallest thing that is genuinely a security capability rather than documentation.**

| Function | MVP form | FTE (P2) |
|---|---|---|
| **White** | One named, independent Exercise Director + designated Legal and Privacy approvers + an Evidence Custodian | **0.75** |
| **Purple** | One dedicated coordinator who owns the pipeline, facilitation, findings, and metrics | **1.0** |
| **Green** | One detection engineer with SIEM/EDR authoring rights + telemetry ownership | **1.5** |
| **Yellow** | Security Champions (1 per delivery team, 4 h/month) + one AppSec engineer | **1.25** |
| **Orange** | Part-time offensive expertise, borrowed or contracted, spent entirely on threat modeling | **0.5** |
| **Red capability** | Contracted, 2× per year, tasked by Purple | contract |
| **Total** | | **~5.0 FTE-equivalents, ~2 net-new** |

**Non-negotiable even in the MVP:**
1. Written authorization before any test action
2. An independent stop authority
3. Deconfliction that works in under 5 minutes
4. Evidence integrity (hashed, immutable, retained)
5. Findings that become engineering work with testable acceptance criteria

Cut anything else before cutting these five. A program without them is not a smaller version of
this model — it is a different, unsafe thing wearing the same name.

---

## 14.2 Recommended mature model (P2, 12–18 months)

| Function | Mature form | FTE |
|---|---|---|
| **White** | Exercise Director + Evidence Custodian + Scoring Analyst; designated Legal/Privacy/Safety; annual independence audit | 2.0 |
| **Purple** | Lead + Adversary Emulation Engineer + Detection Validation Analyst (+0.5 CTI) | 3.5 |
| **Green** | Lead + 2 Detection Engineers + Telemetry Engineer (+ shared identity/cloud/resilience) | 4.0 |
| **Yellow** | 2 AppSec + 1 DevSecOps + Champions across all teams with a real curriculum | 3.0 + champions |
| **Orange** | 2 offensive design reviewers + quarterly Red rotation | 2.0 |
| **Red** | Internal or contracted, independent of the builders, for compliance-grade assessment | 1.0 or contract |
| **Total** | | **~15 FTE-equivalents**, ~6–7 dedicated |

Plus: continuous validation of the top 20 techniques, automated metrics, enforced defensibility
gate, real-incident conversion pipeline, and compliance evidence produced as a byproduct.

---

## 14.3 The five most important hiring or assignment decisions

Ranked by consequence of getting them wrong.

| # | Decision | Why it is decisive | What good looks like | Failure signature |
|---|---|---|---|---|
| **1** | **The White Exercise Director** | This is the only role whose failure invalidates everything else. Weak independence means every metric becomes self-reported. | Senior enough to say no to the CISO. Reports outside the participant chain. Comfortable being unpopular for a day. Often best filled from risk, audit, or legal — **not** from security operations. | Chosen for technical depth rather than authority; reports to the CISO; has never denied a proposal |
| **2** | **The Purple Lead** | The job is ~60% facilitation, documentation, and follow-through; ~40% technical. Most organizations hire the reverse and get exercises that produce reports nobody actions. | Runs a room containing Red and Blue without it becoming adversarial. Writes clearly. Chases remediation for months without being resented. ATT&CK-fluent. | The best offensive operator was promoted into it; findings pile up; the backlog only grows |
| **3** | **The first Green detection engineer** | Everything downstream is conditional on telemetry and detection existing at all. Without this role, Purple measures a vacuum. | Detection-as-code discipline; cost-aware pipeline thinking; writes behavioral not signature logic; tunes ruthlessly and retires noisy content | Rule count rises, detection rate does not; alert fatigue grows; telemetry silently dies |
| **4** | **Security Champions in engineering** | The only mechanism that scales security into engineering without headcount. Cheapest high-leverage investment in the entire model. | 1 per delivery team, 4 h/month **protected and defended by their manager**, real curriculum, visible status | Named but never given time; the program is nominal within a quarter |
| **5** | **Orange's communication ability** | An offensive engineer whom developers avoid produces zero shift-left value regardless of technical skill. | Can run a threat model that engineers leave feeling smarter. Teaches rather than corrects. | Threat models written *for* teams instead of *with* them; teams stop inviting Orange; Purple keeps finding design issues Orange already flagged |

**Assignment rule [M]:** the White Exercise Director and the Purple Lead **must be different
people with different reporting lines.** If one person holds both, there is no independent
authority, and every subsequent control in this document is decorative.

---

## 14.4 The five highest organizational risks

| # | Risk | Likelihood | Impact | Leading indicator | Mitigation |
|---|---|---|---|---|---|
| **1** | **Findings outpace remediation capacity.** The program generates work faster than the org can absorb, credibility collapses, and people stop attending. | **High** | High | Intake:closure ratio (M-12) >1.0 for two consecutive months | Watch it weekly from day one. When it breaches, **slow exercise cadence and move effort to Green/Yellow.** Report this to leadership as discipline — it is. |
| **2** | **White independence is nominal.** Reporting line exists on paper; in practice White never denies, never stops, and defers to the CISO. | **High** | **Critical** | Zero denials, zero stops, zero modifications over 12 months (M-15 at 0%) | Annual Internal Audit independence review; publish denial and stop counts; make the reporting line real at constitution time, because it is nearly impossible to fix later |
| **3** | **Theater** — exercises run, reports written, nothing changes. The most common failure of purple team programs. | **High** | High | M-13 regression conversion near zero; M-9 recurrence rising; backlog only grows | Gate G5 (acceptance criteria) and G6 (retest) enforced absolutely. **Measure the loop closing, not the testing happening.** |
| **4** | **An exercise causes a production incident**, and the program is suspended or cancelled. | Medium | **Critical** | Rollbacks untested; safety assessments perfunctory; scope creep tolerated | Lab-first always; timed and rehearsed rollbacks; stop conditions people actually use; **defend the "unnecessary" stop publicly the first time it happens** — that moment sets the culture |
| **5** | **Key-person dependency.** One person holds the pipeline, the relationships, and the institutional knowledge, and leaves. | Medium | High | No named backups; backups never exercised; artifacts live in someone's head | Named primary + backup for every [M] role, exercised within 12 months; artifacts in systems of record, not in people |

**Honorable mentions:** telemetry cost forcing source cuts that silently kill detections;
compliance capture (the program optimizing for audit evidence rather than security outcomes);
AI-agent deference; and executive attention decaying after the first impressive AAR.

---

## 14.5 The first three exercises to run

| # | Exercise | When | Why this order | Success criterion |
|---|---|---|---|---|
| **1** | **Identity → Cloud** ([§13](12_pilot_exercise.md)) | Days 61–90 | Safest full-workflow test; centralized telemetry; universally applicable; findings are almost always actionable | ≥80/100 on the process score, **and** at least one finding completes discovery → fix → retest → regression test |
| **2** | **Endpoint → Ransomware precursors (detection only, no encryption)** | Month 4–5 | Highest-impact scenario for most organizations; validates EDR, backup, **and restore** together; exercises CSIRT properly | MTTC measured for the first time; ≥1 restore drill completed with real RTO/RPO numbers; **no destructive action anywhere in the exercise** |
| **3** | **Real-incident replay** (convert your most recent significant incident into an emulation) | Month 5–6 | Highest-signal scenario you will ever have; authorization is easy because the owner lived through it; directly answers "would we catch it now?" | Demonstrated improvement vs. the original incident timeline, or an honest finding that nothing has improved — **both are valuable and both must be reported** |

**Deliberately not in the first three:** AI system exercises (frameworks and tooling are immature
— conflict F-8; run this once the process is proven), supply chain (high coordination cost),
physical (separate authorization regime), and anything blind (blind testing before collaborative
testing teaches the wrong lesson and wastes the most expensive learning opportunity you have).

---

## 14.6 Decisions requiring executive approval

| # | Decision | Approver | Why it must be executive | Timing |
|---|---|---|---|---|
| 1 | Constitute the White Team with a reporting line **outside** the CISO org | CEO/COO + GC | Reorganizes accountability; only an executive can grant authority over the CISO's teams | Before Day 1 |
| 2 | Grant unconditional stop authority to a named individual | CEO/COO | Unusual authority; must be visibly backed or it will be tested and overridden once | Before Day 1 |
| 3 | Net-new headcount (~2 FTE) + tooling (~$150K–$275K yr 1) | CFO + CISO | Budget | Day 20 (O-8) |
| 4 | Whether production is ever in scope, and under what conditions | CEO/COO + GC | Accepts residual risk of exercise-caused impact on behalf of the business | Day 15 (O-5) |
| 5 | Risk-acceptance thresholds requiring executive sign-off (recommend: all Critical, and any acceptance >90 days) | Risk Committee | Defines where risk decisions stop being local | Day 25 |
| 6 | Engineering time commitment to remediation SLAs | CTO/VP Eng | An SLA engineering has not agreed to is a fiction that will fail publicly | Day 30 |
| 7 | Whether to pursue the [§10](09_ai_and_automation_governance.md) AI architecture at all | CISO + CTO | Optional; introduces its own risk class | Month 4 |
| 8 | Independent assessor procurement (separate from remediation vendors) | CFO + CISO | Framework independence requirements (conflict F-1) | Month 6 |

---

## 14.7 Assumptions that must be validated before implementation

| # | Assumption | How to validate | If false |
|---|---|---|---|
| A-1 | An executive will genuinely back an independent stop authority | Ask directly, in writing, before Day 1: *"if White stops an exercise and the CISO disagrees, who wins?"* | **Do not start.** Run tabletop exercises only until the answer is White. A stop authority that can be overruled is worse than none — it creates the appearance of control. |
| A-2 | Engineering has capacity to remediate at the proposed SLAs | Sample the last 20 security findings: what was the actual median time to fix? | Renegotiate SLAs to reality and say so openly, rather than setting SLAs that will be missed and quietly ignored |
| A-3 | Telemetry exists for the systems you intend to test | Deliverable 1.11 — inventory it, do not assume it | Sequence changes: telemetry work becomes Phase 1, and the pilot scope narrows to where data exists |
| A-4 | System owners are identifiable and will accept accountability | Deliverable 1.7 — get 10 named acknowledgements | Unowned systems become a governance finding; escalate to the Risk Committee before testing anything |
| A-5 | Legal and Privacy can review an RoE in one business day | Ask them; pre-approve the template once (deliverable 1.3) | Exercise cadence caps at whatever their real turnaround allows; plan accordingly rather than pretending |
| A-6 | A SOC/monitoring capability exists to test against | Confirm coverage hours and triage capability (O-7) | Purple exercises are premature. Build detection and triage first — you cannot measure a detection rate against nothing. |
| A-7 | The lab logs to the same pipeline as production | Verify technically before the pilot | Lab results do not transfer to production conclusions; fix the pipeline or scope the pilot to pre-prod |
| A-8 | Contracts and insurance permit simulated attack activity | Legal review of SaaS agreements and the cyber policy (O-12, O-14) | Scope excludes those systems until contract renewal; add test-permission clauses at renewal |
| A-9 | Frameworks in scope are correctly identified and versioned | Confirm with the assessor/QSA/CO (O-3, O-15, O-16) | The [crosswalk](10_compliance_crosswalk.md) is rebuilt against the correct versions before any evidence claim is made |
| A-10 | Budget figures in [§12](11_implementation_roadmap.md) are within an order of magnitude of reality | Price 2–3 tools; cost the FTEs at loaded rates | Rescale to P1 and accept lower cadence — **a small program run properly beats a large one run badly**, every time |

---

## 14.8 The one-page summary for a decision meeting

> **What we are proposing:** five coordinated security functions — Purple (validate), White
> (authorize and score, independently), Yellow (build securely), Green (make it defensible),
> Orange (find attack paths before we build them) — that convert authorized testing and real
> incidents into measured improvements and audit-ready evidence.
>
> **What it costs (P2):** about 2 net-new FTE and $150K–$275K of tooling in year one, plus
> 10–25% time reallocation from existing security and engineering staff. Roughly 336 person-days
> of project effort across 12 months.
>
> **What we get:** a validated detection rate against the techniques that actually threaten us; a
> measured time to detect and contain; findings that close instead of accumulating; regression
> tests that stop problems from coming back; and assessment evidence produced as a byproduct of
> operations instead of assembled in a panic before an audit.
>
> **What it is not:** compliance, certification, or an authorization to operate. It produces
> evidence those processes consume. Nothing here replaces an independent assessor.
>
> **What we need from you:** an independent White Team reporting line outside the CISO org, a
> named individual with unconditional stop authority whom you will visibly back the first time
> they use it, budget, and a decision on whether production is ever in scope.
>
> **What we will show you in 90 days:** one complete cycle — a real finding discovered under
> written authorization, fixed with verified evidence, retested, and converted into an automated
> regression test — plus a baseline for every metric we will report from then on.
>
> **The one number to watch after that:** the intake:closure ratio. If we generate findings
> faster than we close them, we will slow down testing and tell you, rather than accumulating a
> backlog and calling it progress.
