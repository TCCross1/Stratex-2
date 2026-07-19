# Stratex — Architecture Bible

**Living document.** Every principle here is enforced across shipped code,
documentation, testing agents, and reorganization phases.

Last updated: Phase 2 · Feb 2026.

## Approved principles

1. **NextGen is the canonical Stratex Core shell.** Every authenticated user
   experience lives inside `/nextgen/*`. Legacy portals remain reachable at
   their existing URLs and are migrated per
   [`LEGACY_ROUTE_MIGRATION_PLAN.md`](./LEGACY_ROUTE_MIGRATION_PLAN.md), not
   deleted. No parallel shell, dashboard system, or command-center is built.
2. **Property is the persistent asset.** One canonical property record per
   physical residential asset. Address changes, resolution changes, and
   truth-band changes update the same record.
3. **Job is the commercial engagement.** A property has many jobs over its
   lifetime. Jobs never own the property record.
4. **Mission is the capture operation.** A mission is bound to exactly one
   job and one property. Missions carry the 15-stage operational chain.
5. **Evidence is immutable and provenance-bearing.** Every evidence item is
   content-addressed (SHA-256), tenant-scoped, mission-provenanced. Content
   bytes are never mutated after ingest. Deletion is a state, not a purge.
6. **Passport is the canonical persistent property record.** Only the
   Passport Service writes. Only approved intelligence triggers updates.
   The Passport is hash-chained and audit-anchored.
7. **Habitat reads approved projections.** Habitat is a homeowner-safe read
   view of the Passport — never a source of truth, never writable from the
   homeowner side, and never exposes internal / restricted fields.
8. **Legacy functionality is consolidated, not blindly rewritten.** A
   feature is migrated into NextGen only when its NextGen equivalent has
   parity, tests, and audit coverage. Deletion happens after two release
   cycles of measured zero-traffic on the deprecated path.
9. **No feature is considered live** without:
   - Real data (never fabricated live output)
   - Authorization (role-scoped, tenant-scoped, backend-enforced)
   - Error handling (loading / empty / error / 401 / 404 states)
   - Tests (unit + regression + integration)
   - Auditability (every state change lands in the audit trail)
10. **Provenance is displayed, never fabricated.** When source data is
    missing, the UI shows `PROVENANCE NOT YET AVAILABLE`.
11. **Demo Data is always labeled.** The `DemoDataBadge` component MUST
    accompany any seeded, mocked, or placeholder value visible to a user.
12. **Backend contracts are stable.** UI reorganizations may not silently
    change endpoint shape, semantics, or authorization scope.
13. **CEO portal is isolated.** The `/ceo/*` tree remains an independent
    portal with its own auth and its own surface. It is not migrated into
    the NextGen shell.
14. **Homeowners never see the operator shell.** Homeowners arrive at
    Stratex through the public `/habitat/:token` magic-link view only.
15. **Tests must not depend on external state.** Every test suite must be
    deterministic across runs. Shared dev databases require per-run salt
    (see `test_nextgen_wave2a::_png_bytes`).

## Reserved for future updates

- Phase 3 finalization principles
- Multi-region deployment principles
- SDK / partner integration principles
