# STRATEX™ — PRD & Build Log

## Original Problem Statement
STRATEX™ (Strategic Thermal Reconnaissance & Automated Topology Estimator) — an investor-ready, dark-mode HUD platform that pairs an autonomous solar-powered drone trailer (DJI Dock 2 + Raspberry Pi) with a multi-agent AI core (Forensic, Validation, Reconciliation, Jurisprudential) to deliver insurance-grade roofing estimates without a human ever climbing a ladder. Three modules: STRATEX Vision™ (3D photogrammetry), STRATEX Thermal™ (radiometric moisture mapping), STRATEX Quant™ (multi-agent actuarial estimating with Xactimate billing tags + 20/25 O&P lock).

## User Personas
- **Roofing Contractor / Project Manager** — initiates missions, configures scope, reviews pricing
- **Insurance Adjuster** — consumes the forensic/validation/jurisprudential narratives and Xactimate-tagged line items
- **Investor / VC** — sees the polished dashboard, Quant pricing engine, fleet rig spec, and trailer hardware

## Core Requirements (Static)
- 5-step pre-flight wizard: Intake & Auth → Scope Matrix → Macro-Edge Caliper → Quant Pricing → Launch Portal
- Caliper rule: thickness > 1.00" ⇒ 2 layers + Complete Tear-Off Required + ×1.5 labor & dumping multipliers
- Pricing math: insurance projects locked at 20% Overhead / 25% Net Profit; private cash pay 10/10
- Every line item carries an Xactimate billing tag (RFG ASV, RFG OSB, RFG LAB, etc.)
- Pre-flight gate: trailer_hatch_secured, drone_battery_percentage=100, rtk_gps_signal=Centimeter-Level Locked, comms=Strong/Starlink Verified, weather=clear — ALL TRUE before launch
- Multi-agent narrative reports (Forensic, Validation, Reconciliation, Jurisprudential)
- Brand: Cyber-Shield theme — matte obsidian #06080B, cyber teal #00F0FF, volt green #39FF14, plasma orange #FF5500, silver-white text

## Architecture
- **Backend**: FastAPI + Motor (MongoDB) + emergentintegrations (Claude Sonnet 4.6 via EMERGENT_LLM_KEY)
- **Frontend**: React 19 + react-router + Tailwind + shadcn primitives + sonner + lucide-react
- **Routes**: `/`, `/mission/new`, `/mission/:id`, `/projects`, `/fleet`, `/reports`
- **API**: `/api/projects` (CRUD), `/api/projects/{id}/caliper`, `/api/projects/{id}/pricing`, `/api/projects/{id}/launch`

## What's Been Implemented (2026-02 — v1.2.0)
- ✅ **Roof Topology Engine** (`/app/backend/roof_topology.py`) — full multi-facet geometric engine. Presets: cross-hip, hip, front-gable, L-shape, dutch-gable. Each facet has 3D polygon vertices, normal vector, planar area, true area (sec(θ) corrected), pitch and color tag. Edges classified as ridge / valley / hip / eave / rake by adjacent-facet geometry. Architectural docstring documents the full SfM → MVS/NeRF/3D Gaussian Splatting → mesh extract → RANSAC facet segmentation → dihedral edge classification → RTK calibration → thermal fusion pipeline.
- ✅ **Roof Style Selector** added to NewMission Step 2 — 5 topology presets, drives the 3D model + pricing math.
- ✅ **Advanced Diagnostics dashboard** (3-column layout matching the reference image):
  - LEFT rail: Project meta + STRATEX Quant™ Estimation card (Total Squares / Ridges / Valleys / Hips / Eaves / Rakes-Gables / Primary Pitch / RTK Precision / Topology) + Caliper Result
  - CENTER: Interactive 3D multi-facet wireframe model with anomaly-on-facet polygons + floating callout labels ("Anomaly ID: AD-KY041-001") + click-to-isolate raycaster + edge legend (ridge/valley/hip/eave)
  - RIGHT rail: Forensic Overlay panel (Diagnosis / Facet Location / Area Affected sq.ft. / Confidence % / Thermal Δ + procedural FLIR Iron palette thermal heatmap canvas) + Anomaly Field selector with severity LEDs
