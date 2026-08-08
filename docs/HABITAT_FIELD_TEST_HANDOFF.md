# Habitat field test handoff (stratex-habitat team)

**From:** Stratex-2 Core (`field-test/ready-v1`)  
**To:** stratex-habitat (`field-test/ready-v1` expected)  
**Contract:** `habitat.projection.v1`  
**Authority:** Core seals → Passport stores official truth → Habitat **reads only**

This document describes what Core delivers today and what Habitat should implement next. **There is no Habitat code in the Stratex-2 repo.**

---

## Architecture (do not violate)

```
Matrice capture
  → Core (seal mission package)
  → Passport (single writer: governed publish + property/claim records)
  → habitat.projection.v1 (read model)
  → Habitat dashboard / twin view (consumer)
```

| Layer | May write Passport? | Role |
|-------|---------------------|------|
| **Core** | No (prepares handoff only) | Seal missions, export projections |
| **Passport** | Yes (sole canonical writer) | Ledger entries, property by address, claim codes |
| **Habitat** | **No** | Read projections; owner UX; claim redemption UI only |

Habitat must **never** call `append_entry`, `governed_publish`, or mutate mission seals / geometry truth.

---

## How to get `habitat.projection.v1.json` from Core

### Contract identity

- **`contract_id`:** `habitat.projection.v1`
- **`contract_version`:** `1.0.0`
- **Schema reference (Core):** `docs/HABITAT_PROJECTION_PUBLISH.md`, `backend/nextgen/habitat_projection_export.py`

### Option A — Lab export (fastest for integration dev)

From Stratex-2 repo root, after `pip install -r backend/requirements.txt`:

```bash
python3 -m backend.nextgen.export_sample_habitat_projection > habitat.projection.v1.json
```

Or save explicitly:

```bash
python3 -m backend.nextgen.export_sample_habitat_projection > /path/to/habitat.projection.v1.json
```

**What this does:** Builds the field-test sample mission, seals it, exports projection JSON to stdout.

**Caveats:**

- Uses **lab path** (calls `seal_package` directly — see `docs/FIELD_TEST_README.md`)
- Sets **`authoritative: false`** (no Passport publish)
- Sample `property_id` / address are demo values (see below)

### Option B — Official pipeline + export (field-test sign-off path)

1. Run pipeline (includes ATC pre-seal checklist):

   ```bash
   python3 -m backend.nextgen.field_test_governed_publish_demo --dry-run
   ```

   Confirms `publication_request` shape. For a real file, Core team would export after seal using `export_habitat_projection()` with the pipeline’s `sealed_package`.

2. After **live governed publish** to Passport (requires Mongo — see `docs/FIELD_TEST_GOVERNED_PUBLISH.md`), re-export with:

   ```python
   export_habitat_projection(sealed_pkg, passport_projection=..., authoritative=True)
   ```

   **Today:** live publish is **not verified** in all environments; most handoff files will have `authoritative: false`.

### Option C — Core delivers artifact (recommended for Habitat CI)

Core field test can commit or attach:

- `habitat.projection.v1.json` (sample export)
- Optional: `artifacts/passport_property_registry.json` if `STRATEX_PASSPORT_PROPERTY_REGISTRY_PATH` was set during claim-code demo

Habitat CI should **fetch or copy** this JSON — not regenerate seals inside Habitat.

### Sample file shape (abbreviated)

See full example in `docs/HABITAT_PROJECTION_PUBLISH.md`. Key top-level fields:

```json
{
  "contract_id": "habitat.projection.v1",
  "contract_version": "1.0.0",
  "property_id": "prop-1234-infinity-orlando",
  "mission_id": "MISSION-2026-0801-FT-001",
  "authoritative": false,
  "property_identity": {
    "address_line": "1234 APPALACHIAN WAY",
    "city_state_zip": "LONDON, KY 40741",
    "geo": null
  },
  "scores": { "...": "..." },
  "home_health": { "...": "..." },
  "awe": { "index": 82, "hotspots": [], "brand": "AWE™" },
  "twin": { "mesh_ref": null, "plane_count": 4, "withheld_plane_count": 1, "measurements": {} },
  "openings": [],
  "habitat_role": "read-only"
}
```

