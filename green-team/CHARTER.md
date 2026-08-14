# GREEN TEAM — Charter

**Function:** Defensive security engineering integrated with the builders (Blue + Yellow)
**Owner of this document:** Green Team Lead · **Approver:** Director of Security Engineering + Head of Platform
**Review cadence:** Annual · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)

---

## Mission
Engineer defensibility into the platform: telemetry, hardened configuration, identity controls,
segmentation, endpoint and cloud protections, logging, alerting, response automation, backup and
recovery — so that systems are observable and defensible **before** they reach production, and
so that every shipped fix produces the security signal it was supposed to produce.

## Scope
- **In:** Detection engineering; telemetry pipeline and log source onboarding; hardening
  baselines (CIS/STIG/vendor); identity and conditional-access controls; network and workload
  segmentation; EDR/XDR policy; cloud security posture controls and guardrails; SOAR playbooks;
  backup, restore, and resilience validation; secure platform patterns and paved roads;
  pre-production defensibility gates.
- **Out:** Writing application feature code (Yellow); authorizing exercises (White); executing
  offensive tests (Orange/Purple); front-line alert triage (SOC — though Green should rotate
  through triage periodically to stay honest, [R]).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| G1 | Own the detection catalog: authoring, versioning, testing, tuning, and lifecycle/deprecation of detection content | [M] |
| G2 | Own log source onboarding and telemetry health monitoring (is the data actually arriving?) | [M] |
| G3 | Define and maintain hardening baselines and measure drift | [M] |
| G4 | Engineer identity controls: conditional access, phishing-resistant auth, privileged access workflows, service-principal and workload-identity hygiene | [M] |
| G5 | Segmentation design and validation | [M] |
| G6 | Cloud guardrails as policy-as-code (preventive controls preferred over detective) | [M] |
| G7 | Response automation (SOAR) with human-approval gates on destructive actions | [R] |
| G8 | Backup, restore, and recovery validation — **including restore drills, not just backup success reports** | [M] |
| G9 | Define and enforce a **"defensible-before-production" gate**: required log sources, required detections, required runbook, required rollback | [M] |
| G10 | Verify that deployed fixes emit the expected security signal (fix → telemetry → detection chain) | [M] |
| G11 | Build reusable paved roads (secure-by-default templates, modules, base images, pipeline templates) | [M] |
| G12 | Convert Purple detection gaps into shipped, tested detection content | [M] |
| G13 | Maintain detection-as-code in Git with CI validation and unit tests | [R] |

## Explicit non-responsibilities
- Green does **not** validate its own detections against live adversary emulation — Purple does.
- Green does **not** approve exercises or accept risk.
- Green does **not** own application vulnerabilities (Yellow) or exercise conduct (Purple).
- Green does **not** run offensive tooling.

## Decision authority
| Decision | Green's authority |
|---|---|
| Detection content design, thresholds, and tuning | **Decide** |
| Log sources to onboard and retention tiers | **Decide** within budget; Data Owner concurs |
| Hardening baseline content | **Decide** (must meet governing benchmark, e.g. CIS/STIG) |
| Whether a system passes the defensibility gate | **Decide — blocking authority for production release** |
| Deploying automated *destructive* response (isolate/disable/kill) | **Recommend** — requires System Owner approval and documented rollback |
| Emergency detection deployment during an incident | **Decide** (post-hoc change record required within 24 h) |
| Risk acceptance | **None** |

## Required independence
Low. Green is deliberately fused with Yellow. **One separation is required [M]:** Green may not
be the sole party attesting that a detection works. Purple validates. Where Purple does not yet
exist (P1), a second Green engineer who did not author the rule must validate, and this must be
recorded.

## Inputs and outputs
| Inputs | From |
|---|---|
| Detection gaps, control gaps | Purple |
| Threat models and abuse cases (what to instrument for) | Orange |
| New service designs and deploy plans | Yellow |
| Alert quality feedback, false positives | SOC |
| Threat intel (behavior to detect) | CTI |
| Compliance control requirements | GRC |

