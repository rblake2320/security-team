# ORANGE TEAM — Charter

**Function:** Offensive security expertise integrated with the builders (Red + Yellow)
**Owner of this document:** Orange Lead · **Approver:** CISO + Head of Engineering
**Review cadence:** Annual, and immediately after any Orange-caused incident · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)

---

## Mission
Apply adversarial thinking at design and build time — before code ships — so that attack paths
are removed on a whiteboard instead of discovered in production; and teach builders to recognize
how their own decisions become exploitable.

## Scope
- **In:** Authorized design and architecture reviews; threat modeling facilitation; abuse-case
  and misuse-case development; attack-surface analysis; trust-boundary analysis; pre-production
  security validation in lab/pre-prod; safe regression test development for previously
  discovered weaknesses; developer education derived from real findings; adversarial review of
  AI system designs (prompt injection, tool abuse, retrieval poisoning, agent privilege
  escalation).
- **Out:** Production exploitation; covert operations; persistence; credential theft;
  destructive testing; unauthorized environments; conducting the formal penetration test that
  compliance requires (independence — see below).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| O1 | Facilitate threat models for above-threshold systems and material changes | [M] |
| O2 | Produce abuse cases and misuse cases alongside functional requirements | [M] |
| O3 | Perform attack-surface and attack-path analysis on proposed architectures | [M] |
| O4 | Conduct pre-production security validation in authorized lab / pre-prod environments | [M] |
| O5 | Develop **safe** regression tests for every previously-discovered weakness class, runnable in CI | [M] |
| O6 | Teach: design-review clinics, "how this decision becomes an attack path" sessions, internal lab CTFs | [R] |
| O7 | Review AI/agent system designs for prompt injection, tool-permission escalation, data exfiltration via model output, and untrusted-content trust boundaries | [M] where AI systems exist |
| O8 | Review supply chain and build-system design for tampering paths | [R] |
| O9 | Contribute adversary knowledge to Purple scenario design | [R] |
| O10 | Maintain an internal attack-path catalog specific to the organization's real architecture | [R] |

## Explicit non-responsibilities — read this section twice
- Orange does **not** operate in production. Ever. Design docs, lab, and pre-prod only, unless
  White + System Owner have specifically authorized a production activity under an RoE, and even
  then only for **observation/validation**, not exploitation.
- Orange does **not** introduce covert persistence, destructive payloads, credential-theft
  tooling against real identities, or uncontrolled exploitation. This is a **charter-level
  prohibition**, not a guideline.
- Orange does **not** develop or hold malware, offensive capability against third parties, or
  evasion tooling for use outside an authorized lab.
- Orange does **not** approve its own scope.
- Orange does **not** perform the independent penetration test used as compliance evidence,
  where the governing framework requires assessor independence from the builders (see the
  [compliance crosswalk](../00-shared/10_compliance_crosswalk.md)). Orange is too integrated
  with Yellow to be independent. Use a separate internal Red Team or an external assessor.
- Orange does **not** block releases unilaterally — it raises findings; the gate is Green's
  (defensibility) and the risk decision is the System Owner's.

## Decision authority
| Decision | Orange's authority |
|---|---|
| Threat model content and completeness | **Decide** |
| Whether a design has an unacceptable attack path | **Recommend, strongly** — escalates to System Owner risk acceptance |
| Abuse cases that become required test cases | **Decide** |
| Lab / pre-prod test activity within an approved envelope | **Decide** |
| Any production activity | **None without White + System Owner** |
| Release blocking | **None directly** — via Green gate or risk acceptance |
| Risk acceptance | **None** |

## Required independence
Deliberately low — Orange must be trusted by builders to be useful. **Compensating controls [M]:**
1. Orange's environment authorization is explicit and narrow.
2. Orange activity is logged and reviewable by White.
3. Orange does not produce independent-assessment evidence.
4. Orange tooling is inventoried, approved, licensed, and lab-restricted.

## Inputs and outputs
| Inputs | From |
|---|---|
| Architecture designs, ADRs, epics, API specs | Yellow |
| Threat intel and real-world attack patterns | CTI, Purple |
| Purple findings (what actually worked) | Purple |
| Paved-road patterns and their assumptions | Green |
| Asset inventory and data classification | GRC / Data Owners |

| Outputs | To |
|---|---|
| Threat models (co-owned with Yellow) | Yellow, White, GRC |
| Abuse/misuse cases | Yellow (requirements), Purple (test cases) |
| Attack-path analyses | Yellow, Green (instrument these paths) |
| Pre-production validation results | Yellow, White |
| Safe regression tests | Yellow CI, Purple |
| Instrumentation requirements ("we need to see X") | Green |
| Developer education content | Yellow, HR/L&D |

