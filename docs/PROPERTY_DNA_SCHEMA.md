# PROPERTY DNA SCHEMA SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 011 · OPERATION PROPERTY DNA
**Status:** SCHEMA FINALIZED  
**Scope:** MongoDB Collections & JSON Schema definitions for the Property DNA Engine™.

---

## 1. Physical Data Model (MongoDB Architecture)

Property DNA is stored in a dedicated, read-optimized collection named `property_dna` inside the nextgen database. This collection is structured as an append-only, versioned document store. It coordinates with three primary collections:
1. `properties`: Holds basic physical attributes and geographical data.
2. `passports` and `passport_entries`: The absolute canonical evidence ledger.
3. `findings`: Holds verified, peer-reviewed building system observations.

### ERD Relations

```
 ┌──────────────────────┐             ┌──────────────────────┐
 │      properties      │             │     property_dna     │
 ├──────────────────────┤             ├──────────────────────┤
 │ canonical_id (PK)    ◄────────────►│ property_id (FK)     │
 │ tenant_id            │             │ canonical_id (PK)    │
 │ address              │             │ tenant_id            │
 └──────────────────────┘             │ version              │
                                      │ updated_at           │
                                      │ [Category Fields...] │
                                      └──────────┬───────────┘
                                                 │
                                                 │ (Refers to Source)
                                                 ▼
 ┌──────────────────────┐             ┌──────────────────────┐
 │   passport_entries   │             │       findings       │
 ├──────────────────────┤             ├──────────────────────┤
 │ canonical_id (PK)    │             │ canonical_id (PK)    │
 │ passport_id (FK)     │             │ property_id (FK)     │
 │ entry_type           │             │ status (="APPROVED") │
 │ payload              │             │ severity             │
 └──────────────────────┘             └──────────────────────┘
```

---

## 2. JSON Schema: Property DNA Document

