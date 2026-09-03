# ADR-0001: Enterprise scale platform and promotion gates

**Status:** Accepted target architecture; current deployment does not yet conform
**Date:** 2026-09-03

## Context

AEGIS currently runs as a hardened single-region beta on one Hostinger VPS. That topology is useful for a controlled launch but cannot support an honest 1,000-user or 500,000-user claim: application, PostgreSQL, evidence storage, scanning, logs, and tunnel all share one failure domain. Registered users are also not a workload. Capacity must be defined by active concurrency, endpoint mix, request rate, evidence sizes, scanner demand, connector cadence, tenant distribution, dataset size, and SLOs.

## Decision

Keep the application a modular monolith while making every process stateless. Promote infrastructure in measured tiers:

```text
Cloudflare DNS / TLS / Access / WAF / edge rate limits
                         |
                 regional load balancer
                  /       |       \
          AEGIS API   AEGIS API   AEGIS API       (3+ AZ-spread replicas)
                  \       |       /
                   managed PgBouncer
                          |
             managed PostgreSQL Multi-AZ ---- read replica / PITR
                          |
          +---------------+----------------+
          |               |                |
   object evidence   durable task queue   managed Redis
   + tenant KMS      + scanner workers    quotas/idempotency
          |
   immutable backup / regional replication

All services -> OpenTelemetry -> centralized logs, metrics, traces, alerts
```

The public showcase remains a separate stateless, synthetic-only deployment and never shares databases, evidence, secrets, queues, or service identities with customer workloads.

### Application requirements

- Run schema migration and bootstrap once before workers; serialize cross-replica bootstrap with a PostgreSQL advisory lock.
- Use explicit connection-pool budgets and PgBouncer before horizontal scale.
- Store evidence in object storage; use externally managed per-tenant keys and lifecycle/retention policies.
- Move long-running assessment, export, scanning, and connector work behind a durable queue with bounded retries, idempotency, dead-letter handling, and backpressure.
- Enforce per-identity, per-tenant, per-route, upload, task, connector, scanner, queue, and global budgets. Cloudflare limits are defense in depth, not the only control.
- Emit structured correlated logs, RED/USE metrics, distributed traces, saturation gauges, audit-chain alarms, and SLO burn-rate alerts.
- Keep identity, authorization, approvals, audit-chain, policy binding, and automatic-failure decisions deterministic and model-independent.

### Promotion gates

No gate may be replaced by a document or a green unit suite. Every receipt is tied to the exact Git revision, container digest, profile digest, topology, and timestamp.

| Tier | Minimum proof before claim |
|---|---|
| Controlled beta (10 users) | Twice the claimed identity volume; mixed read/write/evidence workload; one-hour soak; scanner outage; database restart; backup/restore; declared latency/error SLO. |
| Regional SaaS (1,000 users) | Twice identity volume; target peak concurrency and event rate; eight-hour soak; noisy-neighbor test; replica loss; managed-DB failover; restore under load; security test. |
| Enterprise (500,000 users) | One million seeded identities; production traffic model; 24-hour soak; AZ loss; regional failover; PITR; queue/scanner saturation; data-residency controls; independent penetration and operational-readiness reviews. |

The exact target concurrency and arrival rate must be derived from product analytics or a signed forecast. They may not be invented from registered-user count.

### Default SLO starting point

These are engineering defaults until a customer contract replaces them:

- Availability: 99.9% regional beta; higher targets require multi-region proof.
- HTTP error rate attributable to AEGIS: below 0.1% during steady-state tests.
- API latency: p95 below 300 ms and p99 below 500 ms for ordinary non-scan requests.
- Saturation: CPU, memory, database connections, queue depth, and scanner backlog remain below alert thresholds with at least 30% headroom.
- RPO/RTO: explicitly declared and proven by restore/failover drills; never inferred from backup existence.

## Consequences

- The current VPS remains a supported controlled-beta topology after its exact-artifact gates pass; it is not described as enterprise scale.
- Horizontal scaling requires external state services and cannot be achieved by only increasing Uvicorn workers.
- Cloud infrastructure cost and operational ownership rise with each tier, but failure domains become explicit and testable.
- AEGIS can change cloud providers because the target is defined by service capabilities and receipts, not provider-specific marketing.

## Alternatives considered

- **Make the current VPS larger:** rejected as the enterprise path because it preserves every single point of failure.
- **Split immediately into microservices:** rejected until measured scaling domains justify the added operational complexity.
- **Treat Cloudflare as the complete backend platform:** rejected because durable relational state, evidence lifecycle, queues, scanning, recovery, and tenant controls still need governed backing services.
- **Claim capacity from low current CPU:** rejected because idle telemetry is not load evidence.
