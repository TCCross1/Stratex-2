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

# Preserve CI/caller-provided credentials before any file sourcing.
# RT-002 GitHub Actions exports ephemeral RT001_MINIO_* — those must win over
# a freshly generated .rt001/secrets.env so live object-storage tests authenticate.
_PRE_MINIO_USER="${RT001_MINIO_ROOT_USER:-}"
_PRE_MINIO_PASS="${RT001_MINIO_ROOT_PASSWORD:-}"
_PRE_MINIO_BUCKET="${RT001_MINIO_BUCKET:-}"
_PRE_MONGO_PORT="${RT001_MONGO_PORT:-}"

if [[ ! -f "$SECRETS" ]]; then
  if [[ -n "$_PRE_MINIO_USER" && -n "$_PRE_MINIO_PASS" ]]; then
    echo "Using caller-provided MinIO credentials (no secrets.env generate)"
  else
    echo "No .rt001/secrets.env — generating placeholders via generate_local_secrets.sh"
    "$RT001_DIR/generate_local_secrets.sh"
  fi
fi

# shellcheck disable=SC1090
set -a
# Prefer secrets; fall back to example placeholders for compose variable substitution.
[[ -f "$RT001_DIR/.env.example" ]] && . "$RT001_DIR/.env.example"
[[ -f "$SECRETS" ]] && . "$SECRETS"
set +a

# Caller/CI overrides always win (prevents credential mismatch with RT-002 tests).
[[ -n "$_PRE_MINIO_USER" ]] && export RT001_MINIO_ROOT_USER="$_PRE_MINIO_USER"
[[ -n "$_PRE_MINIO_PASS" ]] && export RT001_MINIO_ROOT_PASSWORD="$_PRE_MINIO_PASS"
[[ -n "$_PRE_MINIO_BUCKET" ]] && export RT001_MINIO_BUCKET="$_PRE_MINIO_BUCKET"
[[ -n "$_PRE_MONGO_PORT" ]] && export RT001_MONGO_PORT="$_PRE_MONGO_PORT"
export MINIO_ROOT_USER="${RT001_MINIO_ROOT_USER}"
export MINIO_ROOT_PASSWORD="${RT001_MINIO_ROOT_PASSWORD}"

echo "[OK] starting RT-001 stack (Mongo replica set + MinIO)"
"${COMPOSE[@]}" -f "$RT001_DIR/docker-compose.yml" --project-directory "$RT001_DIR" up -d
echo "[OK] RT-001 start requested. Run ./engineering/rt001/healthcheck.sh next."
exit 0
