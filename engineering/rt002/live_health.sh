#!/usr/bin/env bash
# RT-002 live readiness summary — never prints secrets.
# Overall READY only when required live checks pass.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
export PYTHONPATH="${ROOT}/backend:${PYTHONPATH:-}"
cd "$ROOT"
python3 - <<'PY'
import os, sys
sys.path.insert(0, "engineering")
from rt002.readiness import ReadinessReport, OverallState, redact_url

report = ReadinessReport()
mongo = os.environ.get("RT002_MONGO_URL") or os.environ.get("MONGO_URL") or ""
minio = os.environ.get("RT002_MINIO_ENDPOINT") or os.environ.get("MINIO_ENDPOINT") or ""

# Do not print credential-bearing URLs.
print(f"mongo_url_redacted={redact_url(mongo) or 'unset'}")
print(f"minio_endpoint_redacted={redact_url(minio) or 'unset'}")

live = os.environ.get("RT002_LIVE", "").lower() in {"1", "true", "yes"}
if not live:
    report.set("mongo_reachable", False, "INTEGRATION_ENVIRONMENT_UNAVAILABLE: RT002_LIVE not set")
    report.compute_overall()
    print(f"overall={report.overall.value}")
    for k, v in report.components.items():
        print(f"  {k}: ok={v.ok} detail={v.detail}")
    sys.exit(0)

# Live path: defer detailed checks to pytest live suites; this script only
# reports env presence for operators.
report.set("mongo_reachable", bool(mongo), "present" if mongo else "INTEGRATION_ENVIRONMENT_UNAVAILABLE: MONGO_URL missing")
report.set("object_storage_reachable", bool(minio), "present" if minio else "INTEGRATION_ENVIRONMENT_UNAVAILABLE: MINIO endpoint missing")
# Remaining components must be proven by live tests before READY.
for name in (
    "replica_set_initialized",
    "writable_primary",
    "transaction_proof",
    "critical_passport_indexes",
    "bucket_operation",
    "checksum_proof",
):
    report.set(name, False, "PENDING_LIVE_TEST")
report.compute_overall()
print(f"overall={report.overall.value}")
for k, v in report.components.items():
    print(f"  {k}: ok={v.ok} detail={v.detail}")
if report.overall == OverallState.READY:
    print("ERROR: readiness script must not claim READY without live test proof", file=sys.stderr)
    sys.exit(2)
PY
