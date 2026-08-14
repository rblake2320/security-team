# Standards and cryptographic agility

## Current baselines

- NIST Cybersecurity Framework 2.0 for Govern, Identify, Protect, Detect, Respond, and Recover outcomes.
- MITRE ATT&CK for adversary-behavior identifiers; ATT&CK mappings are hypotheses to test, not proof of detection.
- MITRE D3FEND where defensive countermeasure semantics add value.
- JSON Schema draft 2020-12 for published artifact contracts.
- Ed25519 for short-lived role commands and SHA-256 for content identity and local chains.

Framework names and technique mappings are versioned inputs. A framework update never silently changes a frozen exercise or historical score.

## Algorithm transition policy

Ed25519 and SHA-256 are current mechanisms, not permanent promises. Maintain an inventory of every field, key, signature, digest, and external verifier. A cryptographic change requires a new schema major version and claim version.

Migration sequence:

1. Define the new algorithm identifier and exact canonical payload.
2. Add independent positive, tamper, wrong-key, downgrade, cross-algorithm, and replay tests.
3. Introduce dual verification; do not reinterpret old signatures.
4. During a bounded overlap, require the policy-approved signature set.
5. Re-anchor active evidence and preserve historical public verification material.
6. Revoke old signing authority only after every consumer proves the new path.
7. Keep a rollback path that restores verifier compatibility without restoring revoked authority.

Post-quantum adoption should use finalized, deployment-appropriate standards such as ML-DSA or SLH-DSA only after the runtime, HSM/KMS custody, interoperability, signature-size, latency, and recovery properties are tested. Do not invent a custom hybrid construction. A future `transition/2.x` envelope can carry an explicitly ordered signature set once those dependencies are ready.

## Dependency lifecycle

- CI tools are exact-version pinned and GitHub actions are immutable-commit pinned.
- Runtime dependencies have a declared minimum but release artifacts must lock exact resolved versions and include an SBOM.
- Review updates on a fixed cadence and immediately for exploited vulnerabilities.
- Every update runs unit, malformed-input, cross-version fixture, migration, rollback, and adversarial gates.
- Unsupported Python, SQLite, cryptography, operating-system, and ATT&CK versions are rejected through a versioned compatibility matrix rather than silently tolerated.

