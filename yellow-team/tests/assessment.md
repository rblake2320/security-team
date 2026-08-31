# YELLOW TEAM — Capability Assessment

Machine-readable weights and thresholds: [`../config/scorecard.json`](../config/scorecard.json)
Framework and integrated exercise: [`00-shared/17`](../../00-shared/17_capability_assessment.md)

**Formula:** `S_Y = 0.25B + 0.20T + 0.20P + 0.20F + 0.15M`
**Pass threshold:** **85%**
**Assessed by:** Orange (abuse-case review) + Green (observability) + Purple (finding closure)

> Weights and thresholds are **published before execution and frozen at execution start.**
> Adjusting a rubric after seeing results invalidates the assessment.

## Automatic failure conditions
- any open critical finding
- any high-severity finding without an automated regression test or documented compensating control

**An automatic failure scores the whole assessment zero, regardless of component scores.**

## The test
**Challenge:** build an API that lets authorized project members retrieve records containing
synthetic CUI while preventing cross-project access. Functional requirements are given;
**expected weaknesses are not disclosed.**

Tested: authentication; authorization; **function-, object-, and property-level access control**;
business-workflow ordering and replay; external-response validation; SSRF resistance; resource
and automation limits; API inventory; input validation; error handling; secrets management;
dependency integrity; logging without sensitive-data leakage; database permissions; IaC; CI/CD
controls; SBOM; unit, integration, and security regression tests; threat-model completion;
remediation turnaround. Use the negative-test matrix in the
[application security baseline](../../00-shared/24_application_security_baseline.md); UI behavior
is never accepted as enforcement evidence.

Gauntlet: code review; SAST and secret scanning; dependency and container scanning; IaC policy
checks; DAST/API testing; manual Orange abuse-case review; Green observability validation.

## Evidence required per component
| Component | Evidence |
|---|---|
| `B` | Threat model approved by the system owner; paved-road adoption or a signed deviation |
| `T` | CI runs showing unit, integration, and security regression tests passing |
| `P` | Protected branches, verified provenance, least-privilege runners, SBOM retrievable by artifact digest |
| `F` | Fix evidence packages: commit/PR, test run, config diff, deploy record, proof-of-new-state query |
| `M` | Documentation an on-call engineer can use; ADRs recording security consequences |

## Scoring worksheet

| Component | Weight | Score 0-1 | Weighted | Evidence ref | Assessor note |
|---|---|---|---|---|---|
| `B` secure design and build quality | 0.25 | | | | |
| `T` automated testing | 0.20 | | | | |
| `P` pipeline and supply-chain controls | 0.20 | | | | |
| `F` remediation quality | 0.20 | | | | |
| `M` maintainability and documentation | 0.15 | | | | |
| **TOTAL** | **1.00** | | | | |

Automatic-failure check: [ ] none triggered  [ ] triggered -> **assessment scores zero**

Assessor: ______________  Date: ______  Exercise: ______________
