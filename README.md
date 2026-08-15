# Security Team — Seven-Team Security Operating Model

**Purple · White · Yellow · Green · Orange · Blue · Red**

**Document set version:** 1.3
**Date:** 2026-08-14
**Status:** Design baseline. NOT an authorization. NOT a compliance attestation.
**Classification marking (this set):** UNCLASSIFIED // FOR OFFICIAL USE — INTERNAL PLANNING

> ## ⚠ Program state: `PREREQUISITES_PENDING` → `NOT_ASSESSMENT_READY`
>
> The design is structurally coherent and audit-defensible **by design**. It is **not yet
> assessment-ready operationally.**
>
> **Permitted now:** run exercises · compute diagnostic scores · engineering rehearsal and training.
> **Not permitted:** issue an assurance statement · present any score as assurance · forward
> results to an auditor, regulator, customer, or board.
>
> Every artifact produced in this state carries **`TRAINING_OR_ENGINEERING_USE_ONLY`**, and
> **removing that marking requires a state transition, not an editorial decision.**
>
> Four gates must pass first — [§22](00-shared/21_readiness_gate.md), checked by the automated
> issuance gate `PROGRAM-READINESS-GATE-001` using
> [`config/assessment_readiness.json`](00-shared/config/assessment_readiness.json):
> canonical implementation · Exercise Assurance operational · key custody verified ·
> containment verified on **all** supported platforms.

---

## 0.1 What this is

A production-ready operating model for five coordinated security functions, designed so that
authorized security testing and real incidents are converted into **measurable, evidenced
improvements** in architecture, code, detections, response, resilience, compliance evidence,
and workforce capability.

## 0.1a Layout

**One folder per team**, plus a shared folder for everything cross-cutting.

```

├── README.md              <- you are here: assumptions, Open Decisions, legend
├── 00-shared/             <- cross-team design (§1, §3-§18)
├── purple-team/           <- + runnable: Aegis Purple assurance core (src/ docs/ schemas/ tests/)
├── white-team/   │
├── yellow-team/  ├─ identical structure (below)
├── green-team/   │
├── orange-team/  ┘
├── blue-team/             <- + runnable: Sentinel Blue (src/ docs/ rules/ schemas/ playbooks/ collectors/)
└── red-team/              <- + runnable: Aegis Red Team (src/)
```

Every team folder has the same shape:

```
<team>/
├── .init              machine-readable team manifest (YAML)
├── CHANGELOG.md       versioned change history
├── CHARTER.md         the §2 charter
├── PLAYBOOK.md        day-to-day operating procedure
├── ARTIFACTS.md       the artifacts this team owns
├── AI_AGENT.md        this team's optional AI agent spec
├── config/            scorecard.json — weights, thresholds, auto-fail conditions
├── tests/             assessment.md — capability assessment checklist
├── templates/         copy-ready blank forms
└── examples/          one worked example
```

| File / folder | Contents |
|------|----------|
| `.init` | **Machine-readable manifest** — identity, reporting lines, owned stages/gates/artifacts/metrics, decision authority, separation of duties, dependencies, integrations, staffing, bootstrap checklist. Read this to route work to a team or bootstrap as one. |
| `CHANGELOG.md` | Changes to decision authority, independence, or gates are MAJOR bumps requiring re-approval. |
| `CHARTER.md` | Mission, scope, responsibilities, **non-responsibilities**, authority, independence, inputs/outputs, skills, roles, staffing, reporting, escalation, tools, artifacts, success metrics, failure indicators |
| `PLAYBOOK.md` | Workflow stages owned, rhythms, runbooks, escalation, metrics, anti-patterns |
| `ARTIFACTS.md` | Artifact specs (Blue's and Red's are mostly machine-emitted schemas) |
| `AI_AGENT.md` | Inputs, permitted tools, denied capabilities, approvals, injection defenses, kill switch, fail-closed behavior |
| `config/scorecard.json` | Assessment weights, pass threshold, automatic-failure conditions, program weight — **frozen before execution** |
| `tests/assessment.md` | How to test this team, evidence required per component, scoring worksheet. Blue and Red also hold their unit tests here |
| `templates/` | Copy-ready blank forms — copy the file rather than copy-paste out of a doc |
| `examples/` | One worked example showing what "good" looks like |

