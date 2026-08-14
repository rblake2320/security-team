# ORANGE TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_O = 0.25X + 0.20P + 0.20E + 0.20T + 0.15N`
**Pass threshold:** **80%**
**Assessed by:** Purple (what the exercise later found) + Yellow (usefulness survey)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- any seeded critical attack path missed
- any unsafe testing performed
- any critical recommendation without actionable acceptance criteria

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
Give Orange a nearly finished architecture **without showing it the known findings.**
Seed a known set of critical attack paths so discovery is measurable.

Required output: trust-boundary diagram; data-flow diagram; asset and privilege inventory;
abuse cases; attack trees; identity and authorization attack paths; API and business-logic
weaknesses; cloud and CI/CD attack paths; AI-specific abuse cases if applicable; ranked
engineering recommendations; safe proof-of-concept tests; automated regression-test proposals;
developer briefing.

**Finding weaknesses alone is insufficient** — E + T + N together outweigh X, because the role
exists to change what gets built, not to produce a list.

## Evidence required per component
| Component | Evidence |
|---|---|
| `X` | Seeded critical paths found, with the reasoning; paths found beyond the seeded set |
| `P` | Ranking matches feasibility x impact on independent review; no critical buried under noise |
| `E` | Recommendations Yellow accepted and implemented without rework; acceptance criteria testable |
| `T` | Safe regression tests that FAIL against the vulnerable state and PASS against the fixed state; no exploitation |
| `N` | Developer briefing delivered; usefulness survey >= 4/5; teams invite Orange earlier next time |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `X` attack-path discovery | 0.25 | | | | |
| `P` prioritization accuracy | 0.20 | | | | |
| `E` engineering usefulness | 0.20 | | | | |
| `T` conversion into safe tests | 0.20 | | | | |
| `N` developer knowledge transfer | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
