# PURPLE TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_P = 0.20C + 0.25D + 0.20R + 0.20V + 0.15K`
**Pass threshold:** **80%**
**Assessed by:** White Exercise Director (Purple is a participant and cannot score itself — SoD-4)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- any unresolved critical detection gap at exercise close

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
Three phases, in order:

1. **Blind baseline** against ~10-15 threat-relevant ATT&CK techniques.
   **White must designate this as a blind phase in the RoE** with a stated learning objective and
   an end time — the Purple charter is collaborative-by-default, so an informal blind run is a
   charter violation, not a test-design choice.
2. **Open collaborative session.** Red explains each action; Blue verifies telemetry, detections,
   and response. The blind period ends here and never extends into validation.
3. **Rerun the identical test cases** under identical conditions after gaps are fixed.

Record per technique: technique + test-case ID, business asset and threat hypothesis,
preconditions, start/stop timestamps, expected controls, expected telemetry, prevented?,
telemetry generated?, alert fired?, alert accuracy and severity, investigation and containment
actions, detection/investigation/containment times, remediation ticket, retest result.

## Evidence required per component
| Component | Evidence |
|---|---|
| `C` | Channel archive showing Red-Blue exchange; validation-session record; no withheld detail |
| `D` | Test-case set mapped to the prioritized technique list; six-stage outcomes with evidence for every case |
| `R` | Remediation tickets with named owners and testable acceptance criteria; SLA status |
| `V` | Retest records — original procedure re-executed verbatim, with the delta |
| `K` | Findings legible to an engineer who was not present; emulation library updated; lessons routed with owners |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `C` collaboration and communication | 0.20 | | | | |
| `D` detection-validation coverage | 0.25 | | | | |
| `R` remediation completion | 0.20 | | | | |
| `V` successful retest validation | 0.20 | | | | |
| `K` documentation and knowledge transfer | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