All documents in the `property_dna` collection must validate against the following JSON Schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "PropertyDnaDocument",
  "type": "object",
  "required": [
    "canonical_id",
    "property_id",
    "tenant_id",
    "version",
    "created_at",
    "updated_at",
    "identity",
    "health",
    "awe",
    "risk",
    "lifecycle",
    "financial",
    "history"
  ],
  "properties": {
    "canonical_id": {
      "type": "string",
      "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
      "description": "ULID of the Property DNA record."
    },
    "property_id": {
      "type": "string",
      "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$",
      "description": "ULID pointing to the parent property record."
    },
    "tenant_id": {
      "type": "string",
      "description": "Scoping identifier for multi-tenancy."
    },
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Monotonically increasing version count of the DNA projection."
    },
    "created_at": {
      "type": "string",
      "format": "date-time"
    },
    "updated_at": {
      "type": "string",
      "format": "date-time"
    },
    "identity": {
      "type": "object",
      "required": ["property_name", "address", "build_year", "size", "construction_type", "climate_zone"],
      "properties": {
        "property_name": { "$ref": "#/$defs/dnaField" },
        "address": { "$ref": "#/$defs/dnaField" },
        "build_year": { "$ref": "#/$defs/dnaField" },
        "size": { "$ref": "#/$defs/dnaField" },
        "construction_type": { "$ref": "#/$defs/dnaField" },
        "climate_zone": { "$ref": "#/$defs/dnaField" }
      }
    },
    "health": {
      "type": "object",
      "required": ["overall_home_health", "structural", "roofing", "exterior", "moisture", "air", "energy", "safety", "site"],
      "properties": {
        "overall_home_health": { "$ref": "#/$defs/dnaField" },
        "structural": { "$ref": "#/$defs/dnaField" },
        "roofing": { "$ref": "#/$defs/dnaField" },
        "exterior": { "$ref": "#/$defs/dnaField" },
        "moisture": { "$ref": "#/$defs/dnaField" },
        "air": { "$ref": "#/$defs/dnaField" },
        "energy": { "$ref": "#/$defs/dnaField" },
        "safety": { "$ref": "#/$defs/dnaField" },
        "site": { "$ref": "#/$defs/dnaField" }
      }
    },
    "awe": {
      "type": "object",
      "required": ["air_index", "water_index", "energy_index", "overall_awe_index"],
      "properties": {
        "air_index": { "$ref": "#/$defs/dnaField" },
        "water_index": { "$ref": "#/$defs/dnaField" },
        "energy_index": { "$ref": "#/$defs/dnaField" },
        "overall_awe_index": { "$ref": "#/$defs/dnaField" }
      }
    },
    "risk": {
      "type": "object",
      "required": ["current_risk_level", "five_year_risk_projection", "deferred_maintenance_exposure", "weather_exposure", "moisture_exposure", "insurance_exposure"],
      "properties": {
        "current_risk_level": { "$ref": "#/$defs/dnaField" },
        "five_year_risk_projection": { "$ref": "#/$defs/dnaField" },
        "deferred_maintenance_exposure": { "$ref": "#/$defs/dnaField" },
        "weather_exposure": { "$ref": "#/$defs/dnaField" },
        "moisture_exposure": { "$ref": "#/$defs/dnaField" },
        "insurance_exposure": { "$ref": "#/$defs/dnaField" }
      }
    },
    "lifecycle": {
      "type": "object",
      "required": ["roof_age", "hvac_age", "windows", "exterior", "foundation", "solar", "major_components", "remaining_service_life"],
      "properties": {
        "roof_age": { "$ref": "#/$defs/dnaField" },
        "hvac_age": { "$ref": "#/$defs/dnaField" },
        "windows": { "$ref": "#/$defs/dnaField" },
        "exterior": { "$ref": "#/$defs/dnaField" },
        "foundation": { "$ref": "#/$defs/dnaField" },
        "solar": { "$ref": "#/$defs/dnaField" },
        "major_components": { "$ref": "#/$defs/dnaField" },
        "remaining_service_life": { "$ref": "#/$defs/dnaField" }
      }
    },
    "financial": {
      "type": "object",
      "required": ["estimated_deferred_maintenance", "estimated_annual_energy_waste", "completed_improvements", "future_investment_opportunities"],
      "properties": {
        "estimated_deferred_maintenance": { "$ref": "#/$defs/dnaField" },
        "estimated_annual_energy_waste": { "$ref": "#/$defs/dnaField" },
        "completed_improvements": { "$ref": "#/$defs/dnaField" },
        "future_investment_opportunities": { "$ref": "#/$defs/dnaField" }
      }
    },
    "history": {
      "type": "object",
      "required": ["inspection_count", "mission_count", "major_events", "timeline_summary", "verified_contractor_work", "warranty_status"],
      "properties": {
        "inspection_count": { "$ref": "#/$defs/dnaField" },
        "mission_count": { "$ref": "#/$defs/dnaField" },
        "major_events": { "$ref": "#/$defs/dnaField" },
        "timeline_summary": { "$ref": "#/$defs/dnaField" },
        "verified_contractor_work": { "$ref": "#/$defs/dnaField" },
        "warranty_status": { "$ref": "#/$defs/dnaField" }
      }
    }
  },
  "$defs": {
    "dnaField": {
      "type": "object",
      "required": ["current_value", "provenance", "history"],
      "properties": {
        "current_value": {
          "type": ["string", "number", "boolean", "null"],
          "description": "The active, peer-reviewed value for this property DNA node."
        },
        "provenance": {
          "type": "string",
          "enum": ["Verified", "Estimated", "Projected", "Unknown"],
          "description": "Mandatory level of evidence mapping."
        },
        "history": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["version", "value", "source_attribution", "approval_status", "confidence_score", "reviewer", "timestamp"],
            "properties": {
              "version": { "type": "integer" },
              "value": { "type": ["string", "number", "boolean", "null"] },
              "source_attribution": {
                "type": "string",
                "description": "ULID or ID of the canonical source evidence (PassportEntry ID, Finding ID, or Invoice ID)."
              },
              "approval_status": {
                "type": "string",
                "enum": ["APPROVED"]
              },
              "confidence_score": {
                "type": "number",
                "minimum": 0,
                "maximum": 100
              },
              "reviewer": {
                "type": "string",
                "description": "The user ID of the Admin, GM, or CEO who signed off on the finding."
              },
              "timestamp": {
                "type": "string",
                "format": "date-time"
              }
            }
          }
        }
      }
    }
  }
}
```

---

## 3. Database Indexes

To maintain absolute query speed under Rule #5 (Unified ecosystem consumption), read-optimized composite indexes are established on the MongoDB collection:

```javascript
// Index 1: Fast property lookup within tenant boundaries (Primary Query Path)
db.property_dna.createIndex(
  { "property_id": 1, "tenant_id": 1 },
  { unique: true, name: "idx_property_dna_lookup" }
);

// Index 2: Multi-tenant list and aggregate operations
db.property_dna.createIndex(
  { "tenant_id": 1, "updated_at": -1 },
  { name: "idx_tenant_dna_timeline" }
);

// Index 3: Cross-reference lookup to verify source linkages (Engineering Law verification)
db.property_dna.createIndex(
  { "identity.address.history.source_attribution": 1 },
  { name: "idx_dna_provenance_source_ref" }
);
```
