import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import useIsMobile from "@/hooks/use-is-mobile";
import { ASSETS, UNDERLAYMENT_OPTIONS, DRIP_EDGE_COLORS, DISPOSAL_STRATEGIES, FASTENER_TYPES, PROJECT_TYPES, INSURANCE_CARRIERS, ROOF_STYLES } from "@/lib/constants";
import { createProject, submitCaliper, runScan, launchMission } from "@/lib/api";
import { ArrowRight, ArrowLeft, Crosshair, FileText, Layers, Box, Rocket, AlertTriangle, CheckCircle2, ScanLine } from "lucide-react";
import { toast } from "sonner";

const STEPS = [
  { n: 1, label: "Intake & Auth", icon: FileText },
  { n: 2, label: "Scope Matrix", icon: Layers },
  { n: 3, label: "Macro-Edge Caliper", icon: Crosshair },
  { n: 4, label: "Vision™ Mesh Capture", icon: Box },
  { n: 5, label: "Launch Portal", icon: Rocket },
];

const Segmented = ({ step }) => (
  <div data-testid="wizard-progress" className="flex gap-2 mb-8">
    {STEPS.map((s) => (
      <div key={s.n} className={`seg ${step === s.n ? "active" : step > s.n ? "done" : ""}`} />
    ))}
  </div>
);

const Choice = ({ value, current, onClick, testid }) => (
  <button data-testid={testid} type="button" onClick={() => onClick(value)} className={`hud-option ${current === value ? "active" : ""}`}>
    {value}
  </button>
);

