# Stratex Product Capability Map — Field Test Ready Path

**Branch:** field-test/ready-v1  
**Audience:** Contractors (Core) · Homeowners (Habitat)

---

## Core (Contractors / Operators)

| Capability | Status | Entry point |
|------------|--------|-------------|
| ATC readiness evaluation | Done | `POST /api/nextgen/atc/readiness` |
| Assemble mission package from capture media | Done | `POST /api/nextgen/missions/packages/assemble` |
| Seal Canonical Mission Package | Done | `POST /api/nextgen/missions/packages/seal` |
| Single-path field-test pipeline (4E or 4T) | Done | `POST /api/nextgen/field-test/pipeline/single` |
| Dual-path pipeline (4E + 4T pair gate) | Done | `POST /api/nextgen/field-test/pipeline/dual` |
| Compose Property Intelligence Report | Done | `POST /api/nextgen/reports/compose` |
| Governed publish → Passport | Existing | `governed_publish_service` |
| Mission lifecycle / stages | Existing | `/api/nextgen/missions`, workflow |
| Habitat magic link for homeowner | Existing | `/api/nextgen/v1/properties/{id}/habitat-link` |
| AWE composite | Existing | `/api/nextgen/v1/properties/{id}/awe` |

### Contractor report sections produced
01 Executive Summary · 02–09 Digital Twin / CAD layers · 10 System Health  
11–12 Schedules · 13–14 Energy / Ventilation · 15 Materials · 16 Labor  
17 Found Damages · 18 Maintenance Priority · Deliverables block

---

## Habitat (Homeowners)

| Capability | Status | Entry point |
|------------|--------|-------------|
| Read-only Passport projection | Existing | `PassportProjectionAdapter` |
| Digital twin summary (planes, measurements) | Done | `habitat_field_test_projection` |
| AWE anomaly list + severity counts | Done | same |
| Homeowner dashboard shaping | Done | `extract_homeowner_dashboard` |
| Token-gated property view | Existing | Core Habitat link routes |
| WITHHELD geometry never shown | Done | filter in projection consumer |

---

## Authority rules (always)

- One Passport writer (`passport_service.append_entry`)
- One governed publisher
- Habitat never writes canonical truth
- Low-confidence geometry → WITHHELD
- Truth classifications on scores and findings
- ATC produces candidates only — never self-approves geometry

---

## What still needs live environment / hardware

1. Mongo transactions + seal keys
2. Real Matrice 4E/4T media into evidence ingest
3. Photogrammetry / mesh pipeline for interactive 3D twin assets
4. Controlled dry-run on a real property
5. Atlas sign-off per Field Test Charter
