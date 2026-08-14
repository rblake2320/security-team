# §9 — Toolchain Architecture

← [Index](../README.md) · Prev → [§8 Metrics](07_metrics.md) · Next → [§10 AI Governance](09_ai_and_automation_governance.md)

---

## 9.0 The rule that governs this entire section

> **Buying a tool does not create a capability.** A tool creates a capability only when there is
> (a) a named owner, (b) a documented process it serves, (c) authorization to use it, and (d)
> staff time to operate it. A BAS platform with nobody to interpret results produces reports
> nobody reads. A SIEM with no detection engineer produces vendor default rules and noise.
>
> **Rule of thumb:** budget **≤35% of program spend on tools, ≥65% on people and time.**
> Programs that invert this ratio reliably produce dashboards instead of security.

Every category below is labeled with whether it is genuinely required, and **what you can do
instead if you cannot afford it**.

---

## 9.1 Tool categories

| # | Category | Label | Primary users | If you cannot afford it |
|---|---|---|---|---|
| T1 | **SIEM / security data platform** | [M] | Green (author), SOC (consume), Purple (validate) | Cloud-native logging (Sentinel/Security Lake/SecOps) with disciplined source selection; retain 90 days hot, archive cold. Do not skip. |
| T2 | **EDR / XDR** | [M] | Green (policy), SOC (respond), Purple (read) | No substitute. This is the highest-value single control for most orgs. Buy this before a SIEM if forced to choose. |
| T3 | **SOAR / automation** | [R] | Green (author), SOC (run) | Scripts + scheduled jobs + your ticketing system's automation. Most SOAR value is enrichment, which is scriptable. |
| T4 | **Threat intelligence** | [M] (feed) / [R] (platform) | Purple, CTI, Green | Free/community sources + ISAC membership + vendor blogs. A paid TI *platform* is [O] below ~2,000 employees. |
| T5 | **Attack simulation / BAS** | [R] | Purple | Open-source emulation (Atomic Red Team-style test libraries) run manually from a controlled host. Cheaper, more educational, more work. |
| T6 | **Vulnerability management** | [M] | Yellow, Green, GRC | Cloud-provider native scanning + OS package auditing + dependency scanning in CI. |
| T7 | **Application security (SAST/DAST/SCA/secrets)** | [M] | Yellow | Your code host's native scanning covers SCA + secrets adequately for P1. Secret scanning is the non-negotiable one. |
| T8 | **Cloud security (CSPM/CNAPP)** | [M] where cloud exists | Green, Yellow | Cloud-provider native posture tooling + policy-as-code in the pipeline. Preventive guardrails beat detective posture scanning. |
| T9 | **Identity security (ITDR / privileged access)** | [M] | Green, SOC | Identity provider's native logs + conditional access + a privileged-access process. Identity is the #1 attack path; do not under-invest here. |
| T10 | **Case management** | [M] | All | Your existing ITSM/issue tracker with a security project. **Do not buy a dedicated one.** |
| T11 | **Git-based remediation** | [M] | Yellow, Green | You already have this. Use it for detection-as-code and the emulation library too. |
| T12 | **CI/CD** | [M] | Yellow | You already have this. The security work is configuring it, not replacing it. |
| T13 | **Evidence storage (immutable)** | [M] | White | Object storage with versioning + object-lock/WORM + restricted deletion. Cheap. No excuse to skip. |
| T14 | **Dashboards** | [R] | All | The SIEM's dashboards + a monthly generated report from the case system. |
| T15 | **Knowledge management** | [M] | All | Existing wiki + Git. The requirement is *findable and versioned*, not *fancy*. |

---

## 9.2 Integration architecture

