import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import { getProject } from "@/lib/api";
import { ASSETS } from "@/lib/constants";
import { Activity, Cpu, Crosshair, Gavel, Radar, AlertTriangle, MapPin, Box, ArrowLeft } from "lucide-react";

const sev_color = (s) => s === "CRITICAL" ? "text-plasma glow-orange" : s === "HIGH" ? "text-plasma" : s === "MED" ? "text-teal" : "text-volt";
const sev_led   = (s) => s === "CRITICAL" || s === "HIGH" ? "led-alert pulse-alert" : s === "MED" ? "led-teal" : "led-ok";

export default function MissionDashboard() {
  const { id } = useParams();
  const [project, setProject] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let mounted = true;
    getProject(id).then((p)=>{ if (mounted) setProject(p); }).catch((e)=>setErr(e.message));
    return ()=>{ mounted = false; };
  }, [id]);

  if (err) return <div data-testid="mission-error" className="p-10 text-plasma">{err}</div>;
  if (!project) return <div data-testid="mission-loading" className="p-10 text-muted-hud font-mono uppercase tracking-widest">Loading mission telemetry…</div>;

  const tele = project.roof_telemetry || {};
  const pricing = project.pricing || {};
  const mission = project.mission || {};
  const anomalies = mission.anomalies || [];
  const agents = project.agent_reports || {};

  return (
    <div data-testid="mission-dashboard" className="px-6 md:px-12 py-10 max-w-[1600px] mx-auto">
      {/* HEADER */}
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <Link to="/projects" className="font-mono text-[11px] uppercase tracking-widest text-muted-hud flex items-center gap-1 mb-2 hover:text-teal" data-testid="back-to-projects">
            <ArrowLeft size={12}/> Project Ledger
          </Link>
          <div className="font-mono text-[11px] tracking-[0.32em] text-teal uppercase">// MISSION COMPLETE • {project.id.slice(0,8)}</div>
          <h1 className="font-display text-3xl md:text-4xl uppercase tracking-[0.14em] text-silver">{project.intake?.customer_name}</h1>
          <div className="font-mono text-sm text-muted-hud flex items-center gap-2 mt-1"><MapPin size={12}/> {project.intake?.property_address}</div>
        </div>
        <div className="flex gap-2 items-center">
          <span className="led led-ok pulse-glow"/>
          <span className="font-mono text-[11px] uppercase tracking-widest text-volt">RECON COMPLETE</span>
        </div>
      </div>

      {/* TOP GRID */}
      <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6 mb-6">
        {/* 3D WIREFRAME PLACEHOLDER */}
        <HudCard scanline className="p-4 min-h-[420px] relative">
          <div className="font-mono text-[11px] tracking-widest uppercase text-muted-hud mb-3 flex items-center gap-2"><Box size={14}/> STRATEX Vision™ — Photogrammetry Mesh</div>
          <div className="relative">
            <img src={ASSETS.dashboard_montage} alt="3D wireframe" className="w-full h-auto opacity-90"/>
            <div className="absolute inset-0 grid-floor opacity-10 pointer-events-none"/>
          </div>
          <div className="absolute bottom-4 left-4 right-4 flex flex-wrap gap-4 bg-[#06080B]/85 border border-[#00F0FF]/30 p-3">
            <DataReadout label="Total SF" value={tele.total_sf} testid="tele-sf"/>
            <DataReadout label="Squares" value={tele.squares} testid="tele-sq"/>
            <DataReadout label="Pitch" value={tele.pitch} testid="tele-pitch"/>
            <DataReadout label="Ridge LF" value={tele.ridge_lf} testid="tele-ridge"/>
            <DataReadout label="Eaves LF" value={tele.eaves_lf} testid="tele-eaves"/>
            <DataReadout label="Valleys LF" value={tele.valleys_lf} accent="orange" testid="tele-valleys"/>
          </div>
        </HudCard>

        {/* AGENTS */}
        <div className="space-y-4">
          <AgentPanel icon={Crosshair} title="Forensic Diagnostic Agent" body={agents.forensic} testid="agent-forensic"/>
          <AgentPanel icon={Activity} title="Evidentiary Validation Agent" body={agents.validation} testid="agent-validation"/>
          <AgentPanel icon={Cpu} title="Reconciliation Engine" body={agents.reconciliation} testid="agent-reconciliation"/>
          <AgentPanel icon={Gavel} title="Jurisprudential Code Agent" body={agents.jurisprudential} testid="agent-jurisprudential"/>
        </div>
      </div>

      {/* ANOMALY GRID */}
      <HudCard scanline className="p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-teal font-mono text-[11px] tracking-widest uppercase"><AlertTriangle size={14}/> Thermal Anomaly Field</div>
          <div className="font-mono text-[11px] text-muted-hud uppercase tracking-widest">{anomalies.length} detected • {mission.critical_count} critical</div>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3" data-testid="anomalies-grid">
          {anomalies.map((a)=>(
            <div key={a.id} className={`hud-card ${a.severity==="HIGH" || a.severity==="CRITICAL" ? "hud-card-alert" : ""} p-4`}>
              <span className="corner-bl"/><span className="corner-br"/>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[11px] tracking-widest text-muted-hud">{a.id}</span>
                <span className={`led ${sev_led(a.severity)}`}/>
              </div>
              <div className="font-display text-lg uppercase tracking-widest text-silver">{a.type}</div>
              <div className="font-mono text-[11px] text-muted-hud mt-2 grid grid-cols-2 gap-1">
                <span>Δ {a.thermal_delta}</span>
                <span className={sev_color(a.severity)}>{a.severity}</span>
                <span>conf {(a.confidence*100).toFixed(1)}%</span>
                <span>{a.lat.toFixed(4)},{a.lon.toFixed(4)}</span>
              </div>
            </div>
          ))}
        </div>
      </HudCard>

      {/* PRICING SUMMARY */}
      <HudCard scanline className="p-6 mb-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2 text-teal font-mono text-[11px] tracking-widest uppercase"><Radar size={14}/> STRATEX Quant™ — Locked Estimate</div>
          <div data-testid="mission-pricing-lock" className="font-mono text-[11px] text-plasma uppercase tracking-widest">{pricing.lock_mode}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="hud-table">
            <thead><tr><th>Line Item</th><th>Qty</th><th>Unit</th><th>Unit $</th><th>Total</th><th>Xactimate</th></tr></thead>
            <tbody>
              {(pricing.line_items||[]).map((li, i)=>(
                <tr key={i}>
                  <td className="text-silver">{li.description}</td>
                  <td>{li.qty}</td>
                  <td className="text-muted-hud">{li.unit}</td>
                  <td>${li.unit_price.toFixed(2)}</td>
                  <td className="text-teal">${li.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td>
                  <td><span className="tag-pill">{li.xactimate_tag}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="hud-divider my-4"/>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <DataReadout label="Subtotal" value={`$${(pricing.subtotal||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-subtotal"/>
          <DataReadout label={`Overhead ${(pricing.overhead_rate*100).toFixed(0)}%`} value={`$${(pricing.overhead||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-overhead"/>
          <DataReadout label={`Profit ${(pricing.profit_rate*100).toFixed(0)}%`} value={`$${(pricing.profit||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-profit"/>
          <DataReadout label="Final Total" accent="orange" value={`$${(pricing.final_total||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-final"/>
        </div>
      </HudCard>
    </div>
  );
}

function AgentPanel({ icon: Icon, title, body, testid }) {
  return (
    <div data-testid={testid} className="border-l-2 border-[#00F0FF] pl-4 py-3 bg-gradient-to-r from-[#00F0FF]/5 to-transparent">
      <div className="flex items-center gap-2 mb-1 text-teal">
        <Icon size={14} strokeWidth={1.5}/>
        <span className="font-mono text-[10px] uppercase tracking-[0.26em]">{title}</span>
      </div>
      <p className="text-sm text-silver font-body leading-relaxed">{body || "—"}</p>
    </div>
  );
}
