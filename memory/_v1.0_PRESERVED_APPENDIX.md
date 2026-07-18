# STRATEX CORE — NEXTGEN ARCHITECTURE REVIEW APPENDIX
**Companion document to NEXTGEN_ARCHITECTURE_BLUEPRINT.md v1.0**
**Status**: Answering Executive Review Questions 1-14
**Author**: TC · Stratex AI Product Manager, under directive of Anthony Cross
**Purpose**: Detailed responses to executive architecture review questions issued during the Blueprint hold.

---

## Q1 — TWENTY-FOUR-AGENT ARCHITECTURE (justification)

### Correction of framing
The blueprint's "24 agents" is a **logical software role count**, not a deployable-service count. In production, these logical agents collapse into **5 deployable services** during early phases:

| Service | Logical agents inside | Deployment |
|---|---|---|
| **Mission Ops Service** | Mission Commander · Mission QA · Flight Operations · Mission Assurance · Capture Validation | 1 container, sync + background |
| **Vision Intelligence Service** | Photogrammetry · CAD/BIM · Digital Twin · Roof · Window · Door · Damage Detection · Measurement · Thermal Analysis | 1 container, GPU-optional, async job queue |
| **AWE Intelligence Service** | Water · Air · Energy | 1 container, async job queue |
| **Estimating Service** | Materials · Labor · Estimating · Maintenance Priority | 1 container, sync |
| **Delivery & Sync Service** | Reporting · Passport Sync · Habitat Sync | 1 container, sync + retry queue |

**Rationale**: separately deploying 24 microservices during the prototype phase would introduce
network complexity, deployment cost, and observability burden with no operational payoff.

### Per-agent detail table

| # | Agent | Responsibility | Inputs | Outputs | Model / Service | Logical vs deployed | Sync/Async | Human gate | Cost tier |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Mission Commander | Compose + validate mission plan | property_id, target_systems | mission_plan.json | Claude Sonnet + rule engine | Logical inside Mission Ops | Sync | Yes (dispatcher) | Low |
| 2 | Mission QA | Enforce 20-item preflight gate | mission_plan, drone_state, weather | gate_result{pass,fail,blockers[]} | Deterministic checks | Logical | Sync | No (all-or-nothing) | Free |
| 3 | Flight Operations | Live telemetry watch; safe-return decisions | telemetry stream | control_decisions[] | Rule engine | Logical | Async streaming | Escalates | Low |
| 4 | Mission Assurance | In-flight GSD/overlap QA | live imagery metadata | additional_shots[] | Statistical + Claude | Logical | Async streaming | No (auto-retake) | Low |
| 5 | Capture Validation | Radiometric integrity, RGB↔thermal registration | asset bundle | validation_report | Statistical + Claude | Logical | Async job | Yes | Low |
| 6 | Photogrammetry | Point cloud + mesh generation | RGB assets | .glb, .obj, point_cloud | **AWAITING INTEGRATION** (Pix4D / RealityCapture / OpenDroneMap) | Deployed later | Async job | Yes | High |
| 7 | Thermal Analysis | Radiometric anomaly detection | thermal R-JPG assets | thermal_findings[] | Statistical + Claude | Logical | Async job | Yes | Medium |
| 8 | CAD/BIM Generation | Structural layers, framing extraction | point cloud + mesh | .ifc, .rvt derivatives | **AWAITING INTEGRATION** (commercial) | Deployed later | Async job | Yes | High |
| 9 | Digital Twin | Fuse 3 layers into single twin | reality mesh + CAD + intelligence | twin manifest | Deterministic composition | Logical | Async | Yes | Low |
| 10 | Roof Intelligence | Plane, facet, damage classification | RGB + twin | roof_findings[] | Claude + CV heuristics | Logical | Async | Yes | Medium |
| 11 | Window Intelligence | Type, dimensions, glass, leakage | RGB + thermal + twin | window_findings[] | Claude + CV | Logical | Async | Yes | Medium |
| 12 | Door Intelligence | Type, material, seal condition | RGB + thermal + twin | door_findings[] | Claude + CV | Logical | Async | Yes | Medium |
| 13 | Water (AWE) | Moisture retention, water risk | thermal + roof geometry + weather history | water_findings[], water_score | Claude + rules | Logical inside AWE Service | Async | Yes | Medium |
| 14 | Air (AWE) | Ventilation performance | thermal + door/window findings | air_findings[], air_score | Claude + rules | Logical | Async | Yes | Medium |
| 15 | Energy (AWE) | Envelope performance, heat-loss score | thermal + envelope + weather | energy_findings[], energy_score | Claude + rules | Logical | Async | Yes | Medium |
| 16 | Damage Detection | Cross-system anomaly clustering | all findings[] | prioritized_damage[] | Claude | Logical | Async | Yes | Medium |
| 17 | Measurement Intelligence | Extract precise measurements from twin | twin + registration | measurements[] with tolerance | Deterministic geometry | Logical | Sync | Yes | Free |
| 18 | Materials Intelligence | Compose BOM | measurements + roof/window/door findings | bom[] | Catalog lookup + Claude | Logical inside Estimating | Sync | Yes | Low |
| 19 | Labor Intelligence | Compose labor plan | bom + regional rates | labor_plan | Catalog lookup + Claude | Logical | Sync | Yes | Low |
| 20 | Estimating Intelligence | Final estimate w/ waste, tax, O&P | bom + labor + preferences | estimate.json | Deterministic math | Logical | Sync | Yes | Free |
| 21 | Maintenance Priority | Rank issues by urgency + cost avoidance | all findings + estimate | priorities[] | Composite scoring | Logical | Sync | Yes | Free |
| 22 | Reporting Intelligence | Compose enterprise report | approved intelligence bundle | report.pdf + report.json | Template + Claude narrator | Logical inside Delivery | Sync | No (post-approval) | Low |
| 23 | Passport Sync | Emit ledger delta to Passport | approved bundle | sync receipt | Deterministic | Logical | Async + retry queue | No | Free |
| 24 | Habitat Sync | Emit homeowner packet to Habitat | approved bundle | sync receipt | Deterministic | Logical | Async + retry queue | No | Free |

