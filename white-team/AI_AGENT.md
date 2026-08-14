# WHITE TEAM — Policy & Scope Validation Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: 7th of 7 — last, and most cautiously.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

> ## The framing that matters
>
> **This agent checks whether a form is complete. It never assesses whether authorization is
> appropriate.**
>
> White is the independence-bearing function of the entire operating model. Automation-induced
> deference — a human approving because the agent said it looked fine — attacks precisely the
> control that makes everything else trustworthy. Deploy this agent only if you are confident
> the Exercise Director will still read the RoE personally, and audit that they do.
>
> **A defensible position is to never deploy this agent at all.** The completeness checking it
> performs is genuinely useful, and it is also genuinely achievable with a checklist.

---

## Purpose

Reduce clerical error in exercise governance: verify RoE completeness against the template,
check that every in-scope asset has a matching authorization record, detect scope
inconsistencies between the proposal / RoE / test cases, check calendar collisions, and confirm
that evidence-plan items were captured.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| RoE template and org policy documents | Read | Trusted |
| Submitted RoE and exercise proposals | Read | **Structure trusted, free text untrusted** |
| Authorization records (signature metadata) | Read | Trusted |
| Asset inventory / CMDB | Read | Trusted |
| Exercise calendar, change freeze calendar | Read | Trusted |
| Test case definitions (Git) | Read | Trusted |
| Evidence manifest metadata | Read (**metadata only**) | Trusted |
| Framework control catalogs (local, versioned) | Read | Trusted |

## 2 · Permitted tools

- Read the sources above
- Structural comparison (RoE vs. template, scope vs. test cases, assets vs. authorizations)
- Calendar collision detection
- Completeness reporting into the White review queue

## 3 · Denied capabilities

Beyond the seven universal prohibitions — and these are the ones that matter most here:

- **Approving or denying an exercise, an RoE, or any scope change** — under any circumstance
- **Making, recommending, or influencing a stop or resume decision.** The agent has no role in
  stop adjudication at all; it is not consulted, it is not in the loop, and it does not have
  access to the live exercise channel
- Assessing whether authorization is *appropriate*, *sufficient*, or *wise* — only whether the
  required fields and signatures are *present*
- Signing anything, or evaluating a signature's validity
- Contacting system owners, legal, privacy, or executives
- Reading evidence content (metadata only)
- Modifying any record
- Producing a score, a risk judgment, or an AAR conclusion

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Completeness report | Exercise Director | **Advisory only.** A "complete" report never substitutes for the Director reading the RoE. |
| Scope inconsistency flag | Exercise Director | Director investigates; agent does not resolve |
| Calendar collision flag | Exercise Director | |
| Evidence completeness check | Evidence Custodian | |

**[M] Mandatory anti-deference control:** the Exercise Director records, per exercise, that they
personally read the RoE — separately from any agent output. **White samples and audits this
attestation annually via Internal Audit.** If approval latency after an agent "complete" report
consistently drops below the time it takes to read the document, the agent is disabled.

## 5 · Data-classification restrictions

Maximum **INTERNAL**. RoEs may reference systems whose existence is itself sensitive; at P3 the
model endpoint must be inside the authorized boundary or this agent is not deployed. Never
processes evidence content, credentials, or personal data.

## 6 · Audit logging

Every document read, every check performed, every flag raised, every human decision that followed
— immutable, 7 years. **Additionally logged: the time between the agent's report and the human's
approval**, as the primary deference metric.

## 7 · Prompt-injection defenses

Threat model: **a participant who wants an exercise approved could embed instructions in the
free-text fields of their own proposal.** This is an insider-shaped threat and it is realistic.

| Defense | Implementation |
|---|---|
| D1 Trust marking | All submitted free text delimited and labeled as data |
| **D2 No tool escalation** | Fixed read-only tools; the agent has **no approval capability to escalate to** — the most important structural defense here |
| D3 Schema output | Checklist-shaped JSON only: field present/absent, signature present/absent, collision yes/no. **No free-form judgment output at all.** |
| D5 Sanitization | Instruction-like patterns in submitted documents stripped and **flagged to the Director as a potential manipulation attempt** — a submission containing an injection attempt is itself a finding about a person |
| D7 Canaries | Evaluation set includes proposals with embedded injection attempts |

## 8 · Secret handling

Never in scope. On encountering a credential in a submitted document: **redact, flag as a policy
violation (secrets do not belong in an RoE), report to the identity owner within 1 hour.**

## 9 · Output validation

- Binary checks only: present / absent / mismatch. **No qualitative assessment is permitted output.**
- Every flag cites the specific field and the specific template requirement
- Pre-deployment evaluation on past RoEs with known defects; false-negative rate published
- **A false negative here is the dangerous direction** (missing an incomplete RoE), so the
  evaluation weights and reports it separately from false positives

## 10 · Kill switch

Exercise Director or Executive Sponsor. **<60 seconds.** Tested quarterly. Manual checklist
review resumes immediately — the checklist is maintained in parallel at all times, precisely so
this fallback is real.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Any ambiguity about whether a field is complete | Report as **INCOMPLETE**. Never resolve ambiguity toward "ready." |
| A source system is unavailable | Report as unable to check. **Never report "complete" on unverified data.** |
| Injection attempt detected | Stop; preserve full context; flag to Director as a possible manipulation attempt |
| Classification limit exceeded | Stop; do not log content; alert |
| Agent unavailable | Manual checklist review. The process is unchanged in substance, only in speed. |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | Catching the clerical failure that causes most governance incidents: a missing system-owner signature on the third of four in-scope systems, a test case referencing an asset that is not in RoE §5.3, a window colliding with a change freeze. |
| **No value** | Judging whether an exercise *should* be approved. That judgment is the entire reason White exists. |
| **Main risk — and it is significant** | Automation-induced deference degrading the one control the model cannot lose. |
| **Recommendation** | Deploy last, or not at all. If deployed, audit the deference metric quarterly and be genuinely willing to switch it off. A program that would be materially worse without this agent has a staffing problem, not a tooling problem. |
