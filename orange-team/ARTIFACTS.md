# ORANGE TEAM — Artifact Templates

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).
The Threat Model template is co-owned and lives in
[yellow-team/ARTIFACTS.md](../yellow-team/ARTIFACTS.md) — because Yellow owns the content and it
lives with their code.

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

| Artifact | Approver | Retention | Marking | System of record |
|---|---|---|---|---|
| Threat Model (co-owned) | System Owner | Life of system + 3 yr | INTERNAL | Architecture repo |
| Abuse / Misuse Case Library | Orange Lead | Life of system | INTERNAL | Architecture repo |
| Attack-Path Analysis | Orange Lead | Life of system + 3 yr | **CONFIDENTIAL** | Architecture repo (restricted) |
| Attack-Surface Inventory | Orange Lead | Current + 3 yr | INTERNAL | CMDB / architecture repo |
| Design Review Record | Orange Lead | 3 yr | INTERNAL | Architecture repo |
| Pre-Production Validation Report | Orange Lead + White | 7 yr | INTERNAL | Exercise/test record |
| Safe Regression Test | Eng Manager | Life of codebase | INTERNAL | CI / test suite |
| Internal Attack-Path Catalog | Orange Lead | Current | **CONFIDENTIAL** | Restricted repo |
| Developer education content | Orange Lead | Current | INTERNAL | Knowledge base |

---

## Abuse / Misuse Case

Written alongside functional requirements, in the same language, so they land in the same backlog.

```markdown
# Abuse Case AC-<system>-NNN

Title:              [M]
System:             [M]
Related threat model element: [M]

## Narrative  [M]
As an attacker with <starting position>,
I can <action>,
because <weakness>,
resulting in <impact>.

Starting position:  [M]  unauthenticated | authenticated user | another tenant
                          | compromised workload identity | insider | supply chain
                          -> be specific; this is the assumption most often left vague

## Preconditions  [M]
What must be true for this to work.

## Why this is plausible  [M]
Real-world basis, or reasoning from the architecture. Do not invent threat actors.

## Becomes a requirement  [M]
Functional requirement (for Yellow's backlog):
  "The system MUST <behavior> such that <abuse case> is not possible."
Acceptance criterion (testable):
  "<specific test> returns <specific result>"

## Becomes a test  [M]
Regression test ID: ____   (safe check, not an exploit -- see PLAYBOOK section 5)
Purple test case ID (if emulated): ____

## Instrumentation  [M]  -> to Green
"If this were attempted, we would see ____ in ____."
If the answer is "nothing," that is a telemetry gap -- raise it.
```

---

## Attack-Path Analysis

**Marked CONFIDENTIAL.** This is a map of how to compromise your own systems; distribution is a
named list.

```markdown
# Attack-Path Analysis APA-<system>-NNN
Classification: CONFIDENTIAL   Distribution: named individuals only

System / scope:     [M]
Crown jewel:        [M]  what the attacker actually wants, in business terms
Analyst:            [M]
Date / valid until: [M]  (architecture changes invalidate this -- date it prominently)

## Paths
Path ID | Entry point | Steps (concise) | Privilege required at each step
        | Feasibility (trivial/moderate/difficult) | Impact | Existing controls
        | Control confidence (verified/assumed) | Detectable? (yes/no/partial)
--------|-------------|-----------------|-------------------------------

> "Control confidence: ASSUMED" is where real breaches live. Verify or mark it.

## Choke points  [M]
Steps that appear in MULTIPLE paths. These are the highest-value control
investments -- one fix closes several paths. Name them explicitly; this is the
single most actionable output of the analysis.

## Recommendations  [M]
Path(s) addressed | Recommendation | Effort | Owner | Decision (accepted/rejected/deferred)

## Detectability gaps  [M]  -> to Green
Path steps with no telemetry or no detection.

## Assumptions  [M]
What was assumed rather than verified. Re-analyse when any assumption changes.
```

---

## Attack-Surface Inventory

