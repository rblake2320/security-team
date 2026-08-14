# §4 — End-to-End Workflow

← [Index](../README.md) · Prev → [§3 Org & RACI](02_org_structure_and_raci.md) · Next → [§5 Rules of Engagement](04_rules_of_engagement_template.md)

---

## 4.0 The lifecycle at a glance

```
 [1] Risk/threat selection        GRC+Purple      ─┐
 [2] Exercise proposal            Purple           │  PLAN
 [3] System-owner authorization   System Owner     │  (2-4 weeks)
 [4] RoE approval                 WHITE           ─┘
 [5] Threat modeling              Orange+Yellow   ─┐
 [6] Test-case development        Purple           │  PREPARE
 [7] Safety validation            WHITE           ─┘  (1-2 weeks)
 [8] Execution                    Purple+Red      ─┐  EXECUTE
 [9] Detection/control validation Purple+Blue     ─┘  (1-5 days)
[10] Finding classification       Purple/WHITE    ─┐
[11] Engineering remediation      Yellow+Green     │  IMPROVE
[12] Retesting                    Purple           │  (SLA-driven)
[13] Risk acceptance or closure   System Owner    ─┘
[14] After-action report          WHITE           ─┐
[15] Compliance evidence          GRC+WHITE        │  CLOSE
[16] Lessons learned              All              │  (<=10 business days)
[17] Backlog & roadmap update     Purple+Green    ─┘
                                                    │
                          └──────── feeds [1] ──────┘
```

**Hard gate rule [M]:** stages 8–9 may not begin until stages 3, 4, and 7 are complete with
signed records. There is no "provisional start." There is no "we'll get the signature Monday."

---

## 4.1 Stage detail

Each stage: **Owner (A)** · **Doers (R)** · **Entry criteria** (all must be true to start) ·
**Exit criteria** (all must be true to finish) · **Typical duration** · **Artifact produced** ·
**Failure mode**.

---

### Stage 1 — Risk or threat selection
| | |
|---|---|
| **Owner (A)** | GRC / Risk |
| **Doers (R)** | Purple (analysis), CTI (actor selection) |
| **Consulted** | SOC, Orange, Green, System Owners |
| **Entry** | Current risk register exists; crown-jewel/asset inventory exists with data classification; CTI feed or ISAC membership active |
| **Exit** | A ranked candidate list of ≥3 scenarios, each traceable to (a) a named risk register entry **and** (b) an observed adversary behavior or a real incident; each with a named would-be system owner |
| **Duration** | Monthly, 2–4 hours |
| **Artifact** | Ranked candidate scenario list (appended to the risk register) |
| **Failure mode** | Scenarios chosen because a tool supports them, or because they're interesting. **Test:** if you cannot name the risk-register ID, the scenario is not selected — it is a hobby. |

---

### Stage 2 — Exercise proposal
| | |
|---|---|
| **Owner (A)** | Purple Lead |
| **Doers (R)** | Purple, with Orange and CTI input |
| **Entry** | Scenario selected in stage 1; target systems identified; a system owner has been identified and pre-notified informally |
| **Exit** | Completed Exercise Proposal artifact (see [artifact index](06_artifact_index_and_standards.md)) containing: objective, hypothesis, in-scope systems, out-of-scope exclusions, proposed ATT&CK techniques, proposed environment (lab / pre-prod / prod), proposed window, required participants, estimated effort, expected evidence, **and the pre-declared scoring criteria** |
| **Duration** | 3–8 hours |
| **Artifact** | Exercise Proposal |
| **Failure mode** | Scoring criteria written after execution. **[M] Scoring criteria must be in the proposal and approved before execution** — otherwise the exercise is graded to whatever happened. |

---

### Stage 3 — System-owner authorization
| | |
|---|---|
| **Owner (A)** | System Owner (each in-scope system) |
| **Doers (R)** | White (obtains and records), Purple (briefs) |
| **Entry** | Exercise Proposal complete; system owner identified in the asset inventory (not guessed) |
| **Exit** | Signed authorization from **every** in-scope system's owner, recording: systems authorized, permitted impact level, availability constraints, blackout windows, named on-call contact + backup, rollback expectations, and explicit acknowledgement of the worst credible outcome |
| **Duration** | 3–10 business days (the usual bottleneck) |
| **Artifact** | Authorization Record (per system) |
| **Failure mode** | "The CISO approved it" used as a substitute. The CISO does not own the system. **[M] No system owner signature = that system is out of scope**, full stop. Proceed with the remaining scope or cancel. |

