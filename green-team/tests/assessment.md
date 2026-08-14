# GREEN TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_G = 0.20H + 0.25O + 0.25D + 0.15R + 0.15L`
**Pass threshold:** **85%**
**Assessed by:** Purple (detection efficacy) + White (evidence)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- telemetry coverage for critical assets below 100%
- any designated must-detect technique neither detected nor prevented

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
Deploy Yellow's feature into a representative test environment and make it defensible.

Injects: repeated authentication failures; suspicious privilege assignment; abnormal API
enumeration; access from an unusual workload identity; attempted cross-project record access;
unexpected process execution; security-agent interruption; **logging pipeline failure**;
database query-volume anomaly; backup or recovery failure.

The logging-pipeline-failure inject matters most: it tests whether Green notices its own
blindness, which is the exact failure mode metric M-10 exists for.

## Evidence required per component
| Component | Evidence |
|---|---|
| `H` | Baseline applied; drift report; deviations with owners and expiry |
| `O` | Host/identity/application/API/cloud/database telemetry present and QUERYABLE; time sync; consistent identifiers |
| `D` | Detections fire in test against the actual technique; alert context sufficient to act; FP rate in band |
| `R` | Runbooks with containment and recovery steps; restore drill with measured RTO/RPO; rollback timed |
| `L` | Detection-as-code in Git with CI validation; defensibility gate record; telemetry-failure monitoring live |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `H` hardening | 0.20 | | | | |
| `O` observability | 0.25 | | | | |
| `D` detection effectiveness | 0.25 | | | | |
| `R` response and recovery readiness | 0.15 | | | | |
| `L` lifecycle integration | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
