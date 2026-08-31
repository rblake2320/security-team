# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

The private owner operates AEGIS against their own security-team systems and data. Public customers operate isolated workspaces against their own systems through explicitly provisioned connectors. A public evaluator can use a synthetic, read-only showcase without access to owner or customer data.

## Product Purpose

AEGIS Mission Control is a security operations control plane for coordinating seven security-team functions, agents, evidence, approvals, incidents, and Shadow AI defense. Success means an operator can see what is protected, what is observable, what remains a gap, who owns each decision, and what enforcement is safe to execute.

## Positioning

AEGIS joins multi-agent mission control with evidence-backed security governance. It separates engineering health from assurance, treats high-impact actions as governed work, and makes Shadow AI part of the full security operating model instead of a standalone inventory page.

## Operating Context

The product has three non-overlapping environments: the owner's private operator instance, a synthetic public showcase, and tenant-isolated customer workspaces. Customer connectors are outbound-only collectors and executors. Cloudflare provides the public edge and identity boundary; a dedicated application service and PostgreSQL database hold tenant-scoped operational records.

## Capabilities and Constraints

- Durable workspaces, users, roles, connectors, agents, tasks, approvals, evidence, findings, incidents, retention, and tamper-evident audit records.
- Deny-by-default action catalog, dry-runs for critical actions, independent approval, safety levels, and a kill switch.
- Shadow AI inventory across endpoints, networks, cloud services, models, tools, agents, MCP servers, and resources.
- Customer-defined approved vendors/domains, blocked domains, sensitive-data labels, retention, and enforcement connectors.
- Raw AI prompts and responses are not retained. User and device references from discovery feeds are pseudonymized.
- The browser receives compiled interface assets and tenant-authorized API data, never server source, secret material, or another workspace's records.
- No absolute “zero blind spots” claim is permitted. Coverage is reported as proven, configured, missing telemetry, excepted, or unknown.

## Brand Commitments

The name is AEGIS Mission Control. The existing dark, high-information command-center identity and seven-team spectrum remain recognizable. Copy is direct, precise, evidence-led, and avoids unsupported assurance claims.

## Evidence on Hand

The repository contains the existing AEGIS program model, seven team definitions, executable gates, local observer integration, audit-chain implementation, and a working Mission Control interface. The public showcase must use clearly labeled synthetic records; no customer proof, benchmarks, or testimonials may be fabricated.

## Product Principles

1. Private by construction: owner, showcase, and customer data never share a runtime data store.
2. Evidence before assurance: unknowns and gaps remain visible and cannot be averaged away.
3. Govern every consequential action: least privilege, approval, dry-run, audit, and reversible execution where possible.
4. Make AI defense a team sport: discovery, prevention, detection, response, validation, and governance have explicit owners.
5. Give customers control without exposing implementation or other tenants.

## Accessibility & Inclusion

The web interface must support keyboard operation, visible focus, reduced motion, semantic status text, responsive layouts, and WCAG AA contrast for essential content.

## Temporary Deployment-Boundary Exception

The owner and showcase deployments currently use separate subdomains of `aihangout.ai` for the challenge and review period. This is a temporary hosting exception, not permission to share identities, application sessions, connectors, databases, evidence stores, secrets, or runtime state across the owner, showcase, and customer environments. Cloudflare Access also inherits account-level sign-in branding during this period. Before general availability, AEGIS must move to dedicated product branding and a reviewed domain/cookie boundary; no AEGIS session cookie may be scoped to the parent domain.