---

### Stage 4 — Rules-of-engagement approval
| | |
|---|---|
| **Owner (A)** | White Exercise Director |
| **Doers (R)** | White (drafts final), Purple (technical content), Legal + Privacy (review) |
| **Entry** | Stage 3 complete for all in-scope systems; safety assessment drafted (stage 7 may run concurrently); third-party notification obligations identified |
| **Exit** | RoE signed by: Exercise Director, Purple Lead, each System Owner, Legal, Privacy, Safety (where applicable), and the Executive Sponsor for production-scope exercises. All conditions and modifications recorded. Deconfliction procedure tested. Emergency contact roster tested (**live call, not a list review**). |
| **Duration** | 5–10 business days |
| **Artifact** | Approved Rules of Engagement (see [§5](04_rules_of_engagement_template.md)) |
| **Failure mode** | RoE approved with unresolved conditions ("pending legal"). **[M] Conditional approval is denial** until the condition clears. |

---

### Stage 5 — Threat modeling
| | |
|---|---|
| **Owner (A)** | Orange Lead |
| **Doers (R)** | Orange (facilitates), Yellow (system experts, own the content) |
| **Consulted** | Green (what is instrumented), Purple (what will be tested) |
| **Entry** | Current architecture documentation exists (or is produced during the session — that is an acceptable and common outcome); data flows and trust boundaries identifiable |
| **Exit** | Threat Model artifact approved by the system owner, containing: components, data flows, trust boundaries, classified data at each store, STRIDE (or equivalent) findings, attack paths ranked by feasibility × impact, existing controls per path, **instrumentation gaps handed to Green**, and abuse cases handed to Yellow as requirements |
| **Duration** | 2–4 hours per system for the session; 1–2 days for write-up |
| **Artifact** | Threat Model, Abuse Case set, Attack-Path Analysis |
| **Failure mode** | Orange writes the model alone and presents it. **The model must be produced *with* the engineers** — the knowledge transfer is the point; the document is a byproduct. |

---

### Stage 6 — Test-case development
| | |
|---|---|
| **Owner (A)** | Purple Lead |
| **Doers (R)** | Purple, Red (technique implementation), Orange (abuse-case-derived cases) |
| **Consulted** | Green (what telemetry should appear), SOC (what alerts should fire) |
| **Entry** | Threat model complete; ATT&CK techniques selected; lab environment available |
| **Exit** | Each test case documented with: ATT&CK technique + sub-technique ID, exact executable procedure, required identity/privilege, **expected telemetry (source + field-level)**, **expected detection (rule ID or "none — gap")**, blast radius, cleanup/rollback steps, and safety classification. **Every test case dry-run in lab at least once** [M]. |
| **Duration** | 1–3 days |
| **Artifact** | ATT&CK Test Case (one per technique) |
| **Failure mode** | Expected telemetry left blank. If you have not predicted what *should* appear, you cannot distinguish "detection failed" from "we weren't looking at the right data" — the two have completely different fixes. |

---

### Stage 7 — Safety validation
| | |
|---|---|
| **Owner (A)** | White Exercise Director |
| **Doers (R)** | Purple (drafts), Green + Orange (technical review), Ops (availability review) |
| **Entry** | Test cases complete and lab dry-run; production dependencies mapped |
| **Exit** | Safety Assessment approved, containing per test case: worst credible outcome, blast radius, probability of unintended impact, rollback procedure and its verified time-to-execute, data exposure risk, third-party impact, and a **go / go-with-conditions / no-go** decision. Stop conditions defined and distributed. Backups verified current for any system where the worst case includes data change. |
| **Duration** | 1–3 days |
| **Artifact** | Safety Assessment |
| **Failure mode** | Rollback procedures documented but never timed. "We can restore" is not a rollback plan; "we restored a copy of this database in 42 minutes on 2026-08-04" is. |

