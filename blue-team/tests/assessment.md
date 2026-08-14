# BLUE TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_B = 0.25T + 0.25R + 0.20E + 0.15D + 0.15F`
**Pass threshold:** **85%**
**Assessed by:** Purple (six-stage stages 4-6) + White (evidence and deconfliction log)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- SOC stood down during the exercise window
- a real-vs-exercise ambiguity resolved as 'exercise' without certainty

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
**Operate normally. That is the test.** Blue is told a window exists; Blue is not told the plan.
Registered indicators go to the SOC lead only, sealed.

Assessed live during the integrated exercise. The two automatic failures are not severity
judgments — they are the behaviours that make every other Blue number meaningless.

## Evidence required per component
| Component | Evidence |
|---|---|
| `T` | Six-stage stage 4 per alert: correct / misclassified / not triaged, with the reasoning |
| `R` | MTTI and MTTC measured FROM THE ADVERSARY ACTION, not from the alert; containment approvals with rollback |
| `E` | Evidence preserved BEFORE destructive action, with acquisition method; incident record passes the B14 closure gate |
| `D` | Deconfliction log: every query answered within 5 min; ambiguity resolved as REAL |
| `F` | False positives and false negatives routed to Green; incidents routed to Purple within 30 days |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `T` triage correctness (six-stage stage 4) | 0.25 | | | | |
| `R` response and containment performance (MTTI/MTTC) | 0.25 | | | | |
| `E` evidence preservation and incident-record quality | 0.20 | | | | |
| `D` deconfliction discipline | 0.15 | | | | |
| `F` feedback-loop closure to Green and Purple | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
