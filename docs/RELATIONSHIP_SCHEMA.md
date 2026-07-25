# RELATIONSHIP SCHEMA SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** SCHEMA FINALIZED  
**Scope:** Relationship edges, validation logic, and evidence-backed graph invariants.

---

## 1. Directed Semantic Edge Architecture

In the Property Knowledge Graph, nodes represent discrete entities, and **Edges** represent semantic, directed relationships between those entities. To adhere to **Supreme Engineering Law #1 ("No relationship may exist without evidence")**, every edge is modeling as a rich document in a dedicated `graph_edges` collection that carries explicit, immutable references to verifying evidence.

### Topology Graph Visual Representation
```
                 ┌────────────────────────────────┐
                 │       SYSTEM: Roof Node        │
                 └───────────────┬────────────────┘
                                 │
                   Edge:       ▲ │ Edge:
                   CONTAINS    │ │ INSTALLED_BY
                               │ │
  ┌──────────────────────┐     │ │     ┌────────────────────────┐
  │  MATERIAL: Shingle   │◄────┘ └────►│ CONTRACTOR: Apex Roof  │
  └──────────────────────┘             └────────────────────────┘
             ▲                                     ▲
             │ Edge: EVIDENCE_FOR                  │ Edge: EXECUTED_BY
             │                                     │
  ┌──────────┴──────────┐              ┌───────────┴────────────┐
  │  EVIDENCE: Thermal  │              │ REPAIR: Shingle Patch  │
  └─────────────────────┘              └────────────────────────┘
```

---

## 2. Edge JSON Schema

All relationships in the `graph_edges` collection must validate against the following schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "GraphRelationshipEdge",
  "type": "object",
  "required": [
    "_id", "tenant_id", "property_id", "from_node_id", "to_node_id", 
    "type", "confidence", "evidence_ids", "created_at", "updated_at", "version"
  ],
  "properties": {
    "_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$", "description": "Unique ULID identifying the relationship." },
    "tenant_id": { "type": "string" },
    "property_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
    "from_node_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$", "description": "Source node identifier." },
    "to_node_id": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$", "description": "Target node identifier." },
    "type": {
      "type": "string",
      "enum": [
        "CONTAINS", "INSTALLED_BY", "COVERED_BY", "AFFECTED_BY", 
        "REFERENCED_BY", "ASSESSED", "PERFORMED_ON", "EXECUTED_BY", 
        "COMPRISES", "MANAGED_BY", "CAPTURES", "LOCATED_IN", 
        "SUBSTANTIATES", "EVIDENCES", "TARGETS", "APPLIED_TO"
      ]
    },
    "confidence": { "type": "number", "minimum": 0.0, "maximum": 1.0, "description": "Strength of relationship connection." },
    "evidence_ids": {
      "type": "array",
      "minItems": 1,
      "items": { "type": "string", "pattern": "^[0-9A-HJKMNP-TV-Z]{26}$" },
      "description": "Verifiable reference list of S3 documents, photo IDs, or passport audit IDs proving this relationship exists."
    },
    "created_at": { "type": "string", "format": "date-time" },
    "updated_at": { "type": "string", "format": "date-time" },
    "version": { "type": "integer", "minimum": 1 }
  }
}
```

---

## 3. Relationship Matrix & Permitted Edges

To prevent nonsensical topology (e.g. establishing an `INSTALLED_BY` relationship between a Material and a Photo), the graph engine restricts edges to a strict source-destination matrix.

| Source Node Type | Edge Type | Destination Node Type | Purpose / Description |
| :--- | :--- | :--- | :--- |
| **SYSTEM** | `CONTAINS` | **MATERIAL** | Identifies physical components in an assembly. |
| **SYSTEM** | `INSTALLED_BY` | **CONTRACTOR** | Tracks installation accountability. |
| **SYSTEM** | `COVERED_BY` | **WARRANTY** | Binds system coverage bounds. |
| **SYSTEM** | `AFFECTED_BY` | **TIMELINE_EVENT** | Links storm/freeze impact to physical asset. |
| **SYSTEM** | `REFERENCED_BY` | **DOCUMENT** | Identifies claims, plans, or permit filings. |
| **INSPECTION** | `ASSESSED` | **SYSTEM** | Tracks assessment bounds. |
| **REPAIR** | `PERFORMED_ON` | **SYSTEM** | Details corrective action applied to an asset. |
| **REPAIR** | `EXECUTED_BY` | **CONTRACTOR** | Tracks the certified labor force. |
| **PROJECT** | `COMPRISES` | **REPAIR** | Groups multiple repairs in a single scope. |
| **PROJECT** | `MANAGED_BY` | **CONTRACTOR** | Identifies general contractor for project. |
| **PHOTO** | `CAPTURES` | **SYSTEM** | Binds raw image capture to the asset. |
| **EVIDENCE** | `LOCATED_IN` | **PHOTO** | Maps bounding box annotation to source image. |
| **EVIDENCE** | `SUBSTANTIATES` | **REPAIR** or **SYSTEM** | Links anomalies directly to systems or completed repairs. |
| **DOCUMENT** | `EVIDENCES` | **WARRANTY** or **CONTRACTOR** | Binds certificates of insurability, licenses, or agreements. |
| **PROJECT_OPPORTUNITY** | `TARGETS` | **SYSTEM** | Identifies potential upgrade prospects. |
| **DESIGN_CONCEPT` | `APPLIED_TO` | **PROJECT_OPPORTUNITY** | Links engineered concepts to qualified leads. |

