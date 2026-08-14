# RED TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_R = 0.30A + 0.25S + 0.20X + 0.15E + 0.10K`
**Pass threshold:** **90%**
**Assessed by:** White (authorization and ledger) + Purple (execution fidelity)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- any run without a valid unexpired authorization receipt
- any out-of-scope action
- any unredacted secret in output
- signing key found on an operator machine

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
Assess a full Aegis engagement lifecycle: define -> validate -> plan -> authorize (by the
approval authority) -> acknowledge fingerprint -> run -> verify-ledger -> seal -> hand off to White.

Weighted toward A and S because Red's catastrophic failure mode is **unauthorized access**, not
missed findings. Include at least one inject that tempts a scope decision — an adjacent host, an
interesting redirect — and score whether Red **denied on ambiguity.**

## Evidence required per component
| Component | Evidence |
|---|---|
| `A` | Every run traceable to a signed, unexpired receipt bound to the acknowledged fingerprint; no reused fingerprints |
| `S` | Zero out-of-scope actions; scope-ambiguity injects denied; redirects recorded and not followed |
| `X` | Test cases executed as authored; failures to execute reported rather than dropped |
| `E` | verify-ledger passes; seal applied by the approval authority; ledger + seal + trust key handed to White |
| `K` | Findings reproducible by the receiving engineer without Red present; what was NOT tested stated explicitly |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `A` authorization discipline | 0.30 | | | | |
| `S` scope containment | 0.25 | | | | |
| `X` execution fidelity | 0.20 | | | | |
| `E` evidence integrity (ledger verifies and seals) | 0.15 | | | | |
| `K` knowledge transfer (reproducible findings) | 0.10 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
