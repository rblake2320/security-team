# WHITE TEAM — Charter

**Function:** Independent governance, authorization, exercise control, safety, legal/compliance
oversight, scoring, after-action reporting
**Owner of this document:** White Exercise Director · **Approver:** Executive Sponsor + General Counsel
**Review cadence:** Annual + after any independence audit finding · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)

> **White is the load-bearing function of this entire model.** If White's independence is
> nominal, every metric in §8 becomes self-reported and every RoE becomes a formality. Read
> "Required independence" below before anything else.

---

## Mission
Provide independent authorization, safety, legal and privacy oversight, deconfliction, evidence
integrity, scoring, and after-action reporting for all authorized security testing — and hold
unconditional authority to pause or terminate any exercise.

## Scope
- **In:** Objectives, scope, systems, accounts, tools, techniques, windows, data handling, RoE
  approval; authorization chain verification; stop conditions; deconfliction; conflict
  resolution; evidence custody; scoring; independent AAR; risk-acceptance routing; exercise
  records retention.
- **Out:** Executing tests; writing detections; remediating; choosing which scenario is most
  interesting (that is Purple's proposal, White's approval).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| W1 | Verify and record authorization from: executive sponsor, each system owner, legal, privacy, safety (where applicable), and operations | [M] |
| W2 | Approve or deny each RoE; require modification where unsafe | [M] |
| W3 | Maintain the exercise calendar and deconflict with change freezes, releases, audits, and business-critical events | [M] |
| W4 | Maintain the emergency contact roster (24×7) and test it before each exercise | [M] |
| W5 | Hold the "answer key" — the authoritative record of exercise activity — enabling real-vs-simulated adjudication | [M] |
| W6 | Define and enforce stop conditions; execute stop/resume decisions | [M] |
| W7 | Preserve evidence integrity: hashing, chain of custody, access control, retention | [M] |
| W8 | Score the exercise against pre-declared criteria published *before* execution | [M] |
| W9 | Produce an independent AAR not editable by participants | [M] |
| W10 | Route residual risk to the accountable system owner for formal acceptance | [M] |
| W11 | Resolve disputes between Red/Blue/Engineering on finding validity or severity | [M] |
| W12 | Designate and authorize blind-testing phases, and control the information boundary during them | [R] |
| W13 | Approve third-party and supply-chain test involvement, including provider notification | [M] |
| W14 | Certify destruction of test data and revocation of exercise identities at exercise close | [M] |

## Explicit non-responsibilities
- White does **not** design test cases or choose techniques (Purple does; White approves).
- White does **not** operate tools, run commands, or touch target systems.
- White does **not** remediate or engineer.
- White does **not** advocate for either Red or Blue. White has no score to defend.
- White does **not** accept risk on behalf of a system owner.
- White does **not** report to the CISO **if** the CISO owns exercise participants. (See O-4.)

## Decision authority
| Decision | White's authority |
|---|---|
| Exercise approval / denial | **Decide — final** |
| RoE terms | **Decide — final** |
| Stop, pause, terminate | **Decide — unconditional, immediate, non-appealable during execution** |
| Resume after a stop | **Decide — sole authority** |
| Scope expansion | **Decide** (with System Owner concurrence) |
| Real-incident declaration during an exercise | **Decide** — White adjudicates; CSIRT executes |
| Finding severity disputes | **Decide** |
| Final score and AAR content | **Decide — not editable by participants** |
| Risk acceptance | **Route and record. Does not accept.** |
| Evidence release outside the org | **Decide** with Legal |

## Required independence — [M] and load-bearing
1. The **Exercise Director** must not report, directly or indirectly, to any manager of Red,
   Blue, Purple, Orange, Green, or the system owner under test.
2. Recommended reporting lines, in preference order: **(a)** Chief Risk Officer, **(b)** General
   Counsel, **(c)** CIO/COO where the CISO owns all participants, **(d)** Internal Audit
   (advisory capacity only — note that operational involvement can impair audit independence
   under IIA standards; confirm with your audit leadership).
3. Compensation and performance ratings must not be influenced by exercise outcomes.
4. At P1, where a single person may wear multiple hats, the **only** acceptable dual-hat is
   White + GRC. White + any participant role is prohibited. If that cannot be satisfied
   internally, contract the Exercise Director role — it is ~4–8 hours per exercise.
5. Internal Audit reviews White's independence annually [M].

## Inputs and outputs
| Inputs | From |
|---|---|
| Exercise proposal + threat scenario | Purple |
| Safety assessment | Purple + Orange + Green |
| System criticality, availability requirements, change calendar | System Owners, Ops |
| Legal/privacy/contractual constraints | Legal, Privacy, Vendor Management |
| Insurance and regulatory notification obligations | Risk |
| Live exercise timeline and evidence | Purple, Red, Blue |

