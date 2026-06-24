// STRATEX™ — Demo Scan Wizard
// Auth-free 3-step flow:  Dossier → Upload → Analysis + Report
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { StratexWordmark, StratexGlyph } from "@/components/StratexBrand";
import ParametricTwin from "@/components/ParametricTwin";
import StratexTwinGallery from "@/components/StratexTwinGallery";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const USD = (n) =>
  n == null ? "—" : `$${Number(n).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

const SEV_COLOR = {
  URGENT: "#FF2D78", SEVERE: "#FF2D78", FAILED: "#FF2D78",
  HIGH: "#FF7B00", WORN: "#FFB020", MED: "#FFB020",
  LOW: "#00FF9C", NONE: "#7C8A9E", OK: "#00FF9C",
};

function Pill({ children, color }) {
  return (
    <span className="inline-block px-2 py-0.5 rounded-full text-[8px] font-mono tracking-[0.14em] border"
      style={{ color: color || "#00E5FF", borderColor: color || "#00E5FF" }}>
      {children}
    </span>
  );
}

function Frame({ children, color = "cyan", className = "" }) {
  const palette = {
    cyan: ["rgba(0,229,255,0.45)", "rgba(0,229,255,0.08)"],
    amber: ["rgba(255,176,32,0.45)", "rgba(255,176,32,0.08)"],
    green: ["rgba(0,255,156,0.45)", "rgba(0,255,156,0.08)"],
    mag:   ["rgba(255,45,120,0.45)", "rgba(255,45,120,0.08)"],
  }[color];
  return (
    <div className={"rounded-md p-4 backdrop-blur-md " + className}
      style={{ border: `1px solid ${palette[0]}`, background: "rgba(15,22,34,0.65)", boxShadow: `inset 0 0 24px ${palette[1]}` }}>
      {children}
    </div>
  );
}

export default function DemoScanWizard({ initialStep = 1 }) {
  const nav = useNavigate();
  const [step, setStep] = useState(initialStep);
  const [dossier, setDossier] = useState({
    address: "142 Bluegrass Ridge",
    city_state: "Lexington, KY",
    year_built: 1998,
    ownership: "Anthony Cross",
    region: "Midwest",
    notes: "",
  });
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [analysis, setAnalysis] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const fileRef = useRef(null);
  const autoFiredRef = useRef(false);

  // Auto-load sample analysis when the user lands at step 3 directly
  // (e.g. via the Diagnostic Twin / Quant / Maintenance / Supply Chain tiles).
  // Uses the fast deterministic /sample endpoint — instant, no LLM.
  useEffect(() => {
    if (initialStep === 3 && !analysis && !autoFiredRef.current) {
      autoFiredRef.current = true;
      (async () => {
        setLoading(true);
        try {
          const r = await axios.get(`${API}/demo/sample`, { timeout: 30000 });
          setAnalysis(r.data);
          setSessionId("sample"); // PDF endpoint serves sample on this id
        } catch (e) {
          setError(e.response?.data?.detail || e.message);
        } finally {
          setLoading(false);
        }
      })();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialStep]);

  const upd = (k, v) => setDossier((d) => ({ ...d, [k]: v }));

  const analyze = async () => {
    setLoading(true); setError(null);
    try {
      const fd = new FormData();
      Object.entries(dossier).forEach(([k, v]) => fd.append(k, v));
      files.forEach((f) => fd.append("images", f));
      const r = await axios.post(`${API}/demo/scan-analyze`, fd, { timeout: 90000 });
      setAnalysis(r.data.analysis);
      setSessionId(r.data.session_id);
      setStep(3);
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen text-silver font-sans" data-testid="demo-scan-wizard" style={{
      background: "radial-gradient(ellipse at 80% 5%, rgba(0,229,255,0.10) 0%, transparent 50%), radial-gradient(ellipse at 0% 100%, rgba(255,123,0,0.07) 0%, transparent 50%), #02060B",
    }}>
      {/* Top rail */}
      <div className="border-b border-cyan-400/15 px-8 py-4 flex items-center justify-between">
        <button onClick={() => nav("/")} className="flex items-center gap-3 hover:opacity-80 transition" data-testid="back-switchboard">
          <span className="text-cyan-400 text-lg">←</span>
          <StratexGlyph size={32}/>
          <StratexWordmark size="sm"/>
          <span className="font-mono text-[9px] tracking-[0.22em] text-slate-500 ml-2 hidden sm:inline">SWITCHBOARD</span>
        </button>
        <div className="font-mono text-[9px] text-slate-400 tracking-widest">
          DEMO MODE · NO AUTHENTICATION · SCAN → REPORT
        </div>
      </div>

      {/* Stepper */}
      <div className="px-8 pt-6 max-w-[1480px] mx-auto">
        <div className="flex items-center gap-3 font-mono text-[10px] tracking-[0.18em]">
          {[
            { n: 1, label: "DOSSIER" },
            { n: 2, label: "UPLOAD" },
            { n: 3, label: "ANALYSIS + REPORT" },
          ].map((s, i) => (
            <span key={s.n} className="flex items-center gap-3">
              <span className={"w-7 h-7 rounded-full inline-flex items-center justify-center border-2 " +
                (step >= s.n ? "border-cyan-400 text-cyan-400 bg-cyan-400/10" : "border-slate-700 text-slate-500")}
                style={step >= s.n ? { boxShadow: "0 0 10px rgba(0,229,255,0.5)" } : {}}>
                {s.n}
              </span>
              <span className={step >= s.n ? "text-cyan-400" : "text-slate-500"}>{s.label}</span>
              {i < 2 && <span className="text-slate-700 mx-2">────</span>}
            </span>
          ))}
        </div>
      </div>

      {/* Body */}
      <div className="px-8 pt-8 max-w-[1480px] mx-auto pb-16">
        {step === 1 && (
          <Frame color="cyan" className="max-w-3xl">
            <div className="font-mono text-[9px] text-cyan-400 tracking-[0.28em] mb-4">// PROPERTY DOSSIER</div>
            <h2 className="text-2xl font-bold text-white mb-6 tracking-tight">Tell us about the property</h2>
            <div className="grid grid-cols-2 gap-4">
              <Input label="Street Address" tid="dossier-address" value={dossier.address} onChange={(v) => upd("address", v)}/>
              <Input label="City, State" tid="dossier-city" value={dossier.city_state} onChange={(v) => upd("city_state", v)}/>
              <Input label="Year Built" tid="dossier-year" type="number" value={dossier.year_built} onChange={(v) => upd("year_built", parseInt(v) || 0)}/>
              <Input label="Owner Name" tid="dossier-owner" value={dossier.ownership} onChange={(v) => upd("ownership", v)}/>
              <Input label="Region" tid="dossier-region" value={dossier.region} onChange={(v) => upd("region", v)}/>
              <Input label="Notes (optional)" tid="dossier-notes" value={dossier.notes} onChange={(v) => upd("notes", v)}/>
            </div>
            <div className="mt-6 flex justify-end">
              <button data-testid="dossier-next" onClick={() => setStep(2)}
                className="px-6 py-2.5 rounded font-mono text-xs tracking-[0.18em] text-black bg-cyan-400 hover:brightness-110"
                style={{ boxShadow: "0 0 22px rgba(0,229,255,0.6)" }}>
                CONTINUE → UPLOAD
              </button>
            </div>
          </Frame>
        )}

        {step === 2 && (
          <Frame color="amber" className="max-w-3xl">
            <div className="font-mono text-[9px] text-amber-400 tracking-[0.28em] mb-4">// DRONE PAYLOAD UPLOAD</div>
            <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">Upload your scan</h2>
            <p className="font-mono text-[11px] text-slate-400 mb-6">Drop drone photos, thermal frames, or topology exports. JPEG / PNG, up to 6 files. (Optional — skip to use a sample dataset.)</p>
            <div
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => { e.preventDefault(); setFiles(Array.from(e.dataTransfer.files).slice(0, 6)); }}
              onClick={() => fileRef.current?.click()}
              data-testid="upload-dropzone"
              className="border-2 border-dashed border-amber-400/40 rounded-md p-12 text-center cursor-pointer hover:border-amber-400 transition"
              style={{ background: "rgba(255,176,32,0.04)" }}
            >
              <div className="text-amber-400 text-4xl mb-2">⇧</div>
              <div className="font-mono text-xs text-slate-300 tracking-wide">
                {files.length === 0 ? "DROP FILES HERE · or click to browse" : `${files.length} file(s) selected`}
              </div>
              {files.length > 0 && (
                <div className="font-mono text-[10px] text-slate-500 mt-3 space-y-1">
                  {files.map((f, i) => <div key={i}>{f.name} · {(f.size / 1024).toFixed(0)} KB</div>)}
                </div>
              )}
              <input ref={fileRef} type="file" multiple accept="image/*" className="hidden"
                onChange={(e) => setFiles(Array.from(e.target.files).slice(0, 6))} data-testid="upload-input"/>
            </div>
            {error && <div className="mt-4 font-mono text-xs text-rose-400">⚠ {error}</div>}
            <div className="mt-6 flex justify-between items-center">
              <button onClick={() => setStep(1)} className="font-mono text-xs text-slate-400 hover:text-slate-200 tracking-[0.18em]" data-testid="upload-back">
                ← BACK
              </button>
              <button data-testid="run-analysis" onClick={analyze} disabled={loading}
                className="px-6 py-2.5 rounded font-mono text-xs tracking-[0.18em] text-black bg-amber-400 hover:brightness-110 disabled:opacity-50 disabled:cursor-not-allowed"
                style={{ boxShadow: "0 0 22px rgba(255,176,32,0.6)" }}>
                {loading ? "ANALYZING…" : "RUN STRATEX ANALYSIS →"}
              </button>
            </div>
            {loading && <AnalysisPulse/>}
          </Frame>
        )}

        {step === 3 && !analysis && (
          <Frame color="cyan" className="max-w-3xl">
            <div className="font-mono text-[9px] text-cyan-400 tracking-[0.28em] mb-4">// LOADING STRATEX ANALYSIS</div>
            <h2 className="text-2xl font-bold text-white tracking-tight">Initializing forensic agents…</h2>
            <AnalysisPulse/>
            {error && <div className="mt-4 font-mono text-xs text-rose-400">⚠ {error}</div>}
          </Frame>
        )}

        {step === 3 && analysis && (
          <AnalysisDashboard a={analysis} sessionId={sessionId} onRestart={() => { setStep(1); setAnalysis(null); setSessionId(null); setFiles([]); }}/>
        )}
      </div>
    </div>
  );
}

function Input({ label, tid, value, onChange, type = "text" }) {
  return (
    <div>
      <div className="font-mono text-[9px] text-slate-400 tracking-[0.22em] mb-1.5">{label}</div>
      <input
        data-testid={tid}
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-black/40 border border-cyan-400/30 rounded px-3 py-2 font-mono text-sm text-white focus:outline-none focus:border-cyan-400"
      />
    </div>
  );
}

function AnalysisPulse() {
  const stages = [
    "Spatial Ingestion · GPS lock acquired",
    "Photogrammetry · Mesh alignment 98.3%",
    "Quant Estimation · 11 facets segmented",
    "Thermal Forensics · 4 anomalies isolated",
    "Supply Chain · BOM compiled · Geofence armed",
  ];
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((x) => Math.min(x + 1, stages.length - 1)), 1200);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="mt-6 font-mono text-[10px] tracking-[0.18em] text-cyan-400 space-y-1.5">
      {stages.slice(0, i + 1).map((s, idx) => (
        <div key={idx} className="flex items-center gap-2">
          <span className="w-1.5 h-1.5 bg-cyan-400 rounded-full"/>
          <span>AGENT {idx + 1} · {s}</span>
        </div>
      ))}
    </div>
  );
}

function AnalysisDashboard({ a, sessionId, onRestart }) {
  const pdfUrl = `${API}/demo/scan-report.pdf?session_id=${sessionId}`;
  const [layer, setLayer] = useState(0); // 0 finished / 1 deck / 2 framing
  const [renderMode, setRenderMode] = useState("gallery"); // "gallery" | "parametric" | "ai"
  const [topology, setTopology] = useState(null);
  const layerImgs = [
    `${process.env.REACT_APP_BACKEND_URL}/api/pitch/assets/render_layer1_shingle.png`,
    `${process.env.REACT_APP_BACKEND_URL}/api/pitch/assets/render_layer2_decking.png`,
    `${process.env.REACT_APP_BACKEND_URL}/api/pitch/assets/render_layer3_framing.png`,
  ];

  useEffect(() => {
    axios.get(`${API}/public/demo-topology`)
      .then((r) => setTopology(r.data))
      .catch(() => setTopology(null));
  }, []);
  // Fallback: try the local /app preview path (file mounted via pitch route is more reliable);
  // if the API doesn't expose assets, the Switchboard demo will still show the rest.
  return (
    <div className="space-y-4" data-testid="analysis-dashboard">
      {/* Action bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="font-mono text-[9px] tracking-[0.28em] text-cyan-400 truncate">// PROJECT {a.project.id} · {a.project.city_state}</div>
          <h2 className="text-2xl md:text-3xl font-bold text-white tracking-tight break-words">{a.project.address}</h2>
        </div>
        <div className="flex gap-2 shrink-0">
          <a href={pdfUrl} target="_blank" rel="noreferrer" data-testid="open-pdf"
            className="px-4 py-2.5 rounded font-mono text-[11px] tracking-[0.18em] text-black bg-cyan-400 hover:brightness-110 whitespace-nowrap"
            style={{ boxShadow: "0 0 22px rgba(0,229,255,0.6)" }}>
            FULL PDF REPORT ↗
          </a>
          <button onClick={onRestart} data-testid="new-scan"
            className="px-4 py-2.5 rounded font-mono text-[11px] tracking-[0.18em] text-slate-300 border border-slate-600 hover:border-cyan-400 hover:text-cyan-400 whitespace-nowrap">
            NEW SCAN
          </button>
        </div>
      </div>

      {/* Top KPI row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <Kpi label="TOTAL SQUARES" value={a.quant.total_squares.toFixed(2)} unit="SQ" color="cyan"/>
        <Kpi label="SHINGLE LAYERS" value={`${a.quant.shingle_layers_detected}/${a.quant.code_max_layers}`} unit="DETECT/MAX" color="amber"/>
        <Kpi label="ANOMALIES" value={a.anomalies.length} unit="FORENSIC HOTSPOTS" color="mag"/>
        <Kpi label="ENVELOPE SCORE" value={`${a.envelope_scores.overall_envelope}/100`} unit="COMPOSITE" color="green"/>
      </div>

      {/* Grand total */}
      <Frame color="cyan">
        <div className="font-mono text-[9px] text-cyan-400 tracking-[0.28em]">// EXECUTIVE GRAND TOTAL RANGE</div>
        <div className="font-mono text-2xl sm:text-3xl md:text-4xl text-white mt-2 break-words" style={{ letterSpacing: "-0.02em" }}>
          <span style={{ color: "#00E5FF", textShadow: "0 0 8px rgba(0,229,255,0.6)" }}>{USD(a.totals.grand_total_low_usd)}</span>
          <span className="text-slate-500 text-base sm:text-lg mx-2 sm:mx-3">→</span>
          <span style={{ color: "#FFB020", textShadow: "0 0 8px rgba(255,176,32,0.6)" }}>{USD(a.totals.grand_total_high_usd)}</span>
        </div>
        <div className="font-mono text-[10px] text-slate-400 mt-2 tracking-wide leading-relaxed">
          MATERIALS <span className="text-white">{USD(a.totals.materials_usd)}</span>
          {a.totals.materials_breakdown && (
            <span className="text-slate-500"> [ROOF {USD(a.totals.materials_breakdown.roofing_bom_usd)} · SIDING {USD(a.totals.materials_breakdown.siding_package_usd)} · WALL-MOISTURE {USD(a.totals.materials_breakdown.wall_moisture_remediation_usd)}]</span>
          )}
          {" · "}LABOR <span className="text-white">{USD(a.totals.labor_usd)}</span>
          {a.totals.tear_off_usd ? <span> · TEAR-OFF <span className="text-white">{USD(a.totals.tear_off_usd)}</span></span> : null}
          {" · "}UNFORESEEN <span className="text-white">{USD(a.totals.side_quote_low_usd)}–{USD(a.totals.side_quote_high_usd)}</span>
        </div>
      </Frame>

      {/* Twin viewer + Priority queue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Frame color="amber" className="lg:col-span-2">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <h3 className="font-mono text-[10px] tracking-[0.22em] text-amber-400">TRIPLE-LAYER DIGITAL TWIN · BIM_RENDER AGENT</h3>
            <div className="flex gap-2 items-center flex-wrap">
              {/* Render mode toggle */}
              <div className="flex gap-1 border border-slate-700 rounded p-0.5">
                <button data-testid="render-mode-gallery"
                  onClick={() => setRenderMode("gallery")}
                  className={"px-2 py-1 rounded font-mono text-[9px] tracking-[0.14em] " +
                    (renderMode === "gallery" ? "bg-cyan-400 text-black" : "text-slate-400 hover:text-cyan-400")}
                  title="Approved Stratex BIM digital-twin gallery">
                  BIM TWIN
                </button>
                <button data-testid="render-mode-parametric"
                  onClick={() => setRenderMode("parametric")}
                  className={"px-2 py-1 rounded font-mono text-[9px] tracking-[0.14em] " +
                    (renderMode === "parametric" ? "bg-emerald-400 text-black" : "text-slate-400 hover:text-emerald-400")}
                  title="Parametric 3D from scan data">
                  SCAN 3D
                </button>
                <button data-testid="render-mode-ai"
                  onClick={() => setRenderMode("ai")}
                  className={"px-2 py-1 rounded font-mono text-[9px] tracking-[0.14em] " +
                    (renderMode === "ai" ? "bg-amber-400 text-black" : "text-slate-400 hover:text-amber-400")}
                  title="Layer-specific AI CAD render">
                  AI · CAD
                </button>
              </div>
              {/* Layer toggle */}
              <div className="flex gap-1">
                {["SLATE", "DECK", "FRAMING"].map((l, i) => (
                  <button key={l} data-testid={`twin-layer-${i}`}
                    onClick={() => setLayer(i)}
                    className={"px-3 py-1 rounded font-mono text-[9px] tracking-[0.16em] " +
                      (layer === i ? "bg-amber-400 text-black" : "bg-black/40 text-slate-400 border border-slate-700 hover:border-amber-400 hover:text-amber-400")}>
                    {l}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {renderMode === "gallery" ? (
            <StratexTwinGallery height={360}/>
          ) : renderMode === "parametric" ? (
            topology ? (
              <ParametricTwin topology={{
                facets: topology.facets,
                edges: topology.edges,
                rafters: topology.framing?.rafters || [],
              }} layer={layer} height={360}/>
            ) : (
              <div className="w-full rounded flex items-center justify-center font-mono text-[10px] text-cyan-400 tracking-[0.18em]"
                style={{ height: 360, background: "radial-gradient(ellipse at center, #0B1A22 0%, #03070C 100%)" }}>
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 bg-cyan-400 rounded-full animate-pulse"/>
                  LOADING SCAN TOPOLOGY · BIM_RENDER AGENT…
                </div>
              </div>
            )
          ) : (
            <img src={layerImgs[layer]} alt="" className="w-full rounded" style={{ background: "#03070C" }}
              onError={(e) => { e.target.style.display = "none"; }}/>
          )}

          <div className="font-mono text-[10px] text-slate-400 mt-3 tracking-wide leading-relaxed">
            <span className="text-emerald-400">●</span> Valleys <span className="text-white">{a.quant.valleys_lf.toFixed(1)} lf</span> ·
            Gables <span className="text-white"> {a.quant.gables_lf.toFixed(1)} lf</span> ·
            Ridges <span className="text-white"> {a.quant.ridges_lf.toFixed(1)} lf</span> ·
            Pitch <span className="text-white"> {a.quant.pitch_predominant}</span>
            {renderMode === "parametric" && topology && (
              <span className="text-slate-500"> · {topology.facets.length} facets · {(topology.framing?.rafters || []).length} rafters · drag to rotate</span>
            )}
          </div>
        </Frame>

        <Frame color="green">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-emerald-400 mb-3">AI-PRIORITIZED MAINTENANCE</h3>
          <div className="space-y-2">
            {a.priority_tasks.map((t) => (
              <div key={t.rank} className="grid items-center gap-2"
                style={{ gridTemplateColumns: "18px 60px 1fr 70px", paddingBottom: 6, borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="font-mono text-slate-500 text-xs">{t.rank}</div>
                <Pill color={SEV_COLOR[t.severity]}>{t.severity}</Pill>
                <div className="text-xs text-white">{t.task}</div>
                <div className="font-mono text-[10px] text-right text-emerald-400">${t.annual_savings_usd}/yr</div>
              </div>
            ))}
          </div>
        </Frame>
      </div>

      {/* Tear-off block */}
      {a.water_retention.tear_off_recommended && (
        <Frame color="mag">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 items-center">
            <div>
              <div className="font-mono text-[9px] text-pink-400 tracking-[0.28em]">// CRITICAL · TEAR-OFF MANDATE</div>
              <div className="text-5xl font-bold text-white mt-1">{a.water_retention.probability_pct}%</div>
              <div className="font-mono text-[10px] text-pink-400 tracking-wide mt-1">WATER-RETENTION PROBABILITY · DEPTH {a.water_retention.depth_estimate_in}"</div>
            </div>
            <div className="lg:col-span-2">
              <div className="text-sm text-slate-200 leading-relaxed">{a.water_retention.tear_off_rationale}</div>
              <div className="mt-3 font-mono text-[10px] text-slate-400 tracking-wide">
                TEAR-OFF COST INCLUDED · {USD(a.totals.tear_off_usd)}
              </div>
            </div>
          </div>
        </Frame>
      )}

      {/* Window / Door schedules */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Frame color="cyan">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-cyan-400 mb-3">WINDOW SCHEDULE</h3>
          <table className="w-full font-mono text-[10px]">
            <thead className="text-cyan-400">
              <tr><th className="text-left py-1.5">ID</th><th className="text-left">LOCATION</th><th className="text-left">SHAPE</th><th className="text-right">W</th><th className="text-right">H</th><th className="text-right">QTY</th><th className="text-left">LEAK</th></tr>
            </thead>
            <tbody>
              {a.window_schedule.map((w) => (
                <tr key={w.id} className="border-t border-white/5">
                  <td className="py-1.5 text-cyan-400">{w.id}</td>
                  <td className="text-slate-300">{w.location}</td>
                  <td className="text-slate-300">{w.shape}</td>
                  <td className="text-right text-white">{w.width_in}"</td>
                  <td className="text-right text-white">{w.height_in}"</td>
                  <td className="text-right text-white">{w.qty}</td>
                  <td><Pill color={SEV_COLOR[w.leak_severity]}>{w.leak_severity}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Frame>
        <Frame color="amber">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-amber-400 mb-3">EXTERIOR DOOR SCHEDULE</h3>
          <table className="w-full font-mono text-[10px]">
            <thead className="text-amber-400">
              <tr><th className="text-left py-1.5">ID</th><th className="text-left">LOCATION</th><th className="text-left">SHAPE</th><th className="text-right">W</th><th className="text-right">H</th><th className="text-left">SEAL</th></tr>
            </thead>
            <tbody>
              {a.door_schedule.map((d) => (
                <tr key={d.id} className="border-t border-white/5">
                  <td className="py-1.5 text-amber-400">{d.id}</td>
                  <td className="text-slate-300">{d.location}</td>
                  <td className="text-slate-300">{d.shape}</td>
                  <td className="text-right text-white">{d.width_in}"</td>
                  <td className="text-right text-white">{d.height_in}"</td>
                  <td><Pill color={SEV_COLOR[d.weatherstrip_status]}>{d.weatherstrip_status}</Pill></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Frame>
      </div>

      {/* BOM + Side quote */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Frame color="cyan" className="lg:col-span-2">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-cyan-400 mb-3">BILL OF MATERIALS</h3>
          <table className="w-full font-mono text-[10px]">
            <thead className="text-cyan-400">
              <tr><th className="text-left py-1.5">CATEGORY</th><th className="text-left">MATERIAL</th><th className="text-right">QTY</th><th className="text-left">UNIT</th><th className="text-right">UNIT</th><th className="text-right">LINE</th></tr>
            </thead>
            <tbody>
              {a.bom.map((b, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-1.5 text-slate-400">{b.category}</td>
                  <td className="text-slate-200">{b.material}</td>
                  <td className="text-right text-white">{b.qty}</td>
                  <td className="text-slate-400">{b.unit}</td>
                  <td className="text-right text-slate-300">{USD(b.unit_cost_usd)}</td>
                  <td className="text-right text-cyan-400">{USD(b.line_total_usd)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr><td colSpan="5" className="text-right pt-2 text-slate-400 tracking-widest">MATERIALS TOTAL</td>
                <td className="text-right pt-2 text-white font-bold">{USD(a.totals.materials_usd)}</td></tr>
            </tfoot>
          </table>
        </Frame>
        <Frame color="amber">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-amber-400 mb-3">SIDE QUOTE · UNFORESEEN</h3>
          <div className="space-y-2">
            {a.side_quote_unforeseen.map((s, i) => (
              <div key={i} className="border-b border-white/5 pb-2">
                <div className="flex justify-between text-xs">
                  <span className="text-slate-200">{s.item}</span>
                  <span className="font-mono text-amber-400">{s.probability_pct}%</span>
                </div>
                <div className="font-mono text-[10px] text-slate-400 mt-1">
                  {USD(s.low_usd)} – {USD(s.high_usd)} · <span className="text-slate-500">{s.note}</span>
                </div>
              </div>
            ))}
            <div className="pt-2 font-mono text-[10px] text-slate-400">
              RESERVE RANGE <span className="text-amber-400 font-bold">{USD(a.totals.side_quote_low_usd)}</span>
              <span className="mx-2">→</span>
              <span className="text-pink-400 font-bold">{USD(a.totals.side_quote_high_usd)}</span>
            </div>
          </div>
        </Frame>
      </div>

      {/* Labor */}
      <Frame color="green">
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-4">
          <div>
            <div className="font-mono text-[9px] text-emerald-400 tracking-[0.22em]">REGION</div>
            <div className="text-base text-white mt-1">{a.labor.region}</div>
          </div>
          <Kpi label="NATIONAL AVG / SQ" value={USD(a.labor.national_avg_per_sq)} color="green"/>
          <Kpi label="REGIONAL AVG / SQ" value={USD(a.labor.regional_avg_per_sq)} color="green"/>
          <Kpi label="DAYS" value={a.labor.days_estimated.toFixed(1)} color="green"/>
          <Kpi label="LABOR TOTAL" value={USD(a.labor.labor_total_usd)} color="green"/>
        </div>
      </Frame>

      {/* Wall Envelope + Siding Package */}
      {a.walls && a.siding_package && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Frame color="cyan">
            <h3 className="font-mono text-[10px] tracking-[0.22em] text-cyan-400 mb-3">WALL ENVELOPE · GEOMETRY AGENT</h3>
            <div className="grid grid-cols-2 gap-3">
              <Kpi label="NET WALL SF" value={a.walls.net_wall_sf.toFixed(0)} unit="SIDING TARGET" color="cyan"/>
              <Kpi label="GROSS / FENESTRATION"
                value={`${a.walls.total_gross_wall_sf.toFixed(0)} / ${a.walls.fenestration_subtraction_sf.toFixed(0)}`}
                unit="SF / SF" color="cyan"/>
              <Kpi label="WALL HEIGHT" value={`${a.walls.wall_height_ft.toFixed(1)}'`} unit="EAVE-TO-GRADE" color="cyan"/>
              <Kpi label="ELEVATIONS" value={a.walls.elevations.length} unit="FACADES" color="cyan"/>
            </div>
            <div className="mt-3 space-y-1">
              {a.walls.elevations.map((e) => (
                <div key={e.label} className="flex items-center justify-between font-mono text-[10px] text-slate-300">
                  <span className="text-cyan-400">{e.label}</span>
                  <span>{e.net_sf.toFixed(0)} sf</span>
                  <Pill color={e.moisture_saturation_pct > 25 ? "#FF7B00" : e.moisture_saturation_pct > 12 ? "#FFB020" : "#00FF9C"}>
                    {e.moisture_saturation_pct}% moisture
                  </Pill>
                </div>
              ))}
            </div>
          </Frame>

          <Frame color="amber" className="lg:col-span-2">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-mono text-[10px] tracking-[0.22em] text-amber-400">
                SIDING PACKAGE · {a.siding_package.primary_material.toUpperCase()} · MATERIAL AGENT
              </h3>
              <div className="font-mono text-[10px] text-slate-400 tracking-wide">
                {a.siding_package.profile} · {a.siding_package.color}
              </div>
            </div>
            <table className="w-full font-mono text-[10px]">
              <thead className="text-amber-400">
                <tr>
                  <th className="text-left py-1.5">ACCESSORY</th>
                  <th className="text-right">QTY</th>
                  <th className="text-left">UNIT</th>
                  <th className="text-right">UNIT $</th>
                  <th className="text-right">LINE</th>
                </tr>
              </thead>
              <tbody>
                {a.siding_package.accessories.map((x, i) => (
                  <tr key={i} className="border-t border-white/5">
                    <td className="py-1 text-slate-200">{x.name}</td>
                    <td className="text-right text-white">{x.qty}</td>
                    <td className="text-slate-400">{x.unit}</td>
                    <td className="text-right text-slate-300">{USD(x.unit_cost_usd)}</td>
                    <td className="text-right text-amber-400">{USD(x.line_total_usd)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr><td colSpan="4" className="text-right pt-2 text-slate-400 tracking-widest">SIDING SUBTOTAL</td>
                  <td className="text-right pt-2 text-white font-bold">{USD(a.siding_package.subtotal_usd)}</td></tr>
              </tfoot>
            </table>
          </Frame>
        </div>
      )}

      {/* Wall Moisture / Vapor Barrier — THERMAL AGENT */}
      {a.moisture_vapor && (
        <Frame color="mag">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <div>
              <div className="font-mono text-[9px] text-pink-400 tracking-[0.28em]">// THERMAL AGENT · WALL CAVITY</div>
              <div className="font-mono text-[9px] text-slate-400 tracking-wide mt-2">VAPOR BARRIER</div>
              <div className="text-3xl font-bold text-white mt-0.5">{a.moisture_vapor.vapor_barrier_condition}</div>
              <div className="font-mono text-[9px] text-slate-400 mt-3 tracking-wide">REMEDIATION TOTAL</div>
              <div className="text-2xl font-bold mt-0.5" style={{ color: "#FF2D78", textShadow: "0 0 6px rgba(255,45,120,0.5)" }}>
                {USD(a.moisture_vapor.total_remediation_usd)}
              </div>
            </div>
            <div className="lg:col-span-3">
              <h3 className="font-mono text-[10px] tracking-[0.22em] text-pink-400 mb-3">THERMAL SATURATION ZONES</h3>
              <table className="w-full font-mono text-[10px]">
                <thead className="text-pink-400">
                  <tr>
                    <th className="text-left py-1.5">ID</th>
                    <th className="text-left">ELEV.</th>
                    <th className="text-right">AREA SF</th>
                    <th className="text-right">MOISTURE</th>
                    <th className="text-right">DAMAGE PROB.</th>
                    <th className="text-left">REMEDIATION</th>
                    <th className="text-right">EST.</th>
                  </tr>
                </thead>
                <tbody>
                  {a.moisture_vapor.thermal_saturation_zones.map((z) => (
                    <tr key={z.id} className="border-t border-white/5">
                      <td className="py-1 text-pink-400">{z.id}</td>
                      <td className="text-slate-300">{z.elevation}</td>
                      <td className="text-right text-white">{z.area_sf.toFixed(1)}</td>
                      <td className="text-right">
                        <Pill color={z.moisture_pct > 30 ? "#FF7B00" : z.moisture_pct > 20 ? "#FFB020" : "#00FF9C"}>{z.moisture_pct}%</Pill>
                      </td>
                      <td className="text-right">
                        <Pill color={z.damage_probability_pct > 60 ? "#FF2D78" : z.damage_probability_pct > 40 ? "#FF7B00" : "#FFB020"}>{z.damage_probability_pct}%</Pill>
                      </td>
                      <td className="text-slate-300">{z.remediation_action}</td>
                      <td className="text-right text-amber-400">{USD(z.estimate_usd)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Frame>
      )}

      {/* Energy Leakage Atlas — ENERGY AGENT */}
      {a.energy_leakage && (
        <Frame color="green">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4 mb-4">
            <Kpi label="BLOWER-DOOR ACH₅₀ (EST.)" value={a.energy_leakage.blower_door_ach50_estimated.toFixed(1)} unit="TARGET ≤ 3.0" color="mag"/>
            <Kpi label="ANNUAL kBTU LOSS" value={a.energy_leakage.annual_kbtu_lost_estimated.toLocaleString()} unit="kBTU/YR" color="amber"/>
            <Kpi label="ANNUAL $ LOSS" value={USD(a.energy_leakage.annual_dollar_loss)} unit="/YR" color="green"/>
            <Kpi label="LEAK SOURCES" value={a.energy_leakage.leak_sources.length} unit="IDENTIFIED" color="cyan"/>
          </div>
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-emerald-400 mb-3">LEAK-SOURCE LEDGER · ENERGY AGENT</h3>
          <table className="w-full font-mono text-[10px]">
            <thead className="text-emerald-400">
              <tr>
                <th className="text-left py-1.5">SOURCE</th>
                <th className="text-left">LOCATION</th>
                <th className="text-right">BTU LOSS</th>
                <th className="text-right">$/YR</th>
                <th className="text-left">RECOMMENDED FIX</th>
              </tr>
            </thead>
            <tbody>
              {a.energy_leakage.leak_sources.map((s, i) => (
                <tr key={i} className="border-t border-white/5">
                  <td className="py-1 text-slate-200">{s.label}</td>
                  <td className="text-slate-400">{s.location}</td>
                  <td className="text-right">
                    <Pill color={s.btu_loss_pct > 15 ? "#FF7B00" : s.btu_loss_pct > 10 ? "#FFB020" : "#00FF9C"}>{s.btu_loss_pct}%</Pill>
                  </td>
                  <td className="text-right text-pink-400">${s.annual_dollar_loss.toFixed(0)}/yr</td>
                  <td className="text-slate-300">{s.remediation}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Frame>
      )}

      {/* Expert Agent Chain (manifest) */}
      {a.manifest?.experts_assigned && (
        <Frame color="cyan">
          <h3 className="font-mono text-[10px] tracking-[0.22em] text-cyan-400 mb-3">
            EXPERT AGENT CHAIN · PROJECT MANAGER MANIFEST
          </h3>
          <div className="flex flex-wrap gap-2">
            {a.manifest.experts_assigned.map((id, i) => (
              <div key={id} className="font-mono text-[10px] px-3 py-1.5 rounded border border-cyan-400/40 bg-cyan-400/5 tracking-[0.16em]">
                <span className="text-slate-500 mr-2">{String(i + 1).padStart(2, "0")}</span>
                <span className="text-cyan-400">{id}</span>
              </div>
            ))}
          </div>
        </Frame>
      )}

      {a._fallback && (
        <div className="font-mono text-[10px] text-amber-400 tracking-wide">
          ⓘ Live AI pipeline unavailable; rendered from deterministic Stratex baseline ({a._fallback}).
        </div>
      )}
    </div>
  );
}

function Kpi({ label, value, unit, color = "cyan" }) {
  const c = { cyan: "#00E5FF", amber: "#FFB020", green: "#00FF9C", mag: "#FF2D78" }[color];
  return (
    <div className="rounded p-3" style={{ background: "rgba(15,22,34,0.55)", border: `1px solid ${c}55`, boxShadow: `inset 0 0 18px ${c}10` }}>
      <div className="font-mono text-[8px] tracking-[0.22em] text-slate-400">{label}</div>
      <div className="text-2xl font-bold text-white mt-1 leading-none" style={{ color: c, textShadow: `0 0 6px ${c}66` }}>{value}</div>
      {unit && <div className="font-mono text-[8px] text-slate-500 mt-1 tracking-wide">{unit}</div>}
    </div>
  );
}
