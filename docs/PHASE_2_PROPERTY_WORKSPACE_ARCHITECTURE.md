# Phase 2 · Property & Job Workspace Architecture

**Commit lineage**: `467ba74` (Phase 1) → Phase 2.
**Backup branch**: `backup-before-phase-2-property-workspace`.

Phase 2 delivers the canonical property & job workspace INSIDE the existing
NextGen shell. No new shell was created. No working legacy system was removed
or rewritten. Every route in Phase 1 remains reachable.

## 1 · Canonical Entity Relationship

```
PROPERTY               (persistent residential asset — the long-lived record)
  └── JOB / PROJECT    (specific commercial engagement · 1 property → N jobs)
        └── MISSION    (scheduled field-capture operation for a job)
              └── EVIDENCE          (immutable, content-addressed, SHA-256'd)
                    └── ANALYSIS / FINDINGS   (Property Intelligence Objects)
                          └── ESTIMATE / REPORT
                                └── APPROVED PASSPORT UPDATE   (single writer)
                                      └── HABITAT PROJECTION   (homeowner-safe)
```

Property, Job, and Mission are distinct entities. **The Passport is not per-
job, per-mission, or per-report.** It is a property-scoped hash-chained ledger.

Habitat is **not** the source of property truth — it is a read-only projection.

## 2 · Route Structure

Shell: `/nextgen/*` (unchanged from Phase 1).

**Property list** — `/nextgen/properties` (upgraded in Phase 2).

**Property workspace** — `/nextgen/properties/:propertyId` renders through
`PropertyWorkspaceShell`, which mounts:

| Route (relative) | Component | Real data source | Phase 2 status |
|---|---|---|---|
| `overview`        | `WsOverview`        | `/api/nextgen/properties/:id` + AWE + timeline + passport + habitat-grants | **Live** |
| `jobs`            | `WsJobs`            | `/api/nextgen/missions` filtered by property | **Live** |
| `mission-capture` | `WsMissionCapture`  | active mission from missions list | **Live** |
| `evidence`        | `WsEvidence`        | mission list + per-mission provenance | **Live** |
| `digital-twin`    | `DigitalTwinPage`   | — | Gap page (Phase 2b) |
| `cad-bim`         | `CadBimPage`        | — | Gap page (Phase 2b) |
| `measurements`    | `MeasurementsPage`  | — | Gap page (Phase 2b) |
| `openings`        | `OpeningsPage`      | — | Gap page (Phase 2b) |
| `materials`       | `MaterialsPage`     | — | Gap page (Phase 3) |
| `awe`             | `WsAwe`             | `/api/nextgen/v1/properties/:id/awe` | **Live** |
| `findings`        | `FindingsPage`      | — | Gap page (Phase 2b) |
| `estimate`        | `EstimatePage`      | — | Gap page (Phase 3) |
| `reports`         | `WsReports`         | `/api/nextgen/v1/properties/:id/report/:template` | **Live** |
| `passport`        | `WsPassport`        | `/api/nextgen/v1/properties/:id/passport` | **Live** |
| `habitat`         | `WsHabitat`         | `/api/nextgen/v1/properties/:id/habitat-grants` | **Live** |
| `documents`       | `DocumentsPage`     | — | Gap page (Phase 2b) |
| `history`         | `WsHistory`         | `/api/nextgen/v1/properties/:id/timeline` | **Live** |
| `audit`           | `WsAudit`           | placeholder pointing at global audit | Placeholder |

The shell handles: identity header, job/context selector, breadcrumbs,
role-aware nav, mobile-responsive nav, loading / empty / error / 401 / 404.

## 3 · Role Access Matrix

Defined in `frontend/src/nextgen/roleAccess.js`. `RouteGuard` enforces at the
URL level; `filterNavByRole()` enforces in the nav.