```markdown
# Attack Surface — <system>

Entry point | Type (API/UI/queue/file/webhook/model-input) | Authentication
            | Authorization model | Exposure (internet/internal/privileged)
            | Data classes reachable | Rate limited? | Logged? | Owner
------------|----------------------------------------------|---------------

## AI/agent surfaces (where applicable)  [M]
Untrusted content entering model context | Source | Bounded how? | Validated how?
Tool/function calls available to the model | Permission scope | Who approved
Model output consumed by | Downstream system | Validation applied
                          -> model output feeding a downstream system is an
                             INJECTION VECTOR into that system; treat it as one

## Changes since last review  [M]
New surfaces added | Removed | Changed exposure
```

---

## Design Review Record

```markdown
# Design Review DR-YYYY-NNNN

System / change:      [M]
Design doc / ADR ref: [M]
Reviewer:             [M]
Participants:         [M]  the engineering team
Date:                 [M]
Stage:                [M]  concept | design | pre-freeze | POST-FREEZE
                            -> if POST-FREEZE, record it. Repeated post-freeze
                               reviews are a PROCESS finding, not an Orange finding.

## Findings
ID | Attack path | Feasibility | Impact | Recommendation | Effort | Decision | Owner
---|-------------|-------------|--------|----------------|--------|----------|------
                                                          accepted / rejected / deferred

## Rejected recommendations  [M]
Record the recommendation and the rejection rationale VERBATIM.
Not to assign blame later -- so that if the path is realised, the decision
history is visible to the risk process rather than reconstructed from memory.

## Instrumentation requirements  -> Green  [M]
## Abuse cases raised  -> Yellow backlog  [M]
## Regression tests to build  [M]
## Follow-up review needed?  [M]  yes/no + trigger
```

---

## Pre-Production Validation Report

```markdown
# Pre-Prod Validation PPV-YYYY-NNNN

System / release:     [M]
Environment:          [M]  **lab or pre-prod ONLY -- never production**
Authorization:        [M]  approved envelope reference; White notified
Data:                 [M]  **synthetic only** -- confirm no production data present
Performed by:         [M]
Date:                 [M]

## Scope tested  [M]
Abuse cases validated | Result | Evidence
----------------------|--------|----------

## Findings  [M]
-> Enter the standard Finding workflow (Purple's A5). Do not maintain a
   separate Orange findings list; parallel trackers are where findings die.

## Environment fidelity  [M]
How closely does pre-prod match production? What did that difference prevent
from being tested? -> this determines whether Purple must retest in production
observationally.

## Cleanup  [M]
Artifacts created | Removed | Verified by (non-operator)
```

---

## Internal Attack-Path Catalog

```markdown
# Attack-Path Catalog
Classification: CONFIDENTIAL   Distribution: named list   Review: quarterly

Pattern ID | Pattern name | Description | Systems where observed
           | Root cause class | Paved road that eliminates it | Status
-----------|--------------|-------------|------------------------

## Rules  [M]
- A pattern observed in THREE systems is not a set of findings -- it is a missing
  platform capability. Route it to Green as paved-road work and record it here as
  such. Metric M-9 (recurrence) will keep rising until the platform fix ships.
- Every pattern carries the regression test or policy check that detects it.
- Review quarterly; retire patterns eliminated by a paved road, and record the date
  they were eliminated -- that date is evidence of improvement.
```

---

## Safe Regression Test — authoring standard

```markdown
Test ID:              [M]
Weakness class:       [M]
Source finding(s):    [M]
Assertion:            [M]  what specifically must be true
Runs in:              [M]  CI, on every PR (or nightly if genuinely too slow)
Deterministic:        [M]  yes -- flaky security tests get disabled, and then deleted
Runtime:              [M]  seconds
Failure message:      [M]  states what is wrong AND how to fix it

## Safety attestation  [M]
[ ] Contains no exploitation
[ ] Contains no credential material or payloads
[ ] Runs only against test/CI environments
[ ] Fails safely if the environment is unavailable (does not silently pass)

> A regression test that silently passes when the environment is unavailable is
> worse than no test: it reports coverage you do not have.
```
