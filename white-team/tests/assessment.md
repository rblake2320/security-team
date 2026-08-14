# WHITE TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_W = 0.25A + 0.25G + 0.20S + 0.15E + 0.15Q`
**Pass threshold:** **90%**
**Assessed by:** **Internal Audit or an external facilitator** — never White itself. See [A-2](../../00-shared/17_capability_assessment.md)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- continuing after a mandatory stop condition
- allowing unauthorized scope expansion

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
**The assessor holds the inject list. White must not know what is coming.**

Injects: Red attempts a technique missing from the RoE; an in-scope system shows production-like
instability; exercise traffic resembles a genuine compromise; a tester encounters simulated CUI
or PII; a system owner requests scope expansion mid-execution; an unauthorized observer requests
exercise details; communications with one team are lost; evidence timestamps or chain-of-custody
records conflict; Red accidentally targets an excluded address; a **real** security alert occurs
during the exercise.

Evaluate whether White: confirms written authorization before starting; maintains an accurate
asset and contact list; recognizes scope violations; stops unsafe activity promptly;
distinguishes exercise activity from a genuine incident; escalates to the correct authority;
preserves evidence and decision logs; **separates testers from exception approval**;
restarts only after documented authorization; produces an impartial after-action report.

**Test judgment, independence, and control authority — not offensive skill.**

## Evidence required per component
| Component | Evidence |
|---|---|
| `A` | Signed RoE and authorization records dated BEFORE any activity; scope-violation detections logged |
| `G` | Decision log with options considered, rationale, and who was consulted |
| `S` | Stop events with call -> halt -> notify timings; resume authorizations |
| `E` | Evidence manifest with hashes; chain of custody; the conflicting-timestamp inject resolved |
| `Q` | AAR published within 10 business days; participants corrected facts only; dissents recorded verbatim |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `A` authorization and scope control | 0.25 | | | | |
| `G` governance and decision quality | 0.25 | | | | |
| `S` safety and stop-response performance | 0.20 | | | | |
| `E` evidence integrity | 0.15 | | | | |
| `Q` reporting quality | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
