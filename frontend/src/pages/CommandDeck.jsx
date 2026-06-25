// STRATEX™ — COMMAND DECK
// Single-surface dashboard that exposes every operational app in the platform
// through a vertical, scrollable, branded app-rail on the left and a
// breathtaking bento canvas on the right.  Pure investor/demo surface —
// auth-free, brand-locked, future-noire.
//
// Branding rules (locked):
//   • Background  → obsidian #02060B + radial cyan/amber glow
//   • Logo        → <StratexLogo/> (official PNG, never text-based)
//   • Accents     → cyan #00E5FF · amber #FFB020 · volt #A6FF00 · magenta #FF2D78 · green #00FF9C
//   • Type        → font-mono for chrome, font-display for headlines
//
// Routes covered: every entry across Landing.jsx PORTAL_TILES +
// DASHBOARD_GROUPS, plus surfaces wired in App.js (operator, pilot, admin,
// onboard, billing, simulation, etc.).

import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StratexLogo } from "@/components/StratexBrand";
import {
  Radar, Box, Activity, Cpu, Shield, Satellite, Cloud, Sun, Crosshair,
  Zap, Plane, Map, ClipboardList, BarChart3, Wallet, Snowflake, Eye,
  Layers, Boxes, Truck, Building2, FileSearch, GitBranch, FlaskConical,
  Search, ChevronRight, Sparkles, Gauge, LayoutDashboard, ScrollText,
  AlertOctagon, Compass, Workflow, Network, ListChecks,
} from "lucide-react";

// ──────────────────────────────────────────────────────────────────────────
// APP REGISTRY — single source of truth for the entire deck.
// Each entry: { id, label, sub, to, icon, accent, group, primary? }
// ──────────────────────────────────────────────────────────────────────────
const ACCENTS = {
  cyan:    { hex: "#00E5FF", glow: "0 0 18px #00E5FF99" },
  amber:   { hex: "#FFB020", glow: "0 0 18px #FFB02099" },
  volt:    { hex: "#A6FF00", glow: "0 0 18px #A6FF0099" },
  magenta: { hex: "#FF2D78", glow: "0 0 18px #FF2D7899" },
  green:   { hex: "#00FF9C", glow: "0 0 18px #00FF9C99" },
  purple:  { hex: "#C084FC", glow: "0 0 18px #C084FC99" },
};

