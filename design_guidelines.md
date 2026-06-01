# STRATEX™ Brand Bible · Permanent Design Guidelines

> **Locked by founder directive (2026-06-01).** Every screen, dashboard,
> dialog, and PDF MUST adhere to this aesthetic — Branch Manager view,
> Executive view, Pilot tablet view, Operator terminal, Contractor portal,
> and Investor demo. No exceptions. Apply with 8K-quality polish.

The reference North Star is the STRATEX logo (IMG_2137): a clean glowing
**electric cyan** house silhouette with an **amber prism** accent, set
against deep monochromatic blacks. Bright but never blown out. Premium,
modern, surgical.

---

## 1. Core Palette — `STRATEX FN v4.0-PROD-BRAND`

| Token | Hex | Purpose |
|---|---|---|
| `--stx-cyan`    | `#00E5FF` | Primary brand, scans/data/links, KPI accents |
| `--stx-amber`   | `#FFB020` | Capital, warnings, prism/logo accent, ROI |
| `--stx-green`   | `#00FF9C` | Validated/Authenticated/CONSENSUS_OK |
| `--stx-magenta` | `#FF2D78` | Critical alerts, RESTRICTED_PERIMETER_VIOLATION |
| `--stx-purple`  | `#C084FC` | Secondary categorical (scheduling, contractors) |
| `--stx-text`    | `#E2E8F0` | Body |
| `--stx-muted`   | `#7C8A9E` | Subtitles, meta |
| `--stx-divider` | `#1E293B` | Hairline borders |
| `--stx-bg-main` | `#080C14` | Page background |
| `--stx-bg-card` | `#0F172A` | Card surface |
| `--stx-ink`     | `#030712` | Sidebar / overlay base |

**Forbidden**: violet→indigo gradients on white, generic Tailwind
`bg-purple-500`, raw `#000`, low-contrast greys (>= `#94A3B8` on dark).

---

## 2. Neon Glow System

Every accent color carries its own **glow signature** — a layered
`text-shadow` + `box-shadow` pair using the color twice (tight + wide).
This is what gives STRATEX its "8K depth" feel.

```css
/* Token (use literally — do not invent new values) */
--stx-glow-text-tight: 0 0 10px currentColor;
--stx-glow-text-wide:  0 0 22px currentColor;
--stx-glow-box-tight:  0 0 14px <accent>;
--stx-glow-box-wide:   0 0 28px <accent>66;

/* Card hover lift */
box-shadow: 0 0 0 1px rgba(255,255,255,0.04) inset,
            0 22px 60px -22px <accent>33;
```

**Rules:**
1. Card titles + key metric numbers → `text-shadow: 0 0 12px currentColor`.
2. Pulse dots & status indicators → tight + wide layered glow (`0 0 14px`, `0 0 28px <c>66`).
3. Active nav buttons → outer + inset glow combo.
4. NEVER glow body copy or numerical tables — only accents.
5. Glow alpha caps: solid layer ≤ `currentColor`, ambient layer at `<c>33`–`<c>66`.

---

## 3. Typography

| Use | Family | Weight | Notes |
|---|---|---|---|
| Display headings | `Space Grotesk` | 700–800 | Uppercase, tracking `0.06em–0.10em` |
| Body | `Inter` (fallback) or `Space Grotesk` 400 | 400 | |
| Code / Mono / Telemetry | `JetBrains Mono` | 500–700 | Use for ALL labels, status text, tags |
| Logo lockup | as supplied (logo asset only) | — | |

**Forbidden**: Roboto, Arial, system-ui as primary. No serifs anywhere.

Letter-spacing for uppercase mono labels is **mandatory**:
- Small tags / chips: `letter-spacing: 0.22em–0.28em`
- Section eyebrows: `letter-spacing: 0.32em–0.36em`
- KPI labels: `letter-spacing: 0.16em`

---

## 4. Surface & Layering

Three legitimate surface levels:

