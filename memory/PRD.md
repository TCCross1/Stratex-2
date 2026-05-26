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