```
                        +--------------------------+
                        |   THREAT INTEL (T4)      |
                        |   TTPs, actor profiles   |
                        +------------+-------------+
                                     | prioritized techniques
                                     v
  +---------------+          +-------+--------+          +------------------+
  | EMULATION     |  events  |  PURPLE        |  gaps    |  DETECTION-AS-   |
  | LIBRARY (T5/  +--------->+  ORCHESTRATION +--------->+  CODE REPO (T11) |
  | T11, Git)     |          |  (case mgmt T10)|          |  -> CI -> SIEM  |
  +-------+-------+          +---+--------+---+          +---------+--------+
          |                      |        |                        |
          | executes             |        | findings               | deploys
          v                      |        v                        v
  +---------------+              |   +----+-----------+   +--------+---------+
  | TARGET ENV    |  telemetry   |   | ENGINEERING    |   |  SIEM (T1)       |
  | lab/preprod/  +------------->+   | BACKLOG (T10/  |   |  EDR (T2)        |
  | prod          |              |   | T12)           |   |  CSPM (T8)       |
  +---------------+              |   +----+-----------+   |  IDENTITY (T9)   |
                                 |        |               +--------+---------+
                                 |        | fix + evidence          | alerts
                                 |        v                         v
                                 |   +----+-----------+     +-------+--------+
                                 |   | CI/CD (T12)    |     |  SOC / SOAR    |
                                 |   | + regression   |     |  (T3)          |
                                 |   |   tests        |     +-------+--------+
                                 |   +----------------+             |
                                 |                                  | outcomes
                                 v                                  v
                        +--------+----------------------------------+-------+
                        |  EVIDENCE STORE (T13, WORM)  +  METRICS (T14)     |
                        |  hashed, custodied, retained  -> GRC / crosswalk  |
                        +---------------------------------------------------+
```

### The five integrations that actually matter
Most toolchain projects fail by trying to integrate everything. These five carry ~80% of the value:

| # | Integration | Why | Label |
|---|---|---|---|
| **I1** | Finding → engineering backlog (bidirectional status sync) | Without this, remediation happens in a parallel universe and MTTR is unmeasurable | [M] |
| **I2** | Detection-as-code repo → CI validation → SIEM deploy | Gives you versioning, review, rollback, and the ability to prove *when* a detection existed — which is an audit question | [M] |
| **I3** | Exercise events → SIEM (as a labeled data source) | Lets you compute MTTD automatically by joining action time to alert time, instead of by hand | [R], very high value |
| **I4** | Evidence capture → WORM store with automatic hashing | Manual evidence handling degrades within two exercises | [M] |
| **I5** | Emulation library → CI (regression tests) | This is what makes M-13 possible, which is what stops M-9 recurrence | [R], the compounding one |

### Integration patterns
| Pattern | Use for | Notes |
|---|---|---|
| **Git as source of truth** | Detections, test cases, IaC policy, threat models | Review, history, rollback, and provenance for free |
| **Webhook / event-driven** | Finding creation → ticket; alert → case | Prefer over polling; log every delivery for the audit trail |
| **Scheduled batch reconciliation** | Metrics, coverage layers, telemetry health | Nightly is sufficient; do not build real-time metrics |
| **Read-only API access for Purple** | SIEM/EDR/cloud queries | Enforces the "Purple does not deploy content" separation at the technical layer, not just the policy layer |
| **Write-restricted evidence store** | All evidence | Participants can write once; only the custodian can delete |
| **Schema contract** | The [§6.4 JSON formats](05_communication_protocol.md) | Version them; reject unknown fields rather than silently dropping data |

---

## 9.3 Access model by team

| System | Purple | White | Yellow | Green | Orange | SOC |
|---|---|---|---|---|---|---|
| SIEM | Read + saved search | Read (adjudication) | Read own service | **Author + deploy** | Read | Read + triage |
| EDR/XDR | Read; **no prod response** | Read | — | Policy admin | Read | Respond |
| SOAR | Read | Read | — | Author + deploy | — | Execute |
| BAS / emulation | **Operate** | Read | — | Read results | Lab only | Read results |
| Vuln mgmt | Read | Read | Read own assets | Read | Read | Read |
| AppSec (SAST/DAST/SCA) | Read | — | **Own** | Read | Read | — |
| CSPM/CNAPP | Read | Read | Read own | **Admin** | Read | Read |
| Identity platform | Read logs | Read | — | **Policy admin** | Read logs | Read logs |
| Case management | **Own exercise cases** | **Own exercise record** | Own tickets | Own tickets | Own reviews | Own cases |
| Git (app code) | Read | — | **Write** | Read | Read | — |
| Git (detection-as-code) | Read + propose | Read | — | **Write** | Read | Propose |
| Git (emulation library) | **Write** | Read | Read | Read | Write | Read |
| CI/CD | Read | Read | **Own** | Contribute | Contribute tests | — |
| Evidence store | Write-once | **Custodian** | Write-once | Write-once | Write-once | Write-once |
| Production admin | **Denied** | **Denied** | Per normal policy | Per change mgmt | **Denied** | Per IR policy |

**[M] "Purple denied production admin" and "Orange denied production" must be implemented through technical IAM controls,
not by policy alone.** A rule that depends on someone remembering it will be broken under time
pressure, and the resulting incident will be indistinguishable from an attack.

---

## 9.4 Budget-tiered recommendations