> **Three teams are runnable, and deliberately separated.** `purple-team/` is **Aegis Purple**
> (exercise assurance and lifecycle enforcement, **32 tests passing**), `blue-team/` is
> **Sentinel Blue** (**38 tests passing**), and `red-team/` is **Aegis Red Team** (**15 tests,
> 14 passing / 1 Windows privilege skip**) — verified locally 2026-08-14. Blue and Red were reconciled against the design
> teams in [§15](00-shared/14_blue_team_integration_review.md) and
> [§17](00-shared/16_red_team_integration_review.md), which resolve sixteen real ownership
> conflicts between them. Aegis Purple does not erase the current readiness hold; it makes the
> hold, role separation, frozen plan, evidence completeness, and score ordering executable.
> **Read the integration reviews and `purple-team/README.md` before assuming any boundary.**

### Shared design (`00-shared/`) — read in this order

| # | File | Deliverable |
|---|------|-------------|
| 1 | [`01_executive_operating_model.md`](00-shared/01_executive_operating_model.md) | §1 Executive Operating Model |
| 2 | [`02_org_structure_and_raci.md`](00-shared/02_org_structure_and_raci.md) | §3 Org chart, separation of duties, conflicts of interest, RACI |
| 3 | [`03_end_to_end_workflow.md`](00-shared/03_end_to_end_workflow.md) | §4 17-stage lifecycle with entry/exit criteria and six hard gates |
| 4 | [`04_rules_of_engagement_template.md`](00-shared/04_rules_of_engagement_template.md) | §5 Reusable RoE template |
| 5 | [`05_communication_protocol.md`](00-shared/05_communication_protocol.md) | §6 Channels, cadence, machine-readable formats, deconfliction |
| 6 | [`06_artifact_index_and_standards.md`](00-shared/06_artifact_index_and_standards.md) | §7 Artifact registry + universal standards |
| 7 | [`07_metrics.md`](00-shared/07_metrics.md) | §8 M-1..M-16 + banned vanity metrics |
| 8 | [`08_toolchain_architecture.md`](00-shared/08_toolchain_architecture.md) | §9 Tool categories, integrations, access model, budget tiers |
| 9 | [`09_ai_and_automation_governance.md`](00-shared/09_ai_and_automation_governance.md) | §10 AI governance + Evidence and Metrics agents |
| 10 | [`10_compliance_crosswalk.md`](00-shared/10_compliance_crosswalk.md) | §11 Framework mapping + conflicts |
| 11 | [`11_implementation_roadmap.md`](00-shared/11_implementation_roadmap.md) | §12 30/60/90/6mo/12mo roadmap |
| 12 | [`12_pilot_exercise.md`](00-shared/12_pilot_exercise.md) | §13 Identity → Cloud pilot |
| 13 | [`13_final_recommendation.md`](00-shared/13_final_recommendation.md) | §14 Final recommendation |
| 14 | [`14_blue_team_integration_review.md`](00-shared/14_blue_team_integration_review.md) | §15 Blue integration review — **nine reconciled ownership conflicts** |
| 15 | [`15_why_engine_and_soul_integration.md`](00-shared/15_why_engine_and_soul_integration.md) | §16 Why Engine + Soul System wiring |
| 16 | [`16_red_team_integration_review.md`](00-shared/16_red_team_integration_review.md) | §17 Red integration review — seven reconciliations; **Aegis mechanizes the RoE** |
| 17 | [`17_capability_assessment.md`](00-shared/17_capability_assessment.md) | §18 **Capability assessment** — integrated exercise, per-team scorecards, program readiness |
| 18 | [`18_exercise_assurance.md`](00-shared/18_exercise_assurance.md) | §19 **Exercise Assurance Authority** — who assesses White, and the six things it may do |
| 19 | [`19_aegis_trust_model.md`](00-shared/19_aegis_trust_model.md) | §20 **Five-key trust model** — authorization / execution / evidence / assessment / revocation |
| 20 | [`20_closure_plan.md`](00-shared/20_closure_plan.md) | §21 **Closure plan** — the seven open items, in prescribed order |
| 21 | [`21_readiness_gate.md`](00-shared/21_readiness_gate.md) | §22 **Readiness gate + state model** — automated by `PROGRAM-READINESS-GATE-001`; what may and may not be called assurance |
| 24 | [`24_incident_2026-08-15_recursive_evidence_collection.md`](00-shared/24_incident_2026-08-15_recursive_evidence_collection.md) | §25 **Incident postmortem** — recursive process spawning in the program's own tooling, root cause, fix commits, kernel-enforced containment, standing rule on atomic commits |

### Team charters (§2)