1. **Ink (`--stx-ink`)** — sidebars, modal scrims, behind-glass.
2. **Page (`--stx-bg-main`)** — base scroll surface, gradient-tinted radial okay.
3. **Card (`--stx-bg-card`)** — material panels. Optionally a frosted
   glass variant: `background: rgba(11,16,28,0.55); backdrop-filter:
   blur(22px) saturate(150%);` paired with a 1px accent-color border.

**Border-left accent stripe** (4px solid) is the canonical "category
label" treatment on cards — match stripe color to the card's domain
(cyan = data, green = validated, amber = capital, magenta = critical,
purple = scheduling).

---

## 5. Component Patterns

### Pills / Chips
```jsx
<span className="stx-pill" style={{ borderColor: COLOR, color: COLOR }}>
  LABEL
</span>
```
Styling: `border: 1px solid currentColor; padding: 6px 12px;
border-radius: 2px;` (sharp corners), mono font, `text-shadow: 0 0 8px
currentColor`, `box-shadow: 0 0 10px currentColor` on hover.

### KPI Cards
- Border-left 4px accent stripe.
- Value: `font-size: 24px; font-weight: 800; color: #ffffff;
  text-shadow: 0 0 12px rgba(255,255,255,0.18);`
- Label: uppercase mono, `8.5px`, `letter-spacing: 0.5px`, color muted.

### Buttons
- Sharp corners (`border-radius: 2px–6px`) or fully pill (`9999px`).
- Disabled state: full opacity loss to `rgba(15,30,55,0.6)` with `#1E293B`
  border — **never grayscale a brand color**.
- Active CTA gradient: `linear-gradient(135deg, var(--stx-cyan), #0891b2)`
  with `box-shadow: 0 20px 50px -10px var(--stx-cyan)cc`.

### Frosted Glass Dock / Drawer
- `background: rgba(6, 10, 18, 0.55);`
- `backdrop-filter: blur(22px) saturate(150%);`
- 1px accent-color border at `<c>22`.
- 14px border-radius.
- 24px outer shadow at `rgba(0,0,0,0.65)`.

---

## 6. Iconography

- Library: `lucide-react` only. No emoji icons, no FA, no Material.
- Stroke size: `12px`–`18px` inside cards, `20px` for primary CTAs.
- Always assign `color` prop matching the contextual accent token.

---

## 7. Motion

- All transitions: 160ms–280ms ease (`transition: <prop> 220ms ease`).
- Pulse animation (status dots): 1.6s–2.2s ease-in-out infinite.
- Hover lifts: `transform: translateY(-1px)` + accent glow ramp.
- Cinematic reveals (PDF / demo): stagger by 80–120ms.
- **NO `transition: all`** — it breaks GPU compositing on transforms.

---

## 8. PDF / Deliverable Output

The PDF surface inherits the React design system verbatim via Playwright
render. **Same palette, same glow tokens, same typography.** When the PDF
must include a non-glow print-safe variant (rare), strip the
`text-shadow` only — never change palette.

---

## 9. Data-TestID Discipline

Every interactive element AND every element showing critical user-facing
info MUST carry a kebab-case `data-testid`. Examples:
`ceo-kpi-total-regional-scans`, `pilot-launch-btn`, `tripwire-owner-name`,
`bm-blacklist-count`, `sgd-tile-yellow-triangle`. No exceptions.

---

## 10. Quality Bar

Every new screen must pass these gates:

- [ ] Uses tokens from §1 — no hard-coded greys outside the divider/muted set
- [ ] Every accent has its layered glow signature
- [ ] Typography hierarchy matches §3
- [ ] Lucide icons only, contextual color match
- [ ] At least one `box-shadow: ... -28px <accent>22` ambient lift on key surfaces
- [ ] All interactive + critical elements have `data-testid`
- [ ] Reads cleanly at 1920×900 AND 1366×768 AND mobile 414×896
- [ ] No "AI slop" — no centered everything, no equal-weight card grids
- [ ] Brand presence preserved: a logo lockup, an accent-stripe card, OR a
      glow KPI must be visible above the fold

---

**Authority**: This file overrides any conflicting in-context inference.
If a new feature spec doesn't mention design, default here.
