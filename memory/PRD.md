# STRATEX™ — PRD & Build Log


## What's Been Implemented (2026-02-28 — v3.8.1 — P1 Regression PASS + Flight Audit + KY Targets Mongo Seed)
- ✅ **`testing_agent_v3_fork` iteration_15**: Backend 14/14 pytest green, 5 of 6 UI batches fully driven (AdminSalesHub CRM, Overseer, FlightAudit, FleetLaunch all green; Business Brain + OnboardingROI pages rendered cleanly but full input-fill not driven — Playwright script aborted on non-product Python issue). **Zero critical or minor backend/frontend bugs found.**
- ✅ **`/admin/flight-audit`** — new admin page (`/app/frontend/src/pages/FlightAudit.jsx`) renders authorization rows from `/api/flight-authorizations/recent` with six-check MicroCheck telemetry snapshot grid + meta blocks + cross-link from `/admin/overseer`.
- ✅ **7 Central-Kentucky competitor targets** now upserted to `db.sales_targets` on backend startup (ALE Roofing, Burnett, CentiMark, Big League, A Godsend, Odessa, Barrier) — `/api/admin/sales-targets` now returns `source: "mongo"` not the in-code seed, unblocking the P3 Competitive-Intel JOIN.
- ✅ **`OnboardingMetrics`** schema confirmed in DB to include `historical_sales_2_years: float` — ready for the P3 competitive-intel mapping layer.
- ✅ Added `data-testid="material-configurator"` wrapper on the embedded MaterialConfigurator inside ContractorPortal Business Brain tab (testing-agent action item).

### Carry-forward
- **P3 Competitive Intel Onboarding Mapping** — UI/copy layer: map `historical_sales_2_years` against the now-seeded 7 KY competitors to generate dynamic "you'd reclaim more than Burnett does in a year" outreach hooks on `/onboard`.



## What's Been Implemented (2026-02-28 — v3.8.0 — Fleet Launch Authorization + WS Telemetry Bridge)
- ✅ **Step 5 Fleet Launch Authorization dashboard** (`/launch` standalone + `/operator/launch/:jobId` operator-bound) — `/app/frontend/src/pages/FleetLaunch.jsx`. Six live checks (Trailer Hatch, Battery, RTK GPS, Comm Uplink, Weather, Perimeter) drive an Authorize button gated by all-green telemetry. Strict PBR Luxury-Corporate palette (Electric Teal `#00F5D4`, Neon Orange `#FF5400`, Metallic Nickel `#3A4350`), lucide-react icons, full `data-testid` coverage.
- ✅ **Cloud telemetry simulator** at `wss://<host>/api/ws/stratex/core?token=<jwt>` — emits 4 Hz frames matching the on-site hardware-gateway wire schema verbatim. Converges to flight-ready state in ~10 s. Accepts `AUTHORIZE_FLEET_LAUNCH`, gates against snapshot, persists `flight_authorizations` doc, optionally transitions tied operator job → IN_FLIGHT.
- ✅ **On-site hardware gateway reference** preserved at `/app/hardware-gateway/stratex-gateway.js` + `README.md` — Node + SerialPort/ReadlineParser process for the tablet/dock controller. UI is wire-compatible with both cloud-sim and on-site gateway, zero client change.
- ✅ **HTTP audit endpoint** `GET /api/flight-authorizations/recent` — admin sees all, operator sees own, contractor sees their job-bound authorizations only.
- ✅ **Smoke test** `/app/backend/tests/smoke_fleet_launch.py` validates the full chain (login → WS handshake → telemetry convergence → AUTHORIZE → MISSION_LAUNCHED → persistence read-back). PASSES.
- ✅ E2E verified in browser: WS LIVE · 4 Hz, all checks Nominal, `MISSION AUTHORIZED · <auth_id>` confirmation rendered.


## What's Been Implemented (2026-02-27 — v3.7.0 — Luxury-Corporate QC Pass)
- ✅ **Brand consistency** — `STRATEX™` + `Strategic Thermal Reconnaissance` subtitle locked across hero, scientific-rigor section, fleet command, footer; legacy "Cyber-Shield" branding fully purged.
- ✅ **Hero value-prop rewritten** with explicit scientific rigor: sub-surface analytics + localized weather telemetry + thermal capacitance modeling → true moisture volume and depth beneath the membrane (cubic-inch precision).
- ✅ **Three required technical-language quotes** injected verbatim into a new `[data-testid=scientific-rigor-section]` (Sub-Surface Moisture Quantization, Absolute Mathematical Accuracy, Precision Edge-Mapping). String-audited via playwright — all 3 match exactly.
- ✅ **Strict 3-color palette enforced**:
  - `--electric-teal: #00F5D4`, `--neon-orange: #FF5400`, `--metallic-nickel: #3A4350` locked as single source of truth in `index.css`
  - Legacy `--cyber-teal`, `--volt-green`, `--plasma-orange` re-aliased to the strict palette so existing components keep working while honoring the brand
  - Palette swatch UI on Landing updated to the strict 3 swatches with shadow glow (was 4 mismatched colors)
  - Pricing.jsx off-palette `#39FF14` lime and `#FF5500` orange swapped to `#00F5D4` / `#FF5400`
  - RoofModel3D legend Valley swatch fixed `#FF5500 → #FF5400`
- ✅ **3D viewport caption upgraded** to "Razor-sharp point clouds + high-contrast volumetric mesh overlays. Moisture boundaries pulse Neon Orange against a Metallic Nickel substrate, with Electric Teal vector edges mathematically locked to the exact square inch" — replaces previous generic "orbital photogrammetry" copy.
- ✅ **Module 02 (STRATEX Thermal™) blurb upgraded** to scientific rigor — "Sub-surface radiometric mass quantization. Cross-references diurnal temperature shift cycles with thermal capacitance modeling to isolate true moisture entrapment from surface reflectivity."

## Deferred (carried over from prior directive, not cancelled)
- **P1 — ContractorPortal Business Brain integration** of MaterialConfigurator (currently lives standalone)
- **P1 — CRM stubs** (outreach_notes, call_logs, communication_templates schemas + endpoints)
- **P1 — Competitive-intel widget** on /onboard ("you'd save more than Burnett reclaims in a year")
- **P1 — Dynamic Telemetry Anomaly Halting** loop with Overseer dispatch

## What's Been Implemented (2026-02-27 — v3.6.0 — Onboarding ROI Funnel + Sales Hub + Materials Expert)

