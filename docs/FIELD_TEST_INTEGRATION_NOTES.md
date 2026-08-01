# Field Test Integration Notes

**Branch:** field-test/ready-v1  
**Date:** 2026-08-01

## How to mount the new seal endpoint

In the main FastAPI application (typically `backend/server.py` or the nextgen router aggregator), add:

```python
from backend.nextgen.routes.mission_package_routes import router as mission_package_router

app.include_router(mission_package_router)
```

## Recommended test command (once environment is available)

```bash
cd backend
python -m pytest tests/test_mission_package_seal.py tests/test_mission_to_passport.py -q
```

## Current spine

1. Client or ATC assembles evidence
2. `POST /api/nextgen/missions/packages/seal` → seals + prepares publication request
3. Call existing `governed_publish` with the returned `publication_request`
4. Passport receives the entry via the single writer
5. `report_composer.compose_full_report()` produces the structured report
6. Habitat consumes the resulting projection

## Still required before live field test

- Wire the seal route into the running application
- Connect real Matrice 4E / 4T evidence ingest to package assembly
- Confirm transaction-capable Mongo + seal keys in the target environment
- Run the full seal → publish → project → report path on a controlled property
- Atlas sign-off per Field Test Charter