| Outputs | To |
|---|---|
| Approved (or denied) RoE with conditions | All participants |
| Authorization record | GRC, audit file |
| Deconfliction answer key | CSIRT, SOC lead (sealed until needed) |
| Stop/resume decisions + rationale | All |
| Independent AAR + score | Executive, GRC, all teams |
| Evidence manifest + custody record | Evidence repository |
| Residual risk package | System Owner, Risk Committee |
| Destruction certificate | GRC, Privacy |

## Required skills and certifications
**Skills [M]:** Governance and authorization; risk management; incident command; legal/privacy
literacy sufficient to spot a problem and escalate; evidence handling and chain of custody;
exercise control (borrow from emergency-management / HSEEP practice); technical literacy
sufficient to understand a test case's blast radius; neutral facilitation under conflict.

**Certifications [R]:** CISA, CRISC, CISM, CIPP/US or CIPM for the privacy-facing member,
HSEEP exercise design training (genuinely useful and rarely used in cyber), CISSP.
**[O]:** legal qualification for the counsel member (they already have it).

## Recommended roles
| Role | Notes |
|---|---|
| **Exercise Director (White Cell Lead)** | The independence-bearing role. Named, backed up, empowered. |
| Legal Counsel (designated) | [M] Approver, not full-time |
| Privacy Officer / DPO (designated) | [M] Approver for any personal-data exposure |
| Safety Officer | [M] where OT/ICS/medical/safety-of-life systems exist; otherwise [O] |
| Evidence Custodian | Owns manifest, hashing, retention |
| Scoring Analyst | Applies pre-declared criteria; drafts AAR |
| System Owner Liaison | Rotating per-exercise |
| Executive Sponsor | Approves the program, not each exercise |

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **0.25 FTE.** One named Exercise Director (may be GRC lead or contracted), with counsel and privacy on-call as approvers. |
| P2 | **0.5 FTE Exercise Director** + designated Legal (2 h/exercise) + designated Privacy (1 h/exercise) + Evidence Custodian (0.25 FTE, may be GRC). |
| P3 | **Dedicated White Cell: 2.0–3.0 FTE** — Exercise Director, Evidence Custodian/Records, Scoring Analyst — plus designated Legal, Privacy, Safety, and a government-side authorizing official where applicable. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 0.5 FTE Exercise Director |
| P2 | 1.0 Exercise Director + 0.5 Evidence Custodian + 0.5 Scoring Analyst |
| P3 | 4.0–5.0 FTE White Cell with 24×7 on-call rotation during exercise windows |

## Reporting structure
Exercise Director → CRO / GC / CIO (per Open Decision O-4). **Never** → CISO where the CISO owns
participants. Executive Sponsor holds program-level accountability and receives the AAR directly.

## Escalation path
Any participant → White Exercise Director (direct, always available during exercise windows) →
Executive Sponsor → CEO / Agency Head. Safety issues bypass everything: **any human may call
"STOP" and all activity halts pending White adjudication.** No retaliation, ever — a false stop
costs an hour; a missed stop can cost an outage or a regulatory event.

## Tools and data access
| Access | Level | Label |
|---|---|---|
| Exercise record system / case management | Full, with participant-write-restricted AAR area | [M] |
| Evidence repository | **Custodian-level, WORM/immutable, separate from participant access** | [M] |
| Emergency comms (out-of-band: phone tree + non-corporate messaging) | Full | [M] |
| SIEM | Read-only, for adjudication | [R] |
| Target systems | **None.** White does not touch targets. | [M] |
| Signing capability for authorization records | Full (e-signature) | [M] |

## Artifacts owned
Rules of Engagement (approved) · Authorization Record · Safety Assessment (approval) ·
Deconfliction Answer Key · Stop/Resume Decision Log · Evidence Manifest · Chain of Custody ·
Scoring Rubric · After-Action Report · Risk Acceptance (routing + record) · Destruction
Certificate · Exercise Calendar → see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- 100% of exercises have complete, pre-execution authorization records
- 0 exercises executed outside approved scope or window
- Median RoE approval turnaround ≤ 5 business days
- 100% of exercise activity attributable within 60 seconds when CSIRT queries the answer key
- AAR published within 10 business days, 100% of exercises
- 100% of test data destroyed and exercise identities revoked within 5 business days of close

## Failure indicators
- White approves every proposal without modification → not actually reviewing
- White never invokes a stop and never denies → rubber stamp; independence is nominal
- Participants learn exercise details from White informally → information boundary broken
- AAR edited after publication without a versioned change record → evidence integrity failure
- Legal/privacy sign-off collected after execution → **critical control failure; halt the program**
- Exercise Director's manager also manages a participant → independence void; escalate to Audit
