# Stratex Field-Test Readiness (Habitat + Passport + Core)

**Branch:** `field-test/ready-v1` (Habitat)  
**Date:** 2026-08-01  

## Product split

| Product | Client | Role in field test |
|---------|--------|-------------------|
| **Core** | Contractors / operators | Capture (Matrice 4E/4T), processing, analysis, reports, seal to Passport |
| **Passport** | System of record | Single-writer hash-chain ledger; only source of canonical truth |
| **Habitat** | Homeowners | Read-only projections: dashboard, twin layers, AWE, openings, Exterior Studio proposals |

## Habitat field-test surface (ready to exercise)

1. **Dashboard** `/dashboard` — Property Passport card, health, AWE, financial, openings + rough openings, layer chips  
2. **Digital Twin / Property DNA** `/twin` — existing twin experience  
3. **Exterior Studio** `/exterior-studio` — add structure → side → outline → foundation metrics → roof evaluate (proposal only)  
4. **APIs**  
   - `GET /api/habitat/dashboard/projection` (JSON; prefers `HABITAT_PROJECTION_PATH`)  
   - `GET /api/habitat/openings`  
   - `GET /api/habitat/twin/layers` · `/twin/awe-hotspots`  
   - `POST /api/habitat/v1/claim/redeem` (read-only lookup stub; never mints codes)  
   - `GET /api/habitat/exterior-studio/entry`  
   - `POST /api/habitat/exterior-studio/outline/metrics`  
   - `POST /api/habitat/exterior-studio/roof/evaluate`  

## Point Habitat at Core / Passport JSON (file handoff)

After Core seals and Passport publishes a `habitat.projection.v1` export:

```bash
export HABITAT_PROJECTION_PATH=/absolute/path/to/habitat.projection.v1.json
# Sample (preview, authoritative:false):
#   backend/fixtures/habitat.projection.v1.sample.json
```

Dashboard + openings hydrate from that file. Set `"authoritative": true` only after governed Passport publish — UI shows **Official** vs **Preview**. Habitat remains read-only (no ledger writes, no claim minting, no Core publish).

## Waiting on field data (not blocked for UI/workflow dry-run)

- DJI Matrice 4E daytime + 4T nighttime mission packages on real properties  
- Core photogrammetry / thermal pipeline completion  
- Passport seal of mission package (VERIFIED geometry + findings)  
- Projection publish → Habitat adapter elevates `authoritative` when production mode + live endpoint

## Dry-run path (no drones yet)

1. Run Habitat backend + frontend on `field-test/ready-v1`  
2. Login as homeowner → land on `/dashboard` (demo projection)  
3. Inspect openings + rough openings  
4. Open `/exterior-studio` → Load demo outline → Calculate metrics → Evaluate roof  
5. Confirm Studio does not claim to write Passport  

## Authority rules (do not break)

- Habitat never writes Passport  
- Exterior Studio proposals are non-canonical  
- Landing twin layers (finish / thermal / framing) are Passport projections  
- Truth labels required on scores and findings  

## Core handoff (contractor product)

When Core seals a mission:

```
Core capture → process → analyze → report → SEAL → Passport
Passport projection → Habitat dashboard / twin / openings
```

Habitat field UI is built to consume that projection shape now.