export default function NewMission() {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [project, setProject] = useState(null);
  const [scan, setScan] = useState(null);
  const [scanning, setScanning] = useState(false);
  const [intake, setIntake] = useState({
    customer_name: "Anthony Cross",
    property_address: "Lexington, Kentucky",
    insurance_carrier: "State Farm",
    project_type: "Insurance Claim",
  });
  const [scope, setScope] = useState({
    underlayment_brand: "Premium Synthetic Felt",
    drip_edge_color: "Charcoal",
    disposal_strategy: "Automated Mobile Trailer Rig",
    fastener_type: "Hot-Dipped Galvanized",
    roof_style: "cross_hip",
  });
  const [edgeThickness, setEdgeThickness] = useState(1.15);
  const [preflight, setPreflight] = useState({
    trailer_hatch_secured: true,
    drone_battery_percentage: 100,
    rtk_gps_signal: "Centimeter-Level Locked",
    communication_uplink: "Strong / Starlink Verified",
    local_weather_clear: true,
  });
  const [busy, setBusy] = useState(false);
  const [launchPhase, setLaunchPhase] = useState(null); // "uplink" | "narrative" | "complete"

  const next = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (step === 1) {
        if (!intake.customer_name || !intake.property_address) {
          toast.error("Customer name and property address are required");
          setBusy(false); return;
        }
        setStep(2);
      } else if (step === 2) {
        const p = await createProject({ intake, scope });
        setProject(p);
        toast.success("Project lodged");
        setStep(3);
      } else if (step === 3) {
        const c = await submitCaliper(project.id, parseFloat(edgeThickness));
        setProject({ ...project, caliper: c });
        toast.success(`Caliper: ${c.layers_detected} layer(s) detected`);
        // jump to scan step, then auto-start scan
        setStep(4);
        setScanning(true);
        try {
          const s = await runScan(project.id);
          setScan(s);
          toast.success(`Photogrammetry mesh stitched • ${s.anomalies_count} anomalies`);
        } finally {
          setScanning(false);
        }
      } else if (step === 4) {
        setStep(5);
      } else if (step === 5) {
        setLaunchPhase("uplink");
        await new Promise((r) => setTimeout(r, 600));
        setLaunchPhase("narrative");
        const result = await launchMission(project.id, preflight);
        setLaunchPhase("complete");
        toast.success("AERIAL RECON AUTHORIZED");
        navigate(`/mission/${result.id}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Operation failed");
      setLaunchPhase(null);
    } finally {
      setBusy(false);
    }
  };

  const back = () => { if (step > 1 && !busy) setStep(step - 1); };

  return (
    <div data-testid="new-mission-page" className="px-4 md:px-12 py-6 md:py-10 max-w-[1500px] mx-auto pb-28 md:pb-10">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <div>
          <div className="font-mono text-[11px] tracking-[0.32em] text-teal uppercase">// PRE-FLIGHT PIPELINE</div>
          <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.14em] text-silver">Initiate New Mission</h1>
        </div>
        <div className="font-mono text-[10px] md:text-[11px] tracking-widest text-muted-hud uppercase">
          Step <span className="text-teal">{step}</span> / 5 — <span className="text-silver">{STEPS[step-1].label}</span>
        </div>
      </div>
      <Segmented step={step} />

      {step === 1 && (
        <HudCard scanline className="p-8">
          <div className="flex items-center gap-3 mb-6 text-teal">
            <FileText size={18} /><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 01 • Project Intake & Auth</span>
          </div>
          <div className="grid md:grid-cols-2 gap-6">
            <div>
              <label className="hud-label">Customer Name</label>
              <input data-testid="intake-customer-name" className="hud-input" value={intake.customer_name}
                onChange={(e)=>setIntake({...intake, customer_name: e.target.value})}/>
            </div>
            <div>
              <label className="hud-label">Property Address</label>
              <input data-testid="intake-property-address" className="hud-input" value={intake.property_address}
                onChange={(e)=>setIntake({...intake, property_address: e.target.value})}/>
            </div>
            <div>
              <label className="hud-label">Insurance Carrier</label>
              <select data-testid="intake-insurance-carrier" className="hud-input" value={intake.insurance_carrier}
                onChange={(e)=>setIntake({...intake, insurance_carrier: e.target.value})}>
                {INSURANCE_CARRIERS.map((c)=><option key={c} value={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="hud-label">Project Type</label>
              <div className="grid grid-cols-2 gap-3">
                {PROJECT_TYPES.map((t)=>(
                  <Choice key={t} value={t} current={intake.project_type} onClick={(v)=>setIntake({...intake, project_type:v})} testid={`intake-type-${t.toLowerCase().replace(/\s+/g,'-')}`}/>
                ))}
              </div>
            </div>
          </div>
        </HudCard>
      )}

      {step === 2 && (
        <HudCard scanline className="p-8">
          <div className="flex items-center gap-3 mb-6 text-teal">
            <Layers size={18}/><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 02 • Scope Configuration Matrix</span>
          </div>
          <div className="grid md:grid-cols-2 gap-8">
            <div className="md:col-span-2">
              <label className="hud-label">Roof Topology Preset (drives the Vision™ mesh model)</label>
              <div className="grid sm:grid-cols-3 lg:grid-cols-5 gap-2">
                {ROOF_STYLES.map((s) => (
                  <button
                    key={s.id}
                    type="button"
                    data-testid={`scope-roof-style-${s.id}`}
                    onClick={() => setScope({ ...scope, roof_style: s.id })}
                    className={`hud-option text-left ${scope.roof_style === s.id ? "active" : ""}`}
                  >
                    <div>{s.label}</div>
                    <div className="font-mono text-[10px] mt-1 normal-case tracking-normal text-muted-hud" style={{ textTransform: "none" }}>{s.blurb}</div>
                  </button>
                ))}
              </div>
            </div>
            <div>
              <label className="hud-label">Underlayment Brand</label>
              <div className="grid gap-2">{UNDERLAYMENT_OPTIONS.map((u)=><Choice key={u} value={u} current={scope.underlayment_brand} onClick={(v)=>setScope({...scope, underlayment_brand:v})} testid={`scope-under-${u.toLowerCase().replace(/\s+/g,'-')}`}/>)}</div>
            </div>
            <div>
              <label className="hud-label">Drip Edge Color</label>
              <div className="grid grid-cols-2 gap-2">{DRIP_EDGE_COLORS.map((u)=><Choice key={u} value={u} current={scope.drip_edge_color} onClick={(v)=>setScope({...scope, drip_edge_color:v})} testid={`scope-edge-${u.toLowerCase()}`}/>)}</div>
            </div>
            <div>
              <label className="hud-label">Disposal Strategy</label>
              <div className="grid gap-2">{DISPOSAL_STRATEGIES.map((u)=><Choice key={u} value={u} current={scope.disposal_strategy} onClick={(v)=>setScope({...scope, disposal_strategy:v})} testid={`scope-disposal-${u.toLowerCase().replace(/\s+/g,'-')}`}/>)}</div>
            </div>
            <div>
              <label className="hud-label">Fastener Type</label>
              <div className="grid gap-2">{FASTENER_TYPES.map((u)=><Choice key={u} value={u} current={scope.fastener_type} onClick={(v)=>setScope({...scope, fastener_type:v})} testid={`scope-fastener-${u.toLowerCase().replace(/\s+/g,'-')}`}/>)}</div>
            </div>
          </div>
        </HudCard>
      )}

      {step === 3 && (
        <HudCard scanline className="p-8">
          <div className="grid lg:grid-cols-[1.05fr_1fr] gap-8">
            <div>
              <div className="flex items-center gap-3 mb-6 text-teal">
                <Crosshair size={18}/><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 03 • Macro-Edge Profile & Layer Analysis</span>
              </div>
              <p className="text-sm text-muted-hud font-body mb-6">
                The Aero-Caliper Vision Algorithm measures the vertical thickness of the rake edge in inches. If thickness &gt; 1.00" we flag overlay roofs and force a complete tear-off.
              </p>
              <label className="hud-label">Measured Edge Thickness (inches)</label>
              <input data-testid="caliper-thickness" type="number" step="0.01" min="0.1" max="3" className="hud-input mb-6" value={edgeThickness} onChange={(e)=>setEdgeThickness(e.target.value)}/>

              <div className={`hud-card ${parseFloat(edgeThickness) > 1.0 ? "hud-card-alert" : ""} p-5`}>
                <span className="corner-bl" /><span className="corner-br" />
                <div className="font-mono text-[11px] tracking-widest uppercase mb-2 text-muted-hud">Auto-Determined Scope</div>
                {parseFloat(edgeThickness) > 1.0 ? (
                  <div data-testid="caliper-result-tearoff" className="text-plasma glow-orange font-display text-2xl uppercase tracking-widest flex items-center gap-2">
                    <AlertTriangle size={22}/> Complete Tear-Off Required
                  </div>
                ) : (
                  <div data-testid="caliper-result-overlay" className="text-volt glow-volt font-display text-2xl uppercase tracking-widest flex items-center gap-2">
                    <CheckCircle2 size={22}/> Overlay Permitted
                  </div>
                )}
                <div className="grid grid-cols-3 gap-4 mt-4">
                  <div><div className="hud-label">Layers</div><div className="font-mono text-teal text-lg">{parseFloat(edgeThickness) > 1.0 ? 2 : 1}</div></div>
                  <div><div className="hud-label">Labor ×</div><div className="font-mono text-teal text-lg">{parseFloat(edgeThickness) > 1.0 ? "1.5" : "1.0"}</div></div>
                  <div><div className="hud-label">Dump ×</div><div className="font-mono text-teal text-lg">{parseFloat(edgeThickness) > 1.0 ? "1.5" : "1.0"}</div></div>
                </div>
              </div>
            </div>
            <div>
              <HudCard className="p-2"><img src={ASSETS.caliper_tablet} alt="Caliper Analysis" className="w-full h-auto"/></HudCard>
            </div>
          </div>
        </HudCard>
      )}

      {step === 4 && (
        <HudCard scanline className="p-6">
          <div className="flex items-center justify-between mb-4 flex-wrap gap-2">
            <div className="flex items-center gap-3 text-teal">
              <Box size={18}/><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 04 • STRATEX Vision™ Spatial Mesh Capture</span>
            </div>
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest">
              <span className={`led ${scanning ? "led-teal pulse-glow" : "led-ok"}`}/>
              <span className={scanning ? "text-teal" : "text-volt"}>{scanning ? "STITCHING MESH…" : "MESH READY"}</span>
            </div>
          </div>
          <p className="text-sm text-muted-hud font-body mb-4 max-w-3xl">
            The drone executes a 4-pass autonomous orbit, capturing 240 megapixel orthomosaic frames + radiometric thermal sweeps. The cloud rendering engine stitches them into a millimeter-accurate 3D mesh from which every Quant™ measurement is derived. <span className="text-teal">No calculations run until the mesh is locked.</span>
          </p>

          <div className="grid lg:grid-cols-[1.5fr_1fr] gap-4">
            <div className="hud-card overflow-hidden">
              <span className="corner-bl"/><span className="corner-br"/>
              {project?.roof_telemetry && (
                <RoofModel3D
                  telemetry={project.roof_telemetry}
                  anomalies={scan?.anomalies || []}
                  scanning={scanning}
                  height={isMobile ? 360 : 520}
                  showLabels={!isMobile}
                />
              )}
            </div>
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <DataReadout label="Total SF" value={project?.roof_telemetry?.totals?.total_sf || project?.roof_telemetry?.total_sf || "—"} testid="mesh-sf"/>
                <DataReadout label="Squares" value={project?.roof_telemetry?.totals?.squares || project?.roof_telemetry?.squares || "—"} testid="mesh-sq"/>
                <DataReadout label="Pitch" value={project?.roof_telemetry?.pitch || "—"} testid="mesh-pitch"/>
                <DataReadout label="Ridges LF" value={project?.roof_telemetry?.totals?.ridges_lf || project?.roof_telemetry?.ridge_lf || "—"} testid="mesh-ridge"/>
                <DataReadout label="Valleys LF" value={project?.roof_telemetry?.totals?.valleys_lf || project?.roof_telemetry?.valleys_lf || "—"} accent="orange" testid="mesh-valleys"/>
                <DataReadout label="Hips LF" value={project?.roof_telemetry?.totals?.hips_lf || project?.roof_telemetry?.hips_lf || "—"} testid="mesh-hips"/>
                <DataReadout label="Eaves LF" value={project?.roof_telemetry?.totals?.eaves_lf || project?.roof_telemetry?.eaves_lf || "—"} testid="mesh-eaves"/>
                <DataReadout label="RTK Precision" value={`${project?.roof_telemetry?.rtk_precision_cm || "—"} cm`} accent="volt" testid="mesh-rtk"/>
              </div>

              <HudCard className="p-4" alert={scan?.critical_count > 0}>
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2 flex items-center gap-2"><ScanLine size={12}/> Forensic Scan Result</div>
                {scanning && (
                  <div className="font-mono text-sm text-teal animate-pulse">// Capturing radiometric layer…</div>
                )}
                {!scanning && scan && (
                  <div data-testid="scan-result-summary">
                    <div className="flex items-baseline gap-2">
                      <span className="font-display text-3xl text-plasma glow-orange">{scan.anomalies_count}</span>
                      <span className="text-muted-hud font-mono text-xs uppercase tracking-widest">anomalies detected</span>
                    </div>
                    <div className="font-mono text-xs text-muted-hud mt-1">{scan.critical_count} critical • mesh status {scan.mesh_status}</div>
                    <ul className="mt-3 space-y-1 max-h-44 overflow-auto" data-testid="scan-anomaly-list">
                      {scan.anomalies.map((a)=>(
                        <li key={a.id} className="font-mono text-[11px] flex items-center gap-2">
                          <span className={`led ${a.severity==="CRITICAL"||a.severity==="HIGH" ? "led-alert" : "led-teal"}`}/>
                          <span className="text-silver">{a.id}</span>
                          <span className="text-muted-hud">{a.type}</span>
                          <span className="ml-auto text-plasma">{a.thermal_delta}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </HudCard>
            </div>
          </div>
        </HudCard>
      )}

      {step === 5 && (
        <HudCard scanline className="p-8">
          <div className="flex items-center gap-3 mb-6 text-teal">
            <Rocket size={18}/><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 05 • Fleet Autonomous Launch Portal</span>
          </div>
          <div className="grid lg:grid-cols-2 gap-8">
            <div className="space-y-3">
              {[
                {key:"trailer_hatch_secured", label:"Trailer Hatch Secured", type:"bool"},
                {key:"drone_battery_percentage", label:"Drone Battery", type:"num"},
                {key:"rtk_gps_signal", label:"RTK GPS Signal", type:"text"},
                {key:"communication_uplink", label:"Comms Uplink", type:"text"},
                {key:"local_weather_clear", label:"Local Weather Clear", type:"bool"},
              ].map((row)=>{
                const v = preflight[row.key];
                const ok = row.type==="bool" ? v===true : row.type==="num" ? v >= 90 : (row.key==="rtk_gps_signal" ? v==="Centimeter-Level Locked" : v.startsWith("Strong"));
                return (
                  <div key={row.key} data-testid={`preflight-${row.key}`} className={`hud-card p-4 flex items-center justify-between ${!ok ? "hud-card-alert" : ""}`}>
                    <span className="corner-bl"/><span className="corner-br"/>
                    <div>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">{row.label}</div>
                      <div className="font-heading text-lg text-silver mt-1">
                        {row.type === "bool" ? (v ? "TRUE" : "FALSE") : row.type === "num" ? `${v}%` : v}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`led ${ok ? "led-ok pulse-glow" : "led-alert pulse-alert"}`}/>
                      <button type="button" onClick={()=>{
                        if (row.type==="bool") setPreflight({...preflight, [row.key]: !v});
                        if (row.type==="num") setPreflight({...preflight, [row.key]: v >= 90 ? 78 : 100});
                        if (row.type==="text" && row.key==="rtk_gps_signal") setPreflight({...preflight, [row.key]: ok ? "Drifting" : "Centimeter-Level Locked"});
                        if (row.type==="text" && row.key==="communication_uplink") setPreflight({...preflight, [row.key]: ok ? "Weak" : "Strong / Starlink Verified"});
                      }} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2">TOGGLE</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div className="space-y-4">
              <HudCard className="p-6">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Authorization Window</div>
                <h3 className="font-display text-2xl uppercase tracking-widest text-silver mb-4">Aerial Reconnaissance</h3>
                <p className="text-sm text-muted-hud font-body mb-6">
                  Tapping authorize sends an encrypted relay command to the Raspberry Pi in the trailer. The motorized roof hatch slides open and the DJI Dock 2 launches its autonomous orbit. Multi-agent AI then produces the binding forensic report.
                </p>
                <div className="space-y-3 text-sm font-mono">
                  <div className="flex justify-between"><span className="text-muted-hud">PROJECT_ID</span><span className="text-teal">{project?.id?.slice(0,8)}…</span></div>
                  <div className="flex justify-between"><span className="text-muted-hud">MESH_STATUS</span><span className="text-volt">{scan?.mesh_status || "—"}</span></div>
                  <div className="flex justify-between"><span className="text-muted-hud">ANOMALIES</span><span className="text-plasma">{scan?.anomalies_count || 0} • {scan?.critical_count || 0} crit</span></div>
                </div>
              </HudCard>

              {launchPhase && (
                <HudCard className="p-5" data-testid="launch-progress">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-3">// LAUNCH TELEMETRY</div>
                  <ProgressLine done label="Encrypted relay uplink → Pi" />
                  <ProgressLine done={launchPhase !== "uplink"} active={launchPhase === "uplink"} label="Hatch actuators engaged" />
                  <ProgressLine done={launchPhase === "complete"} active={launchPhase === "narrative"} label="Multi-agent narrative synthesis (Claude Sonnet 4.6)" />
                  <ProgressLine done={launchPhase === "complete"} active={false} label="Mission packet sealed" />
                </HudCard>
              )}
            </div>
          </div>
        </HudCard>
      )}

      {/* footer nav — sticky on mobile, inline on desktop */}
      <div className="md:mt-8 mt-4 md:static fixed bottom-0 left-0 right-0 md:bg-transparent bg-[#06080B]/95 backdrop-blur-md border-t md:border-0 border-[#00F0FF]/20 md:p-0 p-3 z-40 safe-bottom flex flex-wrap items-center justify-between gap-3">
        <button onClick={back} disabled={step===1 || busy} className="btn-hud btn-hud-ghost" data-testid="wizard-back-btn">
          <ArrowLeft size={14}/> Back
        </button>
        <div className="flex gap-3">
          {step === 5 ? (
            <button onClick={next} disabled={busy} className="btn-hud btn-hud-alert pulse-alert" data-testid="authorize-launch-btn">
              <Rocket size={16}/> {busy ? "TRANSMITTING…" : isMobile ? "AUTHORIZE" : "AUTHORIZE AERIAL RECONNAISSANCE"}
            </button>
          ) : (
            <button onClick={next} disabled={busy || (step===4 && scanning)} className="btn-hud" data-testid="wizard-next-btn">
              {busy ? "PROCESSING…" : step===4 ? (isMobile ? "Lock & Continue" : "Lock Mesh & Continue") : "Continue"} <ArrowRight size={14}/>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function ProgressLine({ done, active, label }) {
  return (
    <div className="flex items-center gap-2 font-mono text-[11px] py-1">
      <span className={`led ${done ? "led-ok" : active ? "led-teal pulse-glow" : "led-off"}`}/>
      <span className={done ? "text-volt" : active ? "text-teal" : "text-muted-hud"}>{label}</span>
      {active && <span className="ml-auto text-teal animate-pulse">…</span>}
    </div>
  );
}
