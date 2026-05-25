import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { HudCard } from "@/components/HudCard";
import { ASSETS, UNDERLAYMENT_OPTIONS, DRIP_EDGE_COLORS, DISPOSAL_STRATEGIES, FASTENER_TYPES, PROJECT_TYPES, INSURANCE_CARRIERS } from "@/lib/constants";
import { createProject, submitCaliper, computePricing, launchMission } from "@/lib/api";
import { ArrowRight, ArrowLeft, Crosshair, FileText, Layers, DollarSign, Rocket, AlertTriangle, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";

const STEPS = [
  { n: 1, label: "Intake & Auth", icon: FileText },
  { n: 2, label: "Scope Matrix", icon: Layers },
  { n: 3, label: "Macro-Edge Caliper", icon: Crosshair },
  { n: 4, label: "Quant Pricing", icon: DollarSign },
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
  });
  const [edgeThickness, setEdgeThickness] = useState(1.15);
  const [caliper, setCaliper] = useState(null);
  const [pricing, setPricing] = useState(null);
  const [preflight, setPreflight] = useState({
    trailer_hatch_secured: true,
    drone_battery_percentage: 100,
    rtk_gps_signal: "Centimeter-Level Locked",
    communication_uplink: "Strong / Starlink Verified",
    local_weather_clear: true,
  });
  const [busy, setBusy] = useState(false);

  const next = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (step === 1) {
        // validate
        if (!intake.customer_name || !intake.property_address) {
          toast.error("Customer name and property address are required");
          setBusy(false); return;
        }
        setStep(2);
      } else if (step === 2) {
        const p = await createProject({ intake, scope });
        setProject(p);
        toast.success("Project lodged • Roof telemetry captured");
        setStep(3);
      } else if (step === 3) {
        const c = await submitCaliper(project.id, parseFloat(edgeThickness));
        setCaliper(c);
        toast.success(`Caliper reading: ${c.layers_detected} layer(s) detected`);
        setStep(4);
      } else if (step === 4) {
        const pr = await computePricing(project.id);
        setPricing(pr);
        toast.success("Quant™ engine reconciled");
        setStep(5);
      } else if (step === 5) {
        const result = await launchMission(project.id, preflight);
        toast.success("AERIAL RECON AUTHORIZED");
        navigate(`/mission/${result.id}`);
      }
    } catch (e) {
      toast.error(e?.response?.data?.detail || e.message || "Operation failed");
    } finally {
      setBusy(false);
    }
  };

  const back = () => { if (step > 1) setStep(step - 1); };

  return (
    <div data-testid="new-mission-page" className="px-6 md:px-12 py-10 max-w-[1400px] mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="font-mono text-[11px] tracking-[0.32em] text-teal uppercase">// PRE-FLIGHT PIPELINE</div>
          <h1 className="font-display text-3xl md:text-4xl uppercase tracking-[0.14em] text-silver">Initiate New Mission</h1>
        </div>
        <div className="font-mono text-[11px] tracking-widest text-muted-hud uppercase">
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

      {step === 4 && pricing && (
        <HudCard scanline className="p-8">
          <div className="flex items-center gap-3 mb-6 text-teal">
            <DollarSign size={18}/><span className="font-mono text-[11px] uppercase tracking-[0.28em]">STEP 04 • Quant™ Algorithmic Pricing Node</span>
          </div>
          <div className="grid lg:grid-cols-[2fr_1fr] gap-6">
            <div className="overflow-x-auto">
              <table className="hud-table">
                <thead><tr><th>Line Item</th><th>Qty</th><th>Unit</th><th>Unit $</th><th>Total</th><th>Xactimate</th></tr></thead>
                <tbody data-testid="pricing-table-body">
                  {pricing.line_items.map((li, i)=>(
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
            <div className="space-y-4">
              <HudCard className="p-5">
                <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud mb-1">Margin Lock</div>
                <div data-testid="pricing-lock-mode" className="font-display text-xl text-plasma glow-orange uppercase">{pricing.lock_mode}</div>
              </HudCard>
              <HudCard className="p-5 space-y-3">
                <div className="flex justify-between font-mono text-sm"><span className="text-muted-hud uppercase tracking-widest">Sub-total</span><span className="text-silver">${pricing.subtotal.toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
                <div className="flex justify-between font-mono text-sm"><span className="text-muted-hud uppercase tracking-widest">Overhead ({(pricing.overhead_rate*100).toFixed(0)}%)</span><span className="text-silver">${pricing.overhead.toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
                <div className="flex justify-between font-mono text-sm"><span className="text-muted-hud uppercase tracking-widest">Profit ({(pricing.profit_rate*100).toFixed(0)}%)</span><span className="text-silver">${pricing.profit.toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
                <div className="hud-divider"/>
                <div className="flex justify-between items-end">
                  <span className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">Final Total</span>
                  <span data-testid="pricing-final-total" className="font-display text-2xl text-teal glow-teal">${pricing.final_total.toLocaleString(undefined,{minimumFractionDigits:2})}</span>
                </div>
              </HudCard>
              <img src={ASSETS.pricing_tablet} alt="Pricing reference" className="w-full h-auto opacity-60"/>
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
                {key:"drone_battery_percentage", label:"Drone Battery Percentage", type:"num"},
                {key:"rtk_gps_signal", label:"RTK GPS Signal", type:"text"},
                {key:"communication_uplink", label:"Comms Uplink", type:"text"},
                {key:"local_weather_clear", label:"Local Weather Clear", type:"bool"},
              ].map((row)=>{
                const v = preflight[row.key];
                const ok = row.type==="bool" ? v===true : row.type==="num" ? v===100 : (row.key==="rtk_gps_signal" ? v==="Centimeter-Level Locked" : v.startsWith("Strong"));
                return (
                  <div key={row.key} data-testid={`preflight-${row.key}`} className={`hud-card p-4 flex items-center justify-between ${!ok ? "hud-card-alert" : ""}`}>
                    <span className="corner-bl"/><span className="corner-br"/>
                    <div>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">{row.label}</div>
                      <div className="font-heading text-lg text-silver mt-1">
                        {row.type === "bool" ? (v ? "TRUE" : "FALSE") : v}
                      </div>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className={`led ${ok ? "led-ok pulse-glow" : "led-alert pulse-alert"}`}/>
                      <button type="button" onClick={()=>{
                        if (row.type==="bool") setPreflight({...preflight, [row.key]: !v});
                        if (row.type==="num") setPreflight({...preflight, [row.key]: v===100 ? 78 : 100});
                        if (row.type==="text" && row.key==="rtk_gps_signal") setPreflight({...preflight, [row.key]: ok ? "Drifting" : "Centimeter-Level Locked"});
                        if (row.type==="text" && row.key==="communication_uplink") setPreflight({...preflight, [row.key]: ok ? "Weak" : "Strong / Starlink Verified"});
                      }} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2">TOGGLE</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <div>
              <HudCard className="p-6">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Authorization Window</div>
                <h3 className="font-display text-2xl uppercase tracking-widest text-silver mb-4">Aerial Reconnaissance</h3>
                <p className="text-sm text-muted-hud font-body mb-6">
                  Tapping authorize sends an encrypted relay command to the Raspberry Pi inside the trailer. The motorized roof hatch slides open and the DJI Dock 2 launches its autonomous orbit flight path.
                </p>
                <div className="space-y-3 text-sm font-mono">
                  <div className="flex justify-between"><span className="text-muted-hud">PROJECT_ID</span><span className="text-teal">{project?.id?.slice(0,8)}…</span></div>
                  <div className="flex justify-between"><span className="text-muted-hud">FINAL_TOTAL</span><span className="text-teal">${pricing?.final_total?.toLocaleString(undefined,{minimumFractionDigits:2})}</span></div>
                  <div className="flex justify-between"><span className="text-muted-hud">MARGIN_LOCK</span><span className="text-plasma">{pricing?.lock_mode}</span></div>
                </div>
              </HudCard>
            </div>
          </div>
        </HudCard>
      )}

      {/* footer nav */}
      <div className="mt-8 flex flex-wrap items-center justify-between gap-3">
        <button onClick={back} disabled={step===1 || busy} className="btn-hud btn-hud-ghost" data-testid="wizard-back-btn">
          <ArrowLeft size={14}/> Back
        </button>
        <div className="flex gap-3">
          {step === 5 ? (
            <button onClick={next} disabled={busy} className="btn-hud btn-hud-alert pulse-alert" data-testid="authorize-launch-btn">
              <Rocket size={16}/> {busy ? "TRANSMITTING…" : "AUTHORIZE AERIAL RECONNAISSANCE"}
            </button>
          ) : (
            <button onClick={next} disabled={busy} className="btn-hud" data-testid="wizard-next-btn">
              {busy ? "PROCESSING…" : "Continue"} <ArrowRight size={14}/>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
