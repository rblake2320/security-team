# RED TEAM — Charter

**Function:** Independent adversary emulation and authorized offensive assessment
**Implementation:** **Aegis Red Team** (this folder is runnable code — see [README.md](README.md))
**Owner of this document:** Red Team Lead · **Approver:** CISO + White Exercise Director
**Review cadence:** Annual, and immediately after any out-of-scope event · **Marking:** INTERNAL

← [Index](../README.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md)
· [Integration review](../00-shared/16_red_team_integration_review.md)

> **Read [SECURITY.md](SECURITY.md) before this charter.** It states the operating boundary in
> the tool's own words: *"the authorization receipt is a technical guardrail, not a substitute
> for legal authorization, change control, stakeholder notification, or an emergency plan."*
> That sentence is the correct relationship between Aegis and the
> [Rules of Engagement](../00-shared/04_rules_of_engagement_template.md), and this charter does
> not weaken it.

---

## Mission
Execute authorized offensive assessment that produces **independent** evidence of whether
controls work — under written authorization, inside a fingerprinted scope, with every action
rate-limited, stoppable, and auditable.

## Scope
- **In:** Adversary emulation execution tasked by Purple; independent penetration testing and
  assessment where a framework requires assessor independence; scope and authorization
  enforcement; safe check development; evidence capture and ledger sealing; loaning operators
  into Orange on rotation.
- **Out:** Choosing what to test (Purple proposes, White approves); authorizing its own work;
  design review and threat modeling as a standing duty (Orange); detection engineering (Green);
  remediation (Yellow); triage and incident response (Blue); risk acceptance (System Owner).

## The three-way boundary — Red vs Purple vs Orange

This is the distinction that gets blurred everywhere, so it is stated first:

| | **Red** | **Purple** | **Orange** |
|---|---|---|---|
| Does what | **Executes** the adversary behavior | **Coordinates and measures** the test | **Reviews designs** before code ships |
| Independence | **Independent of the builders — this is the whole point** | Moderate | **Deliberately none** (embedded) |
| Environment | Lab, pre-prod, and production **under an approved RoE** | Observes everywhere | Design docs, lab, pre-prod. **Never production** |
| Can produce independent-assessment evidence? | **Yes** — this is the only team that can | No | **No** (crosswalk conflict F-1) |
| Tasked by | Purple (emulation) or GRC (formal assessment) | Its own pipeline, White approves | Engineering demand |

**Why this matters concretely:** Orange is integrated with the builders by design, cannot satisfy
any independence requirement, and **must not issue an independent assurance opinion**.

Red satisfies independence *from development* and *from defense operations*. But three controls
that look interchangeable demand **three different relationships**, and Red's evidence satisfies
whichever one its organizational position and contractual role actually establish:

| Control | Required relationship | Red? |
|---|---|---|
| **CA-2(1)** | Independent **control assessor** | Depends on assessment context and the authorizing authority — **confirm with the AO** |
| **CA-8(1)** | Independent **penetration-testing agent or team** | Position-dependent |
| **SA-11(5)** | **Developer-performed or developer-provided** penetration testing | Only if Red occupies the developer-provided role for that system |

**SA-11(5) is unqualified with respect to assessor independence, but not unconditionally
satisfied** — the evidence must still establish that the developer performed or contractually
provided the testing. Determine this **per system**, record it, and do not carry the
determination across systems. Full treatment: [§11.14](../00-shared/10_compliance_crosswalk.md).

**Red does not cover FedRAMP, CMMC, or PCI organizational independence** — those require a 3PAO,
C3PAO, or QSA respectively.

Relabelling integrated testing as independent assessment is an audit finding waiting to happen,
and in a federal context is worse than that.

## Responsibilities
| # | Responsibility | Label |
|---|---|---|
| RD1 | Execute only inside a **signed, unexpired authorization bound to the exact scope fingerprint** | [M] |
| RD2 | Acknowledge the scope fingerprint at execution time — a second, deliberate confirmation | [M] |
| RD3 | Enforce the allow-list: public targets denied unless the receipt explicitly opts in | [M] |
| RD4 | Respect request budgets, rate limits, concurrency caps, and timeouts on every run | [M] |
| RD5 | Honour the `.aegis/STOP` kill switch at every safety boundary; resume only on engagement-owner approval | [M] |
| RD6 | Maintain the append-only hash-chained audit ledger; **seal it with the approval authority's key at engagement close** | [M] |
| RD7 | Produce normalized findings with CWE references and **redacted** evidence — one-way digests, never raw secret values | [M] |
| RD8 | Develop new checks only inside the fixed registry protocol; declare target kinds and whether the check makes active requests | [M] |
| RD9 | Execute Purple-authored test cases faithfully and report what happened, including failures to execute | [M] |
| RD10 | Provide independent assessment where a framework requires assessor independence | [M] |
| RD11 | Rotate an operator into Orange 1–2 weeks per quarter | [R] |
| RD12 | Report any actively exploitable production issue to CSIRT **immediately**, without exploiting further | [M] |
| RD13 | Archive ledger, seal, and trust key to an access-controlled immutable store; hand the seal to White | [M] |

