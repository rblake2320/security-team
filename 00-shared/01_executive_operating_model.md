# §1 — Executive Operating Model

← [Index](../README.md) · Next → [§3 Org Structure & RACI](02_org_structure_and_raci.md)

---

## 1.1 The one-paragraph version for executives

The organization already spends money on building systems (engineering), attacking them
(Red/pentest), and defending them (SOC/CSIRT). Today those three spend cycles rarely close.
This model adds **one governance function** (White) and **three integration functions**
(Orange, Green, Purple) that force closure: every authorized test produces a finding, every
finding produces engineering work with a testable exit condition, every fix produces a
detection or a control change, and every change is retested and evidenced. The output is not
"a report." The output is a measurable delta in prevention rate, detection rate, and time to
contain — plus the assessment evidence that regulators and auditors already require you to
produce.

## 1.2 The five functions as a value chain

```
   THREAT / RISK INPUT                                        MEASURABLE OUTPUT
          |                                                          ^
          v                                                          |
   +--------------+     +--------------+     +--------------+     +--------------+
   |   ORANGE     | --> |   PURPLE     | --> |   GREEN      | --> |   YELLOW     |
   | attack       |     | validate     |     | make it      |     | build the    |
   | thinking     |     | under        |     | observable & |     | fix into the |
   | applied      |     | control      |     | defensible   |     | product      |
   | pre-build    |     |              |     |              |     |              |
   +--------------+     +--------------+     +--------------+     +--------------+
          ^                     ^                    ^                    |
          |                     |                    |                    |
          +---------------------+--------------------+--------------------+
                                        |
                                +---------------+
                                |     BLUE      |  operates the defense every day.
                                |  (continuous) |  Consumes what Green builds.
                                +-------+-------+  Feeds Purple what actually happens.
                                        |
                                +---------------+
                                |     WHITE     |  authorization · safety · scoring ·
                                |  (independent)|  evidence integrity · stop authority
                                +---------------+
```

**Blue is the only team whose day is driven by an adversary rather than by a plan**, and the only
one that runs continuously rather than in exercise cycles. It is not "Green at runtime": Green's
output is *content and platform*; Blue's output is *decisions under time pressure with incomplete
information*. The six-stage outcome chain already separates their failures — stages 1–3
(prevented / logged / alerted) grade Green, stages 4–6 (investigated / contained / reported) grade
Blue. That is the sharpest argument for keeping them distinct.
See [§15 Blue integration review](14_blue_team_integration_review.md).

Read it as a **left-shift chain**: Orange finds the attack path on a whiteboard (cheapest),
Green makes sure the path is visible and blocked (cheap), Yellow ships the change (moderate),
Purple proves the whole chain works against real adversary behavior (expensive), White proves
it was all authorized and honestly scored (mandatory). Anything Purple finds that Orange should
have caught is a signal to invest further left.

## 1.3 Where existing organizational entities connect

| Existing entity | Connects to | Nature of connection | What changes for them |
|---|---|---|---|
| **Red Team / offensive contractor** | Purple (execution arm), Orange (knowledge donor) | Purple tasks and deconflicts them; Orange is where their expertise is spent *before* code ships | Stop writing reports nobody actions. Findings enter the Finding schema and are tracked to retest. |
| **Blue Team / SOC** | Purple (validation partner), Green (engineering donor) | Purple runs tests against their detections; Green productizes what they learn | Named analyst participates in collaborative validation. Detection gaps become backlog items with owners, not tribal knowledge. |
| **CSIRT / IR** | White (deconfliction), Purple (tabletop + live validation) | CSIRT is the primary "is this real?" decision point; White holds the answer key | Gains a rehearsed, evidenced IR capability and a real MTTC number. |
| **GRC / Compliance** | White (evidence consumer), all (control mapping) | Consumes artifacts as assessment evidence; maps per §11 | Stops manufacturing evidence at audit time. Evidence is a byproduct of operations. |
| **Legal** | White (mandatory approver) | Authorization, third-party/SaaS test clauses, insurance notification, privilege over findings | Named counsel on the White distribution. One-business-day SLA for RoE review. |
| **Privacy / DPO** | White (mandatory approver for any test touching personal data) | Data minimization, retention, destruction terms in every RoE | Approves the data-handling section of every RoE. Veto power on PII/PHI exposure. |
| **Engineering / Platform / App teams** | **They ARE the Yellow Team** | Not a stakeholder — a participant | Security findings arrive as prioritized backlog with acceptance criteria, not as PDFs. |
| **System Owners / Business Owners** | White (authorization), Yellow (remediation funding), risk acceptance | Only the system owner can authorize testing of their system and accept residual risk | Explicit accountability. Risk acceptance is signed, time-bound, and expires. |
| **Executive leadership / Board** | White (scoring + AAR), metrics (§8) | Receives independent after-action reporting, not self-graded results | Gets trend lines that change budget decisions, not activity counts. |
| **Internal Audit** | White (independence check) | Audits the *White Team's* independence annually | New assurance obligation — small, ~8 hrs/yr. |
| **HR / Workforce development** | Purple, Orange (training pipeline) | Exercise findings feed role-based training requirements | Training content derived from real organizational failure modes. |
| **Third parties / MSSP / cloud providers** | White (notification + authorization), Purple (in-scope boundaries) | Contractual test permission, provider notification, shared-responsibility boundaries | Test clauses added at contract renewal. |

## 1.4 Dedicated team vs. virtual team — the decision rule

This is the most commonly botched decision. The rule:

> **A function requires dedicated headcount when its work is continuous, when its independence
> would be compromised by a reporting line, or when its volume exceeds ~0.5 FTE sustained.
> Otherwise it is a virtual, cross-functional team drawn from existing roles with named
> primaries and backups.**

