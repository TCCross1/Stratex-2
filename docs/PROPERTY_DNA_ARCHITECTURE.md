# PROPERTY DNA ARCHITECTURE SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 011 · OPERATION PROPERTY DNA
**Status:** ARCHITECTURE APPROVED  
**Scope:** System topology, cache design, consensus integration, and extensibility patterns.

---

## 1. System Topology & Decoupling Model

The Property DNA Engine™ sits at the center of the Stratex-2 ecosystem. It acts as a read-optimized, stateful projection layer. By separating canonical writes (which must go through the Property Passport) from consumer reads, we achieve horizontal scalability and near-zero database contention.

```
                  ┌─────────────────────────────────────────┐
                  │          PASSPORT WRITES ONLY           │
                  │   (Inspections, Certified Work, etc.)   │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │    MONGO: canonical passport ledgers    │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
                  ┌─────────────────────────────────────────┐
                  │          PROPERTY DNA PIPELINE          │
                  │      (Resolves & projects fields)       │
                  └────────────────────┬────────────────────┘
                                       │
                                       ▼
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      REDIS DISTRIBUTED CACHE                           │
 │     (High-speed JSON store, key: 'property_dna:{property_id}')         │
 └─────────────────────────────────────┬──────────────────────────────────┘
                                       │
         ┌─────────────────────────────┼─────────────────────────────┐
         ▼                             ▼                             ▼
   ┌───────────┐                 ┌───────────┐                 ┌───────────┐
   │  Habitat  │                 │  Reports  │                 │ Insurance │
   │ (Consume) │                 │ (Display) │                 │ (Future)  │
   └───────────┘                 └───────────┘                 └───────────┘
```

Downstream consumers (such as Habitat, Reports, and Insurance products) never read from the raw, high-churn tables of findings or missions. Instead, they request the fully pre-compiled Property DNA document. This decouples database write performance from user interface load times.

---

## 2. High-Performance Caching Strategy

To deliver Property DNA profiles under 50 milliseconds globally, the engine integrates an aggressive caching layer using Redis.

### A. Key-Value Storage Schema
*   **Key Format:** `property_dna:{property_id}`
*   **Data Type:** RedisJSON or raw compressed string.
*   **TTL (Time-To-Live):** 24 Hours (`86400` seconds).

### B. Cache Invalidation & Write-Through Rules
*   **On DNA Update:** When `/properties/{id}/dna/update` completes a successful transaction, the handler immediately evicts the Redis key: `DEL property_dna:{property_id}`.
*   **On Event Ingest:** The background worker processing `FINDING_APPROVED` or `PASSPORT_ENTRY_COMMITTED` events evicts the cache key post-write.
*   **Cache-Aside Read Pattern:** When a GET request arrives:
    1.  The API queries Redis for `property_dna:{property_id}`.
    2.  If present (Cache Hit), returns the JSON directly.
    3.  If missing (Cache Miss), the API queries MongoDB, invokes the dynamic seeder to resolve any new findings, saves the results to Redis, and returns the payload.

---

## 3. Real-Time Audit Trail Logging

Every modification to the Property DNA document is captured in the platform's central audit ledger, meeting strict regulatory compliance.

### Audit Log Schema
All updates write a document to the `audit` collection:
```json
{
  "canonical_id": "01H2Z5GN2M3S4D5G6Q7W8E9R1T",
  "actor_id": "usr_gm_sarah",
  "actor_role": "gm",
  "action": "property.dna_updated",
  "target_type": "property_dna",
  "target_id": "01H2Z4K9MZ7R8W4Q5Y9E1N3S4A",
  "payload": {
    "field": "health.roofing",
    "value": "Asphalt Shingle: Minor granule loss noted (APPROVED)",
    "version": 3,
    "confidence_score": 95.0
  },
  "timestamp": "2026-07-21T03:15:10Z"
}
```

---

## 4. Consensus & Confidence Scoring Engine

Confidence levels in Property DNA are not arbitrarily assigned. They represent the mathematically derived outputs of the AI Consensus Engine.

### A. Consensus Confidence Derivation
When multiple computer vision models (e.g., Drone Roof Inspection Model A, Thermal Wall Model B) and human analysts evaluate a property feature, they emit confidence levels. The engine aggregates these into a final `confidence_score` using a weighted consensus formula:

$$\text{Confidence Score} = w_{\text{analyst}} \cdot C_{\text{analyst}} + w_{\text{AI}} \cdot C_{\text{AI}}$$

Where:
*   $w_{\text{analyst}} = 0.60$ (Human field observation weight)
*   $w_{\text{AI}} = 0.40$ (AI inference weight)
*   $C$ represents the individual confidence percentage.

### B. Downward Confidence Decay
For components subject to weather wear (roofing, exterior trim), the confidence score decays over time if no new physical observations are made.
*   **Decay Formula:** $C_{\text{current}} = C_{\text{original}} \cdot (1 - r \cdot t)$
    *   $r$: Decay rate (e.g., $0.05$ per year for Roofing).
    *   $t$: Years elapsed since the last verified inspection.
*   Once $C_{\text{current}}$ falls below a specific threshold (e.g., 50.0%), the system automatically flags the field's provenance as `Estimated` or `Projected`, alerting the property owner that a new physical scan is recommended.

---

## 5. Future Extensibility & Integrations

The architecture is built with future strategic integrations in mind, ensuring third-party tools do not bypass safety rules.

1.  **Insurance API Webhooks:** Authorized insurance underwriters can register webhooks to receive real-time updates when a property's `risk.insurance_exposure` or `health.roofing` status changes, facilitating immediate, automated premium adjustments.
2.  **Smart IoT Gateway:** Homeowner IoT gateways (such as smart water meters or relative humidity sensors) can post data stream events. These are processed via the outbox pipeline, and if an anomaly is confirmed, update the `health.moisture` node.
3.  **Green Energy Audits:** Future federal and local rebate systems can query the `financial.future_investment_opportunities` and `awe.energy_index` fields to pre-qualify properties for solar array or heat pump installations automatically, without requiring tedious manual site audits.
