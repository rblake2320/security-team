# YELLOW TEAM — Charter

**Function:** Secure software, platform, infrastructure, and AI-system builders
**Owner of this document:** Head of Engineering + AppSec Lead · **Approver:** CTO/VP Eng + CISO
**Review cadence:** Annual · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)

> **Structural note [M]:** Yellow is not a new org box. Yellow is the existing builder
> population — software engineers, AI/ML engineers, architects, DevSecOps, platform, database,
> and cloud engineers, plus system owners — operating under secure-by-design requirements, with
> **Security Champions** as the named per-team interface. Creating a separate "Yellow Team"
> department reintroduces the security/engineering split this model exists to close.

---

## Mission
Build and operate systems that are secure by design, and convert security findings into
completed engineering work with verifiable acceptance criteria and evidence.

## Scope
- **In:** Application code, APIs, infrastructure-as-code, pipelines, platform services,
  databases, cloud configuration, models/prompts/agent tooling, and the security properties of
  all of them; threat modeling participation; secure coding; dependency and secrets management;
  code review; SBOM generation; CI/CD security controls; remediation and evidence.
- **Out:** Adversary emulation; running the SOC; approving exercises; accepting risk on behalf
  of the business (system/business owner does that, and often is a Yellow participant — the
  roles must be kept distinct in the record).

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| Y1 | Implement secure-by-design requirements from the paved-road catalog (owned by Green) | [M] |
| Y2 | Produce and maintain a threat model for every system above a defined criticality threshold; refresh on material architecture change | [M] |
| Y3 | Secure coding practice and peer review with a security-relevant checklist | [M] |
| Y4 | Dependency management: pinned versions, provenance, known-vulnerability gating, upgrade cadence | [M] |
| Y5 | Secrets management: no secrets in code, IaC, images, logs, prompts, or model context. Rotation on exposure. | [M] |
| Y6 | IaC validation (policy-as-code) before apply | [M] |
| Y7 | SBOM generation per build artifact, stored and queryable | [M] (P3/regulated) / [R] (P1) |
| Y8 | CI/CD security: signed commits or verified provenance, protected branches, least-privilege runners, artifact signing | [M] |
| Y9 | Model/API security: authn/authz on every endpoint, rate limits, input/output validation, tool-permission scoping for agents, tenant isolation | [M] where AI systems exist |
| Y10 | Convert findings into prioritized backlog items with **acceptance criteria written as a testable condition** | [M] |
| Y11 | Provide fix evidence: commit/PR reference, test result, config diff, deployment record | [M] |
| Y12 | Participate in Purple exercises as the system expert when their system is under test | [R] |
| Y13 | Own regression tests for previously-found weaknesses (co-authored with Orange) | [M] |

## Explicit non-responsibilities
- Yellow does **not** decide finding severity (Purple proposes, White adjudicates).
- Yellow does **not** self-certify closure — closure requires Purple/Green retest evidence.
- Yellow does **not** run offensive tooling against other teams' systems.
- Yellow does **not** accept risk *as engineers*; only the accountable system/business owner may.
- Yellow does **not** own SIEM content or SOC processes.

## Decision authority
| Decision | Yellow's authority |
|---|---|
| Implementation approach for a fix | **Decide** (must meet acceptance criteria) |
| Sprint sequencing within severity SLA | **Decide** |
| Whether a fix meets acceptance criteria | **Recommend** — Purple/Green verify |
| Whether to deviate from a paved road | **Recommend** — Green + Orange review, System Owner accepts risk |
| Architecture changes | **Decide** with Orange design review for above-threshold systems |
| Deferring a finding past SLA | **None** — requires documented risk acceptance from System Owner |

## Required independence
None required — Yellow is deliberately integrated. **However:** the person who writes the fix
must not be the sole person who verifies it. Verification is Purple/Green (separation-of-duty
rule SoD-3 in the [org structure](../00-shared/02_org_structure_and_raci.md)).

## Inputs and outputs
| Inputs | From |
|---|---|
| Secure-by-design requirements, paved roads | Green |
| Threat models, abuse cases, design review findings | Orange |
| Findings with acceptance criteria | Purple |
| Vulnerability and dependency alerts | Vuln Mgmt / AppSec tooling |
| Compliance control requirements | GRC |

