# PURPLE TEAM — Artifact Templates

Standards that apply to all artifacts (IDs, marking, retention, integrity, quality gates):
[§7](../00-shared/06_artifact_index_and_standards.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

| ID | Artifact | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| A1 | Exercise Proposal | White Exercise Director | 7 yr | INTERNAL | Exercise record system |
| A2 | Threat Scenario | Purple Lead | 7 yr | INTERNAL / CONFIDENTIAL | Exercise record system |
| A3 | ATT&CK Test Case | Purple Lead + White (safety) | 7 yr | INTERNAL | Emulation library (Git) |
| A5 | Finding | White (severity adjudication) | 7 yr after closure | INTERNAL / CONFIDENTIAL | Case management + backlog |
| A6 | Detection Gap | Green Lead (accepts) | 3 yr after closure | INTERNAL | Detection backlog (Git/issues) |
| A7 | Control Gap | System Owner + GRC | 7 yr | INTERNAL | Risk register |
| A9 | Retest Record | Purple Lead | 7 yr | INTERNAL | Exercise record + case mgmt |
| A13 | Lessons-Learned Record | System Owner / Purple Lead | 3 yr | INTERNAL | Knowledge base + backlog |

---

## A1 · Exercise Proposal

```markdown
# Exercise Proposal EX-YYYY-NNN

## Identification
Exercise name:            [M]
Proposed by:              [M]
Date:                     [M]
Risk register reference:  [M]  <- if blank, this is not a proposal
Threat scenario ref:      [M]  (A2)

## Objective
Business objective:       [M]  What decision will this inform?
Hypothesis:               [M]  Stated so it can be falsified
Success is NOT:           [M]  Explicitly exclude "red team wins"
Learning objectives:      [R]

## Scope
In-scope systems:         [M]  asset ID | named owner | environment | classification
Excluded:                 [M]
Environment:              [M]  lab / dev / pre-prod / prod (+ justification if prod)
Proposed window:          [M]
Blackout constraints:     [M]

## Technical plan
ATT&CK techniques:        [M]  technique + sub-technique IDs
Test case count (est.):   [M]
Tools required:           [M]
Identities required:      [M]  count, privilege level, who issues
Third parties involved:   [M]  yes/no -> if yes, RoE 5.15 applies

## Participants
Purple / Red / Blue / Green / Orange / White / System owners / SOC: [M] named

## Effort and evidence
Estimated effort (pd):    [M]
Expected evidence:        [M]
Expected findings types:  [R]

## PRE-DECLARED SCORING CRITERIA  [M]
Process score (60%):      [M] criteria + points
Outcome score (40%):      [M] criteria + points
Pass threshold:           [M]
> These may not be changed after execution begins.

## Safety summary
Worst credible outcome:   [M]
Rollback exists for every state-changing case: [M] yes/no
Production dependencies:  [M]

## Approvals
Purple Lead: ____  White Exercise Director: ____  Date: ____
```

---

## A2 · Threat Scenario

```markdown
# Threat Scenario TS-YYYY-NNN

Title:                    [M]
Basis:                    [M]  CTI report / real incident / risk register entry / sector advisory
Actor or actor-class:     [M]  named actor OR "commodity/opportunistic" -- do not invent attribution
Confidence in basis:      [M]  confirmed / probable / possible
Relevance to us:          [M]  why THIS org, THIS system

## Behavior chain
Step | Tactic | Technique | Description | Our exposure | Existing control
-----|--------|-----------|-------------|--------------|------------------
1    |        |           |             |              |

## Assumptions
[M] What we are assuming the adversary already has (initial access, credentials, etc.)
    -- "assumed breach" starting position must be explicit

## Out of scope for emulation
[M] Behaviors in the chain we will NOT emulate, and why (safety, authorization, feasibility)

## Detection expectations
[M] Which steps we believe we detect today, and on what evidence

Author: ____  Reviewed by (CTI): ____  Approved (Purple Lead): ____
Marking: INTERNAL, or CONFIDENTIAL if it names a real actor targeting this organization
```

---

## A3 · ATT&CK Technique Test Case

Stored as code in the emulation library. One file per test case.

```yaml
id: TC-2026-014-007            # [M]
exercise_id: EX-2026-014       # [M]
name: "Password spraying against cloud identities"   # [M]
attack:                        # [M]
  tactic: TA0006
  technique: T1110.003
  technique_name: "Brute Force: Password Spraying"
environment: lab               # [M] lab | dev | pre-prod | prod
safety_class: low              # [M] low | medium | high  (high requires named White approval)

prerequisites:                 # [M]
  - "40 synthetic accounts provisioned in lab tenant"
  - "Source host registered in deconfliction record"

identity_required:             # [M]
  type: unauthenticated
  privilege: none

procedure:                     # [M] exact, reproducible, reviewable steps
  - step: 1
    action: "Attempt authentication against each synthetic account"
    parameters:
      attempts_per_account_per_hour: 5
      account_count: 40
      duration_hours: 3
      source: "10.44.7.19 (registered)"
    rate_limit_enforced_by: ["procedure", "lab tenant lockout policy"]

expected_telemetry:            # [M] -- predicted BEFORE execution
  - source: "Cloud IdP sign-in logs"
    signal: "Repeated failures, >=5 distinct accounts, single source IP"
    fields: [userPrincipalName, ipAddress, userAgent, resultType]
    latency_target_minutes: 5

expected_detection:            # [M] rule ID, or the string "none - suspected gap"
  - "none - suspected gap"

blast_radius: "Synthetic lab accounts only. No production federation."   # [M]

rollback:                      # [M]
  steps: ["Unlock any locked synthetic accounts", "Revoke exercise identities"]
  verified_time_minutes: 5
  last_verified: "2026-08-20"

cleanup:                       # [M]
  artifacts_created: ["lockout state on synthetic accounts"]
  verification_by: "non-operator"

stop_conditions:               # [M] in addition to RoE 5.13
  - "Any attempt observed against a production identity"
  - "Lockout affecting any account outside the synthetic set"

lab_dry_run:                   # [M]
  performed: true
  date: "2026-09-02"
  result: "as expected"

automatable: true              # [R] -> candidate for the CI regression suite
regression_test_id: null
```

---

## A5 · Finding

Structured form: [§6.4.2](../00-shared/05_communication_protocol.md). Narrative wrapper:

```markdown
# Finding FND-YYYY-NNNN

Title:            [M]  Describe the WEAKNESS, not the exploit
Type:             [M]  vulnerability | detection_gap | control_gap | process_gap
                       | telemetry_gap | response_gap
Severity:         [M]  critical | high | medium | low | informational
Severity inputs:  [M]  exploitability / impact / exposure / compensating controls
                       + rubric version   <- record the INPUTS, not just the result
Exercise:         [M]
ATT&CK:           [M]
Affected assets:  [M]
System owner:     [M]  named human
Remediation owner:[M]  named human, not a team

## Six-stage outcome  [M]
prevented / logged / alerted / investigated / contained / reported

## Evidence  [M]
EV-refs with hashes. Gate G4: no evidence -> not a finding.

## Description  [M]
What is wrong. Written so an engineer who was not present can understand it.

## Reproduction  [M]
Test case ID + any additional context needed to reproduce.

## Business impact  [M]
Written for the system owner, in their terms. Not "T1098.001 is possible."

## ACCEPTANCE CRITERIA  [M]  -- Gate G5
Testable conditions. Each must be verifiable by re-running the test case or by a
query producing a specific result. Example:
  1. Detection fires within 15 min for >=10 failed auths across >=5 accounts
     from one source within 1 hour
  2. Alert routes to the SOC queue at severity >= medium
  3. Purple re-executes TC-2026-014-007 verbatim and observes the alert
  4. Detection is deployed to PRODUCTION and its source log is live

Target date:      [M]  derived from severity SLA
Status:           [M]
Linked tickets:   [M]
Classification:   [M]
```

---

## A6 · Detection Gap

```markdown
# Detection Gap GAP-YYYY-NNNN

Source finding:            [M]
ATT&CK technique(s):       [M]
Required data source(s):   [M]
Data source available:     [M] yes / no
  -> if NO, this is a TELEMETRY gap first. Raise A7 Control Gap for the log source
     and note that detection work is blocked. Do not assign detection work that
     cannot succeed.
Proposed logic (summary):  [R]  behavior, not signature
Expected FP drivers:       [M]  name them now; they determine whether this is viable
Estimated alert volume:    [R]
Priority:                  [M] P1 (high fidelity, low noise, high impact) .. P4
Assigned to:               [M] Green
Target deploy date:        [M]
Detection ID (once built): 
Validated by Purple:       [ ] date ____   <- SoD-1: Green does not self-attest
Deployed to production:    [ ] date ____   <- lab-only deployment does not close this
```

**Prioritization heuristic:** build the high-fidelity, low-volume detections first (e.g.
credential added to a workload identity). They cost little to operate and buy immediate
credibility. Save the noisy behavioral detections for when tuning capacity exists.

---

## A7 · Control Gap

```markdown
# Control Gap CG-YYYY-NNNN

Source:                  [M] finding / threat model / exercise observation
Control expected:        [M] what should exist (reference the framework control ID if applicable)
Control actual:          [M] what exists today
Gap type:                [M] absent | misconfigured | not deployed to all assets
                              | not monitored | not tested
Affected scope:          [M] asset count / percentage
Framework references:    [R] e.g. NIST 800-53 SI-4, ISO A.8.16
Business impact:         [M]
Remediation options:     [M] with rough effort and cost for each
Recommended option:      [M]
Owner:                   [M] System Owner
Risk register entry:     [M]
Status:                  [M] open | in_remediation | risk_accepted | closed
```

---

## A9 · Retest Record

Structured form: [§6.4.4](../00-shared/05_communication_protocol.md).

```markdown
# Retest RT-YYYY-NNNN

Finding:                        [M]
Test case re-executed:          [M]
Procedure identical to original:[M] yes / no
  -> if NO, state exactly why the original is no longer possible.
     A modified procedure proves something else and does not close a finding.
Environment:                    [M] must match the original
Retest date:                    [M]
Performed by:                   [M] Purple (not the person who wrote the fix -- SoD-3)

Original outcome (six stages):  [M]
Retest outcome (six stages):    [M]
Delta:                          [M]
Time to detect (if detected):   [R]

Verdict:                        [M] closed | partially_remediated | not_remediated | regressed
Evidence:                       [M]
Regression test added:          [M] yes -> ID ____ | no -> reason ____
Production deployment verified: [M] yes / no / n-a
```

---

## A13 · Lessons-Learned Record

```markdown
# Lesson LL-YYYY-NNNN

Exercise / incident:  [M]
Observation:          [M]  What actually happened
Classification:       [M]  SUSTAIN (keep doing) | IMPROVE (fix here)
                            | SYSTEMIC (affects multiple systems)
Root cause:           [R]  Where known. Do not force a root cause you do not have.
Recommendation:       [M]
Owner:                [M]  named human
Due date:             [M]
Work item:            [M]  backlog ID   <- Gate: a lesson without a work item is a feeling
Routing:              [M]  Green (paved road) | Orange (design pattern) | Yellow (code)
                            | White (process) | L&D (training)
Status:               [M]
```

**Systemic lessons rule:** if the same lesson appears in three exercises, it is not a lesson —
it is an unfunded structural problem. Escalate it to the Risk Committee with the three
references attached, rather than logging it a fourth time.