---

### Stage 8 — Execution
| | |
|---|---|
| **Owner (A)** | Purple Lead |
| **Doers (R)** | Red (or Purple emulation engineer) |
| **Observing** | White (control), Blue/SOC (monitoring), Green, Orange, Scribe |
| **Entry** | Stages 3, 4, 7 complete and signed. Exercise identities issued, tagged, and time-bound. Deconfliction channel live and tested. Emergency contacts confirmed reachable **on the day**. White present or immediately reachable. Backups verified. Change freeze checked. |
| **Exit** | All planned test cases executed, deferred with reason, or stopped. Timeline recorded with UTC timestamps. Evidence captured per the evidence plan. Exercise identities revoked. Artifacts and test data removed per RoE. Cleanup verified by a party other than the operator [M]. |
| **Duration** | Hours to 5 days |
| **Artifact** | Execution Timeline, raw evidence, Decision Log |
| **Failure mode** | Scope creep — "while we were in there we also tried X." **[M] Any action not in the approved test-case set requires White approval before execution, in writing, in the exercise channel.** No exceptions, including for trivially safe actions; the precedent is what matters. |

---

### Stage 9 — Detection and control validation
| | |
|---|---|
| **Owner (A)** | Purple Lead |
| **Doers (R)** | Purple + Blue/SOC together (collaborative session), Green |
| **Entry** | Execution complete; SIEM/EDR data ingested and searchable (allow for ingestion lag — do not score at T+0) |
| **Exit** | Every test case scored across the **six-stage outcome chain**, each with supporting evidence: |

| Stage | Question | Possible values |
|---|---|---|
| 1. **Prevented** | Was the action blocked outright? | Blocked / Partially blocked / Not blocked / N/A |
| 2. **Logged** | Did telemetry capture it? | Full / Partial (name the missing field) / None |
| 3. **Alerted** | Did a detection fire? | Alerted (rule ID) / Fired but suppressed / No alert |
| 4. **Investigated** | Did a human triage it correctly? | Correct / Misclassified / Not triaged (timestamp) |
| 5. **Contained** | Was the action stopped or scoped? | Contained (timestamp) / Partial / No |
| 6. **Reported** | Did it reach the required party in the required time? | Yes / Late / No |

| | |
|---|---|
| **Duration** | 4–8 hours collaborative session + 1–2 days write-up |
| **Artifact** | Validation results feeding Findings, Detection Gaps, Control Gaps |
| **Failure mode** | Scoring only "did the alert fire?". A technique that alerts but is never triaged is not detected in any operationally meaningful sense — that is what stage 4 exists to expose. |

> **Collaborative-transparency rule [M]:** in this session Red discloses exactly what was done,
> when, from where, and with which identity. Blue discloses exactly what was seen. Purple does
> not withhold details to protect a score. If White designated a blind phase, the blind period
> ends before this session — it never extends into validation.

---

### Stage 10 — Finding classification
| | |
|---|---|
| **Owner (A)** | White (adjudicates); **R** = Purple (proposes) |
| **Entry** | Validation complete with evidence |
| **Exit** | Every finding recorded with: type (vulnerability / detection gap / control gap / process gap / telemetry gap), severity with documented rationale, affected systems, ATT&CK mapping, evidence references, **proposed acceptance criteria**, remediation owner (named person, not a team), and target date derived from the severity SLA. Disputes resolved and the resolution recorded. |
| **Duration** | 1–2 days |
| **Artifact** | Finding · Detection Gap · Control Gap |
| **Severity SLA (default — adjust in O-3)** | Critical: 7 days · High: 30 days · Medium: 90 days · Low: 180 days or next planned change |
| **Failure mode** | Severity assigned by feel. Use a defined rubric (exploitability × impact × exposure × compensating controls) and record the inputs, so severity changes are auditable. |

---

