# STRATEX™ — Product Requirements & Build Status

## PRIMARY ROLE (CEO DIRECTIVE · LOCKED · Feb 2026)

**Stratex is an ANALYSIS ENGINE for already-created property scan data.**
It does NOT create the original measurements or raw field scans. It ingests
completed scan/model inputs (point clouds, meshes, thermal datasets,
measurement-ready property files), analyzes them through the 5-agent expert
chain, and produces a fast, polished, contractor-ready output:
damage assessment · thermal review · energy-loss review · ventilation review ·
materials · estimates · repair priorities · final reporting.

### Visuals vs. Calculations — Hard Rule
- The approved Stratex digital-twin renders (`/twin/master.jpeg`, `/twin/quad.jpeg`)
  are **PRESENTATION ASSETS ONLY**.
- They appear on landing page, demo states, processing screens, and report-preview
  areas where generic scans were previously shown.
- **All calculations and estimations must come from real compatible scan inputs.**
- A rotatable spin/inspect experience is allowed when (a) real 3D twin / point
  cloud data is available, OR (b) a multi-view image dataset has enough
  overlapping views. Otherwise, use the stepped-angle gallery for presentation
  and keep calculations tied to real imported source data.
- The UI MUST display a "PRESENTATION RENDER" disclaimer on stylized visuals.

## Original Problem Statement
Build STRATEX™ — a dual-sided, hyper-secure B2B SaaS platform for drone-based
roof + envelope inspections and automated quoting. Future-Noire aesthetic,
CAD/BIM precision, ground-truth ±1 cm, forensic-grade reports.

## Personas
- **CEO** (Anthony Cross) — single-tenant command center with SMS-MFA portal.
- **GM / Regional Manager** — branch ops + brand inventory + supplier registry.
- **Contractor** — creates jobs, signs NDA, receives forensic deliverables.
- **Pilot / Operator** — flies drones, sees no pricing.
- **Investor / Homeowner (Demo Mode)** — auth-free Switchboard for live pitches.

