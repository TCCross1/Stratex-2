/**
 * /ceo/command — BUILD-SUPPLY GM Command Center.
 *
 * Faithful rebuild of the Future-Noire mockup the user supplied. Live data
 * from GET /api/ceo/command-center. Slider-driven pricing preview hits
 * POST /api/ceo/pricing/preview. Password-rotation modal calls
 * POST /api/auth/ceo/request-sms then /api/auth/ceo/change-password.
 *
 * Aesthetic is intentionally its own theme (cyan/purple/green/magenta neon)
 * distinct from the PBR Luxury-Corporate Electric-Teal palette used by the
 * rest of STRATEX — per the user's mockup.
 */
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import ConsensusValidationCore from "@/components/ConsensusValidationCore";
import PricingAuditTimeline from "@/components/PricingAuditTimeline";
import YellowTriangleWidget from "@/components/YellowTriangleWidget";
import {
  AlertTriangle, Activity, Users, TrendingUp, PackageX, Radio,
  Folder, BarChart3, Settings, Briefcase, HelpCircle, MapPin,
  KeyRound, LogOut, Calendar, Plane, Box, Truck, Send, ChevronRight,
  ShieldCheck, Thermometer, Ruler, ListOrdered, Hammer, Layers, Droplets, Wrench,
} from "lucide-react";

const FN = {
  bgMain: "#080c14",
  bgCard: "#0f172a",
  bgInput: "#0b1329",
  cyan: "#06b6d4",
  purple: "#a855f7",
  green: "#10b981",
  magenta: "#f43f5e",
  amber: "#f59e0b",
  text: "#cbd5e1",
  muted: "#64748b",
  divider: "#1e293b",
  ink: "#030712",
};

