#!/bin/sh
set -eu

if [ "${AEGIS_ENV:-development}" = "production" ]; then
  : "${DATABASE_ADMIN_URL:?set DATABASE_ADMIN_URL to the migration-only PostgreSQL credential}"
  : "${AEGIS_DB_RUNTIME_PASSWORD:?set AEGIS_DB_RUNTIME_PASSWORD to an independent secret}"
  DATABASE_URL="$DATABASE_ADMIN_URL" alembic upgrade head
  python -m aegis_platform.db_roles provision
  DATABASE_URL="$(python -m aegis_platform.db_roles runtime-url)"
  export DATABASE_URL
fi

exec uvicorn aegis_platform.api:create_app \
  --factory \
  --host "${AEGIS_HOST:-0.0.0.0}" \
  --port "${AEGIS_PORT:-8080}" \
  --workers "${AEGIS_WORKERS:-1}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --no-server-header
