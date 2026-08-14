# Aegis Purple

Aegis Purple is the executable assurance core for this Purple Team program. Its registered claims cover frozen plans (`PURPLE-FROZEN-PLAN-001`), signed lifecycle commands (`PURPLE-SIGNED-TRANSITION-001`), evidence binding (`PURPLE-EVIDENCE-BINDING-001`), fail-closed scoring (`PURPLE-SCORE-FAILCLOSED-001`), and audit integrity (`PURPLE-AUDIT-INTEGRITY-001`).

It does **not** execute attacks, deploy detections, contain hosts, sign its own approvals, or claim that a green test suite proves security. The Red and Blue implementations remain separate systems with separate authority.

## Security invariants

1. A plan is content-addressed and immutable after `FROZEN`.
2. Purple cannot authorize its own plan; White authorizes and closes.
3. The CLI accepts lifecycle changes only as Ed25519-signed, role-bound, five-minute commands using the role registry pinned into the frozen plan.
4. Every command binds the exercise ID, exact plan hash, source state, target state, actor, role, reason, nonce, and validity window.
5. State skipping, stale writes, signature tampering, key-role mismatch, and nonce replay fail closed.
6. Production plans are observation-only; high-safety cases require a verified rollback.
7. Evidence must name a frozen test case and its content hash. Results cannot borrow evidence across cases.
8. Evidence verification requires all six stages: prevented, logged, alerted, investigated, contained, reported.
9. The operator cannot independently verify the evidence they produced.
10. Readiness failure forces `TRAINING_OR_ENGINEERING_USE_ONLY`; diagnostic scores are not assurance.
11. Automatic failures are evaluated before weighted scores.
12. Local audit chains are not called independent until their exported head is published to a separately administered append-only store.

## Quick verification

From the repository root:

```powershell
$env:PYTHONPATH=(Resolve-Path purple-team\src).Path
python -m unittest discover -s purple-team\tests -v
python -m aegis_purple validate-program `
  --readiness 00-shared\config\assessment_readiness.json `
  --claims 00-shared\config\assurance_claims.json
python -m ruff check purple-team\src purple-team\tests
```

Use `--require-ready` in a release or assessment-issuance gate. It intentionally exits nonzero while any readiness prerequisite remains open.

Production packaging must resolve against `tools/requirements-runtime.txt`; `pyproject.toml` keeps a compatible lower bound for library consumers, while the reviewed deployment baseline stays exact.

## Exercise lifecycle

```text
FROZEN -> AUTHORIZED -> EXECUTING -> EXECUTED -> EVIDENCE_VERIFIED -> RETESTED -> CLOSED
    \          \             \            \                \             \
     +----------+-------------+------------+----------------+---------------> STOPPED
```

White may stop from any active state. A stopped exercise is terminal; resumption requires a new versioned plan and authorization.

## Trust deployment

`config/role_trust.example.json` shows the public-key registry shape. Replace every placeholder, validate the registry, compute its canonical SHA-256, and place that digest in the plan before freezing. The CLI rejects a different registry. Do not place private keys in this repository. Production authorization, evidence, and assessment keys must be distinct, non-exportable, and controlled by separately administered identities. The signer creates the transition envelope externally; Aegis Purple only verifies it.

See [architecture](docs/ARCHITECTURE.md), [threat model](docs/THREAT_MODEL.md), [operations](docs/OPERATIONS.md), [standards and crypto agility](docs/STANDARDS_AND_CRYPTO_AGILITY.md), and [adversarial review](docs/ADVERSARIAL_REVIEW.md).
