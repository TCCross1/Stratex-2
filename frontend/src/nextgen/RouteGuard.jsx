import React from "react";
import { Link, useLocation } from "react-router-dom";
import { ShieldAlert, ArrowUpRight } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { canAccess } from "@/nextgen/roleAccess";

/* NextGen route guard (Phase 2).
   Wraps a destination and renders the shared Unauthorized state when the
   current user does not have permission for the route. Presentation-layer
   only — the backend still enforces its own row-scoped checks. */
export default function RouteGuard({ children }) {
  const { user } = useAuth();
  const loc = useLocation();

  // No user yet — let Protected redirect to /auth.
  if (!user) return children;

  if (!canAccess(loc.pathname, user.role)) {
    return <Unauthorized attemptedPath={loc.pathname} role={user.role} />;
  }
  return children;
}

export function Unauthorized({ attemptedPath, role }) {
  return (
    <div data-testid="nx-unauthorized">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow" style={{ color: "var(--nx-critical)" }}>
            // ACCESS DENIED
          </div>
          <h1 className="nx-page-title">Not Authorized</h1>
          <div className="nx-page-sub">
            Your role ({role || "guest"}) does not include access to
            {" "}<code style={{ color: "var(--nx-cyan)" }}>{attemptedPath}</code>.
            {" "}This is enforced both by the shell navigation and by every backend API call.
          </div>
        </div>
      </div>
      <div className="nx-card elevated" style={{ padding: 40, textAlign: "center" }}>
        <ShieldAlert size={44} strokeWidth={1.4} color="var(--nx-critical)" style={{ opacity: 0.9 }} />
        <div style={{ fontSize: 18, color: "#fff", marginTop: 14, fontWeight: 600 }}>
          Route protected by role policy
        </div>
        <div
          style={{
            color: "var(--nx-text-secondary)",
            fontSize: 13,
            marginTop: 8,
            maxWidth: 520,
            marginInline: "auto",
            lineHeight: 1.6,
          }}
        >
          If you believe you should be able to see this surface, contact your Stratex
          administrator. All authorization failures are logged in the audit trail.
        </div>
        <div className="nx-flex nx-gap-3" style={{ marginTop: 22, justifyContent: "center" }}>
          <Link to="/nextgen" className="nx-btn ghost" data-testid="nx-unauthorized-home">
            Back to Overview <ArrowUpRight size={14} strokeWidth={1.8} />
          </Link>
        </div>
      </div>
    </div>
  );
}
