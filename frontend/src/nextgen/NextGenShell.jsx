import React from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import "@/nextgen/nextgen.css";

/* NextGen shell — sidebar + content grid.
   Blueprint v1.2 §3 navigation hierarchy · §20.1 Phase 1 UI honesty banner. */

const NAV = [
  { section: "// COMMAND", items: [
    { idx: "01", label: "Overview", to: "/nextgen" },
  ]},
  { section: "// OPERATIONS", items: [
    { idx: "02", label: "Mission Control", to: "/nextgen/missions" },
    { idx: "03", label: "Properties", to: "/nextgen/properties" },
  ]},
  { section: "// INTELLIGENCE", items: [
    { idx: "04", label: "Property Passport", to: "/nextgen/passport" },
    { idx: "05", label: "AWE™ Intelligence", to: "/nextgen/awe" },
  ]},
  { section: "// DELIVERY", items: [
    { idx: "06", label: "Reports Binder", to: "/nextgen/reports" },
    { idx: "07", label: "Habitat Sync", to: "/nextgen/habitat" },
  ]},
  { section: "// PLATFORM", items: [
    { idx: "08", label: "Audit Trail", to: "/nextgen/audit" },
    { idx: "09", label: "Organization", to: "/nextgen/org" },
  ]},
];

export default function NextGenShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  return (
    <div className="nx-shell" data-testid="nextgen-shell">
      <aside className="nx-sidebar">
        <div className="nx-brand">
          <div className="nx-brand-mark">// STRATEX™ CORE</div>
          <div className="nx-brand-name">NextGen</div>
          <div className="nx-brand-tag">Residential Property Intelligence OS</div>
        </div>

        {NAV.map((sec) => (
          <div key={sec.section}>
            <div className="nx-nav-section">{sec.section}</div>
            <div className="nx-nav">
              {sec.items.map((it) => (
                <NavLink
                  key={it.to}
                  to={it.to}
                  end={it.to === "/nextgen"}
                  data-testid={`nx-nav-${it.label.toLowerCase().replace(/\s+/g,'-')}`}
                  className={({isActive}) => isActive ? "active" : ""}
                >
                  <span className="idx">{it.idx}</span>
                  <span>{it.label}</span>
                </NavLink>
              ))}
            </div>
          </div>
        ))}

        <div className="nx-tenant-chip">
          <div className="label">// Session</div>
          <div className="name">{user?.legal_name || user?.email || "—"}</div>
          <div className="role">{user?.role || "guest"}</div>
          <button
            className="nx-btn ghost small"
            style={{ marginTop: 12, width: "100%" }}
            onClick={() => { logout(); navigate("/auth"); }}
            data-testid="nx-logout-btn"
          >Sign Out</button>
        </div>
      </aside>

      <main className="nx-main">
        <div className="nx-topbar">
          <div className="nx-topbar-title">// STRATEX™ NEXTGEN · BLUEPRINT v1.2 · PHASE 1a</div>
          <div className="nx-topbar-status">
            <span className="nx-pill ok">Preview · Non-Production</span>
            <span className="nx-pill dim">Legacy Frozen</span>
          </div>
        </div>

        <div className="nx-banner" data-testid="nx-phase1-banner">
          <span className="dot" />
          Demonstration content · not sourced from a real inspection until validated (Blueprint §20.1)
        </div>

        <Outlet />
      </main>
    </div>
  );
}