| Team | Charter | One-line mission |
|------|---------|------------------|
| 🟣 Purple | [`purple-team/CHARTER.md`](purple-team/CHARTER.md) | Convert adversary behavior into controlled tests and drive the gaps to closure |
| ⚪ White | [`white-team/CHARTER.md`](white-team/CHARTER.md) | Independent authorization, safety, evidence integrity, scoring — and unconditional stop authority |
| 🟡 Yellow | [`yellow-team/CHARTER.md`](yellow-team/CHARTER.md) | Build secure by design; convert findings into completed, evidenced engineering work |
| 🟢 Green | [`green-team/CHARTER.md`](green-team/CHARTER.md) | Engineer defensibility into the platform before production |
| 🟠 Orange | [`orange-team/CHARTER.md`](orange-team/CHARTER.md) | Remove attack paths on a whiteboard instead of finding them in production |
| 🔵 Blue | [`blue-team/CHARTER.md`](blue-team/CHARTER.md) | Operate the defense every day — detect, investigate, contain, recover, and improve |
| 🔴 Red | [`red-team/CHARTER.md`](red-team/CHARTER.md) | Execute authorized offensive assessment that produces **independent** evidence |

### Testing the teams

[§18 Capability Assessment](00-shared/17_capability_assessment.md) — one controlled end-to-end
scenario, not isolated quizzes. Baseline → collaborative improvement → **identical retest**.

Weights `baseline-v1`, ratified 2026-08-14 — **governance defaults, not empirically validated.**

| Team | Pass | Weight | Automatic failure |
|---|---|---|---|
| Purple | 80% | **18.75%** | Unresolved critical detection gap |
| White | **90%** | **18.75%** | Continuing after a mandatory stop; unauthorized scope expansion |
| Blue | 85% | **15.00%** | SOC stood down; ambiguity called "exercise" without certainty |
| Yellow | 85% | **15.00%** | Open critical; high-severity without a regression test |
| Green | 85% | **11.25%** | <100% critical telemetry; a must-detect technique missed |
| Orange | 80% | **11.25%** | Seeded critical path missed; unsafe testing |
| Red | **90%** | **10.00%** | Any run without a valid receipt; **any** out-of-scope action |

**Auto-fail is applied before aggregation.** One team's automatic failure sets
`program_status = FAILED`; the weighted score is retained for diagnostics only. A weighted mean is
not a safety property — without this ordering, a catastrophic Red or White failure is averaged
away by strong performance elsewhere.

**Who assesses White?** Not White — SoD-4 forbids it. The
[Exercise Assurance Authority](00-shared/18_exercise_assurance.md) (§19): a **role**, not an
eighth team, performed by Internal Audit, an external facilitator, or a framework-named assessor.
**White still controls the exercise; Exercise Assurance assesses how White performed that
control.**

**A 95–100% score triggers a mandatory challenge review**, never a conclusion — the test may have
been easy, the scenario may have leaked, or scoring may have been permissive.

### Institutional memory

Both systems already run on this machine and are wired into the model in
[§16](00-shared/15_why_engine_and_soul_integration.md):

| System | Captures | Answers | Serves |
|---|---|---|---|
| **Why Engine** (`github.com/rblake2320/why-engine`) | Root-cause knowledge as structured, hash-audited WhyCases | *"Has this failure happened before?"* (`why.recall`) | **M-9 recurrence**, M-13 regression conversion |
| **Soul System** (`github.com/rblake2320/soul-system`) | Behavioral learning — decisions, corrections, pain points, outcomes | *"What did we already learn about how to work here?"* | Process quality; fewer repeat mistakes |

**Hard constraint:** security-program WhyCases are **outbox-only, `internal` sensitivity minimum,
never published to any external surface.** Soul ledgers never carry CUI, PII, credentials, or
evidence content. See §16.4 and §16.3.

---

## 0.2 Capability legend

Every capability in this set is labeled:

| Label | Meaning |
|-------|---------|
| **[M] Mandatory** | Without this the model is unsafe, unauthorized, or produces no defensible evidence. Do not operate without it. |
| **[R] Recommended** | Materially improves outcome quality or efficiency. Deferrable with documented risk acceptance. |
| **[O] Optional** | Value only at scale, or only under specific regulatory drivers. |

And separated into five columns of concern:

**PEOPLE** · **PROCESS** · **TECHNOLOGY** · **GOVERNANCE** · **EVIDENCE**

---

## 0.3 Assumptions (all placeholders were left unfilled)

The source request contained 14 unpopulated context fields (`[NAME]`, `[MISSION]`,
`[EMPLOYEES / USERS]`, environment, cloud, stack, impact level, frameworks, current Red
capability, current Blue/SOC capability, staff, budget, target maturity date, primary risks,
constraints). **Nothing about a real organization has been assumed.**

