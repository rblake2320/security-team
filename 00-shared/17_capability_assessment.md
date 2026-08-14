# §18 — Capability Assessment: Testing the Teams

← [Index](../README.md) · Related → [§13 Pilot](12_pilot_exercise.md) · [§8 Metrics](07_metrics.md) · [§5 RoE](04_rules_of_engagement_template.md)

**Purpose:** assess whether each team can actually do its job — through **one controlled,
end-to-end scenario**, not isolated quizzes.

**Source:** the scorecard framework, per-team tests, weightings, and readiness scale in §18.3–§18.6
were supplied by the program owner on 2026-08-14 and are adopted **as written**. Sections marked
**[EXT]** are extensions added during integration: Blue and Red scorecards, the reweighted program
formula, and three reconciliations against the existing charters.

---

## 18.1 Strategy

> Use a cyber range or non-production environment, establish a baseline, run a collaborative
> improvement cycle, then **repeat the exact tests** to prove measurable improvement.

**Representative scenario:**

> A synthetic user account is compromised. The attacker attempts privilege escalation, accesses
> an internal API, and tries to retrieve simulated CUI from a test database.

White authorizes and controls. Orange analyzes attack paths. Yellow fixes the product. Green
builds defenses and telemetry. Red executes. Blue operates the defense. Purple validates the
complete attack → detect → remediate → **retest** loop.

**The exercise concludes with remediation and an exact retest — not a findings report.** That
single rule is what separates an assessment from theater, and it is the same rule as workflow
gate **G6**.

---

## 18.2 Three reconciliations against the charters **[EXT]**

The framework as supplied interacts with three existing rules. Resolve these *before* running it,
or two documents will contradict each other mid-exercise.

| # | Interaction | Resolution |
|---|---|---|
| **A-1** | The framework opens with a **"partially blind baseline"** for Purple. The [Purple charter](../purple-team/CHARTER.md) requires collaborative transparency **by default**, with blind phases permitted only when White designates them. | **Compatible, with one condition: White must designate the baseline as a blind phase in the RoE**, with a stated learning objective and a defined end time. The blind period ends before the collaborative session — it never extends into validation. Do not run a blind baseline informally. |
| **A-2** | **"Do not tell the White Team which governance problems will be injected."** But White normally holds the answer key and controls the exercise. **Who injects surprises at the referee?** | **RESOLVED — the [Exercise Assurance Authority](18_exercise_assurance.md) (§19).** A *role*, not an eighth colour team, performed by Internal Audit, an external facilitator, or a framework-named assessor. **White still controls the exercise; Exercise Assurance assesses how White performed that control.** Its permissions are limited to six things (hold the sealed injects, observe, validate evidence, score White, sign the result, report interference). Without it, the White scorecard is self-graded and the 90% threshold is meaningless. |
| **A-3** | Scorecards must not be adjusted after the fact. | Already covered — [§13.12](12_pilot_exercise.md) requires scoring criteria to be **published before execution and frozen at execution start**. Publish the §18.4 weights in the exercise proposal, not afterward. |

---

## 18.3 Tests by team

| Team | Best test | What success looks like |
|---|---|---|
| **Purple** | ATT&CK-based detection-validation exercise | Reproducible test cases, Red/Blue coordination, identified gaps, assigned remediation, successful retesting |
| **White** | Exercise-control simulation with **surprise safety injects** | Correct authorization, scope control, deconfliction, stop decisions, evidence integrity, independent reporting |
| **Yellow** | Secure product-delivery challenge | A feature passes security requirements, threat-model findings, automated checks, and adversarial regression tests |
| **Green** | Defensibility and observability acceptance test | The platform blocks or detects selected techniques and provides sufficient telemetry for investigation |
| **Orange** | Pre-production adversarial design review | Attack paths identified before release and converted into engineering requirements and regression tests |
| **Blue** **[EXT]** | Live-operations test under exercise conditions | Correct triage without standing down, disciplined deconfliction, evidence preserved before containment, feedback routed to Green and Purple |
| **Red** **[EXT]** | Authorization-and-containment assessment | Every action under a valid receipt, zero out-of-scope events, ledger verifies and seals, findings reproducible without Red present |