### Combination rationale
Agents 13-15 (AWE) cannot be combined because Water, Air, and Energy each require distinct
input signals (weather history vs door/window vs envelope) and produce independently-reported scores.
Similarly, Roof/Window/Door intelligences cannot be combined because approval authority
differs (a contractor may approve roof findings but require an engineer for structural doors).

---

## Q2 — PROPERTY PASSPORT AUTHORITY

### Ownership model (definitive)

| Concern | Authority |
|---|---|
| **Creates Passport** | Stratex Passport service — issued via `POST /passport/v1/mint` with a nonce from Core |
| **Owns canonical identifier** | Stratex Passport service — 12-char uppercase hash, globally unique |
| **May append records** | **Stratex Passport service only.** Core submits deltas via `/passport/v1/append`; Passport service re-verifies chain integrity before writing |
| **May correct records** | Nobody. Records are immutable. Corrections are new appends with an explicit `supersedes` pointer to the prior record |
| **Versioned via** | Sequential ledger `seq` + SHA-256 chain (`prev_hash` field) — already implemented today for the native passport |
| **Findings superseded via** | New ledger entry of type `SUPERSEDE` carrying `prior_seq`, `reason`, and `superseding_finding_id`. Historical record is never destroyed |
| **Core submission path** | `POST /passport/v1/append {passport_id, delta_bundle, core_signature}` → Passport verifies + writes + returns cryptographic receipt |
| **Habitat receipt path** | `GET /passport/v1/projections/homeowner/:passport_id` — a read-only projection scoped to homeowner-appropriate fields |
| **Conflict resolution** | **First-writer-wins with per-property sequence numbers.** Concurrent appends fail with `409 SEQUENCE_CONFLICT`, forcing the loser to re-read and re-submit |
| **Cryptographic proof** | Every accepted append returns a SHA-256 receipt computed over `{payload, seq, prev_hash, signed_at}`. Core stores this receipt in its `sync_audit_log` |
| **Deployment** | **Standalone service** post-parity. Today it is embedded in `/app/backend/routes/passport.py` — this is the first module extracted in Phase 2 |

