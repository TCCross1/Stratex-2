// STRATEX™ — Switchboard Landing
// The unauthenticated front door for live demos. Five tiles:
//  1. NEW DRONE SCAN -> instant report wizard
//  2. Diagnostic Twin Command  -> /demo/twin
//  3. AI Maintenance Prioritization -> /demo/maintenance
//  4. STRATEX Quant™ Estimator Engine -> /demo/quant
//  5. Supply Chain Security Plane -> /demo/supply-chain
//
// Auth portals (CEO / GM / Contractor / Operator) remain reachable
// via the bottom rail for normal day-to-day use.

import { useNavigate } from "react-router-dom";
import { StratexLogo } from "@/components/StratexBrand";

const TILES = [
  {
    id: "scan",
    title: "New Drone Scan",
    sub: "Upload imagery → Instant CAD/BIM forensic report",
    color: "cyan",
    accent: "#00E5FF",
    path: "/demo/scan",
    hero: true,
    icon: "drone",
  },
  {
    id: "twin",
    title: "Diagnostic Twin Command",
    sub: "3D wireframe · framing · radiometric overlay",
    color: "amber",
    accent: "#FFB020",
    path: "/demo/twin",
    icon: "twin",
  },
  {
    id: "maint",
    title: "AI Maintenance Prioritization",
    sub: "Urgency-ranked structural task queue",
    color: "green",
    accent: "#00FF9C",
    path: "/demo/maintenance",
    icon: "list",
  },
  {
    id: "quant",
    title: "STRATEX Quant™ Estimator",
    sub: "Take-off analytics · repair valuation",
    color: "mag",
    accent: "#FF2D78",
    path: "/demo/quant",
    icon: "calc",
  },
  {
    id: "supply",
    title: "Supply Chain Security",
    sub: "Geofence · pipeline · encryption telemetry",
    color: "orange",
    accent: "#FF7B00",
    path: "/demo/supply-chain",
    icon: "shield",
  },
];

const PORTALS = [
  { label: "CEO Portal",        path: "/ceo/login",  testid: "portal-ceo" },
  { label: "GM Ops",            path: "/gm/ops",     testid: "portal-gm" },
  { label: "Contractor Portal", path: "/auth",       testid: "portal-contractor" },
  { label: "Pilot Terminal",    path: "/pilot",      testid: "portal-pilot" },
];

function GlyphDrone() {
  return (
    <svg viewBox="0 0 60 60" width="48" height="48" fill="none" stroke="currentColor" strokeWidth="1.5">
      <circle cx="12" cy="12" r="6"/><circle cx="48" cy="12" r="6"/>
      <circle cx="12" cy="48" r="6"/><circle cx="48" cy="48" r="6"/>
      <rect x="22" y="22" width="16" height="16" rx="2"/>
      <line x1="17" y1="17" x2="22" y2="22"/><line x1="43" y1="17" x2="38" y2="22"/>
      <line x1="17" y1="43" x2="22" y2="38"/><line x1="43" y1="43" x2="38" y2="38"/>
      <circle cx="30" cy="30" r="2" fill="currentColor"/>
    </svg>
  );
}
function GlyphTwin() {
  return (
    <svg viewBox="0 0 60 60" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M30 8 L52 22 L30 36 L8 22 Z"/><path d="M30 36 L30 52"/>
      <path d="M8 22 L8 38 L30 52 L52 38 L52 22"/><path d="M19 28 L41 28"/>
    </svg>
  );
}
function GlyphList() {
  return (
    <svg viewBox="0 0 60 60" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="10" y="14" width="6" height="6"/><line x1="22" y1="17" x2="50" y2="17"/>
      <rect x="10" y="27" width="6" height="6"/><line x1="22" y1="30" x2="50" y2="30"/>
      <rect x="10" y="40" width="6" height="6"/><line x1="22" y1="43" x2="50" y2="43"/>
    </svg>
  );
}
function GlyphCalc() {
  return (
    <svg viewBox="0 0 60 60" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
      <rect x="12" y="8" width="36" height="44" rx="3"/>
      <rect x="18" y="14" width="24" height="8"/>
      <circle cx="22" cy="32" r="2"/><circle cx="30" cy="32" r="2"/><circle cx="38" cy="32" r="2"/>
      <circle cx="22" cy="42" r="2"/><circle cx="30" cy="42" r="2"/><circle cx="38" cy="42" r="2"/>
    </svg>
  );
}
function GlyphShield() {
  return (
    <svg viewBox="0 0 60 60" width="40" height="40" fill="none" stroke="currentColor" strokeWidth="1.5">
      <path d="M30 6 L52 16 L52 32 C52 44 42 52 30 56 C18 52 8 44 8 32 L8 16 Z"/>
      <path d="M20 30 L28 38 L42 22"/>
    </svg>
  );
}
const ICONS = { drone: GlyphDrone, twin: GlyphTwin, list: GlyphList, calc: GlyphCalc, shield: GlyphShield };