---

## 4. Engineering Law Invariant Checks

To guarantee compliance with **Supreme Engineering Law #1**, the database engine implements multi-layered database triggers and software validations.

```
       ┌────────────────────────────────────────────────────────┐
       │                 EDGE INSERTION REQUEST                 │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             Is source/target node present?             │
       └───────────────────────────┬────────────────────────────┘
                                   │
                      ┌────────────┴────────────┐
                      │ Yes                     │ No
                      ▼                         ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │ Are evidence_ids       │    │ REJECT:                │
       │ non-empty and valid?   │    │ "No relationship       │
       └──────────────┬─────────┘    │ without active node."  │
                      │              └────────────────────────┘
          ┌───────────┴───────────┐
          │ Yes                   │ No
          ▼                       ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │ Do evidence_ids        │    │ REJECT:                │
       │ exist in Passport?     │    │ "Relationship rejected.│
       └──────────────┬─────────┘    │ No evidence provided." │
                      │              └────────────────────────┘
          ┌───────────┴───────────┐
          │ Yes                   │ No
          ▼                       ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │ COMMIT EDGE RELATION   │    │ REJECT:                │
       │ - Set confidence score │    │ "Relationship rejected.│
       │ - Log into Audit Trail │    │ Evidence is invalid    │
       └────────────────────────┘    │ or not found."         │
                                     └────────────────────────┘
```

### Database Trigger Invariant Enforcement (Python Pseudocode)
```python
def validate_relationship_edge(edge: dict, db) -> bool:
    # Rule 1: Ensure from_node and to_node exist
    if not db.graph_nodes.find_one({"_id": edge["from_node_id"]}):
        raise ValueError(f"Invalid edge: Source node {edge['from_node_id']} does not exist.")
        
    if not db.graph_nodes.find_one({"_id": edge["to_node_id"]}):
        raise ValueError(f"Invalid edge: Target node {edge['to_node_id']} does not exist.")

    # Rule 2: Matrix schema validation
    from_node = db.graph_nodes.find_one({"_id": edge["from_node_id"]})
    to_node = db.graph_nodes.find_one({"_id": edge["to_node_id"]})
    permitted_relations = get_permitted_relations_matrix()
    
    if edge["type"] not in permitted_relations.get(from_node["node_type"], {}).get(to_node["node_type"], []):
        raise TypeError(f"Invalid edge: Connection from {from_node['node_type']} to {to_node['node_type']} via edge '{edge['type']}' is structurally prohibited.")

    # Rule 3: Supreme Engineering Law Check (Evidence Verification)
    if not edge.get("evidence_ids") or len(edge["evidence_ids"]) == 0:
        raise AssertionError("Supreme Engineering Law Violation: Relationships cannot exist without supporting evidence.")

    for evidence_id in edge["evidence_ids"]:
        evidence_record = db.passports.find_one({"_id": evidence_id}) or db.passport_entries.find_one({"_id": evidence_id})
        if not evidence_record:
            raise AssertionError(f"Supreme Engineering Law Violation: Evidence record {evidence_id} was not found or has been revoked.")

    return True
```
