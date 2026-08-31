# AEGIS Mission Control threat model

**Status:** implementation baseline
**Scope:** private owner console, public showcase, hosted customer workspaces, customer connectors, evidence storage, and Shadow AI defense
**Review trigger:** every new connector, action capability, AI data source, identity path, storage change, or production release

## Security objectives

1. Owner data, public showcase data, and customer data never share a runtime data store.
2. A user, connector, task, evidence object, AI asset, or audit event can belong to exactly one workspace.
3. Browser code never receives server source, secrets, raw AI prompts, another tenant's identifiers, or unrestricted execution capability.
4. Consequential actions are deny-by-default, scope-bound, approved, dry-run when critical, auditable, and stoppable.
5. “Configured” is never reported as “verified.” Missing telemetry and accepted exceptions stay visible.
6. Security evidence is bounded, quarantined, encrypted, integrity-hashed, retained by policy, and held when required.

## Deployment and data-flow boundaries

```text
PUBLIC SHOWCASE (synthetic only)
Internet -> Cloudflare public hostname -> demo container -> compiled UI + synthetic feed
                                        X no database
                                        X no customer connectors
                                        X no control execution

HOSTED CUSTOMER CONTROL PLANE
Human -> Cloudflare Access -> tunnel -> FastAPI authorization -> tenant-scoped PostgreSQL
                                                  |            -> encrypted evidence volume
                                                  |            -> chained audit records
Customer systems -> Access service policy -> connector API ----+
Customer connector <- leased, approved, capability-bound tasks -+

PRIVATE OWNER CONTROL PLANE
Owner browser -> 127.0.0.1 only -> local operator server -> allowlisted repository gates
                                                    -> bounded local observer metadata
```

The hosted product does not connect inward to a customer's network. A customer provisions an outbound connector with a one-time credential and explicit observation/action capabilities. The showcase is a separate deployment with a separate tunnel and no durable customer store.

## Trust boundaries

| Boundary | Threats | Required controls |
|---|---|---|
| Internet to Cloudflare | spoofing, denial of service, hostile input | TLS, Access identity/service policies, bot/rate rules, request limits, dedicated hostnames |
| Cloudflare to application | header spoofing, origin bypass | Tunnel-only origin, no public app port, validated Access JWT for humans, Trusted Host policy |
| Human to workspace | cross-tenant access, privilege escalation | invitation admission, tenant membership, role permissions, same-origin control requests, isolation tests |
| Connector to ingestion API | stolen token, replay, excessive data | one-time hashed token, revocation, scoped capabilities, idempotency keys, body/batch bounds, pseudonymization |
| Control plane to connector | tool abuse, unintended blast radius | deny-by-default action catalog, payload scrubbing, dry-run, approval, separation of duties, lease expiry, kill switch |
| Application to PostgreSQL | injection, tenant leakage, tampering, resource exhaustion | SQLAlchemy parameterization, restricted runtime role, forced tenant RLS, transaction-local identity context, dedicated database, statement timeouts, migrations, backup/restore drills |
| Application to evidence store | malware, path traversal, disclosure, tampering | filename/path normalization, type/size allowlist, fail-closed private ClamAV scan, quarantine, AES-GCM envelope encryption, SHA-256, legal holds |
| AI observation to policy engine | surveillance overcollection, prompt leakage, evasion | no prompt/response fields, user/device HMAC pseudonyms, domain normalization, model/tool/MCP inventory, explicit unknown state |
| Build to runtime | dependency or image compromise | pinned lockfile, dependency audit, migration check, multi-stage image, non-root/read-only runtime, dropped capabilities |

## STRIDE review

| Component | S | T | R | I | D | E |
|---|---|---|---|---|---|---|
| Cloudflare identity | forged or replayed assertion | header manipulation | disputed login | identity disclosure | Access outage | policy misconfiguration |
| Tenant API | connector/user impersonation | record or policy changes | denied decisions | cross-tenant records | request exhaustion | role or object-reference bypass |
| Task queue | forged connector | changed payload/result | disputed execution | sensitive result leakage | lease starvation | capability chaining |
| Evidence store | forged uploader | replaced object | custody dispute | plaintext disclosure | volume exhaustion | path traversal |
| Shadow AI pipeline | forged asset identity | falsified inventory | denied usage | prompt/user disclosure | event flood | blocking without authority |
| Public showcase | brand spoofing | altered synthetic feed | misleading claims | owner-data inclusion | traffic flood | accidental control exposure |

## AI-specific attack cases

- Direct, indirect, retrieval-borne, encoded, and multimodal prompt injection.
- System-instruction extraction and prompt leakage through logs, errors, evidence, or analytics.
- RAG cross-tenant retrieval and unauthorized document disclosure.
- Agent tool abuse, cumulative privilege, confused deputy behavior, unbounded execution, and external side effects.
- Unknown AI applications, local model runtimes, browser extensions, coding assistants, alternate domains, tunnels, and MCP servers.
- Sensitive-data egress to sanctioned or unsanctioned AI, including encoded and side-channel paths.
- Poisoned models, dependencies, embeddings, documents, tools, plugins, skills, MCP resources, and container artifacts.
- Evasion through process renaming, encrypted traffic, proxying, local inference, or unmonitored identities/devices.

