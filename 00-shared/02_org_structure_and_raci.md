# §3 — Organizational Structure, Separation of Duties, and RACI

← [Index](../README.md) · Prev → [§1 Operating Model](01_executive_operating_model.md) · Next → [§4 Workflow](03_end_to_end_workflow.md)

---

## 3.1 Text organization chart (Profile P2 default)

```
                          BOARD / AUDIT COMMITTEE
                                    |
        +---------------------------+---------------------------+
        |                           |                           |
       CEO                    GENERAL COUNSEL            CHIEF RISK OFFICER
        |                           |                           |
   +----+--------+                  |                    == WHITE TEAM ==
   |             |                  |                 Exercise Director (independent)
  CTO          CISO                 |                    |  Evidence Custodian
   |             |            Legal Counsel  <-----------+  Scoring Analyst
   |             |            (designated approver)      |  Privacy Officer (designated)
   |             |                                       |  Safety Officer [where applicable]
   |             |                                       |  Executive Sponsor (program)
   |             |
   |             +-- Director, Security Operations
   |             |        |-- == BLUE TEAM ==  Blue Lead / SOC Manager
   |             |        |        |-- Duty leads + monitoring analysts (triage)
   |             |        |        |-- Incident responders  |-- Threat hunters
   |             |        |        |-- Cloud & identity defender  |-- Forensics lead
   |             |        |        |-- Recovery lead (INCIDENT-TIME only -- C-3)
   |             |        |        +-- runs SENTINEL BLUE (blue-team/, runnable)
   |             |        |-- CSIRT (incident response)
   |             |        |-- Threat Intelligence
   |             |        +-- == PURPLE TEAM ==  Purple Lead   [PEER to Blue, not above it]
   |             |                 |-- Adversary Emulation Engineer
   |             |                 +-- Detection Validation Analyst
   |             |
   |             +-- Director, Security Engineering
   |             |        +-- == GREEN TEAM ==  Green Lead
   |             |                 |-- Detection Engineer(s)
   |             |                 |-- Telemetry / Pipeline Engineer
   |             |                 |-- Identity Security Engineer
   |             |                 |-- Cloud Security Engineer
   |             |                 +-- Resilience Engineer (backup/restore/DR)
   |             |
   |             +-- == RED TEAM ==  Red Team Lead   [independent of the builders]
   |             |        |-- Senior operators (emulation execution)
   |             |        |-- Assessment engineer (framework-facing independent testing)
   |             |        |-- Check developer (fixed safe-check registry)
   |             |        +-- runs AEGIS RED TEAM (red-team/, runnable)
   |             |        NOTE: the Aegis SIGNING KEY is held by the approval authority
   |             |              (White), NOT by Red. Red can execute; Red cannot authorize.
   |             |        (tasked by Purple, loaned to Orange on rotation)
   |             |
   |             +-- == ORANGE TEAM ==  Orange Lead      [embedded with Engineering]
   |             |        |-- Offensive Design Reviewer(s)
   |             |        +-- AI Red-Team Specialist [where AI systems exist]
   |             |
   |             +-- GRC / Compliance
   |                      (consumes evidence; supports White; does not authorize)
   |
   +-- VP Engineering  ==================== YELLOW TEAM (all of it) ====================
            |-- Application Engineering teams ... each with a SECURITY CHAMPION
            |-- Platform / DevSecOps Engineering
            |-- Cloud Engineering
            |-- Data / Database Engineering
            |-- AI / ML Engineering
            |-- Architecture
            +-- AppSec Engineer(s)  [centrally employed, embedded with teams]

   SYSTEM OWNERS / BUSINESS OWNERS  -- sit in the business, not in IT.
        Authorize testing of their system.  Accept residual risk.  Fund remediation.
```

**Key structural facts encoded above:**

