#!/usr/bin/env bash
# RT-001: one-command shutdown for the integration stack.
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
  echo "RT-001 stop skipped — nothing to tear down via Docker."
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  echo "[${STATUS_UNAVAILABLE}] docker"
  echo "  - ${STATUS_UNAVAILABLE}: docker daemon unreachable"
  echo "RT-001 stop skipped — integration environment not available."
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

echo "[OK] stopping RT-001 stack"
"${COMPOSE[@]}" -f "$RT001_DIR/docker-compose.yml" --project-directory "$RT001_DIR" down
echo "[OK] RT-001 stop complete."
exit 0
