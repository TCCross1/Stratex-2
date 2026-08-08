# Publishing sealed missions to Habitat

After Core seals a mission package into Passport, Habitat consumes a **versioned projection**.

## Contract

- **ID:** `habitat.projection.v1`
- **Habitat endpoint (read):** `GET /api/habitat/projection/contract` (schema sample)
- **Habitat dashboard:** `GET /api/habitat/dashboard/projection`
- **File handoff (field-test):** set `HABITAT_PROJECTION_PATH` to a `habitat.projection.v1.json` file; dashboard hydrates from disk (read-only)
- **Claim redeem (read-only stub):** `POST /api/habitat/v1/claim/redeem` — lookup only; does not mint codes or write Passport

## Minimum publish payload (Passport → Habitat)

```json
{
  "contract_id": "habitat.projection.v1",
  "contract_version": "1.0.0",
  "property_id": "<id>",
  "authoritative": true,
  "property_identity": { "address_line": "", "city_state_zip": "" },
  "scores": {
    "certified_score": 0,
    "score_scale": 1000,
    "awe_index": 0,
    "roof_condition": 0,
    "energy_score": 0,
    "moisture_score": 0
  },
  "home_health": {
    "overall": 0,
    "systems": {
      "structure": 0, "roofing": 0, "hvac": 0,
      "plumbing": 0, "electrical": 0, "exterior": 0
    }
  },
  "awe": { "index": 0, "hotspots": [], "brand": "AWE™" },
  "twin": {
    "mesh_ref": null,
    "layers": ["finish", "thermal", "moisture", "framing", "energy", "openings", "awe"],
    "plane_count": 0,
    "measurements": {}
  },
  "openings": [
    {
      "id": "win-1",
      "kind": "window",
      "label": "Front bedroom",
      "elevation": "front",
      "unit_w_in": 36,
      "unit_h_in": 48,
      "rough_w_in": 38,
      "rough_h_in": 50.5,
      "truth": "VERIFIED"
    }
  ],
  "timeline": [],
  "maintenance": { "next_12_months_usd": 0, "actions": [] },
  "truth_policy": "VERIFIED requires sealed evidence. ESTIMATED labeled. WITHHELD never shown.",
  "habitat_role": "read-only"
}
```

## Pipeline

```
Matrice 4E/4T capture
  → Core process / photogrammetry / thermal
  → Core analysis (AWE, openings, scores)
  → mission_package_seal (HMAC)
  → mission_to_passport (Passport single-writer)
  → projection publish (this contract)
  → Habitat dashboard + twin + openings + Exterior Studio (proposals only)
```

Habitat never writes Passport. Exterior Studio designs are non-canonical proposals.
