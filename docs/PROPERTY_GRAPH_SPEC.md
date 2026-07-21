# PROPERTY KNOWLEDGE GRAPH SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** DESIGN COMPLETE · STANDARDIZED  
**Scope:** Universal Property Knowledge Graph (PKG) layer across the entire Stratex ecosystem.

---

## 1. Executive Vision & Core Philosophy

The **Property Knowledge Graph™ (PKG)** is the multi-dimensional, semantic network that bridges raw physical observations, contractor operational history, warranties, and weather events into an intelligent, queryable web of connections. While the **Property Passport** serves as the immutable ledger of truth for facts, and **Property DNA** provides a read-optimized, single-property flat projection, the **Property Knowledge Graph** models the complex, interconnected reality of properties.

By structuring property data as a graph, Stratex transforms isolated database rows into an active operational network. An event or anomaly in one domain (such as a severe weather storm) dynamically propagates risks and insights through connected nodes (such as the specific shingle material, the installing contractor, the active warranty, and pending repair opportunities).

```
                      ┌─────────────────────────────────┐
                      │    CANONICAL PASSPORT LEDGER    │ (Immutable Fact Registry)
                      └────────────────┬────────────────┘
                                       │ (Monotonic Influx)
                                       ▼
                      ┌─────────────────────────────────┐
                      │     PROPERTY DNA ENGINE™        │ (Single-Property Projections)
                      └────────────────┬────────────────┘
                                       │ (Semantic Linkage)
                                       ▼
                      ┌─────────────────────────────────┐
                      │    PROPERTY KNOWLEDGE GRAPH™    │ (Cross-Domain Semantic Web)
                      │    - Nodes: Systems, Materials  │
                      │    - Edges: InstalledBy, Covers │
                      └─────────────────────────────────┘
```

---

## 2. The Supreme Engineering Law

> **No relationship may exist without evidence.**

To prevent "hallucinated" connections, every single edge (relationship) defined within the Property Knowledge Graph **MUST** be explicitly backed by a verifiable chain of custody (evidence). 
1. **Explicit Reference:** An edge cannot be created unless it references at least one canonical `evidence_id` from the Property Passport (e.g., photo UUID, flight record, contractor closeout receipt, or signed legal document).
2. **Confidence Bounds:** The confidence score of a relationship is mathematically bound by the confidence of its underlying evidence.
3. **Automated Severance:** If the supporting evidence node is deleted, superseded, or discredited (e.g., during human-QA override), the relationship must be automatically severed or marked as `INVALID`.

---

## 3. High-Level System Architecture

The Property Knowledge Graph utilizes a **Hybrid Graph Storage Strategy** to balance high-throughput transactional writes with complex, low-latency relational traversals.

```
       ┌────────────────────────────────────────────────────────┐
       │                  MUTATION / EVENT BUS                  │
       │    (Kafka/EventBridge: PASSPORT_UPDATED, etc.)         │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │             GRAPH UPDATE PIPELINE WORKER               │
       │   - Validates incoming events against schemas          │
       │   - Resolves node identities & verifies evidence       │
       └───────────────────────────┬────────────────────────────┘
                                   │
                    ┌──────────────┴──────────────┐
                    ▼                             ▼
       ┌────────────────────────┐    ┌────────────────────────┐
       │      NODE STORE        │    │    TOPOLOGY STORE      │
       │  (MongoDB: Node Body)  │    │  (Neo4j/Adjacency List)│
       │  Contains rich data    │    │  High-speed traversals │
       └────────────▲───────────┘    └────────────▲───────────┘
                    │                             │
                    └──────────────┬──────────────┘
                                   │ (Unified Interface)
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                GRAPH QUERY ENGINE (GQE)                │
       │   - Pathfinding, pattern matching, confidence decay    │
       │   - Exposes GraphQL and REST query interfaces          │
       └───────────────────────────┬────────────────────────────┘
                                   │
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │                 VISUALIZATION PLATFORM                 │
       │   - CENTCOM interactive network dashboards             │
       │   - 3D spatial relationship mappings (Three.js)        │
       └────────────────────────────────────────────────────────┘
```

---

## 4. Key Design Principles

### A. Graph Invariant Verification
A background validator continuously scans the Graph Topology Store against the Node Store. Any edge referencing non-existent nodes, unapproved findings, or missing evidence is immediately quarantined, and a `GRAPH_INTEGRITY_VIOLATION` is published to the CENTCOM Timeline.

### B. Multi-Dimensional Traversals
The graph supports three native dimensions of traversal:
1. **Structural/Physical:** Traversing physical building hierarchies (Property → Roof System → Architectural Shingle Material).
2. **Operational/Temporal:** Traversing chronological lifecycles (Inspection Mission → Finding → Project → Repair Contractor).
3. **Legal/Financial:** Traversing accountability structures (Warranty → Manufacturer → Contractor → Insurance Claim).

### C. Confident Path Propagation
Unlike traditional flat records, risk in the PKG propagates dynamically along relationship paths. If a storm event affects a property, any systems with estimated remaining lifespans below a certain threshold are highlighted as `HIGH_RISK_OPPORTUNITIES`, allowing contractors to proactively bid on repairs.