Instead the model is written against three **reference profiles**. The default spine of this
document is **Profile P2**. Deltas for P1 and P3 are called out inline wherever staffing,
budget, cadence, or evidence rigor changes.

| | **P1 — Small / Commercial** | **P2 — Mid / Regulated (DEFAULT)** | **P3 — Government / CUI / IL4+** |
|---|---|---|---|
| Headcount | 50–500 employees | 500–5,000 | 1,000–20,000 + mission partners |
| Environment | Single cloud, SaaS-heavy | Hybrid: on-prem AD + 1–2 clouds | Hybrid, air-gap or IL4/IL5 enclaves |
| Security staff | 1–4 total | 8–25 total | 25–80 across gov + contractor |
| Frameworks | SOC 2, ISO 27001 | SOC 2 + ISO 27001 + PCI DSS or HIPAA | NIST 800-171 / 800-53 / CMMC L2 / RMF / FedRAMP / STIG |
| Annual security budget | $150K–$750K | $1.5M–$6M | $4M–$20M (often incl. contract labor) |
| Exercise cadence | 2–4 purple ops/yr | 8–12 purple ops/yr | 12–24 + mandated annual independent assessment |
| Dedicated White Team? | No — virtual, 1 named authority | Virtual cell, chaired by CISO-independent role | **Yes — dedicated White Cell required** |
| **Assumed target maturity date** | +12 months from start | +12 months from start | +18 months (ATO/assessment cycles dominate) |

> **Assumption A-1:** Roman numeral maturity is measured against §8 metrics, not against a
> vendor maturity model. "Mature" = all §8 metrics produced automatically, on cadence, with
> named owners, for two consecutive quarters.
>
> **Assumption A-2:** An existing SOC or MSSP with alert triage capability exists. If it does
> not, the Green Team roadmap in §12 extends by ~90 days and Purple exercises must not begin
> until telemetry baseline exists (you cannot measure detection where there is no detection).
>
> **Assumption A-3:** Legal counsel and a privacy function exist and are reachable within
> 1 business day. Where they do not, White Team authority cannot be constituted — see O-4.
>
> **Assumption A-4:** No claim is made that this model produces an ATO, a FedRAMP
> authorization, a CMMC certification, an ISO certificate, or a SOC 2 report. It produces
> *evidence artifacts* those processes consume. See §11.

---

## 0.4 Open Decisions

These must be closed by a named human before the corresponding section can be executed.
**Do not implement past the "Blocks" column without a decision.**

