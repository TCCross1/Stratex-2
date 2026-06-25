// STRATEX™ — CONTRACTOR COMMAND · PROJECT OVERSIGHT PORTAL
// Faithful reproduction of the gold-filigree, cyan-bezel command portal
// reference supplied for the American Roofing Company live pitch.
//
// Layout (top → bottom · L→R):
//   Title bar : crane + "CONTRACTOR COMMAND // PROJECT OVERSIGHT PORTAL"
//   Row 1     : CURRENT PROJECTS · COMPLETED JOB REPORTS · INVOICE · BILLING & INVOICES
//   Row 2     : FINAL REPORTS BOX · PROFESSIONAL CREDENTIALS · PREFERRED VENDOR NETWORK
//   Row 3     : PRE-FLIGHT MISSION CRITICAL GATEWAY · CLIENT PORTFOLIO · PRE-FLIGHT GATES + KPIs + CORPORATE
//
// Brand-locked palette:
//   Gold filigree     #D4B86A → #8C6D32
//   Cyan bezel        #00E5FF · with #00E5FF22 inner glow
//   Accent green      #00FF9C   (active / OK)
//   Accent amber/red  #FF7B00 / #FF2D78  (warn / alert)
//   Background        radial obsidian + faint server-room blueprint

import React, { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useContractor } from "@/lib/contractor";
import {
  Check, AlertOctagon, Truck, Battery, Plane, FileText,
  ShieldCheck, Cpu, Layers, Boxes,
} from "lucide-react";

