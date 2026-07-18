# STRATEX CORE — NEXTGEN ARCHITECTURE BLUEPRINT
**Version**: 1.0 · **Status**: DRAFT · Awaiting Executive Approval
**Author**: TC · Stratex AI Product Manager · Under directive of Anthony Cross
**Directive Reference**: STRATEX CORE DIRECTIVE 001 — Legacy Freeze & NextGen Rebuild
**Design principle**: *Optimize for correctness of architecture, not speed of completion.*

---

## 0. EXECUTIVE FRAMING

Stratex Core NextGen is **not** a drone-inspection app.
It is the **Residential Property Intelligence Operating System** — an enterprise-grade
mission-control platform that orchestrates hardware, AI, human review, and permanent
data custody across three fused pillars:

| Pillar | Purpose |
|---|---|
| **Stratex Core** | Contractor operating system — mission, capture, intelligence, delivery |
| **Stratex Passport** | Permanent, hash-chained property intelligence record — the source of truth |
| **Stratex Habitat** | Homeowner-facing intelligence platform |

The drone is **one sensor among many**. The AI workforce performs the intelligence.
The Property Passport is the permanent source of truth. Habitat is the homeowner face.

**Mandatory architectural workflow — no module bypasses this chain:**

```
Mission Control → Mission Planning → Mission Validation → Flight →
Mission Assurance → Capture Validation → Digital Twin Generation →
AI Workforce Processing → Property Intelligence → AWE™ Intelligence →
Human QA → Report Generation → Property Passport Update →
Habitat Synchronization → Customer Delivery
```

---

## 1. APPLICATION STATE MODEL

Three formally separated states co-exist in the codebase:

| State | Location | Deploy target | Modifiable? | Purpose |
|---|---|---|---|---|
| **PRODUCTION** | `stratexdrone.com` | Frozen at last approved deploy | No — read-only | Customer-visible; unchanged during rebuild |
| **NEXTGEN** | `stratex-quant.preview.emergentagent.com` | Active dev | **Yes** — all new work | Rebuild target |
| **LEGACY** | `/legacy/*` namespace inside preview | Not deployable to prod | Read-only after freeze | Rollback, comparison, knowledge preservation |

### Migration rules — irreversible until parity
Legacy is **never deleted** until ALL of the following pass:
1. Replacement complete
2. QA passed
3. APIs migrated
4. Data migration verified
5. Passport sync verified
6. Habitat sync verified
7. Reports validated
8. Navigation validated
9. AI workflows validated
10. Regression suite passed

---

## 2. MODULE HIERARCHY

The NextGen platform is organized into **14 first-class modules** grouped under 4 layers.

### Layer I — Operations (mission execution)
1. **Mission Control** — command deck; live global state; alerts; fleet status
2. **Mission Planning** — waypoint design, mission templates, geofencing, altitude profiles
3. **Mission Validation** *(formerly Air Traffic Control)* — 20-item preflight hard gate; blocks launch on any failure
4. **Flight Operations** — live telemetry, breadcrumbs, in-air observability
5. **Mission Assurance** — in-flight QA agent; monitors capture density, GSD, overlap; requests additional shots before landing
6. **Capture Validation** — post-flight ingestion; radiometric integrity checks; RGB/thermal registration verification

### Layer II — Intelligence (data → insight)
7. **Digital Twin Studio** — 3-model workspace (Reality Capture · Engineering CAD/BIM · Property Intelligence)
8. **AI Workforce** — orchestration console for the ~20 specialized agents (see §5)
9. **Property Intelligence** — canonical property record view; systems (roof, walls, windows, doors, HVAC, ventilation)
10. **AWE™ Intelligence** *(new pillar)* — **A**ir · **W**ater · **E**nergy — cross-cutting environmental performance analytics
11. **Human QA** — review + approval console; every AI finding requires human sign-off before it enters the Passport

