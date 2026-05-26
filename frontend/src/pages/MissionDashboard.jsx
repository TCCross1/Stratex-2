import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ForensicOverlay, { AnomalySelector } from "@/components/ForensicOverlay";
import useIsMobile from "@/hooks/use-is-mobile";
import { getProject, pdfUrl, computePricing } from "@/lib/api";
import { Activity, Cpu, Crosshair, Gavel, Radar, MapPin, ArrowLeft, Download, Box, FileText, Thermometer, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

export default function MissionDashboard() {
  const { id } = useParams();
  const isMobile = useIsMobile(900);
  const [project, setProject] = useState(null);
  const [err, setErr] = useState(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [mobileTab, setMobileTab] = useState("model"); // model | forensic | anomalies | quant | pricing

  useEffect(() => {
    let mounted = true;
    getProject(id).then(async (p)=>{
      if (!mounted) return;
      if (!p.pricing) {
        try { p = { ...p, pricing: await computePricing(id) }; } catch (_) {}
      }
      setProject(p);
      const ans = p?.mission?.anomalies || p?.scan?.anomalies || [];
      if (ans.length > 0) setSelectedAnomaly(ans[0]);
    }).catch((e)=>setErr(e.message));
    return ()=>{ mounted = false; };
  }, [id]);

  if (err) return <div data-testid="mission-error" className="p-10 text-plasma">{err}</div>;
  if (!project) return <div data-testid="mission-loading" className="p-10 text-muted-hud font-mono uppercase tracking-widest">Loading mission telemetry…</div>;

  const tele = project.roof_telemetry || {};
  const totals = tele.totals || {};
  const pricing = project.pricing || {};
  const mission = project.mission || {};
  const anomalies = mission.anomalies || project.scan?.anomalies || [];
  const agents = project.agent_reports || {};

  const handlePDF = () => {
    window.open(pdfUrl(project.id), "_blank");
    toast.success("Supplement packet generated");
  };

  return (
    <div data-testid="mission-dashboard" className="px-4 md:px-12 py-6 md:py-10 max-w-[1800px] mx-auto">
      {/* HEADER */}
      <div className="flex flex-wrap items-end justify-between gap-3 mb-5 md:mb-6">
        <div className="min-w-0">
          <Link to="/projects" className="font-mono text-[11px] uppercase tracking-widest text-muted-hud flex items-center gap-1 mb-2 hover:text-teal" data-testid="back-to-projects">
            <ArrowLeft size={12}/> Project Ledger
          </Link>
          <div className="font-mono text-[10px] md:text-[11px] tracking-[0.32em] text-teal uppercase">// STRATEX VISION™ • ADVANCED DIAGNOSTICS</div>
          <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.12em] md:tracking-[0.14em] text-silver truncate">Project {project.id.slice(0,8).toUpperCase()}</h1>
          <div className="font-mono text-xs md:text-sm text-muted-hud flex items-center gap-2 mt-1 truncate"><MapPin size={12}/> {project.intake?.customer_name} • {project.intake?.property_address}</div>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <span className="led led-ok pulse-glow"/>
          <span className="font-mono text-[11px] uppercase tracking-widest text-volt mr-2 md:mr-3">RECON COMPLETE</span>
          <button onClick={handlePDF} className="btn-hud" data-testid="download-pdf-btn">
            <Download size={14}/> <span className="hidden sm:inline">Adjuster Supplement (PDF)</span><span className="sm:hidden">PDF</span>
          </button>
        </div>
      </div>

      {/* DIAGNOSTIC HERO: 3-column desktop, tabs on mobile */}
      {isMobile ? (
        <HudCard scanline className="p-3 mb-6">
          <MobileTabs tab={mobileTab} setTab={setMobileTab} anomaliesCount={anomalies.length}/>
          <div key={mobileTab} className="anim-fade-up">
          {mobileTab === "model" && (
            <div className="hud-card overflow-hidden mt-3">
              <span className="corner-bl"/><span className="corner-br"/>
              <RoofModel3D
                telemetry={tele}
                anomalies={anomalies}
                highlightAnomalyId={selectedAnomaly?.id}
                onSelectAnomaly={(a) => { setSelectedAnomaly(a); setMobileTab("forensic"); try{navigator.vibrate?.(10);}catch(_){} }}
                height={380}
                showLabels={false}
              />
            </div>
          )}
          {mobileTab === "quant" && (
            <div className="mt-3 space-y-3">
              <HudCard className="p-4">
                <div className="flex items-center gap-2 mb-2 text-teal"><Box size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">Project</span></div>
                <div className="font-display text-base uppercase text-silver tracking-widest">{project.intake?.customer_name}</div>
                <div className="font-mono text-[11px] text-muted-hud mt-1">{project.intake?.insurance_carrier} • {project.intake?.project_type}</div>
                <div className="font-mono text-[11px] text-muted-hud">{project.intake?.property_address}</div>
              </HudCard>
              <HudCard className="p-4" data-testid="quant-estimation-card">
                <div className="flex items-center gap-2 mb-3 text-teal"><Radar size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">STRATEX Quant™ Estimation</span></div>
                <QuantRows totals={totals} tele={tele}/>
              </HudCard>
              <HudCard className="p-4">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2 flex items-center gap-2"><FileText size={12}/> Caliper Result</div>
                <div className="font-heading text-silver">Layers: <span className="text-teal font-mono">{project.caliper?.layers_detected || 1}</span></div>
                <div className={`font-display text-sm uppercase tracking-widest mt-1 ${project.caliper?.scope_determined === "Complete Tear-Off Required" ? "text-plasma glow-orange" : "text-volt glow-volt"}`}>
                  {project.caliper?.scope_determined || "Overlay Permitted"}
                </div>
              </HudCard>
            </div>
          )}
          {mobileTab === "forensic" && (
            <div className="mt-3">
              <ForensicOverlay anomaly={selectedAnomaly} projectId={project.id}/>
            </div>
          )}
          {mobileTab === "anomalies" && (
            <div className="mt-3">
              <HudCard className="p-3">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Anomaly Field</div>
                <AnomalySelector
                  anomalies={anomalies}
                  selectedId={selectedAnomaly?.id}
                  onSelect={(a) => { setSelectedAnomaly(a); setMobileTab("forensic"); try{navigator.vibrate?.(8);}catch(_){} }}
                />
              </HudCard>
            </div>
          )}
          </div>
        </HudCard>
      ) : (
        <HudCard scanline className="p-3 mb-6">
          <div className="grid lg:grid-cols-[260px_1fr_310px] gap-3">
            {/* LEFT RAIL — project meta + Quant estimation */}
            <div className="space-y-3">
              <HudCard className="p-4">
                <div className="flex items-center gap-2 mb-2 text-teal"><Box size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">Project</span></div>
                <div className="font-display text-base uppercase text-silver tracking-widest">{project.intake?.customer_name}</div>
                <div className="font-mono text-[11px] text-muted-hud mt-1">{project.intake?.insurance_carrier} • {project.intake?.project_type}</div>
                <div className="font-mono text-[11px] text-muted-hud">{project.intake?.property_address}</div>
              </HudCard>
              <HudCard className="p-4" data-testid="quant-estimation-card">
                <div className="flex items-center gap-2 mb-3 text-teal"><Radar size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">STRATEX Quant™ Estimation</span></div>
                <QuantRows totals={totals} tele={tele}/>
              </HudCard>
              <HudCard className="p-4">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2 flex items-center gap-2"><FileText size={12}/> Caliper Result</div>
                <div className="font-heading text-silver">Layers: <span className="text-teal font-mono">{project.caliper?.layers_detected || 1}</span></div>
                <div className={`font-display text-sm uppercase tracking-widest mt-1 ${project.caliper?.scope_determined === "Complete Tear-Off Required" ? "text-plasma glow-orange" : "text-volt glow-volt"}`}>
                  {project.caliper?.scope_determined || "Overlay Permitted"}
                </div>
              </HudCard>
            </div>

            {/* CENTER — 3D model */}
            <div className="hud-card overflow-hidden">
              <span className="corner-bl"/><span className="corner-br"/>
              <RoofModel3D
                telemetry={tele}
                anomalies={anomalies}
                highlightAnomalyId={selectedAnomaly?.id}
                onSelectAnomaly={(a) => setSelectedAnomaly(a)}
                height={620}
              />
            </div>

            {/* RIGHT RAIL */}
            <div className="space-y-3">
              <ForensicOverlay anomaly={selectedAnomaly} projectId={project.id}/>
              <HudCard className="p-3">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Anomaly Field</div>
                <AnomalySelector
                  anomalies={anomalies}
                  selectedId={selectedAnomaly?.id}
                  onSelect={(a) => setSelectedAnomaly(a)}
                />
              </HudCard>
            </div>
          </div>
        </HudCard>
      )}

      {/* AGENT NARRATIVES */}
      <HudCard scanline className="p-6 mb-6">
        <div className="flex items-center gap-2 text-teal font-mono text-[11px] tracking-widest uppercase mb-4">
          <Cpu size={14}/> Multi-Agent Forensic Core
        </div>
        <div className="grid md:grid-cols-2 gap-5">
          <AgentPanel icon={Crosshair} title="Forensic Diagnostic Agent" body={agents.forensic} testid="agent-forensic"/>
          <AgentPanel icon={Activity} title="Evidentiary Validation Agent" body={agents.validation} testid="agent-validation"/>
          <AgentPanel icon={Cpu} title="Reconciliation Engine" body={agents.reconciliation} testid="agent-reconciliation"/>
          <AgentPanel icon={Gavel} title="Jurisprudential Code Agent" body={agents.jurisprudential} testid="agent-jurisprudential"/>
        </div>
      </HudCard>

      {/* PRICING TABLE */}
      <HudCard scanline className="p-6 mb-6">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
          <div className="flex items-center gap-2 text-teal font-mono text-[11px] tracking-widest uppercase"><Radar size={14}/> STRATEX Quant™ — Estimate Locked to Mesh</div>
          <div data-testid="mission-pricing-lock" className="font-mono text-[11px] text-plasma uppercase tracking-widest">{pricing.lock_mode}</div>
        </div>
        <div className="overflow-x-auto">
          <table className="hud-table">
            <thead><tr><th>Line Item</th><th>Qty</th><th>Unit</th><th>Unit $</th><th>Total</th><th>Xactimate</th></tr></thead>
            <tbody data-testid="mission-pricing-table">
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
          <DataReadout label={`Overhead ${((pricing.overhead_rate||0)*100).toFixed(0)}%`} value={`$${(pricing.overhead||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-overhead"/>
          <DataReadout label={`Profit ${((pricing.profit_rate||0)*100).toFixed(0)}%`} value={`$${(pricing.profit||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-profit"/>
          <DataReadout label="Final Total" accent="orange" value={`$${(pricing.final_total||0).toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-final"/>
        </div>
      </HudCard>
    </div>
  );
}

function KV({ label, value, accent, testid }) {
  const color = accent === "orange" ? "text-plasma" : accent === "volt" ? "text-volt" : "text-teal";
  return (
    <div className="flex items-center justify-between" data-testid={testid}>
      <span className="text-muted-hud uppercase text-[10px] tracking-widest">{label}</span>
      <span className={`${color} font-mono`}>{value || "—"}</span>
    </div>
  );
}

function QuantRows({ totals, tele }) {
  return (
    <div className="space-y-2 font-mono text-sm">
      <KV label="Total Squares" value={totals.squares?.toFixed?.(2) || tele.squares} testid="qe-squares"/>
      <KV label="Total SF" value={totals.total_sf || tele.total_sf} testid="qe-totalsf"/>
      <KV label="Ridges" value={`${totals.ridges_lf || tele.ridge_lf} LF`} testid="qe-ridges"/>
      <KV label="Valleys" value={`${totals.valleys_lf || tele.valleys_lf} LF`} accent="orange" testid="qe-valleys"/>
      <KV label="Hips" value={`${totals.hips_lf || tele.hips_lf} LF`} testid="qe-hips"/>
      <KV label="Eaves" value={`${totals.eaves_lf || tele.eaves_lf} LF`} testid="qe-eaves"/>
      <KV label="Rakes / Gables" value={`${totals.rakes_lf || tele.rakes_lf || 0} LF`} testid="qe-rakes"/>
      <KV label="Primary Pitch" value={tele.pitch || `${tele.pitch_num}/12`} testid="qe-pitch"/>
      <KV label="RTK Precision" value={`${tele.rtk_precision_cm || "—"} cm`} accent="volt" testid="qe-rtk"/>
      <KV label="Topology" value={tele.style || "—"} testid="qe-style"/>
    </div>
  );
}

function MobileTabs({ tab, setTab, anomaliesCount }) {
  const tabs = [
    { id: "model",     label: "3D Mesh",  icon: Box },
    { id: "forensic",  label: "Forensic", icon: Thermometer },
    { id: "anomalies", label: `Anomalies${anomaliesCount ? ` (${anomaliesCount})` : ""}`, icon: AlertTriangle },
    { id: "quant",     label: "Quant™",   icon: Radar },
  ];
  const click = (id) => {
    if (id !== tab) {
      try { navigator.vibrate?.(8); } catch (_) {}
      setTab(id);
    }
  };
  return (
    <div data-testid="mobile-diag-tabs" className="flex gap-1 overflow-x-auto -mx-1 px-1 no-bounce">
      {tabs.map((t) => (
        <button
          key={t.id}
          onClick={() => click(t.id)}
          data-testid={`mtab-${t.id}`}
          className={`flex items-center gap-2 px-3 py-2 border whitespace-nowrap font-mono text-[10px] uppercase tracking-widest transition-all ${tab === t.id ? "border-[#00F0FF] text-teal bg-[#00F0FF]/10 shadow-[0_0_12px_rgba(0,240,255,0.35)]" : "border-[#00F0FF]/25 text-muted-hud"}`}
          style={{ minHeight: 40 }}
        >
          <t.icon size={12} strokeWidth={1.5}/> {t.label}
        </button>
      ))}
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
