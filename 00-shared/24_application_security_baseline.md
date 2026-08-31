# Application Security Abuse-Case Baseline

**Document set version:** 1.0
**Status:** Engineering baseline — not an assessment or authorization
**Applies to:** Web applications, APIs, mobile backends, webhooks, workers, and service-to-service interfaces

Machine-readable catalog and CI source: [`config/application_security_baseline.json`](config/application_security_baseline.json)

This baseline turns common application-security mistakes into requirements that can be reviewed
by Orange, implemented by Yellow, observed by Green, and exercised by Purple or an independently
authorized Red engagement. It does not authorize testing.

The source notes that prompted this baseline were truncated after the SSRF discussion. Items 1–7
below preserve the distinct mistakes present in those notes. Items 8–10 complete the engineering
baseline using closely related OWASP API Security risk classes; they are not represented as missing
verbatim content from the source.

## The invariant

The server makes every security decision. For each request or message it determines, from trusted
server-side state:

`actor -> action -> resource -> allowed fields -> workflow state -> limits`

Client visibility, button state, route names, object identifiers, request fields, and an upstream
service's success flag are inputs—not proof. Access is denied unless an explicit policy allows the
complete tuple. Authentication answers *who*; authorization still decides *what this actor may do
to this resource now*.

## Ten mistakes converted into controls

| # | Mistake / abuse case | Required control | Minimum safe negative test |
|---|---|---|---|
| 1 | **Trusting the front end.** A hidden admin control or disabled field is treated as enforcement. | Enforce authentication, authorization, validation, and workflow rules at the backend on every route, resolver, handler, consumer, and job entry point. Return only fields the actor may receive. | Send the same request without using the UI, including a hidden route and client-disabled field; the backend denies it and makes no state change. |
| 2 | **Broken function-level authorization.** A normal user invokes an administrative operation. | Define a deny-by-default policy per action. Centralize enforcement where possible, but test every exposed function and alternate method/path. | A standard user calls every admin mutation and receives a consistent denial; the audit event records the actor, action, target, and policy result without secrets. |
| 3 | **Broken object-level authorization (IDOR/BOLA).** A user changes an identifier to read or mutate another user's or tenant's object. | Scope every lookup and mutation to the authenticated actor's tenant and relationship to the object. Unpredictable identifiers are defense in depth, not authorization. | Swap the object and tenant identifiers with another valid object's values for read, update, delete, export, and nested-resource operations; all are denied without revealing whether the object exists. |
| 4 | **Broken property-level authorization / mass assignment.** A user writes `role`, `owner_id`, `tenant_id`, price, approval state, or another server-controlled field. | Use operation-specific input models and explicit writable-field allowlists. Derive ownership, tenant, price, roles, and workflow state from trusted server-side sources. Apply response-field allowlists too. | Add privileged, unknown, read-only, and nested fields to a legitimate request; the server rejects or ignores them by documented policy and never persists or returns unauthorized values. |
| 5 | **Broken business workflow.** A caller skips payment, approval, verification, inventory reservation, or another required transition and claims the outcome directly. | Model sensitive flows as server-side state machines with explicit allowed transitions, preconditions, transaction boundaries, and single-use/idempotency rules. Re-check authorization and business facts at the transition. | Attempt steps out of order, repeat a completed step, reuse a token, submit concurrently, and alter price/quantity between steps; no reward, shipment, credit, or approval is produced improperly. |
| 6 | **Blind trust in external APIs.** Authentication, payment, identity, fraud, or data-provider responses are accepted merely because the upstream returned success. | Authenticate the peer and callback, verify signatures/audience/issuer/nonce/timestamp where applicable, validate schema and semantics, bind the response to the originating transaction, constrain privileges, and fail closed. Reconcile important outcomes independently. | Replay, reorder, expire, cross-bind, omit, duplicate, and alter a valid-looking upstream response; the application rejects it and alerts on integrity or reconciliation failure. |
| 7 | **Server-side request forgery (SSRF).** User-controlled input causes the server to request an attacker-chosen URL or address. | Prefer destination identifiers over URLs. Allowlist scheme, host, port, and path; resolve and validate every address; block loopback, link-local, private, multicast, metadata, and unsupported protocols; disable redirects; restrict egress at the network layer; cap time and response size. | Test alternate IP encodings, IPv4/IPv6, DNS changes, credentials in URLs, redirects, private/link-local/metadata destinations, non-HTTP schemes, and oversized/slow responses; none reaches a forbidden destination. |
| 8 | **Unbounded resource consumption.** Requests can exhaust CPU, memory, storage, threads, outbound calls, messages, or paid provider quota. | Apply actor-, tenant-, operation-, and global budgets; bound pagination, uploads, query complexity, fan-out, retries, timeouts, concurrency, and queued work. Degrade predictably and make expensive actions observable. | Exceed each documented bound and exercise concurrent/slow requests; work is rejected or curtailed before resource or cost exhaustion, while normal tenants retain service. |
| 9 | **Unrestricted automation of sensitive business flows.** A valid operation—signup, reservation, purchase, coupon, password reset, scraping—is abused at machine scale. | Identify business-sensitive flows and enforce contextual velocity, inventory, uniqueness, anti-replay, step-up verification, anomaly detection, and recoverable business limits. Do not rely on one IP-address limit. | Distribute attempts across accounts, sessions, devices, and addresses and vary request timing; aggregate controls stop abuse without silently completing partial transactions. |
| 10 | **Forgotten or inconsistent API surface.** Old versions, debug routes, alternate content types, webhooks, queues, GraphQL fields, or internal endpoints bypass the main policy. | Maintain an owner-tagged inventory of every deployed interface and version. Put common security middleware and policy checks on all entry points, remove obsolete surfaces, and continuously compare deployment to inventory. | Run the same authorization and validation matrix through alternate methods, versions, encodings, batch endpoints, and asynchronous consumers; no weaker path exists, and unknown surfaces fail the release gate. |

