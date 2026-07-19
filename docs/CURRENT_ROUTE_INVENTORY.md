# Stratex — Current Route Inventory

**Generated during Phase 1 (Feb 2026) as part of the NextGen consolidation.**
Source: `frontend/src/App.js` at commit `HEAD` (branch `main`).

Every route is preserved. This document only records intent and future disposition.
No route is being removed in Phase 1.

Legend for **Disposition**:
- **Keep** — production surface, no move planned
- **Merge → …** — functionality will eventually be reachable inside the NextGen shell
- **Redirect → …** — Phase 2/3 will 301 the old path to the new path
- **Demo-only** — marketing / walkthrough content, kept in `/demo/*` namespace
- **Admin-only** — should only be reachable via Admin nav in NextGen
- **Retire (Phase 3+)** — replaced by NextGen equivalent; deprecate later

## Public routes

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/` | `Landing` | public | Marketing landing / product entry | **Rewritten in Phase 1** to 3-entrance layout |
| `/deck` | `CommandDeck` | public | Executive marketing deck | **Demo-only** (link from Company & Resources) |
| `/reports/binder` | `ReportsBinder` | public | Legacy reports binder demo | **Merge → `/nextgen/reports`** |
| `/passport/:hash` | `PassportPortal` | public | Legacy public passport view | **Merge → `/nextgen/passport`** |
| `/contractor/verify` | `ContractorVerify` | public | Contractor verification landing | **Demo-only** |
| `/mission-control` | `MissionControl` | public | Legacy mission control (marketing) | **Merge → `/nextgen/missions`** |
| `/claim-snapshot` | `ClaimSnapshot` | public | Claim snapshot marketing page | **Demo-only** |
| `/claim-snapshot/:hash` | `ClaimSnapshot` | public | Shared claim snapshot | **Merge → `/nextgen/passport`** |
| `/cosign/:token` | `CosignSign` | public | Cosigning magic link | **Keep** — external signer flow |
| `/switchboard` | `Switchboard` | public | Legacy operational switchboard | **Merge → `/nextgen`** |
| `/demo/scan` · `/demo/twin` · `/demo/maintenance` · `/demo/quant` · `/demo/supply-chain` | `DemoScanWizard` | public | Marketing walkthroughs | **Demo-only** |
| `/onboard` | `OnboardingROI` | public | Onboarding ROI calculator | **Demo-only** |
| `/_neon-preview` | `NeonLayerPreview` | public | Design QA harness | **Retire (Phase 3+)** |
| `/_roof-audit` | `RoofAuditHarness` | public | QA harness | **Retire (Phase 3+)** |
| `/auth` | `AuthPage` | public | JWT + MFA sign-in | **Keep** |
| `/gm/roster` | `GmRoster` | public | GM roster page | **Merge → NextGen Network group** |
| `/habitat/:token` | `HabitatPublic` | public | Homeowner-facing habitat link | **Keep** — magic-link, canonical |

## Contractor role

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/contractor` | `ContractorJobs` | contractor | Contractor jobs list | **Merge → `/nextgen/missions`** |
| `/contractor/jobs/new` | `NewJob` | contractor | Create new job | **Merge → `/nextgen/missions/new`** |
| `/contractor/jobs/:id` | `JobDetail` | contractor | Job detail workspace | **Merge → `/nextgen/missions/:id`** |
| `/contractor/materials` | `MaterialsConfig` | contractor | Materials configuration | **Merge → Contractor & Insurance (NextGen)** |
| `/contractor/deliverable/:jobId` | `ContractorDeliverable` | protected | Contractor deliverable view | **Keep** — external report share |
| `/contractor/deliverable/:jobId/deck` | `DeliverableDeck` | protected | Deliverable deck (presentation) | **Keep** — external report share |
| `/deliverable/demo` | `ContractorDeliverable` | protected | Demo deliverable | **Demo-only** |
| `/deck/demo` | `DeliverableDeck` | protected | Demo deck | **Demo-only** |
| `/contractor/brand` | `ContractorBranding` | contractor | Contractor branding | **Merge → Contractor & Insurance (NextGen)** |
| `/contractor/quote-builder` | `QuoteBuilder` | contractor | Quote builder | **Merge → Contractor & Insurance (NextGen)** |
| `/simulation/:jobId` · `/simulation/demo` | `SimulationRun` | protected | Simulation runner | **Merge → Mission Control (NextGen)** |
| `/billing` · `/billing/success` | `Pricing` / `BillingSuccess` | contractor | Pricing & billing | **Merge → Plans, Licenses & Compliance (NextGen)** |