---

## 18.4 Scorecards

### Purple — `S_P = 0.20C + 0.25D + 0.20R + 0.20V + 0.15K`
`C` collaboration and communication · `D` detection-validation coverage · `R` remediation
completion · `V` successful retest validation · `K` documentation and knowledge transfer.
**Pass: 80%, with no unresolved critical detection gap.**

Run in three phases: **(1)** partially blind baseline against ~10–15 threat-relevant ATT&CK
techniques (White-designated per A-1); **(2)** open collaborative session where Red explains each
action and Blue verifies telemetry, detections, and response; **(3)** fix the gaps and rerun the
same test cases under identical conditions.

**Record per technique:** technique and test-case ID · business asset and threat hypothesis ·
preconditions · start/stop timestamps · expected controls · expected telemetry · prevented? ·
telemetry generated? · alert fired? · alert accuracy and severity · investigation and containment
actions · detection / investigation / containment times · remediation ticket · retest result.

> This record is a superset of the [six-stage outcome chain](12_pilot_exercise.md) — it adds
> preconditions, expected controls, and alert accuracy. **Adopt the fuller version**; it is
> strictly better, and the extra fields are exactly what distinguishes "detection failed" from
> "we were watching the wrong data."

### White — `S_W = 0.25A + 0.25G + 0.20S + 0.15E + 0.15Q`
`A` authorization and scope control · `G` governance and decision quality · `S` safety and
stop-response performance · `E` evidence integrity · `Q` reporting quality.
**Pass: 90%. Automatic failure for continuing after a mandatory stop condition, or allowing
unauthorized scope expansion.**

**Injects (held by the independent assessor per A-2, not by White):**
Red attempts a technique missing from the RoE · an in-scope system shows production-like
instability · exercise traffic resembles a genuine compromise · a tester encounters simulated CUI
or PII · a system owner requests scope expansion mid-execution · an unauthorized observer requests
exercise details · communications with one team are lost · evidence timestamps or chain-of-custody
records conflict · Red accidentally targets an excluded address · a **real** security alert occurs
during the exercise.

**Evaluate whether White:** confirms written authorization before starting · maintains an accurate
asset and contact list · recognizes scope violations · stops unsafe activity promptly ·
distinguishes exercise activity from a genuine incident · escalates to the correct authority ·
preserves evidence and decision logs · **separates testers from exception approval** ·
restarts only after documented authorization · produces an impartial after-action report.

> Test White's **judgment, independence, and control authority — not its offensive skill.**

### Yellow — `S_Y = 0.25B + 0.20T + 0.20P + 0.20F + 0.15M`
`B` secure design and build quality · `T` automated testing · `P` pipeline and supply-chain
controls · `F` remediation quality · `M` maintainability and documentation.
**Pass: 85%, no open critical findings, and every high-severity finding covered by an automated
regression test or a documented compensating control.**

**Challenge:** *build an API that lets authorized project members retrieve records containing
synthetic CUI while preventing cross-project access.* Give functional requirements; **do not
disclose every expected weakness.**

Tests: authentication · authorization · **object-level access control** · input validation ·
error handling · secrets management · dependency integrity · logging without sensitive-data
leakage · database permissions · IaC · CI/CD controls · SBOM · unit/integration/security
regression tests · threat-model completion · remediation turnaround.

Gauntlet: code review · SAST and secret scanning · dependency and container scanning · IaC policy
checks · DAST/API testing · manual Orange abuse-case review · Green observability validation.

### Green — `S_G = 0.20H + 0.25O + 0.25D + 0.15R + 0.15L`
`H` hardening · `O` observability · `D` detection effectiveness · `R` response and recovery
readiness · `L` lifecycle integration.
**Pass: 85%, 100% telemetry coverage for critical assets, and detection or prevention of every
designated must-detect technique.**

