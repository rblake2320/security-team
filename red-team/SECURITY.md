# Security model

## Operating boundary

Use Aegis only on systems you own or have explicit written permission to assess.
The authorization receipt is a technical guardrail, not a substitute for legal
authorization, change control, stakeholder notification, or an emergency plan.

## Threat model and controls

| Risk | Control |
|---|---|
| Forged or out-of-scope authorization | Ed25519 signature, separately pinned trust key, exact-scope fingerprint, expiry |
| Public target touched by default | Public addresses denied unless receipt opts in |
| DNS rebinding | Validate every resolved address and pin the selected address for HTTP |
| Redirect crosses scope | Redirects are recorded and never followed |
| Excess traffic | Global request budget, rate limiter, concurrency and timeout caps |
| Runaway operation | `.aegis/STOP` kill switch checked at safety boundaries |
| Audit tampering | SHA-256 hash chain plus an Ed25519 final seal from the approval authority |
| Secret leakage in reports | Match values are replaced with short one-way digests |
| Engagement file becomes code | Fixed check registry; no arbitrary command or plugin loading |

The final seal authenticates the exact ledger using the separately held approval key.
Archive the ledger, seal, and trust key in an access-controlled immutable store.

## Reporting vulnerabilities

Do not place real secrets, customer data, or exploit payloads in an issue. Provide a
minimal description, affected version, impact, and a safe reproduction in a private
security channel controlled by the project owner.
