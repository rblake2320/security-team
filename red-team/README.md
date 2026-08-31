# Aegis Red Team

Aegis is an authorization-first security assessment platform. It is designed for
owned labs and explicitly approved engagements, with controls that make every live
action scoped, rate-limited, stoppable, and auditable.

## What is implemented

- Ed25519-signed scope receipts bound to the exact targets, checks, and execution limits.
- Public network targets denied unless an unexpired authorization explicitly selects
  public-target mode. Public mode accepts only exclusively public DNS answers; private,
  restricted, or mixed answers fail closed to prevent rebinding into internal services.
- A second scope-fingerprint acknowledgement required at execution time.
- DNS resolution validation and address-pinned HTTP connections to reduce rebinding risk.
- TLS certificate verification, no redirect following, request budgets, rate limits,
  concurrency caps, and a `STOP` kill-switch file.
- Append-only hash-chained JSONL audit records with an integrity verifier.
- Normalized findings, CWE references, redacted secret evidence, JSON output, and a
  human-readable Markdown report.
- Built-in offline source review and minimally invasive HTTP security-header review.
- A bounded check registry that does not execute arbitrary shell commands or plugins.

This release deliberately excludes credential theft, persistence, evasion, malware,
destructive payloads, and uncontrolled scanning.

## Quick start

Python 3.11 or newer is required.

```powershell
python -m pip install -e .
aegis-rt list-checks
aegis-rt plan examples/engagement.json
```

Bind authorization to the exact scope. Use a real approval ticket and an expiry time:

```powershell
$env:AEGIS_KEY_PASSWORD = Read-Host -MaskInput # use a secret manager in automation
aegis-rt keygen --private-key authority.pem --public-key authority.pub.pem `
  --password-env AEGIS_KEY_PASSWORD --purpose authorization-v1
aegis-rt authorize examples/engagement.json `
  --approved-by "Security Director" `
  --ticket "SEC-1234" `
  --expires-at "2027-01-01T00:00:00Z" `
  --signing-key authority.pem `
  --password-env AEGIS_KEY_PASSWORD `
  --ack "I AM AUTHORIZED"
```

Keep the encrypted private key with the approval authority. Distribute only the
public trust key to operators. Clear the temporary environment variable after signing.
Generate a distinct `evidence.pem` keypair with `--purpose evidence-seal-v1`; cross-purpose
key use is rejected by both signing and verification paths.

Run using the fingerprint printed by `plan`:

```powershell
aegis-rt run examples/engagement.json --trust-key authority.pub.pem `
  --ack-scope <64-character-fingerprint>
aegis-rt seal-ledger .aegis/audit.jsonl --seal .aegis/audit.seal.json `
  --evidence-signing-key evidence.pem --password-env AEGIS_KEY_PASSWORD
aegis-rt verify-ledger .aegis/audit.jsonl --seal .aegis/audit.seal.json `
  --evidence-trust-key evidence.pub.pem
```

Creating `.aegis/STOP` halts checks at their next safety boundary. Remove it only
after the engagement owner approves resumption.

## Safe extension model

Checks implement the small protocol in `checks/base.py` and must declare supported
target kinds and whether they make active requests. Register reviewed checks in the
fixed built-in registry. Do not load code from engagement files or accept shell
command templates; data must never become executable control flow.

## Test

```powershell
python -m unittest discover -s tests -v
```

See [SECURITY.md](SECURITY.md) for the threat model and operating boundaries.
