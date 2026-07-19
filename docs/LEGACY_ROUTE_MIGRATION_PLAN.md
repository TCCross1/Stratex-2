# Stratex — Legacy Route Migration Plan

**Status**: Phase 1 (Feb 2026) — planning only. **No legacy route is removed in Phase 1.**
This document defines where each legacy surface will eventually land once NextGen has feature parity.

## Guiding rules

1. **Never break a paying customer / demo link.** Every removed path must be replaced by a permanent HTTP 301 (or client-side `<Navigate replace/>`) to its new home.
2. **Feature parity first.** No legacy route may be removed before its NextGen equivalent is (a) documented, (b) shipped, and (c) verified by testing.
3. **External / magic-link routes stay.** `/cosign/:token`, `/habitat/:token`, `/passport/:hash`, `/claim-snapshot/:hash`, `/contractor/deliverable/:jobId` are permanent public share surfaces — they will not be redirected.
4. **CEO portal stays isolated.** The whole `/ceo/*` tree remains a separate portal per current security model and is out of scope for consolidation.
5. **Demo / marketing routes** move to the `/demo/*` namespace under NextGen Company & Resources; other marketing tools stay under their existing paths for backwards compatibility until Phase 3.

## Phase 2 — Contractor consolidation

| Legacy | Target (NextGen) | Notes |
|---|---|---|
| `/contractor` | `/nextgen/missions` | filtered to contractor's jobs |
| `/contractor/jobs/new` | `/nextgen/missions/new` | |
| `/contractor/jobs/:id` | `/nextgen/missions/:id` | |
| `/contractor/materials` | `/nextgen/network/contractors` | material config lives inside contractor profile |
| `/contractor/brand` | `/nextgen/network/contractors` | brand tab |
| `/contractor/quote-builder` | `/nextgen/missions/new` | quote flow inlined |
| `/simulation/:jobId` | `/nextgen/missions/:id` (Simulation tab) | |
| `/billing` | `/nextgen/plans` | Plans, Licenses & Compliance |
| `/mission-control` | `/nextgen/missions` | 301 |
| `/reports/binder` | `/nextgen/reports` | 301 |

## Phase 2 — Operator / Pilot consolidation

| Legacy | Target (NextGen) | Notes |
|---|---|---|
| `/operator` | `/nextgen/network/operators` | operator's own roster view |
| `/operator/jobs/:id` | `/nextgen/missions/:id` | |
| `/fleet` | `/nextgen/network/operators` | fleet tab |
| `/fleet/live-map` | `/nextgen/geo` | Geographic Intelligence |
| `/gm/roster` | `/nextgen/network/operators` | 301 |
| `/pilot`, `/pilot/job/:jobId`, `/pilot/preflight/:jobId` | **KEEP** | tablet-first surfaces stay independent |
| `/operator/launch/:jobId`, `/launch` | **KEEP** | tablet-first surfaces stay independent |

## Phase 2 — Admin / GM consolidation

| Legacy | Target (NextGen) | Notes |
|---|---|---|
| `/admin/sales` | `/nextgen/org` (Sales tab) | Platform Administration |
| `/admin/overseer` | `/nextgen/org` (QA tab) | |
| `/admin/flight-audit` | `/nextgen/org` (Flight Audit tab) | |
| `/admin/cv-ice-shield` | `/nextgen/org` (CV tab) | |
| `/admin/weather` | `/nextgen/org` (Weather tab) | |
| `/admin/ops` (duplicate removed Phase 1) | `/nextgen/org` (Ops tab) | GmOpsPage kept as canonical |
| `/gm/ops` | **KEEP** | role-scoped |
| `/admin/branch-console` | `/nextgen/org` (Branches tab) | |
| `/admin/consensus` | `/nextgen/org` (Consensus tab) | |
| `/admin/fleet` | `/nextgen/network/operators` | 301 |
| `/admin/blacklist` | `/nextgen/org` (Blacklist tab) | |

## Phase 2 — Marketing / demo consolidation

| Legacy | Target | Notes |
|---|---|---|
| `/demo/*` | `/nextgen/company` (Demo library) | linked from Company & Resources |
| `/onboard` | `/nextgen/company` | link |
| `/switchboard` | `/nextgen` | 301 |
| `/deck` | `/nextgen/company` (Executive Deck) | link |
| `/contractor/verify` | `/nextgen/company` | link |
| `/claim-snapshot` | `/nextgen/company` (Sample outputs) | link |
| `/_neon-preview`, `/_roof-audit` | **Retire Phase 3+** | design QA harnesses |

## Phase 3 — Cutover

Once every Phase 2 destination is shipped:

1. Add redirect entries under `/app/frontend/src/routes/legacy_redirects.js`.
2. Update `App.js` to render `<Navigate to="…" replace/>` for each redirected path (in place of the current component).
3. Delete the deprecated components after two release cycles with no traffic (verified via analytics).

## Not migrated (permanent public share surfaces)

- `/cosign/:token`
- `/habitat/:token`
- `/passport/:hash`
- `/claim-snapshot/:hash`
- `/contractor/deliverable/:jobId`
- `/contractor/deliverable/:jobId/deck`
- `/pilot/*` (tablet-first field surfaces)
- `/operator/launch/:jobId`, `/launch`
- Whole `/ceo/*` tree (isolated portal)
- `/auth`, `/nda`

## Removal is deferred

**Nothing is deleted in Phase 1.** This document is the record of intent so Phase 2/3 can proceed
without ambiguity.