### Section 1 — `/onboard` Onboarding & ROI Funnel
- ✅ Dedicated `/onboard` route (Landing CTA + `cta-new-mission` rewired; sign-in CTA preserved)
- ✅ Four data-capture metrics: `leads_per_week`, `leads_per_month`, `leads_per_year`, `historical_sales_2_years`
- ✅ Live Central Kentucky GC leakage matrix renders the 5 overhead constants exactly per spec (10% commission, $28.50/hr blended labor, $350/mo field rep insurance, $0.655/mi × 45 mi avg, 3.5% ladder safety uplift)
- ✅ ROI formula: `Manual cost ($185/roof) − STRATEX cost ($25/roof) ± 8% sales-rep time reclaim` — UI shows both gross savings AND audited net (default = $123,200 net annual savings at 420 leads/yr × $1.4M 2yr sales)
- ✅ 3-tier pricing chart: Starter $199 (0-15), Growth Pro $499 (16-50), Enterprise Elite $1,299 (51+)
- ✅ AI auto-circle ring follows `leads_per_month` band — verified migrating STARTER ↔ GROWTH PRO ↔ ENTERPRISE ELITE
- ✅ Dual sign-up paths: `Upgraded CapEx Activation` (creates account + Stripe TEST checkout) vs `Commit Later · Standard Access` (creates account only, 3D viewports locked)

### Section 2 — Data Promise & Isolation
- ✅ Discretion Clause callout permanently visible on `/onboard` (Section 2.1 wording verbatim)
- ✅ AES-256 reuse — new financial fields (`contractor_cost_matrix`, `labor_per_hour`, `profit_overhead_multipliers`) flow through the existing Business Brain `encrypt_value` / `decrypt_value` pipeline
- ✅ Admin Financial Blocker: `GET /api/admin/contractor/{id}/financial-config` returns `{}` for ANY admin probe (verified via curl)

### Section 3.1 — Materials Configurator (`/components/MaterialConfigurator.jsx`)
- ✅ 4-system parent selector: Asphalt / Metal Standing-Seam / Slate Premium / Custom
- ✅ Asphalt branch — Manufacturer → Line → Color → Starter → Hip&Ridge → Underlayment (felt/synthetic/I&W groups) → Drip Edge style/material/color → Step + Counter + Pipe Boot flashing → Fastener Matrix
- ✅ Metal branch — Manufacturer → Series → Seam Profile → Substrate → Fasteners → Sealants → Color
- ✅ Slate branch — Manufacturer/Quarry → Quarry Origin → Thickness Grade → Fastener
- ✅ Custom branch — free-text proprietary specification field
- ✅ Live quantity-takeoff math (12% shingle waste / 10% underlayment / 8% edge) — bundle, roll, edge piece counts compute when `takeoff_inputs` provided

### Section 4 — Admin Sales Hub (`/admin/sales`)
- ✅ Sortable table (Contractor / Base / Phone / Status) for all 7 Central Kentucky targets (ALE, Burnett, CentiMark, Big League, A Godsend, Odessa, Barrier)
- ✅ Click-to-advance status pipeline: `uncontacted → contacted → demoed → negotiating → closed-won → closed-lost`
- ✅ Leaflet dark-tile map (CartoDB Dark) with status-color-tinted pulse pins anchored to Lexington-radius coordinates
- ✅ Status filter chips with live counts
- ✅ `Protected role="admin"` guard + backend `admin_only` dependency double-locks the route

### Backend Endpoints Added
- `POST /api/onboarding/signup` — frictionless contractor sign-up (skips TOTP, accepts NDA via Discretion Clause)
- `POST /api/onboarding/stripe-checkout` — Stripe TEST-mode checkout session
- `GET /api/admin/sales-targets` — admin-only Lexington-radius contractor list
- `GET /api/admin/contractor/{id}/financial-config` — admin financial blocker (hard `{}`)
- `GET /api/contractor/materials-config`, `PUT /api/contractor/materials-config` — materials picks persistence

### Compliance Evidence
- Backend curl tests: contractor signup → 200 (returns JWT), contractor → admin endpoint → 403, admin → sales-targets → 200 with 7 records, admin → financial-config → `{}`, materials-config PUT round-trip → 200
- Frontend captures: `/onboard` rendering all 3 tiers + auto-circle migrating with leads_per_month, `/admin/sales` showing table+map+pipeline progression, Landing CTAs verified pointing to `/onboard`
- Stripe TEST mode active (no real charges in this environment per directive)

## What's Been Implemented (2026-02-27 — v3.5.0 — Cinematic Wipe Transition + BEES Live Switcher)
- ✅ **Electric-teal layer-switch wipe transition** in `RoofModel3D.jsx`:
  - Wide bloom-friendly canvas-textured plane (1.2× × 2.6× span) with razor-bright white core flanked by saturated electric-teal halos + HUD scanline streaks.
  - Always billboards toward the camera (`lookAt(camera.position)`) so the bright core face is maximally visible regardless of orbit angle.
  - Additive blending + `depthTest: false` + `renderOrder: 999` so the sweep punches through bloom and renders on top.
  - 1-second cinematic sweep across the X-axis from `centre - 1.5*span` to `centre + 1.5*span`, with sine-curve brightness pulse (peak at u=0.5).
  - Source-layer fades out 0..0.63, destination-layer is REVEALED behind the wipe (delayed cross-fade emerges 0.35..0.91) — matches the "wipe transition" mental model.
  - On wipe complete: source layer is fully hidden, destination layer restored to full opacity + original emissive intensity, wipe plane invisible.
- ✅ **`/_neon-preview` redesigned as a Live Switcher demo** — single RoofModel3D instance + interactive BEES toggle bar (FRAMING / 3-TAB / DIMENSIONAL / METAL / SLATE / GUTTERS overlay). Each click triggers the cinematic wipe. Comment in the file documents that the gallery layout was removed to avoid multi-WebGL-context rAF throttling.
- ✅ **Performance optimizations**: removed per-frame `material.transparent = true` flips (already set at construction); cached `_origEmissive` per material in userData to restore after the wipe; IntersectionObserver gates `composer.render()` for off-screen canvases.