export default function Switchboard() {
  const nav = useNavigate();
  return (
    <div className="min-h-screen bg-obsidian text-silver font-sans" data-testid="switchboard-page" style={{
      background: "radial-gradient(ellipse at 70% 10%, rgba(0,229,255,0.10) 0%, transparent 55%), radial-gradient(ellipse at 10% 90%, rgba(255,123,0,0.08) 0%, transparent 55%), #02060B",
    }}>
      {/* Top rail */}
      <div className="border-b border-cyan-400/15 px-4 sm:px-8 py-3 flex items-center justify-between gap-3">
        <StratexLogo height={36}/>
        <div className="font-mono text-[8px] sm:text-[9px] text-slate-400 tracking-widest hidden sm:block">
          STRATEGIC THERMAL RECONNAISSANCE · MASTER SWITCHBOARD
        </div>
        <div className="font-mono text-[9px] tracking-widest text-emerald-400 flex items-center gap-2 shrink-0">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"/> SYS · OPERATIONAL
        </div>
      </div>

      {/* Hero brand lock-up */}
      <div className="px-4 sm:px-8 pt-10 pb-2 max-w-[1480px] mx-auto flex flex-col items-start">
        <StratexLogo height={96} className="mb-6"/>
        <div className="font-mono text-[10px] tracking-[0.32em] text-cyan-400 mb-3">
          // MASTER PORTAL SWITCHBOARD · DEMO MODE ACTIVE
        </div>
        <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-white">
          Choose Your <span className="text-cyan-400" style={{ textShadow: "0 0 18px rgba(0,229,255,0.55)" }}>Command Plane</span>
        </h1>
        <p className="font-mono text-xs tracking-wide text-slate-400 mt-4 max-w-2xl leading-relaxed">
          Five operational modules. Zero friction. Upload any drone payload to receive a forensic
          CAD/BIM report — squares, valleys, gables, layered digital twin, BOM, labor, and
          unforeseen-repair side quote — in under 90 seconds.
        </p>
      </div>

      {/* Hero scan tile */}
      <div className="px-8 max-w-[1480px] mx-auto">
        {(() => {
          const t = TILES[0];
          const Icon = ICONS[t.icon];
          return (
            <button
              onClick={() => nav(t.path)}
              data-testid="tile-scan-hero"
              className="group w-full text-left rounded-lg border-2 p-8 transition-all hover:scale-[1.005] hover:brightness-110"
              style={{
                borderColor: "rgba(0,229,255,0.55)",
                background: "linear-gradient(135deg, rgba(0,229,255,0.08) 0%, rgba(15,22,34,0.65) 50%, rgba(255,123,0,0.06) 100%)",
                boxShadow: "0 0 40px rgba(0,229,255,0.18), inset 0 0 60px rgba(0,229,255,0.04)",
              }}
            >
              <div className="flex items-start justify-between gap-6">
                <div className="flex items-start gap-6">
                  <div className="text-cyan-400 shrink-0" style={{ filter: "drop-shadow(0 0 6px rgba(0,229,255,0.6))" }}>
                    <Icon/>
                  </div>
                  <div>
                    <div className="font-mono text-[9px] tracking-[0.28em] text-cyan-400 mb-2">
                      PRIMARY OPERATION
                    </div>
                    <div className="text-3xl sm:text-4xl font-bold text-white tracking-tight">
                      {t.title}
                    </div>
                    <div className="font-mono text-xs text-slate-300 mt-2 tracking-wide">
                      {t.sub}
                    </div>
                  </div>
                </div>
                <div className="font-mono text-xs text-cyan-400 tracking-[0.18em] mt-3 shrink-0">
                  LAUNCH →
                </div>
              </div>
            </button>
          );
        })()}
      </div>

      {/* Other tiles */}
      <div className="px-8 mt-6 max-w-[1480px] mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {TILES.slice(1).map((t) => {
          const Icon = ICONS[t.icon];
          return (
            <button
              key={t.id}
              onClick={() => nav(t.path)}
              data-testid={`tile-${t.id}`}
              className="group text-left rounded-md p-6 transition-all hover:scale-[1.01] hover:brightness-110"
              style={{
                border: `1px solid ${t.accent}66`,
                background: "rgba(15,22,34,0.65)",
                boxShadow: `inset 0 0 28px ${t.accent}15`,
              }}
            >
              <div style={{ color: t.accent, filter: `drop-shadow(0 0 5px ${t.accent}99)` }}>
                <Icon/>
              </div>
              <div className="font-mono text-[8px] tracking-[0.24em] mt-3" style={{ color: t.accent }}>
                MODULE · {t.id.toUpperCase()}
              </div>
              <div className="text-lg font-bold text-white mt-1 tracking-tight">{t.title}</div>
              <div className="font-mono text-[10px] text-slate-400 mt-1.5 leading-relaxed">{t.sub}</div>
            </button>
          );
        })}
      </div>

      {/* Auth portals rail */}
      <div className="px-8 mt-12 max-w-[1480px] mx-auto pb-12">
        <div className="font-mono text-[9px] tracking-[0.28em] text-slate-500 mb-3">
          // OPERATIONAL PORTALS · AUTHENTICATED USERS
        </div>
        <div className="flex flex-wrap gap-2">
          {PORTALS.map((p) => (
            <button
              key={p.path}
              data-testid={p.testid}
              onClick={() => nav(p.path)}
              className="px-4 py-2 rounded font-mono text-[10px] tracking-[0.18em] text-slate-300 border border-slate-700 hover:border-cyan-400/60 hover:text-cyan-400 transition"
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="font-mono text-[8px] tracking-widest text-slate-600 mt-8 flex items-center gap-3">
          <StratexLogo height={20}/>
          <span>· STRATEGIC THERMAL RECONNAISSANCE · GROUND-TRUTH ACCURACY ±0.78 CM · PATENT PENDING · CONFIDENTIAL &amp; PROPRIETARY</span>
        </div>
      </div>
    </div>
  );
}