// ─────────────────────────────────────────────────────────────────────────
// Pure-SVG construction crane (gold) — matches the mockup's masthead glyph.
// ─────────────────────────────────────────────────────────────────────────
function CraneGlyph({ size = 110 }) {
  return (
    <svg viewBox="0 0 200 140" width={size} height={size * 0.7}
         style={{ filter: "drop-shadow(0 0 10px rgba(212,184,106,0.65))" }}>
      <defs>
        <linearGradient id="cgGold" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#F5E0A3"/>
          <stop offset="50%" stopColor="#D4B86A"/>
          <stop offset="100%" stopColor="#8C6D32"/>
        </linearGradient>
      </defs>
      <g fill="none" stroke="url(#cgGold)" strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round">
        {/* mast */}
        <line x1="34" y1="14" x2="34" y2="124"/>
        <line x1="48" y1="14" x2="48" y2="124"/>
        <line x1="34" y1="14" x2="48" y2="14"/>
        {[28, 44, 60, 76, 92, 108].map((y) => (
          <g key={y}>
            <line x1="34" y1={y} x2="48" y2={y}/>
            <line x1="34" y1={y} x2="48" y2={y + 8}/>
          </g>
        ))}
        {/* boom */}
        <line x1="34" y1="30" x2="180" y2="30"/>
        <line x1="48" y1="44" x2="180" y2="30"/>
        {/* boom truss */}
        {Array.from({length: 8}).map((_, i) => {
          const x = 48 + i * 16;
          return <line key={i} x1={x} y1="30" x2={x + 8} y2="44"/>;
        })}
        {/* hook line */}
        <line x1="170" y1="30" x2="170" y2="76"/>
        {/* hook */}
        <path d="M 162 76 L 178 76 L 178 86 L 170 92 L 162 86 Z"/>
        {/* house glyph the crane is lifting */}
        <g stroke="url(#cgGold)" strokeWidth="2">
          <path d="M 96 130 L 96 102 L 130 80 L 164 102 L 164 130 Z"/>
          <line x1="96" y1="130" x2="164" y2="130"/>
          <path d="M 90 104 L 130 76 L 170 104"/>
        </g>
      </g>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Gold filigree corner ornament (top-left orientation; flip via transform).
// Inspired by Victorian engraving frames — kept as a single reusable path.
// ─────────────────────────────────────────────────────────────────────────
function FiligreeCorner({ flipX = false, flipY = false, size = 110 }) {
  const sx = flipX ? -1 : 1;
  const sy = flipY ? -1 : 1;
  return (
    <svg viewBox="0 0 140 140" width={size} height={size}
         style={{ position: "absolute",
                  top: flipY ? "auto" : 6, bottom: flipY ? 6 : "auto",
                  left: flipX ? "auto" : 6, right: flipX ? 6 : "auto",
                  pointerEvents: "none" }}>
      <defs>
        <linearGradient id={`fg-${flipX}${flipY}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="#F5E0A3"/>
          <stop offset="50%" stopColor="#D4B86A"/>
          <stop offset="100%" stopColor="#8C6D32"/>
        </linearGradient>
      </defs>
      <g transform={`scale(${sx} ${sy}) translate(${flipX ? -140 : 0} ${flipY ? -140 : 0})`}
         fill="none" stroke={`url(#fg-${flipX}${flipY})`} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
        {/* main double-arc */}
        <path d="M 2 50 Q 2 2 50 2"/>
        <path d="M 2 70 Q 2 18 70 18"/>
        {/* inner curl */}
        <path d="M 18 50 Q 18 18 50 18 Q 70 18 70 36 Q 70 50 56 50 Q 44 50 44 38"/>
        {/* outer flourish leaves */}
        <path d="M 78 6 Q 92 6 96 22 Q 100 38 116 38 Q 130 38 130 22"/>
        <path d="M 6 78 Q 6 92 22 96 Q 38 100 38 116 Q 38 130 22 130"/>
        {/* tendril */}
        <path d="M 50 18 Q 60 12 70 16 Q 80 20 86 30"/>
        <path d="M 18 50 Q 12 60 16 70 Q 20 80 30 86"/>
        {/* dots */}
        <circle cx="50" cy="2"  r="1.6" fill="#F5E0A3"/>
        <circle cx="2"  cy="50" r="1.6" fill="#F5E0A3"/>
        <circle cx="96" cy="22" r="1.4" fill="#D4B86A"/>
        <circle cx="22" cy="96" r="1.4" fill="#D4B86A"/>
      </g>
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Cyan-bezel panel — matches the rounded cyan frames in the mockup.
// ─────────────────────────────────────────────────────────────────────────
function Panel({ title, accent = "cyan", children, className = "", testid, ornate = false }) {
  const accentMap = {
    cyan:  { hex: "#00E5FF", bg: "rgba(0,229,255,0.05)" },
    gold:  { hex: "#D4B86A", bg: "rgba(212,184,106,0.06)" },
    green: { hex: "#00FF9C", bg: "rgba(0,255,156,0.05)" },
    amber: { hex: "#FF7B00", bg: "rgba(255,123,0,0.05)" },
  };
  const a = accentMap[accent] || accentMap.cyan;
  return (
    <div
      data-testid={testid}
      className={`relative rounded-2xl ${className}`}
      style={{
        background: `linear-gradient(180deg, rgba(8,14,24,0.86) 0%, rgba(4,8,14,0.92) 100%), ${a.bg}`,
        border: `1.5px solid ${a.hex}88`,
        boxShadow:
          `0 0 0 1px ${a.hex}22, ` +
          `inset 0 0 36px ${a.hex}10, ` +
          `0 0 18px ${a.hex}25`,
      }}
    >
      {ornate && (
        <>
          <FiligreeCorner size={64}/>
          <FiligreeCorner size={64} flipX/>
          <FiligreeCorner size={64} flipY/>
          <FiligreeCorner size={64} flipX flipY/>
        </>
      )}
      {title && (
        <div className="px-4 pt-3 pb-2 flex items-center justify-center">
          <h3
            className="font-display tracking-[0.22em] uppercase text-[13px] sm:text-[14px]"
            style={{
              color: accent === "gold" ? "#F5E0A3" : a.hex,
              textShadow: `0 0 10px ${accent === "gold" ? "#D4B86A" : a.hex}aa`,
              fontFamily: "'Cinzel', 'Trajan Pro', 'Times New Roman', serif",
              fontWeight: 700,
            }}
          >
            {title}
          </h3>
        </div>
      )}
      <div className="px-4 pb-4">{children}</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Small primitives
// ─────────────────────────────────────────────────────────────────────────
const Row = ({ label, value, valueColor = "#FFFFFF", testid }) => (
  <div data-testid={testid} className="flex items-center justify-between gap-3 py-1">
    <span className="font-mono text-[10.5px] tracking-[0.12em] text-slate-300/85 uppercase">{label}</span>
    <span className="font-mono text-[11px] tracking-[0.14em] uppercase" style={{ color: valueColor }}>
      {value}
    </span>
  </div>
);

const StatusPill = ({ text, color }) => (
  <span
    className="inline-block px-2 py-0.5 rounded-full font-mono text-[9.5px] tracking-[0.16em] uppercase"
    style={{ color, border: `1px solid ${color}66`, background: `${color}10` }}
  >
    {text}
  </span>
);

const CheckLine = ({ ok = true, label, sub, color }) => {
  const c = color || (ok ? "#00FF9C" : "#FF7B00");
  return (
    <div className="flex items-start gap-3 py-2">
      <span
        className="grid place-items-center rounded-sm shrink-0"
        style={{ width: 22, height: 22, background: `${c}18`, border: `1px solid ${c}aa` }}
      >
        <Check size={12} color={c} strokeWidth={3}/>
      </span>
      <div className="min-w-0">
        <div className="font-display tracking-[0.06em] text-[12px] sm:text-[13px] uppercase text-white leading-tight">{label}</div>
        {sub && (
          <div className="font-mono text-[9.5px] tracking-[0.12em] uppercase text-slate-400 mt-0.5">{sub}</div>
        )}
      </div>
    </div>
  );
};

const ProgressBar = ({ pct, color = "#00FF9C" }) => (
  <div className="w-full h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
    <div className="h-full rounded-full" style={{
      width: `${pct}%`,
      background: `linear-gradient(90deg, ${color} 0%, ${color}80 100%)`,
      boxShadow: `0 0 10px ${color}`,
    }}/>
  </div>
);

// ─────────────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────────────
export default function CommandDeck() {
  const nav = useNavigate();
  const c = useContractor();

  // load Cinzel display font once for the ornate title look
  useEffect(() => {
    const id = "cd-cinzel-font";
    if (!document.getElementById(id)) {
      const link = document.createElement("link");
      link.id = id;
      link.rel = "stylesheet";
      link.href = "https://fonts.googleapis.com/css2?family=Cinzel:wght@500;700;900&display=swap";
      document.head.appendChild(link);
    }
  }, []);

  const currentProjects = [
    { id: "LX_ROOF_001",   trade: "Roofing", status: "IN PROGRESS", color: "#FFB020" },
    { id: "LX_SIDING_002", trade: "Siding",  status: "COMPLETED",   color: "#00FF9C" },
    { id: "LX_WIN_003",    trade: "Windows", status: "SCHEDULED",   color: "#00E5FF" },
  ];

  const completedJobs = [
    { addr: "2440 Regency Road",      city: "Lexington, KY",    compliance: true, start: "07/20/2025" },
    { addr: "1185 Harrodsburg Pike",  city: "Lexington, KY",    compliance: true, start: "09/19/2025" },
    { addr: "808 Tates Creek Rd",     city: "Lexington, KY",    compliance: true, start: "10/14/2025" },
  ];

  const recentInvoices = [
    { id: "INV-0045", desc: "Moisture Scan · LX_ROOF_001",  due: "01/14/2026", amount: 1250.00 },
    { id: "INV-0046", desc: "Fleet Deployment",             due: "01/14/2026", amount: 10.00 },
  ];

  const vendors = [
    { name: "GAF",          line: "ROOFING",  approved: true },
    { name: "Owens Corning",line: "ROOFING",  approved: true },
    { name: "CertainTeed",  line: "ROOFING",  approved: true },
    { name: "James Hardie", line: "SIDING",   approved: true },
    { name: "Andersen",     line: "WINDOWS",  approved: true },
    { name: "Pella",        line: "WINDOWS",  approved: true },
  ];

  const clientPortfolio = [
    { name: "Bingham Family Trust",     contact: "client-link", jobs: 10, projects: 2, color: "#FFB020" },
    { name: "Bluegrass Property Group", contact: "client-link", jobs: 20, projects: 1, color: "#00E5FF" },
  ];

  return (
    <div
      data-testid="command-deck"
      className="min-h-screen text-slate-100"
      style={{
        background:
          // server-room ambient
          "radial-gradient(ellipse at 50% 0%, rgba(0,229,255,0.08) 0%, transparent 50%)," +
          "radial-gradient(ellipse at 20% 100%, rgba(212,184,106,0.07) 0%, transparent 55%)," +
          "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
        fontFamily: "'Sora', sans-serif",
      }}
    >
      {/* faint blueprint grid */}
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 opacity-[0.045]"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px)," +
            "linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
          backgroundSize: "48px 48px",
        }}
      />

      {/* OUTER GOLD FILIGREE FRAME ─────────────────────────────────────── */}
      <div className="relative mx-auto max-w-[1500px] my-4 sm:my-6 px-3 sm:px-6">
        <div
          className="relative rounded-[28px] p-4 sm:p-6 lg:p-8"
          style={{
            background: "linear-gradient(180deg, rgba(7,11,20,0.94) 0%, rgba(3,6,12,0.96) 100%)",
            border: "2px solid #D4B86A",
            boxShadow:
              "0 0 0 4px rgba(212,184,106,0.08)," +
              "0 0 0 5px rgba(212,184,106,0.55)," +
              "0 0 0 7px rgba(212,184,106,0.10)," +
              "inset 0 0 60px rgba(212,184,106,0.05)," +
              "0 0 60px rgba(0,229,255,0.10)",
          }}
        >
          {/* gold ornamental corners */}
          <FiligreeCorner/>
          <FiligreeCorner flipX/>
          <FiligreeCorner flipY/>
          <FiligreeCorner flipX flipY/>

          {/* ===================== MASTHEAD ===================== */}
          <header className="flex flex-col sm:flex-row items-center sm:items-end gap-4 sm:gap-6 px-4 pt-4 sm:pt-2 pb-6">
            {/* crane glyph */}
            <div className="shrink-0">
              <CraneGlyph size={120}/>
            </div>

            {/* title block */}
            <div className="flex-1 min-w-0 text-center sm:text-left">
              <h1
                data-testid="cd-title"
                className="leading-none tracking-[0.04em]"
                style={{
                  fontFamily: "'Cinzel', serif",
                  fontWeight: 900,
                  fontSize: "clamp(22px, 3.4vw, 44px)",
                  color: "#F5E0A3",
                  textShadow: "0 0 14px rgba(212,184,106,0.65), 0 2px 0 rgba(0,0,0,0.6)",
                }}
              >
                CONTRACTOR COMMAND <span style={{ color: "#D4B86A" }}>//</span> PROJECT OVERSIGHT PORTAL
              </h1>

              <div className="mt-2 flex flex-wrap items-center justify-center sm:justify-start gap-x-4 gap-y-1 font-mono uppercase tracking-[0.18em] text-[10.5px] sm:text-[11.5px]">
                <span className="text-slate-300">CONTRACTOR:</span>
                <span data-testid="cd-business-name" className="text-white">{c.business_name}</span>
                <span className="text-slate-500">//</span>
                <span style={{ color: "#00E5FF" }}>LICENSED CONTRACTOR</span>
                <span className="text-slate-500">·</span>
                <span className="text-slate-300">STATUS:</span>
                <span style={{ color: "#00FF9C", textShadow: "0 0 8px #00FF9C" }}>{c.status} [LIC: {c.license_no}]</span>
              </div>

              <div className="mt-1 flex flex-wrap items-center justify-center sm:justify-start gap-x-3 gap-y-0.5 font-mono uppercase tracking-[0.18em] text-[10px] text-slate-400">
                <span>{c.address}</span>
                <span className="text-slate-600">·</span>
                <span>{c.city_state}</span>
                <span className="text-slate-600">·</span>
                <span>{c.phone}</span>
              </div>
            </div>

            {/* contractor logo */}
            <div className="shrink-0">
              <div
                className="rounded-md px-4 py-2.5"
                style={{
                  background: "rgba(255,255,255,0.04)",
                  border: "1px solid rgba(212,184,106,0.55)",
                  boxShadow: "0 0 24px rgba(212,184,106,0.18) inset",
                }}
              >
                <img
                  src={c.logo_url}
                  alt={c.business_name}
                  data-testid="cd-contractor-logo"
                  style={{ height: 64, width: "auto", display: "block", maxWidth: 220 }}
                />
              </div>
            </div>
          </header>

          {/* divider */}
          <div className="mb-5" style={{ height: 1, background: "linear-gradient(90deg, transparent 0%, #D4B86A 50%, transparent 100%)" }}/>

          {/* ===================== ROW 1 ===================== */}
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-4">
            {/* CURRENT PROJECTS */}
            <Panel title="Current Projects" testid="panel-current-projects">
              <div className="grid grid-cols-[1fr_auto] gap-x-3 gap-y-2 font-mono text-[10.5px] tracking-[0.14em] uppercase">
                <span className="text-slate-400">Job ID</span>
                <span className="text-slate-400 text-right">Status</span>
                {currentProjects.map((p) => (
                  <React.Fragment key={p.id}>
                    <span data-testid={`cp-${p.id}`} className="text-white truncate">{p.id}</span>
                    <span className="text-right">
                      <span className="text-slate-300">{p.trade}</span>
                      <span className="text-slate-600"> · </span>
                      <span style={{ color: p.color, textShadow: `0 0 6px ${p.color}` }}>{p.status}</span>
                    </span>
                  </React.Fragment>
                ))}
              </div>
            </Panel>

            {/* COMPLETED JOB REPORTS */}
            <Panel title="Completed Job Reports" testid="panel-completed-reports">
              <div className="grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1.5 font-mono text-[10.5px] tracking-[0.12em] uppercase">
                <span className="text-slate-400">Address</span>
                <span className="text-slate-400">Comp.</span>
                <span className="text-slate-400">Start</span>
                {completedJobs.map((j, i) => (
                  <React.Fragment key={i}>
                    <span className="text-white truncate">{j.addr}</span>
                    <span style={{ color: "#00FF9C" }} className="text-center"><Check size={12} className="inline" strokeWidth={3}/></span>
                    <span className="text-slate-300">{j.start}</span>
                  </React.Fragment>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t flex items-center justify-between" style={{ borderColor: "rgba(0,229,255,0.18)" }}>
                <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-400">Total Finalized Reports</span>
                <span className="font-display text-[16px]" style={{ color: "#00E5FF", textShadow: "0 0 10px #00E5FFaa" }}>
                  {c.metrics.total_finalized_reports}
                </span>
              </div>
            </Panel>

            {/* INVOICE / brand panel */}
            <Panel title="Invoice" testid="panel-invoice">
              <div className="flex flex-col items-center gap-2 py-1">
                <img src={c.logo_url} alt={c.business_name} style={{ height: 48, width: "auto", maxWidth: "100%" }}/>
                <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-slate-300">{c.business_name}</div>
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-slate-500">{c.tagline}</div>
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-slate-500 mt-1">{c.address}</div>
                <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-slate-500">{c.city_state}</div>
              </div>
            </Panel>

            {/* BILLING & INVOICES */}
            <Panel title="Billing & Invoices" testid="panel-billing">
              <div className="text-center">
                <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-400">Current Account Balance</div>
                <div className="font-display mt-1 tracking-[0.04em]"
                     style={{ fontSize: 32, color: "#FFB020", textShadow: "0 0 14px rgba(255,176,32,0.55)" }}>
                  ${c.metrics.current_balance_usd.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </div>
              </div>
              <div className="mt-3 grid grid-cols-[1fr_auto_auto] gap-x-3 gap-y-1 font-mono text-[9.5px] tracking-[0.12em] uppercase">
                <span className="text-slate-400">Invoice</span>
                <span className="text-slate-400">Due</span>
                <span className="text-slate-400 text-right">Amount</span>
                {recentInvoices.map((iv) => (
                  <React.Fragment key={iv.id}>
                    <span className="text-white truncate">{iv.id} · {iv.desc}</span>
                    <span className="text-slate-300">{iv.due}</span>
                    <span className="text-right" style={{ color: "#00E5FF" }}>${iv.amount.toFixed(2)}</span>
                  </React.Fragment>
                ))}
              </div>
              <button
                data-testid="cd-statement-btn"
                onClick={() => nav("/billing")}
                className="mt-3 w-full font-mono text-[10px] tracking-[0.22em] uppercase py-2 rounded-md transition hover:brightness-125"
                style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF99", color: "#00E5FF" }}
              >
                View Full Statement & Pay Now
              </button>
            </Panel>
          </section>

          {/* ===================== ROW 2 ===================== */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 mb-4">
            {/* FINAL REPORTS BOX */}
            <Panel title="Final Reports Box" testid="panel-final-reports">
              {[
                { label: "Moisture Analysis",      pct: 100, status: "READY",     icon: FileText },
                { label: "Structural Integrity",   pct: 100, status: "SUBMITTED", icon: ShieldCheck },
                { label: "Compliance Sign-off",    pct: 100, status: "READY",     icon: Check },
              ].map((r) => {
                const Icon = r.icon;
                return (
                  <div key={r.label} className="py-2">
                    <div className="flex items-center justify-between gap-2">
                      <div className="flex items-center gap-2">
                        <Icon size={14} style={{ color: "#00FF9C" }}/>
                        <span className="font-mono text-[11px] tracking-[0.12em] uppercase text-white">{r.label}</span>
                      </div>
                      <StatusPill text={r.status} color="#00FF9C"/>
                    </div>
                    <div className="mt-1.5"><ProgressBar pct={r.pct}/></div>
                  </div>
                );
              })}
              <div className="mt-3 pt-3 border-t flex items-center justify-between" style={{ borderColor: "rgba(0,229,255,0.18)" }}>
                <span className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-400">Final Adjuster Report</span>
                <button
                  data-testid="cd-open-pdf"
                  onClick={() => nav("/reports/binder")}
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1 rounded-md"
                  style={{ background: "rgba(0,255,156,0.12)", border: "1px solid #00FF9C99", color: "#00FF9C" }}
                >
                  Open Binder →
                </button>
              </div>
              <div className="mt-2 pt-2 border-t flex items-center justify-between" style={{ borderColor: "rgba(212,184,106,0.30)" }}>
                <div>
                  <div className="font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color: "#D4B86A" }}>
                    Property Passport
                  </div>
                  <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500 mt-0.5">
                    Homeowner certificate · Carrier link
                  </div>
                </div>
                <a
                  data-testid="cd-open-passport"
                  href={`/passport/877D9E3C8FC3`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1 rounded-md"
                  style={{ background: "rgba(212,184,106,0.14)", border: "1px solid #D4B86A99", color: "#D4B86A" }}
                >
                  Open Portal →
                </a>
              </div>
            </Panel>

            {/* PROFESSIONAL CREDENTIALS */}
            <Panel title="Professional Credentials" testid="panel-credentials">
              <div className="text-center py-2">
                <div className="font-mono text-[10px] tracking-[0.2em] uppercase text-slate-400">License Level</div>
                <div className="font-display mt-1 tracking-[0.06em]" style={{ fontSize: 20, color: "#FFB020", textShadow: "0 0 10px rgba(255,176,32,0.6)" }}>
                  MASTER
                </div>
                <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-300 mt-1">
                  RESIDENTIAL & COMMERCIAL
                </div>
              </div>
              <div className="flex flex-wrap items-center justify-center gap-2 mt-3">
                {c.certifications.map((cert) => (
                  <span key={cert} className="font-mono text-[9.5px] tracking-[0.18em] uppercase px-3 py-1 rounded-full"
                        style={{ color: "#00E5FF", border: "1px solid #00E5FF66", background: "rgba(0,229,255,0.08)" }}>
                    {cert}
                  </span>
                ))}
              </div>
              <div className="mt-4 pt-3 border-t grid grid-cols-2 gap-3" style={{ borderColor: "rgba(0,229,255,0.18)" }}>
                <div className="text-center">
                  <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-slate-500">Primary Contact</div>
                  <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-white mt-1">{c.primary_contact}</div>
                </div>
                <div className="text-center">
                  <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-slate-500">Title</div>
                  <div className="font-mono text-[11px] tracking-[0.12em] uppercase text-white mt-1">{c.contact_title}</div>
                </div>
              </div>
            </Panel>

            {/* PREFERRED VENDOR NETWORK */}
            <Panel title="Preferred Vendor Network" testid="panel-vendors">
              <div className="flex items-center gap-3 mb-3">
                <div className="flex-1">
                  <div className="font-mono text-[9.5px] tracking-[0.16em] uppercase text-slate-400 mb-1">Network Compliance</div>
                  <ProgressBar pct={95} color="#00FF9C"/>
                </div>
                <span className="font-display" style={{ color: "#00FF9C", fontSize: 22, textShadow: "0 0 10px #00FF9Caa" }}>95%</span>              </div>
              <div className="grid grid-cols-2 gap-2">
                {vendors.map((v) => (
                  <div key={v.name} className="px-2.5 py-1.5 rounded-md flex items-center justify-between gap-2"
                       style={{ background: "rgba(0,229,255,0.05)", border: "1px solid rgba(0,229,255,0.25)" }}>
                    <div className="min-w-0">
                      <div className="font-display text-[11px] tracking-[0.08em] uppercase text-white truncate">{v.name}</div>
                      <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">{v.line}</div>
                    </div>
                    <Check size={12} color="#00FF9C" strokeWidth={3}/>
                  </div>
                ))}
              </div>
            </Panel>
          </section>

          {/* ===================== ROW 3 ===================== */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* PRE-FLIGHT MISSION CRITICAL INTEGRATION GATEWAY */}
            <Panel title="Pre-Flight Mission Critical Integration Gateway" accent="amber" testid="panel-preflight-gateway">
              <CheckLine label="Mobile Trailer Power Supply"      sub="Mobile Trailer Inverter @ 90% Output · [STABLE]"/>
              <CheckLine label="DJI Matrice Battery Integrity"    sub="6× Matrice Batt Pods · [UNLOCKED & READY]"/>
              <CheckLine label="Automated Mechanized Box Hatch"   sub="FAA Matrice Mechanized Box Enclosure · [ACTIVE]"/>
              <div className="mt-3 pt-3 border-t grid grid-cols-2 gap-2"
                   style={{ borderColor: "rgba(255,123,0,0.25)" }}>
                <button
                  data-testid="cd-open-verify"
                  onClick={() => nav("/contractor/verify")}
                  className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-2 py-1.5 rounded-md transition hover:brightness-125"
                  style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF66", color: "#00E5FF" }}>
                  3-Contact Wall →
                </button>
                <button
                  data-testid="cd-open-gm-roster"
                  onClick={() => nav("/gm/roster")}
                  className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-2 py-1.5 rounded-md transition hover:brightness-125"
                  style={{ background: "rgba(255,176,32,0.10)", border: "1px solid #FFB02066", color: "#FFB020" }}>
                  GM Roster →
                </button>
              </div>
            </Panel>

            {/* CLIENT PORTFOLIO */}
            <Panel title="Client Portfolio" accent="gold" testid="panel-clients">
              <div className="grid grid-cols-[1fr_auto_auto_auto] gap-x-3 gap-y-2 font-mono text-[10.5px] tracking-[0.12em] uppercase">
                <span className="text-slate-400">Client Name</span>
                <span className="text-slate-400">Contact</span>
                <span className="text-slate-400 text-center">Active</span>
                <span className="text-slate-400 text-center">Projects</span>
                {clientPortfolio.map((cl) => (
                  <React.Fragment key={cl.name}>
                    <span className="text-white truncate" style={{ textShadow: `0 0 8px ${cl.color}55` }}>{cl.name}</span>
                    <span style={{ color: cl.color }}>{cl.contact}</span>
                    <span className="text-center text-white">{cl.jobs}</span>
                    <span className="text-center" style={{ color: cl.color }}>{cl.projects}</span>
                  </React.Fragment>
                ))}
              </div>
              <div className="mt-3 pt-3 border-t flex items-center justify-between font-mono text-[10px] tracking-[0.18em] uppercase"
                   style={{ borderColor: "rgba(212,184,106,0.25)" }}>
                <span className="text-slate-400">Portfolio Vintage</span>
                <span style={{ color: "#D4B86A" }}>Since 2017</span>
              </div>
            </Panel>

            {/* RIGHT — STACKED: Pre-flight gates + KPIs + Corporate */}
            <div className="flex flex-col gap-4">
              <Panel title="Pre-Flight Gates" accent="green" testid="panel-preflight-gates" className="">
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {[
                    { label: "Mobile Trailer Power", icon: Truck },
                    { label: "Drone Charge",         icon: Battery },
                    { label: "Hatch Deploy",         icon: Plane },
                  ].map((g) => {
                    const Icon = g.icon;
                    return (
                      <div key={g.label} className="flex items-center gap-2 p-2 rounded-md"
                           style={{ background: "rgba(0,255,156,0.06)", border: "1px solid rgba(0,255,156,0.35)" }}>
                        <Icon size={14} color="#00FF9C"/>
                        <span className="font-mono text-[9.5px] tracking-[0.12em] uppercase text-white">{g.label}</span>
                        <Check size={12} color="#00FF9C" strokeWidth={3} className="ml-auto"/>
                      </div>
                    );
                  })}
                </div>
              </Panel>

              <div className="grid grid-cols-2 gap-3">
                {[
                  { k: "TOTAL UNITS",  v: c.metrics.total_units,        color: "#00E5FF", Icon: Boxes },
                  { k: "ACTIVE SCANS", v: c.metrics.active_scans,       color: "#00FF9C", Icon: Cpu },
                  { k: "QUEUED",       v: c.metrics.queued,             color: "#FFB020", Icon: Layers },
                  { k: "ALERTS",       v: c.metrics.alerts,             color: "#FF2D78", Icon: AlertOctagon },
                ].map((m) => (
                  <div key={m.k} data-testid={`kpi-${m.k.toLowerCase().replace(/[^a-z]/g, '')}`}
                       className="px-3 py-2.5 rounded-md flex items-center justify-between"
                       style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${m.color}55`, boxShadow: `inset 0 0 14px ${m.color}10` }}>
                    <div>
                      <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">{m.k}</div>
                      <div className="font-display text-lg" style={{ color: m.color, textShadow: `0 0 10px ${m.color}aa` }}>{m.v}</div>
                    </div>
                    <m.Icon size={20} color={m.color} style={{ filter: `drop-shadow(0 0 6px ${m.color})` }}/>
                  </div>
                ))}
              </div>

              {/* Corporate badge */}
              <div className="rounded-md px-3 py-2 flex items-center justify-between"
                   style={{ background: "rgba(212,184,106,0.06)", border: "1px solid rgba(212,184,106,0.35)" }}>
                <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400">CORPORATE</span>
                <span className="font-display text-[14px] tracking-[0.18em]" style={{ color: "#D4B86A", textShadow: "0 0 10px rgba(212,184,106,0.55)" }}>
                  STRATEX × {c.business_name.split(" ")[0].toUpperCase()}
                </span>
              </div>
            </div>
          </section>

          {/* footer rail · routes back to switchboard */}
          <footer className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-3 pt-4 border-t"
                  style={{ borderColor: "rgba(212,184,106,0.25)" }}>
            <div className="flex items-center gap-3">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" style={{ boxShadow: "0 0 6px #00FF9C" }}/>
              <span className="font-mono text-[9px] tracking-[0.24em] uppercase text-slate-500">
                STRATEX™ · SECURE COMMAND LINK · TENANT {c.business_name.toUpperCase()}
              </span>
            </div>
            <div className="flex items-center gap-3">
              <button
                data-testid="cd-edit-profile"
                onClick={() => nav("/contractor/brand")}
                className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md transition hover:brightness-125"
                style={{ background: "rgba(212,184,106,0.10)", border: "1px solid #D4B86A99", color: "#D4B86A" }}
              >
                Edit Branding
              </button>
              <button
                data-testid="cd-switchboard"
                onClick={() => nav("/switchboard")}
                className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md transition hover:brightness-125"
                style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF99", color: "#00E5FF" }}
              >
                Master Switchboard →
              </button>
            </div>
          </footer>
        </div>
      </div>
    </div>
  );
}
