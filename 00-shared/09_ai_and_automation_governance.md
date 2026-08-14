# §10 — AI and Automation: Architecture and Governance

← [Index](../README.md) · Prev → [§9 Toolchain](08_toolchain_architecture.md) · Next → [§11 Compliance](10_compliance_crosswalk.md)

**This entire section is [O] Optional.** The operating model works with zero AI agents. Nothing
here is a prerequisite for anything in §1–§9. Deploy it only after the human process in §4 is
running reliably — **automating an unreliable process produces unreliable output faster.**

Per-agent specifications live with their team:
[Purple](../purple-team/AI_AGENT.md) · [White](../white-team/AI_AGENT.md) ·
[Yellow](../yellow-team/AI_AGENT.md) · [Green](../green-team/AI_AGENT.md) ·
[Orange](../orange-team/AI_AGENT.md) · plus **Evidence** and **Metrics** agents in §10.6–10.7 below.

---

## 10.1 The seven prohibitions — absolute, apply to every agent **[M]**

No AI agent in this architecture may:

1. **Approve its own actions.** Every state-changing action requires a named human approver.
2. **Modify production security controls.** No agent writes to SIEM content, EDR policy,
   identity policy, firewall rules, or cloud guardrails. Agents may *propose*; humans deploy.
3. **Execute offensive activity.** No agent runs a test case, executes a command against a
   target, or operates offensive tooling. Ever, in any environment.
4. **Accept risk.** Risk acceptance is a signed human decision by an accountable owner.
5. **Expand exercise scope.** Scope changes require White + System Owner, both human.
6. **Authorize an exercise, approve an RoE, or resume after a stop.**
7. **Act as the system of record.** Agent output is a draft or a recommendation until a human
   commits it. The record is what the human approved, not what the agent produced.

**Implementation [M]:** these restrictions must be expressed by the *tool permissions granted to the agent's
identity*, not by prompt instructions. An agent whose credentials can write to the SIEM will
eventually write to the SIEM, regardless of what its system prompt says.

---

## 10.2 Architecture

```
                    +-----------------------------------+
                    |   HUMAN AUTHORITY LAYER           |
                    |   White Director | Team Leads |   |
                    |   System Owners  | CISO          |
                    +-----------------+-----------------+
                                      | approvals (typed, logged, named)
                                      v
  +----------------------------------------------------------------------+
  |                      AGENT ORCHESTRATION LAYER                        |
  |   - routes tasks   - enforces per-agent tool allow-lists              |
  |   - logs every call - enforces data-classification limits             |
  |   - KILL SWITCH (single control, disables all agents in <60s)         |
  +--+--------+---------+---------+---------+---------+---------+---------+
     |        |         |         |         |         |         |
     v        v         v         v         v         v         v
  PURPLE   WHITE     YELLOW    GREEN    ORANGE   EVIDENCE   METRICS
  coord.   policy    remed.    detect.  threat   collect.   report.
                     assist    /harden  model
     |        |         |         |         |         |         |
     +--------+---------+---------+---------+---------+---------+
                                      |
                                      v
              +-----------------------+------------------------+
              |  TRUSTED DATA SOURCES (read-only, allow-listed) |
              |  case mgmt | Git | SIEM(read) | CMDB | ATT&CK   |
              |  threat models | detection catalog | evidence   |
              +-------------------------------------------------+
              |  UNTRUSTED CONTENT (quarantined, never trusted)  |
              |  web pages | vendor advisories | log contents    |
              |  ticket text | model output from another agent   |
              +-------------------------------------------------+
```

**Key design choice:** agents are **read-mostly advisors that produce drafts into a queue**.
The queue is worked by humans. This is deliberately unambitious — it is the configuration in
which an agent failure costs review time rather than security posture.

---

## 10.3 Universal agent requirements **[M]**

Every agent specification (in each team folder) must define all twelve of these. An agent
missing any one of them is not approved for deployment.

| # | Requirement | Standard |
|---|---|---|
| 1 | **Inputs & trusted data sources** | Explicit allow-list of systems and data types. Anything not listed is untrusted. |
| 2 | **Permitted tools** | Explicit allow-list, enforced by credential scope, not by prompt |
| 3 | **Denied capabilities** | Explicit, including the seven universal prohibitions |
| 4 | **Required human approvals** | Which actions, which named role, and what the approver sees |
| 5 | **Data-classification restrictions** | Maximum classification the agent may process; behavior on encountering higher |
| 6 | **Audit logging** | Every input, tool call, output, and approval — immutable, retained 7 years |
| 7 | **Prompt-injection defenses** | Per §10.4 |
| 8 | **Secret handling** | Per §10.5 |
| 9 | **Output validation** | Schema validation + human review criteria + confidence reporting |
| 10 | **Kill switch** | Per-agent and global; effective in <60 seconds; testable |
| 11 | **Fail-closed behavior** | Defined failure modes; the default on any error, ambiguity, or unavailable dependency is **stop and escalate to a human** — never proceed on a guess |
| 12 | **Evaluation before deployment** | Documented test set with known-correct answers; false-positive and false-negative rates measured and published to the approving humans |

