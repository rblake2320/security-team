# §15 — Blue Team Integration Review

← [Index](../README.md) · Related → [§1 Operating Model](01_executive_operating_model.md) · [§3 Org & RACI](02_org_structure_and_raci.md)

**Review date:** 2026-08-14 · **Reviewer:** design integration pass
**Subject:** `blue-team/` (Sentinel Blue) as a sixth first-class team
**Verification performed:** test suite executed locally — **38 tests, 38 passed**, before and
after the folder rename. Not a claim from the README; run on 2026-08-14.

---

## 15.1 Answer first

**Blue is not missing content. Blue is missing *shape*.**

The other five teams are design documents with no implementation. Blue is a working
implementation with no charter. Each side has something the other needs:

| Direction | Gap | Action taken |
|---|---|---|
| **Blue lacked** | The four standard team files (CHARTER, PLAYBOOK, ARTIFACTS, AI_AGENT) | **Written** — see `blue-team/` |
| **The other five lacked** | Machine-readable config, an adversarial self-review, a deployment/evidence gate, SECURITY.md, and any executable validation | **Adopted** — see §15.4 |
| **Both** | `.init` manifest and `CHANGELOG.md` | **Added to all six teams** |

The materially important finding is neither of those. It is **§15.5: nine boundary conflicts**
between Sentinel Blue's operating model and the five-team model. Left unreconciled, two
documents would claim the same ownership, and in an incident the two would be discovered to
disagree at the worst possible moment.

---

## 15.2 What Blue is

| Property | Detail |
|---|---|
| Name | Sentinel Blue |
| Nature | Local-first defensive operations core — **runnable Python**, not a document set |
| Size | ~2,960 lines across `src/`, `tests/`, `docs/`, `config/`, `rules/` |
| Tests | **38, all passing** (verified 2026-08-14) |
| Modules | `canonical` · `models` · `store` · `detection` · `coverage` · `health` · `response` · `source_auth` · `assurance` · `errors` · `cli` |
| Docs | 9: architecture, operating model, threat model, IR, detection engineering, program control matrix, adversarial review, deployment checklist, references |
| Config | `coverage_target.json` (22 techniques), `rule_manifest.json`, `sensor_policy.json`, `source_trust.example.json` |
| Stated boundary | **Never performs containment, account disablement, process termination, or blocking.** Response steps are proposals requiring documented approval. |

That last line matters: **Blue's self-imposed boundary already matches this model's
human-approval requirement** for destructive action. The two designs agree on the hardest
question without having been written together.

---

## 15.3 What Blue was missing — now written

| File | Status | Note |
|---|---|---|
| `blue-team/CHARTER.md` | **Written** | Standard 17-field charter. Does not duplicate `docs/OPERATING_MODEL.md` — it defines Blue's *boundaries against the other five teams*, which the existing doc could not, because it was written before they existed. |
| `blue-team/PLAYBOOK.md` | **Written** | Points at the existing runbooks rather than restating them; adds the cross-team runbooks (deconfliction, exercise participation, finding handoff). |
| `blue-team/ARTIFACTS.md` | **Written** | Blue's artifacts are largely **machine-generated** (alerts, cases, coverage reports, health reports, audit chain) — so this file documents the *emitted* schemas and their retention/marking, rather than fill-in templates. |
| `blue-team/AI_AGENT.md` | **Written** | Triage-assistance agent. Highest-risk agent in the set, because it sits closest to live alerts. Denials are correspondingly strict. |
| Folder naming | **Fixed** | `blue team` → `blue-team`. A space in the path breaks `python -m blue_team.cli` invocations in several shells. Tests re-run green after the rename. |

---

## 15.4 What the other five teams were missing — adopted from Blue

Blue's implementation exposed five real gaps in the design-only teams:

