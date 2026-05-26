import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import useIsMobile from "@/hooks/use-is-mobile";
import { listOperatorJobs, getOperatorJob, operatorLaunch } from "@/lib/api";
import { Radar, Rocket, MapPin, AlertTriangle, CheckCircle2, ChevronRight } from "lucide-react";
import { toast } from "sonner";

const STATUS = { PENDING_FIELD_CAPTURE: "Awaiting Launch", IN_FLIGHT: "In Flight", DATA_CAPTURE_COMPLETE: "Capture Complete" };

export function OperatorBoard() {
  const [jobs, setJobs] = useState(null);
  useEffect(()=>{ listOperatorJobs().then(setJobs).catch(()=>setJobs([])); }, []);
  return (
    <div data-testid="operator-board" className="px-4 md:px-10 py-6 max-w-[1500px] mx-auto">
      <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// OPERATOR FLEET TERMINAL</div>
      <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.06em] md:tracking-[0.14em] text-silver mb-4">Pending Field Captures</h1>
      <div className="bg-[#10141D] border border-[#FF5500]/25 px-3 py-2 mb-4 font-mono text-[10px] text-plasma uppercase tracking-widest flex items-center gap-2"><AlertTriangle size={12}/> ZERO FINANCIAL VISIBILITY — Operators see addresses & roof telemetry only</div>
      {jobs === null && <div className="text-muted-hud font-mono">Loading…</div>}
      {jobs && jobs.length === 0 && <HudCard className="p-8 text-center"><p className="text-muted-hud">No pending captures right now.</p></HudCard>}
      {jobs && jobs.length > 0 && (
        <div className="grid md:grid-cols-2 gap-3" data-testid="operator-jobs">
          {jobs.map((j)=>(
            <Link key={j.id} to={`/operator/jobs/${j.id}`} className="hud-card p-4 hover:border-[#00F0FF] transition-all" data-testid={`op-job-${j.id.slice(0,8)}`}>
              <span className="corner-bl"/><span className="corner-br"/>
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-[10px] uppercase tracking-widest text-teal">JOB {j.id.slice(0,8)}</span>
                <span className="font-mono text-[10px] uppercase tracking-widest text-plasma">{STATUS[j.status]}</span>
              </div>
              <div className="font-heading text-silver">{j.contractor_company || "Contractor"}</div>
              <div className="font-mono text-xs text-muted-hud flex items-center gap-1 mt-1"><MapPin size={11}/>{j.property_address}</div>
              <div className="font-mono text-[10px] text-muted-hud mt-2">{j.lat?.toFixed?.(4)}, {j.lon?.toFixed?.(4)} • Topology: {j.roof_style}</div>
              <div className="text-right text-teal text-xs mt-2 flex items-center justify-end gap-1">Open <ChevronRight size={12}/></div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}

export function OperatorJobDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  const isMobile = useIsMobile(900);
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [preflight, setPreflight] = useState({
    trailer_hatch_secured: true,
    drone_battery_percentage: 100,
    rtk_gps_signal: "Centimeter-Level Locked",
    communication_uplink: "Strong / Starlink Verified",
    local_weather_clear: true,
    personnel_clear: true,
  });

  const load = async () => { setJob(await getOperatorJob(id)); };
  useEffect(()=>{ load().catch(()=>{}); }, [id]);

  if (!job) return <div className="p-10 text-muted-hud font-mono">Loading…</div>;
  const tele = job.roof_telemetry || {};
  const anomalies = job.mission?.anomalies || job.anomalies || [];

  const launch = async () => {
    setBusy(true);
    try { try{navigator.vibrate?.(18);}catch(_){}
      const r = await operatorLaunch(id, preflight);
      setJob(r);
      toast.success("AERIAL RECON COMPLETE");
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const checks = [
    {k:"trailer_hatch_secured", label:"Trailer Hatch: Ready (Secured)"},
    {k:"drone_battery_percentage", label:"Drone Battery: 100% (Balanced)", num:true},
    {k:"rtk_gps_signal", label:"RTK GPS: Centimeter Locked", text:true, ok:"Centimeter-Level Locked"},
    {k:"communication_uplink", label:"Communication Link: Strong (Secure)", text:true, ok:"Strong / Starlink Verified"},
    {k:"local_weather_clear", label:"Weather: Optimal (No Precip / Wind < 5mph)"},
    {k:"personnel_clear", label:"Personnel: Clear of Deployment Area"},
  ];
  const allClear = checks.every((c)=>{
    const v = preflight[c.k];
    if (c.num) return v >= 90;
    if (c.text) return v === c.ok;
    return v === true;
  });

  return (
    <div data-testid="operator-job-page" className="px-4 md:px-10 py-6 max-w-[1700px] mx-auto">
      <Link to="/operator" className="font-mono text-[11px] uppercase tracking-widest text-muted-hud flex items-center gap-1 mb-2 hover:text-teal">← Job Board</Link>
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div>
          <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// FIELD CAPTURE • {job.id.slice(0,8)}</div>
          <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.06em] text-silver" style={{ overflowWrap: "anywhere" }}>{job.property_address}</h1>
          <div className="font-mono text-xs text-muted-hud mt-1">Topology: {job.roof_style} • {job.lat?.toFixed?.(4)}, {job.lon?.toFixed?.(4)}</div>
        </div>
        <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
          <span className={`led ${job.status==="DATA_CAPTURE_COMPLETE"?"led-ok":"led-teal pulse-glow"}`}/>
          <span className={job.status==="DATA_CAPTURE_COMPLETE"?"text-volt":"text-teal"}>{STATUS[job.status]||job.status}</span>
        </div>
      </div>

      {job.status === "PENDING_FIELD_CAPTURE" && (
        <HudCard scanline className="p-5">
          <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest mb-3"><Radar size={14}/> PRE-FLIGHT SAFETY HANDSHAKE</div>
          <div className="space-y-2 mb-4">
            {checks.map((c)=>{
              const v = preflight[c.k];
              const ok = c.num ? v>=90 : c.text ? v===c.ok : v===true;
              return (
                <div key={c.k} data-testid={`op-pre-${c.k}`} className={`hud-card p-3 flex items-center justify-between ${!ok?"hud-card-alert":""}`}>
                  <span className="corner-bl"/><span className="corner-br"/>
                  <div className="font-heading text-silver text-sm">{c.label}</div>
                  <div className="flex items-center gap-3">
                    <span className={`led ${ok?"led-ok pulse-glow":"led-alert pulse-alert"}`}/>
                    <button onClick={()=>{
                      if (c.num) setPreflight({...preflight,[c.k]: v>=90?78:100});
                      else if (c.text) setPreflight({...preflight,[c.k]: ok?"Bad":c.ok});
                      else setPreflight({...preflight,[c.k]: !v});
                    }} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2">TOGGLE</button>
                  </div>
                </div>
              );
            })}
          </div>
          <div className="hud-divider my-3"/>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="font-mono text-[11px] uppercase tracking-widest text-teal">All Systems: <span className={allClear?"text-volt":"text-plasma"}>{allClear?"READY":"HOLD"}</span></div>
            <button onClick={launch} disabled={!allClear||busy} className="btn-hud btn-hud-alert pulse-alert" data-testid="authorize-launch-btn">
              <Rocket size={16}/> {busy?"TRANSMITTING…":"AUTHORIZE AERIAL RECONNAISSANCE"}
            </button>
          </div>
        </HudCard>
      )}

      {job.status === "DATA_CAPTURE_COMPLETE" && (
        <>
          <HudCard className="p-3 mb-4 flex items-center gap-3"><CheckCircle2 size={18} className="text-volt"/><span className="font-heading text-silver">DATA_CAPTURE_COMPLETE — packet uploaded to contractor portal. No financial fields rendered to operator role.</span></HudCard>
          <HudCard scanline className="p-3 mb-4">
            <div className="hud-card overflow-hidden">
              <span className="corner-bl"/><span className="corner-br"/>
              <RoofModel3D telemetry={tele} anomalies={anomalies} height={isMobile?380:520} showLabels={!isMobile}/>
            </div>
          </HudCard>
          <HudCard className="p-4">
            <div className="font-mono text-[11px] uppercase tracking-widest text-teal mb-3">Anomalies Detected (operator-visible technical validation)</div>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
              {anomalies.map((a)=>(
                <div key={a.id} className="hud-card p-3" data-testid={`op-anom-${a.id}`}>
                  <span className="corner-bl"/><span className="corner-br"/>
                  <div className="font-mono text-[10px] text-muted-hud">{a.id}</div>
                  <div className="font-heading text-silver text-sm">{a.type}</div>
                  <div className="font-mono text-[10px] text-plasma">{a.thermal_delta} • {a.severity}</div>
                </div>
              ))}
            </div>
          </HudCard>
        </>
      )}
    </div>
  );
}