| Outputs | To |
|---|---|
| Deployed, versioned detection content | SOC, Purple (validation) |
| Telemetry health status | Purple (metric M-10), SOC |
| Hardened baselines, paved roads, modules | Yellow |
| Defensibility gate results | Yellow, System Owner, release process |
| SOAR playbooks | SOC, CSIRT |
| Restore-drill results | Resilience owner, GRC, exec |
| Control implementation evidence | GRC |

## Required skills and certifications
**Skills [M]:** Detection engineering (behavioral over signature; understands data sources and
their gaps); log pipeline engineering; query languages for your SIEM (KQL/SPL/SQL); identity
platform engineering (AD + Entra ID / cloud IAM); cloud security posture and policy-as-code;
endpoint security engineering; network segmentation; automation (Python + IaC); backup/restore
architecture; incident response fundamentals.

**Skills [R]:** Data engineering with cost awareness — **telemetry cost is the single most common
reason detection programs stall**; adversary TTP knowledge sufficient to write behavioral logic.

**Certifications [R]:** GIAC GCDA / GDAT / GCIA; cloud security specialty matched to environment;
Microsoft SC-200 / SC-300 where Entra-heavy; vendor SIEM/EDR certifications.

## Recommended roles
Detection Engineer · Telemetry/Data Pipeline Engineer · Identity Security Engineer · Cloud
Security Engineer · Endpoint Engineer · Automation/SOAR Engineer · Resilience Engineer
(backup/restore/DR) · Green Team Lead

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **0.5 FTE.** One person who can write detections and manage the SIEM/EDR. Rely on vendor-provided content, tuned locally. |
| P2 | **1.5–2.0 FTE:** 1 Detection Engineer + 0.5 Identity/Cloud Security Engineer + 0.25 Resilience. Backed by SOC and platform engineering. |
| P3 | **4.0–6.0 FTE** dedicated detection engineering + telemetry + identity + cloud + automation. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 1.0 FTE |
| P2 | 4.0 FTE: Lead, 2× Detection Engineer, Telemetry Engineer (+ shared identity/cloud) |
| P3 | 10.0–15.0 FTE across detection, telemetry, identity, cloud, endpoint, automation, resilience |

## Reporting structure
Green Lead → Director of Security Engineering (or Security Operations). Strong dotted line into
Platform Engineering — Green ships *platform*, so it must be inside platform's review and release
process, not adjacent to it.

## Escalation path
Green Engineer → Green Lead → Security Engineering Director → CISO. Gate disputes (Green blocks a
release) → System Owner + Engineering Director, with signed risk acceptance as the only override.

## Tools and data access
SIEM: **content author + deploy (Green's core tool)** [M] · EDR/XDR: policy admin [M] ·
Identity platform: conditional access + policy admin (privileged, with break-glass separation)
[M] · CSPM/CNAPP: admin [M] · SOAR: author + deploy [R] · Backup platform: operator + restore
test [M] · Git for detection-as-code [R] · Production change management: standard engineering
path [M].

## Artifacts owned
Detection content (as code) · Detection catalog + ATT&CK mapping · Telemetry/log source
inventory + health dashboard · Hardening baselines + drift reports · Paved-road catalog ·
Defensibility gate checklist and results · SOAR playbooks · Restore drill records · Control
implementation evidence → see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- Telemetry availability ≥ 99% per critical log source (M-10) — *the foundational metric;
  detection coverage is meaningless without it*
- Detection rate on Purple-tested prioritized techniques (M-3), trending up
- False-positive rate per detection within target band (M-11)
- Median time from detection gap identified → content deployed ≤ 15 business days
- % of production services passing the defensibility gate at release ≥ 95%
- Restore drills: ≥ 1 per critical system per quarter, with measured RTO/RPO vs. target
- Paved-road adoption ≥ 80% of new services

## Failure indicators
- Detection count rising while detection rate is flat → writing rules, not coverage
- Alert volume rising with no corresponding true-positive growth → tuning debt; the SOC will
  start ignoring alerts, and then the detection does not exist
- Log sources silently dead for >24 h before anyone notices → telemetry health monitoring absent
- Backups "succeed" but restores are never tested → the classic ransomware failure
- Green ships detections Purple then finds don't fire → validate before declaring done
- Defensibility gate always waived under release pressure → the gate does not exist
