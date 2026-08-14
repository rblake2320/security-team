# Security Policy

## Scope

Report defects that could permit evidence forgery, undetected audit mutation,
detection bypass, unsafe response authorization, secret exposure, denial of
service, or misleading coverage/health claims.

## Safe handling

- Do not include credentials, raw production telemetry, personal data, malware,
  exploit payloads, or customer information in reports or fixtures.
- Reproduce with synthetic events in an isolated database.
- Do not test containment or blocking against production systems.
- Preserve the exact rule manifest and validation output with the report.

## Security boundaries

This repository is a defensive toolkit, not a security boundary against a local
administrator. Unsigned imports are development-only. Production must use
authenticated collectors, transport encryption, least privilege, separate key
custody, immutable backups, an external audit anchor, and monitored failover.

## Response

Treat suspected evidence-integrity or authentication defects as critical. Stop
trusting affected output, preserve the database and configuration read-only,
rotate collector credentials when relevant, establish an independent timeline,
and reprocess source telemetry after remediation.