## What's Been Implemented (2026-02-27 — v3.4.0 — BEES XOR Layer Controller + PBR Pivot Hardening)
- ✅ **BEES Layer Visibility Controller** — `RoofModel3D.jsx` now pre-builds all primary layer mesh groups at mount (framing, shingle/3-tab, dimensional, metal, slate) + secondary gutter overlay. Switching primary layers is now instant visibility toggling (no full scene remount); `resolvedPrimary` removed from useEffect mount-deps.
- ✅ **Hard-reset XOR enforcement** — explicit `VALID_PRIMARIES = ["framing","shingle","dimensional","metal","slate"]` + a hard-reset pass that hides ALL primaries before showing only the active one. Forbidden states (framing + finish, multiple finishes overlapping) are unreachable by construction.
- ✅ **Secondary gutter overlay** — independent visibility preserved across primary toggles, anchored to whichever primary is active.
- ✅ Visually verified all 5 primary panels render distinct textures + the bottom "Gutters OFF" reference panel confirms secondary overlay is properly independent (screenshot capture at `/_neon-preview`).
- ✅ Backward compatibility preserved: legacy `layers={roofing,framing,gutters}` prop shim still works; existing data-testids untouched.

## Original Problem Statement
STRATEX™ — dual-sided, hyper-secure B2B SaaS platform for drone-based roof inspections + automated quoting. Two roles (Contractor / Operator) with isolated views, NDA-gated onboarding, JWT+TOTP MFA, AES-256 encrypted "Business Brain", interactive map dispatch, and forensic 3D mesh + multi-agent narrative post-flight processing.

## User Personas
- **Contractor / Project Manager** — signs NDA, configures encrypted Business Brain, dispatches drone jobs via map, reviews proposals, exports PDF.
- **STRATEX Operator (drone pilot)** — picks up dispatched jobs, runs preflight checklist, authorizes aerial reconnaissance. ZERO visibility into pricing or homeowner contact info.
- **Insurance Adjuster** — consumes the contractor's PDF supplement (forensic/validation/jurisprudential narratives + Xactimate-tagged line items).

## Modules
1. **Auth & NDA Gateway** — JWT (Bearer) + bcrypt + TOTP MFA + typed-name NDA with IP/timestamp audit.
2. **Contractor Portal / Business Brain** — AES-256 (Fernet/HKDF) encrypted materials catalog, overhead/profit/labor/insurance multipliers.
3. **Job Creation & Operator Dispatch** — Leaflet + OpenStreetMap interactive pin-drop + Nominatim geocoding.
4. **Post-Flight Processing** — procedural multi-facet 3D mesh, anomaly detection, labor matrix, Claude Sonnet 4.6 narrative.
5. **Dual-Sided Report Splitting** — operator view strips ALL financial fields; contractor view shows fully unblinded proposal + PDF.

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + PyJWT + bcrypt + pyotp + cryptography (Fernet/HKDF-SHA256) + emergentintegrations.
- **Frontend**: React 19 + Tailwind + shadcn + sonner + lucide-react + vanilla three.js + leaflet + react-leaflet.
- **Routes**:
  - `/` Landing (public)
  - `/auth` 2-step login + signup
  - `/nda` NDA signing (contractor-only, auto-redirect)
  - `/contractor`, `/contractor/jobs/new`, `/contractor/jobs/:id`, `/contractor/materials`
  - `/operator`, `/operator/jobs/:id`

## What's Been Implemented (2026-02-28 — v3.1.0 — BEES Layer Visibility Constraints)
- ✅ **🎛️ Mutually-exclusive layer controller** per spec. New props on `RoofModel3D.jsx`:
  - `primaryLayer` (radio): `"framing" | "shingle" | "metal" | "slate"`
  - `showGutters` (independent bool)
  - Legacy `layers={roofing,framing,gutters}` prop still accepted (back-compat shim translates it)
- ✅ **3 distinct finish textures** (procedural CanvasTexture, cached):
  - **Shingle** — staggered architectural tabs in violet/purple gradient (metalness 0.05 / roughness 0.85)
  - **Metal** — vertical standing-seam panels in steel-blue with raised seam highlights (metalness 0.85 / roughness 0.25)
  - **Slate** — staggered scalloped slate tiles in cool grey (metalness 0.20 / roughness 0.70)
- ✅ **Framing isolation mode** — when `primaryLayer === "framing"`, every facet mesh is hidden (`facetGroups[*].visible = false`) and only the neon-green rafter wireframe + sub-fascia render. Forbidden state collisions (framing + finish, OR multiple finishes) are unreachable by construction.
- ✅ **UI**: 4-button radio group + visual divider + persistent gutters secondary toggle on both `ContractorPortal.jsx` and `Landing.jsx`. `aria-pressed` set correctly. Existing data-testids preserved (`layer-toggle-framing/shingle/metal/slate/gutters`).
- ✅ Visually verified all 4 states + gutter toggle via screenshot cycle on the demo job.

## What's Been Implemented (2026-02-28 — v3.3.0 — Multi-Agent Expert Panel Renderer)
- ✅ **Convened 4-agent expert panel** (Master Framing Carpenter/Architect, Master Roofing Contractor, Master CAD Designer, Master Gutter Contractor). Consensus rules ratified and documented at `/app/memory/expert_panel_review.md`. All renderer changes flow from these rules.
- ✅ **CRITICAL FIX — Slope-aligned UV basis** (Agent 3 / C1). Replaced the world-space UV projection in `buildFacetMesh` with a per-facet (U, V) basis where U = horizontal along the eave, V = up the slope. World-space scale (1 unit = 1 ft) is preserved via `REPEAT_FT` constants per material so a 3-tab shingle ALWAYS reads at correct 12" tab width regardless of facet size.
- ✅ **Material patterns now obey craft rules**:
  - **3-Tab Shingle** (Agent 2 / R1) — 4 courses per texture tile, 3 shingles per row with 3 tabs each; staggered half-shingle offset per course; courses now run PARALLEL TO EAVE on every facet.
  - **Standing-Seam Metal** (Agent 2 / R3) — 2 panels per texture tile; seams run EAVE-TO-RIDGE (verified visually as diagonal converging lines on hip facets); rivet/clip dots every 14" along each seam.
  - **Slate** (Agent 2 / R4) — 3 courses × 3 tiles per texture; bright lavender scalloped top edges; courses parallel to eave.
- ✅ **Ratified neon palette** (unified blue+orange architectural language matching references):
  - Shingle: `#1EA7FF` neon cyan-blue
  - Metal:   `#00F0FF` neon cyan + bright white rivet cores
  - Slate:   `#C77DFF` neon violet
  - Framing rafters: `#00F0FF` cyan
  - Sub-fascia + Gutters: `#FF7A00` neon orange
- ✅ **Variable line weights** (Agent 3 / C2) — every 3rd rafter is a heavier doubled trimmer (r=0.075 vs 0.04); sub-fascia/gutter tubes are heavy; additive glow halos on top of every tube.
- ✅ All visually verified on `/_neon-preview`. Shingle courses + metal seams + slate scallops + framing rafters all align correctly with each facet's slope direction.