- ✅ **Facet-localised anomalies** — every anomaly is now attached to a specific facet (F1, F2, ... or A1, B1, etc.), with area_affected_sf computed from the facet area, AD-KY041-XXX id format, lat/lon, centroid, confidence.

## What's Been Implemented (2026-02 — v1.1.0)
- ✅ **Interactive 3D Spatial Model (vanilla three.js)** — cyber-teal wireframe gable-hip roof generated procedurally from drone telemetry (ridge_lf, eaves_lf, pitch_num). Glowing plasma-orange anomaly polygons placed on the actual roof facets. Auto-rotating orbit camera with mouse drag/zoom. Lives at `/app/frontend/src/components/RoofModel3D.jsx`.
- ✅ **Wizard restructured to 5 steps** — Intake → Scope → Caliper → **STRATEX Vision™ Mesh Capture** (NEW step 4 with auto-scan + 3D model + anomaly list) → Launch Portal. Calculations DO NOT appear until after the mesh is locked (per user feedback).
- ✅ **Mission Dashboard reorganized** — 3D roof model is now the hero card; Quant™ pricing is rendered BELOW it (mesh-first derivation order verified by testing agent y-coords 276 vs 2119).
- ✅ **PDF Supplement Export** — `GET /api/projects/{id}/report.pdf` builds a Cyber-Shield themed adjuster supplement packet via ReportLab (header card, 4 agent narratives, anomaly table, Xactimate line-items, O&P summary). Download button on Mission Dashboard + Reports list.
- ✅ **Preflight battery relaxed** from strict 100 to >=90.
- ✅ **Launch progress UX** — staged ProgressLine indicators (uplink → narrative → seal) during the ~90s Claude generation.
- ✅ Landing page now embeds a live 3D mesh preview in the Spatial Model section.

## What's Been Implemented (2026-02 — v1.0.0 MVP)
- ✅ Landing page (hero + 3 module pillars + fleet command preview + dashboard montage + CTA)
- ✅ 5-step wizard with HUD progress bar, segmented step indicators, glowing buttons
- ✅ Caliper analysis with auto tear-off override and labor/dump multiplier scaling
- ✅ Quant™ Reconciliation Engine (shingle bundles, OSB, drip edge, ice & water, ridge cap, starter, flashing, fasteners, labor hours, disposal tons) with 20/25 O&P insurance lock or 10/10 retail
- ✅ Xactimate billing tags mapped to every line item
- ✅ Preflight checklist with LED indicators (volt-green OK / plasma-orange alert)
- ✅ Mission launch simulation (Raspberry Pi relay command, autonomous orbit flight path) + anomaly detection
- ✅ Claude Sonnet 4.6 multi-agent narrative generation (Forensic, Validation, Reconciliation, Jurisprudential) via Emergent LLM Key
- ✅ Mission Dashboard with 3D wireframe placeholder, telemetry readouts, 4 agent panels, anomaly grid, locked pricing table
- ✅ Project Ledger + Reports + Fleet Command pages
- ✅ Full Cyber-Shield HUD design system (Orbitron + Rajdhani + Sora + JetBrains Mono fonts, scanlines, corner notches, glow pulses)
- ✅ All data-testid attributes for testing
- ✅ Backend 13/13 pytest, Frontend full E2E verified

## Prioritized Backlog (P0/P1/P2)
- **P1** Relax preflight `drone_battery_percentage` gate to ≥ 90 for demo flexibility
- **P1** Real-time launch progress UX ("Generating forensic narrative…" while Claude streams)
- **P1** PDF/JSON export of forensic report for insurance supplement packets
- **P2** Real image upload for caliper edge (replace simulated) via Emergent object storage
- **P2** Real-time mission map (Leaflet/MapboxGL) with GPS-stamped anomaly pins
- **P2** Live 3D mesh viewer (three.js + GLTF) instead of static photogrammetry image
- **P2** Multi-trailer fleet dispatch UI with live status board
- **P2** Stripe per-mission billing for contractor SaaS subscriptions
- **P2** Auth (Emergent Google OAuth) for multi-user contractor accounts

## Next Tasks
- Add export-to-PDF for insurance-ready supplement reports
- Add streaming progress indicator during the ~90s Claude generation
- Optional: integrate real Mapbox map + 3D mesh viewer