---

## 10.4 Prompt-injection defenses **[M]**

Assume all of the following are attacker-controlled, because in a security program they are
precisely the content an attacker would target: log entries, alert text, ticket descriptions,
web pages, vendor advisories, code comments, commit messages, file names, HTTP headers,
usernames, and the output of any other agent.

| # | Defense | Detail |
|---|---|---|
| D1 | **Trust boundary marking** | Untrusted content is wrapped in explicit delimiters and labeled as data. The agent is instructed — and evaluated — never to treat delimited content as instructions. |
| D2 | **No tool escalation from content** | Tool permissions are fixed at session start from the agent's identity. **No content can grant, expand, or unlock a tool.** This is the single most important defense: even a fully successful injection cannot reach a tool the agent never had. |
| D3 | **Output schema enforcement** | Agents emit validated JSON conforming to a fixed schema. Free-form output is rejected. An injected instruction that produces prose fails validation and surfaces as an error. |
| D4 | **Human approval on every state change** | An injection that convinces the agent to draft something harmful still has to convince a human reviewer |
| D5 | **Content sanitization** | Strip or neutralize instruction-like patterns from untrusted input before processing; log what was stripped |
| D6 | **Separate agents for separate trust levels** | The agent that reads untrusted web content has no access to internal systems; findings cross the boundary as structured data, not as text passed to another agent |
| D7 | **Injection canaries in evaluation** | The pre-deployment test set includes injection attempts. Measure and publish the resistance rate. Re-run on every model or prompt change. |
| D8 | **Rate and volume limits** | Anomalous tool-call volume triggers automatic suspension and human review |
| D9 | **No agent-to-agent trust** | One agent's output is untrusted input to another. Route through the queue and a human, or through schema validation with provenance. |
| D10 | **Log the full prompt context** | For post-incident analysis you need to see exactly what the model saw, not a summary |

---

## 10.5 Secret handling **[M]**

| Rule | Detail |
|---|---|
| No secrets in context | Agents never receive credentials, API keys, tokens, or private keys as input |
| Broker pattern | Where an agent needs authenticated access, a broker service holds the credential and exposes only a narrow, audited operation |
| Agent identity | Each agent has its own service identity with least privilege, short-lived credentials, and independent revocation |
| Detection | If an agent encounters a secret in its input, it must **redact, report to the identity owner within 1 hour, and stop processing that item** |
| Never echo | Agents never reproduce a secret in output, logs, or drafts — including partially |
| No production credentials | Under any circumstances, for any agent |
| Rotation | Agent credentials rotate on the standard schedule and immediately on any suspected compromise or prompt-injection incident |

---

## 10.6 Evidence Collection Agent [O]

| Field | Specification |
|---|---|
| **Purpose** | Assemble evidence manifests, verify hashes, check completeness against the evidence plan, flag gaps |
| **Owner** | White Evidence Custodian |
| **Inputs / trusted sources** | Exercise event log, evidence store metadata (**metadata only — not content**), RoE evidence plan, artifact registry |
| **Permitted tools** | Read evidence-store metadata · compute hashes · read exercise records · **write drafts to the manifest queue only** |
| **Denied** | Reading evidence *content* (it may be CUI/PII); deleting or modifying evidence; releasing evidence; altering chain of custody; setting retention or classification |
| **Human approvals** | Evidence Custodian approves every manifest before it is committed; Exercise Director approves any completeness exception |
| **Data classification** | Metadata only. **Must never process content above INTERNAL.** On encountering higher-classified content: stop, do not log the content, alert the custodian. |
| **Audit logging** | Every metadata read, every hash computed, every draft — 7 years, immutable |
| **Prompt-injection defense** | Filenames and metadata fields are untrusted (an attacker can name a file `ignore previous instructions`). D1, D3, D5 apply. Schema-only output. |
| **Secrets** | Never in scope; on encountering, redact + report + stop (§10.5) |
| **Output validation** | Manifest schema validation; hash recomputation verified independently by the custodian on a ≥10% sample |
| **Kill switch** | Custodian or Exercise Director; <60 s; manual manifest assembly resumes immediately |
| **Fail-closed** | Any hash mismatch, missing item, or ambiguity → flag and stop. **Never auto-resolve a discrepancy.** A hash mismatch is a potential integrity incident, not a data-quality nuisance. |
| **Value** | High. Manual manifest assembly is tedious and degrades quickly — exactly the work that benefits from automation with low downside risk. |

