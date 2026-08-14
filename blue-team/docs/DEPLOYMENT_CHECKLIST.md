# Deployment Readiness Checklist

Local tests establish code behavior only. Do not call a deployment production
ready until every applicable item has current evidence.

## Identity and trust

- [ ] Authenticated collector identities with rotation and revocation
- [ ] Encrypted transport and replay protection
- [ ] Separate operator, analyst, responder, and administrative roles
- [ ] Phishing-resistant MFA and emergency-access monitoring
- [ ] Secrets held outside code, logs, process arguments, and tickets

## Pipeline

- [ ] Durable queue, backpressure, dead-letter review, and bounded retries
- [ ] Schema/version compatibility and quarantine for invalid events
- [ ] Multi-source time synchronization monitoring
- [ ] Freshness budgets and synthetic canaries for every critical sensor
- [ ] Tested failover without duplicate or lost correlation state

## Evidence

- [ ] Encrypted storage, least privilege, retention and legal holds
- [ ] Immutable backups with restore proof
- [ ] External signed audit-head anchoring and rollback detection
- [ ] Evidence export integrity and chain-of-custody procedure
- [ ] Privacy minimization and access logging

## Detection and response

- [ ] Representative live positive/negative validation for every critical rule
- [ ] Detection owner, runbook, tuning expiry, and rollback
- [ ] On-call ownership and escalation tested
- [ ] High-risk response requires independent approval and target revalidation
- [ ] Tabletop, containment, restoration, and communication exercises passed

## Release gate

```powershell
$env:PYTHONPATH = (Resolve-Path src).Path
python -m blue_team.cli validate
python -m unittest discover -s tests -v
python -m ruff check src tests
python -m compileall -q src tests
```

A green local gate plus unchecked deployment items is a HOLD, not a GO.
