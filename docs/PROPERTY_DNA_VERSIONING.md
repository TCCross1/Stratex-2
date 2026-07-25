# PROPERTY DNA VERSIONING SPECIFICATION (v1.0)
## CENTCOM DIRECTIVE 011 · OPERATION PROPERTY DNA
**Status:** STANDARD ADOPTED  
**Scope:** Schema migrations, API versioning paths, and consumer backward compatibility.

---

## 1. Multi-Tier Versioning Architecture

To support continuous evolution under Rule #2 without causing broken dependencies across downstream applications (Habitat, Reports, Contractors, or Insurance), the Property DNA Engine™ implements a strict multi-tier versioning hierarchy.

```
 ┌────────────────────────────────────────────────────────┐
 │                      API VERSION                       │
 │      (Exposed via pathing e.g., `/nextgen/v1/`)         │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                    DOCUMENT VERSION                    │
 │    (Document-level 'version' property increments +1)    │
 └───────────────────────────┬────────────────────────────┘
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │                      NODE VERSION                      │
 │     (Individual field history arrays increment v1->v2) │
 └────────────────────────────────────────────────────────┘
```

1.  **API Version:** Defines the contract of the endpoints (REST paths and schema structure).
2.  **Document Version:** Represents the chronological progression of the Property DNA record itself. Every change to any field increments this counter.
3.  **Node Version:** Tracks the historical lifecycle of a single data attribute.

---

## 2. Document-Level vs. Node-Level Versioning

The design differentiates clearly between global and local changes.

### A. Document-Level Versioning (`version` field)
*   The parent Property DNA document holds a `version` attribute (integer).
*   Any write sequence—whether automated via the pipeline or manual via an authorized update path—must atomically increment the parent `version` by `1` using MongoDB’s `$inc` operator.
*   This provides a global optimistic concurrency control (OCC) mechanism for consumer applications.

### B. Node-Level Versioning (`history` array)
*   Every schema property (e.g., `health.roofing`) is an object with a `history` array.
*   The first entry (initial seeding or first finding) is assigned `version: 1`.
*   Subsequent updates append an entry to the `history` array with `version: previous_version + 1`.
*   This ensures that the complete lineage, reviewers, confidence scores, and source evidence IDs of that specific attribute are preserved in chronological order.

---

## 3. Schema Evolution & Migration Strategy

As building technologies change, Stratex will inevitably need to add or refine schema attributes (such as introducing electric vehicle charging infrastructure, heat pumps, or advanced greywater recycling metrics).

### Schema Evolution Rules:
1.  **Additions are Non-breaking:** Adding new nested fields inside existing categories (e.g., adding `lifecycle.heat_pump` or `history.permit_history`) is allowed in patch updates. Since clients read DNA dynamically, new nodes are simply ignored by older clients until they are updated to render them.
2.  **Modifications Require API Path Deprecation:** Renaming or restructuring existing fields (e.g., flattening `identity` or splitting `awe` into separate sub-objects) requires a bump in the API version (e.g., from `/nextgen/v1/` to `/nextgen/v2/`).
3.  **Default Value Fallbacks:** All client-side SDKs and consuming applications must implement default safe values. If a field is missing or contains `null`, the consumer must treat it as `Unknown` and invoke the Null-provenance rendering guard.

---

## 4. API Deprecation & Retirement Policy

To ensure that legacy applications are not abruptly broken by schema changes, Stratex enforces a structured deprecation workflow:

1.  **Deprecation Announcement:** When a new API version (e.g., `/nextgen/v2`) is deployed, the legacy endpoint (`/nextgen/v1`) is marked as `deprecated` in the HTTP response headers:
    ```http
    Warning: 299 - "API version v1 is deprecated and will be removed on 2027-12-31."
    Deprecation: true
    ```
2.  **Sunset Phase:** The deprecated endpoint is maintained for a minimum of **12 months** from the release date of the new version.
3.  **Telemetry Auditing:** Traffic to the deprecated endpoint is continuously monitored. GMs and product managers receive weekly reports detailing any third-party contractors or internal services still invoking the legacy paths.
4.  **Complete Decommissioning:** Once telemetry reaches 0% utilization (or the 12-month window has elapsed), the endpoint is decommissioned, keeping the codebase clean and maintainable.
