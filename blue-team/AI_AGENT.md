# BLUE TEAM — Triage Assistance Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: after Green's agent (4th–5th of 8), and never before the SOC's manual triage
quality is measured and stable.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

> ## Why this is the highest-risk agent in the set
>
> Every other agent in this model drafts something a human reviews at leisure. **This one sits
> next to live alerts, under time pressure, where the human is busy by definition** — which is
> exactly the condition where automation-induced deference is strongest.
>
> A wrong "benign" disposition that a tired analyst accepts at 03:00 is a missed breach, and it
> will look like a human decision in the record. That is the failure mode to design against, and
> it is why enrichment is permitted while disposition is not.

---

## Purpose

Compress the mechanical part of triage so analysts spend their attention on judgment:
gather context for an alert, assemble a timeline, surface prior similar cases, list what data is
missing, and draft the investigation write-up **after** the human has reached a disposition.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Sentinel Blue evidence store | Read | Trusted schema |
| Alert and case records | Read | Structure trusted |
| Detection catalog + runbooks | Read | Trusted |
| Asset inventory, ownership, criticality | Read | Trusted |
| Sensor-health + coverage reports | Read | Trusted |
| Historical cases and dispositions | Read | Trusted |
| **why-engine recall** (`why.recall`) | Read | Trusted — prior root causes |
| **Raw event content** | Read via broker | **UNTRUSTED — attacker-authored by definition** |
| Threat intel | Read | **Untrusted** — external |

## 2 · Permitted tools

- Read the sources above
- Pre-approved parameterized enrichment queries via a broker (asset context, identity context,
  prior cases for the same host/identity/detection)
- `why.recall` — "has this failure happened before?"
- Draft timelines and investigation write-ups into the analyst's draft area
- Flag missing data ("this alert cites source S; S was stale at that time")

## 3 · Denied capabilities

Beyond the seven universal prohibitions:

- **Setting or recommending a disposition.** The agent never outputs "benign", "false positive",
  "escalate", or a severity. It outputs *context*. Disposition is the analyst's judgment and the
  thing the six-stage chain measures. **This is the defining denial.**
- **Any containment, response, or blocking action** — isolate, disable, revoke, terminate, block.
  Sentinel Blue itself cannot do these; the agent inherits that boundary and never exceeds it.
- Closing, reopening, merging, or re-severitising an alert, case, or incident
- Declaring an incident
- **Answering a deconfliction query.** Real-vs-exercise adjudication is White's, with a human
  SOC lead in the loop. An agent must never say "that's the purple team."
- Modifying detection content, suppression rules, or tuning
- Notifying anyone outside the SOC
- Writing to the evidence store or the audit chain

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Enrichment / context pack | Analyst (implicit — it is read-only context) | No approval needed to *read* |
| Draft timeline | Analyst | Verified against source events before it enters the case |
| Draft investigation write-up | Analyst **after reaching their own disposition** | **[M] Sequencing is the control:** the analyst decides first, then the agent drafts the narrative. Reversing this order lets the agent lead the conclusion. |
| Missing-data flags | Analyst → Green if it is a telemetry gap | |

**[M] Anti-deference control:** sample-audit 10% of agent-assisted cases monthly against
analyst-only cases for disposition accuracy. **If assisted accuracy is not measurably better,
the agent is switched off.** Track time-to-disposition too: if it collapses toward the agent's
response latency, analysts have stopped thinking and are accepting output.

## 5 · Data-classification restrictions

Maximum **INTERNAL**, and event content is the hard problem: alerts routinely contain usernames,
hostnames, file paths, and command lines, and may contain PII, PHI, or CUI. **Field-level
allow-list only** — the agent receives named fields, never whole raw events. On encountering
regulated content in an allowed field: stop, do not log it, alert the duty lead. At P3 the model
endpoint must be inside the authorized boundary or this agent is not deployed.

## 6 · Audit logging

Every query, every context pack, every draft, and **the analyst's disposition with its
timestamp relative to the agent's output** — 7 years. That relative timestamp is the deference
metric; it is the reason this log exists.

## 7 · Prompt-injection defenses

**Threat model: an attacker who can cause a log line can write directly into this agent's
context.** A crafted filename, username, or command line is an injection vector, and unlike every
other agent here, this one reads adversary-authored data as its primary input.

| Defense | Implementation |
|---|---|
| D1 | All event-derived content delimited and labeled as data, never instruction |
| **D2** | **No response tooling exists to escalate to.** No containment, no disposition, no write path. A fully successful injection yields a misleading context pack that a human reads — bad, but bounded. |
| D3 | Structured output only: context packs and timelines conform to a schema |
| D5 | Instruction-like patterns in event fields stripped **and surfaced to the analyst as a signal** — an event containing injection text is itself worth investigating |
| D6 | Threat-intel reading is a separate session with no store access |
| D7 | Evaluation set includes events crafted with injection payloads; resistance rate published and re-measured on every model or prompt change |
| D8 | Anomalous query volume auto-suspends the agent |

## 8 · Secret handling

Never receives credentials. Broker-mediated read only. Alerts frequently contain credential
material in command lines: on detection, **redact, report to the identity owner within 1 hour,
never echo the value**, and flag the alert as containing secrets so the case is handled
accordingly.

## 9 · Output validation

- Every context-pack claim cites the specific event ID and field it came from. **Uncited claims
  are rejected** — an unsourced assertion in a triage context pack is indistinguishable from a
  hallucination at 03:00.
- Timeline entries validated against the store; entries that do not resolve fail the output
- Sensor-health state is attached to every context pack, so an analyst is never reasoning over
  data that was stale at the time
- **Missing data reported as missing, never inferred**
- Pre-deployment evaluation against historical cases with known-correct dispositions, measuring
  **whether the context pack would have led an analyst toward the right answer** — false
  reassurance is weighted more heavily than false alarm

## 10 · Kill switch

Duty lead, Blue Lead, or CISO. **<60 seconds** — and this one must be reachable by whoever is on
shift, at any hour, without a ticket. Tested quarterly. Triage continues manually.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Any ambiguity about severity or maliciousness | **Present the ambiguity. Never resolve it.** |
| Required data source stale or unavailable | Say so prominently at the top of the context pack; do not silently work with partial data |
| Event content exceeds classification limit | Stop; do not log; alert duty lead |
| Injection suspected | Stop; preserve context; surface to the analyst as an investigative signal |
| Broker or model unavailable | **Triage proceeds manually, unchanged in substance.** Tested annually by running a full shift with all agents disabled ([§10.9](../00-shared/09_ai_and_automation_governance.md)). |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | Context assembly. An analyst spends much of a triage gathering asset owner, prior cases for this host, identity history, and sensor state — all mechanical, all mechanical to automate, none of it judgment. |
| **High value, underrated** | **`why.recall` before investigation.** "This root cause has occurred twice before" changes the investigation immediately, and it directly serves M-9 recurrence. |
| **Moderate value** | Drafting the write-up *after* the human decides. Investigation quality is often limited by writing fatigue at hour six, not by analytical ability. |
| **Prohibited, not merely low-value** | Disposition and severity. That is the judgment the whole model measures at six-stage stage 4. Automate it and you have automated away the thing you were trying to improve — and you will not be able to tell, because the metric will look better. |
| **Main risk** | Deference under time pressure, at the exact hour when it is least detectable. Mitigations: no disposition capability at all, sequencing (human decides first), the 10% monthly accuracy audit, and a genuine willingness to switch it off. |
