# PURPLE TEAM — Charter

**Function:** Offensive and defensive security integration
**Color code:** Red + Blue → Purple
**Owner of this document:** Purple Team Lead · **Approver:** CISO + White Exercise Director
**Review cadence:** Annual, or on material org change · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)

---

## Mission
Convert threat intelligence and observed adversary behavior into controlled, authorized tests;
measure how the organization blocks, detects, investigates, contains, recovers from, and
reports that behavior; and drive the resulting gaps to closure with evidence.

## Scope
- **In:** Adversary emulation planning and execution against authorized targets; ATT&CK
  technique mapping; collaborative (non-blind) validation with defenders; detection and control
  validation backlog ownership; retesting; exercise-derived metrics; threat-informed
  prioritization; post-incident "could we have caught this earlier?" replay of real incidents.
- **Out:** Unauthorized targets; anything outside an approved RoE; production exploitation
  without explicit White + System Owner approval; vulnerability scanning as a service (that is
  Vulnerability Management); compliance assessment (that is GRC/White).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| P1 | Maintain a ranked, threat-informed exercise pipeline tied to named organizational risks | [M] |
| P2 | Author exercise proposals and test cases; map every test action to ATT&CK (technique + sub-technique) | [M] |
| P3 | Run collaborative validation sessions where Red and Blue observe the same activity in real time | [M] |
| P4 | Record, for each test case, the outcome across six stages: **prevented / logged / alerted / investigated / contained / reported** | [M] |
| P5 | Own and groom the Detection & Control Validation Backlog | [M] |
| P6 | Retest every remediated finding and record measured improvement | [M] |
| P7 | Convert real incidents into repeatable emulation test cases within 30 days of closure | [R] |
| P8 | Publish [§8 metrics](../00-shared/07_metrics.md) monthly | [M] |
| P9 | Maintain the emulation library (test-case-as-code, version controlled) | [R] |
| P10 | Facilitate blind / "black box" phases **only** when White has designated and authorized them | [R] |

## Explicit non-responsibilities
- Purple does **not** approve its own exercises. (White does.)
- Purple does **not** accept risk. (System owners do.)
- Purple does **not** write production detection content directly into the SIEM. (Green does;
  Purple validates. Rationale: separation of build and validate — otherwise Purple grades its
  own homework.)
- Purple does **not** patch, configure, or remediate. (Yellow/Green do.)
- Purple does **not** own vulnerability scanning, phishing awareness programs, or compliance audits.
- Purple does **not** hide attack details from defenders during collaborative validation. The
  default posture is full transparency; opacity requires a White-designated blind phase with a
  documented learning objective.

## Decision authority
| Decision | Purple's authority |
|---|---|
| Which scenario to propose next | **Decide** (informed by CTI, risk register, SOC) |
| Test case content and ATT&CK mapping | **Decide** |
| Whether an exercise may proceed | **Recommend only** — White decides |
| Halting an in-flight test on technical grounds | **Decide** — Purple may always stop; only White may *resume* |
| Finding severity (initial) | **Decide** — White adjudicates disputes |
| Whether a finding is closed | **Decide**, based on retest evidence |
| Risk acceptance | **None** |
| Scope expansion mid-exercise | **None** — requires White + System Owner |

## Required independence
Moderate. Purple should not report to the same manager as the engineering team whose systems it
most frequently tests, to avoid pressure to soften findings. Purple **may** sit under the CISO.
Purple must not sit under a business unit it tests.

## Inputs and outputs
| Inputs | From |
|---|---|
| Threat intelligence, actor TTP profiles | CTI / vendor feeds / ISAC |
| Risk register, crown-jewel inventory | GRC / Risk Committee |
| Incident post-mortems | CSIRT |
| Current detection inventory and coverage state | Green / SOC |
| Architecture and threat models | Orange / Yellow |
| Approved RoE | White |

| Outputs | To |
|---|---|
| Exercise proposal, threat scenario, test cases | White (approval), Orange/Green (prep) |
| Findings, detection gaps, control gaps | Yellow (remediation), Green (detection), GRC (risk) |
| Detection & Control Validation Backlog | Green |
| Retest records | White, GRC |
| Metrics pack | CISO, exec |
| Emulation library (code) | Purple, Green (CI regression) |

