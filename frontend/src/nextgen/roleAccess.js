// Stratex Core — NextGen role-access policy (Phase 2).
//
// Presentation-layer authorization. Every NextGen destination declares which
// roles can enter it. The policy is enforced in two places:
//   1. Navigation — the shell hides destinations the current user cannot see.
//   2. Direct URL — the RouteGuard wraps every /nextgen/* route and renders
//      the shared Unauthorized state instead of the destination when the user
//      does not have the role.
//
// This is a *display* + *client-side redirect* policy. The backend already
// enforces its own row-scoped tenancy & role checks on every /api/* call;
// this file exists so users never see a page they will subsequently be
// blocked from and so we have one place to reason about role visibility.
//
// Role identifiers mirror the JWT `role` claim.

/**
 * Canonical role identifiers used across NextGen.
 * NOTE: `insurance` is documented but not yet present in the seed identity
 *       system — see docs/PHASE_2_PROPERTY_WORKSPACE_ARCHITECTURE.md.
 * NOTE: `homeowner` is never given the NextGen shell — homeowners flow
 *       through the public Habitat magic-link routes only.
 */
export const ROLES = Object.freeze({
  CEO: "ceo",
  ADMIN: "admin",
  CONTRACTOR: "contractor",
  OPERATOR: "operator",
  PILOT: "pilot",
  INSURANCE: "insurance", // documented; not yet seeded
});

/** Roles that always see the full NextGen shell. */
const FULL_ACCESS = new Set([ROLES.CEO, ROLES.ADMIN]);

/**
 * Per-destination role policy.
 * Key is the NextGen route (leading slash).
 * Value is a set of roles allowed to see the destination in nav + open it
 * directly. `FULL_ACCESS` is always implicitly included.
 */
const DESTINATION_POLICY = {
  "/nextgen":                        [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT, ROLES.INSURANCE],
  "/nextgen/alerts":                 [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT, ROLES.INSURANCE],
  "/nextgen/properties":             [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT, ROLES.INSURANCE],
  "/nextgen/missions":               [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT],
  "/nextgen/schedule":               [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT],
  "/nextgen/network/contractors":    [ROLES.CONTRACTOR, ROLES.INSURANCE],
  "/nextgen/network/operators":      [ROLES.OPERATOR, ROLES.PILOT],
  "/nextgen/network/homeowners":     [ROLES.CONTRACTOR, ROLES.INSURANCE],
  "/nextgen/passport":               [ROLES.CONTRACTOR, ROLES.INSURANCE, ROLES.OPERATOR, ROLES.PILOT],
  "/nextgen/habitat":                [ROLES.CONTRACTOR],
  "/nextgen/geo":                    [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT, ROLES.INSURANCE],
  "/nextgen/awe":                    [ROLES.CONTRACTOR, ROLES.INSURANCE],
  "/nextgen/reports":                [ROLES.CONTRACTOR, ROLES.INSURANCE],
  "/nextgen/plans":                  [ROLES.CONTRACTOR],
  "/nextgen/org":                    [], // admin/ceo only
  "/nextgen/audit":                  [ROLES.INSURANCE], // read-only appropriate to audit review
  "/nextgen/company":                [ROLES.CONTRACTOR, ROLES.OPERATOR, ROLES.PILOT, ROLES.INSURANCE],
};

/**
 * @param {string} route  e.g. "/nextgen/missions"
 * @param {string} role   user's JWT role
 * @returns {boolean}
 */
export function canAccess(route, role) {
  if (!role) return false;
  if (FULL_ACCESS.has(role)) return true;
  // Property workspace nested routes inherit /nextgen/properties permission.
  const key = matchRoute(route);
  const allowed = DESTINATION_POLICY[key];
  if (!allowed) return true; // undocumented routes default to visible (never destructive)
  return allowed.includes(role);
}

/**
 * Filters a rail-section list to only destinations the given role may enter.
 * Used by NextGenShell so hidden-nav enforcement stays in sync with URL
 * guards. Sections whose items are all filtered out are dropped entirely.
 */
export function filterNavByRole(sections, role) {
  if (!role) return sections;
  if (FULL_ACCESS.has(role)) return sections;
  return sections
    .map((sec) => ({
      ...sec,
      items: sec.items.filter((it) => canAccess(it.to, role)),
    }))
    .filter((sec) => sec.items.length > 0);
}

/* Match the longest prefix registered in DESTINATION_POLICY.
   Property-workspace nested routes (/nextgen/properties/:id/*) inherit the
   /nextgen/properties permission. */
function matchRoute(route) {
  const keys = Object.keys(DESTINATION_POLICY).sort((a, b) => b.length - a.length);
  return keys.find((k) => route === k || route.startsWith(`${k}/`)) || route;
}