### Layer III — Delivery
12. **Report Studio** — configurable enterprise deliverables; every value carries provenance chip
13. **Property Passport** — immutable hash-chained ledger; native module today; extractable to standalone service in Phase 5
14. **Habitat Sync** — outbound sync of approved data to the homeowner platform

### Layer IV — Platform
- **Identity & Access** — auth, roles, org tenancy, audit
- **Integrations** — DJI, weather, FAA airspace, materials/labor DBs, payments
- **System Console** — health, keys, feature flags, sync queues

---

## 3. NAVIGATION HIERARCHY (canonical)

Single persistent operator shell. No hidden orphans.

```
┌─ MISSION CONTROL ─────────────────────────────────
│  · Overview
│  · Active Missions
│  · Alerts & Notifications
│  · Fleet Status
│
├─ PROPERTY PORTFOLIO ─────────────────────────────
│  · Properties (all)
│  · New Property
│  · Property Detail
│    ├─ Overview
│    ├─ Digital Twin
│    ├─ AWE™ Intelligence
│    ├─ Findings
│    ├─ Reports
│    ├─ Passport Ledger
│    └─ Timeline
│
├─ MISSIONS ────────────────────────────────────────
│  · Mission Planner
│  · Mission Validation (ATC)
│  · Flight Operations (live)
│  · Mission Assurance (in-flight QA)
│  · Capture Validation (post-flight)
│  · Mission History
│
├─ DIGITAL TWIN STUDIO ────────────────────────────
│  · Reality Capture Layer
│  · Engineering CAD/BIM Layer
│  · Property Intelligence Layer
│  · Layer Sync & Compare
│  · Historical Diff
│
├─ AI WORKFORCE ────────────────────────────────────
│  · Agent Registry
│  · Agent Runs (queue + history)
│  · Confidence & Evidence Console
│  · Prompt Version Manager
│  · Cost Ledger
│
├─ AWE™ INTELLIGENCE ──────────────────────────────
│  · Air (ventilation, air quality, leakage)
│  · Water (moisture, roof intrusion, wall retention)
│  · Energy (thermal, envelope, performance score)
│  · AWE Composite Score
│
├─ ESTIMATING ──────────────────────────────────────
│  · Materials Catalog
│  · Labor Catalog
│  · Regional Pricing
│  · National Pricing
│  · Contractor Custom Pricing
│  · Estimate Builder
│  · Estimate Versions
│
├─ REPORTING ───────────────────────────────────────
│  · Report Templates
│  · Report Studio (WYSIWYG)
│  · Delivered Reports
│  · Report Versions
│
├─ HUMAN QA ────────────────────────────────────────
│  · Approval Queue
│  · Rejection Log
│  · QA Audit Trail
│
├─ INTEGRATIONS ────────────────────────────────────
│  · Drone Fleet (DJI)
│  · Weather (Open-Meteo)
│  · Airspace (FAA · LAANC — AWAITING INTEGRATION)
│  · Materials/Labor DBs — AWAITING INTEGRATION
│  · Passport (native)
│  · Habitat (AWAITING INTEGRATION)
│
├─ SYSTEM ──────────────────────────────────────────
│  · Users & Roles
│  · Organizations & Tenants
│  · Security (keys, MFA, audit)
│  · Sync Queues & Health
│  · Feature Flags
│  · Settings
│
└─ LEGACY (hidden, read-only) ─────────────────────
   · /legacy/* — all pre-NextGen screens for reference
```

Every route below the top-level module MUST be reachable from the persistent left nav
OR from a canonical entity detail view. **No orphaned URLs.**

---

## 4. DATABASE DOMAINS

The current single-tenant, dict-based Mongo layer is replaced by **10 typed domains**, each
with Pydantic document models, `to_mongo() / from_mongo()` helpers, and enforced
`created_at / updated_at / created_by / org_id` audit fields.