### Quality Gate (codified in expert_panel_review.md):
Every digital twin generation must pass 6 validation gates before render — codifies the "no wrong layers" rule the user demanded so the visual replication stays in tolerance of actual RTK-calibrated photogrammetry (target: ±1 cm).

## What's Been Implemented (2026-02-28 — v3.4.1 — Brightened Palette + PDF Cert)
- ✅ **User feedback applied**: "dark neons on dark background is hard to read." Brightened the entire palette for proper contrast against the near-black material interiors:
  - Shingle: `#1EA7FF` → **`#4CC3FF`** (bright cyan-blue)
  - Metal:   `#00F0FF` → **`#5FF4FF`** (bright cyan)
  - Slate:   `#C77DFF` → **`#D99DFF`** (bright violet)
  - Sub-fascia + Gutters: `#FF7A00` → **`#FF9A3C`** (bright orange)
  - In-texture line colors also brightened (e.g. shingle tab cuts now `#C8ECFF`, slate scallops now `#E8C2FF`)
- ✅ Bumped emissive intensities ~50% (shingle 0.85→1.30, metal 0.95→1.40, slate 0.80→1.20) so painted lines read at normal viewing distance.
- ✅ Updated Contractor Portal layer-toggle pill colors to match the new palette (`#5FF4FF`, `#4CC3FF`, `#D99DFF`).
- ✅ **PDF Expert Panel Certification block** — added to `_build_pdf()` in `server.py`. Every contractor PDF supplement now opens with a "STRATEX™ EXPERT PANEL CERTIFIED · 6/6 GATES · 100%" header followed by a 5-column table listing each gate's label / agent / rule ref / PASS-FAIL / message. Adjuster-ready trust signal.
- ✅ **Job-detail validation card** — `<ValidationReport />` now renders directly below the 3D viewport on both Contractor JobDetail AND Operator JobDetail pages (using `roof_telemetry.validation` which is set on every Phase 2 data capture).

## What's Been Implemented (2026-02-28 — v3.4.2 — Reference-Accurate Roof Shape)
- ✅ **Rebuilt `preset_stratex_demo`** in `roof_topology.py` to match the user's IMG_2174 plan-view reference. The compound topology is now FIVE distinct hip masses + chimney instead of three:
  1. **Main body** — 18 × 12 ft east-west long axis, pitch 8/12 — the dominant central mass
  2. **Rear wing** — 8 × 4 ft projecting north from the back, pitch 7/12
  3. **West bumpout** — 3 × 6 ft small protrusion on the left side, pitch 7/12
  4. **Front-left hip** — 5 × 4 ft south-west corner projection, pitch 7/12
  5. **Front entry porch** — 4 × 3 ft smallest hip at front-center, pitch 6/12
  6. Chimney prism (1.2 × 1.2 × 3.5) on the main rear slope
- ✅ Added 5 explicit valley edges where each wing intersects the main body (per IRC §R905.2.8.3) — makes the valley line classification render correctly in plasma-orange.
- ✅ Topology stats: **25 facets · 61 edges · 670 sf footprint · 187 lf eave perimeter**. Validation gates still 6/6 PASS at 100% on the new shape.
- ✅ Framing layer now traces all 5 mass footprints distinctly — you can read the architectural plan directly from the cyan-on-orange wireframe.

## What's Been Implemented (2026-02-28 — v3.4.0 — World-Class Polish Pass)
- ✅ **Razor-sharp CAD aesthetic** — stripped post-processing bloom haze and canvas-level `shadowBlur` halos per user feedback ("study top CAD neon drawings"). All neon now comes from saturated 1–2 px strokes on near-black background. Minimal subtle bloom kept (strength 0.18, threshold 0.75) so only the brightest highlights catch a soft glint. Matches Jarvis-HUD / Autodesk Forma reference aesthetic.
- ✅ **Texture rewrite v3** — every line is a single crisp stroke: 2 px course separators, 1.2 px tab cuts (shingle); 2.4 px seams + small bright dot rivets (metal); 2 px scallops + 1.2 px tile edges (slate). Anisotropy 8 for tack-sharp diagonal viewing.
- ✅ **Backend: `validate_topology()` multi-agent quality gate** — codified the 4-agent expert panel into 6 deterministic pre-render gates:
  1. `slope_basis` (CAD Designer / C1)
  2. `gutter_coverage` (Gutter Contractor / G1)
  3. `rafter_count` (Framing Carpenter / F2 — IRC §R802.4 ±20%)
  4. `sub_fascia` (Framing Carpenter / F4)
  5. `material_direction` (Roofing Contractor / R5)
  6. `edge_hierarchy` (CAD Designer / C2)
  - Result attached to `topology["validation"]` on every `build_topology()` call.
  - Returned by `/api/public/demo-topology` AND embedded in `roof_telemetry` on every contractor/operator job after Phase 2 data capture.
- ✅ **Frontend: `<ValidationReport />` component** — clean 6-row report card with agent attribution + rule ref. Rendered on Landing page below the demo mesh AND at the top of the `/_neon-preview` gallery. Insurance-adjuster-ready proof of quality.
- ✅ **Caliper Photo OCR** — new endpoint `POST /api/contractor/caliper-ocr`:
  - Accepts `{image_base64, mime_type}` from a phone camera capture
  - Pipes through **Gemini 3 Flash Preview** via emergentintegrations (Emergent LLM Key) with a strict JSON-only prompt
  - Returns `{thickness_mm, thickness_in, confidence, fallback}`; gracefully falls back to manual entry if vision fails
  - Audit-logged for every call
- ✅ **Frontend: `<CaliperUpload />` component** — phone-capture `<input capture="environment">` button on the Materials Config page; auto-populates `measured_thickness_mm` on success.
- ✅ **MaterialsConfig.measured_thickness_mm** — new persisted field; GET endpoint merges defaults into legacy records so existing contractor docs receive the new field automatically.
- ✅ Backend tested: **8/8 backend tests pass** (iteration_14.json) — validation gates carry correct keys + 100% pass on demo, caliper OCR auth-gated + gracefully falls back without 500, `measured_thickness_mm` round-trips through PUT→GET.

### Architecture Files Added
- `/app/memory/expert_panel_review.md` — the ratified rule book
- `/app/frontend/src/components/ValidationReport.jsx`
- `/app/frontend/src/components/CaliperUpload.jsx`
- `/app/frontend/src/pages/NeonLayerPreview.jsx` (internal `/_neon-preview` gallery)
- `/app/image_testing.md` — caliper image test rules




