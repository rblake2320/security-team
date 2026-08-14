# PURPLE TEAM — Coordination Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and the twelve universal requirements apply in full and are not restated here.

**Deployment order: 6th of 7.** Do not deploy until the manual exercise process has run at least
three complete cycles. This agent is coupled to the live process; automating an unstable process
produces unstable output faster.

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

## Purpose

Reduce the coordination and transcription overhead of running exercises: draft test-case
scaffolding from a threat scenario, map activity to ATT&CK, assemble the six-stage outcome table
from structured event data, draft findings, and flag inconsistencies between predicted and
observed telemetry.

**It does not test anything, decide anything, or approve anything.**

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Emulation library (Git) | Read | Trusted — reviewed code |
| Exercise event log (structured JSON) | Read | Trusted — schema-validated |
| Approved RoE (scope, exclusions, window) | Read | Trusted |
| ATT&CK knowledge base (local copy, versioned) | Read | Trusted |
| Detection catalog (Green's, read-only) | Read | Trusted |
| SIEM query results | Read (via broker) | **Contents untrusted** — log data is attacker-influenced |
| Case management (findings, retests) | Read | Trusted schema, **untrusted free text** |
| Threat intel reports | Read | **Untrusted** — external content |

---

## 2 · Permitted tools

- Read the sources above
- Execute **pre-approved, parameterized** read-only SIEM/telemetry queries through a broker
  (the agent selects from a query catalog; it does not compose arbitrary queries)
- Write **drafts** to the Purple review queue
- Compute ATT&CK mappings and coverage layers
- Validate output against schemas

## 3 · Denied capabilities

Beyond the seven universal prohibitions:

- **Executing any test case, command, or tool against any target, in any environment** — this is
  the single most important denial for this agent, and the agent identity must
  having no execution path at all, not by instruction
- Writing to the emulation library, the exercise record, or case management directly
- Assigning or changing severity (may *propose* with rationale)
- Closing a finding or recording a retest verdict
- Contacting system owners, SOC, or any human on the program's behalf
- Composing arbitrary SIEM queries (catalog only — an injected instruction cannot become a query)
- Reading evidence content above INTERNAL

## 4 · Required human approvals

| Agent output | Approver | What the approver sees |
|---|---|---|
| Draft test case | Purple Lead + White (safety class) | Full draft, source scenario, and the diff vs. any template |
| ATT&CK mapping | Purple Lead | Mapping with the reasoning and confidence |
| Six-stage outcome table | Purple Lead | Table with every evidence reference resolvable |
| Draft finding | Purple Lead, then White for severity | Draft + evidence + proposed severity inputs |
| Coverage layer / metric input | Purple Lead | Values with denominators |

**No agent output enters a system of record without a named human committing it.**
Approvers record a one-line reason — a click alone is not an approval (§10.9, automation-induced
deference).

## 5 · Data-classification restrictions

Maximum: **INTERNAL**. On encountering CUI, PII, PHI, cardholder data, credentials, or any
higher-classified content: **stop processing that item, do not log the content, do not summarize
it, alert the Purple Lead.** Never route regulated content to a model endpoint outside the
authorized boundary (at P3, the endpoint itself must be inside the boundary).

## 6 · Audit logging

Every input, retrieved document, tool call, generated output, and human approval decision —
immutable, 7-year retention, with enough prompt context to reconstruct what the model saw.
Reviewed monthly by the Purple Lead; sampled annually by White.

## 7 · Prompt-injection defenses

Threat model: **SIEM log contents, ticket text, and threat intel reports are attacker-influenced
by definition.** An attacker who can write to a log can attempt to write to this agent's context.

| Defense | Implementation |
|---|---|
| D1 Trust marking | All log/ticket/intel content delimited and labeled as data, never as instruction |
| **D2 No tool escalation** | Tools fixed at session start from the agent identity. **No content can grant a tool.** Even a fully successful injection reaches nothing. |
| D3 Schema output | JSON only, validated. Prose output is rejected — an injected instruction that produces prose fails loudly. |
| D4 Human approval | Every draft reviewed before it enters any record |
| D5 Sanitization | Instruction-like patterns stripped from untrusted input; strips are logged |
| D6 Trust separation | The intel-reading path has no access to internal systems; findings cross as structured data |
| D7 Canaries | Injection attempts in the evaluation set; resistance rate published; re-run on every model or prompt change |
| D9 No agent trust | Other agents' output is untrusted input |

## 8 · Secret handling

Never receives credentials. Broker holds all authentication. On encountering a secret in input:
**redact, report to the identity owner within 1 hour, stop processing that item.** Never echoes a
secret, even partially, in output or logs.

## 9 · Output validation

- Schema validation on every output; non-conforming output is rejected, not repaired
- Every evidence reference must resolve to a real artifact; unresolvable references fail the output
- Every ATT&CK ID must exist in the versioned local knowledge base
- Confidence stated on every mapping and inference
- **Missing data is reported as missing, never inferred**
- Pre-deployment evaluation against a set of past exercises with known-correct outputs;
  false-positive and false-negative rates published to the approving humans and re-measured on
  every model or prompt change

## 10 · Kill switch

Purple Lead or White Exercise Director. Effective in **<60 seconds**. Disables the agent identity
at the credential layer, not just the interface. Tested quarterly. **Manual process resumes
immediately at reduced speed** — see the fail-closed rule below.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Ambiguous scope relative to the RoE | Stop; escalate to Purple Lead. **Never resolve scope ambiguity in favor of doing more.** |
| Data source unavailable or stale | Report the gap; do not estimate, do not interpolate |
| Schema validation failure | Discard; alert; do not retry with relaxed validation |
| Evidence reference unresolvable | Fail the entire output, not just the line |
| Suspected injection detected | Stop; preserve full context; alert Purple Lead and White |
| Classification limit exceeded | Stop; do not log content; alert |
| Model or endpoint unavailable | Process continues manually. **Any workflow that cannot run without this agent is not approved** (§10.9). |

## 12 · Value and honest assessment

| | |
|---|---|
| **Real value** | Transcription and assembly: six-stage tables from event logs, coverage layers, draft findings. This is tedious, error-prone human work over structured data. |
| **Limited value** | Test-case authoring. The scaffolding helps; the judgment about blast radius, safety, and what is actually worth testing does not transfer. |
| **No value, do not attempt** | Deciding what to test, judging severity, facilitating the collaborative session. The validation session's value is *humans talking to each other*; automating around it defeats its purpose. |
| **Main risk** | Volume. An agent can draft findings faster than the organization can remediate them. Findings still require evidence (gate G4) and human validation, and **volume is not a metric** (§8.18). |
