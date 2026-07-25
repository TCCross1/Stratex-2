# NODE SCHEMA SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** SCHEMA FINALIZED  
**Scope:** Unified MongoDB Node Collections and JSON Schemas for the Property Knowledge Graph.

---

## 1. Unified Node Architecture

Every entity in the Property Knowledge Graph is modeled as a document in the `graph_nodes` collection. To maintain absolute consistency while allowing rich domain-specific data, all nodes share a base schema layout consisting of standard identifiers, audit fields, taxonomy types, and confidence parameters.

### Physical Storage Collection
* **Collection Name:** `graph_nodes`
* **Primary Key:** `_id` (ULID string)
* **Indexes:**
  * `{ tenant_id: 1, node_type: 1 }`
  * `{ property_id: 1 }`
  * `{ "metadata.status": 1 }`

---

## 2. Base Node JSON Schema

Every node document in `graph_nodes` must validate against this base schema structure:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "BaseGraphNode",
  "type": "object",
  "required": ["_id", "tenant_id", "property_id", "node_type", "name", "confidence", "provenance", "created_at", "updated_at", "version"],
  "properties": {
    "_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$", "description": "Monotonically increasing ULID identifier." },
    "tenant_id": { "type": "string", "description": "Scoped tenant identifier." },
    "property_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$", "description": "Associated property identifier." },
    "node_type": { 
      "type": "string", 
      "enum": [
        "SYSTEM", "MATERIAL", "CONTRACTOR", "INSPECTION", "REPAIR", 
        "PROJECT", "PHOTO", "EVIDENCE", "WARRANTY", "DOCUMENT", 
        "TIMELINE_EVENT", "DESIGN_CONCEPT", "PROJECT_OPPORTUNITY"
      ] 
    },
    "name": { "type": "string", "description": "Human-readable label for the node." },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0, "description": "Calibrated confidence score." },
    "provenance": { 
      "type": "string", 
      "enum": ["VERIFIED", "ESTIMATED", "PROJECTED", "UNKNOWN"],
      "description": "Evidence categorization tier."
    },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "version": { "type": "integer", "minimum": 1 },
    "properties": { "type": "object", "description": "Domain-specific fields depending on node_type." }
  }
}
```

---

## 3. Concrete Node Taxonomy Properties

Below are the domain-specific properties defined inside the `properties` sub-object for each of the 13 taxonomy types.

### A. SYSTEM
Represents high-level physical building assemblies (e.g., Roof, HVAC, Foundation, Siding, Drainage).
```json
{
  "system_type": "ROOF",
  "installation_date": "2018-04-12T00:00:00Z",
  "last_inspected_at": "2026-05-10T14:30:00Z",
  "overall_health_score": 0.85,
  "estimated_replacement_date": "2048-04-12T00:00:00Z",
  "physical_dimensions": {
    "area_sqft": 2400.0,
    "slope_degrees": 22.5
  }
}
```

### B. MATERIAL
Represents structural components and substances used in building assemblies (e.g., Asphalt Shingle, Metal, Wood, PVC).
```json
{
  "material_category": "ARCHITECTURAL_SHINGLE",
  "manufacturer": "CertainTeed",
  "product_line": "Landmark Pro",
  "color": "Moire Black",
  "expected_lifespan_years": 30,
  "fire_rating_class": "CLASS_A",
  "wind_resistance_mph": 110
}
```

### C. CONTRACTOR
Represents the licensed company/operator executing construction, repair, or inspection work.
```json
{
  "contractor_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C",
  "company_name": "Apex Roofing Solutions",
  "license_number": "LIC-FL-893041-A",
  "insurance_general_liability_limit": 2000000.0,
  "work_territory_region": "SOUTH",
  "rating_score": 4.9,
  "status": "CERTIFIED"
}
```

### D. INSPECTION
Represents specific physical or aerial assessments conducted on the asset.
```json
{
  "mission_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9M",
  "operator_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9O",
  "inspection_method": "DRONE_AERIAL_SCAN",
  "conducted_at": "2026-05-10T14:30:00Z",
  "weather_conditions": {
    "wind_speed_knots": 8.4,
    "cloud_cover": "CLEAR"
  },
  "data_quality_score": 0.98
}
```

### E. REPAIR
Represents physical maintenance or damage remediation performed on a system.
```json
{
  "repair_type": "LEAK_PATCH_COMPLETED",
  "cost": 1250.0,
  "completed_at": "2026-06-12T18:00:00Z",
  "remediated_findings": ["01H2Z4J6KW9T5V2Y7X3V6M8B9F"],
  "materials_used": [
    { "name": "Underlayment Membrane", "quantity": 1.0, "unit": "roll" }
  ],
  "contractor_signoff_by": "Apex Roofing Solutions"
}
```

### F. PROJECT
Represents a multi-stage, coordinated scope of work containing multiple repairs or improvements.
```json
{
  "project_type": "FULL_ROOF_REPLACEMENT",
  "status": "IN_PROGRESS",
  "start_date": "2026-07-01T08:00:00Z",
  "target_completion_date": "2026-07-25T17:00:00Z",
  "budget": 18500.0,
  "actual_expenditure": 12000.0
}
```

### G. PHOTO
Represents high-resolution visual evidence captured via mobile devices, MDUs, or drones.
```json
{
  "photo_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9P",
  "storage_uri": "s3://stratex-evidence-vault/properties/01H2Z4/photos/photo_001.jpg",
  "mime_type": "image/jpeg",
  "dimensions": { "width": 4032, "height": 3024 },
  "exif_metadata": {
    "camera_model": "DJI Mavic 3 Enterprise",
    "gps_coordinates": { "lat": 27.9496, "lon": -82.4584 },
    "captured_at": "2026-05-10T14:35:12Z"
  }
}
```

### H. EVIDENCE
Represents highly granular, localized structural or radiometric findings (e.g., bounding box within a photo, thermal cold spot).
```json
{
  "evidence_type": "THERMAL_MOISTURE_PROXY",
  "parent_photo_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9P",
  "bounding_box": {
    "x_min": 120, "y_min": 450, "x_max": 280, "y_max": 610
  },
  "anomaly_area_sqft": 14.5,
  "temperature_differential_celsius": -4.2,
  "confidence_score": 0.94
}
```

### I. WARRANTY
Represents legal manufacturer or contractor guarantees protecting systems or materials.
```json
{
  "warranty_id": "W-1045",
  "issuer_type": "MANUFACTURER",
  "issuer_name": "CertainTeed",
  "coverage_months": 360,
  "start_date": "2018-04-12T00:00:00Z",
  "expiry_date": "2048-04-12T00:00:00Z",
  "transferable": true,
  "exclusions": ["Acts of God", "Negligent maintenance"]
}
```

### J. DOCUMENT
Represents official physical or digital certificates, engineering specifications, or claims files.
```json
{
  "document_type": "SIGNED_ROOFING_CONTRACT",
  "storage_uri": "s3://stratex-document-vault/properties/01H2Z4/contracts/contract_signed.pdf",
  "sha256_hash": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a1b2c3d4e5f6",
  "signed_at": "2026-06-28T10:15:00Z",
  "signatories": [
    { "name": "John Doe", "role": "HOMEOWNER" },
    { "name": "Apex Roofing", "role": "CONTRACTOR" }
  ]
}
```

### K. TIMELINE_EVENT
Represents localized exogenous events (e.g., Category 3 Storm, freeze event, structural inspections).
```json
{
  "event_type": "SEVERE_WEATHER_STORM",
  "event_name": "Hurricane Barry",
  "severity_level": "CATEGORY_2",
  "peak_wind_gust_mph": 105.0,
  "precipitation_inches": 6.8,
  "occurred_at": "2026-07-15T04:00:00Z",
  "geographical_bounds": {
    "center_lat": 27.9501,
    "center_lon": -82.4578,
    "radius_miles": 50.0
  }
}
```

### L. DESIGN_CONCEPT
Represents advanced structural engineering specs (e.g., Solar-Ready Roof, High-Wind Reinforcement Layout).
```json
{
  "concept_id": "DC-HIGH-WIND-88",
  "title": "High-Wind Perimeter Metal Edge Flash Specification",
  "designer_name": "Stratex Structural Design Labs",
  "applicable_wind_zone_mph": 150.0,
  "technical_schematic_uri": "s3://stratex-spec-vault/concepts/dc-high-wind-88.pdf",
  "requirements": [
    "Continuous cleat 22-gauge steel",
    "Fasteners spaced at 4 inches on center"
  ]
}
```

### M. PROJECT_OPPORTUNITY
Represents highly qualified leads generated by PKG inferences (e.g., Storm Damage + Expiring Warranty = Proactive Re-roof).
```json
{
  "opportunity_type": "PROACTIVE_ROOF_REPLACEMENT",
  "est_revenue": 19500.0,
  "qualification_reason": "Affected by Hurricane Barry with an existing asphalt architectural shingle nearing 18 years of age.",
  "generated_at": "2026-07-16T09:00:00Z",
  "status": "QUALIFIED_LEAD",
  "qualification_score": 0.92,
  "assigned_contractor_id": null
}
```