## Operator / Pilot role

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/operator` | `OperatorBoard` | operator | Operator board | **Merge → Operators & Pilots (NextGen)** |
| `/operator/jobs/:id` | `OperatorJobDetail` | operator | Operator job detail | **Merge → Mission Control (NextGen)** |
| `/operator/launch/:jobId` | `FleetLaunch` | operator | Fleet launch flow | **Keep** — tablet-first surface |
| `/launch` | `FleetLaunch` | protected | Generic launch entry | **Merge → Operators & Pilots (NextGen)** |
| `/pilot` | `PilotDashboard` | operator | Pilot dashboard | **Keep** — tablet-first |
| `/pilot/job/:jobId` | `PilotJobSheet` | operator | Pilot job sheet | **Keep** — tablet-first |
| `/pilot/preflight/:jobId` | `PilotPreflight` | operator | Pre-flight checklist | **Keep** — tablet-first |
| `/fleet` | `FleetBoard` | protected | Fleet board | **Merge → Operators & Pilots (NextGen)** |
| `/fleet/live-map` | `FleetLiveMap` | protected | Live map | **Merge → Geographic Intelligence (NextGen)** |

## Admin / GM role

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/admin/sales` | `AdminSalesHub` | admin | Sales hub | **Merge → Platform Administration (NextGen)** |
| `/admin/overseer` | `OverseerQueue` | admin | Overseer QA queue | **Merge → Platform Administration** |
| `/admin/flight-audit` | `FlightAudit` | admin | Flight audit | **Merge → Platform Administration** |
| `/admin/cv-ice-shield` | `CVIceShield` | admin | CV ice-shield admin | **Merge → Platform Administration** |
| `/admin/weather` | `AdminWeather` | admin | Weather admin | **Merge → Platform Administration** |
| `/admin/ops` | `GmOpsPage` | admin | Ops board (was duplicated with AdminOps; duplicate removed Phase 1) | **Merge → Platform Administration** |
| `/gm/ops` | `GmOpsPage` | gm | GM ops board | **Keep** (role-scoped) |
| `/admin/branch-console` | `BranchConsole` | admin | Branch console | **Merge → Platform Administration** |
| `/admin/consensus` | `AdminConsensus` | admin | Consensus admin | **Merge → Platform Administration** |
| `/admin/fleet` | `MduFleetPortal` | admin | Admin fleet portal | **Merge → Operators & Pilots** |
| `/admin/blacklist` | `BlacklistMatrix` | admin | Admin blacklist matrix | **Merge → Platform Administration** |

## CEO role (isolated)

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/ceo/login` | `CeoLogin` | public | CEO sign-in portal | **Keep** — isolated portal |
| `/ceo/command` | `CeoCommandCenter` | ceo | CEO command center | **Keep** |
| `/ceo/leads` | `SupplyPipeline` | ceo | Leads pipeline | **Keep** |
| `/ceo/orders/build` · `/ceo/orders/ready` · `/ceo/orders/shipped` | `SupplyPipeline` | ceo | Supply pipeline by status | **Keep** |
| `/ceo/inventory` | `InventoryCost` | ceo | Inventory cost | **Keep** |
| `/ceo/live-map` | `FleetLiveMap` | ceo | CEO live map | **Keep** |
| `/ceo/regional` | `RegionalSwitchboard` | ceo | Regional switchboard | **Keep** |
| `/ceo/fleet` | `MduFleetPortal` | ceo | CEO fleet portal | **Keep** |
| `/ceo/blacklist` | `BlacklistMatrix` | ceo | CEO blacklist matrix | **Keep** |
| `/ceo/suppliers` | `CeoSuppliers` | ceo | Suppliers | **Keep** |
| `/ceo/ops` | `CeoOpsPage` | ceo | CEO ops page (aka CENTCOM) | **Keep** |

## NextGen (canonical Stratex Core app)

| Route | Component | Role | Purpose | Disposition |
|---|---|---|---|---|
| `/nextgen` | `NextGenOverview` | auth | Home / Command overview | **Keep — canonical** |
| `/nextgen/properties` | `NextGenProperties` | auth | Jobs & Properties | **Keep — canonical** |
| `/nextgen/missions` · `/missions/new` · `/missions/:id` | `MissionsList` etc. | auth | Mission Control | **Keep — canonical** |
| `/nextgen/missions/:missionId/evidence` | `NextGenEvidence` | auth | Evidence capture | **Keep — canonical** |
| `/nextgen/missions/:missionId/intelligence` | `NextGenIntelligence` | auth | Intelligence workspace | **Keep — canonical** |
| `/nextgen/passport` | `NextGenPassport` | auth | Property Passport | **Keep — canonical** |
| `/nextgen/awe` | `NextGenAwe` | auth | AWE / Geographic Intelligence | **Keep — canonical** |
| `/nextgen/reports` | `NextGenReports` | auth | Reports Binder | **Keep — canonical** |
| `/nextgen/habitat` | `NextGenHabitat` | auth | Stratex Habitat control | **Keep — canonical** |
| `/nextgen/audit` | `NextGenAudit` | auth | Audit trail | **Keep — canonical** |
| `/nextgen/org` | `NextGenOrganization` | auth | Platform Administration | **Keep — canonical** |

### New Phase 1 placeholder destinations (inside NextGen shell)

| Route | Component | Purpose |
|---|---|---|
| `/nextgen/alerts` | `Placeholder` | Alerts inbox (Phase 2) |
| `/nextgen/schedule` | `Placeholder` | Scheduling (Phase 2) |
| `/nextgen/network/contractors` | `Placeholder` | Contractor & insurance network (Phase 2) |
| `/nextgen/network/operators` | `Placeholder` | Operators & pilots roster (Phase 2) |
| `/nextgen/network/homeowners` | `Placeholder` | Homeowner directory (Phase 2) |
| `/nextgen/geo` | `Placeholder` | Geographic intelligence map (Phase 2) |
| `/nextgen/plans` | `Placeholder` | Plans, licenses & compliance (Phase 2) |
| `/nextgen/company` | `Placeholder` | Company & resources aggregator (Phase 2) |

Every placeholder shows a clearly-labeled **Demo Data / Not Yet Implemented** banner.
No fabricated live data. Backend contract unaffected.

## Duplicate route resolved in Phase 1

- `/admin/ops` was declared **twice** in `App.js` — once as `AdminOps`, once as `GmOpsPage`.
  React Router used the later declaration (`GmOpsPage`).
  Phase 1 removes the `AdminOps` duplicate declaration to eliminate confusion.
  The `AdminOps` component itself is retained in the codebase for possible future re-use.
