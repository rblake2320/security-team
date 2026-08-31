#!/bin/sh
set -eu

fail() {
  printf 'AEGIS restore drill refused: %s\n' "$1" >&2
  exit 2
}

umask 077
archive="${1:-}"
if [ -z "$archive" ]; then
  completed="$(find /var/backups/aegis -mindepth 2 -maxdepth 2 -type f -name COMPLETED | sort | tail -n 1)"
  [ -n "$completed" ] || fail "no completed backup exists"
  archive="$(dirname "$completed")"
fi

backup_id="$(basename "$archive")"
printf '%s\n' "$backup_id" | grep -Eq '^20[0-9]{6}T[0-9]{6}Z$' || fail "backup directory name is invalid"
[ "$archive" = "/var/backups/aegis/$backup_id" ] || fail "backup must be a direct child of /var/backups/aegis"
[ -d "$archive" ] && [ ! -L "$archive" ] || fail "backup directory is missing or symbolic"
for required in COMPLETED SHA256SUMS database.dump evidence.tar.gz database-counts.tsv RECEIPT.json; do
  [ -f "$archive/$required" ] && [ ! -L "$archive/$required" ] || fail "backup is missing $required"
done

restore_database="${RESTORE_DRILL_DATABASE:-aegis_monthly_restore_drill}"
printf '%s\n' "$restore_database" | grep -Eq '^[a-z][a-z0-9_]{0,47}_restore_drill$' || \
  fail "RESTORE_DRILL_DATABASE must be a safe PostgreSQL identifier ending in _restore_drill"

(cd "$archive" && sha256sum -c SHA256SUMS)
if tar -tzf "$archive/evidence.tar.gz" | grep -E '(^/|(^|/)\.\.(/|$))' >/dev/null; then
  fail "evidence archive contains an unsafe path"
fi
evidence_entries="$(tar -tzf "$archive/evidence.tar.gz" | awk 'END { print NR + 0 }')"

export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
username="${POSTGRES_USER:?POSTGRES_USER is required}"
started_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
started_epoch="$(date -u +%s)"
backup_epoch="$(stat -c %Y "$archive/COMPLETED")"
backup_age_seconds="$((started_epoch - backup_epoch))"
database_created=0

cleanup() {
  if [ "$database_created" -eq 1 ]; then
    dropdb --host db --username "$username" --force --if-exists "$restore_database" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT HUP INT TERM

dropdb --host db --username "$username" --force --if-exists "$restore_database"
createdb --host db --username "$username" --owner "$username" "$restore_database"
database_created=1
pg_restore \
  --host db \
  --username "$username" \
  --dbname "$restore_database" \
  --clean --if-exists --exit-on-error \
  "$archive/database.dump"

count_sql="/tmp/aegis-restore-count-tables.sql"
actual_counts="/tmp/aegis-restore-database-counts.tsv"
psql \
  --host db \
  --username "$username" \
  --dbname "$restore_database" \
  --no-align \
  --tuples-only \
  --set ON_ERROR_STOP=1 \
  --command "SELECT format('SELECT %L || chr(9) || count(*)::text FROM %I.%I;', schemaname || '.' || tablename, schemaname, tablename) FROM pg_catalog.pg_tables WHERE schemaname = 'public' ORDER BY tablename" \
  > "$count_sql"
psql \
  --host db \
  --username "$username" \
  --dbname "$restore_database" \
  --no-align \
  --tuples-only \
  --set ON_ERROR_STOP=1 \
  --file "$count_sql" \
  > "$actual_counts"

expected_counts_hash="$(sha256sum "$archive/database-counts.tsv" | awk '{ print $1 }')"
actual_counts_hash="$(sha256sum "$actual_counts" | awk '{ print $1 }')"
[ "$expected_counts_hash" = "$actual_counts_hash" ] || fail "restored table counts do not match the backup receipt"

table_count="$(awk 'END { print NR + 0 }' "$actual_counts")"
row_count="$(awk -F '\t' '{ total += $2 } END { print total + 0 }' "$actual_counts")"
[ "$table_count" -gt 0 ] || fail "restored database contains no public tables"

dropdb --host db --username "$username" --force "$restore_database"
database_created=0
trap - EXIT HUP INT TERM

completed_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
completed_epoch="$(date -u +%s)"
duration_seconds="$((completed_epoch - started_epoch))"
receipt_dir="/var/backups/aegis/restore-receipts"
receipt_stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$receipt_dir"
receipt_tmp="$receipt_dir/.$backup_id-$receipt_stamp.json.tmp"
receipt="$receipt_dir/$backup_id-$receipt_stamp.json"
printf '{"schemaVersion":1,"status":"passed","backupId":"%s","startedAt":"%s","completedAt":"%s","durationSeconds":%s,"backupAgeSeconds":%s,"databaseTables":%s,"databaseRows":%s,"encryptedEvidenceArchiveEntries":%s,"checksumsVerified":true,"rowCountsVerified":true,"disposableDatabaseDropped":true}\n' \
  "$backup_id" "$started_at" "$completed_at" "$duration_seconds" "$backup_age_seconds" \
  "$table_count" "$row_count" "$evidence_entries" \
  > "$receipt_tmp"
mv "$receipt_tmp" "$receipt"
printf 'AEGIS restore drill passed: %s\n' "$receipt"
