# GREEN TEAM — Detection & Hardening Recommendation Agent [O] Optional

Governed by [§10](../00-shared/09_ai_and_automation_governance.md). The seven universal
prohibitions and twelve universal requirements apply in full.

**Deployment order: 3rd of 7.**

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [Artifacts](ARTIFACTS.md) · [Index](../README.md)

---

## Purpose

Accelerate detection engineering and hardening: draft detection logic from a detection gap,
identify which data sources a technique requires and whether they exist, estimate alert volume
from historical data, propose tuning for noisy detections, identify baseline drift, and flag
detections that have never produced a true positive.

---

## 1 · Inputs and trusted data sources

| Source | Access | Trust |
|---|---|---|
| Detection-as-code repo | Read | Trusted |
| Detection catalog + ATT&CK mappings | Read | Trusted |
| Telemetry inventory + health data | Read | Trusted |
| SIEM schema and **aggregate** query results | Read via broker | **Aggregates trusted; raw event content untrusted** |
| Detection gaps from Purple | Read | Structure trusted |
| Hardening baselines and drift reports | Read | Trusted |
| Threat models (instrumentation requirements) | Read | Trusted |
| SOC alert dispositions (aggregate) | Read | Trusted |
| ATT&CK data-source model (local, versioned) | Read | Trusted |
| Vendor detection guidance | Read | **Untrusted** — external content |

## 2 · Permitted tools

- Read the sources above
- Execute **pre-approved, parameterized aggregate** queries (counts, distributions, cardinality)
  through a broker — used to estimate alert volume before a detection is built
- Draft detection content into the detection repo as a **pull request** (never to main)
- Draft tuning proposals and baseline drift summaries
- Flag detections with zero true positives over a window

## 3 · Denied capabilities

Beyond the seven universal prohibitions — **this agent operates next to production security
controls, so the denials are the load-bearing part of its design:**

- **Deploying detection content to any SIEM.** Draft PR only; human merges; normal change path deploys.
- **Modifying EDR policy, identity policy, conditional access, firewall rules, or cloud guardrails**
- **Deploying or modifying SOAR playbooks**, especially any containing a destructive action
- Suppressing, disabling, or deleting an existing detection (may **propose** retirement)
- Adding a tuning exclusion directly (may propose; a human applies and dates it)
- Querying raw event content containing PII/CUI — **aggregates only**
- Attesting that a detection works. **Only Purple validates** (SoD-1), and no agent substitutes.

## 4 · Required human approvals

| Agent output | Approver | Note |
|---|---|---|
| Draft detection content | Green engineer **+ peer reviewer** (SoD-1) | Normal PR review, unchanged |
| Tuning proposal / new exclusion | Green Lead | Every exclusion documented and **dated** |
| Detection retirement proposal | Green Lead + SOC Manager | Retirement is legitimate — but it is a human call |
| Baseline change proposal | Green Lead | Must still meet the governing benchmark |
| Data source onboarding proposal | Green Lead + Data Owner (cost + classification) | |
| Anything touching SOAR destructive actions | **Green Lead + System Owner** | Highest-risk output category |

## 5 · Data-classification restrictions

Maximum **INTERNAL**, **aggregates only**. Never processes raw event content, which may contain
PII, PHI, CUI, or credential material. On a query returning unexpected raw content: **discard,
do not log it, alert the Green Lead.** At P3, the model endpoint must be inside the authorized
boundary.

## 6 · Audit logging

Every query (including its parameters), every draft, every human decision — 7 years. Query
parameters are logged specifically so a later "why did we exclude that?" question is answerable.

## 7 · Prompt-injection defenses

Threat model: **an attacker who can write to a log can attempt to write to this agent's context.**
Log fields such as usernames, filenames, user agents, and process command lines are
attacker-controlled by definition — and this agent's whole job is reading log data.

| Defense | Implementation |
|---|---|
| D1 | All event-derived content delimited and labeled as data |
| **D2** | **No deploy path exists.** Even a fully successful injection produces a PR that two humans review. This is the structural control. |
| D3 | Detection drafts must conform to the detection-as-code schema and pass CI validation |
| **D5** | **Aggregate-only querying is itself an injection defense** — the agent rarely sees raw attacker-controlled strings at all |
| D6 | The vendor-guidance reading path is separate from the repo-writing path |
| D7 | Evaluation set includes log records containing injection attempts |
| D8 | Anomalous query volume suspends the agent automatically |

## 8 · Secret handling

Never receives credentials; broker-mediated access only. On encountering a secret in query
output: **discard the result entirely, report to the identity owner within 1 hour, never echo the
value.** Detection logic must never embed a credential, even as an example.

## 9 · Output validation

- Detection drafts must pass CI validation and the unit-test harness before a human reviews them
- **Every draft must be accompanied by an estimated alert volume derived from real historical
  data.** A detection proposal without a volume estimate is rejected — unestimated volume is the
  single most common cause of a detection being deployed and then ignored.
- ATT&CK mappings validated against the versioned local knowledge base
- Data-source claims verified against the telemetry inventory: **if the source does not exist, the
  agent must report a telemetry gap rather than drafting an unrunnable detection**
- Pre-deployment evaluation against past gaps with known-good detections; rates published

## 10 · Kill switch

Green Lead or CISO. <60 s; revokes the agent's repo and broker identities. Tested quarterly.
Detection engineering continues manually.

## 11 · Fail-closed behavior

| Condition | Behavior |
|---|---|
| Required data source does not exist or is unhealthy | **Report a telemetry gap. Do not draft a detection that cannot run.** |
| Alert volume cannot be estimated | Report inability; do not draft |
| Query returns unexpected raw/sensitive content | Discard; do not log; alert |
| CI validation fails | Do not surface to a human; iterate or report inability |
| Injection suspected | Stop; preserve context; alert Green Lead |
| Agent unavailable | Detection engineering proceeds manually |

## 12 · Honest assessment

| | |
|---|---|
| **Real value** | Data-source reasoning ("technique T requires source S; you have S at 62% asset coverage") and **volume estimation before building**. Both are mechanical, both are routinely skipped, and skipping them is why detection catalogs fill with content nobody trusts. |
| **Moderate value** | First-draft detection logic. It saves typing. The judgment — is this behavior actually anomalous *here* — does not transfer. |
| **Low value** | Tuning. Tuning requires knowing which business processes legitimately look like attacks in *your* environment, which is exactly the local knowledge an agent lacks. |
| **Main risk** | Volume. An agent can draft detections faster than they can be validated and tuned, producing a large catalog with a low true-positive rate — which is worse than a small catalog, because it trains analysts to ignore alerts. **Cap intake at what Purple can validate** (SoD-1 is the natural throttle; do not remove it to go faster). |