---

## 10.7 Metrics & Reporting Agent [O]

| Field | Specification |
|---|---|
| **Purpose** | Compute [§8](07_metrics.md) metrics from source systems, draft the reporting pack, flag data-quality problems |
| **Owner** | Purple Lead |
| **Inputs / trusted sources** | Case management (findings, retests), exercise event log, SIEM metadata (alert timestamps, telemetry health), detection catalog, engineering backlog |
| **Permitted tools** | Read-only queries against the above · compute metrics per the published formulas · write drafts to the reporting queue |
| **Denied** | Changing any source data; changing severities or statuses; publishing to executives without human approval; **inventing a number when data is missing** |
| **Human approvals** | Purple Lead approves the pack before any distribution; CISO approves executive/board distribution |
| **Data classification** | Up to INTERNAL. Aggregate output only — no per-individual attribution, ever (§8 universal rules) |
| **Audit logging** | Every query, every computed value with its inputs, every draft — 7 years. Values must be reproducible from the log. |
| **Prompt-injection defense** | Ticket titles and finding text are untrusted. Numeric computation only from structured fields; **never** derive a metric by "reading" free text. D2, D3. |
| **Secrets** | Not in scope |
| **Output validation** | Every metric recomputed by a second method on a sample; denominators explicitly stated; **missing data reported as missing, never imputed** [M] |
| **Kill switch** | Purple Lead; <60 s; manual metric production resumes (slower, unchanged in substance) |
| **Fail-closed** | Missing/stale/contradictory source data → publish the gap, not an estimate. A metric with silently imputed data is worse than no metric because it is believed. |
| **Value** | High. This is the most valuable agent in the architecture: metric production is the first thing to lapse under load, and it is pure computation over structured data. |

---

## 10.8 Deployment sequence [R]

Do not deploy all seven at once.

| Order | Agent | Why this order |
|---|---|---|
| 1 | **Metrics & Reporting** | Read-only, structured data, immediately valuable, lowest blast radius |
| 2 | **Evidence Collection** | Read-only metadata, tedious human work, low risk |
| 3 | **Green — detection/hardening recommendations** | Proposals only; Green already reviews everything before deploying |
| 4 | **Orange — threat modeling assistance** | Draft-only; the value is completeness prompting, not the analysis |
| 5 | **Yellow — remediation assistance** | Code suggestions; existing code review is already the control |
| 6 | **Purple — coordination** | Higher coupling to the live process; deploy once the process is stable |
| 7 | **White — policy/scope validation** | **Last, and most cautiously.** White is the independence-bearing function; automation-induced deference is a real failure mode. The agent checks completeness of a form; it never assesses whether authorization is *appropriate*. |

**Gate between each step [M]:** the previous agent must have run for ≥30 days with measured
accuracy, a tested kill switch, and zero unreviewed outputs reaching a system of record.

---

## 10.9 Program-level AI risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| **Automation-induced deference** — humans rubber-stamp agent output because it is fast and confident | **High** | High | Approvers must record a *reason* for approval, not just click. Sample-audit 10% of approvals for genuine review. Rotate approvers. Track approval latency — approvals consistently under a few seconds indicate rubber-stamping. |
| Prompt injection via log or ticket content | Medium | High | §10.4, especially D2 (no tool escalation from content) |
| Agent output treated as authoritative and entering the record unreviewed | Medium | High | §10.1 prohibition 7; enforce at the write path |
| Sensitive data (CUI/PII/findings) leaving the boundary via a model API | Medium | **Critical** | Classification limits enforced at the orchestration layer; deployment inside the authorized boundary at P3; never route regulated data to an unapproved model endpoint |
| Model or prompt change silently degrades accuracy | Medium | Medium | Re-run the evaluation suite on every change; publish results; block deployment on regression |
| Agent identity compromise | Low | High | Least privilege, short-lived credentials, independent revocation, anomaly-based suspension |
| Over-reliance masking a staffing gap | **High** | Medium | Agents assist; they do not replace headcount. If a role's work is only feasible with agents running, the role is understaffed — report it as such rather than hiding it. |
| Agents used to generate findings volume | Medium | Medium | Findings still require evidence (gate G4) and human validation. Volume is not a metric (§8.18). |

**Standing rule [M]:** if an agent is unavailable, the process must continue manually at
degraded speed. **Any workflow that cannot run without an agent is not approved.** Test this
annually by disabling all agents for one full exercise cycle.