**Note:** `twin.mesh_ref` is **`null`** in field test — no mesh pipeline in Core today.

---

## `authoritative`: `true` vs `false`

| Value | Meaning for Habitat |
|-------|---------------------|
| **`false`** | Preview / lab / pre-Passport export. Scores and openings may include **defaults or ESTIMATED** labels. Show **“Preview — not official”** (or equivalent). Do not present as certified homeowner truth. |
| **`true`** | Passport has accepted the mission evidence publish. Safe to treat as **official read model** for dashboard hydration (still label per-field `truth` on findings/openings). |

**Rules:**

- Core export CLI defaults to **`authoritative: false`**
- Habitat must **not** set `authoritative: true` locally
- Only Core/Passport publish path + explicit export with `authoritative=True` after commit

When `authoritative: false`, honor `truth_policy` and per-item `truth` fields (`ESTIMATED`, `VERIFIED`, etc.).

---

## Identity: `property_id`, `mission_id`, address

### `property_id`

- Stable Stratex property key (tenant-scoped in Core)
- Links Passport ledger, projection, and claim registry
- Example (sample): `prop-1234-infinity-orlando`
- **Habitat primary key** for dashboard session after claim or contractor grant

### `mission_id`

- Identifies the **capture mission** that produced the sealed package
- Example (sample): `MISSION-2026-0801-FT-001`
- Use for timeline, audit, “which flight” — not a substitute for `property_id`

### Address identity (Passport property record)

Core normalizes address for claim lookup (`backend/nextgen/address_normalize.py`):

- Input: `address_line` + `city_state_zip`
- Normalized display: uppercase, collapsed whitespace, e.g. `1234 APPALACHIAN WAY, LONDON, KY 40741`
- Hash: first 24 hex chars of SHA-256 of normalized display (`normalized_address_hash`)
- Passport property records are keyed by **`tenant_id` + normalized_address_hash**

Projection carries display address under `property_identity` (may differ in casing from normalized form).

**Habitat should:**

- Display `property_identity.address_line` + `city_state_zip` to the homeowner
- Store / query by `property_id` after claim
- Use normalized address only when calling Core/Passport lookup APIs (when exposed)

---

## Claim codes

### Format

- **`STRX-XXXX-XXXX`**
- Characters: `A–Z` and `2–9` (no `0`, `1`, `I`, `O` ambiguity)
- Example: `STRX-SC7R-EY74`
- Minted by Core **`passport_property_registry`** when a mission is sealed and **no Habitat owner** exists for that address

### Status values (field test registry)

- `pending_redemption` — code active, not yet claimed
- `redeemed` — owner linked (field test simulation)

### Redemption authority (critical)

**Habitat redeem must only READ Passport — no official writes from Habitat.**

Habitat may call Core/Passport **read APIs** (lookup by `claim_code`, fetch `property_id`, load projection). Any change to Passport truth — marking a code redeemed, linking `habitat_owner_user_id`, appending ledger entries — is performed **only** by Core/Passport writer paths. Habitat never opens Passport collections or calls `append_entry` / `governed_publish`.

Correct pattern:

```
Homeowner enters claim_code in Habitat UI
  → Habitat POST /api/habitat/v1/claim/redeem (Habitat-owned endpoint)
  → Habitat calls Core/Passport READ lookup (claim_code → property_id)
  → Core/Passport writer path records owner link + marks code redeemed
  → Habitat receives property_id + loads habitat.projection.v1 (read)
  → Habitat stores local session/grant mapping user ↔ property_id (Habitat DB only)
```

**Habitat must NOT:**

- Mint claim codes
- Write `nextgen_passport_entries` or mission seals
- Set `authoritative: true` on projections
- Call governed publish or append_entry

Field-test stub on Core (for tests/demos only):

- `get_property_by_claim_code(claim_code)` → property record
- Owner link is written by **Passport writer path on Core**, not Habitat

See `docs/HABITAT_CLAIM_CODE_REDEEM.md` for full redemption design.