### Stage 11 — Engineering remediation
| | |
|---|---|
| **Owner (A)** | System Owner (accountable for it happening) |
| **Doers (R)** | Yellow (code/config/architecture), Green (detection/control/telemetry) |
| **Entry** | Finding accepted with acceptance criteria and a named owner; work item created in the normal engineering backlog (**not** a separate "security tracker" — [M]; parallel trackers are where security work goes to die) |
| **Exit** | Change deployed; acceptance criteria met; fix evidence attached (commit/PR, test result, config diff, deploy record, screenshot/query proving new state); **for Green items, the new detection or control is tested to fire in a non-production environment before deployment** |
| **Duration** | Per severity SLA |
| **Artifact** | Engineering Remediation Ticket + Fix Evidence Package |
| **Failure mode** | Findings tracked in a spreadsheet outside the engineering backlog. If it is not in the team's normal queue with normal prioritization, it competes with nothing and loses to everything. |

---

### Stage 12 — Retesting
| | |
|---|---|
| **Owner (A)** | Purple Lead |
| **Doers (R)** | Purple (re-executes the original test case verbatim), Green (verifies signal) |
| **Entry** | Remediation deployed to the environment where the finding was found; fix evidence submitted |
| **Exit** | Retest Record produced showing: original outcome, retest outcome across all six stages, delta, evidence, and a verdict of **Closed / Partially remediated / Not remediated / Regressed**. On success, the test case is added to the automated regression suite [M] where technically feasible. |
| **Duration** | Hours; run in bi-weekly retest batches |
| **Artifact** | Retest Record |
| **Failure mode** | Retest performed with a modified test case, which quietly proves something else. **[M] Retest the original procedure verbatim.** If the original procedure is no longer possible because the system changed, that is itself the finding — record it that way rather than adapting the test. |

---

### Stage 13 — Risk acceptance or closure
| | |
|---|---|
| **Owner (A)** | System Owner (signs), escalating to Executive above threshold |
| **Doers (R)** | White (routes and records), GRC (registers) |
| **Entry** | Either a passing retest (→ closure) or a decision not to remediate within SLA (→ acceptance) |
| **Exit — closure path** | Retest passed; finding closed; evidence archived; regression test in CI |
| **Exit — acceptance path** | Risk Acceptance signed containing: what is not being fixed, why, compensating controls in place, residual risk statement, **expiry date (max 12 months; max 90 days for Critical)**, review trigger, and the signature of the accountable owner. Registered in the risk register with the finding ID. |
| **Duration** | 1–5 business days |
| **Artifact** | Risk Acceptance |
| **Failure mode** | Perpetual acceptance. **[M] Every acceptance expires.** On expiry it reopens at the original severity and returns to the backlog — it does not auto-renew. Report the count and age of active acceptances to the Risk Committee quarterly; a growing pile is a leading indicator of an incident. |

---

### Stage 14 — After-action reporting
| | |
|---|---|
| **Owner (A)** | White Exercise Director |
| **Doers (R)** | Scoring Analyst (drafts), all teams (factual review only) |
| **Entry** | Stages 9 and 10 complete; participant factual review window closed (3 business days) |
| **Exit** | AAR published within **10 business days** of exercise end, containing: objective and hypothesis, what actually happened (timeline), score against the **pre-declared** criteria, the six-stage outcome table, findings summary by severity, what worked (name it explicitly — a report that only lists failures trains people to avoid exercises), what did not, stop events and why, deviations from the RoE, evidence manifest reference, and recommendations with owners. Participants may correct facts; **participants may not change conclusions or scores** [M]. |
| **Duration** | 3–5 days |
| **Artifact** | After-Action Report |
| **Failure mode** | AAR that reads as a Red Team highlight reel. The audience is decision-makers; the useful content is the six-stage table and the delta from the last exercise of this type. |

---

### Stage 15 — Compliance evidence preservation
| | |
|---|---|
| **Owner (A)** | GRC |
| **Doers (R)** | White Evidence Custodian, Purple, Green |
| **Entry** | AAR published; evidence manifest complete |
| **Exit** | Evidence stored in the system of record with: hash per item, capture timestamp, capture method, custodian, access log, classification marking, retention schedule, destruction date. Mapped to the applicable control IDs (see [crosswalk](10_compliance_crosswalk.md)). Test data destroyed per RoE with a signed destruction certificate. Exercise identities confirmed revoked. |
| **Duration** | 2–3 days |
| **Artifact** | Evidence Manifest + Chain of Custody + Destruction Certificate |
| **Failure mode** | Evidence in a personal drive, a chat thread, or a screenshot folder. If an assessor cannot retrieve it 18 months later without asking a specific person, it is not preserved. |

