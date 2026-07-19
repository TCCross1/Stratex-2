import React, { useState, useCallback } from "react";
import { NavLink, Outlet, useNavigate, useLocation, Link } from "react-router-dom";
import {
  Home, Compass, ShieldCheck, FileText, Menu as MenuIcon,
  Bell, LogOut, Building2, Waves, History, Users,
  Share2, X, ChevronRight, Bell as BellIcon, Calendar,
  Handshake, Plane, Home as HomeIcon2, Map, ScrollText,
  Settings, Info,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import "@/nextgen/nextgen.css";

/* Stratex Core Premium Command Shell (Directive 009 + Phase 1 reorg).
   Responsive: desktop rail · tablet compact rail · mobile bottom nav + More sheet.
   Presentation only — every destination is a real existing NextGen route. */

/* ── Primary destinations (5 slots for mobile bottom nav) ── */
const PRIMARY = [
  { to: "/nextgen",           label: "Home",     icon: Home,        end: true },
  { to: "/nextgen/missions",  label: "Missions", icon: Compass },
  { to: "/nextgen/passport",  label: "Passport", icon: ShieldCheck },
  { to: "/nextgen/reports",   label: "Reports",  icon: FileText },
];

/* ── Desktop rail — Phase 1 canonical structure ── */
const RAIL_SECTIONS = [
  {
    heading: "COMMAND",
    items: [
      { to: "/nextgen",         label: "Overview", icon: Home, end: true },
      { to: "/nextgen/alerts",  label: "Alerts",   icon: BellIcon },
    ],
  },
  {
    heading: "OPERATIONS",
    items: [
      { to: "/nextgen/properties", label: "Jobs & Properties", icon: Building2 },
      { to: "/nextgen/missions",   label: "Mission Control",   icon: Compass },
      { to: "/nextgen/schedule",   label: "Schedule",          icon: Calendar },
    ],
  },
  {
    heading: "NETWORK",
    items: [
      { to: "/nextgen/network/contractors", label: "Contractors & Insurance", icon: Handshake },
      { to: "/nextgen/network/operators",   label: "Operators & Pilots",       icon: Plane },
      { to: "/nextgen/network/homeowners",  label: "Homeowners",               icon: HomeIcon2 },
    ],
  },
  {
    heading: "PROPERTY INTELLIGENCE",
    items: [
      { to: "/nextgen/passport", label: "Property Passport",    icon: ShieldCheck },
      { to: "/nextgen/habitat",  label: "Stratex Habitat",      icon: Share2 },
      { to: "/nextgen/geo",      label: "Geographic Intelligence", icon: Map },
    ],
  },
  {
    heading: "MANAGEMENT",
    items: [
      { to: "/nextgen/reports", label: "Reports",                       icon: FileText },
      { to: "/nextgen/plans",   label: "Plans, Licenses & Compliance",  icon: ScrollText },
      { to: "/nextgen/org",     label: "Platform Administration",       icon: Settings },
    ],
  },
  {
    heading: "COMPANY",
    items: [
      { to: "/nextgen/company", label: "Company & Resources", icon: Info },
    ],
  },
];

/* Flat list used by the mobile More sheet, grouped identically. */
const SECONDARY_GROUPS = RAIL_SECTIONS;

/* ── Desktop rail ──────────────────────────────────────────── */
function DesktopRail() {
  const { user } = useAuth();
  return (
    <aside className="nx-rail" data-testid="nx-rail">
      <Link to="/nextgen" className="nx-rail-brand" data-testid="nx-rail-brand">
        <img
          src="/brand/stratex-core-logo.png"
          alt="STRATEX CORE"
          className="nx-rail-brand-image"
          data-testid="nx-rail-brand-image"
        />
      </Link>

      <div className="nx-rail-scroll">
        {RAIL_SECTIONS.map((sec) => (
          <div key={sec.heading}>
            <div className="nx-rail-section">// {sec.heading}</div>
            {sec.items.map((it) => (
              <NavLink
                key={it.to}
                to={it.to}
                end={it.end}
                data-testid={`nx-rail-${slug(it.label)}`}
                className={({ isActive }) => `nx-rail-item ${isActive ? "active" : ""}`}
                title={it.label}
              >
                <it.icon className="ico" strokeWidth={1.6} />
                <span className="label">{it.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      <div className="nx-rail-footer">
        <div className="nx-rail-tenant">
          <div className="name">{user?.legal_name || user?.email || "Guest"}</div>
          <div className="role">{user?.role || "guest"}</div>
          <div className="env">Preview</div>
        </div>
      </div>
    </aside>
  );
}

/* ── Mobile top header ─────────────────────────────────────── */
function MobileHeader({ onMoreClick }) {
  const nav = useNavigate();
  const loc = useLocation();
  const isRoot = loc.pathname === "/nextgen";

  return (
    <header className="nx-mobile-header" data-testid="nx-mobile-header">
      <div className="nx-mobile-header-row">
        {isRoot ? (
          <button
            type="button"
            className="nx-icon-btn"
            onClick={onMoreClick}
            data-testid="nx-mobile-menu-btn"
            aria-label="Open menu"
          >
            <MenuIcon size={20} strokeWidth={1.6} />
          </button>
        ) : (
          <button
            type="button"
            className="nx-icon-btn"
            onClick={() => nav(-1)}
            data-testid="nx-mobile-back-btn"
            aria-label="Go back"
          >
            <ChevronRight size={20} strokeWidth={1.6} style={{ transform: "rotate(180deg)" }} />
          </button>
        )}

        <div className="center" onClick={() => nav("/nextgen")} style={{ cursor: "pointer" }}>
          <img
            src="/brand/stratex-core-logo.png"
            alt="STRATEX CORE"
            className="nx-mobile-header-logo"
            data-testid="nx-mobile-header-logo"
          />
        </div>

        <button
          type="button"
          className="nx-icon-btn"
          data-testid="nx-mobile-notif-btn"
          aria-label="Notifications"
          onClick={() => nav("/nextgen/alerts")}
        >
          <Bell size={19} strokeWidth={1.6} />
          <span className="dot" />
        </button>
      </div>
    </header>
  );
}

/* ── Mobile bottom nav ─────────────────────────────────────── */
function BottomNav({ onMoreClick }) {
  return (
    <nav className="nx-bottom-nav" data-testid="nx-bottom-nav" aria-label="Primary">
      <div className="nx-bottom-nav-row">
        {PRIMARY.map((it) => (
          <NavLink
            key={it.to}
            to={it.to}
            end={it.end}
            data-testid={`nx-tab-${slug(it.label)}`}
            className={({ isActive }) => (isActive ? "active" : "")}
          >
            <it.icon className="ico" strokeWidth={1.6} />
            <span>{it.label}</span>
          </NavLink>
        ))}
        <button
          type="button"
          onClick={onMoreClick}
          data-testid="nx-tab-more"
          style={{ background: "transparent", border: "none" }}
        >
          <MenuIcon className="ico" size={22} strokeWidth={1.6} />
          <span>More</span>
        </button>
      </div>
    </nav>
  );
}

/* ── More sheet ────────────────────────────────────────────── */
function MoreSheet({ open, onClose }) {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const go = (to) => { onClose(); nav(to); };

  return (
    <>
      <div
        className={`nx-sheet-overlay ${open ? "open" : ""}`}
        onClick={onClose}
        data-testid="nx-sheet-overlay"
      />
      <div className={`nx-sheet ${open ? "open" : ""}`} data-testid="nx-more-sheet" role="dialog" aria-label="More navigation">
        <div className="handle" />
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0 4px 4px 4px" }}>
          <div className="nx-flex nx-gap-2" style={{ alignItems: "center" }}>
            <img
              src="/brand/stratex-core-logo.png"
              alt="STRATEX CORE"
              style={{ height: 40, width: "auto", borderRadius: 6, background: "#000" }}
            />
            <div>
              <div style={{ color: "#fff", fontSize: 12, fontWeight: 700, letterSpacing: "0.16em" }}>
                Property Intelligence
              </div>
              <div style={{ color: "#6D7B8F", fontSize: 11 }}>
                {user?.legal_name || user?.email || "Operator"} · {user?.role || "—"}
              </div>
            </div>
          </div>
          <button className="nx-icon-btn" onClick={onClose} data-testid="nx-more-close" aria-label="Close">
            <X size={18} strokeWidth={1.6} />
          </button>
        </div>

        {SECONDARY_GROUPS.map((grp) => (
          <div key={grp.heading}>
            <h3>// {grp.heading}</h3>
            {grp.items.map((it) => (
              <button
                key={`${grp.heading}-${it.to}-${it.label}`}
                className="nx-sheet-item"
                onClick={() => go(it.to)}
                data-testid={`nx-sheet-${slug(it.label)}`}
              >
                <it.icon className="ico" strokeWidth={1.6} />
                <span>{it.label}</span>
                <ChevronRight className="arrow" size={16} strokeWidth={1.6} />
              </button>
            ))}
          </div>
        ))}

        <h3>// SESSION</h3>
        <button
          className="nx-sheet-item"
          data-testid="nx-sheet-signout"
          onClick={() => { logout(); nav("/auth"); }}
          style={{ color: "var(--nx-critical)" }}
        >
          <LogOut className="ico" strokeWidth={1.6} style={{ color: "var(--nx-critical)" }} />
          <span>Sign out</span>
          <ChevronRight className="arrow" size={16} strokeWidth={1.6} />
        </button>

        <div style={{ marginTop: 18, textAlign: "center", color: "#6D7B8F", fontSize: 10, letterSpacing: "0.24em", textTransform: "uppercase", fontFamily: "var(--nx-font-tech)" }}>
          A Cross AI Softwares Inc. product · Preview build
        </div>
      </div>
    </>
  );
}

/* ── Shell ─────────────────────────────────────────────────── */
export default function NextGenShell() {
  const [moreOpen, setMoreOpen] = useState(false);
  const openMore = useCallback(() => setMoreOpen(true), []);
  const closeMore = useCallback(() => setMoreOpen(false), []);

  return (
    <div className="nx-shell" data-testid="nextgen-shell">
      <div className="nx-app">
        <DesktopRail />
        <div className="nx-app-main-col">
          <MobileHeader onMoreClick={openMore} />
          <main className="nx-main" data-testid="nx-main">
            <Outlet />
          </main>
        </div>
      </div>
      <BottomNav onMoreClick={openMore} />
      <MoreSheet open={moreOpen} onClose={closeMore} />
    </div>
  );
}

/* util */
function slug(s) { return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-"); }
