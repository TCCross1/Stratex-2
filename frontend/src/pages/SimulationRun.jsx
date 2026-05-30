/**
 * /simulation/:jobId · /simulation/demo
 *
 * John's full simulated flight journey — 7 cinematic stages:
 *   1. Launch        — 6 pre-flight checks turn nominal
 *   2. Capture       — frames stream (animated counter)
 *   3. Transfer      — bandwidth + sha-fingerprint sweep
 *   4. AI Agents     — 4 Claude Haiku 4.5 verdicts (parallel, ~5s)
 *   5. Validation    — 100 deterministic checks tick through
 *   6. 3D Twin       — facet table + twin reference image
 *   7. Pricing       — total + CTA → /contractor/deliverable/:jobId
 *
 * Backend (POST /api/simulation/run) returns the entire result in one shot;
 * the page paces it visually so the journey feels real.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Rocket, Camera, Database, Brain, CheckCircle2, XCircle, Box, DollarSign,
  ChevronRight, Loader2, Plane, ShieldCheck, Battery, Satellite, RadioTower,
  CloudRain, Users, Sparkles, FileText, ArrowRight,
} from "lucide-react";
import { api } from "@/lib/api";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";
const INK = "#0B0F19";

const USD = (n) => Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const STAGES = [
  { key: "launch",     label: "Launch Authorization", icon: Rocket,        durationMs: 3500 },
  { key: "capture",    label: "Aerial Capture",       icon: Camera,        durationMs: 3500 },
  { key: "transfer",   label: "Data Transfer",        icon: Database,      durationMs: 2500 },
  { key: "agents",     label: "4-Agent Forensic Pipeline", icon: Brain,    durationMs: 0 },     // waits on API
  { key: "validation", label: "100-Check Validation", icon: CheckCircle2,  durationMs: 4500 },
  { key: "twin",       label: "3D Digital Twin",      icon: Box,           durationMs: 2200 },
  { key: "pricing",    label: "Estimation Pipeline",  icon: DollarSign,    durationMs: 0 },
];

export default function SimulationRun() {
  const { jobId } = useParams();
  const effectiveJobId = jobId || "crown-demo";

  const [stageIdx, setStageIdx] = useState(0);
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [agentSpinIdx, setAgentSpinIdx] = useState(0);   // which agent is currently "running" visually
  const [checkIdx, setCheckIdx] = useState(0);            // 100-check progress
  const [launchChecks, setLaunchChecks] = useState({ hatch: false, battery: 0, rtk: false, uplink: false, weather: false, perimeter: false });
  const [framesCaptured, setFramesCaptured] = useState(0);
  const [transferMb, setTransferMb] = useState(0);
  const apiStartedRef = useRef(false);

  // Kick off the API call immediately on mount (parallel to the visual stage animation).
  useEffect(() => {
    if (apiStartedRef.current) return;
    apiStartedRef.current = true;
    (async () => {
      try {
        const r = await api.post(`/simulation/run?job_id=${encodeURIComponent(effectiveJobId)}`);
        setData(r.data);
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message);
      }
    })();
  }, [effectiveJobId]);

  // ---- Stage 1 (Launch) animation — 6 checks ramp green ----
  useEffect(() => {
    if (stageIdx !== 0) return;
    const tasks = [
      [400,  () => setLaunchChecks((s) => ({ ...s, perimeter: true }))],
      [800,  () => setLaunchChecks((s) => ({ ...s, weather: true }))],
      [1200, () => setLaunchChecks((s) => ({ ...s, rtk: true }))],
      [1700, () => setLaunchChecks((s) => ({ ...s, uplink: true }))],
      [2400, () => setLaunchChecks((s) => ({ ...s, hatch: true }))],
    ];
    const timers = tasks.map(([ms, fn]) => setTimeout(fn, ms));
    // Battery ramps 72→100
    const battTimer = setInterval(() => {
      setLaunchChecks((s) => {
        if (s.battery >= 100) return s;
        return { ...s, battery: Math.min(100, s.battery + 2) };
      });
    }, 60);
    const next = setTimeout(() => setStageIdx(1), STAGES[0].durationMs);
    return () => { timers.forEach(clearTimeout); clearInterval(battTimer); clearTimeout(next); };
  }, [stageIdx]);

  // ---- Stage 2 (Capture) — frame counter to 1284 ----
  useEffect(() => {
    if (stageIdx !== 1) return;
    const targetFrames = data?.flight?.telemetry?.frames_captured || 1284;
    const step = Math.max(8, Math.floor(targetFrames / 40));
    const t = setInterval(() => setFramesCaptured((n) => Math.min(targetFrames, n + step)), 70);
    const next = setTimeout(() => { setFramesCaptured(targetFrames); setStageIdx(2); }, STAGES[1].durationMs);
    return () => { clearInterval(t); clearTimeout(next); };
  }, [stageIdx, data]);

  // ---- Stage 3 (Transfer) — Mb counter sweeps to ~6800 ----
  useEffect(() => {
    if (stageIdx !== 2) return;
    const t = setInterval(() => setTransferMb((n) => Math.min(6824, n + 280)), 90);
    const next = setTimeout(() => { setTransferMb(6824); setStageIdx(3); }, STAGES[2].durationMs);
    return () => { clearInterval(t); clearTimeout(next); };
  }, [stageIdx]);

  // ---- Stage 4 (Agents) — wait for API, then animate verdicts in one at a time ----
  useEffect(() => {
    if (stageIdx !== 3) return;
    if (!data) return; // still loading
    let i = 0;
    setAgentSpinIdx(0);
    const t = setInterval(() => {
      i += 1;
      if (i >= 4) { clearInterval(t); setTimeout(() => setStageIdx(4), 600); }
      setAgentSpinIdx(i);
    }, 700);
    return () => clearInterval(t);
  }, [stageIdx, data]);

  // ---- Stage 5 (Validation) — 100-check ticker ----
  useEffect(() => {
    if (stageIdx !== 4) return;
    const total = 100;
    const step = 2;
    const t = setInterval(() => {
      setCheckIdx((n) => {
        const next = Math.min(total, n + step);
        if (next >= total) { clearInterval(t); setTimeout(() => setStageIdx(5), 500); }
        return next;
      });
    }, 80);
    return () => clearInterval(t);
  }, [stageIdx]);

  // ---- Stage 6 (Twin) — just a pause ----
  useEffect(() => {
    if (stageIdx !== 5) return;
    const next = setTimeout(() => setStageIdx(6), STAGES[5].durationMs);
    return () => clearTimeout(next);
  }, [stageIdx]);

  const isComplete = stageIdx >= 6;

  return (
    <div className="min-h-screen text-silver" style={{ background: INK }} data-testid="simulation-root">
      <div className="max-w-[1200px] mx-auto px-6 md:px-10 py-8">
        <Header data={data}/>
        <StageRail current={stageIdx}/>
        {err && <ErrPanel err={err}/>}

        <main className="mt-8 space-y-6">
          <StageLaunch active={stageIdx === 0} done={stageIdx > 0} checks={launchChecks}/>
          <StageCapture active={stageIdx === 1} done={stageIdx > 1} frames={framesCaptured}/>
          <StageTransfer active={stageIdx === 2} done={stageIdx > 2} mb={transferMb}/>
          <StageAgents active={stageIdx === 3} done={stageIdx > 3} data={data} spinIdx={agentSpinIdx}/>
          <StageValidation active={stageIdx === 4} done={stageIdx > 4} data={data} checkIdx={checkIdx}/>
          <StageTwin active={stageIdx === 5} done={stageIdx > 5} data={data}/>
          <StagePricing active={isComplete} done={isComplete} data={data} jobId={effectiveJobId}/>
        </main>
      </div>
    </div>
  );
}

/* -------------------- top header -------------------- */
function Header({ data }) {
  return (
    <header className="mb-6">
      <div className="flex items-center gap-2 mb-1">
        <span className="led led-teal"/>
        <div className="font-mono text-[11px] uppercase tracking-[0.36em]" style={{ color: TEAL }}>
          // STRATEX™ SIMULATION · END-TO-END JOURNEY
        </div>
      </div>
      <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">
        From Authorize-Launch to Estimate · Live
      </h1>
      <p className="font-body text-sm text-muted-hud max-w-3xl">
        {data?.flight?.project_code && (
          <span className="font-mono mr-3" style={{ color: TEAL }}>
            {data.flight.project_code}
          </span>
        )}
        {data?.client?.contractor_company && `${data.client.contractor_company} · `}
        {data?.client?.name && `for ${data.client.name} · `}
        {data?.flight?.site_address}
      </p>
    </header>
  );
}

