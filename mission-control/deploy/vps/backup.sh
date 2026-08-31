#!/bin/sh
set -eu

umask 077
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
target="/var/backups/aegis/$stamp"
mkdir -p "$target"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"

database="${POSTGRES_DB:?POSTGRES_DB is required}"
username="${POSTGRES_USER:?POSTGRES_USER is required}"
snapshot_fifo="/tmp/aegis-backup-snapshot.$$"
snapshot_pid=""

cleanup_snapshot() {
  rm -f "$snapshot_fifo"
  if [ -n "$snapshot_pid" ]; then
    kill "$snapshot_pid" >/dev/null 2>&1 || true
    wait "$snapshot_pid" >/dev/null 2>&1 || true
  fi
}
trap cleanup_snapshot EXIT HUP INT TERM

# Hold one exported repeatable-read snapshot while both pg_dump and the row
# manifest run. Without this, normal application writes could make a valid
# dump disagree with counts collected a moment later.
mkfifo "$snapshot_fifo"
psql \
  --host db \
  --username "$username" \
  --dbname "$database" \
  --no-psqlrc \
  --quiet \
  --no-align \
  --tuples-only \
  --set ON_ERROR_STOP=1 \
  > "$snapshot_fifo" <<'SQL' &
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SELECT pg_export_snapshot();
SELECT pg_sleep(86400);
ROLLBACK;
SQL
snapshot_pid=$!
IFS= read -r snapshot_id < "$snapshot_fifo"
rm -f "$snapshot_fifo"
printf '%s\n' "$snapshot_id" | grep -Eq '^[0-9A-Fa-f-]+$' || {
  printf 'AEGIS backup failed: PostgreSQL returned an invalid snapshot identifier\n' >&2
  exit 2
}

pg_dump \
  --host db \
  --username "$username" \
  --dbname "$database" \
  --snapshot "$snapshot_id" \
  --format custom \
  --file "$target/database.dump"

tar -C /var/lib/aegis -czf "$target/evidence.tar.gz" evidence

# Record exact per-table row counts so a restore drill proves logical parity,
# rather than merely proving that pg_restore exited successfully.
psql \
  --host db \
  --username "$username" \
  --dbname "$database" \
  --no-psqlrc \
  --quiet \
  --no-align \
  --tuples-only \
  --set ON_ERROR_STOP=1 \
  --set snapshot_id="$snapshot_id" \
  > "$target/database-counts.tsv" <<'SQL'
BEGIN TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET TRANSACTION SNAPSHOT :'snapshot_id';
SELECT format(
  'SELECT %L || chr(9) || count(*)::text FROM %I.%I;',
  schemaname || '.' || tablename,
  schemaname,
  tablename
)
FROM pg_catalog.pg_tables
WHERE schemaname = 'public'
ORDER BY tablename
\gexec
COMMIT;
SQL

cleanup_snapshot
snapshot_pid=""
trap - EXIT HUP INT TERM

table_count="$(awk 'END { print NR + 0 }' "$target/database-counts.tsv")"
row_count="$(awk -F '\t' '{ total += $2 } END { print total + 0 }' "$target/database-counts.tsv")"
evidence_entries="$(tar -tzf "$target/evidence.tar.gz" | awk 'END { print NR + 0 }')"
printf '{"schemaVersion":1,"backupId":"%s","databaseTables":%s,"databaseRows":%s,"encryptedEvidenceArchiveEntries":%s}\n' \
  "$stamp" "$table_count" "$row_count" "$evidence_entries" \
  > "$target/RECEIPT.json"

sha256sum \
  "$target/database.dump" \
  "$target/evidence.tar.gz" \
  "$target/database-counts.tsv" \
  "$target/RECEIPT.json" \
  > "$target/SHA256SUMS"
printf '%s\n' "$stamp" > "$target/COMPLETED"
find /var/backups/aegis \
  -mindepth 1 \
  -maxdepth 1 \
  -type d \
  -name '20??????T??????Z' \
  -mtime +30 \
  -exec rm -rf -- {} +
printf 'AEGIS backup completed: %s\n' "$target"