---

## Minimal endpoints / fields Habitat should implement next

Implement in **stratex-habitat** (suggested — align with your repo conventions):

### 1) Read projection (required)

```
GET /api/habitat/v1/properties/{property_id}/projection
```

**Response:** `habitat.projection.v1` document (or wrapped `{ "projection": { ... } }`).

**Behavior:**

- Read-only
- If `authoritative: false`, include banner flag for UI
- Validate `contract_id` / `contract_version` before hydrate

**Fields to hydrate first (MVP dashboard):**

| Section | Fields |
|---------|--------|
| Header | `property_identity`, `property_id`, `authoritative` |
| Scores | `scores.certified_score`, `scores.awe_index`, `scores.roof_condition` |
| AWE | `awe.index`, `awe.hotspots[]` (`id`, `title`, `severity`, `truth`) |
| Twin summary | `twin.plane_count`, `twin.withheld_plane_count`, `twin.measurements` |
| Openings | `openings[]` (`kind`, `label`, `elevation`, `truth`) |
| Maintenance | `maintenance.actions[]` (optional MVP) |

Skip or stub until authoritative: `timeline`, full `home_health.systems` drill-down, 3D mesh (`mesh_ref` is null).

### 2) Claim redeem (required for homeowner onboarding)

```
POST /api/habitat/v1/claim/redeem
Body: { "claim_code": "STRX-...." }
```

**Habitat responsibility:**

- Authenticate homeowner session
- Call **Core/Passport read/lookup** (future HTTP API) — not local guesswork
- On success: bind `habitat_owner_user_id` ↔ `property_id` in **Habitat DB only**
- Redirect to dashboard; fetch projection by `property_id`

**Core/Passport responsibility (writer):**

- Validate code, mark redeemed, return `property_id` + normalized address

**Do not** implement redeem by writing to Passport collections from Habitat.

### 3) Contract sample (recommended for frontend)

```
GET /api/habitat/v1/projection/contract
```

Returns JSON Schema or sample `habitat.projection.v1` for client code generation (matches Core doc reference).

### 4) Dashboard entry (existing pattern)

If you already have magic-link grants (`GET /v1/habitat/{token}` in Core NextGen), field test may use **claim code** instead for first homeowner link. Do not merge the two flows without explicit product decision.

---

## What Core provides vs what Habitat builds

| Item | Owner |
|------|--------|
| Seal mission package | Core |
| Governed Passport publish | Passport (via Core API) |
| Claim code minting | Passport registry (Core module today) |
| `habitat.projection.v1` export | Core |
| Dashboard UI | Habitat |
| Claim redeem UI | Habitat |
| Owner session ↔ property_id | Habitat (local) |
| 3D mesh / Exterior Studio proposals | Habitat (non-canonical proposals only) |

---

## Field test readiness (honest)

From Core’s perspective (`docs/FIELD_TEST_GO_NO_GO.md`):

- Sample projection JSON: **available**
- Authoritative projection after live publish: **not proven in all envs**
- Claim lookup API over HTTP: **not exposed yet** (in-process registry + tests only)
- Mesh: **null**

Habitat can start integration against **sample `habitat.projection.v1.json`** with `authoritative: false` immediately. Production homeowner flows should wait for Core expose of claim lookup + live Passport publish.

---

## Core contacts / docs index

| Doc | Purpose |
|-----|---------|
| `docs/HABITAT_PROJECTION_PUBLISH.md` | Contract payload |
| `docs/HABITAT_CLAIM_CODE_REDEEM.md` | Claim code redemption |
| `docs/FIELD_TEST_README.md` | Official path vs lab CLI |
| `docs/FIELD_TEST_GO_NO_GO.md` | Software readiness verdict |
| `docs/FIELD_TEST_GOVERNED_PUBLISH.md` | Publish after seal |

**Core modules (reference only):**

- `backend/nextgen/habitat_projection_export.py`
- `backend/nextgen/export_sample_habitat_projection.py`
- `backend/nextgen/passport_property_registry.py`
- `backend/nextgen/address_normalize.py`
