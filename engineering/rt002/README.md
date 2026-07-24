# RT-002 — Remote Live Integration Proof (Lane 5)

**Law:** PARALLELIZE IMPLEMENTATION — NEVER AUTHORITY  
**Production readiness:** NOT READY  
**Baseline main:** `219485d46d3ff2e66463f280c4fd10ddd8e78b57`

## Purpose

Prove **real** MongoDB replica-set transactions and **real** S3-compatible
object storage on GitHub Actions (or authorized Linux runners). Extends
RT-001; does not replace it. Does **not** modify or merge C-P-003 PR #7.

## Commands

```bash
# Local non-container / honesty unit tests
python3 -m pytest backend/tests/test_rt002_unit_honesty.py backend/tests/test_rt001_integration_environment.py -q

# Architecture / security / fast
./stratex verify --architecture
./stratex verify --security
./stratex verify --fast

# Complete remote live verification (GitHub Actions)
# Triggered by pull_request or workflow_dispatch on stratex-live-integration.yml

# Markers
python3 -m pytest -m live_mongo -q          # requires RT002_LIVE=1 + replica set
python3 -m pytest -m live_object_storage -q # requires RT002_LIVE=1 + MinIO
python3 -m pytest -m "live_mongo and cp003_claims" -q  # needs CP003 source fetch
```

## Immutable digests

See `IMAGE_DIGESTS.yaml`. Floating `:latest` is rejected for RT-002 acceptance.

## C-P-003 claim tests

PR #7 is fetched read-only in CI into a temporary worktree. RT-002 does not
commit C-P-003 business code onto this branch.

## Markers emitted by live tests

- `LIVE_MONGO_REPLICA_SET_PROOF`
- `LIVE_S3_COMPATIBLE_STORAGE_PROOF`

## Authority

Lane 5 owns runtime/quality only — no Passport/ATC/Estimator/Habitat business
approval authority.