## Explicit non-responsibilities — read twice
- Red does **not** authorize its own engagements. Aegis will not run without a receipt signed by
  a key Red does not hold. **That is deliberate: the approval authority keeps the private key.**
- Red does **not** decide what is worth testing. Purple proposes; White approves.
- Red does **not** perform credential theft, persistence, evasion, malware deployment,
  destructive payloads, or uncontrolled scanning. **This release deliberately excludes them**
  and the exclusion is a charter-level prohibition, not a roadmap gap.
- Red does **not** load code from engagement files, accept shell-command templates, or execute
  arbitrary plugins. **Data must never become executable control flow.**
- Red does **not** write detections, remediate, triage, or accept risk.
- Red does **not** follow redirects out of scope, and does **not** treat a redirect as
  permission to leave it.
- Red does **not** hold production credentials. It uses per-engagement identities issued by an
  identity owner outside the team (SoD-9).

## Decision authority
| Decision | Red's authority |
|---|---|
| How to execute an approved test case | **Decide** |
| Whether a target resolves inside the authorized scope | **Decide — and deny on ambiguity** |
| Halting its own activity | **Decide** — Red may always stop; only White may authorize resumption |
| Whether a finding is technically valid | **Decide**; severity is Purple's proposal and White's adjudication |
| Check development and registry inclusion | **Decide** (peer review required) |
| Whether an engagement may proceed | **None** — signed authorization or no run |
| Scope expansion | **None** — a new fingerprint means a new authorization |
| Risk acceptance | **None** |

## Required independence — [M]

**"Independent" is four different requirements.** Red satisfies two of them. Corrected by
governance decision 2026-08-14 — see the [four-way taxonomy](../00-shared/10_compliance_crosswalk.md).

| Independence | Red? | Condition |
|---|---|---|
| **From development** | **Yes** | Red does not report through Yellow or Orange |
| **From defense operations** | **Yes** | Red does not operate or own Blue's controls |
| **Independent exercise scoring** | **NO** | **Red cannot score an exercise in which Red participated.** [Exercise Assurance](../00-shared/18_exercise_assurance.md) does |
| **Independent organizational assessment** | **NO** | External assessor required — 3PAO, C3PAO, QSA. No internal function satisfies it |

### Statement of record
> **Red closes the internal technical-assessment independence gap where organizational and
> framework requirements permit internal assessment. Red does not satisfy independent exercise
> scoring when Red participated, nor external organizational-assessor requirements such as 3PAO,
> C3PAO, or QSA independence.**

### Standing rules
1. Red does not report to any engineering manager whose systems it assesses, nor to Blue.
2. **The authorization key stays with the White approval authority, never with Red.** Aegis
   enforces SoD-2 cryptographically — Red can execute but cannot authorize.
   ⚠ Red will hold an **execution key** of its own under the
   [five-key model](../00-shared/19_aegis_trust_model.md); it will never hold the authorization
   or evidence key.
3. Red never scores itself, and never scores an exercise it ran.
4. Red's compensation and ratings are never tied to findings volume or to "success" against
   defenders.
5. Where a framework demands organizational independence, **procure an external assessor and say
   so plainly** rather than stretching the definition. Red's output in that case is *readiness
   evidence*, not the assessment.

## Inputs and outputs
| Inputs | From |
|---|---|
| Approved RoE, authorization receipt, trust key | **White** |
| Test cases, ATT&CK mapping, scenario | Purple |
| Engagement definition (targets, checks, limits) | Purple + System Owner |
| Threat intel / actor TTPs | CTI |
| Threat models and attack paths | Orange |

| Outputs | To |
|---|---|
| Findings (normalized, CWE-referenced, redacted) | Purple → Yellow/Green |
| Execution timeline and raw results | Purple (six-stage scoring stages 1–3) |
| **Sealed audit ledger + seal + trust key** | **White** (evidence manifest) |
| Independent assessment report | GRC (assessment evidence, layer L2) |
| Operator rotation | Orange |
| Reproduction detail | Yellow (they need it to fix) |

