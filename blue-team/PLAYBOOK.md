# BLUE TEAM — Playbook

← [Charter](CHARTER.md) · [Artifacts](ARTIFACTS.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> **Internal runbooks already exist and are not restated here:**
> [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md) (severity, 8-step lifecycle),
> [`docs/DETECTION_ENGINEERING.md`](docs/DETECTION_ENGINEERING.md) (validation matrix, tuning
> rules), [`docs/OPERATING_MODEL.md`](docs/OPERATING_MODEL.md) (shifts, quality gates),
> [`docs/ADVERSARIAL_REVIEW.md`](docs/ADVERSARIAL_REVIEW.md), and
> [`docs/DEPLOYMENT_CHECKLIST.md`](docs/DEPLOYMENT_CHECKLIST.md).
>
> **This playbook covers only what those cannot: working with the other five teams.**

---

## 1. Workflow stages Blue owns

| Stage | Blue's role | Gate |
|---|---|---|
| 8 · Execution (exercise) | **R** — monitor as normal; do not stand down | Deconfliction answered ≤5 min; ambiguity treated as real |
| 9 · Detection validation | **R** (Purple accountable) | Blue discloses exactly what was seen, including nothing |
| 10 · Finding classification | C | Blue's triage record is the evidence for six-stage stage 4 |
| 16 · Lessons learned | R | Hunt/incident lessons become detections or scenarios, not documents |
| — · Live operations | **A** | B14: no incident closed without cause-or-declared-unknown |

**Six-stage ownership split — worth internalizing:** stages 1–3 (prevented / logged / alerted)
grade **Green's** work. Stages 4–6 (investigated / contained / reported) grade **Blue's**. When a
technique alerts but is misclassified, that is a Blue finding, not a Green one — and it is the
failure mode nobody counts unless the six-stage chain is scored honestly.

---

## 2. Daily rhythm

Sentinel Blue commands, run against the operational store:

```powershell
python -m blue_team.cli health   --db runtime\blue.db     # FIRST, every shift
python -m blue_team.cli alerts   --db runtime\blue.db
python -m blue_team.cli verify-ledger --db runtime\blue.db
python -m blue_team.cli coverage                          # declared coverage
python -m blue_team.cli validate                          # config integrity
```

| When | Activity |
|---|---|
| **Every shift start** | `health` first. A silent sensor means every detection depending on it is down. Then the queue. |
| Continuous | Critical queue · sensor blind spots · audit integrity · active incidents |
| Daily | Stale alerts · identity and control changes · exposed assets · backup failures |
| Weekly | Threat hunt · **tuning requests to Green** · false-negative review · case aging |
| Monthly | Tabletop · restore sample · privileged-access review · **audit head-hash export to White** |
| Quarterly | Full incident exercise · crown-jewel threat model with Orange · supplier exercise · DR proof |

---

## 3. Runbook — exercise participation

The single most important Blue runbook in this model, and the one most often got wrong.

```
BEFORE
  - You are told an exercise WINDOW exists. You are NOT told the plan.
  - Registered indicators (source IPs, identities, markers) go to the SOC LEAD only,
    sealed. Analysts work the queue normally.
  - Confirm the deconfliction channel is live and you know who answers it.

DURING -- operate NORMALLY. This is the whole point.
  - Triage as you would any alert. Do not soften. Do not look for the exercise.
  - If something looks real: RESPOND AS IF IT IS REAL, and query deconfliction
    in parallel. Never wait on deconfliction before responding.
  - Query -> #ex-<ID>-deconflict -> expect EXERCISE / NOT EXERCISE / UNKNOWN in 5 min.
      EXERCISE       -> keep practicing the response. Suppress ONLY external
                        notification and destructive containment. Record the time.
      NOT EXERCISE   -> declare a real incident. Full IR.
      UNKNOWN / no answer in 5 min -> TREAT AS REAL. Always.
  - Anything unsafe: call STOP. No justification needed at the time.

AFTER -- the collaborative validation session
  - Disclose exactly what you saw, when, and what you did with it.
  - Disclose what you did NOT see. That is the most valuable sentence in the room.
  - Findings are about SYSTEMS, never about analysts. If that slips, say so
    immediately -- once analysts feel graded, the data becomes useless.
```

**Never** stand the SOC down for an exercise window. A SOC that stops working during exercises
teaches an adversary exactly when to operate, and produces detection metrics that mean nothing.

---

## 4. Runbook — real vs. exercise, at 03:00

```
Suspicious activity observed
   |
   +-- Matches a pre-registered indicator?  -> log as exercise, KEEP RESPONDING
   |
   +-- Otherwise -> query deconfliction, and START RESPONDING NOW
                     (the two happen in parallel, never in sequence)
   |
   +-- Ambiguous, contradictory, or no answer -> IT IS REAL
```

**The rule, in one line: you never lose by treating an exercise as real. You can lose everything
by treating a breach as an exercise.** This belongs in the IR plan itself, not only in exercise
documentation — the analyst at 03:00 reads the IR plan.

---

## 5. Runbook — feeding Green (C-1 boundary)

Blue does not write production detections. Blue produces the three things Green cannot generate
alone:

| Blue produces | Format | Green's action |
|---|---|---|
| **False positive** | Detection ID + sample events + the benign process it matched | Tune, narrow, downgrade, or retire |
| **False negative** | What happened, what should have alerted, which source held the evidence | New or corrected detection content |
| **Telemetry gap from the consumer side** | "We needed field F from source S during case C and it was absent/empty/late" | Pipeline work — this is the highest-signal telemetry feedback there is |

**Tuning requests must name the benign behavior**, not the noisy rule. "DET-0231 is noisy" is
not actionable. "DET-0231 matches the nightly backup service account rotating its own
credential" is a fix. Blue's own standard forbids tuning by excluding a whole admin group,
product, or host class — hold that line even when the queue hurts.

---

## 6. Runbook — feeding Purple (C-6, C-10)

```
INCIDENT CLOSED
  -> within 30 days, joint review with Purple: "could we have caught this earlier?"
  -> the incident becomes a Threat Scenario (A2) and enters the workflow at stage 2
  -> authorization is FAST here: the system owner just lived through it

HUNT FINDING CONFIRMED
  -> to Green if it is detectable  (new detection content)
  -> to Purple if it is emulatable (new scenario -- proves the detection works)
  -> to Orange if the root cause is a design decision (attack-path catalog)
  A hunt finding that goes nowhere is the most expensive wasted work in the model.
```

---

## 7. Runbook — containment approval (C-8)

```
LOW RISK, REVERSIBLE     -> Blue decides. Record action, time, expected impact, rollback.
HIGH RISK / DESTRUCTIVE  -> TWO APPROVERS + written rollback, before acting.
                            (isolate production host, disable privileged identity,
                             block business-critical egress, terminate a service)
DURING AN EXERCISE       -> destructive containment is SUPPRESSED. Practice the decision,
                            record what you WOULD have done and when. That timestamp is
                            the MTTC measurement -- it is not a lesser result.
```

Sentinel Blue enforces this at the platform layer: it only ever emits response *plans*. It does
not contain, disable, terminate, or block. That boundary is deliberate — **do not build around
it.**

---

## 8. Escalation

| Situation | Action |
|---|---|
| Suspected real compromise during an exercise | **CSIRT takes primacy.** Notify White; White decides whether the exercise stops. |
| Sensor silent, detections down | Green immediately; **tell the SOC explicitly which detections are now blind** |
| Audit chain verification fails | Duty lead → Director → White. Treat as a potential integrity incident, not a data-quality nuisance. |
| Deconfliction contact unreachable >15 min | Call a stop |
| Asked to stand down during an exercise window | Refuse; escalate to White. Standing down invalidates the exercise. |
| Pressure to reduce severity for metrics | Escalate. Severity is revised by evidence only. |

---

## 9. Metrics Blue owns

MTTA · **MTTI (M-5)** · **MTTC (M-6)** · triage correctness (six-stage stage 4) · telemetry
freshness (feeds M-10) · false-negative discoveries · reopened incidents · high-risk actions with
complete approval + rollback evidence · deconfliction SLA · declared coverage (M-1 "claimed"
column, distinct from Purple's "validated" column — **C-7**).

**Banned here, per Blue's own operating model and [§8.18](../00-shared/07_metrics.md):** alert
volume, closure count, and any per-analyst statistic.

---

## 10. Anti-patterns

| Anti-pattern | Correction |
|---|---|
| Standing down during exercise windows | Operate normally; that is the measurement |
| Waiting on deconfliction before responding | Respond and query in parallel; ambiguity means real |
| Answering "not exercise" without certainty | The answer is UNKNOWN |
| Writing production detections directly | Propose to Green (C-1); one catalog |
| Tuning by excluding a group, product, or host class | Narrow, named, expiring exceptions with a test proving malicious variants still alert |
| Closing incidents with unstated unknowns | Declare the unknown explicitly (B14) |
| Hunt findings that stay in a document | Route to Green, Purple, or Orange within the week |
| Reporting alert volume as progress | Workload ≠ outcome |
| Per-analyst disposition stats | Destroys the honesty the data depends on |