/* -------------------- horizontal stage rail -------------------- */
function StageRail({ current }) {
  return (
    <ol className="grid grid-cols-7 gap-2" data-testid="simulation-rail">
      {STAGES.map((s, i) => {
        const done = i < current;
        const active = i === current;
        const Icon = s.icon;
        const color = done ? TEAL : active ? ORANGE : NICKEL;
        return (
          <li key={s.key} className="flex flex-col items-center text-center" data-testid={`rail-${s.key}`}>
            <span
              className="w-9 h-9 rounded-full inline-flex items-center justify-center mb-1.5"
              style={{
                background: done ? `${TEAL}1A` : active ? `${ORANGE}1A` : "transparent",
                border: `1px solid ${color}`,
                color,
                boxShadow: active ? `0 0 18px ${ORANGE}66` : done ? `0 0 8px ${TEAL}33` : "none",
              }}
            >
              {active && !done ? <Loader2 size={14} className="animate-spin"/> : <Icon size={14}/>}
            </span>
            <div className="text-[9px] uppercase tracking-widest font-mono leading-tight" style={{ color }}>
              {i + 1} · {s.label.split(" ").slice(0, 2).join(" ")}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/* -------------------- stage card shell -------------------- */
function StageCard({ active, done, idx, title, icon: Icon, children, testid }) {
  return (
    <section
      data-testid={testid}
      className="border-l-4"
      style={{
        borderLeftColor: done ? TEAL : active ? ORANGE : NICKEL,
        background: done ? "rgba(0,245,212,0.03)" : active ? "rgba(255,84,0,0.05)" : "rgba(58,67,80,0.04)",
        borderTop: `1px solid ${NICKEL}`, borderRight: `1px solid ${NICKEL}`, borderBottom: `1px solid ${NICKEL}`,
        opacity: active || done ? 1 : 0.45,
        transition: "opacity .4s",
      }}
    >
      <header className="flex items-center gap-3 px-4 py-3 border-b" style={{ borderColor: NICKEL }}>
        <Icon size={16} style={{ color: done ? TEAL : ORANGE }}/>
        <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: done ? TEAL : ORANGE }}>
          STAGE {idx} · {title}
        </span>
        {done && <span className="ml-auto font-mono text-[10px] uppercase tracking-widest" style={{ color: TEAL }}>● COMPLETE</span>}
      </header>
      <div className="px-4 py-4">{children}</div>
    </section>
  );
}

/* -------------------- stage panels -------------------- */
function StageLaunch({ active, done, checks }) {
  const rows = [
    { k: "hatch",     label: "Trailer Hatch",       ok: checks.hatch,     value: checks.hatch ? "Retracted" : "Locked", icon: ShieldCheck },
    { k: "battery",   label: "Drone Battery",       ok: checks.battery >= 100, value: `${checks.battery}%`,         icon: Battery },
    { k: "rtk",       label: "RTK GPS",             ok: checks.rtk,       value: checks.rtk ? "cm-Locked" : "Acquiring", icon: Satellite },
    { k: "uplink",    label: "Comm Uplink",         ok: checks.uplink,    value: checks.uplink ? "Strong · 92 dBm" : "Attenuated", icon: RadioTower },
    { k: "weather",   label: "Weather Envelope",    ok: checks.weather,   value: checks.weather ? "Optimal" : "Holding", icon: CloudRain },
    { k: "perimeter", label: "Perimeter / Personnel", ok: checks.perimeter, value: checks.perimeter ? "Clear" : "Alert", icon: Users },
  ];
  return (
    <StageCard active={active} done={done} idx="1" title="Launch Authorization" icon={Rocket} testid="stage-launch">
      <ul className="grid md:grid-cols-2 gap-2">
        {rows.map((r) => {
          const Icon = r.icon;
          return (
            <li key={r.k} className="flex items-center justify-between px-3 py-2 border" style={{ borderColor: NICKEL, background: r.ok ? "rgba(0,245,212,0.07)" : "rgba(58,67,80,0.05)" }}>
              <span className="flex items-center gap-2"><Icon size={13} style={{ color: r.ok ? TEAL : NICKEL }}/><span className="text-[12px]">{r.label}</span></span>
              <span className="font-mono text-[11px]" style={{ color: r.ok ? TEAL : "#7A8699" }}>{r.value}</span>
            </li>
          );
        })}
      </ul>
      <div className="mt-3 font-mono text-[10px] uppercase tracking-widest" style={{ color: done ? TEAL : ORANGE }}>
        {done ? "→ AUTHORIZE_FLEET_LAUNCH emitted" : "// arming pre-flight checks…"}
      </div>
    </StageCard>
  );
}

function StageCapture({ active, done, frames }) {
  return (
    <StageCard active={active} done={done} idx="2" title="Aerial Capture · 4 passes" icon={Camera} testid="stage-capture">
      <div className="grid md:grid-cols-3 gap-3">
        <Stat label="Frames Captured" value={frames.toLocaleString()} accent={TEAL}/>
        <Stat label="Altitude (avg)" value="124 ft" accent={TEAL}/>
        <Stat label="Ground Speed (avg)" value="7.4 mph" accent={TEAL}/>
      </div>
      <div className="mt-3 h-2 w-full" style={{ background: "#0F1620", border: `1px solid ${NICKEL}` }}>
        <div style={{ width: `${Math.min(100, (frames / 1284) * 100)}%`, height: "100%", background: TEAL, transition: "width .15s" }}/>
      </div>
    </StageCard>
  );
}

function StageTransfer({ active, done, mb }) {
  return (
    <StageCard active={active} done={done} idx="3" title="Data Transfer · Edge → Cloud" icon={Database} testid="stage-transfer">
      <div className="grid md:grid-cols-3 gap-3">
        <Stat label="Payload Transferred" value={`${mb.toLocaleString()} MB`} accent={TEAL}/>
        <Stat label="Throughput (avg)" value="285 Mbps" accent={TEAL}/>
        <Stat label="Integrity" value="SHA-256 ✓" accent={TEAL}/>
      </div>
      <div className="mt-3 font-mono text-[10px] uppercase tracking-widest" style={{ color: done ? TEAL : ORANGE }}>
        {done ? "→ payload sealed · cv pipeline armed" : "// streaming radiometric frames…"}
      </div>
    </StageCard>
  );
}

function StageAgents({ active, done, data, spinIdx }) {
  const verdicts = data?.agents?.verdicts || [];
  const names = ["perception", "measurement", "forensics", "pricing"];
  return (
    <StageCard active={active} done={done} idx="4" title="4-Agent Forensic Pipeline · Claude Haiku 4.5" icon={Brain} testid="stage-agents">
      <div className="grid md:grid-cols-2 gap-3" data-testid="agents-grid">
        {names.map((n, i) => {
          const v = verdicts.find((x) => x.agent === n);
          const hasVerdict = !!v && (done || i < spinIdx);
          return (
            <div key={n} className="border p-3" style={{ borderColor: hasVerdict ? `${TEAL}66` : NICKEL, background: "#0F1620" }} data-testid={`agent-${n}`}>
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] uppercase tracking-widest" style={{ color: TEAL }}>
                  Agent · {n}
                </span>
                {hasVerdict ? (
                  <span className="font-mono text-[10px] px-2 py-0.5 border uppercase tracking-widest" style={{ color: TEAL, borderColor: TEAL }}>
                    {String(v.verdict).slice(0, 12)} · {v.confidence_pct}%
                  </span>
                ) : (
                  <Loader2 size={12} className="animate-spin" style={{ color: ORANGE }}/>
                )}
              </div>
              <p className="text-[12px] leading-relaxed text-silver">
                {hasVerdict ? (v.narrative || "—") : "// querying agent…"}
              </p>
              {hasVerdict && Array.isArray(v.findings) && v.findings.length > 0 && (
                <ul className="mt-2 space-y-0.5">
                  {v.findings.slice(0, 3).map((f, k) => {
                    const text = typeof f === "string"
                      ? f
                      : (f && (f.detail || f.check || f.result))
                        ? `${f.check || f.result || ""}${f.detail ? ` — ${f.detail}` : ""}`.trim()
                        : JSON.stringify(f);
                    return (
                      <li key={k} className="font-mono text-[10.5px] text-muted-hud flex gap-1"><span style={{ color: TEAL }}>›</span>{text}</li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
      {data?.agents?.elapsed_ms && (
        <div className="mt-3 font-mono text-[10px] uppercase tracking-widest text-muted-hud">
          parallel fan-out · {(data.agents.elapsed_ms / 1000).toFixed(2)}s wall-time
        </div>
      )}
    </StageCard>
  );
}

function StageValidation({ active, done, data, checkIdx }) {
  const items = data?.checks?.items || [];
  const visible = items.slice(Math.max(0, checkIdx - 6), checkIdx);
  return (
    <StageCard active={active} done={done} idx="5" title="100-Check Deterministic Validation" icon={CheckCircle2} testid="stage-validation">
      <div className="grid md:grid-cols-3 gap-3 mb-3">
        <Stat label="Checks Run" value={`${checkIdx} / 100`} accent={TEAL}/>
        <Stat label="Passed" value={done ? data?.checks?.passed ?? checkIdx : checkIdx} accent={TEAL}/>
        <Stat label="Categories" value="5" accent={TEAL}/>
      </div>
      <div className="h-2 w-full mb-3" style={{ background: "#0F1620", border: `1px solid ${NICKEL}` }}>
        <div style={{ width: `${checkIdx}%`, height: "100%", background: TEAL, transition: "width .15s" }}/>
      </div>
      <div className="font-mono text-[10.5px] space-y-0.5 max-h-32 overflow-hidden" data-testid="validation-stream">
        {visible.map((c) => (
          <div key={c["#"]} className="flex gap-3">
            <span style={{ color: c.passed ? TEAL : ORANGE, width: 50 }}>
              {c.passed ? "[PASS]" : "[FAIL]"}
            </span>
            <span className="text-muted-hud" style={{ width: 110 }}>#{c["#"]} {c.category}</span>
            <span className="text-silver flex-1 truncate">{c.name}</span>
          </div>
        ))}
      </div>
    </StageCard>
  );
}

function StageTwin({ active, done, data }) {
  const t = data?.twin || {};
  return (
    <StageCard active={active} done={done} idx="6" title="3D Digital Twin · Forensic Overlay" icon={Box} testid="stage-twin">
      <div className="grid md:grid-cols-[1fr_1.3fr] gap-3">
        <div className="border" style={{ borderColor: NICKEL }}>
          <table className="w-full text-[11px]">
            <thead><tr style={{ background: "#0F1620", color: TEAL }}>
              <th className="px-2 py-1.5 text-left font-mono uppercase tracking-widest">Facet</th>
              <th className="px-2 py-1.5 text-right font-mono uppercase tracking-widest">sqft</th>
              <th className="px-2 py-1.5 text-right font-mono uppercase tracking-widest">pitch</th>
            </tr></thead>
            <tbody>
              {(t.facets || []).map((f) => (
                <tr key={f.id} className="border-t" style={{ borderColor: NICKEL }}>
                  <td className="px-2 py-1.5 font-mono">{f.id} · {f.label}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{f.sqft}</td>
                  <td className="px-2 py-1.5 text-right font-mono">{f.pitch}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {t.reference_url && (
          <div className="border" style={{ borderColor: NICKEL }}>
            <img src={t.reference_url} alt="3D Twin" className="block w-full h-auto"/>
            <div className="px-3 py-1.5 font-mono text-[9.5px] uppercase tracking-widest" style={{ color: TEAL, background: "#0F1620" }}>
              3D Twin · canonical AD-KY041 forensic overlay
            </div>
          </div>
        )}
      </div>
    </StageCard>
  );
}

function StagePricing({ active, done, data, jobId }) {
  const p = data?.pricing || {};
  return (
    <StageCard active={active} done={done} idx="7" title="Estimation Pipeline · Final" icon={DollarSign} testid="stage-pricing">
      <div className="grid md:grid-cols-4 gap-3 mb-4">
        <Stat label="Subtotal"  value={USD(p.subtotal_usd)} accent={TEAL}/>
        <Stat label="Overhead"  value={USD(p.overhead_usd)} accent={TEAL}/>
        <Stat label="Margin"    value={USD(p.margin_usd)}   accent={TEAL}/>
        <Stat label="Total · Estimate" value={USD(p.total_usd)} accent={ORANGE} big/>
      </div>
      {active && (
        <div className="border-l-4 p-4" style={{ borderLeftColor: TEAL, background: "rgba(0,245,212,0.06)", borderColor: NICKEL }}>
          <div className="flex items-start gap-3">
            <Sparkles size={20} style={{ color: TEAL }} className="flex-shrink-0 mt-0.5"/>
            <div className="flex-1">
              <div className="font-mono text-[10px] uppercase tracking-[0.28em] mb-1" style={{ color: TEAL }}>
                // SIMULATION COMPLETE
              </div>
              <p className="text-[13px] leading-relaxed text-silver mb-3">
                Every stage executed cleanly. {data?.checks?.passed || 100} of {data?.checks?.total || 100} validation
                checks passed across geometric, thermal, photogrammetric, forensic, and pricing categories. The
                deliverable packet is ready to hand to the homeowner.
              </p>
              <Link
                to={`/contractor/deliverable/${jobId}`}
                data-testid="cta-view-deliverable"
                className="inline-flex items-center gap-2 px-4 py-2 font-mono text-[11px] uppercase tracking-[0.22em]"
                style={{ background: TEAL, color: INK, boxShadow: `0 0 18px ${TEAL}55` }}
              >
                <FileText size={13}/> View Contractor Deliverable Packet
                <ArrowRight size={13}/>
              </Link>
            </div>
          </div>
        </div>
      )}
    </StageCard>
  );
}

function Stat({ label, value, accent, big }) {
  return (
    <div className="border p-3" style={{ borderColor: `${accent}55`, background: `${accent}0C` }}>
      <div className="font-mono text-[9.5px] uppercase tracking-[0.22em]" style={{ color: accent }}>{label}</div>
      <div className={`font-display ${big ? "text-2xl" : "text-lg"} mt-1 text-silver`}>{value}</div>
    </div>
  );
}

function ErrPanel({ err }) {
  return (
    <div className="mt-4 border p-3 font-mono text-[10.5px] uppercase tracking-widest"
         style={{ borderColor: ORANGE, background: "rgba(255,84,0,0.08)", color: ORANGE }}>
      // SIMULATION ERROR · {String(err).slice(0, 220)}
    </div>
  );
}
