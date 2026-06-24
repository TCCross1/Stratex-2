# STRATEX™ — Master Report-Spec Prompt

> This is the standard system prompt for the STRATEX-QUANT report-building AI.
> It is now baked into `/app/backend/routes/demo_scan.py` (`QUANT_SYSTEM`).

## How it's used
- Pasted as the LLM system message before every scan-analyze request
- Drives the 5-expert agent chain (GEOMETRY · MATERIAL · THERMAL · ENERGY · BIM_RENDER)
- Output is STRICT JSON consumed by `build_demo_report.py` → 15-page Tabloid PDF

## Report Pages (canonical order)
1. Cover · Final Project Report
2. Executive Envelope Summary (gauges + AI maintenance + thermal findings)
3. 3D Digital Twin & Geometry (anomaly atlas + radiometric overlay)
4. Layered System Reconstruction (Layer 1 Finish · Layer 2 Decking · Layer 3 Framing)
5. Window Schedule
6. Exterior Door Schedule
7. Wall Envelope + Siding Package (Geometry + Material Agents)
8. Wall Moisture + Vapor Barrier Analysis (Thermal Agent)
9. Energy Leakage Atlas (Energy Agent)
10. Bill of Materials (precision-to-cm SKU table)
11. Labor & Man-Hours (national + regional benchmarks)
12. Labor Gantt Sequence (phase timeline)
13. Profitability & Project Margins (pie split + commentary)
14. Side Quote · Unforeseen Repairs (probability-weighted reserve)
15. Tear-Off Recommendation (conditional, water-retention ≥ 70%)
16. Executive Summary · Certification & Repair Plan (signature block + disclaimer)

## Inputs (property dossier)
- address, city_state, year_built, ownership, region, notes
- Optional: uploaded scan photos (multipart)

## Audience
Insurance adjusters, engineers, property owners

## Design
Dark slate background, neon accents (teal/orange/red/green), Tabloid 17×11"
landscape, Playwright-rendered Chromium PDF

## Optional dual-version output (future)
- Technical version for adjusters
- Simplified homeowner-friendly version

(The actual prompt text lives in `/app/backend/routes/demo_scan.py` as the
`QUANT_SYSTEM` constant — kept in code so the LLM call stays in sync.)