| Fact | Why |
|---|---|
| White reports to CRO/GC, **not** the CISO | The CISO owns Purple, Green, Orange, SOC, and Red. White cannot be independent inside that chain. |
| Orange sits in the CISO org but is *embedded* with Engineering | Preserves offensive tradecraft and a security escalation path while getting proximity to builders. |
| Yellow has no security reporting line at all | Yellow is engineering. Security influence flows through requirements, paved roads, champions, and gates — not through a reporting line. |
| Purple and Green are in **different** directorates | Purple validates what Green builds. Same manager = self-grading. |
| System Owners are outside IT | Risk acceptance must be a business decision, not a technical one. |

### P1 (small) collapse
```
CEO -> CISO (or Head of IT)
        |-- Security Engineer  ... wears Green (0.5) + Purple (0.5)  [see SoD-1 caveat]
        |-- Contracted Red / pentest (2x per year)
        +-- Contracted or GRC-held EXERCISE DIRECTOR (White)  --> reports to CEO/COO/GC
VP Eng -> engineers + 2-3 Security Champions;  one designated AppSec point of contact
Orange = contracted offensive expertise, 1 day/month, threat modeling only
```
**P1 mandatory caveat:** if one person holds both Purple and Green, they may not validate their
own detection content. Either a second engineer validates, or the validation is contracted.
Record which. See SoD-1.

### P3 (government / CUI / IL4+) expansion
```
Authorizing Official (AO) ------------- White Cell ------------- Independent Assessor (3PAO/CCA)
        |                                   |                          (external, not in this org)
   System Owner / ISSO / ISSM         Exercise Director
   (ISSO participates as Yellow            Records Manager
    system owner + evidence source)        Scoring Analyst
                                           Safety Officer
                                           Government Contracting Officer Rep (CO/COR)
                                              -- verifies contract authorizes the testing --
```
Add: **CO/COR verification that the contract vehicle authorizes security testing** — [M] at P3.
Contractor staff performing testing without contractual authorization is a contracts problem
before it is a security problem.

---

## 3.2 Recommended reporting lines

