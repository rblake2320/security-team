# AEGIS Mission Control

AEGIS is a security operations control plane for seven coordinated security-team functions, governed agent actions, evidence, incidents, and Shadow AI defense.

It has three deliberately separate product surfaces:

| Surface | Data | Controls | Runtime |
|---|---|---|---|
| Private owner console | live local owner data | local allowlisted gates | this machine, loopback only |
| Public showcase | synthetic and redacted only | removed server-side | separate stateless container and tunnel |
| Customer platform | that customer's tenant data only | role-, policy-, approval-, and connector-scoped | dedicated application, PostgreSQL, encrypted evidence |

There is no supported path from the showcase or a customer workspace into the owner's local records. The hosted product keeps authorization, policy, evidence handling, tenant filtering, and execution logic on the server; the browser receives the compiled interface and authorized API responses.

## Run the functioning local product

The Markdown files describe the operating model; they are not the runtime. The functioning product is the hosted-style Mission Control API/UI plus the included customer-edge connector that consumes approved work and executes it against an explicitly allowlisted folder or hostname.

From `C:\Users\techai\security-team`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\mission-control\launch-product.ps1
```

That one command opens `http://127.0.0.1:8790/#/engagements`, starts the durable local platform, provisions an ephemeral least-privilege connector, and starts seven visible team workers against only `C:\Users\techai\security-team`. The credential remains process-only and is revoked when the launcher stops.

To authorize a web target at the connector boundary as well as in the engagement:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\mission-control\launch-product.ps1 -AllowedHost staging.example.com,api.staging.example.com
```

Inside the product: create an engagement, choose **Repository**, enter the exact authorized folder, record the authority and stop conditions, then queue the assessment. Mission Control opens the approval queue; after approval, the connector leases the work, runs the seven-team inspection, returns stable findings and recommendations, and makes the result available for comparison and ZIP export. A configured-but-offline connector is shown as offline and cannot make the assessment button appear ready.

### Model-independence contract

AEGIS does not require a frontier model to complete its core workflow. With every model API unavailable, the application still persists workspace and engagement state, enforces identity and approvals, leases tasks, inspects allowlisted repositories and HTTP targets, analyzes bounded evidence, runs declared engineering gates, records seven-team results and stable finding fingerprints, compares runs, exports evidence, and verifies the audit chain. The connector uses only the Python standard library and the local tools explicitly invoked by an approved gate.

Future model integrations are optional advisory capabilities. They must use a separately scoped connector capability, identify their provider and model in the audit record, treat retrieved content as untrusted data, and never replace deterministic authorization, evidence, scoring overrides, task state, or audit decisions. Removing an advisory model must reduce enrichment only; it must not stop the product.

## Private owner console

From `C:\Users\techai\security-team`:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\mission-control\launch.ps1
```

Open `http://127.0.0.1:8765`. This server refuses non-loopback binding and reads the repository's authoritative manifests, local gate runner, bounded observer metadata, Git state, and append-only action ledger.

## Local customer-platform development

```powershell
Set-Location C:\Users\techai\security-team\mission-control
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Set-Location web
npm ci
npm run build
Set-Location ..
.\.venv\Scripts\python.exe saas_server.py
```

Open `http://127.0.0.1:8780`. Development identity headers work only from loopback. Production refuses to start without PostgreSQL, Cloudflare Access settings, a dedicated hostname, unique secret material, and an encrypted-evidence master key.

## Hosted platform capabilities

- Tenant workspaces, invited users, roles, programs, authorized engagements, connectors, agents, tasks, approvals, evidence, findings, incidents, retention, and exports.
- An engagement workspace for owner-site reviews, pre-launch reviews, client-authorized work, and continuous assurance. Each engagement records targets, scope, exclusions, stop conditions, authority, selected teams, evidence, assessment runs, findings, and recommendations.
- Drag-and-drop media intake for documents, images, audio, video, code/data, and archives. Files are encrypted immediately, scanned by a private fail-closed ClamAV service, held in quarantine until cleared, and never made public by the showcase.
- PostgreSQL-enforced row-level tenant isolation using a restricted runtime role and transaction-local identity/organization context.
- Versioned assessment runs with stable finding fingerprints, baseline comparison, introduced/persistent/resolved results, and a portable ZIP containing JSON, CSV registers, audit records, and a human-readable manifest.
- One-time connector credentials stored only as HMAC digests, explicit observation/action capabilities, revocation, heartbeat, idempotent event ingestion, and bounded payloads.
- Deny-by-default action catalog with risk levels, human approval, successful dry-runs for critical actions, separation of duties, expiring leases, safety levels, and a kill switch.
- Quarantined evidence with path/type/size controls, real malware verdicts, plaintext SHA-256 integrity, per-workspace derived AES-GCM encryption, legal holds, and retention sweeps.
- Per-tenant hash-chained audit records with a verifier.
- Alembic schema migrations, production configuration validation, database timeouts, secure response headers, strict host validation, non-root read-only containers, and health/readiness probes.
- A 50+ control security-coverage baseline spanning identity, endpoint, network, cloud, SaaS, application/API, data, vulnerability, supply chain, privacy, third party, resilience, incident response, and adversarial validation.
- A shipped, model-independent customer-edge execution connector (`python -m aegis_connector`) with independent local path/hostname allowlists, outbound-only task leasing, renewable leases, seven-team repository review, passive web/API checks, bounded evidence analysis, result ingestion, heartbeat visibility, and explicit failure for unsupported target types.