| Function | Dedicated or virtual | Trigger to go dedicated | Never |
|---|---|---|---|
| **Purple** | **Virtual at P1. Dedicated coordinator (1 FTE) at P2. Dedicated 2–4 FTE at P3.** | >8 exercises/yr, OR detection backlog >40 open items, OR exercise scheduling consumes >0.5 FTE | Never staff Purple by promoting the loudest Red operator without coordination and writing skill — the job is 60% facilitation and documentation. |
| **White** | **Virtual cell at P1/P2 with a *dedicated, named, independent* Exercise Director role. Dedicated White Cell at P3, and mandatory for any exercise touching production, safety, or regulated data.** | Any exercise on production, any regulated exercise, any exercise involving a third party, or >12 exercises/yr | **Never** let White report into the same chain as the participants. This is the single independence requirement that cannot be traded away. |
| **Yellow** | **Never a separate team. Yellow *is* engineering.** | — | Never create a "Yellow Team" org box. Creating one re-externalizes security from engineering, which is exactly the failure this model exists to fix. Yellow = existing dev/platform/cloud/data/AI teams operating under secure-by-design requirements, with **Security Champions** as named liaisons. |
| **Green** | **Virtual guild at P1/P2 (SOC engineer + platform engineer, ~0.5–1.5 FTE combined). Dedicated detection-engineering team at P3 or >2,000 endpoints.** | Detection content count >250 rules, OR telemetry pipeline requires full-time ownership, OR SOAR automation in production | Never let Green become "the SOC's ticket queue." Green ships platform patterns and paved roads, not one-off tickets. |
| **Orange** | **Virtual at all profiles until proven otherwise. 0.25–1.0 FTE of offensive expertise loaned into design reviews and threat modeling.** | >30 threat models/yr, OR a formal secure-SDLC gate requiring offensive sign-off | Never let Orange run exploitation in production. Orange operates in design docs, lab, and pre-prod. That constraint is what makes an offensive person safe to embed with builders. |
| **Red** | **Contracted at P1. 1.0 FTE at P2 + contracted independent assessment. 2.0–4.0 FTE at P3 + an external assessor for the formal annual assessment.** | >6 engagements/yr, OR a framework requiring assessor independence on a recurring cycle | Never let Red report to Purple (Purple must be able to critique Red's coverage) or to an engineering leader whose systems it assesses. **Never let Red hold the authorization signing key** — that single convenience destroys the independence the function exists for. |
| **Blue** | **Always dedicated — this is the one function that cannot be virtual.** P1 may outsource volume to an MSSP, but a named internal duty lead is mandatory. | Already dedicated by definition; scale with alert volume and coverage hours | Never stand the SOC down during an exercise window — operating normally *is* the measurement, and a SOC that pauses for exercises teaches an adversary exactly when to operate. Never publish per-analyst detection or disposition statistics; it destroys the data quality it measures. |

**Minimum viable total for P2: ~6.5 FTE-equivalents, of which ~1.5 are net-new headcount.**
The rest are existing people with named, funded time allocations. See each team's `CHARTER.md`
staffing tables and the [roadmap](11_implementation_roadmap.md).

## 1.5 Operating rhythms

| Rhythm | Frequency | Owner | Participants | Output |
|---|---|---|---|---|
| Threat-informed prioritization | Monthly | Purple Lead | CTI, SOC, Orange, GRC | Ranked candidate scenario list |
| Exercise Review Board (approve/deny proposals) | Monthly | White Exercise Director | White, Purple, System Owners, Legal (async ok) | Approved RoEs, denials with reasons |
| Purple exercise execution | 1–2/month (P2) | Purple Lead | Red, Blue, Green, Orange, White observer | Findings, detection gaps, evidence |
| Detection backlog grooming | Bi-weekly | Green Lead | Green, SOC, Purple | Prioritized detection work |
| Secure-design review (Orange gate) | Per-change, continuous | Orange Lead | Yellow team of record | Threat model, abuse cases, regression tests |
| Remediation standup | Weekly | Yellow eng manager | Yellow, Purple (findings owner) | Ticket status, blocked items |
| Retest queue | Bi-weekly | Purple | Purple, Green, Yellow | Retest records, closures |
| After-action report publication | Within 10 business days of exercise end | White | All | Independent AAR, score, lessons |
| Metrics review | Monthly (ops), Quarterly (exec) | Purple Lead / CISO | Leadership | §8 metric pack, decisions |
| Independence audit of White Team | Annual | Internal Audit | White, Audit | Independence attestation |

## 1.6 Charter conflicts and how they are resolved

| Conflict | Resolution rule |
|---|---|
| Purple wants to test; System Owner says the window is bad | White decides; System Owner's availability concern generally wins, but repeated refusal escalates to Executive Sponsor as a risk-acceptance decision |
| Orange says the design is unacceptable; Yellow says ship it | Green defensibility gate applies; if it passes the gate, System Owner signs a time-bound risk acceptance; Orange's objection is recorded verbatim in the record |
| Green says the detection works; Purple says it didn't fire | Purple's empirical result wins. Evidence beats assertion. |
| Red wants blind testing; Purple charter says be transparent | White decides and designates the blind phase in the RoE with a stated learning objective. Blind by default is not permitted. |
| GRC needs evidence Orange produced; framework requires independence | Orange evidence is *supporting*, not *independent assessment*. Procure an independent assessor. Do not relabel. |
| CISO wants to overrule a White stop decision | Not permitted during execution. Post-exercise, the Executive Sponsor may review White's judgment. If the CISO can overrule White in-flight, White does not exist. |
