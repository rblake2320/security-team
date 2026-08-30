#!/bin/sh
set -eu

umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/var/backups/aegis/$stamp"
mkdir -p "$target"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

pg_dump \
  --host db \
  --username "${POSTGRES_USER:?POSTGRES_USER is required}" \
  --dbname "${POSTGRES_DB:?POSTGRES_DB is required}" \
  --format custom \
  --file "$target/database.dump"

tar -C /var/lib/aegis -czf "$target/evidence.tar.gz" evidence
sha256sum "$target/database.dump" "$target/evidence.tar.gz" > "$target/SHA256SUMS"
printf '%s\n' "$stamp" > "$target/COMPLETED"
find /var/backups/aegis -mindepth 1 -maxdepth 1 -type d -mtime +30 -exec rm -rf -- {} +
printf 'AEGIS backup completed: %s\n' "$target"
