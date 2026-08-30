#!/bin/sh
set -eu

if [ "${AEGIS_ENV:-development}" = "production" ]; then
  alembic upgrade head
fi

exec uvicorn aegis_platform.api:create_app \
  --factory \
  --host "${AEGIS_HOST:-0.0.0.0}" \
  --port "${AEGIS_PORT:-8080}" \
  --workers "${AEGIS_WORKERS:-1}" \
  --proxy-headers \
  --forwarded-allow-ips "${FORWARDED_ALLOW_IPS:-*}" \
  --no-server-header
