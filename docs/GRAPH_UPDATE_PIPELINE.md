# PROPERTY KNOWLEDGE GRAPH UPDATE PIPELINE SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** ARCHITECTURE COMPLIANT  
**Scope:** Real-time event consumption, Transactional Outbox patterns, and Graph Invariant synchronization.

---

## 1. End-to-End Real-Time Ingest Pipeline

The Property Knowledge Graph is entirely event-driven. External actions—such as a completed drone flight, an approved analyst finding, a signed repair contract, or an oncoming hurricane—emit standardized platform events. A dedicated **Graph Update Pipeline Worker** consumes these events and translates them into semantic graph mutations.

```
┌────────────────────────────────────────────────────────┐
│               1. Platform Event Sources                │
│ (Drone flight, Finding approval, signed contract, etc.)│
└───────────────────────────┬────────────────────────────
                            │ (Publishes to Event Bus)
                            ▼
┌────────────────────────────────────────────────────────┐
│            2. Transactional Outbox Handler             │
│ (Atomically writes source change + queue event record) │
└───────────────────────────┬────────────────────────────┘
                            │ (Guarantees delivery)
                            ▼
┌────────────────────────────────────────────────────────┐
│           3. Kafka / EventBridge Message Bus          │
│    (Message routing of 'PASSPORT_UPDATED', etc.)       │
└───────────────────────────┬────────────────────────────┘
                            │ (Subscribed Consumer Group)
                            ▼
┌────────────────────────────────────────────────────────┐
│              4. Graph Synchronizer Worker              │
│  - Decodes message and loads context node properties   │
│  - Verifies evidence matches Passport Ledger           │
│  - Executes Transactional Node/Edge Mutation           │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼ (On Success)            ▼ (On Law Failure)
┌─────────────────────────────────┐ ┌─────────────────────────────────┐
│ Commit mutations to Graph Store │ │ Discard, quarantine message,    │
│ & push update event to CENTCOM. │ │ trigger CENTCOM Alerts dashboard│
└─────────────────────────────────┘ └─────────────────────────────────┘
```

---

## 2. Ingestion Event Directory

The Graph Synchronizer is registered to consume a defined subset of the standardized platform event directory.

| Emitted Event Name | Action Taken by Graph Synchronizer | State Impact on Graph Nodes/Edges |
| :--- | :--- | :--- |
| `PASSPORT_UPDATED` | Parses updated ledger entry. | Creates or updates `SYSTEM` or `MATERIAL` nodes. Appends to history. |
| `MISSION_COMPLETED`| Extracts aerial telemetry and sensor metadata. | Creates `INSPECTION` node. Connects to `SYSTEM` via `ASSESSED` edge. |
| `AI_REVIEW` | Translates computer-vision detections (e.g. radiometric hotspots). | Creates `EVIDENCE` node. Establishes `LOCATED_IN` edge to `PHOTO` node. |
| `CONTRACT_SIGNED` | Parses roofing/repair transaction details. | Creates `PROJECT` node. Establishes `INSTALLED_BY` link to `CONTRACTOR`. |
| `WARRANTY_REGISTERED`| Parses manufacturer certification details. | Creates `WARRANTY` node. Establishes `COVERED_BY` link to `SYSTEM`. |
| `CRITICAL_FINDING` | Ingests structural anomalies exceeding safety thresholds. | Creates `PROJECT_OPPORTUNITY` lead. Establishes `TARGETS` edge. |

---

## 3. Transactional Integrity & Outbox Guarantees

To prevent state divergence (where a contract is signed but the graph edge is never created due to a mid-process container crash), all source systems must employ the **Transactional Outbox Pattern**.

### Ingestion Sequence Details
1. **Atomic Transaction:** The write to the source system (e.g., adding a repair record in `nextgen_repairs`) and the write to an `outbox` table (`event_outbox`) occur inside the *same atomic database transaction*.
2. **Outbox Relay:** An independent background relay process polls the `event_outbox` collection, publishes the event to the Kafka stream, and marks the outbox record as `DISPATCHED` upon receiving broker acknowledgement.
3. **Idempotent Consumption:** The Graph Synchronizer Worker tracks the `id` (UUIDv4) of every processed event in a local Redis cache for 72 hours. If a duplicate event is received, it is immediately discarded to prevent redundant node version increments.

---

## 4. Evidence Validation & Rollback Procedures

### A. Graph Invariant Verification
During edge creation, the synchronizer executes a validation cycle that checks for existence of the backing evidence in the **Passport Canonical Ledger**.

If an edge exists, but the backing evidence is subsequently:
1. **Superseded:** During human-QA editing, a finding is marked as `SUPERSEDED` by a newer observation.
2. **Invalidated/Revoked:** A contractor's license is revoked, or a photo is flagged as corrupted.

The Graph Synchronizer must execute an **Automated Severance & Rollback** flow:

```
        ┌────────────────────────────────────────────────────────┐
        │            EVIDENCE RECALL EVENT DETECTED              │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │         Find all edges referencing evidence_id        │
        └───────────────────────────┬────────────────────────────┘
                                    │
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │      Are there alternative evidence links active?      │
        └───────────────────────────┬────────────────────────────┘
                                    │
                       ┌────────────┴────────────┐
                       │ Yes                     │ No
                       ▼                         ▼
        ┌────────────────────────┐    ┌────────────────────────┐
        │ Keep edge alive;       │    │ 1. DELETE Edge Record  │
        │ Decrement edge         │    │ 2. Re-evaluate Node    │
        │ confidence score.      │    │    confidence weights. │
        └────────────────────────┘    │ 3. Emit alert stream.  │
                                      └────────────────────────┘
```

### B. Rollback Invariant Python Pseudocode
```python
def handle_evidence_revocation(revocation_event: dict, db):
    target_evidence_id = revocation_event["evidence_id"]
    tenant_id = revocation_event["tenant_id"]
    
    # 1. Locate affected edges
    affected_edges = db.graph_edges.find({
        "tenant_id": tenant_id,
        "evidence_ids": target_evidence_id
    })
    
    for edge in affected_edges:
        remaining_evidence = [e_id for e_id in edge["evidence_ids"] if e_id != target_evidence_id]
        
        if len(remaining_evidence) > 0:
            # Downgrade confidence since some supporting evidence is gone
            new_confidence = max(0.1, edge["confidence"] * 0.5)
            db.graph_edges.update_one(
                {"_id": edge["_id"]},
                {
                    "$set": {
                        "evidence_ids": remaining_evidence,
                        "confidence": new_confidence,
                        "updated_at": get_current_utc_timestamp()
                    },
                    "$inc": {"version": 1}
                }
            )
            log_graph_change(edge["_id"], "EDGE_DOWNGRADED", f"Evidence {target_evidence_id} revoked.")
        else:
            # Severe relationship entirely (Engineering Law #1)
            db.graph_edges.delete_one({"_id": edge["_id"]})
            log_graph_change(edge["_id"], "EDGE_SEVERED", f"Edge deleted due to complete loss of evidence.")
            
            # 2. Propagate changes upstream (re-calculate confidence of connected nodes)
            recalculate_node_confidence(edge["from_node_id"], db)
            recalculate_node_confidence(edge["to_node_id"], db)
```