Costs are **rough planning ranges, not quotes** — they vary enormously by seat count, data
volume, and negotiation. Validate before budgeting.

### P1 — small / commercial (~$150K–$750K total security spend)
| Buy | Skip | Rationale |
|---|---|---|
| EDR/XDR [M] · cloud-native SIEM with tight source selection [M] · code-host native SCA + secret scanning [M] · cloud-provider native CSPM [M] · object storage w/ lock for evidence [M] | BAS platform · TI platform · SOAR · dedicated case management | At this size the constraint is *people*, not tools. One good engineer with an EDR beats four products with nobody to run them. |
| **Emulation:** open-source test library, run manually | | Educational and free; the manual effort is the training |
| **Indicative incremental cost** | ~$15K–$40K/yr beyond existing spend | Mostly evidence storage and log retention |

### P2 — mid / regulated (~$1.5M–$6M)
| Buy | Consider | Skip |
|---|---|---|
| Everything in P1, plus: SIEM with real retention [M] · CNAPP [M] · ITDR or identity-focused detection content [M] · DAST/API scanning [M] · SOAR [R] | BAS platform [R] if exercise cadence >8/yr *and* someone owns it · TI platform [R] | Dedicated purple-team platform · dedicated case management |
| **Indicative incremental cost** | ~$120K–$300K/yr tooling + ~$400K–$700K/yr staffing (1.5 net-new FTE + allocations) | |

### P3 — government / CUI / IL4+
| Additional requirements | Note |
|---|---|
| FedRAMP-authorized SaaS or on-prem/gov-cloud equivalents for anything touching CUI [M] | This constrains tool choice more than budget does — **verify authorization status before selection, not after** |
| STIG-compliant configuration of the tools themselves [M] | The security tooling is in scope for hardening too |
| Separate accredited evidence storage inside the boundary [M] | |
| Approved cross-domain/transfer procedures where enclaves differ [M] | |
| **Indicative incremental cost** | ~$300K–$900K/yr tooling + $1.2M–$3M/yr staffing including contract labor | |

---

## 9.5 Tool selection criteria

Score candidates on these, weighted for your context. **Reject any tool scoring 0 on a [M] row.**

| Criterion | Weight | [M]? | Test during evaluation |
|---|---|---|---|
| API completeness (can you get your data out?) | High | [M] | Extract 30 days of a real data type via API in the trial |
| Data residency / boundary compliance | High | [M] at P3 | Written confirmation, not a sales claim |
| Detection-as-code support (export/import/version rules) | High | [M] for SIEM | Round-trip a rule through Git and back |
| Existing team skills | High | — | Who will operate it on day 91? Name them. |
| Total operating cost incl. data ingestion at 3× current volume | High | [M] | Model it; ingestion pricing is where budgets die |
| Integration with I1–I5 | High | [M] | Build one integration during the trial, not after purchase |
| Ability to run in an authorized environment | High | [M] at P3 | |
| Vendor lock-in / exit cost | Medium | — | Can you export detections, cases, and evidence on exit? |
| Roadmap and support model | Medium | — | |
| Marketing claims about AI | **Zero** | — | Evaluate what it does, not what it is called |

**[M] Run a real exercise during every trial.** Vendor demos are built to succeed. Run pilot
scenario TC-001 through the trial tool and see whether it produces a finding you can action.

---

## 9.6 Anti-patterns

| Anti-pattern | Why it fails | Do instead |
|---|---|---|
| Buying a BAS platform to "be" a purple team | BAS produces test results; purple teams produce organizational change. The platform cannot facilitate a validation session or write acceptance criteria. | Staff the coordination role first; buy BAS when the human is saturated |
| A dedicated "purple team platform" separate from engineering tooling | Second source of truth; nobody updates it; remediation drifts | Use the engineering backlog and existing case management (§7.4) |
| Ingesting everything into the SIEM | Cost explosion → panic reduction → the wrong sources get cut → detections silently die | Source selection driven by the prioritized technique list; measure M-10 |
| Detections authored only in the SIEM UI | No version history, no review, no rollback, no ability to prove when a detection existed | Detection-as-code in Git with CI validation |
| Automated destructive response without approval gates | One false positive isolates production | Human approval gate on destructive actions; automate enrichment freely |
| Tool sprawl from acquisitions and pilots | Nobody owns half of them; overlapping coverage creates false confidence | Annual tool inventory with a named owner per tool; retire the unowned |
| Buying tools before closing Open Decision O-2 (classification) | You may buy something you cannot legally put your data in | Close O-2 first |
