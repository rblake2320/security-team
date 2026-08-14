# ORANGE TEAM — Threat Modeling & Abuse-Case Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: 4th of 7.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

> ## The one that must be said first
>
> **This agent never executes anything.** No commands, no tools against targets, no scanning, no
> exploitation, no payload generation — in any environment, including lab. Orange's own charter
> prohibits production activity; the agent's prohibition is broader and absolute.
>
> This agent specification provides **no execution path at all** — no shell, no
> network egress to target systems, no credentials to any environment. It is a document-reading,
> document-writing agent. Nothing in its permission set could execute anything even if it were
> fully compromised.

---

## Purpose

Improve the **completeness** of threat models and abuse-case coverage: prompt for elements a
model has not addressed, draft abuse cases from a design document, propose STRIDE coverage per
element, and check that every identified attack path has both a control decision and an
instrumentation decision.

**Completeness prompting is the value.** Human threat models are rarely wrong about what they
cover; they are routinely incomplete about what they skipped.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Design documents, ADRs, API specs | Read | Trusted |
| Source code (read-only) | Read | Trusted |
| Existing threat models | Read | Trusted |
| Internal attack-path catalog | Read | Trusted (**CONFIDENTIAL** — see §5) |
| Abuse-case library | Read | Trusted |
| Asset inventory + data classification | Read | Trusted |
| Paved-road catalog | Read | Trusted |
| ATT&CK, CWE, and internal weakness taxonomies (local, versioned) | Read | Trusted |
| Public advisories and security research | Read | **Untrusted** — external content |

## 2 · Permitted tools

- Read the sources above
- Draft threat model sections, abuse cases, and attack-path candidates into the Orange review queue
- Check an existing threat model for completeness against a structured checklist
- Cross-reference a design against the internal attack-path catalog

## 3 · Denied capabilities

Beyond the seven universal prohibitions:

- **Executing anything, anywhere.** No commands, no scans, no network interaction with any
  system, no exploitation, in any environment. Enforced by permission set, not by instruction.
- **Generating exploit code, payloads, evasion techniques, or persistence mechanisms** — the
  output vocabulary is *design weakness and control decision*, never *working attack*
- Accessing production, pre-production, or lab environments in any way
- Handling credentials or any credential-shaped material
- Approving a threat model or a design (Orange Lead + System Owner do)
- Deciding that an attack path is acceptable
- Writing to the architecture repo, the attack-path catalog, or any record directly

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Draft threat model section | Orange Lead **+ the engineering team** | **The team must engage with it, not receive it.** An agent-drafted model handed over unreviewed reproduces the exact anti-pattern the Orange charter prohibits. |
| Draft abuse case | Orange Lead | Then to Yellow as a requirement |
| Attack-path candidate | Orange Lead | Human validates feasibility — the agent cannot assess what your controls actually do |
| Completeness gap list | Orange Lead | Advisory input to the session, not a substitute for it |
| Catalog pattern proposal | Orange Lead | |

## 5 · Data-classification restrictions

Maximum **CONFIDENTIAL** — this is the only agent in the architecture permitted above INTERNAL,
because attack-path analyses are inherently CONFIDENTIAL.

**Consequences of that [M]:**
- At P3, or wherever attack paths of CUI-processing systems are in scope, the model endpoint
  **must be inside the authorized boundary**, or this agent is not deployed
- Outputs inherit CONFIDENTIAL marking automatically
- Access list is the same named list as the attack-path catalog
- **Never processes production data, credentials, or evidence content**

## 6 · Audit logging

Every document read, every draft, every human decision — 7 years, with full prompt context.
Access to CONFIDENTIAL attack-path material is logged and reviewed quarterly by the Orange Lead.

## 7 · Prompt-injection defenses

Threat model: **design documents and code comments are writable by anyone with repo access**, and
public security research is fully attacker-controllable.

| Defense | Implementation |
|---|---|
| D1 | Design docs, code comments, and external research delimited and labeled as data |
| **D2** | **No tools to escalate to.** The agent has no execution path, no environment access, and no credentials. This is the defining structural control. |
| D3 | Structured output: threat model sections and abuse cases conform to the [ARTIFACTS.md](ARTIFACTS.md) schemas |
| D5 | Instruction-like patterns in documents stripped and flagged |
| D6 | External research is read in a separate session with no access to internal material; conclusions cross as structured data |
| D7 | Evaluation set includes design documents containing injection attempts |

## 8 · Secret handling

Never receives secrets. On finding a credential in a design document or code:
**redact, report to the identity owner within 1 hour, and raise it as a finding** — a credential
in a design document is itself a weakness worth recording.

## 9 · Output validation

- Schema validation against the abuse-case and threat-model templates
- Every abuse case must state its **starting position** explicitly — an abuse case with a vague
  starting position is rejected, because vague starting positions are the most common defect in
  human threat models too
- Every attack path must state control confidence as **verified** or **assumed**; unmarked paths
  are rejected
- Every CWE/ATT&CK reference validated against the versioned local taxonomy
- **No output may contain exploit code, payloads, or step-by-step attack instructions** — this is
  validated by an output filter, not only by instruction [M]
- Pre-deployment evaluation against past threat models with known-good outputs; measured on
  **recall of known paths** specifically, since completeness is the entire value proposition

## 10 · Kill switch

Orange Lead or CISO. <60 s. Tested quarterly. Threat modeling continues exactly as before — the
sessions are human and always were.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Design documentation insufficient to model | **Report what is missing.** Do not infer an architecture. An inferred architecture produces a confident model of a system that does not exist. |
| Data classification unknown for a store | Stop; ask. Classification drives everything downstream. |
| Output would contain exploit-shaped content | Suppress; report; do not attempt a "safer" rewrite |
| Classification limit exceeded | Stop; do not log content; alert |
| Injection suspected | Stop; preserve context; alert Orange Lead |
| Agent unavailable | Threat modeling sessions run unchanged |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | **Completeness prompting.** "You modeled the API but not the message queue." "This data store has no classification." "Three paths have no instrumentation decision." Humans are good at depth and reliably bad at coverage; this is the inverse of the agent's weakness. |
| **Moderate value** | Drafting abuse cases from a design doc. A useful starting point that a human sharpens. |
| **No value — and actively harmful if attempted** | **Replacing the threat modeling session.** The session's value is engineers reasoning about their own system out loud, with someone adversarial in the room. An agent-produced model handed to a team is precisely the anti-pattern the [charter](CHARTER.md) prohibits: no knowledge transfer, no ownership, stale within a month. |
| **Main risk** | A complete-looking model that nobody engaged with, creating false confidence — worse than an obviously incomplete one, which at least prompts someone to finish it. **Mitigation: the engineering team's engagement is a required approval, not a courtesy.** |