**Injects:** repeated authentication failures · suspicious privilege assignment · abnormal API
enumeration · access from an unusual workload identity · attempted cross-project record access ·
unexpected process execution · security-agent interruption · **logging pipeline failure** ·
database query-volume anomaly · backup or recovery failure.

Provide: required host/identity/application/API/cloud/database telemetry · time synchronization
and consistent identifiers · correctly configured preventive controls · actionable alerts with
context · dashboards · runbooks with containment and recovery steps · detection-as-code under
version control · tested backup and rollback · **monitoring for telemetry failure itself** ·
evidence the control works after deployment.

### Orange — `S_O = 0.25X + 0.20P + 0.20E + 0.20T + 0.15N`
`X` attack-path discovery · `P` prioritization accuracy · `E` engineering usefulness ·
`T` conversion into safe tests · `N` developer knowledge transfer.
**Pass: 80%, discovery of all seeded critical attack paths, no unsafe testing, and actionable
acceptance criteria for every critical recommendation.**

Give Orange a nearly finished architecture **without showing it the known findings.** Require:
trust-boundary diagram · data-flow diagram · asset and privilege inventory · abuse cases · attack
trees · identity and authorization attack paths · API and business-logic weaknesses · cloud and
CI/CD attack paths · AI-specific abuse cases if applicable · ranked engineering recommendations ·
safe proof-of-concept tests · automated regression-test proposals · developer briefing.

> **Finding weaknesses alone is insufficient.** Orange is scored on translating attacker thinking
> into changes Yellow can implement — which is why `E` + `T` + `N` together outweigh `X`.

### Blue — `S_B = 0.25T + 0.25R + 0.20E + 0.15D + 0.15F` **[EXT]**
`T` triage correctness (six-stage stage 4) · `R` response and containment performance (MTTI/MTTC) ·
`E` evidence preservation and incident-record quality · `D` deconfliction discipline ·
`F` feedback-loop closure (FP/FN to Green, incidents to Purple).
**Pass: 85%. Automatic failure if the SOC stood down during the exercise window, or if a
real-vs-exercise ambiguity was resolved as "exercise" without certainty.**

Those two auto-fails are not severity judgments — they are the two behaviours that make every
other Blue number meaningless.

### Red — `S_R = 0.30A + 0.25S + 0.20X + 0.15E + 0.10K` **[EXT]**
`A` authorization discipline · `S` scope containment · `X` execution fidelity (cases executed as
authored; failures reported honestly) · `E` evidence integrity (ledger verifies and seals) ·
`K` knowledge transfer (findings reproducible without Red present).
**Pass: 90%. Automatic failure for any run without a valid unexpired receipt, any out-of-scope
action, any unredacted secret in output, or the signing key found on an operator machine.**

Weighted toward `A` and `S` deliberately: Red's catastrophic failure mode is **unauthorized
access**, not missed findings.

---

## 18.5 Integrated exercise — order of operations

1. **White** approves the scenario, scope, safety controls, and evidence plan
2. **Orange** threat-models the target and predicts likely attack paths
3. **Yellow** delivers the application and its security evidence
4. **Green** deploys hardening, telemetry, detections, and response procedures
5. **Purple** executes the baseline ATT&CK test cases *(via **Red**, under an Aegis receipt — **[EXT]**)*
6. **White** introduces governance, safety, and deconfliction events
7. **Purple** records prevention, detection, investigation, and response results *(with **Blue** operating live and not standing down — **[EXT]**)*
8. **Yellow** remediates product defects
9. **Green** fixes control, telemetry, and detection gaps
10. **Orange** reviews whether the remediation closes the **complete** attack path
11. **Purple** reruns the identical test cases
12. **White** verifies evidence and independently scores the exercise *(and is itself scored by the independent assessor per A-2 — **[EXT]**)*

