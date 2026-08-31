#!/bin/sh
set -eu

# Atomic AEGIS Mission Control release with health-gated rollback.
# Usage: ./release.sh /tmp/aegis-<commit>.tgz <release-tag> <40-char-commit>

fail() {
  printf 'AEGIS release refused: %s\n' "$1" >&2
  exit 2
}

[ "$#" -eq 3 ] || fail "expected ARCHIVE RELEASE_TAG RELEASE_COMMIT"
[ "$(id -u)" -eq 0 ] || fail "run as root on the dedicated AEGIS VPS"

archive="$1"
release_tag="$2"
release_commit="$3"
current=/opt/aegis/current
release="/opt/aegis/releases/$release_tag/mission-control"

case "$archive" in
  /tmp/aegis-*.tgz) ;;
  *) fail "archive must be a /tmp/aegis-*.tgz file" ;;
esac
case "$release_tag" in
  ''|*[!A-Za-z0-9._-]*) fail "release tag contains unsafe characters" ;;
esac
case "$release_commit" in
  *[!0-9a-f]*) fail "release commit must be lowercase hexadecimal" ;;
esac
[ "${#release_commit}" -eq 40 ] || fail "release commit must contain 40 characters"
[ -f "$archive" ] && [ ! -L "$archive" ] || fail "archive is missing or is a symbolic link"
[ ! -e "$release" ] || fail "release already exists: $release"

tar -tzf "$archive" >/dev/null
if tar -tzf "$archive" | grep -E '(^/|(^|/)\.\.(/|$))' >/dev/null; then
  fail "archive contains an unsafe path"
fi

