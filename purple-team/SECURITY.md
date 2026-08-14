# Security policy

Report suspected authorization bypass, signature validation errors, scope expansion, evidence substitution, ledger corruption, readiness overclaim, or unsafe production behavior to the program owner and White authority. Do not include credentials, private keys, exploit payloads, or sensitive evidence in a ticket.

## Supported boundary

- Python 3.11 or newer.
- SQLite on a locally trusted filesystem.
- Ed25519 role public keys pinned in a reviewed trust registry.
- Private signing keys held outside the application.
- Production plans limited to observation-only validation.

## Explicit limits

- A local database administrator can replace the database and its local metadata together. Export the audit anchor to an independent append-only witness to detect whole-store rollback.
- Role strings inside the library are not an identity system. The supported CLI boundary requires signed commands; embedded callers must provide an equivalently authenticated boundary.
- Content hashes prove byte identity, not truth, completeness, ownership, or independent collection.
- Configuration validation proves internal consistency, not live detection efficacy.
- No promise of zero missed attacks, permanent algorithm suitability, or future compatibility is made. Schema versions, claim versions, migration tests, and deprecation windows are the durability mechanism.