### Domain 1 · Identity & Access
| Collection | Purpose |
|---|---|
| `orgs` | Multi-tenant root |
| `users` | Human accounts |
| `roles` | RBAC definitions |
| `sessions` | JWT session ledger |
| `api_keys` | Machine tokens |
| `audit_events` | Every mutation with actor + before/after |

### Domain 2 · Property Registry
| Collection | Purpose |
|---|---|
| `properties` | Canonical property record (parcel, address, geo) |
| `addresses` | Normalized street/city/state/zip |
| `parcels` | County-parcel linkage |
| `owners` | Legal + occupant ownership records |
| `contractors` | Contractor profiles (replaces scattered `_contractor` dicts) |
| `property_org_bindings` | Which orgs may access which properties |

### Domain 3 · Mission Operations
| Collection | Purpose |
|---|---|
| `missions` | Formal mission record |
| `mission_plans` | Waypoints, altitude, camera plans |
| `mission_validations` | ATC 20-item results |
| `mission_telemetry` | In-flight breadcrumbs |
| `capture_sessions` | Post-flight ingest records |

### Domain 4 · Capture Assets (object storage)
| Collection | Purpose |
|---|---|
| `assets` | Metadata for RGB, thermal, video, twin exports; body in S3-compatible store |
| `asset_derivatives` | Downsamples, PNG previews, cropped tiles |
| `asset_provenance` | Chain-of-custody per asset |

### Domain 5 · Intelligence Findings
| Collection | Purpose |
|---|---|
| `findings` | Every AI/human finding — one row per anomaly / measurement / classification |
| `finding_evidence` | Links to source assets + regions |
| `finding_confidence` | Model + confidence + version + provenance |
| `agent_runs` | Every AI invocation with input hash, output, cost, model version |

### Domain 6 · AWE™ Metrics
| Collection | Purpose |
|---|---|
| `awe_readings` | Per-inspection Air/Water/Energy readings |
| `awe_scores` | Composite AWE score per property/inspection |
| `awe_history` | Longitudinal AWE trend per property |

### Domain 7 · Estimating
| Collection | Purpose |
|---|---|
| `materials_catalog` | SKU, unit, unit price by region |
| `labor_catalog` | Trade, rate, region |
| `estimates` | Estimate documents linked to inspections |
| `estimate_versions` | Immutable revisions |

### Domain 8 · Reports & Deliverables
| Collection | Purpose |
|---|---|
| `report_templates` | Versioned templates |
| `reports` | Rendered report records |
| `report_versions` | Every render with provenance snapshot |
| `report_signatures` | Human approvals |

### Domain 9 · Passport & Habitat Sync
| Collection | Purpose |
|---|---|
| `passport_ledger` | Hash-chained immutable ledger (existing, migrated + typed) |
| `passport_sync_log` | Outbound sync audit trail |
| `habitat_sync_log` | Habitat-bound events |
| `sync_retry_queue` | Failed sync retries with backoff |

### Domain 10 · Compliance & Observability
| Collection | Purpose |
|---|---|
| `provenance_chain` | Every value's derivation lineage |
| `event_log` | Immutable event bus record |
| `error_events` | Exceptions with correlation IDs |
| `cost_ledger` | AI + storage + compute cost per mission/property |

---

## 5. AI WORKFORCE ARCHITECTURE

Every agent conforms to a strict contract:

```python
class Agent(Protocol):
    id: str                # e.g. "roof-intel-v2"
    version: str           # semver
    inputs: JsonSchema     # required + typed
    outputs: JsonSchema    # always includes: value, confidence, evidence_ids, provenance
    model: str             # e.g. anthropic/claude-sonnet-4-6
    prompt_version: str    # hash of the prompt template
    cost_estimate_usd: float
    human_gate_required: bool
```

### Agent registry