| Outputs | To |
|---|---|
| Working, deployed fixes + evidence | Purple (retest), GRC (evidence) |
| Threat models | Orange, White, GRC |
| SBOMs, provenance attestations | Supply-chain evidence store |
| Telemetry emitted by new features | Green |
| Regression tests in CI | Purple, Green |
| Deviation/exception requests | Green, Orange, System Owner |

## Required skills and certifications
**Skills [M]:** Language-appropriate secure coding; authn/authz design (OAuth2/OIDC, token
handling, session management); input validation and output encoding; cryptography *usage* (not
invention); cloud IAM and resource policy; container and Kubernetes security basics; IaC;
CI/CD pipeline security; data modeling with classification awareness. For AI systems: prompt
injection and tool-abuse defense, model/tenant isolation, output validation, retrieval-source
trust boundaries.

**Skills [R]:** Threat modeling (STRIDE or attack-tree), performance-aware security design.

**Certifications [O]:** Vendor cloud security certs. Secure-coding certifications are generally
weak signal — prefer demonstrated remediation history and a passing secure-code exercise.

**Security Champion program [M]:** ≥1 champion per delivery team, given 4 h/month protected
time and a defined curriculum. This is the single highest-leverage Yellow investment.

## Recommended roles
Security Champion (per team) · Application Security Engineer (shared) · Platform/DevSecOps
Engineer · Cloud Engineer · Data/DB Engineer · AI/ML Engineer · Solution Architect · System Owner

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | Existing engineers + **2–3 Security Champions at 4 h/month each** (~0.1 FTE total). One engineer designated as AppSec point of contact. |
| P2 | **1.0 FTE AppSec Engineer** (net-new or reallocated) + 1 Champion per delivery team (~6–10 champions × 4 h/month ≈ 0.25 FTE). |
| P3 | 2.0–4.0 FTE AppSec/DevSecOps + Champions across all teams + dedicated IaC policy owner. |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | 0.5 FTE AppSec + champions |
| P2 | 2.0 FTE AppSec + 1.0 DevSecOps + champions with formal curriculum and rotation |
| P3 | 6.0–10.0 FTE across AppSec, DevSecOps, IaC policy, AI security engineering |

## Reporting structure
Yellow reports through **engineering**, not security. AppSec Engineers may be centrally
employed and embedded (recommended) or fully embedded. Security Champions report to their
engineering manager with a dotted line to AppSec for curriculum and community.

## Escalation path
Engineer → Security Champion → AppSec Engineer → Engineering Manager → (dispute on severity or
SLA) → Purple Lead → White → System Owner for risk acceptance.

## Tools and data access
IDE security plugins [R] · SAST/SCA/secret scanning in CI [M] · DAST/API scanning against
pre-prod [M] · IaC policy scanning [M] · SBOM generation [M/R] · artifact signing [R] ·
container registry scanning [M] · Git with protected branches and required reviews [M] ·
ticketing/backlog [M] · **production admin: per normal least-privilege engineering policy,
unchanged by this model** · SIEM: read-only on their own service's logs [R].

## Artifacts owned
Threat Model · Engineering Remediation Ticket · Fix Evidence Package · SBOM · Provenance
attestation · Regression test · Architecture Decision Record · Deviation/Exception request
→ see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- % of above-threshold systems with a current, approved threat model ≥ 90% (M-14)
- Mean time to remediate by severity, within SLA (M-7)
- Recurrence rate of previously-fixed findings < 5% (M-9)
- % findings with automated regression coverage ≥ 60% (M-13)
- Paved-road adoption rate (deviation count trending down)
- Zero secrets detected in main-branch code for 90 consecutive days

## Failure indicators
- Fix evidence is a ticket comment saying "done" with no artifact reference
- Same finding class recurs across services → paved road is missing, not developers "not caring"
- Threat models exist but are never updated after the first release
- Remediation SLA met by re-classifying severity downward → audit severity changes
- Champions never given protected time → program is nominal
- Exceptions granted verbally and never expire
