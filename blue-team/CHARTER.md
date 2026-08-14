# BLUE TEAM — Charter

**Function:** Defensive operations — monitoring, detection triage, investigation, containment, recovery
**Implementation:** **Sentinel Blue** (this folder is runnable code, not only design — see [README.md](README.md))
**Owner of this document:** Blue Team Lead / SOC Manager · **Approver:** Director of Security Operations
**Review cadence:** Annual · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)
· [Integration review](../00-shared/14_blue_team_integration_review.md)

> **Read this alongside, not instead of, the existing Sentinel Blue docs.**
> [`docs/OPERATING_MODEL.md`](docs/OPERATING_MODEL.md) defines Blue's internal roles, shifts, and
> quality gates. **This charter defines Blue's boundaries against the other five teams** — which
> that document could not, because it was written before they existed. Where the two differ, the
> nine reconciliations in [§15.5](../00-shared/14_blue_team_integration_review.md) govern.

---

## Mission
Know the environment, maintain visibility, detect material adversary behavior, investigate with
evidence, contain proportionately, recover safely, and continuously improve — operating the
defense every day against a real adversary rather than a plan.

## Scope
- **In:** Alert queue operation and triage; investigation and scoping; incident command and
  response; evidence preservation and forensics; threat hunting; containment recommendation and
  execution under approval; incident-time recovery; exposure triage; sensor-health and
  audit-integrity watch; deconfliction of exercise vs. real activity.
- **Out:** Authoring and deploying production detection content (Green); authorizing exercises
  (White); building or remediating systems (Yellow); offensive testing (Purple/Orange/Red);
  scheduled restore drills (Green); accepting risk (System Owner).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| B1 | Operate the alert queue within acknowledgement and triage targets, by severity | [M] |
| B2 | Investigate with evidence: establish confirmed / believed / estimated / unknown | [M] |
| B3 | Preserve evidence before destructive action, with acquisition method recorded | [M] |
| B4 | Incident command for declared incidents; scribe, evidence owner, and comms channel assigned | [M] |
| B5 | Recommend containment — least-destructive action that stops ongoing harm — with approval, expected impact, success signal, and rollback | [M] |
| B6 | Execute containment **only** under documented approval; **two approvers for high-risk actions** | [M] |
| B7 | Incident-time recovery under IR command; validate service and data integrity; obtain business-owner acceptance | [M] |
| B8 | Hypothesis-led threat hunting across identity, endpoint, cloud, network | [R] |
| B9 | Feed Green: false positives, tuning requests, false-negative discoveries, telemetry gaps observed from the consumer side | [M] |
| B10 | Feed Purple: real incidents as emulation candidates within 30 days of closure | [M] |
| B11 | Answer deconfliction queries during exercises — **5-minute SLA**, and treat ambiguity as real | [M] |
| B12 | Watch sensor health and audit integrity continuously; escalate silent telemetry immediately | [M] |
| B13 | Export the Sentinel Blue audit-chain head hash to White's evidence manifest at each exercise close and month end (closes the rollback gap Blue's own README names) | [M] |
| B14 | Never close an incident without scope, cause or declared unknown, containment evidence, recovery validation, lessons, and detection/prevention follow-up | [M] |

## Explicit non-responsibilities
- Blue does **not** author or deploy production detection content. (Green does; Blue reports how
  it behaves in production.) — conflict **C-1**
- Blue does **not** own the telemetry pipeline. Blue owns *noticing it is broken*. — **C-4**
- Blue does **not** perform scheduled restore drills. (Green does; Blue owns incident-time
  recovery.) — **C-3**
- Blue does **not** remediate vulnerabilities. Blue triages exposure and validates that a fix
  landed in the running environment. — **C-5**
- Blue does **not** authorize, score, or stop exercises. (White does. Blue *may* call a stop, as
  may anyone.)
- Blue does **not** perform offensive testing, and does not run emulation tooling.
- Blue does **not** accept risk.
- Blue does **not** perform autonomous counterattack, containment without approval, or blocking
  actions from the platform. **Sentinel Blue proposes; humans approve.**

## Decision authority
| Decision | Blue's authority |
|---|---|
| Alert disposition and severity at triage | **Decide** |
| Declare an incident | **Decide** |
| Incident command decisions during a live incident | **Decide** (incident commander) |
| Containment action, low-risk and reversible | **Decide** with record |
| Containment action, high-risk or destructive | **Recommend** — two approvers + rollback required (**C-8**) |
| Whether observed activity is a real incident during an exercise | **Decide** — and where uncertain, **default to real** |
| Call a stop on an exercise | **Decide** — any Blue member, no justification required at the time |
| Resume an exercise | **None** — White only |
| Detection content changes | **Recommend** to Green |
| Risk acceptance | **None** |

## Required independence
Moderate. Blue must be able to report that a detection did not fire without that reflecting on
Blue. **[M] Never publish per-analyst detection or disposition statistics** — it destroys the
data quality it measures and drives dishonest dispositions. Blue is measured on improvement
velocity and response quality, not on initial detection rate, which is Green's output.

## Inputs and outputs
| Inputs | From |
|---|---|
| Deployed detection content, telemetry, hardening state | Green |
| Threat intelligence | CTI |
| Exercise notification, registered indicators, deconfliction answers | White / Purple |
| Asset inventory, ownership, criticality | GRC / System Owners |
| Known exposure and remediation state | Yellow |