| # | Agent | Responsibility | Confidence source | Human gate |
|---|---|---|---|---|
| 1 | **Mission Commander** | Compose + validate mission plan | Rule-based + Claude | Yes |
| 2 | **Mission QA** | ATC 20-item gate | Deterministic checks | No (all-or-nothing) |
| 3 | **Flight Operations** | Live telemetry watch, safe-return decisions | Rule-based | Escalates to human |
| 4 | **Mission Assurance** | In-flight capture density QA | GSD/overlap math | No (auto-retake) |
| 5 | **Capture Validation** | Radiometric integrity, RGB/thermal registration | Statistical + Claude | Yes |
| 6 | **Photogrammetry** | Point-cloud + mesh generation | AWAITING INTEGRATION | Yes |
| 7 | **Thermal Analysis** | Radiometric anomaly detection | Model + statistical | Yes |
| 8 | **CAD/BIM Generation** | Structural layers, framing extraction | AWAITING INTEGRATION | Yes |
| 9 | **Digital Twin** | Fuse 3 layers into single twin | Deterministic composition | Yes |
| 10 | **Roof Intelligence** | Roof plane, facet, damage classification | CV + Claude | Yes |
| 11 | **Window Intelligence** | Window type, dimensions, glass, leakage | CV + Claude | Yes |
| 12 | **Door Intelligence** | Door type, material, seal condition | CV + Claude | Yes |
| 13 | **Water (AWE)** | Moisture retention, roof water risk | Thermal + Claude | Yes |
| 14 | **Air (AWE)** | Ventilation performance, leakage paths | Thermal + Claude | Yes |
| 15 | **Energy (AWE)** | Envelope performance, heat-loss score | Thermal + Claude | Yes |
| 16 | **Damage Detection** | Anomaly clustering across all systems | CV + Claude | Yes |
| 17 | **Measurement Intelligence** | Extract precise measurements from twin | Deterministic geometry | Yes |
| 18 | **Materials Intelligence** | Compose BOM with confidence | Catalog + Claude | Yes |
| 19 | **Labor Intelligence** | Compose labor plan | Catalog + Claude | Yes |
| 20 | **Estimating Intelligence** | Final estimate with waste, tax, O&P | Deterministic math | Yes |
| 21 | **Maintenance Priority** | Rank issues by urgency + cost avoidance | Composite scoring | Yes |
| 22 | **Reporting Intelligence** | Compose enterprise report | Template + Claude narrator | Yes |
| 23 | **Passport Sync** | Emit ledger delta to Passport service | Deterministic | No |
| 24 | **Habitat Sync** | Emit homeowner packet to Habitat | Deterministic | No |

### Absolute rules (non-negotiable)
1. **No agent may fabricate a measurement.** If input is insufficient, output must be `null` + reason.
2. **Every output carries `confidence_pct`, `evidence_ids[]`, `provenance{}`.**
3. **Every human-gated finding is BLOCKED from entering the Passport until QA approves.**
4. **Every agent run is written to `agent_runs`** with input hash, output, cost, model version, prompt version — permanent audit.
5. **Cost caps per property + org** — hard-stop when exceeded.

---

## 6. API BOUNDARIES

Five formal API planes, each with its own auth, rate limits, and versioning.

| Plane | Prefix | Audience | Auth |
|---|---|---|---|
| **Public Read API** | `/api/pub/v1/` | Anonymous (via passport hash) | Signed URL / hash |
| **Product API** | `/api/v1/` | Authenticated users | JWT + org context |
| **Agent API** | `/api/agents/v1/` | Backend agent runners only | Service token |
| **Sync API** | `/api/sync/v1/` | Passport + Habitat services | mTLS + service token |
| **Webhook API** | `/api/hooks/v1/` | External inbound (DJI, FAA, weather) | HMAC signature |

All existing routes at `/api/passport/*`, `/api/claim-snapshot/*`, `/api/mission-control/*`
are preserved under legacy compatibility shims that forward to the new plane 1:1 during
the parity window.

---

## 7. EVENT FLOW & STATE MANAGEMENT

Event-driven backbone. Every domain mutation emits an immutable event to `event_log`.
Downstream consumers subscribe by event type.

