# §16 — Why Engine and Soul System Integration

← [Index](../README.md) · Related → [§4 Workflow](03_end_to_end_workflow.md) · [§7 Artifacts](06_artifact_index_and_standards.md) · [§8 Metrics](07_metrics.md)

**Status:** wiring specification. Both systems already exist and run on this machine.
**Repos:** `github.com/rblake2320/why-engine` · `github.com/rblake2320/soul-system`
**Local:** `C:\Users\techai\why-engine` · `C:\Users\techai\soul-system`
**Verified present 2026-08-14:** why-engine CLI responds (`collect-evidence · analyze · publish ·
capture-and-publish · promote-why · search|recall · stats · doctor · audit-repair · verify-audit ·
verify-audit-chain · start-mcp`); a live case store exists at `PKA testing\.why-engine\` with
real WhyCases.

> **Implementation status — MANUAL PRACTICE.** No executable consumer in this program invokes
> Why Engine or Soul. Every trigger and recall point below is a human procedure/checklist item,
> not an automated control. Automation may be credited only after code and falsification tests
> are added; absence of a marker or recall result does not block the current runner.

---

## 16.1 Why these two, and what each is for

The operating model has a known weak point, stated plainly in [§14.4](13_final_recommendation.md)
as organizational risk #3: **theater** — exercises run, reports written, nothing changes. The two
systems attack that from opposite ends.

| | **Why Engine** | **Soul System** |
|---|---|---|
| Captures | **Root-cause knowledge** — why it broke, why it wasn't caught, why the fix worked, how to prevent it | **Behavioral learning** — decisions, corrections, pain points, outcomes |
| Unit | WhyCase (structured, hash-audited) | Ledger entry (append-only, hash-chained) |
| Answers | *"Has this failure happened before?"* (`why.recall`) | *"What did we already learn about how to work here?"* (session recall) |
| Serves metric | **M-9 recurrence** · M-13 regression conversion | Process quality; reduced repeat mistakes |
| Consumer | Humans and agents, before writing a fix | Every agent session, automatically |
| Retention | Case store + audit chain | Ledger + `LEARNED.md` digest |

**They are not evidence stores.** [White's WORM evidence manifest](06_artifact_index_and_standards.md)
remains the system of record for exercise evidence. These two carry *learning*, and learning has
different retention, different classification, and a different audience.

---

## 16.2 The mapping that makes this work

The WhyCase schema and this model's artifacts line up almost field for field — which is the real
argument for wiring them rather than inventing a parallel format.

| WhyCase field | Comes from | Note |
|---|---|---|
| `title` | Finding title (A5) | Describe the weakness, not the exploit |
| `rootCause` | Finding root cause / incident cause | Blue's declared-unknown is valid input: say "unknown" honestly |
| **`whyNotCaught`** | **The six-stage outcome chain** | This is the single best fit in the whole integration. "Prevented: no. Logged: full. Alerted: no alert. Investigated: n/a." *is* why it wasn't caught, in structured form. |
| `whyFixWorked` | Retest Record (A9) verdict + delta | Only populated **after** a passing retest — never from the fix author's assertion |
| `preventNextTime` | Acceptance criteria + regression test ID + paved road | |
| `generalizablePattern` | Orange's attack-path catalog pattern | The field that makes a case reusable rather than a diary entry |
| `evidence` | Commit range, diff summary, file list | Code-side evidence only — **not** exercise evidence (see §16.4) |
| `tags` | Exercise ID, ATT&CK technique, severity, team | Makes `stats` recurring-cluster detection useful |
| `sensitivity` | **`internal` by default** | See §16.4. Never `public` for exercise or incident material. |

### Where WhyCases are created — three triggers, all mandatory

| # | Trigger | Owner | Workflow stage |
|---|---|---|---|
| **W-1** | A finding is **closed by a passing retest** | Purple | [Stage 12→13](03_end_to_end_workflow.md) |
| **W-2** | An **incident is closed** | Blue (incident commander) | Closure gate B14 |
| **W-3** | A **systemic lesson** is confirmed (same lesson in 3 exercises, or a recurrence) | Purple / Orange | Stage 16 |

This aligns with the PKA workspace rule already in force — *"Every confirmed root cause
resolution produces a WhyCase. No exception."* — and gives it a precise definition of
"confirmed": **a passing retest, not an assertion of completion.**

### Where `why.recall` is called — before work, not after

| # | Call point | Who | Why it matters |
|---|---|---|---|
| **R-1** | Before starting remediation on a finding | Yellow | "This root cause has occurred twice before" changes the fix from a patch to a platform decision |
| **R-2** | Before triage of a non-obvious alert | Blue | Prior root causes reframe the investigation immediately |
| **R-3** | Before scenario selection | Purple | A cluster in `why-engine stats` is a ranked list of what actually keeps breaking — better than intuition |
| **R-4** | Before a design review | Orange | Feeds the attack-path catalog with real history |

```bash
why-engine search --repo-path . --query "<the raw error, finding title, or alert text>"
why-engine stats  --repo-path .          # recurring root-cause clusters = M-9 in narrative form
```

> **`stats` recurring clusters and metric M-9 (recurrence) measure the same thing from different
> ends.** M-9 counts it; `stats` explains it. When they disagree, one of the two pipelines is
> broken — that disagreement is a useful monthly check.

---

## 16.3 Soul System wiring

Soul captures how the *team and its agents* work, not what the systems do. Markers are
line-anchored, so they must start the line.

| Marker | Emitted when | By |
|---|---|---|
| `SOUL-DECISION:` | White records a decision that changes scope, safety, severity, or status ([§6.5](05_communication_protocol.md)) | White |
| `SOUL-LEARNING:` | A lesson is classified **Improve** or **Systemic** (stage 16) | Any team |
| `SOUL-PAIN:` | A stop event, a failed retest, or a rollback that did not work as documented | Purple / White / Blue |
| `SOUL-OUTCOME:` | A retest verdict, or a risk acceptance reaching expiry | Purple |
| `SOUL-NOTE:` | Durable operational context worth carrying between sessions | Any |

**Constraints that are not optional:**

| # | Constraint | Reason |
|---|---|---|
| **S-1** | **No CUI, PII, PHI, cardholder data, credentials, or evidence content in soul ledgers, ever.** Markers carry *behavioral* statements, not findings. | Soul is not an accredited store and is not in the RoE's data-handling scope ([§5.9](04_rules_of_engagement_template.md)) |
| **S-2** | Soul is **never** the system of record for a decision. White's Decision Log is. A `SOUL-DECISION:` marker is a *copy for learning*, and the two must not diverge. | [§7.4](06_artifact_index_and_standards.md) single-source-of-truth |
| **S-3** | Soul's trust model quarantines non-user-authored and synced content by design. **Leave that on.** Recall injects into every session, so unquarantined inbound content is a prompt-injection path. | Matches [§10.4 D9](09_ai_and_automation_governance.md): no agent-to-agent trust |
| **S-4** | Exercise details under a **blind phase** are never emitted as markers until the phase ends | Recall would leak them into another session |
| **S-5** | Soul stays disconnected from the Brain and from MemoryWeb — no undeclared parallel memory-write paths | Existing standing decision; unchanged by this model |

---

## 16.4 Publication and classification — the hard constraint **[M]**

**Why Engine can publish to aihangout.ai. Exercise and incident material must never take that
path.**

| Rule | Detail |
|---|---|
| **P-1** | All security-program WhyCases are created with `--target outbox`. **Never `--target api`, never `--target both`.** |
| **P-2** | `sensitivity` is `internal` at minimum. Findings on crown jewels, attack paths, and risk acceptances are `confidential` and are **not** candidates for promotion. |
| **P-3** | `promote-why` requires `sensitivity === "public"` — which security-program cases never are. **Therefore no security WhyCase is ever promoted to a public surface.** This is enforced by the tool, and stated here so nobody tries to work around it. |
| **P-4** | The PKA workspace data-isolation rule already forbids passing workspace, owner, or session content to any external API. Exercise findings are squarely inside that prohibition. |
| **P-5** | Why Engine's secret scanner is a backstop, not the control. **The control is not collecting the material in the first place** (RoE §5.9 minimization). A case that needs redaction to be safe was written wrong. |
| **P-6** | `generalizablePattern` is the one field written to be *shareable in principle* — a pattern with no system names, no identifiers, and no architecture detail. Even so: outbox only, and Legal approves any external use. |

**A useful sanity test before saving a case:** if this text appeared in a competitor's hands,
would it help them attack us? If yes, it is `confidential` and stays local.

---

## 16.5 Per-team obligations

| Team | Why Engine | Soul System |
|---|---|---|
| 🟣 **Purple** | **Owns W-1 and W-3.** Creates the case at retest closure. Runs `stats` monthly and reports clusters alongside M-9. | `SOUL-OUTCOME:` on retest verdicts; `SOUL-PAIN:` on failed retests |
| ⚪ **White** | Verifies a WhyCase exists before an exercise is formally closed (RoE §5.19 checklist). Does not author them. | **Owns `SOUL-DECISION:`** — but the Decision Log remains the record (S-2) |
| 🟡 **Yellow** | **Calls R-1 before every remediation.** Supplies `whyFixWorked` evidence via the fix evidence package. | `SOUL-LEARNING:` on systemic engineering lessons |
| 🟢 **Green** | Supplies `whyNotCaught` telemetry/detection detail. Uses clusters to prioritize paved roads. | `SOUL-PAIN:` on silent-telemetry events |
| 🟠 **Orange** | **Owns `generalizablePattern` quality.** Calls R-4 before design reviews; feeds the attack-path catalog. | `SOUL-LEARNING:` on design patterns |
| 🔵 **Blue** | **Owns W-2** at incident closure (B14). Calls R-2 during triage. | `SOUL-PAIN:` on rollbacks that did not work as documented |

---

## 16.6 Health and integrity

Both systems maintain hash-chained audit logs, and both can be tampered with or corrupted. Treat
their health as an operational check, not an assumption.

```bash
why-engine doctor --repo-path .          # 8-point health check, exit 1 on failure
why-engine verify-audit --repo-path .
soul audit-verify
```

| Check | Frequency | Owner | On failure |
|---|---|---|---|
| `why-engine doctor` | Weekly | Purple | Exit 1 → investigate before creating more cases |
| `why-engine verify-audit` | Monthly + at exercise close | Purple → White | Chain invalid = integrity incident, escalate |
| `soul audit-verify` | Monthly | Whoever owns the workstation | Corrupt chain → archive and start a fresh chain, record why |
| Cluster vs. M-9 agreement | Monthly | Purple | Disagreement means one pipeline is broken |

**Known limitation, stated rather than assumed:** a torn audit tail from a crash is classified and
repairable (`doctor --fix`, `audit-repair`); mid-log corruption is **non-repairable tamper
evidence** and must be treated as such. Do not "fix" it away.

---

## 16.7 What this does not do

- It does not replace the evidence manifest, the risk register, or the engineering backlog.
- It does not make findings compliant, authorized, or closed. **Only a passing retest or a signed
  risk acceptance closes a finding.**
- It does not remove the need for [stage 16](03_end_to_end_workflow.md) lessons learned. A
  WhyCase is the durable, searchable form of a lesson — the routing to an owner with a due date
  still has to happen.
- It does not justify skipping the AAR. The AAR is White's independent product; a WhyCase is
  Purple's or Blue's operational one.
