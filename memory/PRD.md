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
- [x] **Command Deck (`/deck`) — vertical scrolling app rail with all 37 surfaces (Feb 2026)**
- [x] **3D Component Catalog page added to Adjuster PDF — 8 isometric SVG cards (J/F-Channel · Starter · Finish Trim · Drip Edge · Soffit · Inside Corner · Utility Trim). PDF now 17 pages.**
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
- Backend: **OPERATIONAL** · 13-page PDF renders in ~25s · sample endpoint <200ms
- Frontend: **OPERATIONAL** · Switchboard + analysis dashboard fully wired
- Demo flow: **READY for live pitch** (`/` → "New Drone Scan" → analysis → PDF)
- Production deployment (stratexdrone.com): **stale** — user must redeploy

## Architecture
- `/app/backend/` — FastAPI, MongoDB, Stripe, Emergent LLM key (Gemini), Twilio
- `/app/backend/agents/` — Expert Agent dispatcher + registry
- `/app/backend/data/manifests/` — Project Manager scan manifests
- `/app/frontend/` — React + Tailwind, lucide-react, sonner toasts
- `/app/stratex_pitch/` — pitch deck + AI render assets + demo report builder
- `/app/memory/` — PRD, TRIFECTA spec, test credentials
