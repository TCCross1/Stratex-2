# EXPLAINER PERFORMANCE BENCHMARKS
## CENTCOM DIRECTIVE 016 · OPERATION EXPLAINER VALIDATION™ (v1.0)
**Prepared by:** General Atlas & The Stratex-2 Executive Committee  
**Status:** APPROVED / OPERATIONAL  
**Classification:** CORE + PROPERTY PASSPORT (EXECUTIVE PRIORITY)  

---

## 1. Scope & SLA Targets

To ensure the Stratex-2 universal explanation layer operates fluidly under tactical demand, we establish performance targets for both read-heavy retrieval endpoints and write-heavy generation pipelines. 

All metrics are measured under simulated multi-tenant loads representing standard operational conditions.

---

## 2. Performance SLA Targets & KPIs

The system must satisfy the following latency and error rate criteria:

| SLA ID | Operational Target | P50 Latency | P95 Latency | P99 Latency | Max Error Rate | Max Timeout Rate |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **PB-01** | **Single Explanation Retrieval** | < 15 ms | < 45 ms | < 100 ms | < 0.01% | < 0.05% |
| **PB-02** | **Property-Wide Explanation (12 Domains)** | < 40 ms | < 120 ms | < 250 ms | < 0.05% | < 0.10% |
| **PB-03** | **Multi-Domain Explanation Generation (AI)** | < 1.2 s | < 2.5 s | < 4.0 s | < 1.00% | < 2.00% |
| **PB-04** | **Complete Evidence Trace Retrieval** | < 20 ms | < 60 ms | < 150 ms | < 0.01% | < 0.05% |
| **PB-05** | **Regeneration after Passport Update** | < 150 ms | < 450 ms | < 900 ms | < 0.10% | < 0.20% |
| **PB-06** | **Cache Hit Latency** | < 2 ms | < 5 ms | < 12 ms | < 0.00% | < 0.00% |
| **PB-07** | **Cache Miss Latency (Direct DB Read)** | < 18 ms | < 50 ms | < 110 ms | < 0.05% | < 0.10% |
| **PB-08** | **Concurrent Tenant Requests (100 Users)** | < 80 ms | < 220 ms | < 500 ms | < 0.10% | < 0.30% |
| **PB-09** | **Large Knowledge Graph Traversal** | < 35 ms | < 95 ms | < 180 ms | < 0.05% | < 0.10% |

---

## 3. Key Metrics Definitions

### A. Latency Percentiles (P50, P95, P99)
- **P50 (Median):** 50% of requests must complete faster than this duration. Indicates normal system performance.
- **P95:** 95% of requests must complete faster than this duration. Represents typical worst-case user experience.
- **P99:** 99% of requests must complete faster than this duration. Reveals edge-case behavior and system bottlenecks.

### B. Error & Timeout Rate
- **Error Rate:** The percentage of requests resulting in a HTTP 5xx server error.
- **Timeout Rate:** The percentage of requests failing to complete within the 10-second gateway threshold.

### C. Cache Effectiveness
- **Target Cache Hit Rate:** $\ge 85\%$ for read-heavy public endpoints (e.g. Habitat projections).
- **Target Cache Invalidation Latency:** $< 200\text{ ms}$ following a new approved finding or reviewer override.

### D. Trace Completeness
- **Completeness Target:** Exactly $100\%$. Under no circumstances may an explanation retrieve without all 8 mandatory trace elements.

### E. Generation Cost
- **SLA Ceiling:** $<\$0.012$ per explanation generation pass (based on token ingestion/output rates of standard models).

---

## 4. Load Testing & Benchmarking Tooling

The performance suite executes simulated traffic using standard load-testing tools:

```bash
# Executing direct single retrieval load test
locust -f tests/load/locust_explainer.py \
  --host="http://localhost:8000" \
  --users=1000 \
  --spawn-rate=50 \
  --run-time=10m
```

The load-testing harness simulates active tenant boundaries, ensuring that parallel traffic across Tenant A and Tenant B does not cause database connection pooling exhaustion or cache eviction conflicts. If P99 latency spikes above 500ms under load, the test fails, indicating a need for index adjustments on the `property_id` and `tenant_id` fields in MongoDB.
