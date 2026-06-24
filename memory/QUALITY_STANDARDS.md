# STRATEX™ — Quality Standards (CEO Directive · LOCKED)

## 3D DIGITAL TWIN — NON-NEGOTIABLES
Every 3D twin presented to the CEO or any prospect MUST meet these standards.
NEVER present a "wireframe-only / amateur" 3D twin again.

### Mandatory rendering features
- **Filled shaded surfaces** with sun-direction lighting (three-point: sun + cyan fill + orange rim)
- **Multiple stroke weights**: heavy outer edges, medium ridges/valleys, light internal hatching
- **Edge classification colors**: ridge cyan · valley magenta · hip amber · eave orange · rake light-cyan
- **Material textures**: shingle = dark slate w/ subtle metalness · decking = warm tan w/ plywood seams · framing = lumber-brown cylinders (not lines)
- **Plywood seam grid** overlay on Layer 2 (4×8 sheets)
- **Cylindrical rafter geometry** on Layer 3 (not just lines — actual 3D bodies)
- **PCF soft shadows** with shadow map ≥ 1024×1024
- **ACES Filmic tone mapping** + 1.15× exposure
- **Compass/North arrow** at ground plane
- **Subtle context grid** + circular ground plate
- **Auto-rotate** with pointer-drag orbit (touch + mouse)
- **Anti-aliased** + devicePixelRatio capped at 2 for crisp lines

### Camera & composition
- 3/4 isometric (theta ≈ π/4, phi ≈ 0.55) — never straight-on
- Background: radial gradient #122035 → #03070C (not flat black)
- Border: 1px cyan @ 18% opacity + inset glow

## REPORT (PDF) — NON-NEGOTIABLES
- 100% reconciliation on every total (no rounding > 0.1%)
- Brand wordmark: STRAT silver-gradient + EX cyan-outline italic + ™
- Tabloid 17×11" landscape, Playwright-rendered
- All headers carry the brand glyph + wordmark + crumb
- Tables: full mono font, alternating row tint, mono headers

## DASHBOARD (UI) — NON-NEGOTIABLES
- Mobile-first: NO horizontal overflow at iPhone width (393 px)
- Currency: NEVER truncate ("$33,9..." is not acceptable); use break-words + smaller breakpoint
- Time units: per-hour for labor rates · per-year ONLY for annual energy loss · per-day for project duration
- Buttons: whitespace-nowrap on action CTAs · shrink-0 to prevent address text from overlapping
- "FULL PDF REPORT" — never label with a page count that goes stale

## CEO REVIEW PROTOCOL
Before presenting ANY screen or PDF to the CEO:
1. Self-screenshot at iPhone 393×852 viewport
2. Verify no text overflow, no truncation, no overlap
3. Verify 3D twin meets ALL mandatory rendering features above
4. If any check fails, FIX before presenting