```
mission.planned          → validates mission
mission.validated        → unlocks flight
flight.completed         → triggers capture_validation
capture.validated        → schedules AI workforce runs
finding.produced         → notifies human_qa
finding.approved         → passport.ledger.append
passport.updated         → habitat.sync.request
```

Frontend state: **React Query** for server state + **Zustand** for local UI state.
Rejected — Redux (too much ceremony), Recoil (deprecating), unmanaged local state (current problem).

---

## 8. SYNCHRONIZATION FLOW

```
STRATEX CORE  ─(approved finding)→  PASSPORT LEDGER  ─(sync webhook)→  HABITAT
                                          │
                                          └─(sync webhook)→  CARRIER (optional)
```

- **Idempotency**: every sync carries a UUID; duplicate reception is a no-op
- **Ordering**: strict per-property via sequence numbers
- **Retry**: exponential backoff to `sync_retry_queue`
- **Audit**: every attempt logged to `passport_sync_log` / `habitat_sync_log`
- **Cryptographic receipt**: SHA-256 over the payload, written into the ledger
  (already implemented for the Claim Snapshot co-sign — reuse the pattern)

---

## 9. SECURITY MODEL

### Identity
- JWT (short-lived) + refresh tokens
- MFA required for CEO + admin roles
- SSO (SAML / OIDC) — AWAITING INTEGRATION (Phase 5)

### Authorization
- **RBAC**: CEO · GM · Contractor · Inspector · Pilot · Homeowner · Adjuster · Service
- **ABAC overlay**: property-level access via `property_org_bindings`
- Every API call enforces: `authorize(user, action, resource)`

### Data protection
- Passport ledger: hash-chained (already implemented)
- Cryptographic receipts on all critical writes (already implemented for co-sign)
- Field-level encryption on PII (address, owner name, contact) using envelope encryption
- Object storage: signed URLs with expiry; per-org bucket isolation

### Provenance chain
Every value shown to a user must resolve to a `provenance{}` record answering:
1. **Source** — sensor, agent, human, calculation
2. **Confidence** — 0-100 or "verified"
3. **Version** — model version, prompt version
4. **Timestamp** — captured, computed, approved
5. **Signer** — if human-approved, who + when

### Observability
- Sentry (frontend + backend) — AWAITING INTEGRATION
- Structured logs (JSON, trace-id correlated)
- Distributed tracing via OpenTelemetry — AWAITING INTEGRATION
- Health probes: `/healthz`, `/readyz`, `/livez`

---

## 10. DEPLOYMENT MODEL

Three environments, promoted linearly:

```
NextGen preview  →  Staging  →  Production (stratexdrone.com)
```

- Every deploy requires: passing `iter-XX` regression suite + human sign-off
- **Blue/green** at the Emergent ingress layer
- **Rollback**: existing Emergent checkpoint feature (no code needed)
- **Feature flags**: LaunchDarkly or open-source alternative — AWAITING INTEGRATION
- **CI/CD**: pushed to Emergent-managed pipeline; supplemented by repo-side lint/test workflow — AWAITING INTEGRATION

Object storage (S3-compatible) required for asset domain — **AWAITING INTEGRATION**.

---

## 11. VISUAL DESIGN PRINCIPLES

Not negotiable. Every screen must pass this rubric:

### Aesthetic pillars
1. **Mission-control system**, not a form-flow app
2. **Dark graphite base** — never white primary
3. **Glass panels** — 12-24px backdrop blur, subtle stroke
4. **Teal illumination** as anchor color (`#00E5FF`)
5. **Orange highlights** as accent (`#FF7B00`)
6. **Gold ceremonial** for approvals (`#D4B86A`)
7. **Magenta for urgency** (`#FF2D78`)
8. **Green for validated** (`#00FF9C`)
9. **Typography**: Sora display · Space Grotesk body · JetBrains Mono for data
10. **Generous negative space** — 2-3× typical SaaS density
11. **Cinematic motion** — reveal choreography, no boring transitions
12. **Provenance chip on every meaningful value** (mandatory shared component)

