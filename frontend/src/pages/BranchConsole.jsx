/**
 * /admin/branch-console — STRATEX™ Branch Manager Console (v2.6)
 *
 * Three surfaces in one dark-neon page:
 *  1. Master Price Index    — live tier 1/2/3 ledger (managed via /admin/ops Catalog tab)
 *  2. Drone Telemetry Input — paste / edit the raw payload, run the pipeline
 *  3. Multi-Agent Consensus — 3 Haiku verifiers + 1 Sonnet 4.5 senior reviewer
 *
 * NOTHING gets registered onto a job until consensus passes.
 */
import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  CheckCircle2, AlertTriangle, Lock, PlayCircle, Cpu, Award,
  Activity, ShieldCheck, FileWarning, Atom, Zap, ExternalLink,
} from "lucide-react";
import YellowTriangleWidget from "@/components/YellowTriangleWidget";
import ScrollingGlassDock from "@/components/ScrollingGlassDock";

const TEAL = "#00F0FF";
const ORANGE = "#FF7B00";
const RED = "#EF4444";
const YELLOW = "#F59E0B";
const NICKEL = "#3A4350";
const BG_MAIN = "#05080E";
const BG_CARD = "#080D16";

const USD = (n) => Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

const DEFAULT_PAYLOAD = {
  projectId: "STRATEX-AD-KY041",
  job_id: "crown-demo",
  contractor_id: null,
  assigned_tier: "tier3",
  measurements: {
    roofPerimeter_ft: 180, roofArea_sqft: 2450, pitch: 6, pitchMultiplier: 1.118,
    hips_ft: 128, ridges_ft: 48, valleys_ft: 168, overhang_in: 18,
    housePerimeter_ft: 160, wallAreaGross_sqft: 3200, wallHeight_ft: 10,
    windowOpenings_sqft: 240, doorOpenings_sqft: 60,
    windowPerimeter_ft: 96, doorPerimeter_ft: 42,
  },
  thermalSensors: {
    moistureDetections: [
      { id: "M01", level: 0.78, placement: "Valley Overlap Run",   target: "decking",  code: "CODE-B2-RED"    },
      { id: "M02", level: 0.65, placement: "Dormer Sidewall",      target: "framing",  code: "CODE-F10-AMBER" },
      { id: "M03", level: 0.42, placement: "Chimney Crickets",     target: "chimney",  code: "CODE-H8-AMBER"  },
    ],
    altitudinalExtensions_ft: 45,
  },
  pipeBootsData: [{ count: 3, size_in: 2 }, { count: 1, size_in: 3 }],
  financials: { overheadPercent: 10, profitPercent: 8, isInsuranceJob: true, insuranceMultiplier: 1.04 },
  register: false,
};

const Panel = ({ title, right, children, testid }) => (
  <section data-testid={testid}
    style={{
      background: BG_CARD, border: `1px solid ${TEAL}33`,
      borderRadius: 8, padding: "1.5rem", marginBottom: "1.5rem",
      boxShadow: `0 0 15px ${TEAL}0D`,
    }}>
    <div className="flex items-center justify-between mb-4">
      <h2 className="font-mono text-[13px] uppercase tracking-[0.22em]"
        style={{ color: TEAL, textShadow: `0 0 5px ${TEAL}4D` }}>// {title}</h2>
      {right}
    </div>
    {children}
  </section>
);

const NeonStat = ({ label, value, accent = TEAL, sub }) => (
  <div style={{
    background: BG_MAIN, border: `1px solid ${accent}33`,
    borderLeft: `3px solid ${accent}`, padding: "0.75rem 1rem", borderRadius: 4,
  }}>
    <div className="text-[9px] font-mono uppercase tracking-[0.25em]" style={{ color: "#64748B" }}>{label}</div>
    <div className="font-mono text-[18px] font-bold tabular-nums mt-0.5" style={{ color: accent, textShadow: `0 0 6px ${accent}55` }}>
      {value}
    </div>
    {sub && <div className="text-[10px] font-mono mt-0.5" style={{ color: "#64748B" }}>{sub}</div>}
  </div>
);

const Badge = ({ children, color = TEAL }) => (
  <span style={{
    background: `${color}1A`, border: `1px solid ${color}55`, color,
    padding: "0.2rem 0.55rem", borderRadius: 3, fontSize: 10,
    fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase",
    fontFamily: "monospace",
  }}>{children}</span>
);

