#!/bin/sh
set -eu

archive="${1:?usage: restore-drill.sh /var/backups/aegis/TIMESTAMP}"
case "${RESTORE_DRILL_DATABASE:-}" in
  *_restore_drill) ;;
  *) printf 'RESTORE_DRILL_DATABASE must end in _restore_drill\n' >&2; exit 2 ;;
esac
test -f "$archive/COMPLETED"
(cd "$archive" && sha256sum -c SHA256SUMS)
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
pg_restore \
  --host db \
  --username "${POSTGRES_USER:?POSTGRES_USER is required}" \
  --dbname "$RESTORE_DRILL_DATABASE" \
  --clean --if-exists --exit-on-error \
  "$archive/database.dump"
printf 'Restore drill completed in disposable database: %s\n' "$RESTORE_DRILL_DATABASE"