| # | Blue has | The five lacked | Resolution |
|---|---|---|---|
| **1** | `config/coverage_target.json` — 22 techniques with priority and required telemetry | The "prioritized technique list" (metric **M-1**'s denominator) existed only as prose in [§8](07_metrics.md) and as a roadmap deliverable | **`blue-team/config/coverage_target.json` is now the single source of truth for M-1's denominator.** Purple maintains it jointly with Blue; it is version-controlled and machine-readable. This closes the most common way M-1 gets fudged — an unstated denominator. |
| **2** | `docs/ADVERSARIAL_REVIEW.md` — how the defensive system itself could be defeated | The five teams have "failure indicators" (symptoms), but no team asked *"how would an adversary defeat this function on purpose?"* | Each team's `.init` now carries an `adversarial_review` field. Orange owns producing one per team, starting with White (the highest-value target: defeat the authorization function and every other control becomes negotiable). |
| **3** | `docs/DEPLOYMENT_CHECKLIST.md` — a production evidence gate | The Green defensibility gate existed as prose in [green-team/PLAYBOOK.md](../green-team/PLAYBOOK.md); no team had a checklist an operator could actually execute | Green's gate now cross-references Blue's checklist format. Blue's is the reference implementation. |
| **4** | `SECURITY.md` | No team declared how to report a problem *in the team's own tooling or process* | Added as a program-level pointer in the root README; teams inherit it. |
| **5** | **Executable validation** (`python -m blue_team.cli validate`, 38 tests) | Design docs cannot have unit tests — but they can have structural validation, and had none | Link integrity is now checked (0 broken links across 40+ files); `.init` files are schema-shaped so they can be validated the same way. Blue proved the pattern is worth having. |

---

## 15.5 Boundary conflicts — the material finding

Sentinel Blue's `docs/OPERATING_MODEL.md` defines a ten-role blue team. Several of those roles
own work that the five-team model assigns elsewhere. **These are genuine conflicts, not wording
differences.** Each is resolved below; the resolution is now reflected in
[`blue-team/CHARTER.md`](../blue-team/CHARTER.md).

| # | Conflict | Blue's doc says | This model says | **Resolution** |
|---|---|---|---|---|
| **C-1** | **Detection engineering ownership** | Blue role "Detection engineer" owns rule quality, telemetry contracts, ATT&CK coverage, testing | Green (G1) owns the detection catalog; Purple validates (SoD-1) | **Green owns authoring and deployment. Blue owns *operational feedback*** — false positives, tuning requests, and false-negative discovery from hunts. Blue's "detection engineer" role maps to Green, staffed from the SOC. **One catalog, in Green's repo.** Blue's `rules/*.json` is the reference rule format; production rules live in Green's detection-as-code repo. |
| **C-2** | **Detection independence** | "Detection engineer samples closed alerts" as the independent check | SoD-1: the author may not be the sole party attesting the rule works | Both apply, and they are complementary: Blue's sampling checks *triage quality*; Purple's validation checks *detection efficacy*. Neither substitutes for the other. Recorded in SoD-1's note. |
| **C-3** | **Recovery and backup** | Blue role "Recovery lead" owns backup integrity, rebuild, restore | Green (G8) owns restore drills and resilience validation | **Split by mode.** Green owns *scheduled* restore drills (proactive, evidence for CP-4/CC7.5). Blue's recovery lead owns *incident-time* recovery (reactive, under IR command). Same tooling, different trigger, different owner. |
| **C-4** | **Telemetry / pipeline health** | Blue role "Security platform engineer" owns pipeline health, retention, integrations | Green (G2) owns log source onboarding and telemetry health; **M-10 is Green's foundation metric** | **Green owns the pipeline. Blue owns noticing it is broken from the consumer side.** Blue's `health` module and `sensor_policy.json` are the *detector*; Green is the *fixer*. Blue's health report is an input to M-10, not a competing measurement. |
| **C-5** | **Vulnerability management** | Blue role "Vulnerability lead" owns exposure triage and remediation validation | Yellow (Y4) owns dependency management; the model explicitly puts vuln scanning outside Purple | **Blue triages exposure and validates that a fix landed in the running environment. Yellow performs remediation.** Neither owns the scanner; that is a platform service. |
| **C-6** | **Threat hunting** | Blue role "Threat hunter" runs hypothesis-led searches | Purple owns threat-informed scenario selection and validation | **Complementary and both required.** Hunting looks for *what is already there* (past/present). Purple emulates *what could happen* (future). **A hunt finding is one of the highest-value scenario sources there is** — a confirmed hunt finding enters the Purple workflow at [stage 2](03_end_to_end_workflow.md) as Variant A (real-incident conversion). Now wired explicitly. |
| **C-7** | **Coverage measurement** | Blue's `coverage` module reports covered / partial / gap against `coverage_target.json` | Purple's M-1 measures *validated* coverage — technique executed, prevention or detection observed | **Two different claims, and the difference is the whole point.** Blue reports **declared** coverage (a rule exists and its telemetry is present). Purple reports **validated** coverage (it was tested and it fired). [§8 M-1](07_metrics.md) already requires reporting both and treating the gap between them as the interesting number. **Blue's report is now the "claimed" column; Purple's is the "validated" column.** |
| **C-8** | **Response approval** | Blue: high-risk response requires **two approvers** plus a rollback statement | Green: destructive SOAR actions require System Owner approval and documented rollback | **Adopt Blue's stricter rule everywhere.** Two-person approval plus rollback is now the standard for any destructive automated action, in both Green's SOAR playbooks and Blue's response plans. Blue's is the better-specified control; it wins. |
| **C-9** | **Audit / evidence integrity** | Blue maintains a tamper-evident hash-chained audit chain in its own store, and states plainly that it detects mutation and interior deletion but **not** rollback or deletion of the whole database | White owns the evidence manifest, chain of custody, and WORM storage | **No conflict once sequenced — they are different layers, and Blue names its own limitation honestly.** Blue's chain protects *operational* records in-place. White's WORM store provides the external anchor Blue's own README says is still required. **Action: Blue's audit chain head hash is exported to White's evidence manifest at each exercise close and at each month end.** That single line closes the rollback gap Blue correctly flagged about itself. |

**None of these conflicts required changing Sentinel Blue's code.** All nine are resolved by
assigning ownership, and in two cases (C-8, C-9) by adopting Blue's approach as the standard.

---

## 15.6 Where Blue sits in the model

Blue was already present in the design as "SOC/Blue" — it appears as a column in the
[RACI](02_org_structure_and_raci.md) and as a participant throughout the workflow. What it
lacked was a folder, a charter, and a name. The value chain now reads:

```
   ORANGE  -->  PURPLE  -->  GREEN  -->  YELLOW
   attack       validate     make it     build the
   thinking     under        observable  fix into
   pre-build    control      & defensible  the product
      ^            ^            ^            |
      |            |            |            |
      +------------+-----+------+------------+
                         |
                      BLUE  <-- operates the defense every day.
                      Consumes what Green builds. Feeds Purple what
                      actually happens. The only team that runs 24x7
                      and the only one whose day is driven by an adversary
                      rather than by a plan.
                         |
                  +------+------+
                  |    WHITE    |  authorization · safety · scoring ·
                  | (independent)|  evidence integrity · stop authority
                  +-------------+
```

**Why Blue is not simply "Green at runtime":** Green's output is *content and platform*. Blue's
output is *decisions under time pressure with incomplete information*. Purple's six-stage
outcome chain measures exactly the seam between them — stages 1–3 (prevented/logged/alerted)
grade Green's work; stages 4–6 (investigated/contained/reported) grade Blue's. **That is the
sharpest argument for keeping them separate teams: they fail differently, and the six-stage
chain already distinguishes their failures.**

---

## 15.7 Changes applied to the shared design

| File | Change |
|---|---|
| [`01_executive_operating_model.md`](01_executive_operating_model.md) | Blue added to the value chain and to the dedicated-vs-virtual decision table |
| [`02_org_structure_and_raci.md`](02_org_structure_and_raci.md) | Blue elevated from "SOC/Blue" to a named team in the org chart; SoD-1 note added (C-2); SoD-11 added for the audit-chain export (C-9) |
| [`07_metrics.md`](07_metrics.md) | M-1 denominator bound to `blue-team/config/coverage_target.json`; declared-vs-validated coverage columns named |
| [`README.md`](../README.md) | Six teams; layout updated |
| All six team folders | `.init` and `CHANGELOG.md` added |

---

## 15.8 Residual items — not fixed, flagged

| # | Item | Why it is not fixed here | Owner |
|---|---|---|---|
| **R-1** | Two PKA delivery documents — `Owner's Inbox/2026-08-13_sentinel-blue-defensive-platform.md` and `Team/tasks/20260813-sentinel-blue-defensive-platform.md` — reference `PKA testing\blue team`, which no longer exists (the folder moved under `Purple team/` and was renamed) | Editing delivery records and task files is a PKA workspace decision, not a design decision. **The references were already stale before this review**, from the move. | Owner / ATLAS |
| **R-2** | Sentinel Blue has no `CHANGELOG.md` of its own inside the code project, and no version in `pyproject.toml` matching a release | Blue now has a team-level `CHANGELOG.md`; a code-level version scheme is a project decision | Blue Lead |
| **R-3** | Blue's `rules/` and Green's future detection-as-code repo will diverge unless one is declared canonical | Requires the Green repo to exist first (roadmap Phase 2, deliverable 2.4) | Green Lead |
| **R-4** | Blue's severity model (Critical/High/Medium/Low with response objectives) has **no remediation SLA in days**; the five-team model does (7/30/90/180) | The two are compatible — Blue's is a *response* clock, the model's is a *remediation* clock — but the identical labels will be confused in conversation | Purple + Blue, at first joint exercise |
| **R-5** | `coverage_target.json` currently lists 22 techniques, weighted toward Windows endpoint and identity. The [pilot](12_pilot_exercise.md) is identity→cloud; cloud technique coverage is thinner (T1562.008, T1098, T1078 present; no T1580, T1530, T1098.001 sub-technique) | Extending it is Purple + Blue's first joint task, and should follow the threat model rather than be padded now | Purple + Blue |
