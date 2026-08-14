# Defensive Program Control Matrix

The detection engine is only one layer. A complete blue team owns evidence and
continuous improvement across all six NIST CSF 2.0 functions.

| Function | Required capability | Minimum evidence |
|---|---|---|
| Govern | Risk ownership, legal/privacy obligations, exceptions, suppliers, metrics | Approved policy, risk register, named owners, expiring exceptions |
| Identify | Hardware/software/cloud/SaaS/data/identity inventory and critical dependencies | Reconciled inventory, ownership, criticality, unsupported/unknown assets |
| Protect | Hardened configuration, patching, MFA, least privilege, secrets, segmentation, encryption | Configuration baseline, drift report, patch proof, access review |
| Detect | Endpoint, identity, cloud, network, email, data, backup and control-health telemetry | Freshness report, validated rules, hunt results, audit integrity |
| Respond | Severity, command, evidence, containment, communication, legal/privacy coordination | Cases, approvals, timelines, evidence references, rollback results |
| Recover | Immutable backup, rebuild, restore, dependency order, heightened monitoring | Restore test, RPO/RTO result, integrity validation, owner acceptance |

## Non-negotiable infrastructure practices

- Phishing-resistant MFA and separate administrative identities
- Just-in-time privilege with session and change evidence
- Default-deny exposure and egress appropriate to asset criticality
- Centralized time, identity, configuration, and asset ownership
- Immutable/offline recovery copies with separate credentials
- Secure boot, disk encryption, endpoint protection, application control, and logging
- Rapid remediation for exploited exposure; explicit compensating controls when delayed
- Secrets in managed stores, not source, command lines, tickets, or telemetry
- Protected CI/CD, signed provenance where practical, dependency and artifact review
- Tested incident communications and supplier escalation paths

## Assurance loop

Every incident, exercise, false negative, sensor outage, recovery failure, and
material near miss creates an owner, deadline, test, evidence requirement, and
verification step. Findings are not closed by documentation alone.