## What's Been Implemented (2026-02-28 — v3.0.1 — Landing Page Demo Mesh Uplift)
- ✅ **🌐 New public endpoint** `GET /api/public/demo-topology` (no auth) — returns the full `stratex_demo` compound topology (17 facets + 40 edges + framing rafters + gutter polylines + 4 sample anomalies) keyed off a deterministic `LANDING_DEMO_v1` seed so the marketing page is reproducible.
- ✅ **🖼️ Landing page mesh swapped** — `Landing.jsx` previously hardcoded a 4-facet cross-hip mesh (the cause of the "still looks the same" report). Now fetches from `/api/public/demo-topology` on mount and renders the compound roof with all 3 tri-layer toggles (roofing + framing + gutters) ON by default.
- ✅ Visually confirmed: landing page Photogrammetry Mesh section now shows the main hip body + 2 hip wings + chimney prism + green rafters + cyan gutters + labeled anomaly callouts, matching reference image 2's structural complexity.

## What's Been Implemented (2026-02-28 — v3.0.0 — Compound Demo Topology + Default-On Tri-Layer)
- ✅ **🏘️ New `stratex_demo` roof preset** — compound L-shape that mirrors the marketing reference render:
  - **Main body**: 16 × 10 hip volume, pitch 9/12 (dominates the silhouette)
  - **Front-left wing**: 5 × 6 hip projecting forward/left, pitch 7/12
  - **Right-rear wing**: 6 × 4 hip projecting back/right, pitch 7/12
  - **Chimney prism**: 1.2 × 1.2 × 3.5 box on the main rear slope (5 facets — 4 walls + top cap)
  - 2 explicit valley edges where the wings intersect the main body
  - Generates **17 facets, 40 edges, 7 anomalies, 119 rafters, 12 gutter polylines + 12 downspouts**
- ✅ **🛠️ Default fallback** — `build_topology()` now defaults to `stratex_demo` (instead of `cross_hip`). Existing jobs with set styles keep their selection.
- ✅ **🆕 Dropdown** — new-job form lists the demo style first ("STRATEX Compound Demo (recommended)") and defaults to it.
- ✅ **🟢 All 3 Tri-Layer toggles ON by default** — ROOFING + FRAMING + GUTTERS visible from the moment the 3D canvas loads, so the full forensic stack shows immediately without operator interaction.
- ✅ Verified end-to-end: created `stratex_demo` job → Phase 1 PASS → operator launch → DATA_CAPTURE_COMPLETE with 17 facets → 3D canvas renders the compound roof with chimney + anomaly patches + dimension callouts (screenshot confirmed).

## What's Been Implemented (2026-02-28 — v2.9.0 — 24h Reminder Background Sweep)
- ✅ **🔔 24h reminder background scheduler** — `_reminder_24h_sweep_loop()` runs as an asyncio task started in `on_startup`. Every 15 min (configurable via `REMINDER_SWEEP_INTERVAL_S`) it scans for jobs with `scheduled_launch_at` in the 23–25h window (lead=24h ± 1h, configurable) AND `reminder_24h_sent_at` absent. Fires SMS (Twilio) + email (Resend) reminders to the homeowner, flips `status: PHASE1_BLOCKED → RESCHEDULED_CONFIRMED`, stamps `reminder_24h_sent_at` for idempotency, records audit event `REMINDER_24H_SENT`. Cleanly cancelled in `on_shutdown`.
- ✅ **🛠️ Manual trigger** — `POST /api/contractor/run-reminder-sweep` returns `{swept_at, sent, errors}` for ops/QA without waiting for the 15-min tick.
- ✅ Frontend: new `RESCHEDULED_CONFIRMED` status added to `STATUS_LABEL` ("Reschedule Confirmed", volt-green).
- ✅ Re-running Phase 1 from `RESCHEDULED_CONFIRMED` allowed (the auto re-check the morning of the scheduled scan).
- ✅ E2E smoke: created a target=now+24h job → manual sweep returned `sent:1` → job status flipped → audit shows full 5-event chain (`PHASE1_FAIL → PHASE1_FAIL_EMAIL_SENT → HOMEOWNER_DELAY_NOTIFIED → HOMEOWNER_SCHEDULED_VIA_SMS → REMINDER_24H_SENT`). Re-sweep returned `sent:0` (idempotent ✓).

## What's Been Implemented (2026-02-28 — v2.8.0 — Launch Countdown Badge)
- ✅ **⏱️ Live launch-countdown badge** on the Pipeline rows + Job Detail header. New component `/components/LaunchCountdownBadge.jsx` ticks every 30s, reads `job.scheduled_launch_at`. Four tiers with distinct color + pulse behavior:
  - `future` (≥7 days) — cyan, no pulse, "LAUNCHES IN 12D"
  - `soon` (24h–7d) — neon green, no pulse, "LAUNCHES IN 2D 4H"
  - `imminent` (<24h) — orange, **pulsing**, "LAUNCHES IN 18H 14M"
  - `ready` (≤1h or past) — red, **pulsing**, "READY TO LAUNCH"
- ✅ Auto-surfaces locked-in jobs at a glance — turns the pipeline into a live launch-cadence dashboard. Visually verified on `/contractor` route: orange "LAUNCHES IN 18H 14M" pulses on the SMS-confirmed job, other rows render without the badge as expected. `data-testid="launch-countdown-badge"` + `data-tier="…"` attributes for E2E.

## What's Been Implemented (2026-02-28 — v2.7.0 — 2-Way SMS Reschedule Loop)
- ✅ **🔁 Twilio inbound SMS webhook** — new public `POST /api/twilio/inbound-sms` (form-encoded; Twilio standard). Homeowner texts back `1`/`2`/`3` → backend matches sender phone to most-recent `PHASE1_BLOCKED` job, locks `scheduled_launch_at` + `scheduled_window_label` + `scheduled_via="homeowner_sms_reply"`, responds with TwiML confirmation message that Twilio relays to the homeowner. Audit event `HOMEOWNER_SCHEDULED_VIA_SMS` captures the choice, the selected ISO, and the Twilio MessageSid.
- ✅ **📤 Numbered SMS body** — outbound `_homeowner_delay_sms_body` now lists windows as `1) … 2) … 3) …` with "Reply 1/2/3 to confirm" CTA.
- ✅ **🎯 "Homeowner Locked In" banner** on the contractor `reschedule-card` (data-testid `homeowner-scheduled-banner`) showing the confirmed window + the source (SMS reply / manual). Volt-green confirmation aesthetic.
- ✅ **Job state extensions**: `proposed_windows` persisted on notify so reply mapping survives restarts; `scheduled_launch_at`, `scheduled_window_label`, `scheduled_via`, `scheduled_at` fields added.
- ✅ Twilio webhook setup: in Twilio Console → Phone Numbers → your number → Messaging → **A MESSAGE COMES IN** → set to `{REACT_APP_BACKEND_URL}/api/twilio/inbound-sms` (POST). Twilio will form-POST `From`, `Body`, `MessageSid`.