const NumField = ({ label, value, onChange, step = 1 }) => (
  <label className="block">
    <span className="block text-[9px] font-mono uppercase tracking-[0.22em] mb-1" style={{ color: "#64748B" }}>{label}</span>
    <input type="number" step={step} value={value}
      onChange={(e) => onChange(parseFloat(e.target.value) || 0)}
      style={{
        background: "#000", border: `1px solid ${TEAL}4D`, color: "#fff",
        padding: "0.3rem 0.55rem", width: "100%", fontFamily: "monospace", fontSize: 12, borderRadius: 3,
      }}/>
  </label>
);

const RULING_TONE = {
  REGISTER:             { color: TEAL,   label: "REGISTER",            icon: CheckCircle2 },
  REGISTER_WITH_FLAGS:  { color: YELLOW, label: "REGISTER · W/FLAGS",  icon: AlertTriangle },
  HALT:                 { color: RED,    label: "HALT · DO NOT REGISTER", icon: FileWarning },
};

export default function BranchConsole() {
  const [ledger, setLedger] = useState([]);
  const [payload, setPayload] = useState(DEFAULT_PAYLOAD);
  const [result, setResult] = useState(null);
  const [runs, setRuns] = useState([]);
  const [running, setRunning] = useState(false);
  const [err, setErr] = useState("");

  async function loadLedger() {
    try {
      const r = await api.get("/branch/master-price-index");
      setLedger(r.data.items || []);
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    }
  }
  async function loadRuns() {
    try {
      const r = await api.get("/branch/consensus-runs");
      setRuns(r.data.runs || []);
    } catch (e) {/* non-fatal */}
  }
  useEffect(() => { loadLedger(); loadRuns(); }, []);

  function setMeas(k, v) { setPayload((p) => ({ ...p, measurements: { ...p.measurements, [k]: v } })); }
  function setFin(k, v)  { setPayload((p) => ({ ...p, financials: { ...p.financials, [k]: v } })); }
  function setTier(t)    { setPayload((p) => ({ ...p, assigned_tier: t })); }

  async function executePipeline(register = false) {
    setRunning(true);
    setResult(null);
    setErr("");
    try {
      const r = await api.post("/branch/quantify", { ...payload, register });
      setResult(r.data);
      const tone = RULING_TONE[r.data.ruling] || RULING_TONE.HALT;
      toast.success(`Senior Ruling: ${tone.label} · Score ${r.data.consensus_score}`);
      await loadRuns();
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
      toast.error("Pipeline failed: " + (e.response?.data?.detail || e.message));
    } finally {
      setRunning(false);
    }
  }

  const ruling = result?.ruling;
  const tone = RULING_TONE[ruling];

  return (
    <div style={{ background: BG_MAIN, color: "#F1F5F9", minHeight: "100vh", padding: "2rem", fontFamily: "monospace" }}>
      <ScrollingGlassDock portal="gm" routePrefix="/admin"/>
      <div className="max-w-[1600px] mx-auto">

        {/* Header */}
        <div className="mb-6 flex items-end justify-between border-b pb-5" style={{ borderColor: `${TEAL}22` }}>
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em]" style={{ color: TEAL }}>
              <Lock size={11}/> Stratex Core Engine · v2.6
            </div>
            <h1 className="text-3xl md:text-4xl font-bold tracking-tight mt-2" style={{ color: "#fff" }}>
              <span style={{ color: TEAL, textShadow: `0 0 8px ${TEAL}55` }}>//</span> EMERGENCE STACK ARCHITECTURE
            </h1>
            <p className="text-xs mt-2" style={{ color: "#64748B", maxWidth: 720 }}>
              Multi-Agent Swarm Integration · Branch Manager Override Command Console.
              Drone telemetry is parsed deterministically, then cross-checked by three independent
              Haiku verifiers and a Senior Sonnet 4.5 reviewer before any data is registered to a job.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <YellowTriangleWidget portal="gm"/>
            <a href="/admin/overseer"
              data-testid="branch-view-halts-link"
              style={{
                display: "inline-flex", alignItems: "center", gap: 6,
                padding: "0.45rem 0.9rem", borderRadius: 4,
                background: `${RED}12`, border: `1px solid ${RED}55`, color: RED,
                fontSize: 10, fontWeight: 700, letterSpacing: "0.2em",
                textTransform: "uppercase", fontFamily: "monospace",
                textDecoration: "none", textShadow: `0 0 4px ${RED}55`,
              }}>
              <FileWarning size={11}/> View Halts · Overseer
              <ExternalLink size={9}/>
            </a>
            <Badge color={TEAL}><Atom size={10} className="inline mr-1"/>v2.6 Live</Badge>
          </div>
        </div>

        {/* Branch Manager Materials Ledger snapshot */}
        <Panel title="BRANCH MANAGER GLOBAL MATERIALS LEDGER" testid="branch-ledger-panel"
          right={<Badge color={ORANGE}>{ledger.length} CANONICAL SKUS</Badge>}>
          <div style={{ overflowX: "auto" }}>
            <table className="w-full text-left" style={{ fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #14233C" }}>
                  {["Component Element", "Tier 1 (Base)", "Tier 2 (Strategic)", "Tier 3 (Enterprise)"].map((h, i) => (
                    <th key={i} className="px-3 py-2 text-[10px] uppercase tracking-[0.18em]" style={{ color: "#64748B" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {ledger.map((m) => (
                  <tr key={m.id} style={{ borderBottom: "1px solid #14233C" }} data-testid={`branch-row-${m.id}`}>
                    <td className="px-3 py-2.5 font-bold" style={{ color: "#F1F5F9" }}>{m.name}</td>
                    <td className="px-3 py-2.5 tabular-nums" style={{ color: "#94A3B8" }}>{USD(m.tier1_usd)}</td>
                    <td className="px-3 py-2.5 tabular-nums" style={{ color: TEAL, textShadow: `0 0 4px ${TEAL}55` }}>{USD(m.tier2_usd)}</td>
                    <td className="px-3 py-2.5 tabular-nums font-bold" style={{ color: ORANGE, textShadow: `0 0 4px ${ORANGE}55` }}>{USD(m.tier3_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="mt-3 text-[10px]" style={{ color: "#64748B" }}>
            Manage SKUs (add / edit / purge) at <a href="/admin/ops" style={{ color: TEAL }}>/admin/ops</a> → Material Catalog tab.
          </div>
        </Panel>

        {/* Drone Telemetry Input */}
        <Panel title="DRONE TELEMETRY PAYLOAD · QUANTIFY INPUT" testid="quantify-input-panel"
          right={
            <div className="flex items-center gap-2">
              {["tier1", "tier2", "tier3"].map((t) => (
                <button key={t} onClick={() => setTier(t)}
                  data-testid={`tier-toggle-${t}`}
                  style={{
                    padding: "0.3rem 0.7rem", borderRadius: 3, fontSize: 10, fontWeight: 700,
                    letterSpacing: "0.2em", textTransform: "uppercase",
                    cursor: "pointer", fontFamily: "monospace",
                    background: payload.assigned_tier === t ? `${TEAL}1F` : "transparent",
                    border: `1px solid ${payload.assigned_tier === t ? TEAL : NICKEL + "55"}`,
                    color: payload.assigned_tier === t ? TEAL : "#94A3B8",
                  }}>
                  {t}
                </button>
              ))}
            </div>
          }>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
            <NumField label="Roof Perimeter ft" value={payload.measurements.roofPerimeter_ft} onChange={(v) => setMeas("roofPerimeter_ft", v)}/>
            <NumField label="Roof Area sqft" value={payload.measurements.roofArea_sqft} onChange={(v) => setMeas("roofArea_sqft", v)}/>
            <NumField label="Pitch ×Multiplier" value={payload.measurements.pitchMultiplier} step="0.001" onChange={(v) => setMeas("pitchMultiplier", v)}/>
            <NumField label="Valleys ft" value={payload.measurements.valleys_ft} onChange={(v) => setMeas("valleys_ft", v)}/>
            <NumField label="Ridges ft" value={payload.measurements.ridges_ft} onChange={(v) => setMeas("ridges_ft", v)}/>
            <NumField label="Hips ft" value={payload.measurements.hips_ft} onChange={(v) => setMeas("hips_ft", v)}/>
            <NumField label="Wall Gross sqft" value={payload.measurements.wallAreaGross_sqft} onChange={(v) => setMeas("wallAreaGross_sqft", v)}/>
            <NumField label="Window Openings sqft" value={payload.measurements.windowOpenings_sqft} onChange={(v) => setMeas("windowOpenings_sqft", v)}/>
            <NumField label="Door Openings sqft" value={payload.measurements.doorOpenings_sqft} onChange={(v) => setMeas("doorOpenings_sqft", v)}/>
            <NumField label="Overhead %" value={payload.financials.overheadPercent} onChange={(v) => setFin("overheadPercent", v)}/>
            <NumField label="Profit %" value={payload.financials.profitPercent} onChange={(v) => setFin("profitPercent", v)}/>
            <NumField label="Insurance ×" value={payload.financials.insuranceMultiplier} step="0.01" onChange={(v) => setFin("insuranceMultiplier", v)}/>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => executePipeline(false)} disabled={running}
              data-testid="quantify-dry-run"
              style={{
                background: `${TEAL}1A`, border: `1px solid ${TEAL}`, color: TEAL,
                padding: "0.7rem 1.4rem", borderRadius: 4, fontFamily: "monospace",
                fontSize: 11, fontWeight: 700, letterSpacing: "0.18em",
                textTransform: "uppercase", cursor: running ? "not-allowed" : "pointer",
                opacity: running ? 0.4 : 1, display: "inline-flex", alignItems: "center", gap: 8,
              }}>
              <PlayCircle size={14}/>{running ? "Running Swarm…" : "Execute Pipeline · Dry Run"}
            </button>
            <button onClick={() => executePipeline(true)} disabled={running || !payload.job_id}
              data-testid="quantify-register"
              style={{
                background: `${ORANGE}1A`, border: `1px solid ${ORANGE}`, color: ORANGE,
                padding: "0.7rem 1.4rem", borderRadius: 4, fontFamily: "monospace",
                fontSize: 11, fontWeight: 700, letterSpacing: "0.18em",
                textTransform: "uppercase", cursor: (running || !payload.job_id) ? "not-allowed" : "pointer",
                opacity: (running || !payload.job_id) ? 0.4 : 1, display: "inline-flex", alignItems: "center", gap: 8,
              }}>
              <ShieldCheck size={14}/>Run + Register if Consensus
            </button>
            {err && <span style={{ color: RED, fontSize: 11 }} data-testid="quantify-error">{err}</span>}
          </div>
        </Panel>

        {/* Consensus Verdict */}
        {result && tone && (
          <Panel title="MULTI-AGENT CONSENSUS VERDICT" testid="consensus-verdict-panel"
            right={
              <div className="flex items-center gap-2">
                <Badge color={tone.color}><tone.icon size={11} className="inline mr-1"/>{tone.label}</Badge>
                {result.registered && <Badge color={TEAL}>WRITTEN TO JOB</Badge>}
                {!result.registered && result.ruling === "HALT" && (
                  <a href="/admin/overseer"
                    data-testid="consensus-view-halt-link"
                    style={{
                      display: "inline-flex", alignItems: "center", gap: 4,
                      padding: "0.2rem 0.55rem", borderRadius: 3,
                      background: `${RED}1A`, border: `1px solid ${RED}55`, color: RED,
                      fontSize: 10, fontWeight: 700, letterSpacing: "0.18em",
                      textTransform: "uppercase", fontFamily: "monospace",
                      textDecoration: "none",
                    }}>
                    Inspect in Overseer <ExternalLink size={9}/>
                  </a>
                )}
              </div>
            }>
            <div style={{
              background: `linear-gradient(135deg, ${BG_MAIN} 0%, ${tone.color}11 100%)`,
              border: `1px solid ${tone.color}55`, borderLeft: `4px solid ${tone.color}`,
              padding: "1.25rem 1.5rem", borderRadius: 6,
              boxShadow: `0 0 20px ${tone.color}22, inset 0 0 0 1px ${tone.color}22`,
            }} data-testid="consensus-senior-card">
              <div className="flex items-center gap-3 mb-2">
                <Cpu size={18} color={tone.color}/>
                <div className="text-[10px] uppercase tracking-[0.3em]" style={{ color: tone.color }}>SENIOR REVIEWER · CLAUDE SONNET 4.5</div>
              </div>
              <div className="text-[14px] font-bold mb-1" style={{ color: "#fff" }}>
                Ruling: <span style={{ color: tone.color, textShadow: `0 0 6px ${tone.color}55` }}>{tone.label}</span>
                <span className="ml-3 text-[12px]" style={{ color: "#94A3B8" }}>· consensus score {result.consensus_score}/100</span>
              </div>
              <div className="text-[12px] mt-2" style={{ color: "#CBD5E1", lineHeight: 1.55 }}>
                {result.senior_ruling?.reasoning || "—"}
              </div>
              <div className="grid grid-cols-2 gap-3 mt-3">
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] mb-1" style={{ color: TEAL }}>Agreements</div>
                  <ul className="text-[11px] space-y-0.5" style={{ color: "#CBD5E1" }}>
                    {(result.senior_ruling?.agreements || []).map((a, i) => (
                      <li key={i}>· {a}</li>
                    ))}
                    {(result.senior_ruling?.agreements || []).length === 0 && <li style={{ color: "#64748B" }}>—</li>}
                  </ul>
                </div>
                <div>
                  <div className="text-[9px] uppercase tracking-[0.22em] mb-1" style={{ color: ORANGE }}>Dissents</div>
                  <ul className="text-[11px] space-y-0.5" style={{ color: "#CBD5E1" }}>
                    {(result.senior_ruling?.dissents || []).map((d, i) => (
                      <li key={i}>· {d}</li>
                    ))}
                    {(result.senior_ruling?.dissents || []).length === 0 && <li style={{ color: "#64748B" }}>—</li>}
                  </ul>
                </div>
              </div>
            </div>

            {/* 3-verifier triad */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mt-4">
              {(result.verifier_reports || []).map((v) => {
                const conf = v.confidence_pct ?? 0;
                const isConfirmed = v.verdict === "confirmed";
                const accent = isConfirmed ? TEAL : v.verdict === "flagged" ? YELLOW : RED;
                return (
                  <div key={v.verifier}
                    data-testid={`verifier-card-${v.verifier}`}
                    style={{
                      background: BG_MAIN, border: `1px solid ${accent}55`,
                      borderTop: `3px solid ${accent}`, padding: "1rem 1.1rem", borderRadius: 4,
                    }}>
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-[10px] uppercase tracking-[0.22em] font-bold" style={{ color: accent }}>
                        Verifier · {v.verifier}
                      </div>
                      <Activity size={12} color={accent}/>
                    </div>
                    <div className="text-[20px] font-bold tabular-nums" style={{ color: accent, textShadow: `0 0 6px ${accent}55` }}>
                      {conf}%
                    </div>
                    <div className="text-[9px] uppercase tracking-[0.22em] mt-0.5" style={{ color: "#64748B" }}>{v.verdict || "—"}</div>
                    <div className="text-[11px] mt-2 leading-snug" style={{ color: "#CBD5E1" }}>{v.narrative || "—"}</div>
                    {(v.discrepancies || []).length > 0 && (
                      <div className="mt-2 text-[10px]" style={{ color: ORANGE }}>
                        {(v.discrepancies || []).map((d, i) => <div key={i}>· {d}</div>)}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </Panel>
        )}

        {/* Deterministic output */}
        {result?.deterministic && (
          <Panel title="DETERMINISTIC COMPUTATION REPORT" testid="deterministic-report-panel">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
              <NeonStat label="Net Wall Area" value={`${result.deterministic.geometry.net_wall_sqft.toLocaleString()} sqft`} accent={TEAL}/>
              <NeonStat label="Adjusted Roof" value={`${result.deterministic.geometry.roof_total_sqft_adjusted.toLocaleString()} sqft`} accent={TEAL}/>
              <NeonStat label="Squares · Net" value={result.deterministic.geometry.roof_squares_net.toFixed(2)} accent={YELLOW}/>
              <NeonStat label="Squares · +Waste" value={result.deterministic.geometry.roof_squares_with_waste.toFixed(2)} sub="incl. 10% waste" accent={ORANGE}/>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
              <NeonStat label="Materials Cost" value={USD(result.deterministic.financial_summary.materials_cost_usd)} accent={TEAL}/>
              <NeonStat label={`Labor · ${result.deterministic.labor.estimated_man_hours} hrs @ $${result.deterministic.labor.rate_per_hour_usd}/hr`} value={USD(result.deterministic.financial_summary.labor_cost_usd)} accent={YELLOW}/>
              <NeonStat label="Mechanical Subtotal" value={USD(result.deterministic.financial_summary.mechanical_subtotal_usd)} accent="#94A3B8"/>
              {result.deterministic.financial_summary.insurance_markup_usd > 0 && (
                <NeonStat label={`Insurance × ${result.deterministic.financial_summary.insurance_multiplier}`}
                  value={USD(result.deterministic.financial_summary.insurance_markup_usd)} accent={YELLOW}/>
              )}
              <NeonStat label={`Overhead ${result.deterministic.financial_summary.overhead_pct}% + Profit ${result.deterministic.financial_summary.profit_pct}%`}
                value={USD(result.deterministic.financial_summary.overhead_profit_usd)} accent={ORANGE}/>
              <div style={{
                background: `linear-gradient(135deg, ${BG_MAIN} 0%, ${TEAL}1F 100%)`,
                border: `1px solid ${TEAL}`, borderLeft: `4px solid ${TEAL}`,
                padding: "0.75rem 1rem", borderRadius: 4,
                boxShadow: `0 0 20px ${TEAL}33, inset 0 0 0 1px ${TEAL}33`,
              }}>
                <div className="text-[9px] uppercase tracking-[0.22em]" style={{ color: `${TEAL}AA` }}>Net Gross Total</div>
                <div className="font-mono text-[22px] font-bold tabular-nums" style={{ color: TEAL, textShadow: `0 0 8px ${TEAL}88` }}>
                  {USD(result.deterministic.financial_summary.gross_total_usd)}
                </div>
              </div>
            </div>

            <details>
              <summary className="text-[10px] uppercase tracking-[0.22em] cursor-pointer mb-2" style={{ color: TEAL }}>
                ▸ View {result.deterministic.line_items.length} line items
              </summary>
              <div style={{ overflowX: "auto" }}>
                <table className="w-full text-left mt-3" style={{ fontSize: 12 }}>
                  <thead>
                    <tr style={{ borderBottom: "1px solid #14233C" }}>
                      {["Line Item", "Qty", "Unit Price", "Line Total"].map((h, i) => (
                        <th key={i} className={`px-3 py-2 text-[10px] uppercase tracking-[0.18em] ${i > 0 ? "text-right" : ""}`} style={{ color: "#64748B" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.deterministic.line_items.map((li, i) => (
                      <tr key={i} style={{ borderBottom: "1px solid #14233C" }} data-testid={`line-${i}`}>
                        <td className="px-3 py-2" style={{ color: "#F1F5F9" }}>{li.label}</td>
                        <td className="px-3 py-2 text-right tabular-nums" style={{ color: "#94A3B8" }}>{li.quantity}</td>
                        <td className="px-3 py-2 text-right tabular-nums" style={{ color: "#94A3B8" }}>{USD(li.unit_price_usd)}</td>
                        <td className="px-3 py-2 text-right tabular-nums font-bold" style={{ color: TEAL }}>{USD(li.line_total_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          </Panel>
        )}

        {/* Recent runs */}
        <Panel title="RECENT CONSENSUS RUNS" testid="recent-runs-panel">
          {runs.length === 0 ? (
            <div className="text-[11px] py-6 text-center" style={{ color: "#64748B" }}>No runs yet · execute the pipeline above.</div>
          ) : (
            <table className="w-full text-left" style={{ fontSize: 12 }}>
              <thead>
                <tr style={{ borderBottom: "1px solid #14233C" }}>
                  {["Run ID", "Project", "Tier", "Ruling", "Score", "Registered", "When"].map((h) => (
                    <th key={h} className="px-3 py-2 text-[10px] uppercase tracking-[0.18em]" style={{ color: "#64748B" }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {runs.slice(0, 10).map((r) => {
                  const t = RULING_TONE[r.ruling] || RULING_TONE.HALT;
                  return (
                    <tr key={r.id} style={{ borderBottom: "1px solid #14233C" }} data-testid={`run-row-${r.id}`}>
                      <td className="px-3 py-2 font-mono" style={{ color: "#94A3B8" }}>{r.id}</td>
                      <td className="px-3 py-2" style={{ color: "#F1F5F9" }}>{r.project_id}</td>
                      <td className="px-3 py-2"><Badge color={ORANGE}>{r.assigned_tier}</Badge></td>
                      <td className="px-3 py-2"><Badge color={t.color}>{t.label}</Badge></td>
                      <td className="px-3 py-2 font-mono tabular-nums" style={{ color: t.color }}>{r.consensus_score}</td>
                      <td className="px-3 py-2">{r.registered ? <Badge color={TEAL}>YES</Badge> : <Badge color={NICKEL}>NO</Badge>}</td>
                      <td className="px-3 py-2 font-mono text-[10px]" style={{ color: "#64748B" }}>{(r.created_at || "").slice(0, 16).replace("T", " ")}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </Panel>
      </div>
    </div>
  );
}