## Required skills and certifications
**Skills [M]:** Offensive experience (web/API/cloud/identity at minimum); threat modeling
methodology (STRIDE, attack trees; LINDDUN for privacy [R]); architecture literacy (can read a
system design and find the trust boundary); code reading in the org's primary languages;
**teaching and non-condescending communication — this is a hiring gate, not a nice-to-have**;
cloud IAM attack paths; CI/CD and supply-chain attack paths. For AI: prompt injection classes,
indirect injection via retrieved content, tool/function-call abuse, and model output as an
injection vector into downstream systems.

**Skills [R]:** Secure code review depth; exploit development background — for judging
exploitability realistically, not for use.

**Certifications [R]:** OSCP / OSWE / OSEP, CRTO, GWAPT, GXPN, cloud pentest specialty.
**[O]:** none required. The real signal is a threat model that engineers found useful — ask
candidates to run a live threat model on a sample architecture during the interview.

## Recommended roles
Orange Lead / Principal Offensive Engineer · Application Security Architect (offensive-leaning) ·
Cloud Attack-Path Specialist · AI Red-Team Specialist [R where AI systems exist] · Embedded
offensive reviewer (rotating from Red Team, 1–2 weeks per quarter — **highly recommended**: it
keeps Orange's tradecraft current and Red's context organizational)

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **0.25 FTE** — contracted or borrowed offensive expertise, ~1 day/month, focused entirely on threat modeling the top 3 systems. |
| P2 | **0.5–1.0 FTE** — one offensive engineer embedded part-time with engineering, plus a rotating Red Team loan. |
| P3 | **2.0–3.0 FTE** — dedicated design-review capability across multiple program offices. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 0.5 FTE |
| P2 | 2.0 FTE + quarterly Red rotation |
| P3 | 4.0–6.0 FTE + standing rotation program |

## Reporting structure
Two viable models — pick one explicitly, do not leave it ambiguous:
- **Recommended:** Orange reports to Security (CISO org) and is *embedded* with engineering.
  Preserves offensive tradecraft and a security-side escalation path.
- **Alternative:** Orange reports to Engineering with a dotted line to CISO. Better adoption,
  weaker escalation. Choose this only if your engineering culture will not listen to an outsider.

## Escalation path
Orange Engineer → Orange Lead → CISO (or Engineering Director) → System Owner for risk decision.
**Any Orange discovery of an actively exploitable production issue goes immediately to CSIRT**,
not through the design-review queue — and Orange does not exploit it to prove the point.

## Tools and data access
| Access | Level | Label |
|---|---|---|
| Design docs, ADRs, source code | Read | [M] |
| Threat modeling tooling | Full | [M] |
| Lab / cyber range | Admin | [M] |
| Pre-production environment | Test-level, per approved envelope | [M] |
| **Production** | **Read-only at most; no offensive tooling; no exploitation** | [M] |
| Offensive tooling | Inventoried, approved, lab-restricted, license-tracked | [M] |
| CI/CD | Contribute regression tests; no pipeline admin | [R] |
| Credential material | **None.** Orange uses lab-only synthetic identities. | [M] |

## Artifacts owned
Threat Model (co-owned with Yellow) · Abuse/Misuse Case Library · Attack-Path Analysis ·
Attack-Surface Inventory · Pre-Production Validation Report · Safe Regression Test suite ·
Internal Attack-Path Catalog · Design Review Record · Developer education curriculum
→ see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- % of above-threshold systems with an approved, current threat model ≥ 90% (M-14)
- **Shift-left ratio:** issues found by Orange at design/pre-prod ÷ issues found by Purple in
  later validation. Rising ratio = the model is working. *(Orange's single most important metric.)*
- % of Purple findings that trace back to a design decision Orange previously flagged — **low is
  good**; high means Orange's recommendations are being ignored, and the escalation belongs to
  governance, not to Orange
- % of previously discovered weakness classes with a safe regression test in CI ≥ 80%
- Developer-reported usefulness of design reviews (survey ≥ 4/5) — soft, but predictive of
  whether teams will invite Orange early
- Zero production incidents caused by Orange activity

## Failure indicators
- Orange invited only after architecture is frozen → the function is decorative; fix the process gate
- Threat models produced by Orange *for* teams rather than *with* them → no knowledge transfer,
  models go stale immediately
- Orange findings routinely marked "won't fix" with no risk acceptance record
- Orange tooling found in production, or an Orange action causes an outage → **immediate charter
  review and White investigation**
- Orange used as a cheap substitute for independent penetration testing → compliance evidence gap
- Developers avoid Orange → communication-skill problem; this is a staffing decision, not a
  training one