### Anti-patterns (forbidden)
- Purple/violet gradients on white
- Generic card grids with equal padding
- Emoji as functional icon (allowed only in written narrative)
- Placeholder Lorem Ipsum
- Any dashboard tile that shows a mock number without a `MOCK` chip

### Provenance chip specification
Every displayed value shall carry one of the following badges:
- 🟢 **MEASURED** — from a physical sensor
- 🔵 **CALCULATED** — from measured inputs
- 🟡 **ESTIMATED** — from a model with confidence <95%
- ✅ **VERIFIED** — human QA approved
- 🤖 **AI-ASSISTED** — model output pending human QA
- ⏳ **AWAITING INTEGRATION** — capability shipping in a future phase
- 🎭 **DEMO DATA** — visible in prototype builds only

---

## 12. EXECUTIVE ARCHITECTURE REVIEW

Per your directive: *"Do not assume the architecture is perfect. Critique it."*

### Strengths
1. **Passport hash chain is genuinely defensible** — cryptographic tamper-evidence is rare in this industry
2. **Cosign SHA-256 receipt pattern is reusable** across every human sign-off in the platform
3. **Storm→calendar bridge + Open-Meteo integration** proves the platform can react to real-world events
4. **PDF pipeline is production-grade** — Playwright + cache-first design already survives Emergent K8s
5. **Emergent LLM Key + `emergentintegrations`** eliminates vendor lock-in on AI

### Weaknesses
1. **Monolithic `server.py`** (2,684 lines) — will not survive scale; must be broken into per-domain routers
2. **No canonical property model** — the single `property_passports` document does too much
3. **Zero product-route auth** — the biggest deployment risk today
4. **No object storage** — PDFs and images live on ephemeral disk
5. **AI orchestration is ad-hoc** — no agent registry, no cost ledger, no prompt versioning
6. **No frontend TypeScript** — 50 pages of unchecked JS across a growing platform
7. **No test coverage on the UI** — regressions are only caught by the testing subagent

### Technical debt (top-priority)
- Break `server.py` (P0)
- Add `require_auth` to every product route (P0)
- Introduce Pydantic doc models per collection (P0)
- Add object storage (P1)
- Formal event log (P1)
- Prompt version manager (P1)
- Frontend TypeScript migration (P2)
- OpenTelemetry tracing (P2)

### Risks
1. **DJI SDK is closed** — the Matrice/Manifold/Dock integration will require an NDA and a licensed developer account. Timeline unknown.
2. **Photogrammetry / CAD-BIM** — no open-source pipeline meets enterprise quality; likely commercial (Bentley ContextCapture, Pix4D, Reality Capture). Cost pressure.
3. **Real thermal ingest** — radiometric R-JPG parsing needs FLIR/DJI SDK. Not free.
4. **Multi-tenant refactor** — every existing query must be rewritten. High regression risk.
5. **Ledger migration** — moving the existing Bingham passport into normalized rows must preserve every hash — mistakes here are unrecoverable.

### Missing integrations (formally declared)
- FAA LAANC airspace
- DJI Cloud API + FlightHub 2
- Manifold 3 edge compute
- Photogrammetry pipeline
- CAD/BIM generator
- Materials + labor DB (regional pricing)
- Object storage (S3-compatible)
- Sentry / OpenTelemetry
- Habitat platform (its own service)
- SSO (SAML / OIDC)

### Performance concerns
1. `/api/storms/active` is O(N passports × 1 external HTTP call) — must be batched + cached
2. Passport ledger unbounded growth — no compaction strategy
3. PDF cache is not shared across replicas — will race on scale-out
4. No pagination in list endpoints — will fail beyond 1k records

### Security concerns
1. Public passport URL leaks all passport data to anyone with the hash — must move to signed URLs
2. Cosign token generation has no per-passport race guard
3. No CSRF on state-changing endpoints
4. WebSocket accepts any client — needs authenticated handshake