| Role | Solid line | Dotted line | Must NOT report to |
|---|---|---|---|
| White Exercise Director | CRO / GC / CIO | Executive Sponsor, Audit Committee | CISO (where CISO owns participants); any system owner under test |
| Evidence Custodian | White Exercise Director | GRC (records retention) | Any participant team |
| Purple Lead | Director, Security Operations | White (exercise conduct only) | Engineering leadership of systems under test |
| Green Lead | Director, Security Engineering | Head of Platform Engineering | Purple Lead |
| Orange Lead | CISO | Head of Engineering | Any single delivery team whose designs it reviews |
| AppSec Engineer | VP Engineering | CISO (craft/community) | — |
| Security Champion | Their engineering manager | AppSec Engineer | — |
| Red Team / contractor | CISO (or contract manager) | Purple (tasking), Orange (rotation) | Purple Lead as line manager (Purple must be able to critique Red's coverage) |
| SOC Manager | Director, Security Operations | Purple (validation participation) | — |

---

## 3.3 Separation-of-duty requirements

| ID | Rule | Label | Compensating control if violated |
|---|---|---|---|
| **SoD-1** | The person who **authors** a detection may not be the sole person who **attests it works** | [M] | Second-engineer validation, recorded; or contract the validation |
| **SoD-1a** | Blue's sampling of closed alerts checks **triage quality**; Purple's validation checks **detection efficacy**. Neither substitutes for the other, and both are required | [M] | None — they measure different failures (conflict C-2) |
| **SoD-2** | The person who **authorizes** an exercise may not **execute** it | [M] | None. This one has no compensating control — it is the definition of authorization. **Aegis enforces it cryptographically**: the encrypted signing key stays with the approval authority, so Red can execute but cannot produce a valid receipt or seal its own ledger. Adopt this pattern wherever tooling allows (conflict RC-4). |
| **SoD-3** | The person who **writes a fix** may not be the sole person who **verifies the fix closed the finding** | [M] | Peer verification by another engineer + Purple retest sampling ≥ 25% |
| **SoD-4** | The person who **scores** an exercise may not be a **participant** in it | [M] | External scoring analyst, or Exercise Director scores personally |
| **SoD-5** | The **evidence custodian** may not be a participant, and evidence storage must be write-once from the participants' perspective | [M] | Immutable/WORM storage with custodian-only deletion, plus access logging |
| **SoD-6** | **Risk acceptance** may only be signed by the accountable system/business owner — never by security, never by the engineer who would otherwise have to fix it | [M] | None |
| **SoD-7** | Orange may not both **discover** a production-exploitable issue and **exploit** it | [M] | Immediate CSIRT handoff on discovery |
| **SoD-8** | Purple may not **deploy** production detection content | [R] | Where P1 forces it, a Green/SOC peer reviews and deploys; record the reviewer |
| **SoD-9** | The **exercise identities** used for testing must be distinct from any operator's normal account and must be issued, tracked, and revoked by an identity owner outside the exercise team | [M] | None — this is what makes deconfliction and forensic attribution possible |
| **SoD-10** | Whoever **grants** the exercise's elevated access is not the person who **uses** it | [R] | Approval workflow with logged justification |
| **SoD-11** | Blue's operational audit chain must be **externally anchored** by a party that cannot write to it: the Sentinel Blue head hash is exported to White's WORM evidence manifest at every exercise close and monthly | [M] | None. Blue's own README states its chain detects mutation and interior deletion but **not** whole-database rollback — the external anchor is what closes that (conflict C-9) |

---

## 3.4 Primary and backup role assignments

Every [M] role requires a **named primary and a named backup**, and the backup must have
exercised the role at least once in the preceding 12 months. Empty cells are the org's to fill —
that is deliberate (see Open Decision O-9).

| Role | Primary | Backup | Backup last exercised | Coverage requirement |
|---|---|---|---|---|
| White Exercise Director | ______ | ______ | ______ | Available within 15 min during any exercise window |
| Stop authority (delegated) | Exercise Director | Named deputy | ______ | 24×7 during exercise; **no gap permitted** |
| Evidence Custodian | ______ | ______ | ______ | Business hours + on-call at exercise close |
| Legal approver | ______ | ______ | ______ | 1 business day SLA |
| Privacy approver | ______ | ______ | ______ | 1 business day SLA |
| Purple Lead | ______ | ______ | ______ | Business hours |
| Exercise Scribe | Rotating | Rotating | ______ | Full exercise duration |
| Green on-call (detection emergency) | ______ | ______ | ______ | Per SOC on-call schedule |
| Orange Lead | ______ | ______ | ______ | Business hours |
| System Owner (per system) | ______ | ______ | ______ | Reachable during their system's test window |
| CSIRT commander | ______ | ______ | ______ | 24×7 |

**Rule [M]:** if the primary and the backup are both unavailable for a required role, the
exercise does not start, or it stops. This is not negotiable and is a standing stop condition.

---

## 3.5 Avoiding conflicts of interest

| Conflict | How it shows up | Control |
|---|---|---|
| **Self-grading** | The team that built the control also measures it | SoD-1, SoD-3, SoD-4; Purple validates Green; White scores everyone |
| **Score protection** | Blue softens a finding because it reflects on the SOC's metrics | Findings are about *systems*, not teams. Never publish per-analyst detection stats. Blue is scored on improvement velocity, not on initial detection rate. |
| **Red heroics** | Red optimizes for impressive compromise rather than for organizational learning | Purple sets objectives; Red's success metric is techniques *validated*, not systems owned |
| **Budget capture** | Purple recommends the tool its own vendor relationship favors | Procurement decisions require Green + Yellow + GRC concurrence; declare vendor relationships annually |
| **Consulting capture** | An external assessor recommends its own remediation services | Contractual separation of assessment and remediation vendors, [R] at P1/P2, [M] at P3 |
| **Manager pressure** | A director asks for a finding to be downgraded before an executive review | All severity changes are logged with author, timestamp, and rationale, and are reviewable by White; audit severity-change history quarterly |
| **Exercise Director capture** | White becomes socially embedded with the participants it oversees | Rotate the Scoring Analyst; annual independence attestation to Internal Audit; White does not attend participant social/team events during an active exercise |
| **System-owner reluctance** | The owner refuses testing to avoid discovering problems | Refusal is a recorded risk-acceptance decision routed to the Risk Committee, not a private "no" |
| **AI-agent capture** | Agent recommendations are accepted without review because they are fast and confident | Every agent output carries a required human approver; see [AI governance](09_ai_and_automation_governance.md) |

---

## 3.6 RACI matrix

**R** = Responsible (does the work) · **A** = Accountable (single owner, signs off) ·
**C** = Consulted (input required before) · **I** = Informed (told after)

Exactly one **A** per row. Where an entity is absent from a row, it has no role.

| Activity | Purple | White | Yellow | Green | Orange | SOC/Blue | Red | System Owner | GRC | Legal/Privacy | Exec |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Risk/threat selection** | R | C | C | C | C | C | C | C | **A** | I | I |
| **Exercise proposal** | **R/A** | C | I | C | C | C | C | C | I | I | I |
| **Authorization (RoE approval)** | C | **R/A** | I | I | I | I | I | **C (must concur)** | C | **C (must concur)** | I |
| **System-owner authorization** | I | R | I | I | I | I | I | **A** | I | I | I |
| **Safety assessment** | R | **A** | C | R | R | C | C | C | I | C | I |
| **Threat modeling** | C | I | **R** | C | **R/A** | I | I | C | I | I | — |
| **Test-case development** | **R/A** | C | I | C | R | C | R | I | I | I | — |
| **Test execution** | **R/A** | C (observes) | I | I | C | I | R | I | I | I | I |
| **Real-time monitoring during exercise** | R | C | I | C | I | **R/A** | I | I | — | — | — |
| **Deconfliction (test vs. real)** | R | **A** | I | C | I | R | R | I | I | I | I |
| **Stop / pause / terminate** | R (may call) | **A (decides)** | R (may call) | R (may call) | R (may call) | R (may call) | R (may call) | R (may call) | I | I | I |
| **Detection development** | C | I | I | **R/A** | C | C | I | I | I | — | — |
| **Detection validation** | **R/A** | C | I | C | I | C | R | I | I | — | — |
| **Finding classification / severity** | **R** | **A** (adjudicates disputes) | C | C | C | C | C | C | C | I | I |
| **Engineering remediation** | C | I | **R** | R | C | I | I | **A** | I | I | I |
| **Fix acceptance criteria** | **R** | C | C | R | C | I | I | **A** | I | — | — |
| **Retesting** | **R/A** | C | C | R | C | C | R | I | I | — | — |
| **Risk acceptance** | C | R (routes/records) | C | C | C | I | I | **A (signs)** | R | C | I (>threshold: **A**) |
| **Evidence collection & integrity** | R | **R/A** | R | R | R | R | R | I | C | I | I |
| **Scoring** | C | **R/A** | I | I | I | I | I | I | C | I | I |
| **After-action report** | C | **R/A** | C | C | C | C | C | C | C | C | I |
| **Lessons learned → backlog** | **R** | C | R | R | R | R | I | **A** | I | — | I |
| **Compliance evidence preservation** | C | R | C | C | C | C | I | I | **R/A** | C | I |
| **Metrics production & reporting** | **R/A** | C | C | R | C | C | I | I | C | — | I |
| **Program-level go/no-go** | C | C | C | C | C | C | C | C | C | C | **A** |

### RACI notes that matter
- **Authorization has two mandatory concurrences** (System Owner and Legal/Privacy) even though
  White is Accountable. White cannot approve over a system owner's objection.
- **Stop authority is Responsible to everyone.** Any human can call stop. Only White decides
  whether to resume. This asymmetry is intentional.
- **Risk acceptance is Accountable to the System Owner**, escalating to Executive above a
  defined threshold (recommend: any Critical finding, or any acceptance exceeding 90 days).
- **Remediation is Accountable to the System Owner, not to engineering.** Engineers do the work;
  the owner owns whether it gets funded and prioritized.
- **Finding severity: Purple is Responsible, White is Accountable.** Purple proposes; if anyone
  disputes, White decides. This stops severity negotiation from happening in hallways.