| Outputs | To |
|---|---|
| Alerts triaged, cases, incident records | CSIRT record, GRC |
| False positives, tuning requests, false-negative findings | **Green** |
| Real incidents as emulation candidates; six-stage outcomes 4–6 | **Purple** |
| Sensor-health and coverage reports | Green (M-10), Purple (M-1 declared column) |
| Hunt findings | Purple (scenario source), Green (detection source) |
| Audit-chain head hash | **White** (evidence manifest anchor) |
| Containment and recovery evidence | White, GRC |

## Required skills and certifications
**Skills [M]:** Alert triage under volume; investigation and scoping across identity, endpoint,
cloud, and network; evidence handling and chain of custody; incident command; log/query fluency
in the org's SIEM; containment technique and its blast radius; forensics fundamentals; clear
writing under time pressure — **an investigation nobody can follow is not an investigation**.
**Skills [R]:** Threat hunting methodology; malware triage; cloud control-plane forensics;
scripting for enrichment.
**Certifications [R]:** GCIA, GCIH, GCFA, GNFA; SC-200 where Entra-heavy; vendor SIEM/EDR
certifications. **[O]:** CISSP for the lead.

## Recommended roles
Per [`docs/OPERATING_MODEL.md`](docs/OPERATING_MODEL.md): Duty lead · Monitoring analyst ·
Incident responder · Threat hunter · Cloud and identity defender · Forensics lead · Recovery lead
(incident-time) · Vulnerability triage lead · Security platform liaison (to Green).

**Two roles in that document map elsewhere in this model:** "Detection engineer" → **Green**
(C-1); "Security platform engineer" pipeline ownership → **Green** (C-4). Staff them from the
SOC if you like — but they report and deliver into Green's catalog and pipeline.

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **MSSP + 0.5 FTE internal duty lead.** The internal role is non-negotiable: someone must own disposition quality and be reachable for deconfliction. |
| P2 | **4.0–6.0 FTE** for business-hours internal coverage with MSSP after-hours, or 8–10 for internal 24×7. Duty lead + analysts + 1 responder + 0.5 hunter. |
| P3 | **10–20 FTE** across shifts, plus forensics and cloud/identity specialists. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 1.0 FTE + MSSP |
| P2 | 8.0–12.0 FTE: duty leads, tiered analysts, 2 responders, hunter, forensics, cloud/identity defender |
| P3 | 25–40 FTE with follow-the-sun coverage and a dedicated hunt team |

## Reporting structure
Blue Lead / SOC Manager → Director, Security Operations. Peer to Purple (**not** subordinate —
Purple validates Blue's detections and must not manage the team it grades). Strong operational
line to CSIRT during declared incidents, where the incident commander outranks normal structure.

## Escalation path
Analyst → Duty lead → Incident commander → Director, Security Operations → CISO → Executive.
**During an exercise, any Blue member may call a stop directly to White, bypassing everyone.**
**On suspected real compromise during an exercise, CSIRT takes primacy over the exercise, always.**

## Tools and data access
| Access | Level | Label |
|---|---|---|
| **Sentinel Blue** (this folder) | Operate — `ingest`, `alerts`, `health`, `coverage`, `verify-ledger`, `validate` | [M] |
| SIEM | Read + triage + case management | [M] |
| EDR/XDR | Read + **respond, under approval** | [M] |
| Identity platform | Read logs; **disable/revoke under approval** | [M] |
| SOAR | Execute playbooks; **not author** (Green authors) | [R] |
| Detection content | **Read + propose. No deploy.** (C-1) | [M] |
| Forensic acquisition tooling | Per role | [R] |
| Evidence store | Write-once | [M] |
| Emulation / offensive tooling | **Denied** | [M] |

## Artifacts owned
Alert · Case · Incident record · Investigation timeline · Containment approval record ·
Recovery validation · Hunt record · Sensor-health report · Declared-coverage report ·
Audit chain + head-hash export · Deconfliction query log → see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- Median time to acknowledge, investigate, contain, recover — **by severity** (feeds M-5, M-6)
- % of critical telemetry within freshness budget (feeds M-10)
- **Triage correctness** — six-stage stage 4 in Purple validation. *This is Blue's headline
  number*: an alert that fires and is misclassified is a detection failure nobody counts.
- False-negative discoveries and time to durable coverage
- Reopened incidents and recurrence
- % of high-risk actions with complete approval **and rollback** evidence
- Deconfliction: 100% answered within 5 minutes
- 100% of closed incidents reviewed for emulation conversion within 30 days

## Failure indicators
- Alert volume and closure count reported as success — **these are workload measures** and
  Blue's own operating model already says so
- Severity reduced to improve service-level metrics → audit severity changes
- Incidents closed with "cause unknown" and no declared unknown, no follow-up detection
- Deconfliction answered "not exercise" without certainty → the answer is **UNKNOWN**; a
  confident wrong "no" burns a real IR activation, a confident wrong "yes" stands the SOC down
  during a breach
- Sensor silent for >24 h before anyone notices → B12 is not being performed
- Blue quietly writing production detections → C-1 violation; the catalog forks and diverges
- Tuning by excluding an entire admin group, product, or host class → forbidden by Blue's own
  detection standard, and it is how coverage silently disappears
- Hunt findings that never become detections or scenarios → the most expensive wasted work in
  the whole model