## Brand
- **Wordmark:** "STRAT" silver-gradient + "EX" cyan neon outline (italic) + ™
- **Glyph:** roof outline (cyan #4DF6FF) + orange/amber low-poly facet (#FF7B00)
- **Palette:** cyan #4DF6FF · amber #FFB020 · green #00FF9C · magenta #FF2D78 · orange #FF7B00
- **Product names:** STRATEX™ · STRATEX Quant™ · STRATEX Vision™ · STRATEX Twin™ · STRATEX Recon™
- **Brand component:** `/app/frontend/src/components/StratexBrand.jsx` — single source of truth

## Architecture — Expert Agent Schema (Phase 3 BIM/Quantification)

The Project Manager dispatcher (`/app/backend/agents/dispatcher.py`) delegates each scan
to a chain of expert agents:

| Agent | Domain |
|---|---|
| `GEOMETRY_AGENT`   | Wall + roof surface areas minus fenestration |
| `MATERIAL_AGENT`   | Multi-material siding + accessories (J-channel, starter, soffit/fascia, gutters) |
| `THERMAL_AGENT`    | Wall-cavity moisture + damage-probability correlation |
| `ENERGY_AGENT`     | BTU loss / air-leakage modeling (windows, doors, walls, attic) |
| `BIM_RENDER_AGENT` | Finish / Vapor / Framing digital-twin renderer |

A manifest is recorded at `/app/backend/data/manifests/{scan_id}_manifest.json`.

## Live Endpoints (no auth)

- `GET  /` → **Switchboard** (5 portal tiles + auth rail)
- `GET  /demo/scan` → 3-step wizard (Dossier → Upload → Analysis)
- `GET  /demo/{twin|maintenance|quant|supply-chain}` → instant Analysis dashboard
- `GET  /api/demo/sample` → deterministic analysis (no LLM)
- `POST /api/demo/scan-analyze` → multi-agent Gemini analysis with sample fallback
- `GET  /api/demo/scan-report.pdf?session_id=…` → 13-page Tabloid PDF
- `GET  /api/pitch/strategic-briefing.pdf` → Doug Piercy investor pitch deck
- `GET  /api/pitch/assets/{file}` → AI-generated CAD renders

## Report (13 pages, Tabloid landscape, Playwright-rendered)

1. Cover — Brand lock-up + Grand-Total range
2. Executive Envelope Summary (gauges + AI maintenance + thermal findings)
3. Forensic Anomaly Atlas (radiometric render + ledger)
4. Triple-Layer Digital Twin (Finish / Decking / Framing — AI renders)
5. Window Schedule (shape, w, h, qty, U-factor, leak severity)
6. Exterior Door Schedule (shape, dims, weatherstrip status)
7. **NEW — Wall Envelope + Siding Package** (Geometry + Material agents)
8. **NEW — Wall Moisture + Vapor Barrier Analysis** (Thermal agent)
9. **NEW — Energy Leakage Atlas** (Energy agent)
10. Bill of Materials (precision to cm via SKU table)
11. Labor (national avg / regional avg / applied / crew / days)
12. Side Quote — Unforeseen Repairs (probability-weighted reserve)
13. Tear-Off Recommendation (conditional, water-retention > threshold)

## Implementation Log

### Feb 2026 — Demo Mode + Expert Agent Schema Shipped
- Restored stubbed `App.js` / `server.py` / `ContractorPortal.jsx` / `fleet_telemetry.py` from prior git commits (auto-commit had truncated them).
- Built Switchboard landing replacing the auth wall at `/`.
- Built 3-step `DemoScanWizard` with multi-agent Gemini + sample fallback.
- Built `routes/demo_scan.py` with full Stratex-Quant Expert Agent schema:
  walls / siding_package / moisture_vapor / energy_leakage domains added to
  the analysis schema and to `_sample_analysis()`.
- Built `agents/dispatcher.py` recording the 5-agent Project Manager manifest.
- Built `stratex_pitch/build_demo_report.py` — 13-page HTML/Playwright PDF
  generator including the 3 new envelope pages.
- Added `/api/pitch/assets/{file}` route to serve AI CAD renders.
- Brand: `components/StratexBrand.jsx` — official STRAT(silver) + EX(cyan)
  wordmark + roof+facet glyph; PDF cover + every page header.
- Fixed all "STRATE Quant" / "STRATE™ Quant™" typos → "STRATEX Quant™" (canonical).

## Prioritized Backlog

### P0 — DONE (demo-ready)
- [x] Auth-free Switchboard with master portal grid
- [x] One-click scan → instant report flow
- [x] 3-layer digital twin viewer (Finish/Deck/Framing)
- [x] Window + Door schedules
- [x] Tear-off recommendation logic
- [x] Side-quote unforeseen reserve
- [x] National + regional labor
- [x] Wall envelope (Geometry agent)
- [x] Siding package multi-material (Material agent)
- [x] Wall moisture + vapor barrier (Thermal agent)
- [x] Energy leakage atlas (Energy agent)
- [x] Expert Agent chain manifest
- [x] Official STRATEX brand wordmark + glyph everywhere
- [x] All typos fixed (STRATEX Quant™ — never STRATE)

### P1 — Post-demo polish
- [x] **Contractor Branding registry (`/contractor/brand`)** — logo upload + business profile form, persists to localStorage, flows to Deck + reports. Default: American Roofing Company.
- [x] **Command Deck rebuilt as ornate "CONTRACTOR COMMAND // PROJECT OVERSIGHT PORTAL"** matching the supplied reference — gold filigree frame, crane glyph, cyan-bezel panels (Current Projects, Completed Reports, Invoice, Billing, Final Reports Box, Credentials, Vendor Network, Pre-Flight Gateway, Client Portfolio, Pre-Flight Gates, KPIs, Corporate).
- [x] **PDF reports branded** — every page now leads with American Roofing logo + business band (license, primary contact, city, phone, website).
- [x] **Demo project relocated** to American Roofing's "2440 Regency Road, Lexington KY 40503".
- [x] **Command Deck (`/deck`) — vertical scrolling app rail with all 37 surfaces (Feb 2026)** — superseded by ornate contractor portal; Master Switchboard preserved at `/switchboard`.
- [x] **3D Component Catalog page added to Adjuster PDF — 8 isometric SVG cards. PDF now 17 pages.**
- [x] **Claim Snapshot Engine (Feb 2026)** — Backend diff engine (`/api/claim-snapshot/*`) compares baseline vs post-storm scans of a Property Passport. Returns CLAIM_SUPPORTABLE / MONITOR / NO_CHANGE verdict, Claude-Sonnet adjuster narrative (timeout-hardened), KPI deltas (envelope, moisture, area, repair-$), NEW / WORSENED / RESOLVED anomaly clusters, and storm correlation. Tabloid PDF (`/api/claim-snapshot/:pid/pdf`). Frontend page `/claim-snapshot/:hash` + tile on App Launcher + CTA on Passport Portal.
- [x] **Live-Ops WebSocket (Feb 2026)** — `/api/ws/live-ops` fan-out channel pushes `STORM_DETECTED` events from storm-watcher and `ATC_REPOLL` pings every 60s. Mission Control surfaces a `WS · LIVE` pill and re-polls all panels on each ping. Self-respawning broadcast loop.
- [x] **Regional Storms endpoint (Feb 2026)** — `/api/storms/active?lat&lon&radius_miles=100` scans every passport inside a 100-mile radius and returns the freshest storms per property + region.
- [x] **Storm → Calendar bridge** — `storm_watcher` upserts a `CHECKUP` calendar event the day after each detected storm crossing a passport's GPS (idempotent on storm date + kind).
- [x] **Adjuster Co-Sign + SHA-256 Receipt (Feb 2026)** — `/api/claim-snapshot/{pid}/cosign/*` mints a one-time magic-link token, snapshots the diff at mint-time (pinned_diff so receipt is bit-stable), validates a single submit, computes a SHA-256 receipt over canonical {diff + signer + ts}, appends an immutable `COSIGN` entry to the passport's hash-chained ledger, and fans out `COSIGN_RECEIVED` on the live-ops WS. Adjuster signing surface at `/cosign/:token`; ClaimSnapshot UI renders a green `CARRIER CO-SIGNED · APPROVED` badge with adjuster + company + truncated receipt once locked. **This closes the LAE-bypass loop end-to-end.**
- [x] **NextGen Architecture Blueprint v1.2 (Feb 26 2026)** — Blueprint frozen at v1.2 with 20 v1.1 corrections + 10 v1.2 consistency corrections. Served via `/api/blueprint/v1.2/*` (MD/PDF/redline/ADRs). **Executive approval pending.**
- [x] **Sequence Diagrams Pack v1.0 (Feb 26 2026 · Directive 003)** — 24 sequence diagrams (SD-001…SD-024) covering onboarding, identity resolution, product selection, planning, preflight, flight, capture finalization, DayScan/AWE/Elite processing, agent execution, finding lifecycle, report generation, passport append, Habitat sync, claim snapshot, adjuster co-sign, corrections, identity operations, failed missions, retention, public projections, durable-event recovery, and the end-to-end 15-stage workflow. Served via `/api/blueprint/sequence-diagrams/v1.0/{md,pdf}`. **Documentation only. Awaiting executive review.**
- [x] **Canonical Data Model Specification v1.0 (Feb 26 2026 · Directive 003)** — Ten logical domains (Tenants, Properties, Missions, Inspections, Evidence, Findings, Agents, Workflows, Passports, Audit) with ~100 entities, shared value objects, enum separation, ten ER diagrams, twenty invariants, normalization/pragmatism review, and cross-artifact traceability matrix mapping every SD to its entities/audit/durable events. Served via `/api/blueprint/canonical-data-model/v1.0/{md,pdf}`. **Logical specification only. No migrations authored. Awaiting executive review.**
- [x] **Directive 005 · Phase 1a — Legacy Freeze + NextGen Foundation (Feb 26 2026)** — Backend NextGen module at `/api/nextgen/*` isolated from legacy: catalog (3 products), organizations, properties (SD-002 identity resolution + create + duplicate detection), missions (SD-003 create + SD-024 stage advance), passports (Phase 1c read stub), workflow overview, audit trail. Frontend NextGen shell at `/nextgen/*` with sidebar nav, 15-stage strip, mission-control aesthetic, dark base + cyan/gold Directive-005 visual contract, Blueprint §20.1 demo-honesty banner. **Executive gates for production deploy / legacy deletion / passport-authority change / vendor cost >$250 remain withheld.** Verified 100% (backend 19/19 · full UI happy path).
- [x] **Directive 006 · Wave 2A — Evidence Ingest + Canonical Mission Package (Feb 26 2026)** — Backend evidence surface at `/api/nextgen/v1/*`: upload with SHA-256 streaming, tenant-path storage adapter (replaceable), Pillow-only EXIF/GPS extraction (never fabricates), duplicate detection at 409 with intended-duplicate override, MIME + blocked-extension guards, evidence-relationship graph, product-specific requirement profiles (DayScan/AWE/Elite), package validate + finalize with append-safe versioning, SHA-256 manifest digest, downloadable JSON manifest, durable outbox emit `EVIDENCE_PACKAGE_FINALIZED` (idempotent), stage advance to 7 (Digital Twin Generation) on finalize. Frontend `/nextgen/missions/:missionId/evidence` workspace with drag-drop multi-upload, inventory, detail drawer, validation panel, manifest download. Storage: local disk `NEXTGEN_STORAGE_ROOT`, content-addressed, tenant-isolated, backend-proxied downloads only. **Vendor cost gate untouched.** Verified 25/25 backend + full UI happy path (iteration_23).
- [x] **Directive 007 · Wave 2B — Property Intelligence Engine (Feb 26 2026)** — Structured intelligence replaces generic findings and becomes the single source of truth. Backend: `nextgen/taxonomy.py` canonical building-system taxonomy (18 systems / 81 components), severity/priority/risk enums, tier_for_severity mapping. `nextgen/passport_service.py` internal Passport Service with SHA-256 content-addressed hash chain (`prior_hash → content_hash → signature`), monotonic sequence via optimistic Mongo `find_one_and_update`. `nextgen/routes/intelligence.py` endpoints: `POST /v1/intelligence` (creates PIO with AWE impact, visibility scopes, historical comparison to prior approved), `GET /v1/missions/{id}/intelligence`, `GET /v1/intelligence/{id}` with versions + reviews, `POST /v1/intelligence/{id}/review` (approve triggers Passport append + timeline entry + INTELLIGENCE_APPROVED outbox event + audit event), `GET /v1/properties/{id}/timeline`, `GET /v1/properties/{id}/passport?audience=…`, `GET /v1/properties/{id}/report/{template}` (7 templates as pure projections). Frontend: `/nextgen/missions/:id/intelligence` workspace; `/nextgen/passport` shows hash-chained ledger with audience switcher, timeline, live report projection. Verified 27/27 backend + full UI + hash chain confirmed end-to-end (iteration_24).
- [x] **Directive 008 · First Field Pilot Prep (Feb 26 2026)** — Deterministic **AWE Composite Intelligence** engine (`nextgen/awe.py`): Air/Water/Energy scores from approved PIOs with severity/priority-weighted penalties, weighted composite (Water 0.40 · Air/Energy 0.30), confidence + evidence completeness, `INTERNAL_DRAFT` release-state gate per Blueprint §17.1. `nextgen/routes/habitat.py`: `POST /v1/properties/{id}/habitat-link` mints expiring token grants (default 7d, max 30d), `GET /v1/habitat/{token}` **public no-auth read** with rate-limit + revocation (410) + expiration, `POST /v1/habitat-grants/{id}/revoke`, `GET /v1/properties/{id}/awe`, `GET /v1/properties/{id}/report/{template}/html` polished dark-mode HTML projection. Frontend: `HabitatPublic.jsx` at `/habitat/:token` renders AWE dials + priority items + maintenance + timeline (no contractor data, no confidence scores); PassportPage gains AWE Composite panel + "Share with Homeowner" one-click magic link (clipboard-copied) + Open HTML Report action. Mobile-tablet touch targets (44px min) applied across NextGen. Verified: AWE deterministic scoring (87 composite from approved PIOs), habitat public read renders, revoke → 410, HTML report renders end-to-end. **First contractor-operated field pilot can now run.**
- [ ] True vision-grounded Gemini (attach uploaded images to the LLM call so
      the analysis reflects what's actually in the photos, not just the dossier)
- [ ] Three.js parametric twin renderer driven by REAL scan data (Track B —
      forensic-grade reports, not marketing visuals)
- [ ] Photogrammetry pipeline (OpenDroneMap self-hosted, or DroneDeploy API)
- [ ] BOM editor / supplier price overrides per region (GM tier)
- [ ] Wire the new envelope domains into the live LLM prompt (currently the
      LLM doesn't yet ask for walls/siding/energy — only the sample includes them)
- [ ] **Phase 3:** GM Brand Roster + GM Pricing Inventory (3-tier CRUD)
- [ ] **Phase 4:** Contractor Dashboard rebuild (app-tile launcher + 3-contact verification wall)
- [ ] **Phase 5:** Preferred Materials Brand App (Roofing/Gutters/Vinyl — draft list for user sign-off first)
- [ ] **Phase 8:** Full Workflow Simulation + Tripwire breach test

### P2 — Future / refactor
- [ ] App-wide `data-testid` audit
- [ ] Modularize `deck.html`
- [ ] WebSocket push for live scan status to Switchboard tiles
- [ ] Email-the-report button (Resend integration)
- [ ] CSV / DOCX report export

## Project Health
- Backend: **OPERATIONAL** · 13-page PDF renders in ~25s · sample endpoint <200ms · NextGen `/api/nextgen/*` module live (Phase 1a)
- Frontend: **OPERATIONAL** · Switchboard + analysis dashboard fully wired · NextGen shell live at `/nextgen/*` (Phase 1a)
- Demo flow: **READY for live pitch** (`/` → "New Drone Scan" → analysis → PDF)
- Production deployment (stratexdrone.com): **stale** — user must redeploy
- NextGen Phase 1a: **DELIVERED** · 19/19 backend tests · full UI happy path passed (iteration_22)
- **Directive 009 (Feb 2026): DELIVERED** — STRATEX CORE Premium Command Interface (presentation-layer rebuild only). New responsive shell (desktop rail + mobile bottom nav + More sheet), premium Home / Missions / Reports Binder / AWE / Habitat / Passport / Organization pages, new STRATEX CORE brand SVG assets. 100% pass on iteration_25 across desktop (1440x900) + mobile (390x844). Backend/DB/business logic untouched. Legacy untouched.
- **Phase 1 Reorganization (Feb 2026, commit `467ba74`): DELIVERED** — canonical NextGen shell is now the authenticated Stratex Core application. Backup branch `backup-before-nextgen-consolidation` recorded before any edits. Landing rewritten to exactly 3 primary entrances (Operator/Pilot, Contractor/Insurance, CENTCOM) + single "Company & Platform Information" secondary link. Duplicate `/admin/ops` route resolved in favor of `GmOpsPage`. NextGen shell nav rebuilt into 6 canonical groups (COMMAND · OPERATIONS · NETWORK · PROPERTY INTELLIGENCE · MANAGEMENT · COMPANY) with 8 new placeholder destinations (`/nextgen/alerts`, `/schedule`, `/network/{contractors,operators,homeowners}`, `/geo`, `/plans`, `/company`) — all clearly labeled `PLACEHOLDER · NO LIVE DATA`. Reusable `DemoDataBadge` component surfaces mocked/seed status. Two migration docs added at `docs/CURRENT_ROUTE_INVENTORY.md` + `docs/LEGACY_ROUTE_MIGRATION_PLAN.md`. Frontend production build succeeds. Backend Phase 1a + v25 regression suites: 33/33 pass. All legacy routes preserved.

## Architecture
- `/app/backend/` — FastAPI, MongoDB, Stripe, Emergent LLM key (Gemini), Twilio
- `/app/backend/agents/` — Expert Agent dispatcher + registry
- `/app/backend/data/manifests/` — Project Manager scan manifests
- `/app/frontend/` — React + Tailwind, lucide-react, sonner toasts
- `/app/stratex_pitch/` — pitch deck + AI render assets + demo report builder
- `/app/memory/` — PRD, TRIFECTA spec, test credentials
