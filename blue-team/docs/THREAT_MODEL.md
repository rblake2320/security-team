# Threat Model: Attacking the Defender

## Protected assets

- Telemetry integrity and availability
- Detection rules and suppression policy
- Alert, case, and response evidence
- Analyst identities and privileged response channels
- Backups, recovery credentials, and restoration procedures
- Audit history and external integrity anchors

## Likely attacks against the blue team

| Adversary goal | Defensive design |
|---|---|
| Disable or starve sensors | Independent freshness budgets; critical impairment alerts; source diversity |
| Replay trusted-looking events | Event-ID hash binding; conflicting replay rejection; time checks |
| Split behavior below thresholds | Stateful correlation by host, user, domain, and time window |
| Flood the queue | Input/run limits, bounded alert evidence, backpressure design, priority lanes |
| Abuse Unicode or field ambiguity | NFKC normalization, collision rejection, strict top-level schema |
| Cause expensive rule evaluation | No arbitrary code or regular expressions; bounded operators and windows |
| Silence critical alerts with tuning | Critical rules cannot be suppressed; all changes require review evidence |
| Poison audit evidence | Canonical hashing, sequence and predecessor validation, external-anchor requirement |
| Trick responders into destructive action | Recommendation-only plans, two-person approval, rollback required |
| Compromise the analyst identity | Phishing-resistant MFA, separate admin accounts, just-in-time privilege, session review |
| Destroy backups or recovery | Immutable copies, separate credentials, restore exercises, recovery monitoring |
| Live quietly in legitimate tools | Identity/endpoints/cloud correlation, behavior baselines, threat hunts, change validation |

## Residual risks

- A same-host administrator can replace the complete local database and code.
- Sensors can agree on false data if their shared upstream source is compromised.
- Unsigned local JSONL proves content integrity after ingestion, not collector
  identity. Production ingestion requires authenticated collectors and transport.
- ATT&CK mappings and passing unit tests do not establish real detection efficacy.
- Unknown techniques and environment-specific abuse require hunts and incident learning.
- Encrypted traffic limits content inspection; metadata and endpoint evidence remain essential.

These are explicit engineering requirements for deployment, not hidden caveats.