## Required skills and certifications
**Skills [M]:** ATT&CK fluency including data-source and detection-coverage reasoning; adversary
emulation planning; log/telemetry literacy across EDR, identity, cloud control plane, and
network; detection engineering literacy (can read a rule, cannot necessarily ship it);
facilitation and technical writing; scripting (Python/PowerShell); cloud IAM fundamentals.

**Skills [R]:** Threat intel analysis (Diamond Model, kill chain, ATT&CK Navigator layers);
statistics sufficient to not misreport a rate; incident command familiarity.

**Certifications** — treat as *evidence of baseline*, never as a hiring gate:
[R] MITRE ATT&CK Defender (MAD) SOC Assessment / Adversary Emulation; GIAC GCTI, GCDA, GDAT;
OSCP or CRTO for the emulation-capable member; cloud-native (AZ-500 / AWS Security Specialty)
matched to your environment. **[O]** CISSP for the lead if executive credibility requires it.

## Recommended roles
| Role | Focus |
|---|---|
| Purple Team Lead | Pipeline, facilitation, metrics, exec reporting |
| Adversary Emulation Engineer | Test case authoring, safe tooling, emulation library |
| Detection Validation Analyst | Six-stage outcome scoring, backlog grooming, retest |
| Threat Intelligence Analyst *(shared)* | Actor selection, TTP prioritization |
| Exercise Scribe *(rotating)* | Timeline, decision log, evidence capture |

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **0.5 FTE.** One senior engineer, half-time, running 2–4 exercises/yr. External Red contracted per-exercise. |
| P2 | **1.0 FTE dedicated Purple Lead** + 0.25 FTE CTI + 0.25 FTE scribe (rotating). Red capability contracted or borrowed. |
| P3 | **2.0 FTE** (Lead + Emulation Engineer) minimum, with dedicated scribe support during exercise weeks. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 1.0 FTE Purple Lead |
| P2 | 3.0 FTE: Lead, Emulation Engineer, Detection Validation Analyst (+0.5 CTI) |
| P3 | 5.0–7.0 FTE: Lead, 2× Emulation, 2× Detection Validation, dedicated CTI, dedicated scribe/records |

## Reporting structure
Purple Lead → Director of Security Operations (or CISO directly at P1/P2). Dotted line to the
White Exercise Director **for exercise conduct only** — not for performance management (that
would compromise White's independence).

## Escalation path
Technical issue → Purple Lead → (safety/authorization issue) → White Exercise Director →
(unresolvable) → Executive Sponsor. **Any participant may invoke a stop directly to White,
bypassing Purple.**

## Tools and data access
| Access | Level | Label |
|---|---|---|
| SIEM / data lake | Read + saved searches. **No content deployment.** | [M] |
| EDR/XDR console | Read + telemetry query. Response actions **denied** in production. | [M] |
| Attack simulation / BAS platform | Operate, in authorized scopes only | [R] |
| ATT&CK Navigator / coverage tooling | Full | [M] |
| Case management | Full on exercise cases | [M] |
| Lab / cyber range | Admin | [M] |
| Production admin credentials | **Denied.** Purple uses purpose-built, time-bound, tagged exercise identities issued per-RoE. | [M] |
| Source code | Read | [R] |

## Artifacts owned
Exercise Proposal · Threat Scenario · ATT&CK Test Case · Finding (initial authorship) ·
Detection Gap · Control Gap · Retest Record · Detection & Control Validation Backlog ·
Emulation Library · Metrics Pack → see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- ATT&CK coverage of *prioritized* techniques rising quarter over quarter (M-1)
- Detection rate on retest > detection rate on first test, per technique (M-3, M-8)
- % of findings converted into automated regression tests ≥ 60% by month 12 (M-13)
- Median finding age (open, high severity) trending down (M-12)
- ≥ 80% of exercises produce at least one shipped detection or control change

## Failure indicators
- Exercises produce reports but the backlog never shrinks → Purple is doing theater
- Same technique fails detection across three consecutive exercises → escalate to Green
  staffing/tooling, not to "more testing"
- ATT&CK coverage climbing while MTTD is flat → coverage is being counted, not achieved
- Purple writes its own detections → independence lost, metrics are self-graded
- No exercise ever stopped for safety in 12 months → stop conditions probably are not enforced (M-15)
- Red operators refuse collaborative sessions → cultural failure; escalate to CISO
