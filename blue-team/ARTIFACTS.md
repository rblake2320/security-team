# BLUE TEAM — Artifacts

Standards for all artifacts: [§7](../00-shared/06_artifact_index_and_standards.md).

← [Charter](CHARTER.md) · [Playbook](PLAYBOOK.md) · [AI Agent](AI_AGENT.md) · [Index](../README.md)

> **Blue's artifacts are mostly machine-emitted, not hand-filled.** Sentinel Blue produces
> alerts, cases, coverage reports, health reports, response plans, and the audit chain as
> program output. This file therefore documents **emitted schemas, their governance metadata,
> and the two artifacts humans do author** (incident record, hunt record) — rather than
> pretending they are forms.

| Artifact | Produced by | Approver | Retention | Marking | System of record |
|---|---|---|---|---|---|
| Event (normalized) | `blue_team.canonical` / `models` | — | 90 d hot / per policy cold | INTERNAL | Evidence store (SQLite WAL) |
| Alert | `blue_team.detection` | Duty lead (disposition) | 3 yr | INTERNAL | Evidence store + SIEM |
| Case | `blue_team.store` | Duty lead | 7 yr | INTERNAL / CONFIDENTIAL | Evidence store + case mgmt |
| **Incident record** | **Human** — incident commander | Director, Sec Ops | 7 yr | CONFIDENTIAL | CSIRT record |
| Investigation timeline | Human + tooling | Incident commander | 7 yr | CONFIDENTIAL | CSIRT record |
| Containment approval record | Human — **two approvers** | System Owner | 7 yr | INTERNAL | Change/IR record |
| Recovery validation | Recovery lead | Business owner accepts | 7 yr | INTERNAL | IR record + GRC |
| **Hunt record** | **Human** — threat hunter | Blue Lead | 3 yr | INTERNAL | Knowledge base |
| Sensor-health report | `blue_team.health` | Blue Lead | 1 yr | INTERNAL | Evidence store |
| Declared-coverage report | `blue_team.coverage` | Blue Lead | 1 yr | INTERNAL | Evidence store |
| Response plan | `blue_team.response` | **Two approvers if high-risk** | 7 yr | INTERNAL | IR record |
| Audit chain + head hash | `blue_team.store` | Blue Lead → **White** | 7 yr | INTERNAL | Blue store → White evidence manifest |
| Deconfliction query log | Human | White | 7 yr | Per RoE | Exercise record |

---

## Emitted schemas

Canonical event schema: [`schemas/event.schema.json`](schemas/event.schema.json).
Bounded at 64 KiB per line, newline-delimited JSON, all fields untrusted at the telemetry
boundary (see [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)).

```powershell
# The commands that produce each artifact
python -m blue_team.cli ingest examples\events.jsonl --db runtime\blue.db   # events, alerts, cases
python -m blue_team.cli alerts        --db runtime\blue.db                  # alert set
python -m blue_team.cli health        --db runtime\blue.db                  # sensor-health report
python -m blue_team.cli coverage                                            # declared-coverage report
python -m blue_team.cli verify-ledger --db runtime\blue.db                  # audit chain verification
python -m blue_team.cli validate                                            # config integrity
```

**Governance metadata that must accompany every exported artifact [M]:** capture time (UTC),
source, tool + version, SHA-256, classification marking, retention, custodian. The store does not
apply these — the exporter does, at the moment of export into White's evidence manifest.

---

## Incident record (human-authored)

Lifecycle per [`docs/INCIDENT_RESPONSE.md`](docs/INCIDENT_RESPONSE.md). Closure gate is **B14**.

