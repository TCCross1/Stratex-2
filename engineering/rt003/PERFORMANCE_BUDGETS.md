# RT-003 Performance Budgets (CI-safe, synthetic)

**Production readiness:** NOT READY  
**Scope:** Bounded local synthetic workloads only — not production SLOs, not
live Mongo/MinIO soak tests, not customer traffic.

## Principles

1. **Hard ceilings** protect CI runners from runaway loops (iterations, wall time, ops/sec safety cap).
2. **Soft targets** (p95) are recorded as notes; they do not alone declare production READY.
3. **No network** in default harness — CPU/memory local only.
4. **No customer payloads** — synthetic markers only (`RT003_SYNTHETIC`).

## Default budgets

| Budget | Max iterations | Max wall ms | Ops/sec safety cap | Soft p95 target |
|--------|----------------|-------------|--------------------|-----------------|
| `json_hash_roundtrip` | 200 | 5000 | 50000 | 25 ms |
| `json_serialize_hash_microbench` | 100 | 3000 | 20000 | 40 ms |

`json_serialize_hash_microbench` is a tighter local serialize+SHA-256 microbenchmark
only. It does **not** measure end-to-end DLQ/audit scrub throughput or production
capacity.

Executable definitions: `engineering/rt003/load_harness.py` → `DEFAULT_BUDGETS`.

## CI usage

```bash
python3 -m pytest backend/tests/test_rt003_load_budgets.py -q
```

Exceeding hard ceilings (iterations, wall ms, errors) → test FAIL.
Soft notes: p95 target overrun and ops/sec above documented cap (cheap CPU ops
often exceed the cap; that alone is not a hard fail).

## Explicit non-claims

- These budgets do **not** prove production capacity.
- Passing synthetic load does **not** imply LIVE_MONGO / LIVE_S3 proof.
- Production readiness remains **NOT READY**.