These cases are owned across the Purple, White, Yellow, Green, Orange, Blue, and Red control lanes; Shadow AI is not a single-team responsibility.

## Priority risk register

| ID | Risk | STRIDE | Inherent | Implemented controls | Residual | Required follow-up |
|---|---|---|---|---|---|---|
| R-001 | Cross-tenant object access | I/E | critical | context resolution, tenant predicates, restricted runtime role, forced PostgreSQL RLS, transaction-local tenant binding, opaque IDs, automated two-workspace tests | low | independent penetration test and continued policy-drift testing |
| R-002 | Owner data copied into showcase | I | critical | separate demo mode/container/tunnel, no database, synthetic feed, controls rejected server-side | low | deployment inspection and content scan before every showcase release |
| R-003 | Stolen connector credential | S/E | high | one-time token, HMAC hash only, scoped capabilities, revocation, Access service policy, audit | medium | rotation workflow, short-lived machine identity option, anomaly rules |
| R-004 | Unauthorized containment/block action | T/E/D | critical | deny-by-default catalog, successful dry-run, independent approval, scoped connector, lease token/expiry, kill switch | medium | exercise every action-specific rollback and blast-radius limit |
| R-005 | Prompt or sensitive content retained | I | critical | schemas omit prompts/responses, policy rejects prompt retention, payload secret scrubbing, metadata-only AI usage | low | DLP regression corpus and log/evidence content scans |
| R-006 | Evidence theft, malware, or replacement | T/I/R | critical | tenant-derived AES-GCM envelope, plaintext SHA-256, automatic private ClamAV verdict, fail-closed quarantine, atomic write, chain audit, retention/legal hold | medium | off-host immutable backup, key rotation/HSM design, advanced detonation sandbox for high-risk formats |
| R-007 | Audit-chain deletion or database-admin tampering | T/R | high | per-tenant chained hashes and verifier | medium | export signed checkpoints to separate immutable storage |
| R-008 | Supply-chain compromise | T/E | critical | lockfile, dependency audits, migration checks, minimal non-root container, read-only filesystem | medium | signed images/SBOM/provenance and admission verification in CI/CD |
| R-009 | Cloudflare/identity misconfiguration | S/E | high | production config fails closed, audience/issuer validation, Trusted Host, tunnel-only origin | medium | staged negative identity tests and policy export review before DNS cutover |
| R-010 | Missing telemetry creates a false sense of coverage | R/I | high | control/source mapping, telemetry-gap state, configured not equal verified, seven-team ownership | medium | customer onboarding checklist and periodic source-health attestations |
| R-011 | Backup exists but cannot restore | D | high | database/evidence checksum bundle and isolated restore-drill script | medium | scheduled restore drills with retained receipts and measured RPO/RTO |
| R-012 | Public reverse engineering | I | medium | proprietary authorization, policy, data, and execution remain server-side; browser receives compiled UI only | low | accept that client UI/network contracts are inspectable; protect value with server controls, not obfuscation claims |

## Production release gates

A release is blocked unless all of the following have evidence:

- Python and frontend tests pass, migration upgrade succeeds, and Alembic reports no schema drift.
- Tenant isolation, role denial, connector revocation, task approval, lease expiry, and kill-switch tests pass.
- The showcase image has no production environment file, database volume, connector route, owner record, or control path.
- Cloudflare Access allows an invited human, denies an uninvited human, accepts only the dedicated connector service policy, and denies direct origin access.
- Database and evidence backup completes, checksums validate, and an isolated restore drill succeeds.
- The real digest-pinned ClamAV engine accepts clean evidence, rejects EICAR, and scanner outage tests preserve quarantine and fail readiness.
- Dependency, container, secret, and source scans meet the project's fail threshold.
- Security headers, request/body bounds, error behavior, responsive UI, keyboard operation, and reduced motion are verified.
- Every enabled critical control is either verified or explicitly excepted with an owner and expiry; unknown is never silently accepted.

## Known residual work before regulated or large-enterprise claims

- PostgreSQL row security is enforced for tenant-owned tables. Externally managed
  per-tenant keys are not yet implemented.
- ClamAV provides a real signature-based malware gate; advanced detonation, archive recursion policy tuning, and a multi-engine service remain risk-based enhancements for hostile high-risk formats.
- Billing, contractual compliance mappings, regional data residency, legal terms, support operations, and breach notification processes require business decisions outside this codebase.
- High availability, multi-region recovery, independent penetration testing, and formal SOC 2/ISO certification have not been proven.

These are visible release-scope decisions, not hidden assumptions.
