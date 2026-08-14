# WHITE TEAM — Artifact Templates

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).
The full **Rules of Engagement** template is [§5](../00-shared/04_rules_of_engagement_template.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

| ID | Artifact | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| — | Rules of Engagement | Per RoE §5.18 | 7 yr | Per RoE | Exercise record |
| — | Authorization Record | System Owner | 7 yr | INTERNAL | Exercise record |
| A4 | Safety Assessment | White Exercise Director | 7 yr | INTERNAL | Exercise record |
| — | Deconfliction Answer Key | Exercise Director | 7 yr | Per RoE | Exercise record (sealed) |
| — | Decision Log (incl. stops) | Exercise Director | 7 yr | Per RoE | Exercise record |
| A11 | Evidence Manifest + Chain of Custody | Exercise Director | Longest applicable | Inherits | Evidence store (WORM) |
| — | Scoring Rubric | Exercise Director | Versioned indefinitely | INTERNAL | Exercise record |
| A12 | After-Action Report | Exercise Director | 7 yr | INTERNAL / CONFIDENTIAL | Exercise record + exec repo |
| A10 | Risk Acceptance | **System Owner signs**; Exec above threshold | 7 yr past expiry | CONFIDENTIAL | Risk register |
| — | Destruction Certificate | Evidence Custodian + Privacy | 7 yr | INTERNAL | Evidence store |

---

## Authorization Record

One per in-scope system. **[M] No signature = that system is out of scope.**

```markdown
# Authorization Record AUTH-YYYY-NNN-<asset>

Exercise:                     [M]
System / asset ID:            [M]
System name:                  [M]
System owner (named human):   [M]
Business owner (if different): [M]
Data classification:           [M]
Criticality tier:              [M]

## Authorized activity  [M]
Permitted impact ceiling:  none | read-only | config change | service degradation
Environments authorized:   lab | dev | pre-prod | prod
Techniques authorized:     [reference the test-case list]
Window:                    [M]

## Constraints  [M]
Availability requirements:  e.g. 99.9% -- max acceptable disruption ____
Blackout periods:           [M]
On-call contact + backup:   [M] name, phone
Rollback expectation:       [M]
Notification requirements:  [M] who must be told, when

## Acknowledgement  [M]
> I am the accountable owner of this system. I have read the exercise proposal and
> the safety assessment. I understand the worst credible outcome described below.
> I authorize the activity within the constraints above. I understand that I may
> withdraw this authorization at any time, and that doing so stops the activity
> immediately with no justification required.

Worst credible outcome (stated by White, acknowledged by owner):  [M]

Owner signature: ____________  Date: ______
```

---

## A4 · Safety Assessment

```markdown
# Safety Assessment SA-YYYY-NNN

Exercise:                 [M]
Assessed by:              [M]  Purple (draft) + Green + Orange + Ops (review)
Approved by:              [M]  White Exercise Director
Date:                     [M]

## Per test case  [M]
TC | Worst credible outcome | Blast radius | P(unintended impact) | Rollback | Rollback
   |                        |              |                      | procedure| VERIFIED
   |                        |              | low/med/high         |          | time (min)
---|------------------------|--------------|----------------------|----------|----------

> A rollback that has never been executed and timed is not a rollback.
> Reject any row where "Rollback VERIFIED time" is blank.

## Aggregate assessment  [M]
Systems that could be affected beyond the in-scope list:   [M]
Third-party / customer impact possible:                     [M] yes/no + detail
Data exposure risk:                                          [M]
Availability risk:                                           [M]
Safety-of-life risk:                                         [M] must be "none" or the
                                                                  exercise does not proceed
Backups verified current (within 24h of window):             [M] yes/no + timestamp
Change freeze checked:                                       [M]
Concurrent exercises / audits:                               [M]

## Stop conditions specific to this exercise  [M]
[in addition to the standing conditions in RoE 5.13]

## Decision  [M]
[ ] GO
[ ] GO WITH CONDITIONS -- conditions: ____  (unmet conditions = NO-GO)
[ ] NO-GO -- reason: ____

Exercise Director: ____________  Date: ______
```

---

## Deconfliction Answer Key

Sealed. Released only in response to a specific query.

```markdown
# Answer Key AK-YYYY-NNN   [SEALED -- Exercise Director custody]

Registered source infrastructure:  IP/CIDR | hostname | owner | active from-to
Exercise identities:               name | privilege | active from-to
Exercise markers:                  string used in user agents, filenames, accounts
Planned activity schedule:         TC | planned start | planned end | target

## Query log
Timestamp | Queried by | Query | Answer given | Answered within SLA?
----------|------------|-------|--------------|---------------------

> Answer ONLY the specific query. Do not volunteer the plan.
> Response vocabulary is fixed: EXERCISE / NOT EXERCISE / UNKNOWN-INVESTIGATING.
> If not certain, the answer is UNKNOWN. A wrong "NOT EXERCISE" wastes an IR
> activation; a wrong "EXERCISE" stands the SOC down during a real breach.
```

---

## Decision Log

```markdown
# Decision Log EX-YYYY-NNN

ID | UTC | Decision maker | Decision | Options considered | Rationale | Consulted | Reversible
---|-----|----------------|----------|--------------------|-----------|-----------|------------

> Decision maker is always a NAMED HUMAN. Never "the team." Never an AI agent.
```

### Stop event sub-record
Structured form: [§6.4.5](../00-shared/05_communication_protocol.md).
```markdown
Stop ID | Called by | Called at | Halted at | Reason category | White assessment
        | Decision | Conditions | Decided by | Decided at | Downtime (min)

> EVERY stop is recorded and appears in the AAR, including stops later found
> unnecessary. Suppressing "false" stops teaches people not to call them.
```

---

## A11 · Evidence Manifest and Chain of Custody

```markdown
# Evidence Manifest EM-YYYY-NNN

Exercise:            [M]
Custodian:           [M]
Storage location:    [M]
Immutability:        [M] WORM / object-lock enabled -- verified by test on ____
Access list:         [M] named individuals
Marking:             [M] inherits the highest-classified content
Retention:           [M]
Destruction date:    [M]
Legal hold:          [ ] none  [ ] active -- ref ____

## Items
EV-ID | Description | Captured by | Captured at (UTC) | Method | Tool+version
      | SHA-256 | Classification | Size | Related TC/finding
------|-------------|-------------|-------------------|--------|-------------

## Completeness check  [M]
Evidence plan (from RoE) required: ____ items
Captured: ____
Gaps: ____ + reason for each   <- gaps are recorded, never silently omitted

## Chain of custody
UTC | Action (capture/transfer/access/verify/destroy) | By whom | Purpose | Hash verified?
----|--------------------------------------------------|---------|---------|---------------

Custodian: ____  Exercise Director: ____  Date: ____
```

**[M] A hash mismatch is a potential integrity incident, not a data-quality nuisance.** Stop,
preserve, and escalate to the Exercise Director and Legal.

---

## Scoring Rubric

**[M] Published before execution. Frozen at execution start. Never adjusted afterward.**

```markdown
# Scoring Rubric SR-YYYY-NNN   (frozen at ____ UTC)

## Process score (recommend 60% for early exercises, 40% once mature)
Criterion | Points | Evidence required | Pass condition
----------|--------|-------------------|---------------
Complete authorization before any activity | 15 | signed RoE + auth records | all present
All activity within approved scope | 10 | event log vs RoE 5.3 | zero deviations
Deconfliction SLA met | 10 | query log | 100% < 5 min
Evidence complete, hashed, retrievable | 10 | manifest | no unexplained gaps
Stop conditions executable | 5 | stop test record | tested at least once
Cleanup verified by a non-operator | 5 | checklist | signed
Daily updates + decision log maintained | 5 | channel archive | complete

## Outcome score
Criterion | Points | Notes
----------|--------|------
Test cases executed as planned | 10 | documented deferrals score full
Six-stage outcomes recorded with evidence | 10 | completeness, not favorability
Findings have acceptance criteria + named owners | 10 |
Predicted vs observed telemetry documented | 10 | gaps FOUND score the same as gaps ABSENT

## Rules  [M]
- Detection rate does NOT affect the score in a first or second exercise.
- A safety stop does NOT reduce the score. An IGNORED stop scores zero overall.
- Any activity outside approved scope scores zero overall.

Pass threshold: ____ / 100
```

---

## A12 · After-Action Report

```markdown
# After-Action Report AAR-YYYY-NNN
Classification: [M]   Version: [M]   Published: [M]   Author: White Scoring Analyst
Approved by: White Exercise Director

## 1. Executive summary  [M]   -- one page, decisions first
## 2. Objective and hypothesis  [M]  -- was the hypothesis falsified?
## 3. Scope and authorization  [M]  -- what was authorized, by whom
## 4. What actually happened  [M]  -- timeline, UTC
## 5. Six-stage outcome table  [M]  -- the analytical core of the report
## 6. Score against the frozen rubric  [M]  -- per criterion, with evidence
## 7. WHAT WORKED  [M]   <- FIRST, and specific. Name the people and controls that
                            performed. A report of only failures teaches the
                            organization to avoid exercises.
## 8. What did not work  [M]
## 9. Stop events  [M]  -- all of them, including unnecessary ones, with outcomes
## 10. Deviations from the RoE  [M]  -- including approved scope changes
## 11. Findings summary  [M]  -- by severity, with IDs; detail lives in the finding records
## 12. Recommendations  [M]  -- each with a named owner and a due date
## 13. Evidence manifest reference  [M]
## 14. Dissents  [R]  -- any participant conclusion White did not adopt, recorded verbatim

## Review record  [M]
Circulated for FACTUAL review: ____ to ____
Factual corrections accepted: ____
Conclusions/scores changed by participants: NONE  <- required value
```

---

## A10 · Risk Acceptance

```markdown
# Risk Acceptance RA-YYYY-NNNN

Finding(s):                [M]
System:                    [M]
System owner:              [M]  <- the ONLY valid signer (SoD-6)
Severity:                  [M]

## What is not being fixed  [M]
## Why  [M]   -- business rationale, not "no capacity"
## Compensating controls in place  [M]  -- and how each was VERIFIED
## Residual risk statement  [M]  -- in business terms
## Conditions that would change this decision  [M]

Expiry date:               [M]   max 12 months; max 90 days for Critical
Review trigger:            [M]   e.g. "architecture change", "new exploit published"
Risk register entry:       [M]

## Approvals
System Owner: ______  Date: ______
Executive (required if Critical, or >90 days): ______  Date: ______
GRC registered by: ______  Date: ______
White recorded by: ______  Date: ______
```

**[M] Every acceptance expires.** On expiry the finding reopens at its original severity and
returns to the backlog. It does not auto-renew. Report count and age of active acceptances to
the Risk Committee quarterly — **a growing pile of acceptances is a leading indicator of an
incident.**

---

## Destruction Certificate

```markdown
# Destruction Certificate DC-YYYY-NNN

Exercise:                  [M]
Data destroyed:            [M]  description + volume
Storage locations cleared: [M]  including backups, caches, and any working copies
Method:                    [M]
Date executed:             [M]
Executed by:               [M]
Verified by:               [M]  a different person
Legal hold checked:        [M]  confirmed none active before destruction

Exercise identities revoked: [M]  list + revocation timestamps + confirmed by identity owner
Test infrastructure decommissioned: [M]

Evidence Custodian: ______  Privacy Officer: ______  Date: ______
```