const APPS = [
  // ── Demo Modules ── (auth-free walkthroughs)
  { id: "scan",        label: "New Drone Scan",          sub: "Upload imagery → CAD/BIM forensic report", to: "/demo/scan",          icon: Radar,        accent: "cyan",    group: "demo",     primary: true,
    tag: "PRIMARY OPERATION", desc: "Five-agent expert system runs geometry, material, thermal, BIM and supply-chain panels against any drone payload — 90-second turnaround." },
  { id: "twin",        label: "Diagnostic Twin",         sub: "3D wireframe · framing · radiometric overlay", to: "/demo/twin",          icon: Box,          accent: "amber",   group: "demo",
    tag: "MODULE · TWIN", desc: "Rotatable parametric twin with shaded substrate layers, framing skeleton and live moisture pulse." },
  { id: "maint",       label: "AI Maintenance Priority", sub: "Urgency-ranked structural task queue",     to: "/demo/maintenance",   icon: Activity,     accent: "green",   group: "demo",
    tag: "MODULE · MAINT", desc: "Auto-prioritised repair backlog ranked by structural risk × insurance recoverability." },
  { id: "quant",       label: "STRATEX Quant™ Estimator", sub: "Take-off analytics · repair valuation",   to: "/demo/quant",         icon: Cpu,          accent: "magenta", group: "demo",
    tag: "MODULE · QUANT", desc: "Multi-agent estimating engine. Auto-maps every line-item to Xactimate under the locked 20/25 O&P envelope." },
  { id: "supply",      label: "Supply Chain Security",   sub: "Geofence · pipeline · encryption telemetry", to: "/demo/supply-chain",  icon: Shield,       accent: "amber",   group: "demo",
    tag: "MODULE · SUPPLY", desc: "Tripwire & geofence telemetry for the entire material pipeline — encryption + chain-of-custody attestation." },

  // ── Executive Cockpits ──
  { id: "ceo-ops",       label: "CEO Cockpit",          sub: "Single-tenant command center",            to: "/ceo/ops",       icon: Satellite,   accent: "volt",    group: "exec" },
  { id: "ceo-command",   label: "CEO Command Center",   sub: "Strategic theatre · live ops",            to: "/ceo/command",   icon: LayoutDashboard, accent: "volt",  group: "exec" },
  { id: "ceo-regional",  label: "Regional Switchboard", sub: "Branch heat-map · roster controls",       to: "/ceo/regional",  icon: Map,         accent: "cyan",    group: "exec" },
  { id: "ceo-fleet",     label: "MDU Fleet Portal",     sub: "Mobile drone unit roster & capital",      to: "/ceo/fleet",     icon: Truck,       accent: "cyan",    group: "exec" },
  { id: "ceo-suppliers", label: "Supplier Registry",    sub: "Expandable branch supplier index",        to: "/ceo/suppliers", icon: Cloud,       accent: "amber",   group: "exec" },
  { id: "ceo-inventory", label: "Inventory & Cost",     sub: "Material pricing & landed cost",          to: "/ceo/inventory", icon: Boxes,       accent: "amber",   group: "exec" },
  { id: "ceo-leads",     label: "Lead Pipeline",        sub: "Pre-build deal flow",                     to: "/ceo/leads",     icon: GitBranch,   accent: "green",   group: "exec" },
  { id: "ceo-blacklist", label: "Blacklist Matrix",     sub: "Tripwire breaches · banned actors",       to: "/ceo/blacklist", icon: AlertOctagon, accent: "magenta", group: "exec" },
  { id: "ceo-livemap",   label: "Live Fleet Map",       sub: "Real-time MDU & drone positions",         to: "/ceo/live-map",  icon: Compass,     accent: "cyan",    group: "exec" },
  { id: "ceo-login",     label: "CEO Secure Portal",    sub: "TOTP-gated executive access",             to: "/ceo/login",     icon: Shield,      accent: "magenta", group: "exec" },

  // ── Operations (GM · Admin · Pricing) ──
  { id: "gm-ops",        label: "GM Ops Dashboard",     sub: "Branch & tenant operations",              to: "/gm/ops",        icon: Activity,    accent: "amber",   group: "ops" },
  { id: "admin-ops",     label: "Admin Operations",     sub: "Cross-tenant supervisor view",            to: "/admin/ops",     icon: Workflow,    accent: "amber",   group: "ops" },
  { id: "admin-sales",   label: "Sales Hub",            sub: "Deal stages · contractor onboarding",     to: "/admin/sales",   icon: BarChart3,   accent: "volt",    group: "ops" },
  { id: "admin-branch",  label: "Branch Console",       sub: "Per-branch operating controls",           to: "/admin/branch-console", icon: Building2, accent: "cyan", group: "ops" },
  { id: "admin-overseer",label: "Overseer Queue",       sub: "Trifecta validation queue",               to: "/admin/overseer",icon: ListChecks,  accent: "green",   group: "ops" },
  { id: "admin-flight",  label: "Flight Audit",         sub: "Drone mission integrity review",          to: "/admin/flight-audit", icon: Plane,  accent: "cyan",    group: "ops" },
  { id: "admin-cvice",   label: "CV Ice-Shield",        sub: "Computer-vision ice & snow guard",        to: "/admin/cv-ice-shield", icon: Snowflake, accent: "cyan", group: "ops" },
  { id: "admin-weather", label: "Weather Telemetry",    sub: "Diurnal cycle & wind window",             to: "/admin/weather", icon: Cloud,       accent: "cyan",    group: "ops" },
  { id: "admin-consensus", label: "Consensus Engine",   sub: "Trifecta verification stack",             to: "/admin/consensus", icon: Network,   accent: "magenta", group: "ops" },
  { id: "admin-fleet",   label: "MDU Fleet (Admin)",    sub: "Capital & rig roster",                    to: "/admin/fleet",   icon: Truck,       accent: "amber",   group: "ops" },
  { id: "admin-blacklist", label: "Blacklist (Admin)",  sub: "Tripwire breaches",                       to: "/admin/blacklist", icon: AlertOctagon, accent: "magenta", group: "ops" },
  { id: "pricing",       label: "Pricing & Plans",      sub: "Contractor licensing tiers",              to: "/pricing",       icon: Wallet,      accent: "volt",    group: "ops" },

  // ── Field & Contractor ──
  { id: "contractor",    label: "Contractor Portal",    sub: "Jobs · materials · deliverables",         to: "/auth",          icon: Crosshair,   accent: "cyan",    group: "field" },
  { id: "onboard",       label: "Contractor Onboarding", sub: "NDA · ROI walkthrough",                  to: "/onboard",       icon: ScrollText,  accent: "volt",    group: "field" },
  { id: "pilot",         label: "Pilot Terminal",       sub: "Tablet-first field operator surface",     to: "/pilot",         icon: Sun,         accent: "amber",   group: "field" },
  { id: "operator",      label: "Operator Console",     sub: "Mission board · launch sequence",         to: "/operator",      icon: Radar,       accent: "cyan",    group: "field" },
  { id: "fleet",         label: "Fleet Board",          sub: "Active mission roster",                   to: "/fleet",         icon: Layers,      accent: "cyan",    group: "field" },
  { id: "fleet-livemap", label: "Fleet Live Map",       sub: "Real-time MDU positions",                 to: "/fleet/live-map",icon: Compass,     accent: "green",   group: "field" },
  { id: "launch",        label: "Fleet Launch",         sub: "Pre-flight checklist · go/no-go",         to: "/launch",        icon: Plane,       accent: "amber",   group: "field" },
  { id: "simulation",    label: "Simulation Run",       sub: "End-to-end workflow rehearsal",           to: "/simulation/demo", icon: FlaskConical, accent: "magenta", group: "field" },
  { id: "deliverable",   label: "Deliverable Preview",  sub: "Adjuster · homeowner report bundle",      to: "/deliverable/demo", icon: FileSearch, accent: "amber", group: "field" },
  { id: "deck",          label: "Pitch Deck",           sub: "Investor narrative",                      to: "/deck/demo",     icon: Eye,         accent: "volt",    group: "field" },
];

