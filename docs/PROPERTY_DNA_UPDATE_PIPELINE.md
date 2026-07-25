# PROPERTY DNA UPDATE PIPELINE SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 011 · OPERATION PROPERTY DNA
**Status:** ARCHITECTURE COMPLIANT  
**Scope:** Real-time stream processing, outbox patterns, and transaction limits for Property DNA.

---

## 1. End-to-End Dynamic Ingestion Pipeline

The Property DNA Engine™ is designed around an event-driven, outbox-mediated ingest pipeline. No system edits the `property_dna` collection directly. Instead, when findings or contractor activities are peer-reviewed and approved, the platform emits immutable events that are processed by a dedicated worker.

```
 ┌────────────────────────────────────────────────────────┐
 │            1. Canonical System Ingestion               │
 │ (Drone scan completed, finding created, work certified)│
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │            2. Finding Approval Phase (PIE)            │
 │  (Authorized reviewer approves, appends to Passport)  │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │             3. Transactional Outbox Pattern            │
 │ (Atomically write finding + enqueue 'FINDING_APPROVED')│
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │            4. Event Broker / Message Queue             │
 │         (Delivers message to DNA pipeline consumer)    │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │           5. Property DNA Ingest & Resolution         │
 │ (Checks version, builds history entry, updates DNA)    │
 └────────────────────────────────────────────────────────┘
```

---

## 2. Ingestion Triggers & Event Listeners

Three central event triggers invoke the Property DNA pipeline:

1.  **`FINDING_APPROVED`**: Triggered when a raw physical observation or AI image analysis gets approved by an authorized role (CEO, Admin, GM).
2.  **`PASSPORT_ENTRY_COMMITTED`**: Triggered when a new entry is successfully written to the ledger (such as a warranty activation, renovation contract closure, or mechanical service record).
3.  **`PROPERTY_INITIALIZED`**: Triggered when a brand-new property is created inside Stratex, triggering the initial seeding sequence.

### Real-Time Event Payload Example
```json
{
  "id": "evt_01H2Z5FN2M3S4D5G6Q7W8E9R1T",
  "type": "FINDING_APPROVED",
  "timestamp": "2026-07-21T03:12:00Z",
  "region": "US-NE",
  "operator": "usr_system_seeder",
  "details": {
    "property_id": "01H2Z4J6KW9T5V2Y7X3V6M8B9X",
    "finding_id": "01H2Z4P2M9T5Q7F8N1B6A2D1V",
    "category": "roofing",
    "component": "Shingles",
    "observation": "Asphalt Shingle (Architectural) installation verified compliant",
    "severity": "INFORMATIONAL",
    "confidence_pct": 98.0
  }
}
```

---

## 3. Dynamic Seeding & Initialization Logic

When a Property DNA profile is requested for the first time via the GET route, the engine checks for its existence. If it does not exist, a dynamic seeder is triggered:

1.  **Retrieve Core Property Attributes:** Fetches physical specifications from the `properties` collection (e.g., Address, Build Year).
2.  **Make Baseline Field Entries:** For each required category, generates a version `1` entry with "Baseline Record" attribution.
3.  **Map approved history:** Performs an immediate, real-time aggregate query across existing `APPROVED` findings and `passport_committed` intelligence objects.
4.  **Write and return:** Inserts the compiled DNA record into `property_dna` atomically.

---

## 4. Aggregation & Category Mapping Rules

The pipeline uses a strict taxonomy category map to routes Passport information to its correct place in the Property DNA schema.

| Taxonomy Category / System | Target DNA Schema Field | Notes |
| :--- | :--- | :--- |
| `roof` / `roofing` | `health.roofing`, `lifecycle.roof_age` | Maps shingle state and flashing integrity. |
| `foundation` / `crawlspace` | `health.structural`, `lifecycle.foundation`| Tracks settlement and moisture readings. |
| `exterior` / `cladding` | `health.exterior`, `lifecycle.exterior` | Vinyl, wood, or brick masonry siding age. |
| `windows` | `lifecycle.windows` | Tracks insulation envelope seal failures. |
| `doors` | `identity.construction_type` | Outer barrier integrity. |
| `hvac` / `mechanical` | `health.air`, `lifecycle.hvac_age` | Maps furnace, heat pump, or AC status. |
| `electrical` | `health.safety` | Panel capacity and GFCI hazard status. |
| `plumbing` | `health.moisture` | Maps active leak alerts or pipe types (e.g. PEX). |
| `insulation` | `health.energy` | Outer thermal barrier (R-value). |
| `awe` | `awe.overall_awe_index` | Captures overall resilient building systems. |

---

## 5. Transaction Safety & Write Hardening

To ensure absolute atomicity under Rule #1 (Passport remains the only canonical record), the pipeline performs updates inside a MongoDB multi-document session transaction:

1.  **Lock Passport Entry:** Appends the dynamic `DNA_FIELD_UPDATED` entry to `nextgen_passport_entries` first.
2.  **Calculate Update Value:** Reads the existing DNA record, builds the new history block, and calculates the next incremental version.
3.  **Perform Update:** Updates `property_dna` using `$set` on the current value and `$push` on the history array.
4.  **Write Audit Trail:** Records a `property.dna_updated` event to the central platform audit log.
5.  **Commit Transaction:** If any of steps 1-4 fail, the transaction is immediately aborted, rolling back all state changes. No orphaned or partial DNA writes can exist.