### Scalability concerns
1. Single Mongo instance, no replica set — no HA
2. Single uvicorn worker — no horizontal scaling
3. Static file serving from same process as API — must move to CDN

### Recommended improvements
1. **Event sourcing** for the intelligence pipeline — every finding derives from an immutable event chain
2. **CQRS split** — reads from denormalized projections, writes to normalized commands
3. **Agent-as-a-service** pattern — every agent runs as an idempotent HTTP endpoint
4. **Feature flags** for every AWAITING INTEGRATION capability so we can flip them on without deploys
5. **Contract-first API design** — publish OpenAPI specs before implementation for every new endpoint

---

## 13. PHASE 1 DELIVERABLE MAP (traceability)

Mapping this blueprint to the seven Phase 1 acceptance criteria you set:

| Criterion | Deliverable | Section |
|---|---|---|
| 1. Deployable NextGen Preview | Working `/nextgen/*` route tree with shell + workspace stubs on preview URL | Implementation phase |
| 2. Architecture Blueprint | **This document** | §1-§12 |
| 3. System Flow Validation | Workflow chain diagram + per-stage stub route | §0 workflow + §3 nav |
| 4. Visual Design Review | Screenshots of every workspace in the shell | Implementation phase |
| 5. AI Workforce Map | 24-agent registry table | §5 |
| 6. Executive Architecture Review | Strengths · weaknesses · debt · risks · improvements | §12 |
| 7. Final deliverable | Preview + all above docs bundled + sign-off form | Post-implementation |

---

## 14. WHAT MUST NOT BE BUILT YET (Phase 1 forbidden list)

To maintain architectural correctness over speed, these are **explicitly deferred**:
- ❌ Any DJI SDK integration
- ❌ Any photogrammetry pipeline
- ❌ Any real radiometric thermal ingest
- ❌ Any CAD/BIM generator
- ❌ Real materials/labor DB
- ❌ Habitat platform itself (only the sync surface)
- ❌ SSO
- ❌ Payments live checkout
- ❌ Multi-tenant migration (deferred to Phase 2)

Every one of the above is labeled **AWAITING INTEGRATION** in the UI. No exceptions.

---

## 15. IMPLEMENTATION SEQUENCE (once blueprint is approved)

**Phase 1a — Legacy Freeze** (1 session)
1. Create `/app/frontend/src/legacy/` and move every existing page there
2. Create `/app/backend/routes/legacy/` mirroring same
3. Prefix all legacy routes with `/legacy/*`
4. Delete `Andrew` page (✅ done)
5. Snapshot preserved as read-only reference

**Phase 1b — NextGen Shell** (1-2 sessions)
1. `/app/frontend/src/nextgen/` root
2. Persistent operator shell (top command bar, left nav, provenance-aware page frame)
3. All 14 modules as route stubs — every workspace exists, most show "AWAITING INTEGRATION"
4. Provenance chip component (shared)
5. Cross AI + Stratex logo lockup in the shell

**Phase 1c — Workspace Stubs** (1-2 sessions)
1. Mission Control · Property Portfolio · Missions · Digital Twin Studio · AI Workforce · AWE™ Intelligence · Estimating · Reporting · Human QA · Integrations · System
2. Every workspace has: hero, workflow-step indicator, provenance chips wired to real backend state (using existing endpoints)
3. Live workflow chain visible from any workspace

**Phase 1d — Screenshot + Executive Review Package** (final)
1. Screenshot every workspace on desktop + iPhone
2. Bundle blueprint + screenshots + review as a single deliverable
3. Request executive approval before Phase 2

---

## 16. APPROVAL BLOCK

Executive approval required before Phase 1b begins.

☐ Blueprint reviewed by Anthony Cross
☐ Executive Architecture Review reviewed
☐ Phase 1 acceptance criteria confirmed
☐ Authorized to proceed to Phase 1a implementation

Signature: ______________________ Date: ______________