```markdown
# Incident INC-YYYY-NNNN

Severity:                 [M] critical | high | medium | low
Declared at / by:         [M] UTC, named human
Incident commander:       [M]
Scribe / evidence owner:  [M]
Comms channel:            [M]
Systems / identities:     [M]
Business impact:          [M] in the owner's terms

## Evidence preservation  [M]
Preserved BEFORE destructive action: [M] what, when, acquisition method
> If containment happened first, say so plainly. Do not backfill.

## Validation  [M]
CONFIRMED:  [M]
BELIEVED:   [M]
ESTIMATED:  [M]
UNKNOWN:    [M]   <- a declared unknown is an acceptable closure state.
                     A silent unknown is not.

## Scope  [M]
Identities | hosts | cloud resources | network | persistence | data access | recovery systems

## Containment  [M]
Action | Risk | Approver 1 | Approver 2 (if high-risk) | Expected impact
       | Success signal | Rollback | Executed at | Result

## Eradication  [M]
Persistence removed | exposure closed | secrets rotated | controls restored
| alternate access hunted

## Recovery  [M]
Restored from | integrity validated how | monitoring elevated until
| **business-owner acceptance: name + date**

## Timing  [M]
First activity | first signal | acknowledged | investigated | contained | recovered
-> feeds M-5 (MTTI), M-6 (MTTC). Measure from ADVERSARY ACTION, not from the alert.

## Closure gate  [M] -- all required (B14)
[ ] Scope established
[ ] Cause established OR unknown explicitly declared
[ ] Containment evidence attached
[ ] Recovery validated and accepted
[ ] Lessons recorded with owners and dates
[ ] Detection/prevention follow-up raised to Green / Yellow / Orange
[ ] Emulation-conversion review scheduled with Purple (within 30 days)
[ ] WhyCase created -- see ../00-shared/15_why_engine_and_soul_integration.md
```

---

## Hunt record (human-authored)

```markdown
# Hunt HUNT-YYYY-NNNN

Hypothesis:           [M] falsifiable. "If X were happening, we would see Y in Z."
Basis:                [M] threat intel | incident | architecture insight | anomaly
Data sources queried: [M] and their freshness at query time
Time range:           [M]
Queries:              [M] preserved verbatim -- a hunt you cannot re-run is an anecdote

## Result  [M]
[ ] Hypothesis supported -> raise an incident
[ ] Hypothesis not supported -> record the NEGATIVE result. Still valuable:
      it is evidence of coverage and it stops the same hunt being re-run blind.
[ ] Inconclusive -> state exactly what data was missing -> telemetry gap to Green

## Routing  [M]  -- a hunt that routes nowhere was wasted
Detectable?    -> Green: detection request
Emulatable?    -> Purple: scenario candidate
Design cause?  -> Orange: attack-path catalog
Nothing?       -> say so explicitly and close
```

---

## Audit chain export (C-9) **[M]**

Sentinel Blue's chain detects mutation and interior deletion. It does **not** detect rollback or
deletion of the entire database — the project's own README says so. The external anchor closes
that gap.

```markdown
# Audit Chain Export ACE-YYYY-NN

Store:                [M] path + environment
Verification command: python -m blue_team.cli verify-ledger --db <db>
Result:               [M] valid | INVALID  -> INVALID is an integrity incident: escalate
Event count:          [M]
Head hash (SHA-256):  [M]
Exported at:          [M] UTC
Exported by:          [M]
Received into White evidence manifest: [M] EM ref + custodian + date

Frequency: at every exercise close, and monthly.
```

**A verification failure is escalated to the Blue Lead, the Director, and White — not retried
quietly.**

---

## Configuration as artifact

| File | Governs | Cross-team significance |
|---|---|---|
| [`config/coverage_target.json`](config/coverage_target.json) | 22 techniques with priority + required telemetry | **This is the single source of truth for metric M-1's denominator** ([§15.4](../00-shared/14_blue_team_integration_review.md)). Maintained jointly by Purple and Blue. Changing it changes every coverage number — treat edits as governed changes with a changelog entry. |
| `config/rule_manifest.json` | Rule integrity | Verified on every ingest |
| `config/sensor_policy.json` | Freshness budgets per source | Feeds M-10 |
| `config/source_trust.example.json` | Collector authentication | **Never commit real secrets.** Production uses 32-byte-or-longer secrets from environment variables. |
| [`rules/`](rules/) | Detection logic, bounded operators only | Reference rule *format*. Production detection content lives in **Green's** detection-as-code repo (C-1, residual **R-3**). |
