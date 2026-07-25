# EXPLAINABILITY API SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** SPEC COMPLETE · IMPLEMENTATION READY  
**Scope:** RESTful surface, request/response payloads, and error schemas for the Explainer Engine.

---

## 1. Overview & Authentication

The Explainer Engine exposes a high-performance REST API under the `/nextgen/v1` namespace. This API is consumed by the Habitat front-end, Reports generation services, Centcom operational maps, and downstream AI agents.

### Base URL
*   Internal/External Gateway: `https://api.stratex.com/api/nextgen/v1`
*   Development: `http://localhost:8000/api/nextgen/v1`

### Authentication & Authorization
All endpoints are secured and require standard nextgen headers:
*   `Authorization: ******
*   `X-Tenant-ID: <TENANT_ID>`

Explanations are filtered according to user roles. For instance, Homeowners calling the API will only receive `level_1` explanations, whereas Contractors or Engineers can query `level_2` and `level_3` fields.

---

## 2. API Endpoints Surface

| Method | Path | Description | Access Role |
| :--- | :--- | :--- | :--- |
| **GET** | `/explanations` | Query, filter, and paginate through historical explanation records. | Homeowner, Contractor, Engineer, Auditor |
| **GET** | `/explanations/{id}` | Retrieve a specific explanation by its unique ID. | Homeowner, Contractor, Engineer, Auditor |
| **GET** | `/property/{id}/explain` | Generate or retrieve explanations for all systems of a specific property. | Homeowner, Contractor, Engineer, Auditor |
| **POST** | `/explain/query` | Execute semantic, multi-system, or cross-property queries for explanations. | Contractor, Engineer, Auditor |

---

## 3. Detailed Endpoint Specs & Payloads

---

### A. GET /explanations
Retrieve a paginated, filtered list of historical explanation records.

#### Query Parameters
*   `limit` (integer, optional): Maximum records to return (Default: `20`, Max: `100`).
*   `offset` (integer, optional): Pagination offset (Default: `0`).
*   `system_category` (string, optional): Filter by building system (e.g., `ROOF`, `FOUNDATION`, `HVAC`).
*   `min_confidence` (number, optional): Filter by minimum confidence score (e.g., `85.0`).
*   `property_id` (string, optional): Filter by a specific property.

#### Success Response: `HTTP 200 OK`
```json
{
  "total_records": 1,
  "limit": 20,
  "offset": 0,
  "results": [
    {
      "explanation_id": "expl_9a2b8c7d6e4f3a21",
      "property_id": "prop_8820c78a11b942fe",
      "system_category": "WATER_INTRUSION",
      "overall_confidence_score": 92.5,
      "created_at": "2026-07-21T10:30:00Z",
      "updated_at": "2026-07-21T10:30:00Z"
    }
  ]
}
```

---

### B. GET /explanations/{id}
Retrieve a specific, complete explanation by its unique ID.

#### Path Parameters
*   `id` (string, required): The unique identifier of the explanation (e.g., `expl_9a2b8c7d6e4f3a21`).

#### Query Parameters
*   `level` (integer, optional): Restrict the payload output to a specific level (`1`, `2`, `3`, or `4`). If omitted, all levels the user has access to are returned.

#### Success Response: `HTTP 200 OK`
```json
{
  "explanation_id": "expl_9a2b8c7d6e4f3a21",
  "property_id": "prop_8820c78a11b942fe",
  "tenant_id": "tenant_stratex_residential",
  "dna_version_referenced": 14,
  "system_category": "WATER_INTRUSION",
  "created_at": "2026-07-21T10:30:00Z",
  "updated_at": "2026-07-21T10:30:00Z",
  "overall_confidence_score": 92.5,
  "levels": {
    "level_1": {
      "conclusion": "An active minor water leak has been identified in the attic space directly beneath the roof valleys.",
      "supporting_evidence": [
        "A moisture sensor reading in the attic rafters recorded 24% relative dampness on 2026-07-21.",
        "High-resolution photos from the roof inspection show separated flashing in the north valley."
      ],
      "confidence_explanation": "Our confidence is High (92.5%) because the issue was detected by a calibrated sensor and verified with aerial drone photography taken today.",
      "why_this_matters": "Unaddressed water leaks lead to wood rot in rafters, damaged drywall, and toxic mold growth, which will significantly lower home value and increase repair costs.",
      "recommended_next_steps": [
        "Cover the roof valley area with a temporary tarp to prevent further moisture ingress.",
        "Contact a roofing contractor to repair the valley flashing."
      ],
      "related_systems": [
        "Roof valley flashing",
        "Attic insulation",
        "Living room ceiling drywall"
      ],
      "assumptions": [
        "The leak was caused during the recent high-wind storm on 2026-07-19.",
        "Attic insulation in the path has absorbed some moisture and will require drying."
      ],
      "unknowns": [
        "The exact extent of water absorption in the hidden parts of the drywall ceiling is currently unverified."
      ]
    }
  },
  "evidence_trace": {
    "origin_mission_ids": ["msn_9022_roof_thermal_flyover"],
    "evidence_ids": ["ev_file_9918a2d1e2e3", "ev_sensor_damp_sens_44"],
    "passport_entry_ids": ["pass_entry_00994f2b"],
    "dna_nodes_referenced": ["health.moisture.current_value"],
    "knowledge_graph_paths": [
      "ROOF_VALLEY --[DRAINS_TO]--> ATTIC_RAFTERS"
    ],
    "applicable_standards": [
      "International Residential Code (IRC) 2021 Section R905.2.8.2"
    ]
  }
}
```

---

### C. GET /property/{id}/explain
Generate or retrieve the latest compiled explanations for all systems of a specific property. This acts as the high-density explanation feed for the Habitat Homeowner dashboard.

#### Path Parameters
*   `id` (string, required): The target property ID (e.g., `prop_8820c78a11b942fe`).

#### Query Parameters
*   `bypass_cache` (boolean, optional): If set to `true`, forces the Explainer Pipeline to re-traverse the Knowledge Graph and re-compile the reasoning text, updating the database record. (Default: `false`).

#### Success Response: `HTTP 200 OK`
```json
{
  "property_id": "prop_8820c78a11b942fe",
  "dna_version_referenced": 14,
  "compiled_at": "2026-07-21T10:35:00Z",
  "explanations": {
    "ROOF": {
      "explanation_id": "expl_roof_1122",
      "overall_confidence_score": 95.0,
      "conclusion": "Your roof shingles are in excellent condition with no functional damage.",
      "why_this_matters": "A well-maintained roof prevents all water leaks and maintains home thermal insulation efficiency."
    },
    "WATER_INTRUSION": {
      "explanation_id": "expl_9a2b8c7d6e4f3a21",
      "overall_confidence_score": 92.5,
      "conclusion": "An active minor water leak has been identified in the attic space directly beneath the roof valleys.",
      "why_this_matters": "Unaddressed water leaks lead to wood rot in rafters, damaged drywall, and toxic mold growth."
    }
  }
}
```

---

### D. POST /explain/query
Execute a cross-property or multi-category query using structured parameters. Useful for insurance carriers assessing overall risk exposure or contractors identifying portfolio opportunities.

#### Request Headers
*   `Content-Type: application/json`

#### Request Body Schema
```json
{
  "property_ids": ["prop_8820c78a11b942fe", "prop_9918a2d1e2e3"],
  "categories": ["ROOF", "WATER_INTRUSION"],
  "filters": {
    "confidence_range": {
      "min": 80.0,
      "max": 100.0
    },
    "severity_level": "MODERATE",
    "search_keyword": "leak"
  }
}
```

#### Success Response: `HTTP 200 OK`
```json
{
  "query_timestamp": "2026-07-21T10:40:00Z",
  "match_count": 1,
  "results": [
    {
      "property_id": "prop_8820c78a11b942fe",
      "explanation_id": "expl_9a2b8c7d6e4f3a21",
      "system_category": "WATER_INTRUSION",
      "overall_confidence_score": 92.5,
      "preview": {
        "conclusion": "An active minor water leak has been identified in the attic space directly beneath the roof valleys.",
        "severity": "MODERATE",
        "why_this_matters": "Unaddressed water leaks lead to wood rot in rafters, damaged drywall, and toxic mold growth."
      }
    }
  ]
}
```

---

## 4. Error Schemas & Status Codes

All errors returned by the Explainer API are formatted according to the standard Stratex-2 API error collection schema, containing a clear traceback context.

### Standard Error JSON Format
```json
{
  "error_code": "EXPLAINER_PIPELINE_ERROR",
  "message": "Detailed human-readable error message explaining the failure.",
  "status_code": 422,
  "timestamp": "2026-07-21T10:45:00Z",
  "details": {
    "trace_error_context": "Any specific system stack or validation detail."
  }
}
```

### Common HTTP Error Scenarios

*   **HTTP 400 Bad Request:** Occurs when query parameters or body parameters are malformed.
    *   *Example Error Code:* `INVALID_INPUT_PARAMETERS`
*   **HTTP 401 Unauthorized:** Occurs when `Authorization` token is missing, expired, or invalid.
    *   *Example Error Code:* `AUTHENTICATION_FAILED`
*   **HTTP 403 Forbidden:** Occurs when a homeowner attempts to access level 3 or level 4 details.
    *   *Example Error Code:* `INSUFFICIENT_ACCESS_ROLE`
*   **HTTP 404 Not Found:** Occurs when the requested `property_id` or `explanation_id` does not exist.
    *   *Example Error Code:* `RESOURCE_NOT_FOUND`
*   **HTTP 422 Unprocessable Entity:** Occurs when trace verification or schema validation fails due to broken hash-chains.
    *   *Example Error Code:* `TRACE_VERIFICATION_FAILED`
