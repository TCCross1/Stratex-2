# STRATEX™ 3D Visualization — Multi-Agent Expert Panel Review
**Date:** 2026-02-28 · **Status:** RATIFIED — implementation aligned

A 4-agent expert panel was convened to ratify the design rules for the STRATEX Vision
3D digital-twin renderer. **NO drone-derived geometry / texture data should reach the
renderer until it has been validated against the consensus rules below.** These rules
codify roofing/framing/gutter/CAD craft practices and govern every layer of the canvas.

---

## Agent 1 — Master Framing Carpenter & Licensed Architect
**Charter:** Structural framing geometry, rafter spacing, hip/ridge boards, sub-fascia.

**Rules ratified:**
- **F1.** Rafters run PERPENDICULAR to ridges/hips, PARALLEL to the slope direction. Never horizontal across a facet.
- **F2.** Rafter spacing follows IRC §R802.4: 16" or 24" on-center based on span. Default = 16" o.c.
- **F3.** Every 3rd rafter is rendered HEAVIER (radius 0.085) representing a doubled trimmer at facet intersections. Standard rafters use radius 0.045.
- **F4.** Sub-fascia is a continuous structural board along EVERY eave, ~6-8" deep, sitting 0.5 units below the eave plane. Rendered as a heavy tube radius 0.12.
- **F5.** Ridge boards & hip boards are explicit members rendered at the highest elevation, slightly thicker than rafters.
- **F6.** Framing color = bright neon cyan (#00F0FF) for rafters and ridge/hip boards. Sub-fascia accent = neon orange (#FF7A00) to differentiate the structural perimeter from interior framing.

---

## Agent 2 — Master Roofing Contractor (GAF/Owens Corning certified)
**Charter:** Asphalt, metal, slate material layout, course/seam direction, exposure dimensions.

**Rules ratified:**
- **R1. ASPHALT 3-TAB SHINGLES:**
    - Exposure: 5" (each course shows 5" of shingle face)
    - Shingle width: 36"; 3 tabs at 12" each separated by 2 vertical cuts (each cut ~2" deep)
    - Course direction: **ALWAYS PARALLEL TO EAVE.** Courses run horizontally.
    - Stagger: each course offset by 6" (half-tab) from the one below.
    - Render: dark base + neon cyan-blue (#1EA7FF) course separators + tab cuts.
- **R2. ARCHITECTURAL / DIMENSIONAL SHINGLES:** same as 3-tab but with random shadow staggers within each course; same direction.
- **R3. STANDING-SEAM METAL:**
    - Panel width: 16-24" (default 18")
    - Panels run **EAVE-TO-RIDGE** (vertical in slope direction). NEVER horizontal.
    - Raised seam at every panel edge.
    - Clip/rivet dots visible along each seam every 12-18".
    - Render: dark base + neon cyan (#00F0FF) seam lines + bright white rivet dots.
- **R4. SLATE TILES:**
    - Tile size: 12" wide × 18" tall (standard scallop)
    - Courses parallel to eave (like asphalt), staggered half-tile per course.
    - Render: dark base + neon violet (#C77DFF) scalloped tile outlines, lavender-white top edge (lit edge).
- **R5. All materials respect the slope direction** — texture orientation MUST be derived from the facet's slope-aligned basis, not the world-space axes.

---

## Agent 3 — Master CAD Designer (former Autodesk principal)
**Charter:** UV mapping, line weights, render hierarchy, neon stylization rules.

**Rules ratified:**
- **C1.** **Slope-aligned UV basis** per facet:
    - `N` = facet normal
    - `U` = `normalize(cross(N, worldUp))` (horizontal, along eave direction)
    - `V` = `normalize(cross(U, N))` (perpendicular to U on facet plane, up the slope)
    - Project vertex world position onto (U, V); divide by `REPEAT_FT` (default 4ft) so texture scale is constant across all facets regardless of facet size.
- **C2.** Edge weight hierarchy:
    - **Eaves & ridges:** BOLD (radius 0.10 tube or 3px line) — primary architectural reading
    - **Hips & valleys:** MEDIUM (radius 0.06)
    - **Rafters / tabs / seams / scallops:** THIN to MEDIUM (1.5-2.5 px in canvas)
- **C3.** **Neon glow** = additive-blended duplicate of every line offset by scale 1.004, opacity 0.35.
- **C4.** Anomaly heat patches use radial gradient + AdditiveBlending + `depthWrite: false`.
- **C5.** Per-facet outline color = layer accent (cyan-blue / cyan / violet / yellow / orange), NOT a generic orange wash.
- **C6.** No solid neon color wash on facet interiors. Interior must remain DARK so detail lines self-illuminate via `emissiveMap`.

---

## Agent 4 — Master Gutter Contractor (NRCA-certified)
**Charter:** Gutter routing, downspout placement, hangers, splash blocks, code compliance.

**Rules ratified:**
- **G1.** Continuous K-style gutter trough runs along EVERY eave edge — no gaps.
- **G2.** Profile: 5" standard / 6" heavy (selected by facet area + pitch per IRC Ch. 11).
- **G3.** Downspouts at every external corner + every 30-40 ft on long runs. Always drop to grade.
- **G4.** Each downspout has visible elbow elements: A-elbow at top, B-elbow at splash block.
- **G5.** Hangers every 24" o.c. (rendered as bright halo dots along the trough).
- **G6.** Render color = bright neon orange (#FF7A00) for ALL gutter geometry. Hangers = hot amber (#FFB877). Splash elbows = matching orange torus arcs at ground level.
- **G7.** Gutter is **always toggleable independently** of the primary roofing layer (XOR architecture preserved).

---

## Quality Gate — Pre-Render Validation Checklist
Every digital twin generation MUST pass these gates before rendering to UI:
- [ ] All facets carry a valid (U, V) slope basis (Agent 3 / C1)
- [ ] Texture orientation matches material rules (Agent 2 / R1–R5)
- [ ] Gutter polylines cover 100% of eave edges (Agent 4 / G1)
- [ ] Framing rafter count = `eave_length_ft / (oc_in / 12)` rounded up (Agent 1 / F2)
- [ ] No facet shows a solid neon color wash (Agent 3 / C6)
- [ ] Outline edge weights respect hierarchy (Agent 3 / C2)

If any gate fails, the renderer raises a `RoofTopologyValidationError` and surfaces the
specific rule violated. This prevents the "wrong layers" failure mode the user
reported and ensures the visual output remains within tolerance of the actual photogrammetry-derived geometry (target: ±1 cm per RTK calibration).