**Conditions [M]:** cyber range · synthetic identities · simulated sensitive data · test-only
credentials · predefined stop conditions. **No production exploitation for an initial maturity
assessment.**

---

## 18.6 Overall readiness

**As supplied (five teams):**
```
S_program = 0.25·S_P + 0.25·S_W + 0.20·S_Y + 0.15·S_G + 0.15·S_O          (= 1.00)
```

**Extended to seven — `baseline-v1`, ratified 2026-08-14.** The original five are scaled by 0.75;
the two new teams take 0.25 between them, weighted toward Blue because it operates continuously.

| Team | Weight | | Team | Weight |
|---|---|---|---|---|
| Purple | **18.75%** | | Green | **11.25%** |
| White | **18.75%** | | Orange | **11.25%** |
| Blue | **15.00%** | | Red | **10.00%** |
| Yellow | **15.00%** | | **Total** | **100.00%** |

```
S_program = 0.1875·S_P + 0.1875·S_W + 0.1500·S_Y + 0.1125·S_G
          + 0.1125·S_O + 0.1500·S_B + 0.1000·S_R                    (= 1.0000)
```

> **These are governance defaults, not empirically validated weights.** Blue's continuous
> operation supports its higher weight, but future weights should be driven by **mission risk and
> exercise objectives**, and revised only through a **versioned governance change** after several
> exercises have produced a score distribution. Do not tune them per exercise.

### Evaluation order **[M]** — auto-fail is applied *before* aggregation

```
if any(team.auto_fail for team in teams):
    program_status  = "FAILED"
    weighted_score  = calculated_for_diagnostics_only
elif evidence_completeness < required_threshold:
    program_status  = "INSUFFICIENT_EVIDENCE"
else:
    program_status  = score_to_readiness(weighted_score)
```

**Why the order matters:** a weighted mean is not a safety property. Without this, a catastrophic
Red failure (an out-of-scope action) or a White failure (continuing after a mandatory stop) is
averaged away by strong performance elsewhere, and the program reports "mature" while having
demonstrated it cannot be trusted to run an exercise safely. **One auto-fail fails the program.**
The weighted score is still computed — it is diagnostically useful — but it is not the status.

**`INSUFFICIENT_EVIDENCE` is a real outcome, not a soft fail.** Evidence completeness is
determined by [Exercise Assurance](18_exercise_assurance.md), not by the teams being scored.

### Readiness bands

| Score | Readiness |
|---|---|
| Below 60% | Capability is informal or unsafe |
| 60–74% | Developing; requires supervised exercises |
| 75–84% | Operational with identifiable weaknesses |
| 85–94% | Mature and repeatable |
| **95–100%** | **MANDATORY CHALLENGE REVIEW** — see below |

### The 95–100% challenge review **[M]**

A near-perfect score triggers a review whose job is to **disprove** the flattering explanation.
Four hypotheses, all of which must be examined:

1. The organization is genuinely mature.
2. **The test lacked difficulty.**
3. **Telemetry or process leaked the scenario** to participants.
4. **Scoring was too permissive.**

> **A 95–100% result never automatically means "no more testing needed."**

Same logic as metric [M-15](07_metrics.md), where a 0% safety-stop rate is a finding about your
culture rather than a clean record. The correct response to a very high score is a harder test,
not a smaller budget.

### Exit criteria that matter more than the percentage

The framework says this and it is worth repeating verbatim, because it is the part people skip:

- No uncontrolled critical risk
- Documented authorization
- Successful remediation
- Preserved evidence
- **A repeatable retest demonstrating that security actually improved**

A program scoring 78% with all five satisfied is in better shape than one scoring 91% without
them.

---

## 18.7 Machine-readable scorecards

Each team's weights, thresholds, and automatic-failure conditions are in
`<team>/config/scorecard.json`, so scores are computed the same way twice and cannot be quietly
adjusted after execution. The assessment checklist and evidence requirements for each team are in
`<team>/tests/assessment.md`.
