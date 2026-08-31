# Production deployment runbook

## Where it goes

Use both Hostinger and Cloudflare, with different jobs:

- **Hostinger VPS:** runs the application container, dedicated PostgreSQL, encrypted evidence volume, and backup job.
- **Cloudflare:** owns DNS, TLS, Access identity/service policies, rate limits, and the outbound Tunnel. No inbound VPS application or database port is opened publicly.
- **This Windows machine:** keeps the private owner console and owner data. Do not point a public tunnel at its operator port.

The public showcase uses a separate stateless container, hostname, and tunnel token. It never mounts the customer database or evidence volumes.
Its Compose build also selects the dedicated `showcase` web profile. That profile excludes private mutation routes from the browser bundle and emits no public source maps.

## Required decisions before external release

Choose two dedicated hostnames on a domain you control, for example:

- `mission.example.com` — invited customer platform
- `demo.example.com` — public synthetic showcase

Do not reuse `ultrarag.app`, its current Windows tunnel, or an unrelated production hostname. Create dedicated Cloudflare Access applications and dedicated tunnel tokens.

## 1. Prepare the Hostinger VPS

Use an Ubuntu LTS VPS. Patch it, create a non-root deployment user, install Docker Engine with the Compose plugin, enable automatic security updates, and configure the firewall to allow only SSH from an approved administration path. The application uses an outbound Cloudflare Tunnel, so ports 80, 443, 5432, and 8080 do not need public inbound rules.

Copy the `mission-control` directory to an owner-controlled deployment directory on the VPS. Do not copy `.env` files, `runtime`, test databases, the local audit ledger, or private owner data.

For updates to an existing installation, create a Git archive of the reviewed
`mission-control` tree with an `AEGIS_COMMIT` receipt, transfer it to `/tmp`, and run
`deploy/vps/release.sh ARCHIVE RELEASE_TAG RELEASE_COMMIT`. The release script validates
archive paths and the commit receipt, builds digest-pinned dependencies, labels both
runtime images with the commit, switches `/opt/aegis/current` atomically, and rolls back
both containers if any health or post-deployment boundary check fails.

## 2. Create production secrets

Copy `deploy/vps/.env.production.example` to `deploy/vps/.env.production`, set permissions to owner-read/write only, and replace every placeholder. Generate unrelated random values for the database password, token pepper, evidence master key, and tunnel token.

The evidence key must be 32 random bytes encoded with URL-safe base64. Store an offline recovery copy in the approved secret manager. Losing this key makes evidence unrecoverable; exposing it compromises evidence confidentiality. Never put it in Git, screenshots, logs, chat, or the public demo environment.

`DATABASE_URL` must contain the URL-encoded database password. The database service has no published port and is reachable only on the internal Compose network.

## 3. Create Cloudflare identity boundaries first

Before creating the public hostname:

1. Create a Cloudflare Zero Trust self-hosted Access application for `mission.example.com`.
2. Add a default deny policy and an allow policy for explicitly invited customer identities or managed groups.
3. Create a more-specific Access application for `mission.example.com/api/v1/connector/*` using a Service Auth policy. Provision a distinct service token for each customer connector deployment process. A connector sends the Cloudflare service-token headers plus its AEGIS bearer credential; both layers must pass.
4. Record the human Access application's AUD value in `CF_ACCESS_AUD`. Set the team domain and exact public hostname in the production environment.
5. Add Cloudflare rate limits for authentication, invitation, task, evidence, and connector ingestion routes. Start conservatively and tune from measured customer traffic.
6. Create a dedicated named Tunnel and token. Configure one public hostname route: `mission.example.com` → `http://app:8080`.

The application also validates the human Access JWT audience/issuer and Host header. Connector endpoints depend on the Tunnel/Access service policy plus the connector's separately scoped AEGIS credential.

## 4. Validate and start the platform

From `mission-control/deploy/vps`:

