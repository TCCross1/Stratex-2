# PROPERTY KNOWLEDGE GRAPH API SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** API APPROVED  
**Scope:** Hardened NextGen v1 Graph REST/GraphQL endpoints for querying, traversing, and modifying nodes and relationships.

---

## 1. System API Hierarchy & Auth Roles

The Property Knowledge Graph (PKG) exposes dedicated REST endpoints under `/nextgen/v1/graph` designed for rapid navigation, sub-millisecond lookups, and strict validation of relational connections. 

### Security & Scope Matrix

| Method | Endpoint | Auth Scope | Purpose |
| :--- | :--- | :--- | :--- |
| **GET** | `/nextgen/v1/properties/{property_id}/graph` | Reader / Contractor / GM / CEO | Returns the entire Property Graph (all nodes and edges). |
| **GET** | `/nextgen/v1/graph/nodes/{node_id}` | Reader / Contractor / GM / CEO | Retrieves detailed attributes of a single graph node. |
| **POST** | `/nextgen/v1/graph/nodes` | Contractor / GM / CEO | Creates or registers a new node within the ecosystem. |
| **POST** | `/nextgen/v1/graph/edges` | Contractor / GM / CEO | Establishes a semantic relationship. *Enforces Evidence Rules.* |
| **DELETE**| `/nextgen/v1/graph/edges/{edge_id}` | Admin / GM / CEO | Severs an established relationship. |
| **GET** | `/nextgen/v1/graph/nodes/{node_id}/traverse`| Reader / Contractor / GM / CEO | Executes deep neighborhood searches and path traversals. |
| **POST** | `/nextgen/v1/graph/query` | Reader / Contractor / GM / CEO | Custom semantic pattern matcher (DSL query). |

---

## 2. API Endpoints Specification

### A. GET Full Property Graph
**Path:** `/nextgen/v1/properties/{property_id}/graph`  
**Description:** Retrieves the entire Property Knowledge Graph, separating nodes and edges. Highly optimized for visualization engines.

#### Request Headers
```http
Authorization: ******
X-Tenant-ID: tenant_north_east_01
```

#### Successful Response (200 OK)
```json
{
  "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
  "version": 14,
  "nodes": [
    {
      "id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
      "node_type": "SYSTEM",
      "name": "Primary Roof System",
      "confidence": 0.98,
      "provenance": "VERIFIED"
    },
    {
      "id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C",
      "node_type": "CONTRACTOR",
      "name": "Apex Roofing Solutions",
      "confidence": 1.0,
      "provenance": "VERIFIED"
    }
  ],
  "edges": [
    {
      "id": "01H2Z4M9RE6X7S2W1E5T0N9V4A",
      "from_node_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
      "to_node_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C",
      "type": "INSTALLED_BY",
      "confidence": 0.95,
      "evidence_ids": ["01H2Z4J6KW9T5V2Y7X3V6M8B9E"]
    }
  ]
}
```

---

### B. POST Establish Edge Relation
**Path:** `/nextgen/v1/graph/edges`  
**Description:** Creates a directed, semantic edge connecting two existing nodes. Must pass **Supreme Engineering Law** checks by providing active `evidence_ids`.

#### Request Payload
```json
{
  "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
  "from_node_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
  "to_node_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C",
  "type": "INSTALLED_BY",
  "confidence": 0.95,
  "evidence_ids": ["01H2Z4J6KW9T5V2Y7X3V6M8B9E"]
}
```

#### Successful Response (201 Created)
```json
{
  "success": true,
  "edge_id": "01H2Z4M9RE6X7S2W1E5T0N9V4A",
  "created_at": "2026-07-21T09:12:00Z",
  "version": 1
}
```

#### Failure Response (403 Forbidden - No Evidence Provided)
```json
{
  "error": "SUPREME_ENGINEERING_LAW_VIOLATION",
  "message": "No relationship may exist without evidence. Edge creation rejected because 'evidence_ids' was empty or reference could not be verified in Passport Ledger."
}
```

---

### C. GET Neighborhood Traversal
**Path:** `/nextgen/v1/graph/nodes/{node_id}/traverse`  
**Description:** Executes a path traversal from a specified root node up to `N` depth, optionally filtering by relationship types or confidence bounds.

#### Request Parameters
| Parameter | Type | Required | Default | Description |
| :--- | :--- | :--- | :--- | :--- |
| `depth` | integer | No | `1` | Depth of traversals (Maximum: `5`). |
| `direction` | string | No | `OUTGOING` | Edge direction: `OUTGOING`, `INCOMING`, `ANY`. |
| `edge_types` | string | No | `null` | Comma-separated list of edges to traverse. |
| `min_confidence`| float | No | `0.0` | Filters out paths dropping below threshold. |

#### Request URL Example
`/nextgen/v1/graph/nodes/01H2Z4K9MZ7R8W4Q5Y9E1N3S4A/traverse?depth=2&edge_types=CONTAINS,INSTALLED_BY&min_confidence=0.75`

#### Successful Response (200 OK)
```json
{
  "origin_node_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
  "depth_reached": 2,
  "paths": [
    {
      "nodes": [
        { "id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A", "type": "SYSTEM", "name": "Primary Roof System" },
        { "id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4M", "type": "MATERIAL", "name": "Architectural Shingle" }
      ],
      "edges": [
        { "id": "01H2Z4M9RE6X7S2W1E5T0N9V4D", "type": "CONTAINS", "confidence": 1.0 }
      ],
      "path_confidence": 1.0
    },
    {
      "nodes": [
        { "id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A", "type": "SYSTEM", "name": "Primary Roof System" },
        { "id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C", "type": "CONTRACTOR", "name": "Apex Roofing Solutions" }
      ],
      "edges": [
        { "id": "01H2Z4M9RE6X7S2W1E5T0N9V4A", "type": "INSTALLED_BY", "confidence": 0.95 }
      ],
      "path_confidence": 0.95
    }
  ]
}
```

---

### D. POST Query Language Engine (GQE)
**Path:** `/nextgen/v1/graph/query`  
**Description:** Evaluates structured queries in our high-performance graph pattern matcher DSL. Excellent for cross-cutting queries.

#### Request Payload (Finding roof systems installed by 'Apex' with open opportunities)
```json
{
  "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
  "query": "MATCH (s:SYSTEM {system_type: 'ROOF'})-[r:INSTALLED_BY]->(c:CONTRACTOR {company_name: 'Apex Roofing Solutions'}) MATCH (s)-[o:TARGETS]-(op:PROJECT_OPPORTUNITY) RETURN s, c, op"
}
```

#### Successful Response (200 OK)
```json
{
  "query_id": "01H2Z4P8W3Q2E5N4A7X1C2D3E4",
  "took_ms": 1.84,
  "columns": ["s", "c", "op"],
  "rows": [
    [
      { "id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A", "node_type": "SYSTEM", "name": "Primary Roof System" },
      { "id": "01H2Z4J6KW9T5V2Y7X3V6M8B9C", "node_type": "CONTRACTOR", "name": "Apex Roofing Solutions" },
      { "id": "01H2Z4M9RE6X7S2W1E5T0N9V4P", "node_type": "PROJECT_OPPORTUNITY", "name": "High-Wind Shingle Upgrade" }
    ]
  ]
}
```