const USD = (n) =>
  Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function CeoCommandCenter() {
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const [pkt, setPkt] = useState(null);
  const [err, setErr] = useState("");
  const [selectedSku, setSelectedSku] = useState(null);
  const [marginPct, setMarginPct] = useState(45);
  const [preview, setPreview] = useState(null);
  const [showRotate, setShowRotate] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get("/ceo/command-center");
        setPkt(r.data);
        // pick first SKU by default
        if (r.data.catalog?.length) setSelectedSku(r.data.catalog[0].sku);
      } catch (e) {
        const detail = e?.response?.data?.detail;
        setErr(typeof detail === "string" ? detail : "Command Center unavailable");
        if (e?.response?.status === 401 || e?.response?.status === 403) {
          // Not a CEO — bounce back to CEO login
          setTimeout(() => nav("/ceo/login", { replace: true }), 1500);
        }
      }
    })();
  }, [nav]);

  // Recalc adjusted price whenever slider or SKU changes
  useEffect(() => {
    if (!selectedSku) return;
    const t = setTimeout(async () => {
      try {
        const r = await api.post("/ceo/pricing/preview", { sku: selectedSku, margin_pct: marginPct });
        setPreview(r.data);
      } catch { /* silent — slider keeps moving */ }
    }, 120);
    return () => clearTimeout(t);
  }, [selectedSku, marginPct]);

  // Auto-prompt password rotation on first command-center load
  useEffect(() => {
    if (user?.must_rotate_password) setShowRotate(true);
  }, [user]);

  const selectedCatalog = useMemo(
    () => pkt?.catalog?.find((c) => c.sku === selectedSku),
    [pkt, selectedSku],
  );

  if (err && !pkt) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4" style={{ background: FN.bgMain, color: FN.text }}>
        <FutureNoireGlobals/>
        <div className="border max-w-md p-6" style={{ borderColor: FN.magenta, background: "rgba(244,63,94,0.06)" }}>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: FN.magenta }}>// CLEARANCE DENIED</div>
          <p className="text-[13px]">{err}</p>
          <p className="text-[11px] mt-2" style={{ color: FN.muted }}>Redirecting to CEO sign-in…</p>
        </div>
      </div>
    );
  }
  if (!pkt) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: FN.bgMain }}>
        <FutureNoireGlobals/>
        <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: FN.green }}>// SYNCING COMMAND FEED…</div>
      </div>
    );
  }

  return (
    <div className="app-container" data-testid="ceo-cc-root" style={{ background: FN.bgMain, color: FN.text }}>
      <FutureNoireGlobals/>

      {/* HEADER */}
      <header className="ceo-header">
        <div>
          <h1>BUILD-SUPPLY · GM COMMAND CENTER</h1>
          <p className="ceo-sub">{pkt.region.toUpperCase()} REGION · LOCALIZED MATERIAL LOGISTICS &amp; STRATEX CLIENT YIELDS</p>
        </div>
        <div className="ceo-header-right">
          <YellowTriangleWidget portal="ceo"/>
          <span className="ceo-pulse"><span className="ceo-pulse-dot"/> STX LINK SECURE</span>
          <button onClick={() => setShowRotate(true)} data-testid="ceo-rotate-btn"
            className="ceo-pill" style={{ borderColor: FN.amber, color: FN.amber }}>
            <KeyRound size={11}/> Rotate Pass
          </button>
          <button onClick={() => { logout?.(); nav("/ceo/login", { replace: true }); }} data-testid="ceo-logout"
            className="ceo-pill" style={{ borderColor: FN.magenta, color: FN.magenta }}>
            <LogOut size={11}/> Sign Out
          </button>
        </div>
      </header>

      {/* SIDEBAR */}
      <nav className="ceo-sidebar">
        {[
          { Icon: Folder, label: "Rolodex", active: true },
          { Icon: AlertTriangle, label: "Warning", badge: pkt.kpis.critical_stockouts },
          { Icon: BarChart3, label: "Sales" },
          { Icon: Briefcase, label: "Assets" },
          { Icon: Settings, label: "Settings" },
          { Icon: HelpCircle, label: "Help" },
        ].map(({ Icon, label, active, badge }) => (
          <div key={label} className={`ceo-nav-btn ${active ? "active" : ""}`}>
            <div className="ceo-nav-icon-wrap">
              <Icon size={16}/>
              {badge ? <span className="ceo-nav-badge">{badge}</span> : null}
            </div>
            <span>{label}</span>
          </div>
        ))}
      </nav>

      {/* MAIN GRID */}
      <main className="ceo-main">
        {/* KPI ROW */}
        <section className="ceo-kpi-grid" data-testid="ceo-kpi-row">
          <KpiCard accent={FN.cyan}    Icon={Box}     title="Total Regional Scans" value={pkt.kpis.total_regional_scans}/>
          <KpiCard accent={FN.purple}  Icon={Plane}   title="Local Scans Scheduled" value={pkt.kpis.scans_scheduled}/>
          <KpiCard accent={FN.purple}  Icon={Users}   title="Active Contractor Profiles" value={pkt.kpis.active_contractors}/>
          <KpiCard accent={FN.green}   Icon={TrendingUp} title="Regional Gross Revenue (Month)" value={USD(pkt.kpis.monthly_gross_revenue_usd)}/>
          <KpiCard accent={FN.magenta} Icon={PackageX} title="Critical Stock-Outs" value={`${pkt.kpis.critical_stockouts} Alerts`}/>
        </section>

        {/* MIDDLE: ROI Matrix + Map */}
        <section className="ceo-mesh">
          <div className="ceo-card" data-testid="ceo-roi-matrix" style={{ borderLeft: `4px solid ${FN.cyan}` }}>
            <h3 className="ceo-card-title" style={{ color: FN.cyan }}>STRATEX Investment Return Matrix</h3>
            <p className="ceo-card-sub">Contractor scan portfolio · Lexington Metro mesh · global price-lock active</p>
            <table className="ceo-table">
              <thead>
                <tr>
                  <th>Client</th>
                  <th className="ceo-r">Scan Cost</th>
                  <th className="ceo-r">Gain</th>
                  <th className="ceo-r">ROI</th>
                </tr>
              </thead>
              <tbody>
                {(pkt.roi_matrix || []).slice(0, 4).map((row, i) => (
                  <tr key={i}>
                    <td>{row.client}</td>
                    <td className="ceo-r" style={{ color: FN.purple }} data-testid={`ceo-scan-cost-${i}`}>
                      {pkt.price_lock?.scan_cost_label || `$${row.scan_cost_usd} / Scan`}
                    </td>
                    <td className="ceo-r" style={{ color: FN.green }}>{USD(row.gain_usd)}</td>
                    <td className="ceo-r ceo-mono" style={{ color: FN.amber }}>{row.roi_multiple}x</td>
                  </tr>
                ))}
                {!pkt.roi_matrix?.length && (
                  <tr><td colSpan={4} className="ceo-empty">No completed scans yet · pipeline pending</td></tr>
                )}
              </tbody>
            </table>
            <div className="ceo-license-strip" data-testid="ceo-license-strip">
              {pkt.price_lock?.license_label || "MONTHLY LICENSE FEE: $1,500 / Location"}
            </div>
          </div>

          <div className="ceo-card ceo-map-tile" data-testid="ceo-map">
            <div className="ceo-map-grid"/>
            <div className="ceo-map-blip" style={{ top: "30%", left: "40%", "--c": FN.cyan }}/>
            <div className="ceo-map-blip" style={{ top: "55%", left: "60%", "--c": FN.green }}/>
            <div className="ceo-map-blip" style={{ top: "42%", left: "72%", "--c": FN.amber }}/>
            <div className="ceo-map-inner">
              <Radio size={32} color={FN.cyan}/>
              <span className="ceo-map-title">Central KY Doppler Tracking Mesh · Fleet Active</span>
              <span className="ceo-map-sub">
                <MapPin size={10}/> Lexington Metro · Localized Operational Mesh
              </span>
              <div className="ceo-map-legend">
                <span><i style={{ background: FN.cyan }}/> Drone Active</span>
                <span><i style={{ background: FN.green }}/> Capture Done</span>
                <span><i style={{ background: FN.amber }}/> Storm Cell</span>
              </div>
            </div>
          </div>
        </section>

        {/* OPEN JOBS + CALENDAR */}
        <section className="ceo-mesh-3">
          <div className="ceo-card" data-testid="ceo-open-jobs" style={{ borderLeft: `4px solid ${FN.purple}` }}>
            <h3 className="ceo-card-title" style={{ color: FN.purple }}>Open Jobs · Pending Closures</h3>
            <table className="ceo-table">
              <thead>
                <tr>
                  <th>Job #</th>
                  <th>Address</th>
                  <th className="ceo-r">Gain</th>
                  <th className="ceo-r">ROI</th>
                </tr>
              </thead>
              <tbody>
                {(pkt.open_jobs || []).slice(0, 5).map((j) => (
                  <tr key={j.job_id}>
                    <td className="ceo-mono">{j.project_code}</td>
                    <td className="ceo-truncate">{j.address}</td>
                    <td className="ceo-r" style={{ color: FN.green }}>{USD(j.gain_usd)}</td>
                    <td className="ceo-r ceo-mono" style={{ color: FN.amber }}>{j.roi_multiple}x</td>
                  </tr>
                ))}
                {!pkt.open_jobs?.length && (
                  <tr><td colSpan={4} className="ceo-empty">No open jobs · queue clear</td></tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="ceo-card" data-testid="ceo-calendar" style={{ borderLeft: `4px solid ${FN.cyan}` }}>
            <h3 className="ceo-card-title" style={{ color: FN.cyan }}><Calendar size={12}/> Predictive Flight Calendar · 7-Day</h3>
            <div className="ceo-cal-grid">
              {(pkt.calendar || []).map((d, i) => (
                <div key={d.date} className={`ceo-cal-cell ${i === 0 ? "today" : ""}`}>
                  <div className="ceo-cal-day">{d.label.split(" ")[0]}</div>
                  <div className="ceo-cal-date">{d.label.split(" ").slice(1).join(" ")}</div>
                  <div className="ceo-cal-stats">
                    <span style={{ color: FN.cyan }}>{d.scans}<small> scans</small></span>
                    {d.value_usd > 0 && <span style={{ color: FN.green }}>{USD(d.value_usd)}</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="ceo-card" data-testid="ceo-mission" style={{ borderLeft: `4px solid ${FN.green}` }}>
            <h3 className="ceo-card-title" style={{ color: FN.green }}>KY-SUPPLY-01 · Mission Status</h3>
            <div className="ceo-mission-body">
              <div className="ceo-mission-meta">
                <div className="ceo-mono" style={{ fontSize: 11, color: FN.muted }}>LIVE SITE</div>
                <div className="ceo-mono" style={{ fontSize: 14, color: FN.text, fontWeight: 700 }}>KY-SUPPLY-01</div>
                <div className="ceo-mono" style={{ fontSize: 9, color: FN.muted, marginTop: 6 }}>PHASE</div>
                <div className="ceo-mono" style={{ fontSize: 12, color: FN.green }}>04 · IN FLIGHT</div>
              </div>
              <div className="ceo-mission-progress">
                {[1, 2, 3, 4, 5, 6, 7].map((p) => (
                  <div key={p} className="ceo-progress-segment"
                       style={{ background: p <= 4 ? FN.green : FN.divider,
                                boxShadow: p === 4 ? `0 0 8px ${FN.green}` : "none" }}/>
                ))}
              </div>
              <div className="ceo-mission-foot">
                <span><Plane size={10}/> +1 Drone</span>
                <span><Activity size={10}/> Telemetry OK</span>
              </div>
            </div>
          </div>
        </section>

        {/* NEW ROW · CONSENSUS AI VALIDATION CORE + VINYL SIDING / GUTTERS BLUEPRINTS */}
        <section className="ceo-mesh" data-testid="ceo-row-consensus-blueprint">
          <ConsensusValidationCard consensus={pkt.consensus}/>
          <BlueprintsCard blueprint={pkt.blueprint}/>
        </section>

        {/* LIVE 4-AGENT CONSENSUS CORE — pure addition wired to /api/ceo/consensus/* */}
        <section data-testid="ceo-row-consensus-live" style={{ marginTop: 16 }}>
          <ConsensusValidationCore token={typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null}/>
        </section>

        {/* PRICING SLIDER WIDGET */}
        <section className="ceo-card ceo-pricing" data-testid="ceo-pricing" style={{ borderLeft: `4px solid ${FN.purple}` }}>
          <div className="ceo-pricing-cols">
            <div>
              <label className="ceo-label">Item / Auto Landed Base Cost</label>
              <select value={selectedSku || ""} onChange={(e) => setSelectedSku(e.target.value)}
                      className="ceo-select" data-testid="ceo-sku-select">
                {(pkt.catalog || []).map((c) => (
                  <option key={c.sku} value={c.sku}>{c.name}</option>
                ))}
              </select>
              <span className="ceo-mono" style={{ color: FN.purple, fontSize: 12 }}>
                {USD(selectedCatalog?.tier_1_price_usd)} Base / {selectedCatalog?.unit_label}
              </span>
            </div>
            <div className="ceo-slider-col">
              <input type="range" min="-100" max="200" value={marginPct}
                     onChange={(e) => setMarginPct(parseFloat(e.target.value))}
                     className="ceo-slider"
                     data-testid="ceo-margin-slider"
                     style={{ accentColor: FN.purple }}/>
              <div className="ceo-mono" style={{ color: FN.purple, fontSize: 11, fontWeight: 700, marginTop: 6 }}>
                {marginPct >= 0 ? "+" : ""}{marginPct}% Adjustment
              </div>
            </div>
            <div className="ceo-price-readout">
              <label className="ceo-label">Resulting Adjusted Price</label>
              <div className="ceo-price-value" data-testid="ceo-adjusted-price">
                {preview ? `$${preview.adjusted_usd.toFixed(2)}` : "—"}
              </div>
            </div>
          </div>
        </section>

        {/* PRICING AUDIT LEDGER — v3.37.0 append-only timeline view.
            Does not alter telemetry cards, KY Doppler map, or return matrices. */}
        <PricingAuditTimeline FN={FN}/>
      </main>

      {/* BOTTOM DOCK */}
      <footer className="ceo-dock">
        <button onClick={() => nav("/ceo/leads")}
                className="ceo-dock-btn" data-testid="dock-leads"
                style={{ borderColor: FN.cyan, color: FN.cyan }}>
          <Users size={12}/> New Clients / Sales
        </button>
        <button onClick={() => nav("/ceo/orders/build")}
                className="ceo-dock-btn" data-testid="dock-build"
                style={{ borderColor: FN.purple, color: FN.purple }}>
          <Box size={12}/> Orders to Build
        </button>
        <button onClick={() => nav("/ceo/orders/ready")}
                className="ceo-dock-btn" data-testid="dock-ready"
                style={{ borderColor: FN.cyan, color: FN.cyan }}>
          <Truck size={12}/> Orders Ready
        </button>
        <button onClick={() => nav("/ceo/orders/shipped")}
                className="ceo-dock-btn" data-testid="dock-shipped"
                style={{ borderColor: FN.purple, color: FN.purple }}>
          <Send size={12}/> Orders Shipped
        </button>
        <button onClick={() => nav("/ceo/inventory")}
                className="ceo-dock-btn" data-testid="dock-inventory"
                style={{ borderColor: FN.green, color: FN.green }}>
          <Briefcase size={12}/> Complete Inventory Cost <ChevronRight size={12}/>
        </button>
        <button onClick={() => nav("/ceo/live-map")}
                className="ceo-dock-btn" data-testid="dock-live-theater"
                style={{ borderColor: FN.cyan, color: FN.cyan }}>
          <Plane size={12}/> Live Theater · Fleet Tracking <ChevronRight size={12}/>
        </button>
        <button onClick={() => nav("/ceo/regional")}
                className="ceo-dock-btn" data-testid="dock-regional"
                style={{ borderColor: FN.purple, color: FN.purple }}>
          <Box size={12}/> Regional Switchboard · National Rollup <ChevronRight size={12}/>
        </button>
      </footer>

      {showRotate && (
        <RotatePasswordModal phoneLast4={pkt.ceo?.phone_last4 || ""} onClose={() => setShowRotate(false)}/>
      )}
    </div>
  );
}

/* =====================================================================
   COMPONENTS
   ===================================================================== */

function KpiCard({ Icon, title, value, accent }) {
  return (
    <div className="ceo-card ceo-kpi" data-testid={`ceo-kpi-${title.toLowerCase().replace(/\s+/g, "-")}`}
         style={{ borderLeft: `4px solid ${accent}` }}>
      <div className="ceo-kpi-head">
        <span>{title}</span>
        <Icon size={14} color={accent}/>
      </div>
      <div className="ceo-kpi-value">{value}</div>
    </div>
  );
}

/* ----- Consensus AI Validation Core ----- */
const VALIDATOR_ICONS = {
  "Geometry · Mesh": Ruler,
  "Thermal · Radiometric": Thermometer,
  "Quantity Estimator": ListOrdered,
};

function ConsensusValidationCard({ consensus }) {
  if (!consensus) return null;
  const okay = consensus.state === "CONSENSUS_OK";
  const headerColor = okay ? FN.green : FN.magenta;
  const tolerance = consensus.tolerance_pct;
  const maxObs = consensus.max_observed_pct;
  return (
    <div className="ceo-card" data-testid="ceo-consensus-card"
         style={{ borderLeft: `4px solid ${headerColor}` }}>
      <div className="flex items-center justify-between">
        <h3 className="ceo-card-title" style={{ color: headerColor, marginBottom: 4 }}>
          <ShieldCheck size={13}/> Multi-Agent Consensus AI Validation Core
        </h3>
        <span className="ceo-pill" data-testid="ceo-consensus-state"
              style={{ borderColor: headerColor, color: headerColor, padding: "4px 9px", fontSize: 8.5 }}>
          {okay ? "● CONSENSUS_OK" : "△ VECTOR_RESCAN HOLD"}
        </span>
      </div>
      <p className="ceo-card-sub" style={{ marginBottom: 14 }}>
        Triple cross-audit · Δ tolerance ≤ {tolerance.toFixed(2)}% · current max drift {maxObs.toFixed(4)}%
        {consensus.drone_lock_engaged && " · drone HOLD engaged"}
      </p>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {(consensus.validators || []).map((v, i) => {
          const Icon = VALIDATOR_ICONS[v.agent] || ShieldCheck;
          const drift = Number(v.last_variance_pct || 0);
          const pctOfTolerance = Math.min(100, (drift / tolerance) * 100);
          const fillColor = drift <= tolerance ? FN.green : FN.magenta;
          return (
            <div key={i} className="ceo-validator-row" data-testid={`ceo-validator-${i}`}>
              <div className="ceo-validator-head">
                <span className="ceo-validator-icon" style={{ background: `${fillColor}14`, border: `1px solid ${fillColor}55` }}>
                  <Icon size={13} color={fillColor}/>
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="ceo-validator-name">{v.agent}</div>
                  <div className="ceo-validator-domain">{v.domain}</div>
                </div>
                <span className="ceo-validator-pct" style={{ color: fillColor }}>
                  Δ {drift.toFixed(4)}%
                </span>
              </div>
              <div className="ceo-validator-bar">
                <div style={{
                  width: `${pctOfTolerance}%`, background: fillColor,
                  height: "100%", borderRadius: 2, transition: "width 0.4s",
                  boxShadow: `0 0 6px ${fillColor}`,
                }}/>
              </div>
            </div>
          );
        })}
      </div>

      <div className="ceo-consensus-foot">
        <Activity size={9}/> Zero human intervention · cross-audit cadence locked to every drone frame
      </div>
    </div>
  );
}

/* ----- Vinyl Siding / Gutters Multi-Trade Blueprint ----- */
const PHASE_META = {
  framing: { label: "Framing", Icon: Wrench,   accent: FN.purple  },
  roofing: { label: "Roofing", Icon: Hammer,   accent: FN.amber   },
  gutters: { label: "Gutters", Icon: Droplets, accent: FN.cyan    },
  siding:  { label: "Vinyl Siding", Icon: Layers, accent: "#B8865B" },
};

function BlueprintsCard({ blueprint }) {
  if (!blueprint) return null;
  const phases = blueprint.phases || {};
  const grandTotal = blueprint.totals?.phase_total_usd || 0;
  return (
    <div className="ceo-card" data-testid="ceo-blueprint-card"
         style={{ borderLeft: `4px solid ${FN.amber}` }}>
      <div className="flex items-center justify-between">
        <h3 className="ceo-card-title" style={{ color: FN.amber, marginBottom: 4 }}>
          <Hammer size={13}/> Vinyl Siding / Gutters Blueprints
        </h3>
        <span className="ceo-pill" style={{ borderColor: FN.amber, color: FN.amber, padding: "4px 9px", fontSize: 8.5 }}
              data-testid="ceo-blueprint-source">
          {blueprint.project_code || "—"}
        </span>
      </div>
      <p className="ceo-card-sub" style={{ marginBottom: 12 }}>
        Multi-trade snip · drone-modeled · {blueprint.site || "—"}
        {blueprint.roof_sqft ? ` · ${blueprint.roof_sqft.toLocaleString()} ft² roof footprint` : ""}
      </p>

      <div className="ceo-blueprint-rows">
        {["framing", "roofing", "gutters", "siding"].filter((k) => phases[k]).map((k) => {
          const meta = PHASE_META[k];
          const ph = phases[k];
          const pct = grandTotal > 0 ? (Number(ph.total_price_usd || 0) / grandTotal) * 100 : 0;
          return (
            <div key={k} className="ceo-blueprint-row" data-testid={`ceo-blueprint-${k}`}>
              <span className="ceo-blueprint-icon"
                    style={{ background: `${meta.accent}14`, border: `1px solid ${meta.accent}55` }}>
                <meta.Icon size={13} color={meta.accent}/>
              </span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="ceo-blueprint-label" style={{ color: FN.text }}>
                  {meta.label}
                </div>
                <div className="ceo-blueprint-scope">{ph.scope}</div>
                <div className="ceo-blueprint-bar">
                  <div style={{ width: `${pct}%`, background: meta.accent, height: "100%", borderRadius: 1 }}/>
                </div>
              </div>
              <div className="ceo-blueprint-num">
                <div className="ceo-mono" style={{ fontSize: 12, color: meta.accent, fontWeight: 700 }}>
                  {USD(ph.total_price_usd)}
                </div>
                <div className="ceo-mono" style={{ fontSize: 8.5, color: FN.muted, marginTop: 1 }}>
                  {ph.estimated_man_hours} mh · {(pct).toFixed(1)}%
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="ceo-blueprint-foot">
        <span className="ceo-mono">{blueprint.totals?.combined_man_hours || 0} combined man-hours</span>
        <span className="ceo-mono" style={{ color: FN.green, fontWeight: 700 }}>{USD(grandTotal)} phase total</span>
      </div>
    </div>
  );
}

function RotatePasswordModal({ phoneLast4, onClose }) {
  const [stage, setStage] = useState("init"); // init | code | success
  const [code, setCode] = useState("");
  const [debugCode, setDebugCode] = useState("");
  const [newPass, setNewPass] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const requestSms = async () => {
    setErr(""); setBusy(true);
    try {
      const r = await api.post("/auth/ceo/request-sms", {});
      setStage("code");
      if (r.data.debug_code) setDebugCode(r.data.debug_code);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to send SMS");
    } finally { setBusy(false); }
  };

  const commit = async () => {
    setErr(""); setBusy(true);
    try {
      await api.post("/auth/ceo/change-password", { sms_code: code, new_password: newPass });
      setStage("success");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Failed to change password");
    } finally { setBusy(false); }
  };

  return (
    <div className="ceo-modal-overlay" onClick={onClose} data-testid="ceo-rotate-modal">
      <div className="ceo-modal" onClick={(e) => e.stopPropagation()}>
        <div className="font-mono text-[10px] tracking-[0.35em] uppercase mb-2" style={{ color: FN.amber }}>
          // PASSPHRASE ROTATION
        </div>
        <h2 className="text-[18px] font-bold mb-3" style={{ color: FN.text }}>Change CEO Passphrase</h2>

        {stage === "init" && (
          <>
            <p className="text-[12px] mb-4" style={{ color: FN.muted }}>
              A 6-digit code will be sent via SMS to the phone ending in <strong style={{ color: FN.text }}>•••• {phoneLast4}</strong>.
            </p>
            <button onClick={requestSms} disabled={busy} data-testid="ceo-send-sms"
              className="ceo-pill-solid" style={{ background: FN.amber, color: FN.ink }}>
              {busy ? "Sending…" : "Send Verification Code"}
            </button>
          </>
        )}

        {stage === "code" && (
          <>
            <label className="ceo-label">SMS Code</label>
            <input value={code} onChange={(e) => setCode(e.target.value)} maxLength={6}
                   placeholder="6 digits" className="ceo-input-modal" data-testid="ceo-sms-input"
                   autoComplete="one-time-code"/>
            {debugCode && (
              <div className="text-[10px] font-mono mt-1 mb-3" style={{ color: FN.amber }}>
                // DEV BYPASS · code = {debugCode}
              </div>
            )}
            <label className="ceo-label">New Passphrase</label>
            <input type="password" value={newPass} onChange={(e) => setNewPass(e.target.value)}
                   placeholder="min 4 chars" className="ceo-input-modal" data-testid="ceo-newpass-input"/>
            <button onClick={commit} disabled={busy || code.length !== 6 || newPass.length < 4}
              data-testid="ceo-commit-pw"
              className="ceo-pill-solid mt-4" style={{ background: FN.green, color: FN.ink }}>
              {busy ? "Rotating…" : "Commit New Passphrase"}
            </button>
          </>
        )}

        {stage === "success" && (
          <>
            <p className="text-[12px] mb-4" style={{ color: FN.green }}>Passphrase updated.</p>
            <button onClick={onClose} className="ceo-pill-solid" style={{ background: FN.green, color: FN.ink }}>Close</button>
          </>
        )}

        {err && <p className="text-[11px] mt-3" style={{ color: FN.magenta }}>{err}</p>}
        <button onClick={onClose} data-testid="ceo-rotate-close"
          className="absolute top-2 right-3 font-mono text-[12px]" style={{ color: FN.muted }}>×</button>
      </div>
    </div>
  );
}

/* =====================================================================
   GLOBAL STYLES (scoped via class names — never leaks to other pages)
   ===================================================================== */

function FutureNoireGlobals() {
  return (
    <style>{`
      .app-container {
        display: grid;
        width: 100%;
        min-height: 100vh;
        grid-template-columns: 80px 1fr;
        grid-template-rows: auto 1fr auto;
        grid-template-areas:
          "header header"
          "sidebar main"
          "footer footer";
      }
      .ceo-header {
        grid-area: header;
        background: linear-gradient(135deg, ${FN.ink} 0%, ${FN.bgCard} 100%);
        border-bottom: 3px solid ${FN.green};
        padding: 14px 22px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 14px;
      }
      .ceo-header h1 {
        color: ${FN.green};
        font-size: 15px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 0 0 10px rgba(16,185,129,0.35);
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-sub {
        font-size: 10px;
        color: ${FN.muted};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 3px;
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-header-right { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
      .ceo-pulse {
        font-size: 9px;
        color: ${FN.cyan};
        font-family: 'JetBrains Mono', monospace;
        letter-spacing: 0.3em;
        text-transform: uppercase;
        display: inline-flex; align-items: center; gap: 6px;
      }
      .ceo-pulse-dot {
        width: 6px; height: 6px; border-radius: 50%; background: ${FN.cyan};
        box-shadow: 0 0 8px ${FN.cyan};
        animation: ceoPulse 2s infinite;
      }
      @keyframes ceoPulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
      .ceo-pill {
        background: transparent; border: 1px solid; padding: 6px 12px; border-radius: 2px;
        font-family: 'JetBrains Mono', monospace; font-size: 9px; letter-spacing: 0.25em;
        text-transform: uppercase; font-weight: 700; cursor: pointer;
        display: inline-flex; align-items: center; gap: 6px;
        transition: all 0.2s;
      }
      .ceo-pill:hover { transform: translateY(-1px); }

      .ceo-sidebar {
        grid-area: sidebar;
        background: ${FN.ink};
        border-right: 1px solid ${FN.divider};
        display: flex; flex-direction: column; align-items: center;
        padding: 18px 0; gap: 18px;
      }
      .ceo-nav-btn {
        width: 56px; padding: 8px 4px; border-radius: 4px;
        border: 1px solid ${FN.divider}; background: ${FN.bgCard};
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        cursor: pointer; color: ${FN.muted};
        transition: all 0.2s ease;
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-nav-btn.active {
        border-color: ${FN.cyan}; color: ${FN.cyan};
        box-shadow: 0 0 10px rgba(6,182,212,0.25);
      }
      .ceo-nav-btn:hover { border-color: ${FN.cyan}99; color: ${FN.cyan}; }
      .ceo-nav-icon-wrap { position: relative; }
      .ceo-nav-badge {
        position: absolute; top: -6px; right: -8px;
        background: ${FN.magenta}; color: white;
        font-size: 8px; font-weight: 700;
        width: 14px; height: 14px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 6px ${FN.magenta};
      }
      .ceo-nav-btn span { font-size: 7.5px; text-transform: uppercase; margin-top: 4px; letter-spacing: 0.05em; }

      .ceo-main {
        grid-area: main; padding: 18px 22px; overflow-y: auto;
        display: flex; flex-direction: column; gap: 18px;
      }
      .ceo-kpi-grid {
        display: grid; grid-template-columns: repeat(5, 1fr); gap: 12px;
      }
      .ceo-mesh {
        display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px;
      }
      .ceo-mesh-3 {
        display: grid; grid-template-columns: 1.1fr 1.4fr 1fr; gap: 16px;
      }

      .ceo-card {
        background: ${FN.bgCard};
        border: 1px solid ${FN.divider};
        padding: 16px 18px;
        border-radius: 4px;
        position: relative;
      }

      .ceo-kpi { padding: 14px 16px; min-height: 92px; }
      .ceo-kpi-head {
        display: flex; justify-content: space-between; align-items: center;
        font-size: 8.5px; color: ${FN.muted};
        text-transform: uppercase; letter-spacing: 0.5px;
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-kpi-value { font-size: 22px; font-weight: 800; color: #fff; margin-top: 8px; }

      .ceo-card-title {
        font-size: 11px; margin-bottom: 12px;
        text-transform: uppercase; letter-spacing: 1.5px;
        font-weight: 700;
        font-family: 'JetBrains Mono', monospace;
        display: inline-flex; align-items: center; gap: 6px;
      }
      .ceo-card-sub { font-size: 10px; color: ${FN.muted}; margin-bottom: 10px; }

      .ceo-table { width: 100%; border-collapse: collapse; font-size: 11px; }
      .ceo-table th {
        font-size: 9px; text-transform: uppercase; letter-spacing: 0.2em;
        color: ${FN.muted}; text-align: left; padding: 6px 4px;
        border-bottom: 1px solid ${FN.divider};
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-table td { padding: 6px 4px; border-bottom: 1px solid ${FN.divider}; color: ${FN.text}; }
      .ceo-table tr:last-child td { border-bottom: 0; }
      .ceo-r { text-align: right; }
      .ceo-mono { font-family: 'JetBrains Mono', monospace; }
      .ceo-empty { text-align: center; color: ${FN.muted}; padding: 14px 0; font-style: italic; }
      .ceo-truncate { max-width: 180px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .ceo-license-strip {
        margin-top: 10px; padding: 8px 10px;
        background: rgba(16,185,129,0.07);
        border: 1px solid rgba(16,185,129,0.3);
        color: ${FN.green}; font-size: 10px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.15em;
        font-family: 'JetBrains Mono', monospace;
      }

      /* Map */
      .ceo-map-tile {
        min-height: 240px;
        background: radial-gradient(ellipse at center, #0f1c3f 0%, ${FN.bgMain} 100%);
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        text-align: center; overflow: hidden;
      }
      .ceo-map-grid {
        position: absolute; inset: 0;
        background-image: linear-gradient(${FN.cyan}11 1px, transparent 1px),
                          linear-gradient(90deg, ${FN.cyan}11 1px, transparent 1px);
        background-size: 28px 28px;
        opacity: 0.55;
      }
      .ceo-map-inner { position: relative; z-index: 2; display: flex; flex-direction: column; align-items: center; gap: 6px; }
      .ceo-map-title { color: ${FN.cyan}; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.2em; font-family: 'JetBrains Mono', monospace; }
      .ceo-map-sub { display: inline-flex; align-items: center; gap: 4px; font-size: 9.5px; color: ${FN.muted}; font-family: 'JetBrains Mono', monospace; }
      .ceo-map-legend { display: flex; gap: 12px; margin-top: 14px; font-size: 9px; color: ${FN.muted}; font-family: 'JetBrains Mono', monospace; }
      .ceo-map-legend span { display: inline-flex; align-items: center; gap: 4px; }
      .ceo-map-legend i { display: inline-block; width: 8px; height: 8px; border-radius: 50%; box-shadow: 0 0 6px currentColor; }
      .ceo-map-blip {
        position: absolute; width: 10px; height: 10px; border-radius: 50%;
        background: var(--c); box-shadow: 0 0 10px var(--c);
        animation: ceoBlip 1.6s infinite ease-out;
      }
      @keyframes ceoBlip { 0% { transform: scale(0.7); opacity: 1;} 100% { transform: scale(2); opacity: 0;} }

      /* Calendar */
      .ceo-cal-grid {
        display: grid; grid-template-columns: repeat(7, 1fr); gap: 4px;
      }
      .ceo-cal-cell {
        background: ${FN.bgInput}; border: 1px solid ${FN.divider};
        padding: 8px 6px; border-radius: 2px; text-align: center;
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-cal-cell.today { border-color: ${FN.green}; box-shadow: inset 0 0 0 1px ${FN.green}55; }
      .ceo-cal-day { font-size: 8.5px; color: ${FN.muted}; text-transform: uppercase; }
      .ceo-cal-date { font-size: 11px; color: ${FN.text}; font-weight: 700; margin-top: 2px; }
      .ceo-cal-stats { display: flex; flex-direction: column; gap: 1px; margin-top: 4px; font-size: 8.5px; }
      .ceo-cal-stats small { font-size: 7.5px; color: ${FN.muted}; }

      /* Mission */
      .ceo-mission-body { display: flex; flex-direction: column; gap: 10px; }
      .ceo-mission-meta { font-family: 'JetBrains Mono', monospace; }
      .ceo-mission-progress { display: flex; gap: 3px; }
      .ceo-progress-segment { flex: 1; height: 6px; border-radius: 1px; }
      .ceo-mission-foot {
        display: flex; gap: 12px; font-size: 9.5px; color: ${FN.muted};
        font-family: 'JetBrains Mono', monospace; text-transform: uppercase;
      }
      .ceo-mission-foot span { display: inline-flex; align-items: center; gap: 4px; }

      /* Pricing slider */
      .ceo-pricing { border-left-color: ${FN.purple}; }
      .ceo-pricing-cols {
        display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 20px; align-items: center;
      }
      .ceo-label {
        display: block; font-size: 8.5px; color: ${FN.muted};
        text-transform: uppercase; letter-spacing: 0.3em;
        margin-bottom: 4px;
        font-family: 'JetBrains Mono', monospace;
      }
      .ceo-select {
        width: 100%; background: ${FN.bgInput}; border: 1px solid ${FN.divider};
        color: ${FN.text}; padding: 6px 8px; font-size: 11px; border-radius: 2px;
        font-weight: 700; margin-bottom: 4px;
      }
      .ceo-slider-col { text-align: center; }
      .ceo-slider {
        width: 100%; cursor: pointer; height: 6px; appearance: none;
        background: linear-gradient(90deg, ${FN.magenta} 0%, ${FN.amber} 33%, ${FN.green} 66%, ${FN.cyan} 100%);
        border-radius: 3px; outline: none;
      }
      .ceo-price-readout { text-align: right; }
      .ceo-price-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px; font-weight: 800; color: ${FN.green};
        text-shadow: 0 0 12px rgba(16,185,129,0.35);
      }

      /* Bottom dock */
      .ceo-dock {
        grid-area: footer;
        background: ${FN.ink};
        border-top: 1px solid ${FN.divider};
        padding: 12px 22px;
        display: flex; justify-content: flex-end; gap: 12px; flex-wrap: wrap;
      }

      /* Consensus validator card */
      .ceo-validator-row {
        background: ${FN.bgInput};
        border: 1px solid ${FN.divider};
        border-radius: 3px;
        padding: 10px 12px;
      }
      .ceo-validator-head { display: flex; align-items: center; gap: 10px; }
      .ceo-validator-icon {
        width: 28px; height: 28px; border-radius: 3px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }
      .ceo-validator-name {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: ${FN.text}; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
      }
      .ceo-validator-domain {
        font-size: 9.5px; color: ${FN.muted};
        line-height: 1.3; margin-top: 1px;
      }
      .ceo-validator-pct {
        font-family: 'JetBrains Mono', monospace;
        font-size: 10.5px; font-weight: 700;
        letter-spacing: 0.05em; flex-shrink: 0;
      }
      .ceo-validator-bar {
        height: 4px; background: ${FN.divider}; border-radius: 2px;
        margin-top: 8px; overflow: hidden;
      }
      .ceo-consensus-foot {
        margin-top: 14px; padding-top: 10px;
        border-top: 1px solid ${FN.divider};
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px; color: ${FN.muted};
        text-transform: uppercase; letter-spacing: 0.2em;
        display: flex; align-items: center; gap: 6px;
      }

      /* Blueprint card */
      .ceo-blueprint-rows { display: flex; flex-direction: column; gap: 8px; }
      .ceo-blueprint-row {
        display: flex; align-items: center; gap: 10px;
        background: ${FN.bgInput}; border: 1px solid ${FN.divider};
        padding: 8px 10px; border-radius: 3px;
      }
      .ceo-blueprint-icon {
        width: 30px; height: 30px; border-radius: 3px;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0;
      }
      .ceo-blueprint-label {
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; font-weight: 700;
        text-transform: uppercase; letter-spacing: 0.1em;
      }
      .ceo-blueprint-scope {
        font-size: 10px; color: ${FN.muted};
        margin-top: 2px;
        overflow: hidden; text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        line-height: 1.3;
      }
      .ceo-blueprint-bar {
        height: 3px; background: ${FN.divider}; border-radius: 2px;
        margin-top: 5px; overflow: hidden;
      }
      .ceo-blueprint-num {
        text-align: right; flex-shrink: 0; min-width: 78px;
      }
      .ceo-blueprint-foot {
        display: flex; justify-content: space-between; align-items: center;
        margin-top: 12px; padding-top: 10px;
        border-top: 1px solid ${FN.divider};
        font-size: 10px; color: ${FN.muted};
        text-transform: uppercase; letter-spacing: 0.15em;
      }
      .ceo-dock-btn {
        background: transparent; border: 1px solid; padding: 9px 16px; border-radius: 3px;
        font-family: 'JetBrains Mono', monospace; font-size: 9.5px; letter-spacing: 0.25em;
        text-transform: uppercase; font-weight: 700; cursor: pointer;
        display: inline-flex; align-items: center; gap: 6px;
        transition: all 0.2s;
      }
      .ceo-dock-btn:hover { transform: translateY(-1px); box-shadow: 0 0 10px currentColor; }

      /* Rotate modal */
      .ceo-modal-overlay {
        position: fixed; inset: 0; background: rgba(3,7,18,0.78);
        display: flex; align-items: center; justify-content: center;
        z-index: 60; padding: 16px;
        backdrop-filter: blur(4px);
      }
      .ceo-modal {
        background: ${FN.bgCard}; border: 1px solid ${FN.amber};
        padding: 28px 26px; border-radius: 4px; width: 100%; max-width: 420px;
        position: relative;
        box-shadow: 0 20px 50px rgba(0,0,0,0.5), 0 0 0 1px rgba(245,158,11,0.2);
      }
      .ceo-input-modal {
        width: 100%; background: ${FN.bgInput}; border: 1px solid ${FN.divider};
        color: ${FN.text}; padding: 9px 11px; font-size: 13px; border-radius: 2px;
        font-family: 'JetBrains Mono', monospace; letter-spacing: 0.2em;
        margin-bottom: 12px; outline: none;
      }
      .ceo-input-modal:focus { border-color: ${FN.amber}; }
      .ceo-pill-solid {
        padding: 10px 18px; border: 0; border-radius: 2px;
        font-family: 'JetBrains Mono', monospace; font-size: 10px; letter-spacing: 0.3em;
        text-transform: uppercase; font-weight: 700; cursor: pointer;
      }

      /* ===================== MOBILE: ≤768px ===================== */
      @media (max-width: 768px) {
        .app-container {
          grid-template-columns: 1fr;
          grid-template-rows: auto auto 1fr auto;
          grid-template-areas:
            "header"
            "sidebar"
            "main"
            "footer";
          height: auto;
        }
        .ceo-header { flex-direction: column; align-items: flex-start; }
        .ceo-header h1 { font-size: 13px; }
        .ceo-sub { font-size: 9px; }
        .ceo-header-right { width: 100%; justify-content: space-between; }
        .ceo-sidebar {
          flex-direction: row; justify-content: space-around;
          padding: 8px 6px; gap: 6px;
          border-right: none; border-bottom: 1px solid ${FN.divider};
          overflow-x: auto;
        }
        .ceo-nav-btn { width: auto; flex-direction: row; gap: 5px; padding: 6px 10px; flex-shrink: 0; }
        .ceo-nav-btn span { font-size: 9px; margin-top: 0; }
        .ceo-kpi-grid { grid-template-columns: 1fr 1fr; gap: 8px; }
        .ceo-mesh,
        .ceo-mesh-3 { grid-template-columns: 1fr; }
        .ceo-pricing-cols { grid-template-columns: 1fr; gap: 14px; }
        .ceo-price-readout { text-align: left; }
        .ceo-cal-grid { grid-template-columns: repeat(4, 1fr); }
        .ceo-dock { justify-content: center; padding: 10px 12px; }
        .ceo-dock-btn { flex: 1 1 calc(50% - 6px); justify-content: center; }
      }

      /* ===================== TABLET: 769–1124px ===================== */
      @media (min-width: 769px) and (max-width: 1124px) {
        .app-container { grid-template-columns: 70px 1fr; }
        .ceo-kpi-grid { grid-template-columns: repeat(3, 1fr); }
        .ceo-kpi-grid > div:nth-child(5) { grid-column: span 3; }
        .ceo-mesh,
        .ceo-mesh-3 { grid-template-columns: 1fr; }
        .ceo-pricing-cols { grid-template-columns: 1fr 1fr; }
        .ceo-price-readout { grid-column: span 2; text-align: center; }
      }
    `}</style>
  );
}