## Customer-edge connector

Provision a connector credential in **Workspace Controls**, granting only the required capabilities. Put the credential in the operating-system secret manager or a mounted secret file, configure the exact local roots and hosts, and prove the connection before starting the service:

```powershell
$env:AEGIS_API_URL = "https://mission.example.com"
$env:AEGIS_CONNECTOR_TOKEN_FILE = "C:\secure\aegis_connector_token"
$env:AEGIS_PROGRAM_ROOT = "C:\authorized\security-team"
$env:AEGIS_ALLOWED_ROOTS = "C:\authorized\customer-repository"
$env:AEGIS_ALLOWED_HOSTS = "staging.example.com,api.staging.example.com"
python -m aegis_connector --doctor
python -m aegis_connector
```

For container deployment, use `Dockerfile.connector` and `deploy/connector/compose.example.yml`. The connector container runs without root, drops Linux capabilities, uses a read-only filesystem, mounts the authorized workspace read-only, accepts secrets through mounted files, and exposes no inbound port.

## Shadow AI defense

Shadow AI is part of every team's work, not an isolated widget:

- **Purple:** validates the full discover → prevent → detect → respond → retest loop.
- **White:** owns policy, exceptions, independent authority, privacy, retention, and audit.
- **Yellow:** secures AI-generated code, dependencies, models, tools, plugins, artifacts, and MCP supply chains.
- **Green:** maps identities, devices, trust boundaries, models, tools, agents, resources, and data paths.
- **Orange:** maintains prompt-injection, exfiltration, poisoning, tool-abuse, evasion, fraud, and misuse cases.
- **Blue:** discovers network/endpoint/cloud AI, applies data classification, detects violations, preserves evidence, and coordinates response.
- **Red:** performs separately authorized validation of prompt injection, agent misuse, data exfiltration, local models, alternate clients, tunnels, and discovery evasion.

The platform stores AI asset and usage metadata—destination, model, tools, MCP servers, resources, data labels, volume, token counts, and estimated cost. It does not accept or retain raw prompts or responses. User and device references are pseudonymized before persistence.

## Public showcase

The containerized showcase is a separate stateless demo with a synthetic readiness program, synthetic agent feed, no database, no customer connectors, and HTTP 403 for every control action.

For a temporary local preview:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\mission-control\share-demo.ps1
```

For a stable public showcase, use `deploy/vps/compose.showcase.yml` with its own hostname and Cloudflare tunnel token. Never reuse the customer-platform database, volumes, environment file, or tunnel.

## Authorized engagement workflow

Open **Engagements**, choose a template, and record the target, environment, objective, scope, exclusions, stop conditions, and authorization. Add only targets the customer owns or has explicitly authorized. Select the security teams that should participate, then create the workspace.

Drop supporting files into the engagement. AEGIS encrypts each file and sends its bounded plaintext stream over the private internal network to ClamAV. Only the engine's clean verdict releases it; malware or scanner failure keeps it blocked. Clean files can be downloaded by an authorized human or analyzed by a leased, capability-scoped connector. Raw uploaded files are deliberately excluded from engagement exports.

To assess a live site, API, repository, cloud environment, or supplied artifact, provision a customer-owned connector with the narrow `assessment.execute` capability. Launching creates a high-risk task that must receive human approval before a connector can lease it. Without that connector and approval, AEGIS reports the missing prerequisite and does not claim an assessment ran.

Export the engagement at any time to preserve its scope, findings, asset register, audit trail, and run comparison. Run it again after changes and select **Compare latest** to show what was introduced, what persists, and what was resolved.

## Verification

```powershell
Set-Location C:\Users\techai\security-team\mission-control
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe check
.\.venv\Scripts\python.exe tools\test_onboarding_ui.py
Set-Location web
npm audit --audit-level=high
npm run typecheck
npm run build
```

The implementation threat model and honest residual-risk register live in `docs/THREAT_MODEL.md`. VPS and Cloudflare release steps live in `PRODUCTION.md`.

## 60-second demo sequence

1. **0–8s:** Command view—“AEGIS shows what is protected, what is proven, and what is still unknown.”
2. **8–20s:** Security Coverage—show seven-team ownership and telemetry gaps that cannot be averaged away.
3. **20–34s:** Shadow AI—show inventory, data-egress metadata, customer policy, and prompt-retention permanently off.
4. **34–47s:** Workspace Controls—show connector scope, an approval, and the governed critical-action path.
5. **47–56s:** Evidence—show quarantine, encryption/integrity, and the valid audit chain.
6. **56–60s:** Close with: **“Trust is a state. Prove every transition.”**
