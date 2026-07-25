# PROPERTY KNOWLEDGE GRAPH QUERY ENGINE (v1.0)
## CENTCOM DIRECTIVE 012 · OPERATION PROPERTY KNOWLEDGE GRAPH
**Status:** ARCHITECTURE APPROVED  
**Scope:** Graph Traversal Algorithms, Query Compilation, Optimization, and Tenant Sandboxing.

---

## 1. Engine Core Overview

The **Graph Query Engine (GQE)** is the computation layer that parses, compiles, optimizes, and executes multi-hop relational lookups across the Stratex Property Knowledge Graph. It provides both low-latency point-to-point traversal APIs and expressive semantic pattern-matching capabilities, enabling executive analysis such as:
* *"Identify all asphalt roof systems in the South region that have been affected by storm events, carry warranties older than 5 years, and are target opportunities for our certified contractor network."*

```
     ┌────────────────────────────────────────────────────────┐
     │                  USER INPUT RAW QUERY                  │
     │     (MATCH (s:SYSTEM)-[r]->(c) RETURN s, r, c)         │
     └───────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
     ┌────────────────────────────────────────────────────────┐
     │              LEXER, PARSER & AST BUILDER               │
     │      (Validates query syntax & builds logical tree)     │
     └───────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
     ┌────────────────────────────────────────────────────────┐
     │                TENANT SECURITY SANDBOX                 │
     │      (Injects mandatory tenant_id scope checks)        │
     └───────────────────────────┬────────────────────────────┘
                                 │
                                 ▼
     ┌────────────────────────────────────────────────────────┐
     │               LOGICAL QUERY OPTIMIZER                  │
     │ (Selects cheapest starting node via indexed attributes) │
     └───────────────────────────┬────────────────────────────┘
                                 │
                    ┌────────────┴────────────┐
                    ▼ (Cache Hit)             ▼ (Cache Miss)
       ┌────────────────────────┐    ┌────────────────────────┐
       │   REDIS CACHE LOOKUP   │    │  TOPOLOGY SEARCH CORES │
       │ (Instant return state) │    │  (BFS/DFS Execution)   │
       └────────────────────────┘    └──────────┬─────────────┘
                                                │
                                                ▼
                                     ┌────────────────────────┐
                                     │  HYBRID DATA MERGING   │
                                     │ (Merges MongoDB node   │
                                     │ properties with edges) │
                                     └──────────┬─────────────┘
                                                │
                                                ▼
                                     ┌────────────────────────┐
                                     │      RETURN ROWSET     │
                                     └────────────────────────┘
```

---

## 2. Traversal Algorithms

The GQE implements customized, in-memory traversal algorithms optimized for dense building assembly relationships.

### A. Breath-First Search (BFS) / Depth-First Search (DFS)
* **Point-to-Point Reachability:** Used to determine if a relationship chain exists between two nodes (e.g. is this Photo verified evidence for a Warranty).
* **Search Depth Limiting:** All traversals carry a mandatory `depth_limit` parameter (defaults to `3`, strictly capped at `5`) to prevent runaway infinite-loop traversals.

### B. Dijkstra / Pathfinding (Risk Propagation)
* **Shortest Path Determination:** Identifies the shortest chain of accountability between an issue and a certified contractor.
* **Weighted Edge Traversal:** Edges are weighted by their inverse confidence scores:
  $$\text{Weight} = \frac{1}{\text{Confidence}}$$
  Dijkstra’s algorithm finds the path of *maximum confidence* by minimizing total path weight.

---

## 3. Performance Optimizations & Caching

Graph operations can quickly become computationally expensive. The GQE applies two primary optimization patterns:

### A. Index-Backed Seed Node Resolution
Before traversing edges, the query optimizer selects the most restrictive index to locate the starting (seed) nodes.
* **Nodes Index:** `{ tenant_id: 1, node_type: 1, "properties.system_type": 1 }`
* **Edges Index:** `{ tenant_id: 1, from_node_id: 1, type: 1 }` and `{ tenant_id: 1, to_node_id: 1, type: 1 }`

### B. Two-Tiered Redis Cache Strategy
1. **Edge Topology Cache:** Stores the lightweight node adjacency lists (edge maps) in Redis as compressed JSON structures, keyed by `graph:topo:<property_id>`. This allows the traversal algorithm to map routes in sub-millisecond speeds.
2. **Node Properties Cache:** Stores rich node attribute payloads, keyed by `graph:node:<node_id>`, utilizing a standard hash-set format (`HGETALL`).

---

## 4. Tenant Security Sandboxing

Since Stratex operates in a multi-tenant enterprise landscape, preventing cross-tenant leakage within graph traversals is a **CRITICAL** requirement.

```python
def enforce_tenant_sandbox(logical_ast: dict, context_tenant_id: str) -> dict:
    """
    Rewrites the compiled AST to inject mandatory tenant_id filters 
    on every node and relationship pattern lookup.
    """
    for match_pattern in logical_ast.get("match_patterns", []):
        # Inject tenant restriction directly into Node and Edge filter maps
        match_pattern["node_filters"]["tenant_id"] = context_tenant_id
        
        if "edge_filters" in match_pattern:
            match_pattern["edge_filters"]["tenant_id"] = context_tenant_id
            
    return logical_ast
```

### Safety Invariants
1. **AST Injection:** The query compiler rejects any query that contains hardcoded `tenant_id` parameters or tries to bypass the context tenant.
2. **Memory Exhaustion Safeguard:** During query execution, the GQE tracks memory allocation. If a single traversal evaluates more than `10,000` nodes, the execution context is instantly aborted, and a `GRAPH_COMPUTATION_LIMIT_EXCEEDED` exception is thrown.

---

## 5. Quantitative Analytics & Path Metrics

The GQE provides built-in analytics aggregators to evaluate complex structural state and opportunity qualification.

### A. Graph Risk Scoring Formula
The structural risk score ($R_s$) of a system propagates from connected environmental threat events (Timeline Events) and age decay factors:

$$R_s = \min\left(1.0, \sum (T_{severity} \times C_{edge}) + \frac{\text{Current Age}}{\text{Expected Lifespan}}\right)$$

Where:
* $T_{severity}$ is the normalized intensity of a storm or weather event node (0.0 to 1.0).
* $C_{edge}$ is the confidence score of the `AFFECTED_BY` edge connecting the storm to the system.

### B. Lead Qualification Pipeline
When a severe weather event (e.g. `TIMELINE_EVENT` Category 2 Storm) is logged, the GQE triggers an analytics query:
1. Traverse `AFFECTED_BY` edges to identify affected `SYSTEM` nodes.
2. Filter for roofs whose connected `MATERIAL` nodes have expected lifespans exceeding current age by less than 5 years.
3. Traverse `COVERED_BY` links to check if warranties have expired or are nearing expiry.
4. If qualified, register a `PROJECT_OPPORTUNITY` node connected to the system, with a lead score matching the calculated risk level.
