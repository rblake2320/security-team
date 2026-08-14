# YELLOW TEAM — Artifact Templates

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

| ID | Artifact | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| — | Threat Model (co-owned with Orange) | System Owner | Life of system + 3 yr | INTERNAL | **Architecture repo, versioned with the code** |
| A8 | Engineering Remediation Ticket | System Owner | 3 yr after closure | INTERNAL | **The normal engineering backlog** |
| — | Fix Evidence Package | Purple (verifies) | 7 yr with the finding | INTERNAL | Case management + CI records |
| — | SBOM / provenance attestation | Eng Manager | Life of artifact + 3 yr | INTERNAL | Artifact registry |
| — | Regression test | Eng Manager | Life of the codebase | INTERNAL | CI / test suite |
| — | Deviation / Exception request | Green + Orange review; **System Owner accepts** | 7 yr past expiry | INTERNAL | Risk register |
| — | Architecture Decision Record | Architect | Life of system | INTERNAL | Architecture repo |

---

## Threat Model

Lives **with the code**, versioned. Not on a wiki, not in a slide deck.

```markdown
# Threat Model — <system>   TM-<system>-vN

System:               [M]
System owner:         [M] named human
Engineering owner:    [M]
Facilitated by:       [M] Orange
Participants:         [M] the engineers who build it -- if they were not in the room,
                          this model will be stale within a month
Date:                 [M]
Next review due:      [M] material change, or 12 months -- whichever first
Criticality tier:     [M]

## 1. What are we building?  [M]
Components:           [M]
Data flows:           [M] diagram + narrative
Trust boundaries:     [M] explicitly marked
Data stores:          [M] store | data class | classification | retention
External dependencies:[M] service | data shared | trust assumption
Identities:           [M] human and workload; what each can reach

## 2. What can go wrong?  [M]
Per element, STRIDE (or attack tree):
Element | Threat | STRIDE | Attack path | Feasibility | Impact | Existing control | Gap
--------|--------|--------|-------------|-------------|--------|------------------|----

## 3. What are we doing about it?  [M]
Gap | Decision (mitigate / transfer / accept / eliminate) | Owner | Work item | Due
----|------------------------------------------------------|-------|-----------|----

## 4. Instrumentation requirements  [M]   -> handed to GREEN
"To detect path X we need source S with field F."
Path | Required telemetry | Exists today? | Green work item
-----|--------------------|---------------|----------------

## 5. Abuse cases  [M]   -> become requirements in OUR backlog
"As an attacker with <starting position>, I can <action>, because <weakness>."

## 6. AI-specific (where applicable)  [M]
Untrusted content entering model context: [M] sources, and how they are bounded
Tool/function permissions available to the model: [M] and who approved each
Model output consumed by downstream systems: [M] validation applied
Tenant / data isolation: [M]
Prompt-injection mitigations: [M]

## 7. Assumptions and out-of-scope  [M]
Explicitly state what you assumed to be secure. Most missed attack paths hide here.

## 8. Review
Did we do a good job? What did we skip and why?  [M]

Approved by System Owner: ______  Date: ______
```

---

## A8 · Engineering Remediation Ticket

Created in the **normal backlog**, with these fields present.

```markdown
Title:                 [M]  the outcome, not the finding ID
Finding ref:           [M]  FND-YYYY-NNNN
Severity / SLA:        [M]
Target date:           [M]
System owner:          [M]  accountable for it happening
Assignee:              [M]  named engineer

## ACCEPTANCE CRITERIA  [M]  -- copied verbatim from the finding
1.
2.
3.
> If any criterion is not testable, reject back to Purple before starting.

## Approach  [R]
## Blast radius / rollback  [M] for anything touching production
## Regression test  [M]  ID, or explicit "not automatable because ____"
## Fix evidence  [M]  see below
## Status  [M]  open | in_progress | awaiting_retest | closed
> Only a PASSING RETEST moves this to closed. Not the assignee.
```

---

## Fix Evidence Package

```markdown
# Fix Evidence — FND-YYYY-NNNN

Criterion 1: <text>
  Evidence:   [M] commit/PR link + the specific diff hunk
              [M] CI run ID showing test <name> passing
  Verified:   [M] by whom (NOT the author -- SoD-3), when

Criterion 2: <text>
  Evidence:   [M] config diff / IaC plan output / policy export
              [M] query executed against <environment> at <UTC> returning <result>

Deployment:   [M] environment | version | timestamp | change record ref
Regression:   [M] test ID + first passing run
Residual:     [M] anything the fix does NOT address, stated plainly
```

---

## SBOM / Provenance

```markdown
Artifact:            [M] name + version + digest
Build:               [M] pipeline run ID, commit SHA, builder identity
SBOM format:         [M] SPDX or CycloneDX
SBOM location:       [M] retrievable by artifact digest
Components:          [M] name | version | license | source
Known vulnerabilities at build: [M] with disposition for each
Signature/attestation: [R] signing identity + verification instructions
Generated:           [M] UTC
```

**[M] The SBOM must be retrievable by artifact digest years later.** An SBOM generated in CI and
discarded satisfies a checkbox and answers no question you will actually be asked.

---

## Deviation / Exception Request

```markdown
# Deviation DEV-YYYY-NNNN

Standard being deviated from:  [M]  paved road / baseline / policy reference
System:                        [M]
Requested by:                  [M]
Why the standard does not fit: [M]  be specific -- "too slow" needs a number
Proposed alternative:          [M]
Security analysis:             [M]  Orange review
Detectability analysis:        [M]  Green review -- can we see abuse of this path?
Residual risk:                 [M]
Expiry:                        [M]  max 12 months
Review trigger:                [M]

Green reviewed: ____  Orange reviewed: ____
**System Owner accepts risk: ____  Date: ____**   <- only valid signer (SoD-6)
Registered in risk register: ____
```

**Deviations are a signal, not a failure.** Three deviations from the same paved road means the
paved road is wrong — route that to Green as a platform work item rather than processing a
fourth exception.

---

## Architecture Decision Record (security-relevant)

```markdown
# ADR-NNNN: <title>
Status:      proposed | accepted | superseded by ADR-____
Context:     [M]  including the security constraint driving the decision
Decision:    [M]
Consequences:[M]  security consequences explicitly -- what does this make easier
                  for an attacker, and what does it make harder?
Threat model impact: [M]  which section of the threat model changes
Orange reviewed:     [M] yes/no + date  (required for above-threshold systems)
```