previous="$(readlink -f "$current")"
case "$previous" in
  /opt/aegis/releases/*/mission-control) ;;
  *) fail "current release does not resolve inside /opt/aegis/releases" ;;
esac
[ -d "$previous/deploy/vps" ] || fail "current release is incomplete"

previous_operator_image="$(cd "$previous/deploy/vps" && docker inspect --format '{{.Config.Image}}' "$(docker compose --env-file .env.production -f compose.production.yml ps --quiet app)")"
previous_showcase_image="$(cd "$previous/deploy/vps" && docker inspect --format '{{.Config.Image}}' "$(docker compose --env-file .env.showcase -f compose.showcase.yml ps --quiet showcase)")"
previous_operator_tag="${previous_operator_image##*:}"
previous_showcase_tag="${previous_showcase_image##*:}"
revision_before="$(cd "$previous/deploy/vps" && docker compose --env-file .env.production -f compose.production.yml exec -T app alembic current 2>/dev/null | tail -n 1)"
switched=0

rollback() {
  [ "$switched" -eq 1 ] || return 0
  printf 'AEGIS release failed; restoring %s\n' "$previous" >&2
  ln -sfn "$previous" /opt/aegis/current.rollback
  mv -Tf /opt/aegis/current.rollback "$current"
  cd "$previous/deploy/vps"
  AEGIS_IMAGE_TAG="$previous_operator_tag" docker compose --env-file .env.production -f compose.production.yml up --detach --no-deps --force-recreate app
  AEGIS_IMAGE_TAG="$previous_showcase_tag" docker compose --env-file .env.showcase -f compose.showcase.yml up --detach --no-deps --force-recreate showcase
  switched=0
}

on_exit() {
  status=$?
  if [ "$status" -ne 0 ]; then
    rollback || printf 'AEGIS automatic rollback also failed; operator intervention required\n' >&2
  fi
  trap - 0
  exit "$status"
}
trap on_exit 0

wait_healthy() {
  compose_file="$1"
  env_file="$2"
  service="$3"
  max_attempts="${4:-60}"
  attempt=0
  while [ "$attempt" -lt "$max_attempts" ]; do
    container_id="$(docker compose --env-file "$env_file" -f "$compose_file" ps --quiet "$service")"
    health="$(docker inspect --format '{{.State.Health.Status}}' "$container_id" 2>/dev/null || true)"
    [ "$health" = healthy ] && return 0
    attempt=$((attempt + 1))
    sleep 2
  done
  docker compose --env-file "$env_file" -f "$compose_file" logs --tail 100 "$service" >&2 || true
  return 1
}

umask 077
mkdir -p "$release"
tar -xzf "$archive" -C "$release"
[ -z "$(find "$release" -type l -print -quit)" ] || fail "release archive contains a symbolic link"
[ "$(cat "$release/AEGIS_COMMIT")" = "$release_commit" ] || fail "archive commit receipt does not match"
install -m 0600 "$previous/deploy/vps/.env.production" "$release/deploy/vps/.env.production"
install -m 0600 "$previous/deploy/vps/.env.showcase" "$release/deploy/vps/.env.showcase"

cd "$release/deploy/vps"
docker compose --env-file .env.production -f compose.production.yml config --quiet
docker compose --env-file .env.showcase -f compose.showcase.yml config --quiet
AEGIS_IMAGE_TAG="$release_tag" AEGIS_COMMIT="$release_commit" docker compose --env-file .env.production -f compose.production.yml build --pull app
AEGIS_IMAGE_TAG="$release_tag" AEGIS_COMMIT="$release_commit" docker compose --env-file .env.showcase -f compose.showcase.yml build --pull showcase

# Warm the private malware scanner before switching releases. The bounded
# seven-minute allowance covers first-run signature initialization.
docker compose --env-file .env.production -f compose.production.yml up --detach clamav
wait_healthy compose.production.yml .env.production clamav 210

switched=1
ln -sfn "$release" /opt/aegis/current.next
mv -Tf /opt/aegis/current.next "$current"

AEGIS_IMAGE_TAG="$release_tag" docker compose --env-file .env.production -f compose.production.yml up --detach --no-deps --force-recreate app
wait_healthy compose.production.yml .env.production app
AEGIS_IMAGE_TAG="$release_tag" docker compose --env-file .env.showcase -f compose.showcase.yml up --detach --no-deps --force-recreate showcase
wait_healthy compose.showcase.yml .env.showcase showcase

[ "$(readlink -f "$current")" = "$release" ]
app_id="$(docker compose --env-file .env.production -f compose.production.yml ps --quiet app)"
showcase_id="$(docker compose --env-file .env.showcase -f compose.showcase.yml ps --quiet showcase)"
[ "$(docker inspect --format '{{.Config.Image}}' "$app_id")" = "aegis-mission-control:$release_tag" ]
[ "$(docker inspect --format '{{.Config.Image}}' "$showcase_id")" = "aegis-mission-control-showcase:$release_tag" ]
[ "$(docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$app_id")" = "$release_commit" ]
[ "$(docker inspect --format '{{index .Config.Labels "org.opencontainers.image.revision"}}' "$showcase_id")" = "$release_commit" ]
[ "$(docker compose --env-file .env.production -f compose.production.yml exec -T app cat /app/web/dist/aegis-build-profile.txt)" = operator ]
[ "$(docker compose --env-file .env.showcase -f compose.showcase.yml exec -T showcase cat /app/web/dist/aegis-build-profile.txt)" = showcase ]
[ -z "$(docker compose --env-file .env.showcase -f compose.showcase.yml exec -T showcase find /app/web/dist -name '*.map' -print -quit)" ]
docker compose --env-file .env.showcase -f compose.showcase.yml exec -T showcase sh -c "grep -R -F -q '/api/snapshot' /app/web/dist/assets/*.js"
if docker compose --env-file .env.showcase -f compose.showcase.yml exec -T showcase sh -c "grep -R -F -q -e '/api/v1/' -e '/api/runs' /app/web/dist/assets/*.js"; then
  fail "showcase bundle contains a private operator route"
fi

curl --fail --silent --header 'Host: mission.aihangout.ai' http://127.0.0.1:8780/api/ready >/dev/null
snapshot="$(docker compose --env-file .env.showcase -f compose.showcase.yml exec -T showcase python -c 'import urllib.request; print(urllib.request.urlopen("http://127.0.0.1:8080/api/snapshot", timeout=5).read().decode("utf-8"))')"
printf '%s' "$snapshot" | grep -F -q '"controlsEnabled":false'
printf '%s' "$snapshot" | grep -F -q '"dataClass":"redacted-manifests-and-synthetic-agent-feed"'
revision_after="$(docker compose --env-file .env.production -f compose.production.yml exec -T app alembic current 2>/dev/null | tail -n 1)"
revision_expected="$(docker compose --env-file .env.production -f compose.production.yml exec -T app alembic heads 2>/dev/null | tail -n 1)"
[ "$revision_after" = "$revision_expected" ] || fail "database did not reach the reviewed migration head"

switched=0
printf 'PRODUCTION_APP=HEALTHY\n'
printf 'EVIDENCE_SCANNER=HEALTHY\n'
printf 'PUBLIC_SHOWCASE=HEALTHY\n'
printf 'OPERATOR_PROFILE=PASS\n'
printf 'SHOWCASE_PROFILE=PASS\n'
printf 'SHOWCASE_SOURCE_MAPS=PASS\n'
printf 'SHOWCASE_PRIVATE_ROUTES=PASS\n'
printf 'SHOWCASE_DATA_BOUNDARY=PASS\n'
printf 'MIGRATION_BEFORE=%s\n' "$revision_before"
printf 'MIGRATION=%s\n' "$revision_after"
printf 'RELEASE=%s\n' "$release"
printf 'COMMIT=%s\n' "$release_commit"