## Required skills and certifications
**Skills [M]:** Offensive tradecraft in the org's actual stack (web/API, cloud, identity);
scope discipline and the judgment to *deny on ambiguity*; log-aware execution (knowing what your
action should look like in telemetry); scripting; clear written reproduction steps — **a finding
an engineer cannot reproduce is not a finding**; cryptographic hygiene around key handling.
**Skills [R]:** Exploit development for judging exploitability realistically; cloud control-plane
attack paths; CI/CD and supply-chain attack paths.
**Certifications [R]:** OSCP / OSEP / OSWE, CRTO, GXPN, GPEN, cloud pentest specialty.
**[O]:** CREST/equivalent where a client or regulator asks for it by name.

## Recommended roles
Red Team Lead · Senior Operator (emulation execution) · Assessment Engineer (framework-facing
independent testing) · Check Developer (safe check registry) · Evidence/Ledger Custodian
(may be shared with White's custodian — **but never the same person who executes**).

## Minimum viable staffing
| Profile | Staffing |
|---|---|
| P1 | **Contracted, 2× per year.** No internal Red. Purple tasks the contractor; White authorizes. |
| P2 | **1.0 FTE internal operator** + contracted independent assessment 1–2× per year for framework evidence |
| P3 | **2.0–4.0 FTE** internal, plus an external assessor for the formal annual assessment |

## Mature staffing model
| Profile | Staffing |
|---|---|
| P1 | Contract only |
| P2 | 2.0 FTE + annual external assessment |
| P3 | 5.0–8.0 FTE with a standing Orange rotation and a dedicated check-development function |

## Reporting structure
Red Team Lead → CISO (or contract manager for external Red).
**Not** → Purple Lead as line manager: Purple must be able to critique Red's coverage and
technique selection without managing the people it critiques.
**Not** → any engineering leader whose systems Red assesses.

## Escalation path
Operator → Red Team Lead → White Exercise Director (authorization or safety) → CISO →
Executive Sponsor. **Any operator may call a stop directly to White.**
**Actively exploitable production issue → CSIRT immediately, in parallel with everything else.**

## Tools and data access
| Access | Level | Label |
|---|---|---|
| **Aegis Red Team** (this folder) | Operate: `plan`, `validate`, `run`, `verify-ledger` | [M] |
| **Authorization signing key** | **DENIED — held by the approval authority** | [M] |
| Trust (public) key | Read — distributed to operators | [M] |
| Lab / cyber range | Admin | [M] |
| Pre-production | Per approved envelope | [M] |
| Production | **Only under an approved RoE, per-action, with White present** | [M] |
| Production admin credentials | **Denied** | [M] |
| SIEM | Read-only, post-exercise, for validation sessions | [R] |
| Source code | Read, where the engagement includes source review | [R] |
| Evidence store | Write-once | [M] |

## Artifacts owned
Engagement definition · Authorization receipt (**receives**, does not issue) · Scope fingerprint ·
Execution plan · Findings (normalized) · Audit ledger + seal · Assessment report ·
Check definitions → see [ARTIFACTS.md](ARTIFACTS.md)

## Success metrics
- **100% of runs executed under a valid, unexpired, fingerprint-bound authorization** — a single
  exception is a program-level incident, not a metric dip
- 0 out-of-scope actions
- 0 unredacted secrets in any finding or report
- Ledger verifies and seals cleanly, 100% of engagements
- Techniques **validated** (feeds M-1), not systems compromised
- Findings reproducible by the receiving engineer without Red's help ≥ 90%
- Independent assessment findings that are **new**, not repeats of known-unremediated items

## Failure indicators
- **"Red won" appears anywhere in a report.** Red has no score. Adversarial framing makes Red
  optimize for impressive compromise over organizational learning
- A run executed with `--ack-scope` copied from a stale plan → the second acknowledgement has
  become a formality
- Findings volume rising while M-3 detection rate is flat → Red is finding what is easy, not
  what matters
- Scope questions resolved in Red's favour → **deny on ambiguity, always**
- The signing key found on an operator's machine → **independence void; halt and rotate keys**
- Red refuses collaborative validation sessions → cultural failure; escalate to CISO
- Checks added outside the fixed registry, or engagement files carrying command templates →
  the tool's central safety property has been defeated
