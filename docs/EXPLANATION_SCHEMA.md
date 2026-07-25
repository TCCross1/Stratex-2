# EXPLANATION SCHEMA SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 013 · OPERATION INTELLIGENCE EXPLAINER
**Status:** SCHEMA FINALIZED  
**Scope:** MongoDB Collection structure, JSON Schema (Draft 2020-12), and canonical payload examples.

---

## 1. Database Architecture & Collections

Explanations are generated dynamically and stored in a read-optimized collection named `intelligence_explanations`. Each document represents a snapshot of the reasoning behind a specific score, recommendation, or warning, frozen in time and locked to specific versions of Property DNA and the Passport Ledger.

### Collections and ERD Relations

```
 ┌──────────────────────┐             ┌─────────────────────────────┐
 │     property_dna     │             │  intelligence_explanations  │
 ├──────────────────────┤             ├─────────────────────────────┤
 │ canonical_id (PK)    ◄────────────►│ explanation_id (PK)         │
 │ property_id (FK)     │             │ property_id (FK)            │
 │ version              │             │ dna_version_referenced      │
 └──────────────────────┘             │ system_category             │
                                      │ overall_confidence_score    │
                                      │ levels [Level 1,2,3,4]      │
                                      │ evidence_trace              │
                                      └──────────────┬──────────────┘
                                                     │
                                                     │ (Refers to Source)
                                                     ▼
 ┌──────────────────────┐             ┌─────────────────────────────┐
 │   passport_entries   │             │          findings           │
 ├──────────────────────┤             ├─────────────────────────────┤
 │ canonical_id (PK)    ◄────────────►│ canonical_id (PK)           │
 │ passport_id (FK)     │             │ property_id (FK)            │
 │ entry_type           │             │ status                      │
 └──────────────────────┘             └─────────────────────────────┘
```

---

## 2. JSON Schema: Intelligence Explanation Document

