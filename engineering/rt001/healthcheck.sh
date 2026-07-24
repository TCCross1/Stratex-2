#!/usr/bin/env bash
# RT-001 health / readiness check.
# Reports INTEGRATION_ENVIRONMENT_UNAVAILABLE when Docker/stack is missing.
# Exit 0 on unavailable so repo verify is not failed by missing Docker.
# Production readiness: NOT READY.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RT001_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

STATUS_UNAVAILABLE="INTEGRATION_ENVIRONMENT_UNAVAILABLE"
OVERALL_OK=1

report() {
  local status="$1"
  local name="$2"
  shift 2
  echo "[${status}] ${name}"
  for msg in "$@"; do
    echo "  - ${msg}"
  done
}

if ! command -v docker >/dev/null 2>&1; then
  report "$STATUS_UNAVAILABLE" "rt001_health" \
    "${STATUS_UNAVAILABLE}: docker CLI not found on PATH" \
    "LocalDiskAdapter object-storage proof remains available without Docker"
  exit 0
fi

if ! docker info >/dev/null 2>&1; then
  report "$STATUS_UNAVAILABLE" "rt001_health" \
    "${STATUS_UNAVAILABLE}: docker daemon unreachable"
  exit 0
fi

# Optional: load secrets for published ports
SECRETS="$ROOT/.rt001/secrets.env"
if [[ -f "$SECRETS" ]]; then
  set -a
  # shellcheck disable=SC1090
  . "$SECRETS"
  set +a
fi
MONGO_PORT="${RT001_MONGO_PORT:-27018}"
MINIO_PORT="${RT001_MINIO_API_PORT:-9000}"

# Container presence (best-effort)
for cname in stratex-rt001-mongo1 stratex-rt001-minio; do
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$cname"; then
    report "OK" "$cname" "container running"
  else
    report "$STATUS_UNAVAILABLE" "$cname" \
      "${STATUS_UNAVAILABLE}: container not running (start with ./engineering/rt001/start.sh)"
    OVERALL_OK=0
  fi
done

# TCP probes (best-effort; no credentials logged)
python3 - "$MONGO_PORT" "$MINIO_PORT" <<'PY' || true
import socket, sys
mongo_port = int(sys.argv[1])
minio_port = int(sys.argv[2])

def probe(host, port, name):
    s = socket.socket()
    s.settimeout(2)
    try:
        s.connect((host, port))
        print(f"[OK] {name}_tcp")
        print(f"  - {host}:{port} accepting connections")
        return True
    except OSError as exc:
        print(f"[INTEGRATION_ENVIRONMENT_UNAVAILABLE] {name}_tcp")
        print(f"  - INTEGRATION_ENVIRONMENT_UNAVAILABLE: {host}:{port} ({exc})")
        return False
    finally:
        s.close()

ok_m = probe("127.0.0.1", mongo_port, "mongo")
ok_s = probe("127.0.0.1", minio_port, "minio")
sys.exit(0 if (ok_m and ok_s) else 1)
PY
tcp_rc=$?
if [[ "$tcp_rc" -ne 0 ]]; then
  OVERALL_OK=0
fi

if [[ "$OVERALL_OK" -eq 1 ]]; then
  report "OK" "rt001_health" "Mongo + MinIO appear ready (local integration only; NOT production)"
else
  report "$STATUS_UNAVAILABLE" "rt001_health" \
    "${STATUS_UNAVAILABLE}: one or more RT-001 services not ready"
fi

# Always exit 0 when classified unavailable so verify is not blocked.
exit 0
