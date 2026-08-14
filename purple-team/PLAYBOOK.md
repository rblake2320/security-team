# PURPLE TEAM — Playbook

Day-to-day operating procedure. Derived from [§4 workflow](../00-shared/03_end_to_end_workflow.md),
[§6 comms](../00-shared/05_communication_protocol.md), [§8 metrics](../00-shared/07_metrics.md).

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

---

## 1. Workflow stages Purple owns

| Stage | Purple's role | Gate Purple enforces |
|---|---|---|
| 1 · Risk/threat selection | R (GRC accountable) | Every scenario traces to a risk-register ID |
| 2 · Exercise proposal | **A** | Scoring criteria written **before** execution |
| 4 · RoE approval | C (White accountable) | Technical accuracy of scope and technique list |
| 6 · Test-case development | **A** | Every case dry-run in lab; expected telemetry predicted |
| 8 · Execution | **A** | **G — no action outside the approved test-case set** |
| 9 · Detection/control validation | **A** | Six-stage outcome recorded for every case, with evidence |
| 10 · Finding classification | R (White adjudicates) | **G4 — no evidence, no finding** |
| 12 · Retesting | **A** | **G6 — verbatim retest, or record why not** |
| 17 · Backlog/roadmap update | **A** (with Green) | Intake:closure ratio reported |

Full entry/exit criteria: [§4](../00-shared/03_end_to_end_workflow.md).

---

## 2. Weekly rhythm

| Day | Activity | Output |
|---|---|---|
| Mon | Backlog triage; check intake:closure ratio; review overnight regression failures | Prioritized week |
| Tue | Test-case development / emulation library work | Test cases in Git |
| Wed | Bi-weekly: retest batch (alternating with detection backlog grooming with Green) | Retest records |
| Thu | Exercise execution window (when scheduled) or threat-informed prioritization prep | — |
| Fri | Findings write-up; metrics refresh; scenario pipeline grooming | Updated pipeline |
| Monthly | Threat-informed prioritization meeting; Exercise Review Board; metrics pack | Ranked candidates, approved RoEs |

---

## 3. Runbook — proposing an exercise

```
1. Pick from the ranked candidate list. Confirm the risk-register ID.
2. Identify in-scope systems from the asset inventory. Identify the NAMED owner.
3. Informally pre-notify the system owner. ("I'm going to propose testing X.
   Any windows I should avoid?")  -- this single step removes most authorization delay.
4. Draft the Exercise Proposal (ARTIFACTS.md A1). Include:
      - hypothesis, stated so it can be falsified
      - what does NOT count as success
      - pre-declared scoring criteria
5. Submit to the Exercise Review Board >= 10 business days before the desired window.
6. Support White through RoE drafting. Do NOT draft the RoE yourself -- White owns it.
7. On approval, book the window in the exercise calendar and open the #ex-<ID>-ops channel.
```

**Common rejection reasons — pre-empt them:** no risk-register trace · system owner not
identified · scoring criteria missing · production scope without justification · window collides
with a change freeze · no rollback for a state-changing case.

---

## 4. Runbook — executing an exercise

```
T-2 days   Pre-exercise brief. Re-verify contact roster BY LIVE CALL.
           Confirm SOC is in normal ops (not handling a real incident).
T-1 day    Exercise identities issued (by the identity owner, not by us).
           Source infrastructure registered with SOC leadership.
           Final lab dry-run of any case not run in the last 30 days.
T-0 09:00  Go/no-go with White. Post daily update. Confirm scribe present.
During     - One operator acts at a time unless the RoE says otherwise
           - Scribe records every action with UTC timestamp
           - Every artifact created is logged AT CREATION for cleanup
           - Any deviation -> written White approval BEFORE acting, in #ex-<ID>-ops
           - Deconfliction queries answered in <5 min, logged as events
T-0 17:00  Daily update. Handoff if crossing a shift boundary.
End        Cleanup checklist. Verification by someone who is NOT the operator.
           Identity revocation confirmed by the identity owner.
```

**If anything unexpected happens: stop first, think second.** The cost of an unnecessary stop is
an hour. The cost of continuing into an unknown state is an incident.

---

## 5. Runbook — the collaborative validation session

The highest-value four hours in the entire program. Protect them.

```
SETUP     Red, Blue, Green, Orange, Purple, scribe in one room (or one call).
          Timeline on screen. SIEM on screen. Nobody presents slides.
RULES     - Red discloses exactly what was done, when, from where, as which identity
          - Blue discloses exactly what was seen, and what they did with it
          - No withholding to protect a score, on either side
          - Findings are about SYSTEMS. Never about people. Enforce this immediately
            and visibly the first time it slips.
PER CASE  Walk the six stages: prevented / logged / alerted / investigated /
          contained / reported. Capture evidence reference for each.
          Compare PREDICTED telemetry to OBSERVED. The delta is a finding.
OUTPUT    Six-stage table complete for every case, with evidence refs.
          Draft findings with proposed severity.
          Detection gaps handed to Green with the required data source named.
ANTI-PATTERN  Scoring only "did the alert fire". Stage 4 (was it triaged correctly)
          is where most real-world failures live.
```

---

## 6. Runbook — severity assignment

Record the inputs, not just the output, so severity changes are auditable.

| Input | Scale | Notes |
|---|---|---|
| Exploitability | trivial / moderate / difficult | Would a commodity attacker do this? |
| Impact | critical / high / medium / low | Against the business, not against the system |
| Exposure | internet / internal / privileged-only | Who can reach it |
| Compensating controls | none / partial / strong | Must be *verified*, not assumed |

Default mapping (adjust per O-3): trivial+critical+internet → **Critical** ·
moderate+high+internal → **High** · difficult+medium+privileged → **Medium** · otherwise **Low**.

**Rule:** if you find yourself arguing about severity for more than 10 minutes, escalate to White.
That is exactly what White adjudication exists for, and hallway negotiation is how severity
quietly drifts down.

---

## 7. Escalation and stop

| Situation | Action |
|---|---|
| Technical problem, no safety implication | Purple Lead resolves |
| Unexpected system behavior | **Stop.** Notify White. Assess. |
| Suspected real incident | **Stop.** White adjudicates. CSIRT if real. |
| Deconfliction contact unreachable >15 min | **Stop.** |
| Scope ambiguity | **Stop.** Never resolve scope ambiguity in your own favor. |
| Severity dispute | Escalate to White |
| Remediation not happening | Escalate to System Owner, then Risk Committee — not to the engineer |

---

## 8. Metrics Purple owns

M-1 ATT&CK coverage · M-2 prevention rate · M-3 detection rate · M-4 MTTD · M-8 retest success ·
M-9 recurrence · M-12 findings by severity and age · M-13 regression conversion.
Formulas and decision-linkage: [§8](../00-shared/07_metrics.md).

**The two Purple must never let slide:**
- **M-12 intake:closure ratio.** >1.0 sustained → slow cadence, fund remediation. Report it.
- **M-13 regression conversion.** This is the compounding mechanism. Everything else is one-time.

---

## 9. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Scenarios chosen because a tool supports them | Every scenario traces to a risk-register ID |
| Purple writes and deploys its own detections | Green builds, Purple validates. Otherwise you grade your own homework. |
| Blind testing by default | Blind is the exception, White-designated, with a stated learning objective |
| Retesting with an "improved" test case | Verbatim, always |
| Reporting technique counts | Report validated coverage against the prioritized list |
| Running more exercises when the backlog is saturated | Slow down; fund Green/Yellow; say so |
| Findings that end in a PDF | Gate G5: no testable acceptance criteria, no finding |
