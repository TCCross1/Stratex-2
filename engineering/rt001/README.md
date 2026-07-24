# RT-001 Integration Environment (Lane 5 Runtime / QE)

**Mission:** Reproducible local integration scaffolding for transaction-capable
Mongo (replica set) and object storage (MinIO or LocalDiskAdapter).

**Production readiness:** NOT READY — scaffolding and honesty probes only.
No production deployment claims.

**Base SHA:** `0c09b0cf44fb133852ddbb9ce96cea2e137ade6d`

## Quick start

```bash
# Generate local secrets (gitignored under .rt001/)
./engineering/rt001/generate_local_secrets.sh

# Start Mongo replica set + MinIO (requires Docker)
./engineering/rt001/start.sh

# Health / readiness
./engineering/rt001/healthcheck.sh

# Probes
python3 engineering/rt001/mongo_txn_probe.py
python3 engineering/rt001/object_storage_proof.py

# Shutdown
./engineering/rt001/stop.sh
```

## Docker unavailable

If Docker is not installed or the daemon is unreachable, scripts print
`INTEGRATION_ENVIRONMENT_UNAVAILABLE` and exit `0` so repository verify gates
(`./stratex verify --architecture` / `--security` / `--fast`) are not failed
by missing local Docker. Integration proof remains honest — unavailable, not passed.

## Layout

| Path | Purpose |
|------|---------|
| `docker-compose.yml` | Mongo single-node replica set + MinIO |
| `.env.example` | Safe placeholders only |
| `generate_local_secrets.sh` | Writes `.rt001/secrets.env` (gitignored) |
| `start.sh` / `stop.sh` | One-command lifecycle |
| `healthcheck.sh` | Readiness summary |
| `mongo_txn_probe.py` | Transaction capability probe |
| `object_storage_proof.py` | Upload/download/checksum proof |
| `_common.py` | Shared status helpers |

Runtime artifacts live under repo-root `.rt001/` (gitignored).