## What's Been Implemented (2026-02-28 — v2.6.0 — Twilio SMS Homeowner Delay Notify)
- ✅ **📲 Twilio SMS channel** layered on top of the email Phase-1-delay notification. `POST /api/contractor/jobs/{id}/notify-homeowner-delay` now accepts `homeowner_email` AND/OR `homeowner_phone` and fans out to both Resend (email) and Twilio (SMS). Either channel mocks gracefully when its credential env (`RESEND_API_KEY` / `TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN,TWILIO_FROM`) is absent. E.164 validation (`^\+[1-9]\d{6,14}$`) on phone — invalid → mock+skip without erroring the whole call. `twilio==9.10.9` added to requirements.txt.
- ✅ **🆕 Homeowner phone field** on the New Job form (`data-testid="job-homeowner-phone"`), separate email field (`data-testid="job-homeowner-email"`). Both optional; backend already supported them.
- ✅ Audit log event `HOMEOWNER_DELAY_NOTIFIED` now records BOTH `email_mocked` and `sms_mocked` flags (or `null` for skipped channel). New job fields `delay_notified_sms` for idempotency tracking.
- ✅ Notify button toast now shows per-channel status: "email LOGGED · SMS LOGGED · 1 window" (mocked) vs "email sent to X · SMS sent to +Y" (live).

