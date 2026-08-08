# Habitat claim code redemption (field test v1)

**Branch:** `field-test/ready-v1`  
**Architecture:** Core seals → Passport stores property + claim → Habitat reads official data (read-only until owner redeems)

## What Core does today

After a mission package is sealed, Core registers (or updates) a **Passport property record** keyed by **normalized address**:

- Normalization: uppercase, collapsed whitespace, hash of `"LINE1, CITY STATE ZIP"`
- Module: `backend/nextgen/passport_property_registry.py`
- If **no Habitat owner** is linked for that address, Passport mints a one-time **`claim_code`** (format `STRX-XXXX-XXXX`)
- If an owner already exists, **no new claim code** is created

This is separate from `governed_publish` / `append_entry` — it is the field-test minimum for address-keyed property identity + owner onboarding.

## Demo (Core)

```bash
python3 -m backend.nextgen.field_test_claim_code_demo
```

Or the existing sample seal demo (now includes address + claim_code):

```bash
python3 -m backend.nextgen.sample_field_test_package
```

Example output fields:

```json
{
  "normalized_address": "1234 APPALACHIAN WAY, LONDON, KY 40741",
  "claim_code": "STRX-AB12-CD34",
  "habitat_owner_exists": false
}
```

Optional persistence for demos:

```bash
export STRATEX_PASSPORT_PROPERTY_REGISTRY_PATH=artifacts/passport_property_registry.json
```

## How Habitat redeems later (no full rewrite)

Habitat stays **read-only** for canonical Passport truth. Redemption is a **one-time link** step that binds a homeowner account to the Passport property record.

### Proposed flow (stratex-habitat, future endpoint)

```
Homeowner enters claim_code in Habitat UI
  → POST /api/habitat/v1/claim/redeem  { "claim_code": "STRX-...." }
  → Habitat validates code against Passport registry (read API or shared store)
  → On success: set habitat_owner_user_id on property record (Passport writer path)
  → Habitat loads habitat.projection.v1 for property_id (read-only dashboard)
  → claim_code_status → redeemed; code cannot be reused
```

### Habitat responsibilities (consumer only)

1. **Collect** claim code from homeowner (QR, email, contractor handoff)
2. **Call** Passport/Core redeem API (or read registry in field-test shared JSON)
3. **Attach** authenticated Habitat user as owner
4. **Hydrate** dashboard from `habitat.projection.v1` — scores, AWE, twin summary, openings

### Habitat must NOT

- Write mission seals or geometry truth
- Mint claim codes (Core/Passport only)
- Mark projections `authoritative: true` without Passport publish

### Field-test stub lookup (today)

Core exposes in-process helpers for tests and demos:

- `get_property_by_claim_code(claim_code)` → property record + `property_id`
- `link_habitat_owner(...)` → simulates successful redemption in unit tests

When Habitat integrates, replace the in-process store with a Passport read API backed by Mongo (`nextgen_passport_property_records` collection in production).

## Invariants preserved

| Layer | Role |
|-------|------|
| **Core** | Capture, process, seal missions |
| **Passport** | Official property record by normalized address; claim codes |
| **Habitat** | Read projections; redeem claim to become owner viewer |

## Related modules

- `backend/nextgen/address_normalize.py`
- `backend/nextgen/passport_property_registry.py`
- `backend/nextgen/field_test_claim_code_demo.py`
- `backend/tests/test_passport_property_registry.py`
