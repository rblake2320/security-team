# Sentinel Blue

Sentinel Blue is a local-first defensive operations core. It turns normalized
security telemetry into correlated alerts, auditable cases, coverage evidence,
sensor-health findings, and approval-gated response plans.

It is deliberately not an autonomous counterattack system. It never performs
containment, account disablement, process termination, or blocking actions.
Those actions are proposed as response steps and require documented approval in
the operator's downstream tooling.

## What it protects against

- Silent telemetry failure and stale sensors
- Event replay, conflicting duplicate IDs, malformed input, and oversized input
- Detection bypass through case changes, split event bursts, and noisy flooding
- Alert suppression hiding critical defense-impairment events
- Audit-log deletion or modification
- Destructive response without an approval boundary
- Coverage theater: every target technique is reported as covered, partial, or a gap

## Quick start

```powershell
python -m blue_team.cli init --db runtime\blue.db
python -m blue_team.cli ingest examples\events.jsonl --db runtime\blue.db
python -m blue_team.cli alerts --db runtime\blue.db
python -m blue_team.cli health --db runtime\blue.db
python -m blue_team.cli coverage
python -m blue_team.cli verify-ledger --db runtime\blue.db
python -m blue_team.cli validate
```

For development without installation:

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m unittest discover -s tests -v
```

## Design boundaries

- Input is newline-delimited JSON, one event per line, capped at 64 KiB.
- Local unsigned imports are development-only. Production-style collectors use
  `--trust-policy config\source_trust.json` and source-specific 32-byte-or-longer
  secrets supplied through environment variables, never committed files.
- SQLite writes use WAL mode, foreign keys, busy timeouts, and explicit transactions.
- The audit chain detects mutation and interior deletion. External anchoring is
  still required to detect rollback or deletion of the entire database.
- Rules use bounded operators rather than arbitrary regular expressions or code.
- High-risk response steps are recommendations only and require two-person approval.
- ATT&CK mappings are evidence labels, not proof that a rule is effective.

## Documentation

- `docs/ARCHITECTURE.md` — trust boundaries and data flow
- `docs/OPERATING_MODEL.md` — roles, shifts, escalation, and quality gates
- `docs/THREAT_MODEL.md` — attacks against the defender and mitigations
- `docs/INCIDENT_RESPONSE.md` — severity model and response lifecycle
- `docs/DETECTION_ENGINEERING.md` — rule lifecycle and validation standard
- `docs/PROGRAM_CONTROL_MATRIX.md` — full Govern-to-Recover control model
- `docs/ADVERSARIAL_REVIEW.md` — how the defensive system could be defeated
- `docs/DEPLOYMENT_CHECKLIST.md` — production evidence gate
- `docs/REFERENCES.md` — primary standards used by the design
