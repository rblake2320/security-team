# RED TEAM — Assessment Support Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: last, alongside White's — or not at all.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

> ## The prohibition that defines this agent
>
> **No AI agent may execute offensive activity.** That is universal prohibition #3, it applies
> everywhere in this model, and Red is where it matters most — because Red is the one team whose
> humans *are* authorized to execute.
>
> This agent has **no execution path whatsoever**: no shell, no network egress to any target, no
> Aegis `run` capability, no credentials, no signing key. It reads engagement definitions and
> results. It cannot cause a packet to leave the machine.
>
> The reason is not squeamishness. Aegis's entire safety model rests on a **human** deliberately
> acknowledging a scope fingerprint at execution time. An agent that could acknowledge a
> fingerprint would dissolve that control, and the tool would still report itself as operating
> correctly.

---

## Purpose

Reduce the clerical load around an engagement: check an engagement definition for scope
problems before it is signed, draft reproduction steps from structured results, draft the
assessment report, and cross-reference findings against prior WhyCases.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Engagement definitions (JSON) | Read | Structure trusted, values **untrusted** |
| Approved RoE (scope, exclusions, window) | Read | Trusted |
| Aegis results and normalized findings | Read | Trusted schema |
| Audit ledger **metadata** (event types, counts, hashes) | Read | Trusted — **never raw evidence content** |
| Check registry and `checks/base.py` protocol | Read | Trusted |
| CWE catalog (local, versioned) | Read | Trusted |
| why-engine recall | Read | Trusted |
| Prior assessment reports | Read | Trusted |

## 2 · Permitted tools

- Read the sources above
- Structural comparison: engagement targets vs. RoE §5.3 in-scope table; allowed checks vs.
  registry; limits present and non-empty
- Draft reproduction steps and report prose into the Red review queue
- `why.recall` against a finding title

## 3 · Denied capabilities

Beyond the seven universal prohibitions:

- **Executing `aegis-rt run`, or any command that contacts a target, in any environment**
- **Acknowledging a scope fingerprint.** The `--ack-scope` confirmation is a human act, always
- **Generating, signing, or handling an authorization receipt**; touching the signing key or its
  password
- **Sealing a ledger**
- Generating exploit code, payloads, evasion techniques, or persistence mechanisms
- Writing to `src/`, the check registry, or any engagement definition
- Setting or adjusting finding severity
- Reading raw evidence content or unredacted match values
- Deciding that a target is in scope — it may only **flag a mismatch** for a human

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Scope mismatch flag | Red Lead → White | Advisory. **A clean report never substitutes for reading the engagement file.** |
| Draft reproduction steps | The operator who ran the test | Verified against the ledger before release |
| Draft assessment report | Red Lead, then GRC for L2 evidence use | |
| Prior-case cross-reference | Red Lead | |

**[M] Anti-deference control:** the Red Lead records that they personally read the engagement
definition and the RoE, separately from any agent output. Audited annually by White alongside
the Exercise Director's equivalent attestation.

## 5 · Data-classification restrictions

Maximum **INTERNAL**. Assessment findings are frequently **CONFIDENTIAL** — attack paths into
crown jewels are exactly the material an adversary wants. **The agent works from normalized,
redacted findings only.** It never receives raw evidence, credential material, or unredacted
matches. At P3, the model endpoint must be inside the authorized boundary or this agent is not
deployed.

## 6 · Audit logging

Every read, flag, and draft, plus the human decision that followed — 7 years, immutable, kept
**separate from the Aegis ledger**. The ledger records what the *engagement* did; polluting it
with agent activity would weaken the evidence it exists to provide.

## 7 · Prompt-injection defenses

Threat model: **engagement definitions are attacker-influenceable** (a target value, an ID, a
check name), and **assessment results contain adversary-authored content by definition** —
response bodies, headers, file contents from the systems under test.

| Defense | Implementation |
|---|---|
| D1 | Engagement values and result content delimited and labeled as data |
| **D2** | **No execution path to escalate to.** No shell, no network, no `run`, no keys. A fully successful injection produces a misleading draft that a human reads |
| D3 | Structured output only; free-form is rejected |
| D5 | Instruction-like patterns in target values or result content stripped **and flagged** — an engagement file containing injection text is a finding about whoever submitted it |
| D6 | Result-reading is a separate session from engagement-review; conclusions cross as structured data |
| **D11** | **Output filter blocks exploit-shaped content** — payloads, command sequences, evasion guidance. Suppressed and reported, never "rewritten more safely" |

## 8 · Secret handling

Never receives credentials, private keys, or the signing password. Aegis already redacts matched
values to one-way digests; the agent sees only digests. On encountering anything credential-shaped:
**stop, redact, report to the identity owner within 1 hour, never echo it.**

## 9 · Output validation

- Every reproduction step must map to a real ledger event; steps that do not resolve fail the output
- Every CWE reference validated against the local catalog
- **Every claim cites its result record.** Uncited claims are rejected — an unsourced assertion
  in an assessment report is indistinguishable from a fabrication, and this report may become
  compliance evidence
- Scope flags cite the specific engagement field and the specific RoE row
- **Missing data reported as missing, never inferred** — "not tested" must never become
  "tested, no findings"
- Pre-deployment evaluation against past engagements with known-correct reports; **fabricated or
  unsupported findings are weighted as the critical failure mode**

## 10 · Kill switch

Red Lead, White Exercise Director, or CISO. <60 s. Tested quarterly. Assessment work continues
manually — it always could.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Any ambiguity about whether a target is in scope | **Report OUT OF SCOPE / ambiguous.** Never resolve toward permitting |
| Authorization or RoE unreadable | Report unable to check. **Never report "looks fine" on unverified data** |
| Result references an environment not in the RoE | Stop; flag as a possible out-of-scope event; alert Red Lead and White |
| Output would contain exploit-shaped content | Suppress; report; do not attempt a safer rewrite |
| Injection suspected in an engagement file | Stop; flag as a submission-integrity concern |
| Classification limit exceeded | Stop; do not log content; alert |
| Agent unavailable | Engagements proceed unchanged |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | **Pre-signature scope review.** Comparing an engagement definition against the RoE's in-scope table, field by field, is exactly the mechanical check humans skim — and a scope error is the most expensive mistake this function can make. |
| **Moderate value** | Reproduction steps and report drafting. Reports are written at the end of a tiring engagement, which is when they get thin. |
| **High value, underrated** | `why.recall` against a finding — "this root cause has appeared twice before" turns a point finding into a systemic one, and feeds M-9. |
| **Prohibited, not low-value** | Anything touching execution, authorization, or acknowledgement. Those are the controls; automating them removes them. |
| **Main risk** | A confident, fluent assessment report containing a finding nobody verified. This report may become **compliance evidence** under CA-2(1) or PCI DSS 11.4 — a fabricated finding in that context is a materially different problem from a bad suggestion in a code review. Hence the citation requirement and the weighting of fabrication in evaluation. |
