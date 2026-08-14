# Threat model

## Protected properties

- Authorization cannot be forged by Purple or Red.
- A frozen test plan cannot be expanded after approval.
- Evidence cannot be silently substituted across exercises or test cases.
- An operator cannot independently certify their own evidence.
- A catastrophic safety failure cannot be averaged away by a strong score.
- Pending prerequisites cannot be presented as assurance.

## Adversaries considered

- An operator seeking broader scope or a better score.
- A compromised integration sending malformed, oversized, replayed, stale, or Unicode-confusable data.
- A local process modifying exercise state or evidence.
- A reviewer with a conflict of interest.
- A well-intentioned maintainer introducing schema drift or weakening a gate.
- A same-host administrator capable of rolling back the complete database.

## Controls

| Attack | Control | Remaining limit |
|---|---|---|
| Change plan after approval | Canonical plan digest stored with immutable JSON | Whole database replacement needs external anchor |
| Skip lifecycle state | Explicit transition graph + expected-state compare | Library embedding must preserve authenticated caller boundary |
| Claim another role | Plan-pinned Ed25519 role-key registry and signed CLI commands | Key custody/IAM must be proven externally |
| Replay approval | 128-bit nonce, five-minute window, consumed-nonce store | Host clock must be trustworthy |
| Inflate score | Exact components, evidence required, auto-fail first | Evidence quality still needs independent judgment |
| Swap evidence | Exercise/test-case foreign binding and content hash | Hash does not prove collection truth |
| Self-review | Plan-owner and operator identity separation | Identity federation must supply stable unique principals |
| Delete audit tail | Stored head/count and sequence chain | Full-store rollback requires external witness |
| Parser/resource abuse | 1 MB input, depth/item/string caps, strict types | Deliberate storage exhaustion needs host quotas |
| Future schema ambiguity | Namespaced schemas, exact fields, explicit migrations | Governance must maintain deprecation discipline |

## Trust assumptions

System time, SQLite durability, the Python/cryptography runtime, OS access control, public-key registry integrity, signer identity, and independent anchor publication are trusted dependencies. Until production custody and independent witnessing are exercised, assessment issuance remains held.