| Route | ceo/admin | contractor | operator/pilot | insurance |
|---|:-:|:-:|:-:|:-:|
| `/nextgen` (Overview) | ✅ | ✅ | ✅ | ✅ |
| `/nextgen/properties` (+ workspace) | ✅ | ✅ | ✅ | ✅ |
| `/nextgen/missions` | ✅ | ✅ | ✅ | — |
| `/nextgen/schedule` | ✅ | ✅ | ✅ | — |
| `/nextgen/network/contractors` | ✅ | ✅ | — | ✅ |
| `/nextgen/network/operators` | ✅ | — | ✅ | — |
| `/nextgen/network/homeowners` | ✅ | ✅ | — | ✅ |
| `/nextgen/passport` | ✅ | ✅ | ✅ | ✅ |
| `/nextgen/habitat` | ✅ | ✅ | — | — |
| `/nextgen/geo` | ✅ | ✅ | ✅ | ✅ |
| `/nextgen/awe` | ✅ | ✅ | — | ✅ |
| `/nextgen/reports` | ✅ | ✅ | — | ✅ |
| `/nextgen/plans` | ✅ | ✅ | — | — |
| `/nextgen/org` | ✅ | — | — | — |
| `/nextgen/audit` | ✅ | — | — | ✅ |
| `/nextgen/company` | ✅ | ✅ | ✅ | ✅ |

**Homeowners** never enter the NextGen shell — they arrive via public
`/habitat/:token` magic links only.

**Note**: the `insurance` role identifier is documented but **not yet seeded**
in the identity system. The policy is in place; when the identity system
grows an `insurance` role, no code change is required — the policy already
grants the correct scope.

## 4 · Reused Components & Services

- `nxGetProperty` · `nxListMissions` · `nxPropertyAwe` · `nxPropertyPassport`
  · `nxPropertyTimeline` · `nxListHabitatGrants` · `nxReportTemplates` ·
  `nxPropertyReport` · `nxOpenReportHtml`
- `Placeholder` + `DemoDataBadge` (from Phase 1)
- `nx-*` design tokens (from Directive 009)

## 5 · New APIs

**Zero.** Phase 2 is a UI consolidation and reuses existing endpoints.

## 6 · Database Changes

**None.**

## 7 · Provenance Rules

Every substantive intelligence item shown in the workspace supports the
provenance chip:

```jsx
<ProvenanceChip mission={...} evidence={...} approvedBy={...}
                confidence={...} at={...} />
```

When any of those are absent, the chip renders `PROVENANCE NOT YET AVAILABLE`.
Fake provenance is never generated. When the backend gains a provenance API
for a category, wire the fields into the chip — no other change is needed.

## 8 · Passport Authority Rules

- The `Passport Service` is the only writer.
- Approved intelligence is the only input that triggers a Passport update.
- Habitat reads the audience-scoped projection.
- Homeowner projections strip: internal notes, reviewer identity, AI
  confidence numbers, insurance-only fields, unapproved intelligence.

## 9 · Status Vocabulary

Defined in `frontend/src/nextgen/PropertyWorkspaceShell.jsx` (`STATUS` export):

`COMPLETE · IN_PROGRESS · REQUIRED · MISSING · NOT_ORDERED · NOT_APPLICABLE
· AWAITING_APPROVAL · BLOCKED · NOT_YET_IMPLEMENTED`

Never leave a substantive field blank. Use `NOT_YET_IMPLEMENTED` for surfaces
whose backend has not shipped.

## 10 · Demo Data Indicator

`<DemoDataBadge kind="placeholder" />` is rendered on every gap page and on
seed/mock surfaces. Never fabricate live data without the badge.

## 11 · Foundation Corrections Landed in Phase 2

- **A.1** — Landing.jsx header comments now describe the three-door layout
  and the fact that legacy app-launcher content lives only behind
  "Company & Platform Information".
- **A.2** — TC assistant is offset above the NextGen mobile bottom nav
  (84 px) via `.tc-assistant-pill` / `.tc-assistant-panel` classes and a
  `body.nx-active` marker mounted by the shell.
- **A.3** — Role-aware NextGen access as documented above. `RouteGuard`
  renders `Unauthorized` (`data-testid="nx-unauthorized"`) when a user hits
  a URL they cannot enter.
- **A.4** — Evidence-upload test isolation. `_png_bytes()` now mixes the
  session-level `_TEST_SUFFIX` into pixel data; the `FLIGHT_LOG` payload has
  a per-run header comment. Production duplicate detection is unchanged.

## 12 · Future Migration Plan

- **Phase 2b** — connect Findings, Digital Twin, CAD/BIM, Measurements,
  Openings, Documents, Findings, Estimate as they ship on the backend.
- **Phase 3** — legacy consolidation per
  `docs/LEGACY_ROUTE_MIGRATION_PLAN.md` (contractor portal, admin ops,
  operator/pilot).

Nothing in Phase 2 blocks Phase 2b/3 — every new surface follows the same
`WorkspaceShell` + `Placeholder` + `StatusPill` + `ProvenanceChip` pattern.