```bash
docker compose --env-file .env.production -f compose.production.yml config
docker compose --env-file .env.production -f compose.production.yml build --pull
docker compose --env-file .env.production -f compose.production.yml up -d db app
curl --fail http://127.0.0.1:8780/api/health
curl --fail http://127.0.0.1:8780/api/ready
docker compose --env-file .env.production -f compose.production.yml up -d tunnel
```

The application entrypoint runs `alembic upgrade head` before starting. Production schema auto-creation is disabled; a failed migration prevents startup.

Verify these negative and positive paths before inviting anyone:

- uninvited human denied at Cloudflare;
- invited owner admitted to only the correct workspace;
- wrong Access audience denied by the application;
- connector without the service token denied at Cloudflare;
- connector with service token but wrong/revoked AEGIS token denied by the application;
- direct VPS public access unavailable;
- cross-workspace object identifiers denied;
- critical action denied without successful dry-run and different human approver;
- kill switch prevents new work and blocks queued/running work.

## 5. Back up and prove recovery

Run a first backup:

```bash
docker compose --env-file .env.production -f compose.production.yml --profile maintenance run --rm backup
```

The backup bundle contains a PostgreSQL custom-format dump, encrypted evidence directory, checksums, and a completion receipt. Copy backup bundles to off-VPS immutable storage with independent credentials and lifecycle policy. A local VPS volume is not a disaster-recovery backup.

Schedule the one-shot backup command daily. At least monthly, restore the latest bundle into a separately named disposable database ending in `_restore_drill`, validate record counts and evidence decryption, record measured recovery time/data loss, and destroy only that verified drill database afterward.

Do not interpret the presence of a dump file as proof of recoverability.

## 6. Publish the public showcase separately

Create `demo.example.com`, a separate public Tunnel, and `deploy/vps/.env.showcase` from its example. Then:

```bash
docker compose --env-file .env.showcase -f compose.showcase.yml config
docker compose --env-file .env.showcase -f compose.showcase.yml up -d --build
```

Configure the demo tunnel route to `http://showcase:8080`. Confirm:

- the UI says public/synthetic/read-only;
- `/api/snapshot` contains only synthetic/redacted values;
- `POST /api/runs` returns 403;
- there is no database/evidence volume or customer connector service;
- no production `.env` or secret exists in the showcase container.
- no `.map` artifact, `sourceMappingURL`, `/api/runs`, or `/api/v1/` string exists in the showcase web output.

## 7. Release and operations gates

Every release must pass:

```bash
python -m pytest -q
alembic upgrade head
alembic check
cd web
npm ci
npm audit --audit-level=high
npm run typecheck
npm run build
```

Also require dependency/container/secret scans, an SBOM, signed image provenance, Cloudflare policy review, backup receipt, recent restore evidence, and responsive/keyboard UI checks. Monitor health, error rates, denied authorization, connector freshness, telemetry gaps, approval age, audit-chain state, evidence-scan backlog, backup age, and open Shadow AI violations.

## Demoing the working product

For the challenge recording, use the private owner console locally and show a real allowlisted gate. Do not display secrets, browser tabs, terminals, personal paths, or notification content. Use the customer workspace locally for tenant controls and Shadow AI, populated with clearly labeled synthetic records. Use the public showcase URL only for audience follow-up.

The strongest one-minute proof is:

1. seven-team coverage identifies a real telemetry gap;
2. Shadow AI inventory creates a sensitive-data violation without storing a prompt;
3. a critical block action fails without dry-run/independent approval;
4. evidence lands quarantined and encrypted;
5. the audit-chain verifier detects tampering.

## Honest production boundary

This build supplies a strong single-region beta platform, not a certification or perfect-security claim. Database-enforced row security, externally managed per-tenant keys, integrated malware scanning, multi-region high availability, signed audit checkpoints, billing, contractual compliance mappings, independent penetration testing, and formal certifications remain explicit release-scope work for regulated or large-enterprise use. See `docs/THREAT_MODEL.md`.