---

### Stage 16 — Lessons learned
| | |
|---|---|
| **Owner (A)** | System Owner (for their system's lessons); Purple (for program lessons) |
| **Doers (R)** | All participants |
| **Entry** | AAR published |
| **Exit** | Lessons-Learned Records created, each classified as **Sustain / Improve / Systemic**. Systemic lessons (affecting more than one system) are escalated to Green as paved-road work or to Orange as a design-review pattern. Training needs routed to L&D. Process changes routed to the owning charter with a document version bump. |
| **Duration** | 1 session, 60–90 minutes, within 10 business days |
| **Artifact** | Lessons-Learned Record |
| **Failure mode** | Lessons captured as a document and never converted into a work item or a document change. **[M] Every lesson has an owner and a due date, or it is not a lesson — it is a feeling.** |

---

### Stage 17 — Backlog and roadmap update
| | |
|---|---|
| **Owner (A)** | Purple Lead (validation backlog) + Green Lead (detection backlog) |
| **Doers (R)** | Purple, Green, Yellow |
| **Entry** | Findings, gaps, and lessons recorded |
| **Exit** | Detection & Control Validation Backlog updated and reprioritized; ATT&CK coverage layer regenerated; next-quarter exercise roadmap updated; recurring techniques flagged for structural (platform) fixes rather than repeated point fixes; metrics refreshed |
| **Duration** | 2–4 hours |
| **Artifact** | Updated backlog, ATT&CK Navigator layer, exercise roadmap |
| **Failure mode** | The backlog grows monotonically. If intake consistently exceeds closure, the constraint is remediation capacity — the correct response is to *slow exercise cadence and invest in Green/Yellow*, not to run more tests. Track and report the intake:closure ratio. |

---

## 4.2 Two workflow variants

### Variant A — Real-incident conversion [R], strongly recommended
Real incidents are the highest-signal scenario source you will ever have.

```
Incident closed by CSIRT
   -> Purple reviews post-mortem within 30 days
   -> "Could we have detected this earlier?" analysis
   -> Enter workflow at stage 2 with the incident as the scenario
   -> Skip stage 1 (risk selection is self-evident)
   -> Faster authorization: the system owner just lived through the incident
```

### Variant B — Emergency validation (active threat) [M] for any org receiving CTI
When credible intelligence indicates a specific technique is being used against your sector:

```
Threat bulletin received
   -> Purple + Green assess coverage from existing detection catalog + telemetry inventory (2-4 h)
   -> If coverage is unclear, request EMERGENCY RoE from White (target: 24 h)
   -> Lab-only validation first, ALWAYS
   -> Production validation only with abbreviated but COMPLETE authorization
      -- abbreviation applies to timelines, NEVER to signatures --
   -> Findings go straight to Green as priority detection work
```
**[M] "Emergency" compresses the calendar, never the authorization chain.** An emergency RoE has
the same signatures as a normal one; they are just obtained in hours instead of days. Pre-agree
this path with Legal and System Owners *before* you need it — that is what makes 24 hours
achievable.

---

## 4.3 Entry/exit criteria summary — the six hard gates

| Gate | Between stages | Enforced by | Cannot be waived by |
|---|---|---|---|
| **G1 — Authorization gate** | 3 → 4 | White | Anyone. Missing system-owner signature = out of scope. |
| **G2 — RoE gate** | 4 → 8 | White | Anyone. Conditional approval = denial. |
| **G3 — Safety gate** | 7 → 8 | White | Anyone. No-go means no-go. |
| **G4 — Evidence gate** | 9 → 10 | Purple | A finding without evidence is an opinion; it does not enter the backlog. |
| **G5 — Acceptance-criteria gate** | 10 → 11 | Purple + System Owner | A finding without testable acceptance criteria cannot be closed, so it cannot be started. |
| **G6 — Retest gate** | 12 → 13 | Purple | Closure requires a passing retest **or** a signed, expiring risk acceptance. There is no third option. |