### Access-control matrix

| Actor | Read | Append | Correct | Habitat receive |
|---|---|---|---|---|
| Contractor (Core) | ✅ (their org's properties) | ✅ (approved bundles only) | ❌ | ❌ |
| Homeowner | ✅ (their property only, homeowner projection) | ❌ | ❌ | ✅ |
| Adjuster | ✅ (via magic link) | ✅ (cosign entries only — already exists) | ❌ | ❌ |
| Passport service itself | ✅ | ✅ (all writes go through it) | ✅ (via SUPERSEDE semantics) | — |
| Habitat service | ❌ direct | ❌ | ❌ | ✅ pull only |

### Existing Claim Snapshot cosign receipt pattern (§8 blueprint) is the canonical template for how every future append works.

---

## Q3 — PROVENANCE INTERFACE

### Visual-noise avoidance rules

**Always visible (chip in-line)** — applies to high-consequence numbers only:
- Envelope Score
- Moisture %
- Repair Estimate $
- AWE™ scores (Air, Water, Energy)
- Truth Score
- Confidence %

**Progressive disclosure** — for supporting values:
- Every measurement (dimension, count, area) shows a small colored dot only
- Tap / hover reveals a hover-card with the full provenance object
- "Open Evidence" button in the hover-card drops into an Evidence Drawer

**Mobile behavior**:
- Chips shrink to a single colored dot (4px) on ≤430 px viewports
- Long-press opens the provenance drawer (not hover)
- Drawer takes 90% of screen height, dismissible with swipe-down

**Evidence Drawer contents**:
- Source asset thumbnail (with a "view full size" affordance)
- Model + version + prompt version
- Confidence, timestamp, signer (if human-approved)
- "Reject / Escalate" affordance if the user has QA role

### Provenance vs Confidence vs Truth Score (clarified)

| Concept | Question it answers |
|---|---|
| **Provenance** | *Where did this value come from?* — Source lineage |
| **Confidence** | *How sure is the model / measurement?* — Per-agent numeric or human-verified |
| **Finding confidence** | Aggregate confidence across all inputs for a single finding |
| **Truth Score** | *How trustworthy is this entire property record?* — See Q4 |

---

## Q4 — TRUTH SCORE (honest specification)

### Definition (revised, non-marketing)
Truth Score is a **composite property-record trust indicator**, expressed on a 0-100 scale in **10-point bands** (never in decimal form) with descriptive language:

| Band | Language |
|---|---|
| 90-100 | **Field-verified · production-grade** |
| 70-89 | **AI-assisted · human-approved** |
| 50-69 | **AI-assisted · pending human review** |
| 30-49 | **Partial coverage** |
| 0-29 | **Insufficient evidence** |

### Component inputs
1. **Evidence coverage** (0-30 pts) — fraction of expected asset types present (RGB, thermal, dimensional)
2. **Model confidence average** (0-25 pts) — mean confidence of all findings
3. **Human verification ratio** (0-25 pts) — % of findings signed by human QA
4. **Recency** (0-10 pts) — age of freshest scan
5. **Cross-registration** (0-10 pts) — RGB↔thermal alignment score (if AWE performed)

### Weighting
Deterministic weighted sum with published coefficients — never a model output.

### Missing-evidence behavior
Missing evidence subtracts from Evidence Coverage. Never treated as "confident zero."

### Contradictory-evidence behavior
Contradictions between two findings trigger a **CONTRADICTION** event that:
- caps Truth Score at 60 until reconciled
- surfaces both findings to the Human QA queue

### Human verification effect
Each human-approved finding contributes to the Human Verification Ratio component. A property with 100% human approval on all findings can reach the 90-100 band.

### Versioning
Truth Score has its own version number (e.g. `TS.v1.0`). Historical scores are frozen in the passport ledger.

### Calibration
Requires empirical field-verification runs against ground truth before we publish the score externally. Until then, the score is displayed with the label **"Prototype scoring — not calibrated to industry standard yet."**

### Display language rules
- **Prohibited**: "97.43%," "99.7% accurate," "AI-verified truth."
- **Required**: 10-point band + descriptive label + provenance chip

### Marketing restrictions
- Truth Score may **not** be presented to insurance carriers or in contracts as a warranty of accuracy until calibration is published.
- May be presented **only** as a "record-completeness signal" during the prototype phase.

### The four levels distinguished
| Level | Scope |
|---|---|
| Model confidence | Per-inference (one AI call) |
| Measurement confidence | Per-measurement (one dimension) |
| Finding confidence | Per-finding (composite of contributing model + measurement confidences) |
| **Truth Score** | Per-property record (composite of all findings + coverage + verification) |

---

## Q5 — AWE™ MISSION SEPARATION

### Recognized: AWE requires a separate mission

The blueprint is amended: AWE™ is **not a processing toggle on daytime imagery**. Three explicit mission products exist:

### Product 1 · **Stratex Core DayScan™**
- **When**: daytime, dry conditions
- **Captures**: RGB imagery only
- **Produces**: measurements, roof/exterior geometry, damage imagery, Digital Twin (Reality + CAD layers), material quantities, DayScan report
- **Updates**: Property Passport DayScan chain

### Product 2 · **Stratex AWE™ Scan**
- **When**: nighttime, only when environmental eligibility passes:
  - ΔT between indoor and outdoor ≥ 15°F (configurable per region)
  - No rain within last 4 hours
  - Wind < 15 mph
  - Humidity < 80%
  - No direct solar loading (≥1 hour past sunset)
- **Captures**: radiometric thermal + reference RGB
- **Produces**: Air / Water / Energy findings with false-positive controls (moisture-mimic exclusion, ventilation-shadow rejection)
- **Requires**: field verification for any finding above a materiality threshold before Passport entry
- **Updates**: Property Passport AWE chain

### Product 3 · **Stratex Elite™ Property Intelligence**
- Combines DayScan + AWE Scan (with cross-registration between RGB and thermal datasets)
- Produces unified evidence graph, combined report, **AWE Index™** (composite Air/Water/Energy)
- Updates Property Passport with a single approved bundle referencing both scan hashes

### Mission planner enforcement
The Mission Planner (§3 blueprint) must present the operator with a **product selector** as the first step: DayScan vs AWE Scan vs Elite. The 20-item ATC gate then loads the product-specific validation subset.

---

## Q6 — DIGITAL TWIN ARCHITECTURE

### Canonical decisions

| Concern | Decision |
|---|---|
| **Coordinate system** | WGS84 lat/lon + local ENU (East-North-Up) origin per property; twin is stored in local ENU with a lat/lon origin pin |
| **Geometry source** | Photogrammetry point cloud + mesh (from RGB) — **AWAITING INTEGRATION** |
| **RGB texture source** | DayScan RGB assets |
| **Thermal-to-RGB registration** | Feature-based homography per capture; per-pixel registration confidence stored |
| **Layer manifest** | JSON manifest listing each layer (Reality, CAD, Intelligence) with URIs, hashes, version |
| **Formats** | Storage: glTF 2.0 (`.glb`) canonical; IFC 4 and DXF for CAD; PLY for point clouds; radiometric TIFF for thermal source |
| **Measurement provenance** | Every extracted measurement carries `derived_from: [asset_ids]` + tolerance ± value |
| **Level-of-detail** | glTF LOD hierarchy: L0 (full), L1 (medium), L2 (mobile); browser streams L2 by default, promotes to L0 on zoom |
| **Version comparison** | Two twin versions can be diffed; findings that shift receive a `DIFF` event |
| **Browser streaming** | glTF over HTTPS with Draco compression + KTX2 textures |
| **Mobile performance** | L2 mesh + 1k textures target < 20 MB total; renders on iPhone 12 and later at 60 fps |
| **Vendor-neutral storage** | S3-compatible object storage. No vendor-specific format inside the canonical bundle |
| **Exportability** | Every twin can be exported as `.glb` + `.ifc` + `.dxf` bundle to a customer download link |
| **External processor replacement** | Photogrammetry, CAD/BIM, and radiometric processing are all **adapter contracts**. Concrete provider (Pix4D, RealityCapture, OpenDroneMap) is swappable without changing Core |

### Stratex-owned vs external-processor-owned

**Stratex owns forever**:
- Mission package (plan, waypoints, targets)
- Evidence graph (which asset produced which finding)
- Findings + approvals + Passport records
- The layer manifest and its version history
- Signed measurement provenance

**External processors own only** the raw mesh/CAD generation step and are treated as replaceable adapters behind a `PhotogrammetryProvider` / `BimProvider` interface.

---

## Q7 — DATA-STATE HONESTY

### Adopted implementation-state vocabulary

Every feature, integration, and displayed value shall carry exactly one of:

| State | Meaning |
|---|---|
| **Operational** | Live end-to-end in production, verified by tests |
| **Partially operational** | Some flows live, others use fallback or fixtures — clearly labeled which |
| **Mocked** | Fixture data; nothing real behind it |
| **Planned** | Design complete, not built |
| **Awaiting credentials** | Built but requires API key / license not yet obtained |
| **Awaiting hardware** | Built but requires drone / sensor / dock not yet on hand |
| **Awaiting validation** | Built but requires field calibration before trust |
| **Deprecated** | Phasing out; do not use for new work |
| **Legacy** | Frozen, read-only, under `/legacy/*` |

### Marketing rules

- No screen may claim "operational" for a component that is any other state
- The UI shall render each state with a distinct chip color and label
- Reports shall footer with a state summary of every value in the document

---

## Q8 — EXISTING ASSET PRESERVATION MAP

| Asset | Decision | Rationale |
|---|---|---|
| Official Stratex branding (logo, colors, typography) | **Preserve unchanged** | Approved; carried into NextGen shell |
| Property Passport ledger (hash-chained) | **Preserve unchanged**, migrate storage to `passport_ledger` collection with Pydantic model | Working crypto — do not touch the algorithm |
| Claim Snapshot engine | **Refactor** into `findings` + specialized `claim_snapshot` view; keep public API | Genuine value; needs normalized storage |
| Adjuster co-sign SHA-256 receipt | **Preserve** as the canonical template for all future human sign-offs | Generalize the pattern to every Human QA event |
| Open-Meteo weather integration | **Preserve unchanged**; extract into `WeatherProvider` adapter | Simple, working, free |
| Live Ops WebSocket bus | **Refactor** onto formal event bus (§7 blueprint); keep client contract | WS is fine; server logic needs event log |
| PDF / Report pipeline (Playwright + cache-first) | **Preserve**; graduate to Report Studio in Delivery Service | Production-safe already |
| Reports Binder (PyMuPDF) | **Preserve** as embedded viewer in Report Studio | Works |
| Existing authentication (JWT + bcrypt, CEO login) | **Refactor** — extract to Identity Service, expand to full RBAC | Foundation good; scope must grow |
| Existing authorization | **Refactor** — introduce `require_auth` + `require_org` on all product routes | Critical gap today |
| Service credentials / HMAC patterns | **Preserve** patterns; regenerate secrets on each service split | Reusable |
| Existing Core → Passport → Habitat contracts | **Migrate** — Passport becomes standalone; Habitat contract is new | Formalized in Q2 |
| Existing test suites (`test_iter17_new_features.py` … `test_iter21_cosign.py`) | **Preserve** as legacy regression harness; add NextGen suite alongside | Keep the safety net |
| Static illustrations in `/twin/*` and `_binder_cache/*` | **Retire** once real twin renders exist, but keep for the interim label as `DEMO DATA` | Cannot be shown as real intelligence |
| `_sample_analysis()` hardcoded fixture | **Retire** — replaced by the AI Workforce pipeline | Explicit deletion at Phase 3 |

**Nothing is deleted through omission.** Every asset is accounted for.

---

## Q9 — SECURITY SCOPE (phased introduction)

### Phase 1 (Foundation)
- **Initial roles**: `admin`, `contractor`, `pilot`, `inspector`, `homeowner`, `adjuster`
- **Initial permissions**: read/write/approve/sign
- **Organization isolation**: `org_id` required on every mutable resource; enforced in query builder
- **Property-level access**: `property_org_bindings` table; contractors see only their org's properties
- **Contractor access**: read all properties in their org, write findings after inspector approval
- **Homeowner access**: read-only projection of their property only
- **Pilot / operator access**: read mission plans, write telemetry + capture assets
- **Administrator access**: full within their org; cross-org requires service token
- **Engineer/adjuster reviewer access**: read + sign findings/reports via magic-link tokens (existing cosign pattern)

### Service-to-service authorization
- mTLS between Core ↔ Passport ↔ Habitat (Phase 2+)
- Short-lived service tokens with per-endpoint scopes

### Audit logging
- Every mutation → `audit_events` (actor, action, resource, before, after)
- Retention: 2 years hot, 7 years cold storage — **AWAITING INTEGRATION**

### Secrets management
- All secrets in `.env` today
- Move to Emergent-managed secret store or HashiCorp Vault (Phase 5)

### Rate limiting
- Per-user + per-IP token buckets on all public endpoints
- Passport, cosign, storm APIs: 60 req/min per IP; 300 per authenticated user

### File access
- All object-storage assets served via **signed URLs** with expiry (default 5 min)
- Signed uploads via presigned POST
- Every download logged to `asset_provenance`

### Explicit Phase 1 stops
- No SSO in Phase 1
- No field-level encryption in Phase 1 (Phase 3)
- No SIEM in Phase 1 (Phase 5)

---

## Q10 — DATABASE-DOMAIN JUSTIFICATION

**Correction**: the 10 domains described in §4 of the blueprint are **logical modules**, not 10 separate databases. During prototype and MVP phases, all 10 domains live inside a **single MongoDB database** with strict per-collection schemas and boundaries enforced at the application layer.

### Per-domain table

| Domain | Purpose | Core entities | Ownership boundary | Transactions | Retention | Sensitivity | Separate DB? |
|---|---|---|---|---|---|---|---|
| Identity & Access | Auth + RBAC + audit | orgs, users, roles, api_keys, audit_events | Identity Service | ACID-lite (Mongo multi-doc tx) | 7 yrs (audit) | HIGH (PII) | No — logical only |
| Property Registry | Canonical property record | properties, addresses, parcels, owners, contractors | Property Service | Multi-doc tx on write | Permanent | MEDIUM (PII) | No |
| Mission Operations | Mission lifecycle | missions, mission_plans, mission_validations, mission_telemetry, capture_sessions | Mission Ops Service | Sequential per mission | 3 yrs | LOW-MEDIUM | No |
| Capture Assets | Binary asset metadata (binary in S3) | assets, asset_derivatives, asset_provenance | Vision Service | Metadata only | 7 yrs (bodies in S3) | MEDIUM | No (metadata) / Yes (S3 binaries) |
| Intelligence Findings | AI + human findings | findings, finding_evidence, finding_confidence, agent_runs | Vision + AWE + Estimating Services | Append-only ledger-like | Permanent | MEDIUM | No |
| AWE™ Metrics | AWE readings + scores | awe_readings, awe_scores, awe_history | AWE Service | Sequential per property | Permanent | LOW | No |
| Estimating | Materials + labor + estimates | materials_catalog, labor_catalog, estimates, estimate_versions | Estimating Service | Versioned; last-write-wins | Permanent | LOW-MEDIUM (business) | No |
| Reports & Deliverables | Rendered reports | report_templates, reports, report_versions, report_signatures | Delivery Service | Sequential | Permanent | LOW | No |
| Passport & Habitat Sync | Sync audit + queue | passport_ledger, passport_sync_log, habitat_sync_log, sync_retry_queue | Passport Service | Ledger append + idempotent queue | Permanent | HIGH (cryptographic) | **Yes** — Passport becomes standalone in Phase 2 |
| Compliance & Observability | Provenance, events, cost | provenance_chain, event_log, error_events, cost_ledger | Platform | Append-only | 2 yrs hot | LOW | No |

**Only the Passport domain justifies extraction into a separate database (Phase 2)** — because its records are the immutable source of truth for all downstream systems. Everything else remains logical modules inside the primary Mongo database until scale demands otherwise.

---

## Q11 — API-PLANE JUSTIFICATION

**Correction**: the 5 planes are **logical route-prefix conventions with distinct middleware chains**, not 5 separate network services. All planes run inside the same FastAPI app initially; some may split later.

### Per-plane table

| Plane | Prefix | Consumers | Auth | Authz | Versioning | Rate limits | Errors | Idempotency | Audit | Network boundary? |
|---|---|---|---|---|---|---|---|---|---|---|
| **Public Read** | `/api/pub/v1/` | Anonymous (via passport hash) | Signed URL / hash | Resource-level | URL versioned | 60/min/IP | RFC 7807 JSON | GET only | Read log to `audit_events` | No (same process, edge-cacheable) |
| **Product** | `/api/v1/` | Authenticated users | JWT | RBAC + ABAC (org, property, role) | URL versioned | 300/min/user | RFC 7807 | Idempotency-Key header on POST/PUT | Full audit | No (same process) |
| **Agent** | `/api/agents/v1/` | Backend agent runners | Service token | Scope-per-endpoint | URL versioned | Internal only | RFC 7807 | Idempotency-Key required | agent_runs table | **Yes** — internal network only, blocked at ingress |
| **Sync** | `/api/sync/v1/` | Passport, Habitat services | mTLS + service token | Service allow-list | URL versioned | Bounded by queue depth | RFC 7807 + retry semantics | Idempotency-Key required | Full audit | **Yes** (Phase 2+) |
| **Webhook** | `/api/hooks/v1/` | External inbound (DJI, FAA, weather) | HMAC signature | Provider allow-list | URL versioned | Provider quotas | 202 on accept, HMAC failure → 401 | Idempotency by event id | Full audit | No (same process) |

**Actual network boundaries introduced only where necessary** — Agent and Sync are gated at the ingress layer. Everything else is logical.

---

## Q12 — EVENT-DRIVEN ARCHITECTURE (Phase 1 events only)

### Phase 1 minimum viable event set

Only these events are wired in Phase 1. All others are deferred until real workflows demand them.

| Event | Producer | Consumer | Payload | Idempotency key | Retry | Failure | DLQ | Audit | Sync alternative? |
|---|---|---|---|---|---|---|---|---|---|
| `mission.planned` | Mission Ops | Mission Validation | mission_id, plan | mission_id | 3× exp backoff | Log + surface in Mission Ops UI | Yes | audit_events + event_log | Sync is fine; keep async |
| `mission.validated` | Mission Validation | Mission Ops (unlock launch) | mission_id, pass/fail, gate_details | mission_id | none | Block launch | No | audit_events | Sync (immediate) |
| `capture.received` | Vision (adapter) | Vision Service | mission_id, asset_bundle_id | asset_bundle_id | 3× | Escalate to Human QA | Yes | audit_events + event_log | Async needed (large uploads) |
| `finding.produced` | Any AI agent | Human QA | finding_id, agent_id, confidence | finding_id | none | Halt Passport append | No | agent_runs | Sync (blocks Passport) |
| `finding.approved` | Human QA | Passport Sync | finding_id, signer, receipt | finding_id | none | Halt sync | No | audit_events | Sync (blocks sync) |
| `passport.appended` | Passport Service | Habitat Sync | passport_id, seq, receipt_hash | (passport_id, seq) | 3× | sync_retry_queue | Yes | passport_sync_log | Async (external system) |
| `habitat.received` | Habitat (webhook back) | Passport Sync | passport_id, seq, ack | (passport_id, seq) | — | Alert ops | Yes | habitat_sync_log | Async (ack) |

**No full event-bus infrastructure in Phase 1.** These events are recorded in `event_log` and dispatched via in-process async tasks (FastAPI background tasks). If cross-service messaging becomes necessary in Phase 2+, we upgrade to a proper broker (NATS or Redis Streams) — not before.

---

## Q13 — TECHNOLOGY DECISIONS (justified)

| Tech | Problem solved | Why existing is insufficient | Adoption cost | Migration risk | Simpler alternative | Necessary in phase |
|---|---|---|---|---|---|---|
| **React Query** | Server-state caching, retries, background refresh, optimistic UI | Current app uses ad-hoc `useEffect` + `fetch`; race conditions and stale data are already visible | Low (drop-in; ~1 day) | Low (per-page adoption) | Continue with useEffect (rejected — bugs) | Phase 1b |
| **Zustand** | Small global UI state (e.g. current mission, active twin layer) | React Context works but rerenders too much | Very low | None | Redux (too heavy); Context (already present) | Phase 1b |
| **Event-driven backbone** | Decoupling AI pipeline stages | Current code is deeply coupled (`storm_watcher` reaches into passport internals) | Medium | Medium | Sync in-process only (acceptable in Phase 1) | **Deferred to Phase 2** |
| **Blue/green deployment** | Zero-downtime cutovers | Emergent single-container deploys create brief unavailability | Low (Emergent may not support natively) | Low | Just rollback via checkpoint (fine for now) | **Deferred to Phase 5** |
| **Feature flags** | Ship stubs safely, control AWAITING INTEGRATION states | Currently commenting out code | Low (implement in-house) | None | Env vars (works but less granular) | Phase 1b (in-house key-value flag) |
| **Cryptographic receipts** | Prove what was submitted / approved | Already implemented (cosign) — extend the pattern | Free (already exists) | None | (already chosen) | Phase 1 (existing) |
| **RBAC** | Role-based access control | Current app has none on product routes | Medium (~1 week) | Medium (retrofit every route) | ACLs only (too rigid) | Phase 1 mandatory |
| **ABAC overlay** | Property/org-level access rules | RBAC alone can't gate by `property_org_binding` | Low on top of RBAC | Low | RBAC-only (rejected — leaks data) | Phase 2 |

### Rejected in this round
- **Kubernetes multi-cluster**: unjustified until scale demands
- **Kafka**: overkill; NATS/Redis Streams sufficient when we need a broker
- **GraphQL**: REST + tight schemas is sufficient
- **Rust rewrite of any component**: no
- **Any new frontend framework**: React is the standard here

---

## Q14 — PHASE 1 SCOPE CONTROL (explicit)

Phase 1 **creates the architecture and operating shell** but delivers **no finished production intelligence engines**.

### Phase 1 SHALL establish (deliverable list)

1. Application boundaries (Production / NextGen / Legacy)
2. Navigation (14 modules, canonical routes)
3. Workflow state machine (14-stage mandatory chain)
4. Mission shell (Mission Ops workspace stubs)
5. Property shell (Property Portfolio + Property Detail with tabs)
6. Evidence schema (asset ↔ finding ↔ approval)
7. Provenance schema (chip component + backing data model)
8. Agent-run audit schema (`agent_runs` collection)
9. Passport contract (Q2 above)
10. Habitat synchronization contract (§8 blueprint + Q2)
11. Digital Twin layer contract (Q6)
12. AWE mission contract (Q5)
13. Design-system foundation (tokens, provenance chip, module frame)
14. Security foundation (RBAC skeleton, `require_auth` middleware)
15. Test strategy (regression harness plan)

### Phase 1 SHALL NOT claim to deliver

- Production-ready photogrammetry
- Production-ready thermal diagnosis
- Automated CAD/BIM generation
- Field-validated AWE conclusions
- Automated damage classification with contract-grade accuracy
- Any measurement presented as production-truth without human sign-off

**Every screen in Phase 1 delivering intelligence content shall wear one of these labels:**
`DEMO DATA · MOCKED · AWAITING INTEGRATION · AWAITING HARDWARE · AWAITING VALIDATION`.

### Success criteria (Phase 1 exit gate)
- All 14 items above delivered
- Blueprint + Appendix + Executive Review signed off
- Screenshots of every workspace captured on desktop + mobile
- Regression suite green
- Zero fabricated intelligence displayed in the shell

---

## APPENDIX — REVISION HISTORY

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0 | Feb 26, 2026 | TC | Initial draft of NextGen Architecture Blueprint (623 lines) |
| 1.0-app | Feb 26, 2026 | TC | Review Appendix v1.0 answering Executive Review Questions 1-14 |

**End of Review Appendix.**