## What's Been Implemented (2026-02-28 — v2.5.1 — Homeowner Weather-Delay Notification)
- ✅ **🤝 One-click "Notify Homeowner of Delay"** — new `POST /api/contractor/jobs/{id}/notify-homeowner-delay` endpoint. Visible as a button on the `reschedule-card` of any `PHASE1_BLOCKED` job in the contractor portal. Pulls the next 3 ASTM-compliant launch windows and emails the homeowner in friendly, non-technical language (Helvetica white-glove template, NOT cyber-industrial). Records `HOMEOWNER_DELAY_NOTIFIED` audit event with `mocked` flag + window count. Button shows persistent ✓ checkmark with truncated email once notified. Helper: `_homeowner_delay_email_html`.
- ✅ Frontend `notify-homeowner-delay-btn` (data-testid'd) with idempotency UX (disabled after first notification using `job.delay_notified_to`).

## What's Been Implemented (2026-02-28 — v2.5.0 — Phase 1 Email Notify + Operator Weather Pulse)
- ✅ **📧 Automated Phase 1 ASTM Weather-Abort Email** — when `POST /api/contractor/jobs/{id}/run-phase1` returns `overall=FAIL`, the backend now auto-fires a Resend email to the contractor with the failing gates + the next 3 ASTM-compliant launch windows. Audit log captures a `PHASE1_FAIL_EMAIL_SENT` event (with `mocked: true/false`). RESEND_API_KEY unset → email gracefully mocked but audit row still written. New helpers: `_phase1_fail_email_html`, `_safe_reschedule_windows`, `_live_weather_pulse`.
- ✅ **🛰️ Operator-side Live Weather Pulse** — new endpoint `GET /api/operator/jobs/{id}/weather-monitor` (operator_only, returns same payload as contractor variant). New `op-weather-monitor-card` on `/operator/jobs/:id` renders for jobs in `PENDING_FIELD_CAPTURE` or `IN_FLIGHT` status; polls every 30s with abort badge (`op-weather-abort-badge`) when any ASTM gate breaches.
- ✅ **🧪 iteration_13 testing agent**: backend 6/6 (v2.3) + frontend 100% + v2.2 regression suite green after stale assertion fix.

## What's Been Implemented (2026-02-27 — v2.4.0 — STRATEX™ Vision UI Upgrade)
- ✅ **🎨 Tactical Cyber-Industrial Console aesthetic** — `#0B0F19` ambient backdrop, frosted-glass overlay cards (`backdrop-blur: 16-18px`), thin neon teal/orange borders with inset glow.
- ✅ **🧊 Color-coded geometry** — Ridges (cyan), Valleys (plasma orange), Hips (mid-teal), Eaves (silver). Edge opacity tuned per classification (valleys most visible).
- ✅ **🟦 Facet orientation segmentation** — each facet colored by its dominant normal direction: front-facing → cyan, rear-facing → warm bronze (`#c99a5e`), side-facing → steel-teal (`#8fb8c6`).
- ✅ **📐 Blueprint grid texture** — every facet rendered with a procedural canvas-generated grid pattern texture (16×16 fine + 4×4 heavy axes), planar-projected onto the dominant plane, tinted by facet orientation color, additively glowing via `emissiveMap`.
- ✅ **🔥 Heat-mapped anomaly patches** — anomaly polygons render as orange additive-blended overlays sized proportional to `area_affected_sf / facet_area`, with pulsing edge opacity.
- ✅ **📏 Dimension callouts** — the longest 2 edges per classification (8 total) get crisp white technical-font length labels overlaid on the canvas (HTML over WebGL), color-tinted per classification with glow.
- ✅ **🏷️ Project Identity card** (`ProjectIdentityCard`) — top-left frosted card with circular shield logo, Project ID, Principal/CEO, Property.
- ✅ **📊 STRATE™ Quant™ Estimation card** (`QuantEstimationCard`) — bottom-left summary: Total Squares · Valleys (LF) · Gables/Hips (LF) · Ridges (LF) · Total Roof SF.
- ✅ **💰 Anomaly Monetization Engine card** (`AnomalyMonetizationCard`) — bottom-right floating asset card showing `Anomaly #XX: Diagnosis (X sq.ft.)` + dollar value (proposal total proportionally allocated by anomaly area share) + cyan diamond accent.
- ✅ **🌡️ Enhanced Forensic Overlay PiP** — vertical thermal scale axis (+25°C / +5°C / −15°C), `640×512 IR · FLIR Iron` label, gradient legend bar (navy→magenta→orange→white).
- ✅ **🎥 3/4 isometric camera framing** — 28° FOV, elevated position (1.4× span), positioned to mirror the reference image angle.
- ✅ **✨ Ground glow plate** — radial cyan gradient under the model + tactical grid floor at 35% opacity gives the "blueprint laid out on a console table" depth illusion.

## What's Been Implemented (2026-02-27 — v2.3.0 — ASTM C1153 Live Weather)
- ✅ **🌦️ REAL Open-Meteo integration** (free, no API key) replacing all 3 weather mocks in Phase 1 Digital Gatekeeping.
- ✅ **4 ASTM C1153-compliant thermographic gates** wired into `_astm_phase1()`:
  1. **Pre-Rain 24h Lookback** — FAIL if past_24h precipitation > 0.05" (`Delayed_Surface_Moisture`); WARN if 0.01–0.05".
  2. **Solar Loading (12h Cloud Cover)** — FAIL if avg cloud cover past 12h > 70% (`Delayed_Insufficient_Solar_Load`); WARN if 50–70%.
  3. **Forecast 2h Buffer (Incoming Front)** — FAIL if next 2h precipitation probability > 30% OR forecast precip > 0.01" (`Delayed_Incoming_Front`).
  4. **Sustained Wind** — FAIL if > 8 mph; WARN if 5–8 mph; PASS if ≤ 5 mph.
- ✅ **Fail-closed network behavior** — if Open-Meteo is unreachable, all 4 weather gates auto-FAIL with "Weather telemetry unavailable" rather than launching blind.
- ✅ **Phase 1 now shows 6 distinct rows** (FAA + 4 weather + GIS) instead of the previous 3, giving contractors line-by-line ASTM-compliance visibility on every dispatch.
- ✅ **Verified live**: Lexington KY (0.67" precip past 24h, 97% cloud past 12h) → **2 FAIL rows blocking launch**. Phoenix AZ (0.00" precip, sunny) → all 4 weather rows PASS.

### Still mocked
- FAA / LAANC Airspace (no free public FAA API; ~10% WARN / 4% FAIL per job-id hash)
- Utility & Power-Line GIS (paid GIS API later)
- Resend email (no API key set)
- Fleet telemetry (procedurally generated)

## What's Been Implemented (2026-02-26 — v2.2.0 — Model A + Risk Engine)
- ✅ **💰 Model A Pricing** — replaced 5 legacy tiers with **2 production tiers**: **On-Demand** ($98/mo + $350/drop, 0 included) and **Volume Builder** ($998/mo + 4 drops included + $198/extra drop, marked CORE TARGET).
- ✅ **🛂 Phase 1 — Digital Gatekeeping** — `POST /api/contractor/jobs/{id}/run-phase1` runs 3 deterministic mocked checks (FAA LAANC airspace, Doppler micro-weather, GIS utility lines). On FAIL the job status becomes `PHASE1_BLOCKED` and operator cannot pull it. UI shows a `Phase1Card` with PASS/WARN/FAIL pills + descriptive details.
- ✅ **🪪 Phase 2 — On-Site Physical Safety** — operator tablet sign-off on `homeowner_verified`, `vertical_obstruction_clear`, `k9_and_child_clear_zone`. Each row has SIGN OFF / UNDO toggles + alert-red LED until cleared.
- ✅ **📡 Phase 3 — Hardware Diagnostic Lock** — `battery_cell_variance_v < 0.020 V`, drone battery ≥ 90%, RTK centimeter-lock, communication uplink "Strong / Starlink Verified", trailer hatch optical sensor, micro-weather clear. Software-locked launch — if any sub-check fails, the AUTHORIZE button stays disabled.
- ✅ **🚨 Dry-Run Penalty (flag-only)** — operator `POST /api/operator/jobs/{id}/dry-run` with reason picker (locked_gate / unnotified_homeowner / aggressive_animal / wrong_address / other) + optional notes. Adds $150 to `billing_meter.dry_run_charges_usd` on the contractor's current month bucket. NO instant Stripe charge — penalty rolls into next month's invoice. Contractor sees a red alert banner on the job detail.
- ✅ **🔐 Immutable Audit Trail** — new `preflight_audit` collection. Every Phase 1 result, Phase 2/3 failure, LAUNCH_AUTHORIZED event, and DRY_RUN_FLAGGED gets appended. Endpoint `/api/contractor/jobs/{id}/audit-log` (owner-only). UI `AuditLogPanel` is collapsible on the contractor job detail.
- ✅ **📊 Billing Meter** — `/api/contractor/billing/meter` returns the upcoming invoice breakdown: monthly retainer + drops_used/included + overage charges + dry-run penalties + estimated total. Rendered as a "Current Month" panel under the pricing tiers.
- ✅ **Robust 422 handling** — axios response interceptor flattens Pydantic validation arrays into readable toast strings (no more React-child crashes from raw error objects).
- ✅ **iteration_12 testing agent**: 100% backend (12/12 pytest) + 100% frontend.

## What's Been Implemented (2026-02-26 — v2.1.0)
- ✅ **🛰️ Esri Satellite Tile Upgrade** — `MapPicker` now defaults to Esri World Imagery with a SAT/MAP toggle; operator dispatch target map also uses satellite. Free, no key required.
- ✅ **⏳ Animated 4-Agent Streaming UX** — clicking "Compute Proposal" runs a paced visual: Forensic → Validation → Reconciliation → Jurisprudential, each phase advancing every 900ms with spinning → checkmark transitions.
- ✅ **🚛 Fleet Command** — new `/fleet` page (contractor + operator). Continental satellite map with 6 STRATEX rigs (Vanguard, Outrider, Horizon, Raven, Sentinel, Obsidian), KPI strip (Total/Deployed/Standby/Charging/Maintenance/Avg Battery), rig roster panel with battery/uplink/RTK telemetry. Polls every 6s with deterministic rotation through STANDBY/CHARGING/DEPLOYED/IN_FLIGHT/MAINTENANCE states.
- ✅ **📧 Resend Email Integration** — `POST /api/contractor/jobs/{id}/email-proposal` (PDF attachment) + `POST /api/auth/email-nda`. Gracefully mocks when `RESEND_API_KEY` is unset (returns `{ok:true, mocked:true}`). HTML templates designed in STRATEX cyber-shield aesthetic.
- ✅ **💳 Stripe Subscription Billing** — `/billing` Pricing page with 3 tiers: Starter $99 / Pro $299 (highlighted) / Enterprise $999. Uses Emergent-managed test key `sk_test_emergent`. Full flow: create-checkout → Stripe-hosted checkout → `/billing/success` polls `/billing/status/{session_id}` → idempotently upgrades user subscription_tier on `payment_status="paid"`. Webhook handler at `/api/webhook/stripe` also catches `checkout.session.completed`. 20s timeout + 1 retry around upstream Stripe proxy to avoid 502 hangs.
- ✅ **🔐 Emergent Google Sign-In** — `AuthCallback.jsx` detects `#session_id=…` hash, calls `/api/auth/google/session` which exchanges with `EMERGENT_AUTH_URL` and either creates a new contractor account (NDA still required) or signs in an existing one, issuing a STRATEX JWT. "Continue with Google" button on `/auth`.
- ✅ **🛡️ MaterialsConfig Pydantic Validation** — all percentage fields bounded 0–100, all price fields non-negative and ≤ $100k. 422 on violation.
- ✅ **Backend Code Quality** — Stripe upstream call now bounded by `asyncio.wait_for(20s)` + 1 automatic retry.

## What's Been Implemented (2026-02-26 — v2.0.0)
- ✅ **Dual-Portal Auth** — JWT (60-min access + 7-day refresh) + bcrypt + TOTP MFA via `pyotp`. 2-step login (creds → MFA). QR enrollment for new signups. Auto-fetch TOTP via `/auth/totp-debug` (gated by `DEMO_MFA_BYPASS=1`).
- ✅ **NDA Gateway** — Typed-name signature must match registered legal name; IP + UTC timestamp captured; full agreement text rendered with placeholders; `nda_accepted` boolean gates contractor portal access.
- ✅ **AES-256 Business Brain** — Fernet symmetric encryption with HKDF-SHA256 key derivation from `AES_KEY` env. All private financial fields (overhead_pct, profit_margin_pct, labor rates, insurance supplement, wholesale unit prices) stored as opaque `_encrypted` payload.
- ✅ **Leaflet + OpenStreetMap Map Dispatch** — `MapPicker.jsx` component with cyber-teal SVG pin, click-to-drop, Nominatim search + reverse geocode, live lat/lon readouts. Operator detail page shows read-only target map.
- ✅ **Role-Aware Nav** — Contractor: Pipeline / New Job / Business Brain / Logout. Operator: Job Board / Logout. Anon: Sign In. Mobile drawer + role pill badge.
- ✅ **Cross-Portal Isolation** — Backend `role_dep` returns 403 if wrong role accesses an endpoint; operator job views strip `pricing`, `homeowner_email`, `homeowner_phone` keys.
- ✅ **Security Banner** — Permanent banner across contractor pages declaring AES-256 hardware-isolated encryption + ZERO operator visibility.
- ✅ **Job Lifecycle** — DRAFT → PENDING_FIELD_CAPTURE → IN_FLIGHT → DATA_CAPTURE_COMPLETE → PROPOSAL_READY → AUDIT_APPROVED → SENT_TO_HOMEOWNER. State transitions verified.
- ✅ **Seeded Accounts** — admin@stratex.io, anthony@apexroofing.com (contractor, NDA pre-accepted), pilot@stratex.io (operator). Test credentials documented in `/app/memory/test_credentials.md`.
- ✅ **Backend regression suite** at `/app/backend/tests/test_stratex_v2.py` (18/18 PASS via iteration_10 testing agent).
- ✅ **Legacy v1 pages deleted** — NewMission, MissionDashboard, Projects, Fleet, Reports removed (kept inside JobDetail under contractor portal).
- ✅ **iteration_10 testing agent run**: 100% backend + 100% frontend pass.

## What's Been Implemented (2026-02 — v1.x carry-over)
- ✅ Multi-facet 3D roof topology engine (`roof_topology.py`) with 5 presets (cross-hip / hip / gable / l-shape / dutch-gable).
- ✅ Vanilla three.js (in React `useEffect`) wireframe model with anomaly facet overlays + click-to-isolate.
- ✅ ReportLab PDF "Homeowner Proposal" supplement generator.
- ✅ Multi-agent Claude Sonnet 4.6 narrative via emergentintegrations + EMERGENT_LLM_KEY (deterministic fallback if network fails).
- ✅ Mobile / iPhone 13 Pro responsive layout, safe-area-insets, PWA tags, 44px tap targets.

## Prioritized Backlog
### P1 — Next sprint
- 🟡 **Refactor `server.py`** (1228 LOC) into `routes/{auth,contractor,operator,billing,fleet,email,pdf}.py`.
- 🟡 **Resend API key wiring** — when the user supplies `RESEND_API_KEY`, real email delivery flips on automatically.
- 🟡 **Stripe webhook signature verification end-to-end** — currently using emergentintegrations defaults (works in test mode).
- 🟡 **Per-row data-testids on Pipeline table** for E2E test stability.

### P2 — Future
- Real image upload for caliper edge measurement (Emergent object storage). *(Skipped in v2 — drone mesh measurements replaced it.)*
- Switch from `@app.on_event("startup")` to FastAPI `lifespan` context (deprecation hardening).
- Stripe customer portal link for cancellation/upgrades.
- Multi-tenant white-label theming (Enterprise tier feature).
- Auto-retry email delivery on transient Resend failures.
- Real-time websocket fleet telemetry (replace 6s poll).

## Key DB Collections
- `users` — `{id, email, legal_name, company_name, role, password_hash, totp_secret, totp_enrolled, nda_accepted, nda_signed_at, nda_signed_ip, created_at}`
- `ndas` — signed NDA records with rendered_text + ip + signed_at
- `materials_configs` — `{user_id, _encrypted, <public brand fields>, updated_at}`
- `jobs` — full lifecycle document with `roof_telemetry`, `anomalies`, `mission`, `agent_reports`, `pricing`

## Key API Endpoints
- `POST /api/auth/signup` — creates user, returns TOTP setup URI/secret
- `POST /api/auth/login` — step 1: email+password → `mfa_required:true`. step 2: + `totp_code` → tokens
- `POST /api/auth/refresh` — refresh access token
- `GET /api/auth/me` — current user
- `GET /api/auth/totp-debug?email=…` — DEMO only (gated by `DEMO_MFA_BYPASS=1`)
- `GET /api/auth/nda-preview`, `POST /api/auth/accept-nda`
- `GET/PUT /api/contractor/materials` (AES-256 round-trip)
- `POST/GET /api/contractor/jobs[/{id}]`, `POST .../compute-proposal`, `.../audit-approve`, `.../mark-sent`, `.../report.pdf`
- `GET /api/operator/jobs[/{id}]` (pricing-stripped), `POST /api/operator/jobs/{id}/launch`
