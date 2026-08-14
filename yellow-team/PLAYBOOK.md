# YELLOW TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> Yellow is engineering. This playbook describes what changes in *how you already work* — not a
> parallel process to run alongside it.

---

## 1. Workflow stages Yellow owns

| Stage | Yellow's role | Gate |
|---|---|---|
| 5 · Threat modeling | **R** (Orange facilitates; Yellow owns the content) | Model approved by the system owner |
| 11 · Engineering remediation | **R** (System Owner accountable) | Acceptance criteria met **and evidenced** |
| 12 · Retesting | C — provide the environment and context | Verification is **not** by the person who wrote the fix (SoD-3) |
| 16 · Lessons learned | R | Every lesson becomes a work item |

---

## 2. What changes in the SDLC

| SDLC stage | Added requirement | Owner | Label |
|---|---|---|---|
| Idea / epic | Security-relevant? → threat model required for above-threshold systems | Champion | [M] |
| Design | Orange design review for above-threshold changes; abuse cases become acceptance criteria | Architect + Orange | [M] |
| Build | Paved road used, or a deviation raised; secrets never in code, IaC, images, logs, or prompts | Engineer | [M] |
| PR | Security-relevant checklist in review; SAST/SCA/secret scan must pass | Reviewer | [M] |
| Pre-merge | IaC policy-as-code passes; regression tests for known weakness classes pass | CI | [M] |
| Pre-release | **Green defensibility gate**: required log sources, detections, runbook, rollback | Green | [M] |
| Release | SBOM generated and stored; provenance attested | CI | [M]/[R] |
| Post-release | Telemetry confirmed flowing as designed | Green + Yellow | [M] |

---

## 3. Runbook — receiving a finding

```
1. Read the ACCEPTANCE CRITERIA first, not the description. They define "done."
2. If the criteria are not testable, REJECT BACK to Purple. Do not start work
   against a criterion you cannot prove you met. This is not obstruction --
   gate G5 exists so that you are never asked to close something unclosable.
3. Confirm the severity SLA and the target date. If it is not achievable,
   say so NOW -- to the System Owner, not on the due date.
4. Pull it into the NORMAL backlog. Not a security spreadsheet.
   Work that lives outside the team's queue competes with nothing and loses to everything.
5. Fix. Then assemble the FIX EVIDENCE PACKAGE (ARTIFACTS.md) --
   commit/PR, test result, config diff, deploy record, proof-of-new-state query.
6. Mark awaiting_retest. Do NOT mark closed. Only a passing retest closes a finding.
7. If it cannot be fixed in SLA: route a RISK ACCEPTANCE to the System Owner.
   Silence past the due date is the one unacceptable outcome.
```

---

## 4. Runbook — threat modeling (as a participant)

Orange facilitates. **You own the content** — the model must be yours, or it goes stale the day
after the session.

```
BEFORE   Bring: architecture diagram (whiteboard-quality is fine), data flows,
         what data lives where, and the classification of each store.
         If no diagram exists, producing one IS the first half of the session.
DURING   Four questions, in order:
           1. What are we building?           (components, flows, boundaries)
           2. What can go wrong?              (STRIDE per element, or attack trees)
           3. What are we going to do about it?  (control per path, or accept)
           4. Did we do a good job?           (review the model itself)
         Push back. A threat model you disagree with is worthless.
AFTER    You own the document. It lives WITH THE CODE, versioned, not on a wiki.
         Instrumentation gaps -> Green.  Abuse cases -> your backlog as requirements.
REFRESH  On material architecture change, or every 12 months -- whichever first.
         A stale threat model counts as ABSENT in metric M-14, and is worse than
         none because it creates false confidence.
```

---

## 5. Runbook — the Security Champion role

4 hours per month, protected. **If your manager does not defend that time, the program is
nominal — escalate rather than quietly absorbing it.**

| Activity | Time |
|---|---|
| Attend the champions community call; bring your team's issues | 1 h |
| Review your team's open findings and unblock them | 1 h |
| Threat model refresh or design review participation | 1 h |
| Curriculum / craft development | 1 h |

**What a champion is:** the person on the team who knows *where to ask* and *what "secure enough"
looks like here*. **What a champion is not:** the person who does all the security work, or a
gatekeeper who approves their teammates' code.

---

## 6. Acceptance criteria — writing them well

Purple proposes; you must be able to prove you met them. Push back on anything untestable.

| Bad (untestable) | Good (testable) |
|---|---|
| "Improve input validation" | "Requests with a `tenant_id` not matching the authenticated principal return 403; integration test `t_cross_tenant_denied` passes in CI" |
| "Harden the service principal" | "The workload identity holds only roles X and Y; a policy-as-code check fails the build on any additional role assignment" |
| "Add logging" | "Every authentication decision emits an event to source S with fields {principal, result, source_ip, tenant}; Green confirms the event is queryable within 5 minutes of the action" |
| "Fix the dependency" | "Package P is at version ≥N in all built artifacts; SCA scan reports zero known-critical findings for P; SBOM reflects the new version" |

---

## 7. Fix evidence — what actually counts

| Counts | Does not count |
|---|---|
| Commit/PR link with the security-relevant diff | "Fixed in the last release" |
| CI test run showing the new test passing | "It works on my machine" |
| Config diff or IaC plan output | A screenshot of a settings page with no timestamp |
| Deployment record with timestamp and environment | "Deployed last week sometime" |
| Query result proving the new state in the target environment | A verbal assurance in standup |
| Regression test ID added to the suite | A comment saying "should add a test" |

---

## 8. Escalation

| Situation | Escalate to |
|---|---|
| Acceptance criteria not testable | Purple Lead |
| Severity disputed | Purple Lead → White |
| Cannot meet SLA | **System Owner, before the due date** |
| Paved road does not fit the use case | Green (+ Orange if there is a security implication) |
| Design review found something that changes the delivery plan | Engineering Manager + System Owner |
| Green defensibility gate is blocking a release | Engineering Director + System Owner (risk acceptance is the only override, and it is signed) |

---

## 9. Metrics Yellow owns

M-7 MTTR by severity · M-9 recurrence · M-13 regression conversion · M-14 threat model coverage ·
paved-road adoption · secrets-in-code (target: zero on main for 90 consecutive days).

**Watch M-9 recurrence hardest.** Recurrence means you are fixing instances of a problem whose
*cause* lives somewhere else — usually in a missing platform capability. The right response is to
ask Green for a paved road, not to fix it a fourth time.

---

## 10. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Security findings tracked outside the normal backlog | One queue. Always. |
| Closing a finding without a retest | Only a passing retest closes a finding |
| Threat model produced once and never updated | Refresh on material change; stale = absent (M-14) |
| Champions named but given no protected time | Escalate; a nominal program is worse than none because it creates false assurance |
| Deviating from a paved road silently | Raise a deviation; the System Owner accepts the risk explicitly |
| "We'll add the test later" | The regression test is part of the fix, not a follow-up |
