# STRATEX™ — PRD & Build Log

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
- 🟡 **Email delivery** for signed NDA + final homeowner quote PDF (Resend or SendGrid — call `integration_playbook_expert_v2` before implementing).
- 🟡 **Streaming progress UX** during the ~90 s Claude narrative generation.
- 🟡 **Refactor `server.py`** (855 LOC) into `routes/{auth,contractor,operator,pdf}.py`.
- 🟡 **MaterialsConfig validation** — reject negative prices and pct > 100.

### P2 — Future
- Real Mapbox satellite tiles (optional upgrade over OSM raster).
- Real image upload for caliper edge measurement (Emergent object storage).
- Multi-trailer fleet dispatch board with live status.
- Stripe per-mission billing for contractor SaaS subscriptions.
- Emergent Google OAuth as alternate sign-in.
- Switch from `@app.on_event("startup")` to FastAPI `lifespan` context (deprecation hardening).

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