## Required review questions

For every application change, answer these before approval:

1. Which actors can reach this entry point without the intended UI?
2. Which actions may each actor perform, on exactly which objects and tenant?
3. Which request and response properties may each actor read or write?
4. What state must already exist, and which state transitions are legal?
5. What happens on replay, duplication, reordering, and concurrent execution?
6. Which external claims are authenticated, validated, transaction-bound, and reconciled?
7. Can any input influence a network destination, protocol, redirect, or DNS resolution?
8. What is bounded per request, actor, tenant, dependency, and globally?
9. How could a valid business function be abused through automation?
10. Which alternate or legacy interface could reach the same operation?

An answer such as “the UI prevents it,” “the ID is hard to guess,” “the provider said success,”
or “that endpoint is internal” is an unverified assumption and becomes an abuse case.

## Evidence and handoff

For each applicable row, the change record must link:

- an Orange abuse case and explicit trust-boundary assumption;
- a Yellow requirement and a negative regression test that fails on the vulnerable behavior;
- a Green telemetry assertion for allow, deny, replay, limit, and upstream-validation decisions;
- a named owner, deployment surface, and remediation or accepted-deviation record;
- Purple/Red test coverage only when the exercise plan and authorization permit it.

Security tests use synthetic identities and data in CI or a designated test environment. They
assert denial and absence of unauthorized side effects; they do not contain exploit payloads,
credentials, production identifiers, or uncontrolled callbacks.

## Standards alignment

- OWASP API Security Top 10 (2023): API1, API3, API4, API5, API6, API7, API9, and API10.
- OWASP Application Security Verification Standard (ASVS) 5.0.0 for requirement-level
  verification; record the exact ASVS IDs selected for each system rather than claiming blanket
  conformance from this summary.
- OWASP Authorization Cheat Sheet and SSRF Prevention Cheat Sheet for implementation detail.

This crosswalk is guidance, not certification. The applicable ASVS level and requirements must be
chosen and evidenced for the system being built.