const GROUPS = [
  { id: "demo",  label: "Demo Modules",        sub: "Auth-free walkthroughs for live prospect demonstrations", accent: "cyan" },
  { id: "exec",  label: "Executive Cockpits",  sub: "Single-tenant command centers",                          accent: "volt" },
  { id: "ops",   label: "Operations",          sub: "GM · Admin · Pricing — branch and tenant ops",           accent: "amber" },
  { id: "field", label: "Field & Contractor",  sub: "Contractor portal · drone operator · pilot terminal",    accent: "green" },
];

// ──────────────────────────────────────────────────────────────────────────
// Sidebar atom — single app row.
// ──────────────────────────────────────────────────────────────────────────
function AppRow({ app, active, onSelect, onLaunch }) {
  const a = ACCENTS[app.accent];
  const Icon = app.icon;
  return (
    <div
      role="button"
      tabIndex={0}
      data-testid={`deck-rail-${app.id}`}
      onMouseEnter={() => onSelect(app.id)}
      onFocus={() => onSelect(app.id)}
      onClick={() => onLaunch(app.to)}
      onKeyDown={(e) => { if (e.key === "Enter") onLaunch(app.to); }}
      className="group relative flex items-center gap-3 px-3 py-2.5 cursor-pointer transition-all rounded-sm"
      style={{
        background: active ? `linear-gradient(90deg, ${a.hex}18 0%, transparent 80%)` : "transparent",
        borderLeft: `2px solid ${active ? a.hex : "transparent"}`,
        boxShadow: active ? `inset 0 0 24px ${a.hex}10` : "none",
      }}
    >
      <span
        className="shrink-0 grid place-items-center"
        style={{
          width: 28, height: 28,
          color: a.hex,
          filter: `drop-shadow(${a.glow})`,
        }}
      >
        <Icon size={16} strokeWidth={1.6}/>
      </span>
      <div className="min-w-0 flex-1">
        <div className="font-display text-[11.5px] uppercase tracking-[0.14em] text-slate-100 leading-tight truncate">
          {app.label}
        </div>
        <div className="font-mono text-[8.5px] tracking-[0.16em] text-slate-500 mt-0.5 truncate">
          {app.to}
        </div>
      </div>
      <ChevronRight
        size={12}
        className="opacity-0 group-hover:opacity-100 transition"
        style={{ color: a.hex }}
      />
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Bento canvas tile — main grid card.
// ──────────────────────────────────────────────────────────────────────────
function BentoTile({ app, span = "md", onLaunch }) {
  const a = ACCENTS[app.accent];
  const Icon = app.icon;
  const cls =
    span === "xl" ? "sm:col-span-2 lg:col-span-3 row-span-2" :
    span === "lg" ? "sm:col-span-2 row-span-2" :
    span === "wide" ? "sm:col-span-2" :
    "";
  return (
    <button
      onClick={() => onLaunch(app.to)}
      data-testid={`deck-tile-${app.id}`}
      className={`group relative text-left rounded-md p-5 md:p-6 transition-all hover:scale-[1.012] hover:brightness-110 overflow-hidden ${cls}`}
      style={{
        background: "linear-gradient(140deg, rgba(15,22,34,0.85) 0%, rgba(8,12,20,0.92) 60%, rgba(15,22,34,0.85) 100%)",
        border: `1px solid ${a.hex}3A`,
        boxShadow: `inset 0 0 36px ${a.hex}10, 0 0 0 1px ${a.hex}08`,
      }}
    >
      {/* corner bracket */}
      <span className="absolute top-2 right-2 w-3 h-3 border-t border-r" style={{ borderColor: a.hex }}/>
      <span className="absolute bottom-2 left-2 w-3 h-3 border-b border-l" style={{ borderColor: a.hex }}/>
      {/* scanline */}
      <span
        className="pointer-events-none absolute inset-0 opacity-20"
        style={{
          background: `repeating-linear-gradient(0deg, transparent 0px, transparent 3px, ${a.hex}08 3px, ${a.hex}08 4px)`,
        }}
      />
      <div className="relative">
        <div className="flex items-center gap-3 mb-4">
          <span
            className="grid place-items-center rounded-sm"
            style={{
              width: 40, height: 40,
              background: `${a.hex}12`,
              border: `1px solid ${a.hex}55`,
              color: a.hex,
              filter: `drop-shadow(${a.glow})`,
            }}
          >
            <Icon size={20} strokeWidth={1.6}/>
          </span>
          <span className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: a.hex }}>
            {app.tag || `MODULE · ${app.id.toUpperCase()}`}
          </span>
        </div>
        <h3 className="font-display text-base md:text-lg uppercase tracking-[0.12em] text-slate-100">
          {app.label}
        </h3>
        <p className="font-mono text-[10.5px] text-slate-400 mt-2 leading-relaxed tracking-wide">
          {app.sub}
        </p>
        {app.desc && span !== "md" && (
          <p className="text-[12.5px] text-slate-300/85 mt-3 leading-relaxed max-w-md">
            {app.desc}
          </p>
        )}
        <div className="mt-4 flex items-center justify-between">
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">{app.to}</span>
          <span className="font-mono text-[10px] tracking-[0.2em] uppercase flex items-center gap-1" style={{ color: a.hex }}>
            Launch <ChevronRight size={12}/>
          </span>
        </div>
      </div>
    </button>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Main page
// ──────────────────────────────────────────────────────────────────────────
export default function CommandDeck() {
  const nav = useNavigate();
  const [query, setQuery] = useState("");
  const [hoverId, setHoverId] = useState("scan");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return APPS;
    return APPS.filter(a =>
      a.label.toLowerCase().includes(q) ||
      a.sub.toLowerCase().includes(q) ||
      a.id.toLowerCase().includes(q) ||
      a.to.toLowerCase().includes(q)
    );
  }, [query]);

  const grouped = useMemo(() => {
    const g = {};
    for (const a of filtered) {
      (g[a.group] ||= []).push(a);
    }
    return g;
  }, [filtered]);

  const launch = (to) => nav(to);
  const active = APPS.find(a => a.id === hoverId) || APPS[0];
  const activeAccent = ACCENTS[active.accent];

  // Hero curation — three highest-value tiles.
  const featured = ["scan", "twin", "quant"]
    .map(id => APPS.find(a => a.id === id))
    .filter(Boolean);

  return (
    <div
      data-testid="command-deck"
      className="min-h-screen text-slate-100 flex"
      style={{
        background:
          "radial-gradient(ellipse at 78% 8%, rgba(0,229,255,0.10) 0%, transparent 55%)," +
          "radial-gradient(ellipse at 6% 92%, rgba(255,176,32,0.08) 0%, transparent 55%)," +
          "#02060B",
        fontFamily: "'Sora', sans-serif",
      }}
    >
      {/* animated grid floor */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 opacity-[0.06]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,229,255,0.7) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(0,229,255,0.7) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          maskImage: "radial-gradient(ellipse at center, black 30%, transparent 75%)",
          WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 75%)",
        }}
      />

      {/* ─────────────────────────────── LEFT RAIL ─────────────────────────────── */}
      <aside
        data-testid="deck-rail"
        className="hidden lg:flex flex-col shrink-0 sticky top-0 self-start h-screen w-[300px] border-r"
        style={{
          borderColor: "rgba(0,229,255,0.15)",
          background:
            "linear-gradient(180deg, rgba(8,12,20,0.85) 0%, rgba(2,6,11,0.95) 100%)",
          backdropFilter: "blur(14px)",
        }}
      >
        {/* logo block */}
        <div className="px-5 pt-6 pb-4 border-b" style={{ borderColor: "rgba(0,229,255,0.12)" }}>
          <button
            onClick={() => nav("/")}
            data-testid="deck-logo"
            className="block"
          >
            <StratexLogo height={44}/>
          </button>
          <div className="mt-3 font-mono text-[8.5px] tracking-[0.3em] text-cyan-400 uppercase">
            // COMMAND DECK · v4.0
          </div>
          <div className="mt-1 font-mono text-[8px] tracking-[0.22em] text-slate-500 uppercase">
            STRATEGIC THERMAL RECONNAISSANCE
          </div>
        </div>

        {/* search */}
        <div className="px-5 py-4 border-b" style={{ borderColor: "rgba(0,229,255,0.10)" }}>
          <div
            className="flex items-center gap-2 rounded-sm px-3 py-2"
            style={{
              background: "rgba(15,22,34,0.7)",
              border: "1px solid rgba(0,229,255,0.25)",
            }}
          >
            <Search size={13} className="text-cyan-400"/>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              data-testid="deck-search"
              placeholder="Search apps · routes"
              className="bg-transparent outline-none flex-1 font-mono text-[11px] tracking-wider text-slate-200 placeholder:text-slate-500"
            />
            {query && (
              <button
                onClick={() => setQuery("")}
                className="font-mono text-[10px] text-slate-500 hover:text-cyan-400"
              >
                CLR
              </button>
            )}
          </div>
        </div>

        {/* scrollable categories */}
        <nav
          className="flex-1 overflow-y-auto px-2 py-3 space-y-5 deck-rail-scroll"
          style={{ scrollbarWidth: "thin", scrollbarColor: "#00E5FF44 transparent" }}
        >
          {GROUPS.map((grp) => {
            const apps = grouped[grp.id] || [];
            if (apps.length === 0) return null;
            const dot = ACCENTS[grp.accent].hex;
            return (
              <div key={grp.id} data-testid={`deck-rail-group-${grp.id}`}>
                <div className="px-3 mb-2 flex items-center gap-2">
                  <span
                    className="w-1.5 h-1.5 rounded-full"
                    style={{ background: dot, boxShadow: `0 0 8px ${dot}` }}
                  />
                  <span className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-300">
                    {grp.label}
                  </span>
                  <span className="ml-auto font-mono text-[8px] text-slate-600">{apps.length}</span>
                </div>
                <div className="space-y-0.5">
                  {apps.map((a) => (
                    <AppRow
                      key={a.id}
                      app={a}
                      active={hoverId === a.id}
                      onSelect={setHoverId}
                      onLaunch={launch}
                    />
                  ))}
                </div>
              </div>
            );
          })}

          {Object.keys(grouped).length === 0 && (
            <div className="px-4 py-8 font-mono text-[10px] tracking-widest text-slate-600 uppercase text-center">
              No matches.
            </div>
          )}
        </nav>

        {/* rail footer */}
        <div className="px-5 py-3 border-t font-mono text-[8px] tracking-[0.24em] uppercase text-slate-600 flex items-center justify-between"
             style={{ borderColor: "rgba(0,229,255,0.10)" }}>
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ boxShadow: "0 0 6px #00FF9C" }}/>
            SYS · OPERATIONAL
          </span>
          <span>{APPS.length} APPS</span>
        </div>
      </aside>

      {/* ─────────────────────────────── MAIN CANVAS ─────────────────────────────── */}
      <main className="flex-1 min-w-0 relative">
        {/* mobile top brand bar */}
        <div className="lg:hidden sticky top-0 z-30 flex items-center justify-between px-4 py-3 border-b"
             style={{ borderColor: "rgba(0,229,255,0.15)", background: "rgba(2,6,11,0.92)", backdropFilter: "blur(14px)" }}>
          <StratexLogo height={28}/>
          <span className="font-mono text-[9px] tracking-[0.24em] text-cyan-400 uppercase">// COMMAND DECK</span>
        </div>

        {/* hero */}
        <section className="px-4 sm:px-8 lg:px-12 pt-10 lg:pt-14 pb-6 max-w-[1480px] mx-auto">
          <div className="flex items-center gap-3 mb-5">
            <span className="w-2 h-2 rounded-full" style={{ background: activeAccent.hex, boxShadow: `0 0 10px ${activeAccent.hex}` }}/>
            <span className="font-mono text-[10px] tracking-[0.32em] uppercase" style={{ color: activeAccent.hex }}>
              // {active.tag || `MODULE · ${active.id.toUpperCase()}`}
            </span>
            <span className="font-mono text-[9px] tracking-[0.22em] text-slate-500 uppercase hidden sm:inline">
              · {active.to}
            </span>
          </div>

          <h1 className="font-display text-[1.9rem] sm:text-5xl lg:text-6xl uppercase tracking-[0.04em] sm:tracking-[0.08em] leading-[0.96]"
              style={{ overflowWrap: "anywhere" }}>
            <span className="block text-slate-100">Every</span>
            <span className="block" style={{ color: activeAccent.hex, textShadow: `0 0 22px ${activeAccent.hex}66` }}>
              Command Surface
            </span>
            <span className="block text-slate-300">in one Deck.</span>
          </h1>

          <p className="mt-5 max-w-2xl text-[13px] sm:text-sm text-slate-400 font-mono tracking-wide leading-relaxed">
            Hover the rail to preview · click to launch. {APPS.length} live operational surfaces — demo modules, executive cockpits,
            branch operations and field terminals — wired to a single, brand-locked deck.
          </p>

          {/* live preview pill */}
          <div className="mt-6 inline-flex items-center gap-3 px-4 py-2.5 rounded-full"
               style={{
                 background: `linear-gradient(90deg, ${activeAccent.hex}14 0%, transparent 100%)`,
                 border: `1px solid ${activeAccent.hex}55`,
               }}>
            <Sparkles size={14} style={{ color: activeAccent.hex, filter: `drop-shadow(${activeAccent.glow})` }}/>
            <span className="font-mono text-[10.5px] tracking-[0.22em] uppercase text-slate-200">
              Previewing
            </span>
            <span className="font-display text-[12px] tracking-[0.14em] uppercase" style={{ color: activeAccent.hex }}>
              {active.label}
            </span>
            <button
              onClick={() => launch(active.to)}
              data-testid="deck-hero-launch"
              className="ml-2 font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1 rounded-full"
              style={{
                background: activeAccent.hex,
                color: "#02060B",
                boxShadow: activeAccent.glow,
              }}
            >
              LAUNCH →
            </button>
          </div>
        </section>

        {/* KPI strip */}
        <section className="px-4 sm:px-8 lg:px-12 pb-2 max-w-[1480px] mx-auto">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { k: "ACCURACY",   v: "±0.78 CM", c: "cyan" },
              { k: "TURNAROUND", v: "< 90 SEC", c: "amber" },
              { k: "O&P LOCK",   v: "20 / 25",  c: "volt" },
              { k: "UPLINK",     v: "STARLINK", c: "green" },
            ].map((m) => {
              const a = ACCENTS[m.c];
              return (
                <div
                  key={m.k}
                  data-testid={`deck-kpi-${m.k.toLowerCase().replace(/[^a-z]/g,'')}`}
                  className="px-4 py-3 rounded-sm"
                  style={{
                    background: "rgba(15,22,34,0.6)",
                    border: `1px solid ${a.hex}33`,
                  }}
                >
                  <div className="font-mono text-[8.5px] tracking-[0.3em] uppercase text-slate-500">{m.k}</div>
                  <div className="font-display text-base sm:text-lg mt-1 tracking-[0.1em]"
                       style={{ color: a.hex, textShadow: `0 0 12px ${a.hex}55` }}>
                    {m.v}
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        {/* Featured row */}
        <section className="px-4 sm:px-8 lg:px-12 pt-8 max-w-[1480px] mx-auto">
          <div className="flex items-baseline justify-between mb-4">
            <div className="flex items-center gap-3">
              <span className="w-2 h-2 rounded-full" style={{ background: "#00E5FF", boxShadow: "0 0 8px #00E5FF" }}/>
              <h2 className="font-display text-base sm:text-lg uppercase tracking-[0.2em] text-slate-100">Primary Missions</h2>
            </div>
            <span className="font-mono text-[9px] tracking-[0.24em] uppercase text-slate-500 hidden sm:inline">// hero deck</span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {featured.map((a, i) => (
              <BentoTile key={a.id} app={a} span={i === 0 ? "wide" : "md"} onLaunch={launch}/>
            ))}
          </div>
        </section>

        {/* Group canvases */}
        {GROUPS.map((grp) => {
          const apps = grouped[grp.id] || [];
          if (apps.length === 0) return null;
          const dot = ACCENTS[grp.accent].hex;
          return (
            <section key={grp.id} className="px-4 sm:px-8 lg:px-12 pt-10 max-w-[1480px] mx-auto"
                     data-testid={`deck-section-${grp.id}`}>
              <div className="flex items-baseline justify-between mb-4 gap-3 flex-wrap">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="w-2 h-2 rounded-full shrink-0" style={{ background: dot, boxShadow: `0 0 8px ${dot}` }}/>
                  <h2 className="font-display text-base sm:text-lg uppercase tracking-[0.18em] text-slate-100 truncate">
                    {grp.label}
                  </h2>
                  <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500 hidden md:inline truncate">
                    // {grp.sub}
                  </span>
                </div>
                <span className="font-mono text-[9px] tracking-[0.24em] uppercase text-slate-500 shrink-0">
                  {apps.length} APPS
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {apps.map((a) => <BentoTile key={a.id} app={a} onLaunch={launch}/>)}
              </div>
            </section>
          );
        })}

        {/* Footer */}
        <footer className="px-4 sm:px-8 lg:px-12 mt-14 pb-10 max-w-[1480px] mx-auto">
          <div className="border-t pt-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-3"
               style={{ borderColor: "rgba(0,229,255,0.12)" }}>
            <div className="flex items-center gap-3">
              <StratexLogo height={22}/>
              <span className="font-mono text-[8.5px] tracking-[0.24em] uppercase text-slate-600">
                STRATEGIC THERMAL RECONNAISSANCE · GROUND-TRUTH ±0.78 CM · PATENT PENDING
              </span>
            </div>
            <span className="font-mono text-[9px] tracking-[0.24em] uppercase text-cyan-400">
              COMMAND DECK · v4.0
            </span>
          </div>
        </footer>
      </main>

      {/* scrollbar styling */}
      <style>{`
        .deck-rail-scroll::-webkit-scrollbar { width: 6px; }
        .deck-rail-scroll::-webkit-scrollbar-track { background: transparent; }
        .deck-rail-scroll::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.28); border-radius: 4px; }
        .deck-rail-scroll::-webkit-scrollbar-thumb:hover { background: rgba(0,229,255,0.5); }
      `}</style>
    </div>
  );
}
