#!/usr/bin/env bash
# RT-001: one-command start for Mongo replica set + MinIO.
# When Docker is unavailable, reports INTEGRATION_ENVIRONMENT_UNAVAILABLE
# and exits 0 so repo verify is not failed by missing Docker.
# Production readiness: NOT READY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RT001_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

STATUS_UNAVAILABLE="INTEGRATION_ENVIRONMENT_UNAVAILABLE"

if ! command -v docker >/dev/null 2>&1; then
  echo "[${STATUS_UNAVAILABLE}] docker"
  echo "  - ${STATUS_UNAVAILABLE}: docker CLI not found on PATH"
  echo "RT-001 start skipped — integration environment not available."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "[${STATUS_UNAVAILABLE}] docker"
  echo "  - ${STATUS_UNAVAILABLE}: docker daemon unreachable"
  echo "RT-001 start skipped — integration environment not available."
  exit 0
fi

COMPOSE=(docker compose)
if ! docker compose version >/dev/null 2>&1; then
  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
  else
    echo "[${STATUS_UNAVAILABLE}] docker-compose"
    echo "  - ${STATUS_UNAVAILABLE}: neither 'docker compose' nor docker-compose found"
    exit 0
  fi
fi

mkdir -p "$ROOT/.rt001"
SECRETS="$ROOT/.rt001/secrets.env"
if [[ ! -f "$SECRETS" ]]; then
  echo "No .rt001/secrets.env — generating placeholders via generate_local_secrets.sh"
  "$RT001_DIR/generate_local_secrets.sh"
fi

# shellcheck disable=SC1090
set -a
# Prefer secrets; fall back to example placeholders for compose variable substitution.
[[ -f "$RT001_DIR/.env.example" ]] && . "$RT001_DIR/.env.example"
[[ -f "$SECRETS" ]] && . "$SECRETS"
set +a

echo "[OK] starting RT-001 stack (Mongo replica set + MinIO)"
"${COMPOSE[@]}" -f "$RT001_DIR/docker-compose.yml" --project-directory "$RT001_DIR" up -d
echo "[OK] RT-001 start requested. Run ./engineering/rt001/healthcheck.sh next."
exit 0