| ID | Open decision | Why it matters | Blocks | Proposed default (if silence) | Decision owner | Due |
|----|---------------|----------------|--------|-------------------------------|----------------|-----|
| O-1 | Organization name, mission, and legal entity structure | Determines who can authorize testing and who is liable | RoE §5, all charters | — none; hard blocker | Executive sponsor | Before Day 1 |
| O-2 | Highest data classification / impact level in scope (Public / PII / PHI / CHD / CUI / IL2 / IL4 / IL5) | Drives evidence handling, tool authorization, cloud region, and whether testing may touch production at all | §5 RoE, §7 artifact markings, §9 toolchain, §10 AI agents | Treat as **CUI-equivalent**; most restrictive handling | CISO + Data Owner | Day 5 |
| O-3 | Authoritative framework set and which is the *governing* one when they conflict | Frameworks disagree on pentest frequency, independence, and evidence retention (see §11 conflicts) | §11, §8 metric targets | NIST CSF 2.0 as the organizing spine; strictest specific requirement wins per control | GRC lead | Day 10 |
| O-4 | Who holds White Team stop authority, and to whom do they report? | White Team independence is the single load-bearing control in this model | §2 White charter, §3 org chart | Report to CIO/COO/General Counsel — **not** to the CISO who owns Red/Blue | Executive sponsor + GC | Day 10 |
| O-5 | Is production in scope for any Orange/Purple activity, and under what conditions? | Determines lab investment, RoE severity, and insurance/legal exposure | §4 stage 7, §5, §13 | Production = **observe/validate only**; all exploitation in lab or pre-prod | System Owners + CISO | Day 15 |
| O-6 | Current Red Team capability (internal / contracted / none) | Determines whether Purple is coordination-only or must also *execute* | §2 Purple charter, §12 phase 1 staffing | Assume **no internal Red**; Purple starts as coordination + emulation-tool operator, contracts specialist Red 2×/yr | CISO | Day 15 |
| O-7 | Current SOC/CSIRT model (24×7 internal / follow-the-sun / MSSP / business hours) | Determines MTTD/MTTC baselines and whether exercise windows must avoid MSSP handoffs | §6, §8 metrics, §13 | Assume **MSSP + business-hours internal**; exercise windows inside internal coverage only | SOC Manager | Day 15 |
| O-8 | Annual budget envelope and whether it is opex, capex, or contract-funded | Determines tool vs. staff trade in §9 and §12 | §9, §12 | P2 midpoint (~$3M security total; ~12% allocated to this model = ~$360K/yr incremental) | CFO + CISO | Day 20 |
| O-9 | Available staff count and skills inventory | Determines virtual vs. dedicated for each of the five functions | §2 staffing, §3 | P2 minimum viable = 6.5 FTE-equivalents drawn from existing roles (see §2) | CISO + Eng leadership | Day 20 |
| O-10 | Target maturity date | Determines roadmap compression and which items are deferred | §12 | +12 months (P1/P2), +18 (P3) | Executive sponsor | Day 20 |
| O-11 | Primary risks (top 5 named, ranked) | Purple exercise selection must be risk-driven, not tool-driven | §4 stage 1, §13 pilot choice | Default ranking: (1) identity compromise → cloud takeover, (2) SaaS/third-party token abuse, (3) ransomware/backup integrity, (4) CI/CD and supply chain, (5) AI/LLM data exposure & agent abuse | Risk Committee | Day 25 |
| O-12 | Known constraints (union/works council, change freeze windows, safety-of-life systems, ITAR/EAR, mission blackout periods, contractual no-test clauses with SaaS vendors) | Any one of these can void an RoE mid-exercise | §5, §4 stage 6 | Assume: SaaS providers require written test notification; quarterly change freezes exist; no safety-of-life systems | Legal + Ops | Day 25 |
| O-13 | Pilot exercise focus | The pilot sets the template for everything after | §13 | **Identity → Cloud** (see §13). Alternates fully scoped: API, Supply Chain, AI System | CISO + Purple Lead | Day 30 |
| O-14 | Cyber insurance policy terms regarding adversary emulation and incident notification | Some policies require notification of simulated incidents or void coverage for self-inflicted outage | §5 stop conditions | Assume notification required for any exercise touching production | Risk/Legal | Day 30 |
| O-15 | HIPAA Security Rule status — the 2025 NPRM proposed mandatory annual pentest and semiannual vulnerability scanning | If finalized, changes HIPAA from "evaluation" to a prescriptive testing mandate | §11 crosswalk row | Verify current rule status with counsel before relying on §11 HIPAA row | GRC + Counsel | Day 30 |
| O-16 | FedRAMP program baseline in effect (Rev 5 baselines vs. FedRAMP 20x program changes) and current Penetration Test Guidance version | Determines mandated attack vectors and assessor independence | §11 FedRAMP row, §12 | Verify against the FedRAMP PMO's current published guidance before scoping any FedRAMP-facing test | GRC | Day 30 |

**Rule:** any section consumed downstream of an unclosed Open Decision must carry the marking
`[UNRESOLVED: O-nn]` in the working copy. Do not delete the marking to make a document look finished.

---

## 0.5 The five non-negotiables

If budget, time, or politics force cuts, these five survive. Everything else is negotiable.

1. **[M] Written authorization before any test action.** No verbal approvals. No "the CISO said
   it's fine." A signed RoE with a named system owner, or the activity does not happen.
2. **[M] An independent stop authority.** One named human, outside the exercise chain, who can
   halt everything in under 5 minutes and whose decision is not appealable during the exercise.
3. **[M] Deconfliction that works under stress.** Every exercise action is attributable to the
   exercise within 60 seconds, or the SOC will spend a real incident chasing your traffic.
4. **[M] Evidence integrity.** Hashed, timestamped, access-controlled, retained to the longest
   applicable schedule. Evidence you cannot prove was unaltered is not evidence.
5. **[M] Findings convert to engineering work with acceptance criteria.** A finding that does
   not become a ticket with a testable exit condition is a report, not a security improvement.

---

## 0.6 How to instantiate this for a real organization

1. Close O-1 through O-5. These are hard blockers.
2. Pick your profile (P1/P2/P3). Delete the other two columns everywhere.
3. Populate §5 RoE template header once as an org-standard; version it in Git.
4. Stand up the artifact schemas in §7 in whatever system of record you already own. Do not
   buy a new one for this. See §9 for why.
5. Run the §13 pilot end to end **before** hiring, before purchasing, and before promising
   metrics to an executive audience. The pilot is the estimate.