All documents in the `intelligence_explanations` collection, and all API responses returning explanations, must validate against the following Draft 2020-12 JSON Schema.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "IntelligenceExplanationDocument",
  "type": "object",
  "required": [
    "explanation_id",
    "property_id",
    "tenant_id",
    "dna_version_referenced",
    "system_category",
    "created_at",
    "updated_at",
    "overall_confidence_score",
    "levels",
    "evidence_trace"
  ],
  "properties": {
    "explanation_id": {
      "type": "string",
      "description": "Unique, system-wide identifier for this explanation record."
    },
    "property_id": {
      "type": "string",
      "description": "The unique identifier of the target property."
    },
    "tenant_id": {
      "type": "string",
      "description": "Multi-tenant identifier for platform segregation."
    },
    "dna_version_referenced": {
      "type": "integer",
      "description": "The exact version of the Property DNA projection active when this explanation was compiled."
    },
    "system_category": {
      "type": "string",
      "enum": [
        "ROOF",
        "FOUNDATION",
        "WINDOWS",
        "HVAC",
        "ELECTRICAL",
        "PLUMBING",
        "WATER_INTRUSION",
        "THERMAL_FINDINGS",
        "ENERGY_PERFORMANCE",
        "INSURANCE_CLAIMS",
        "MAINTENANCE",
        "PROJECT_OPPORTUNITIES"
      ],
      "description": "The specific building system or logical assessment domain."
    },
    "created_at": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of explanation compilation in ISO 8601 UTC."
    },
    "updated_at": {
      "type": "string",
      "format": "date-time",
      "description": "Timestamp of last modification in ISO 8601 UTC."
    },
    "overall_confidence_score": {
      "type": "number",
      "minimum": 0,
      "maximum": 100,
      "description": "Calculated percentage confidence score (0-100) representing reliability of evidence chain."
    },
    "levels": {
      "type": "object",
      "required": ["level_1", "level_2", "level_3", "level_4"],
      "properties": {
        "level_1": {
          "$ref": "#/$defs/explanationContent",
          "description": "Level 1: Simple Homeowner Explanation."
        },
        "level_2": {
          "$ref": "#/$defs/explanationContent",
          "description": "Level 2: Contractor Explanation."
        },
        "level_3": {
          "$ref": "#/$defs/explanationContent",
          "description": "Level 3: Engineering Explanation."
        },
        "level_4": {
          "type": "object",
          "required": ["evidence_chain_ledger"],
          "properties": {
            "evidence_chain_ledger": {
              "type": "array",
              "items": {
                "type": "object",
                "required": ["step_index", "source_type", "reference_id", "timestamp", "payload_hash", "fact_snapshot"],
                "properties": {
                  "step_index": { "type": "integer" },
                  "source_type": { "type": "string", "enum": ["EVIDENCE", "PASSPORT_ENTRY", "DNA_NODE", "KG_PATH", "AI_REASONING"] },
                  "reference_id": { "type": "string" },
                  "timestamp": { "type": "string", "format": "date-time" },
                  "payload_hash": { "type": "string" },
                  "fact_snapshot": { "type": "object" }
                }
              }
            }
          },
          "description": "Level 4: Complete Evidence Chain. Chronological, non-narrative raw ledger track."
        }
      }
    },
    "evidence_trace": {
      "type": "object",
      "required": [
        "origin_mission_ids",
        "evidence_ids",
        "passport_entry_ids",
        "dna_nodes_referenced",
        "knowledge_graph_paths",
        "applicable_standards"
      ],
      "properties": {
        "origin_mission_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of inspection, flight, or maintenance mission IDs from which raw evidence was gathered."
        },
        "evidence_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of direct raw file or database attachment IDs (images, thermal, sensor logs)."
        },
        "passport_entry_ids": {
          "type": "array",
          "items": { "type": "string" },
          "description": "List of canonical Passport Ledger entry IDs holding the approved findings."
        },
        "dna_nodes_referenced": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Specific path nodes within the Property DNA object referenced by this explanation."
        },
        "knowledge_graph_paths": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Represented as arrays of directional traversal segments, e.g., 'NODE_A -> REL_TYPE -> NODE_B'."
        },
        "applicable_standards": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Regulatory codes or building guidelines referenced (e.g., 'IRC 2021 Chapter 9', 'ASTM D3462')."
        }
      }
    }
  },
  "$defs": {
    "explanationContent": {
      "type": "object",
      "required": [
        "conclusion",
        "supporting_evidence",
        "confidence_explanation",
        "why_this_matters",
        "recommended_next_steps",
        "related_systems",
        "assumptions",
        "unknowns"
      ],
      "properties": {
        "conclusion": {
          "type": "string",
          "description": "The clear, direct, and unambiguous bottom-line state assessment or rating."
        },
        "supporting_evidence": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Human-readable summaries of the direct physical observations and verification actions."
        },
        "confidence_explanation": {
          "type": "string",
          "description": "Narrative explaining WHY the confidence score is at its current percentage value, detailing factors like age or source type."
        },
        "why_this_matters": {
          "type": "string",
          "description": "Detailed impacts of this finding, covering safety, financial implications, structural decay, or risk exposure."
        },
        "recommended_next_steps": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Ordered, actionable recommendations for remediation, monitoring, or further inspection."
        },
        "related_systems": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Other building components or operational areas connected physically or logically to this system."
        },
        "assumptions": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Physical parameters or logical baselines assumed (e.g., material default lifespans, standard wind load tolerances)."
        },
        "unknowns": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Physical details or parameters that are completely unverified, missing, or obscured. Must be explicit."
        }
      }
    }
  }
}
```

---

## 3. Canonical Payload Example (Validating Document)

The following JSON is an official, comprehensive record of an explanation for a **Water Intrusion** issue, formatted exactly as it is saved in MongoDB and output by APIs.

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
    },
    "level_2": {
      "conclusion": "Minor flashing separation in north roof valley is permitting moisture ingress, saturating decking and joists at attic grid location A-12.",
      "supporting_evidence": [
        "Calibrated moisture pin-probe sensor (ID: damp_sens_44) returned 24% wood moisture equivalent.",
        "Drone flight mission ID: msn_9022 drone photo ID: img_3329 shows a 2-inch mechanical gap in lead-valley metal flashing."
      ],
      "confidence_explanation": "Confidence calculated at 92.5% based on physical photo proof (< 48 hrs old) and matching electronic telemetric sensor validation.",
      "why_this_matters": "Moisture level (24% WME) exceeds the decay threshold (20% WME). Continuous exposure will cause mechanical failure of the 1/2-inch plywood decking within 90 days and compromise drywall ceiling integrity.",
      "recommended_next_steps": [
        "Secure a tarp on the roof valley surface spanning 4 feet on either side of the joint.",
        "Remove damaged valley metal flashing and re-lay ICE & SHIELD underlayment layer before nailing new flashing."
      ],
      "related_systems": [
        "North valley flashing joints",
        "Plywood decking panels (A-12 grid)",
        "Ceiling drywall layers"
      ],
      "assumptions": [
        "Standard local wind-driven rain rates applied during calculation models.",
        "Existing underlayment under valley flashing is standard organic felt."
      ],
      "unknowns": [
        "Whether dry rot has already taken hold inside the concealed joist-plate connection below the insulation layer."
      ]
    },
    "level_3": {
      "conclusion": "Localized water intrusion originating from mechanical rupture of north valley metal flashing, resulting in 24% WME in adjacent structural roof rafters (Grid A-12).",
      "supporting_evidence": [
        "Mission ID msn_9022 sensor damp_sens_44: Telemetry logs indicate relative wood moisture equivalent has risen from 12% to 24% over 48 hours.",
        "High-density photogrammetry shows an aperture separation of 50mm in lead-alloy flashing at slope interface coordinate x:422, y:815."
      ],
      "confidence_explanation": "92.5% confidence is computed via dual-point verification: a high-resolution optical asset (Weight: 0.50, reliability: 0.95) and an on-site telemetry sensor node (Weight: 0.50, reliability: 0.90) with overlapping geographical targets.",
      "why_this_matters": "A wood moisture content of 24% triggers active fungal growth (Coniophora puteana) and structural decay. The structural load capacity of standard Douglas Fir No. 2 rafters decreases exponentially under sustained saturation.",
      "recommended_next_steps": [
        "Apply emergency adhesive vapor barrier membrane across slope joint coordinates.",
        "Perform mechanical replacement of valley metal flashing in compliance with SMACNA architectural sheet metal guidelines."
      ],
      "related_systems": [
        "Roofing Slope Valleys",
        "Douglas Fir No. 2 rafters (load-bearing)",
        "Under-roof air circulation envelope"
      ],
      "assumptions": [
        "Wood species is Douglas Fir with a default dry-density weight of 32 lbs/cu.ft.",
        "Ambient relative humidity inside attic remains at 55% baseline."
      ],
      "unknowns": [
        "Total volumetric moisture retention within the fiberglass insulation batts at the base of the rafter bay."
      ]
    },
    "level_4": {
      "evidence_chain_ledger": [
        {
          "step_index": 1,
          "source_type": "EVIDENCE",
          "reference_id": "ev_file_9918a2d1e2e3",
          "timestamp": "2026-07-21T08:15:22Z",
          "payload_hash": "sha256:d5e829a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9",
          "fact_snapshot": {
            "mime_type": "image/jpeg",
            "resolution": "4032x3024",
            "gps": {"lat": 27.9472, "lng": -82.4584},
            "sensor_id": "drone_camera_sony_a7"
          }
        },
        {
          "step_index": 2,
          "source_type": "PASSPORT_ENTRY",
          "reference_id": "pass_entry_00994f2b",
          "timestamp": "2026-07-21T09:00:10Z",
          "payload_hash": "sha256:88fa2b13c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1",
          "fact_snapshot": {
            "status": "APPROVED",
            "inspector_id": "usr_atlas_99",
            "notes": "Verified north valley flashing separation of approx 2 inches."
          }
        },
        {
          "step_index": 3,
          "source_type": "DNA_NODE",
          "reference_id": "dna_node_health_moisture",
          "timestamp": "2026-07-21T09:05:00Z",
          "payload_hash": "sha256:44b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f188fa2b13c4d5e6f7a8b9c0d1e2f3",
          "fact_snapshot": {
            "current_value": "FAILING",
            "provenance": "Verified",
            "confidence_score": 92.5
          }
        },
        {
          "step_index": 4,
          "source_type": "KG_PATH",
          "reference_id": "kg_path_roof_to_attic_moisture",
          "timestamp": "2026-07-21T09:05:15Z",
          "payload_hash": "sha256:1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1112",
          "fact_snapshot": {
            "traversal_path": "ROOF_VALLEY -> CHANNELS_WATER_TO -> ATTIC_RAFTERS -> EXPOSES_TO -> CEILING_DRYWALL"
          }
        },
        {
          "step_index": 5,
          "source_type": "AI_REASONING",
          "reference_id": "ai_inference_7722",
          "timestamp": "2026-07-21T10:30:00Z",
          "payload_hash": "sha256:f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f122",
          "fact_snapshot": {
            "model_used": "claude-sonnet-4.6",
            "tokens_consumed": 1824,
            "validation_status": "PASSED_GUARDRAIL"
          }
        }
      ]
    }
  },
  "evidence_trace": {
    "origin_mission_ids": ["msn_9022_roof_thermal_flyover"],
    "evidence_ids": ["ev_file_9918a2d1e2e3", "ev_sensor_damp_sens_44"],
    "passport_entry_ids": ["pass_entry_00994f2b", "pass_entry_00994f2c"],
    "dna_nodes_referenced": ["health.moisture.current_value", "risk.moisture_exposure.current_value"],
    "knowledge_graph_paths": [
      "ROOF_VALLEY --[DRAINS_TO]--> ATTIC_RAFTERS",
      "ATTIC_RAFTERS --[TOUCHES]--> CEILING_DRYWALL"
    ],
    "applicable_standards": [
      "International Residential Code (IRC) 2021 Section R905.2.8.2 (Valleys)",
      "ASTM D3462 (Standard Specification for Asphalt Shingles Made from Glass Felt)"
    ]
  }
}
```
