import React, { useEffect, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import useIsMobile from "@/hooks/use-is-mobile";
import { listOperatorJobs, getOperatorJob, operatorLaunch, operatorDryRun, operatorWeatherMonitor } from "@/lib/api";
import { Radar, Rocket, MapPin, AlertTriangle, CheckCircle2, ChevronRight, Shield, Wind, Radio, Zap, UserCheck, Eye, PawPrint, Battery, Lock, XCircle, Activity, CloudRain } from "lucide-react";
import { toast } from "sonner";
import { MapContainer, TileLayer, Marker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

const OP_ICON = L.divIcon({
  className: "stratex-leaflet-pin",
  html: `<div style="position:relative;width:28px;height:36px;transform:translate(-14px,-32px);filter:drop-shadow(0 0 6px #FF5500);">
    <svg viewBox="0 0 28 36" width="28" height="36" xmlns="http://www.w3.org/2000/svg">
      <path d="M14 0 C5.5 0 0 6.7 0 14.5 C0 25 14 36 14 36 C14 36 28 25 28 14.5 C28 6.7 22.5 0 14 0 Z" fill="#06080B" stroke="#FF5500" stroke-width="1.5"/>
      <circle cx="14" cy="14" r="4.5" fill="#FF5500"/>
    </svg></div>`,
  iconSize: [28, 36], iconAnchor: [14, 32],
});

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
    // Phase 2 — on-site physical safety (start unchecked — operator MUST sign off)
    homeowner_verified: false,
    vertical_obstruction_clear: false,
    k9_and_child_clear_zone: false,
    // Phase 3 — hardware diagnostics (start green/ready)
    trailer_hatch_secured: true,
    drone_battery_percentage: 100,
    battery_cell_variance_v: 0.015,
    rtk_gps_signal: "Centimeter-Level Locked",
    communication_uplink: "Strong / Starlink Verified",
    local_weather_clear: true,
    personnel_clear: true,
  });
  const [dryRunOpen, setDryRunOpen] = useState(false);
  const [dryRunReason, setDryRunReason] = useState("locked_gate");
  const [dryRunNotes, setDryRunNotes] = useState("");
  const [weather, setWeather] = useState(null);

  const load = async () => { setJob(await getOperatorJob(id)); };
  useEffect(()=>{ load().catch(()=>{}); }, [id]);

  // Live weather pulse — poll every 30s while job is awaiting capture so the operator
  // sees real-time wind / cloud / precip changes that may trigger an abort recommendation
  useEffect(() => {
    if (!job || (job.status !== "PENDING_FIELD_CAPTURE" && job.status !== "IN_FLIGHT")) {
      setWeather(null); return;
    }
    let stopped = false;
    const fetchIt = () => operatorWeatherMonitor(id).then((w)=>{ if(!stopped) setWeather(w); }).catch(()=>{});
    fetchIt();
    const t = setInterval(fetchIt, 30000);
    return () => { stopped = true; clearInterval(t); };
  }, [job?.status, id]);

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

  const flagDryRun = async () => {
    setBusy(true);
    try {
      try{navigator.vibrate?.(40);}catch(_){}
      await operatorDryRun(id, dryRunReason, dryRunNotes || null);
      toast.success("Dry-run flagged · $150 added to contractor invoice");
      setDryRunOpen(false);
      navigate("/operator", { replace: true });
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const phase2 = [
    { k: "homeowner_verified", label: "Homeowner / Tenant Verified", sub: "Occupant aware of operation", icon: UserCheck },
    { k: "vertical_obstruction_clear", label: "Vertical Obstruction Sweep", sub: "No tree canopies, towers, or unmapped lines", icon: Eye },
    { k: "k9_and_child_clear_zone", label: "K-9 & Child Clear Zone", sub: "Pets indoors · launch hatch perimeter clear", icon: PawPrint },
  ];
  const phase3 = [
    { k: "trailer_hatch_secured", label: "Trailer Hatch", sub: "Optical sensors clear of debris / ice", icon: Lock, fmt: (v)=>v?"SECURED":"OBSTRUCTED" },
    { k: "drone_battery_percentage", label: "Battery Charge", sub: "Must be ≥ 90%", icon: Battery, fmt: (v)=>`${v}%`, ok: (v)=>v>=90 },
    { k: "battery_cell_variance_v", label: "Cell Voltage Variance", sub: "Must be < 0.020 V", icon: Battery, fmt: (v)=>`${v.toFixed(3)} V`, ok: (v)=>v<0.02 },
    { k: "rtk_gps_signal", label: "RTK GPS Lock", sub: "Centimeter-level kinematic lock", icon: Radio, fmt: (v)=>v, ok: (v)=>v==="Centimeter-Level Locked" },
    { k: "communication_uplink", label: "Communication Uplink", sub: "Starlink primary · LTE failover", icon: Zap, fmt: (v)=>v, ok: (v)=>v.startsWith("Strong") },
    { k: "local_weather_clear", label: "Micro-Weather", sub: "Wind <5mph · precip <10%", icon: Wind, fmt: (v)=>v?"OPTIMAL":"DEGRADED" },
  ];
  const phase2OK = phase2.every((c)=>preflight[c.k] === true);
  const phase3OK = phase3.every((c)=>c.ok ? c.ok(preflight[c.k]) : preflight[c.k] === true);
  const allClear = phase2OK && phase3OK;

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

      {/* Phase 1 confirmation badge (operator can see it passed) */}
      {job.phase1_status && (
        <HudCard className="p-3 mb-4" data-testid="op-phase1-confirmation">
          <div className="flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-volt">
              <Shield size={13}/> Phase 1 Digital Gatekeeping · CLEARED at {job.phase1_completed_at}
            </div>
            <div className="flex gap-1 text-[10px] font-mono uppercase tracking-widest">
              {job.phase1_status.checks.map((c, i) => (
                <span key={i} className={`px-2 py-0.5 border ${c.status==="PASS"?"text-volt border-[#39FF14]/40":c.status==="WARN"?"text-teal border-[#00F0FF]/40":"text-plasma border-[#FF5500]/40"}`}>{c.status}</span>
              ))}
            </div>
          </div>
        </HudCard>
      )}

      {/* LIVE WEATHER PULSE — refresh every 30s; visible during PENDING_FIELD_CAPTURE or IN_FLIGHT */}
      {weather && weather.available && (job.status === "PENDING_FIELD_CAPTURE" || job.status === "IN_FLIGHT") && (
        <HudCard scanline alert={!!weather.abort_recommended} className="p-4 mb-3" data-testid="op-weather-monitor-card">
          <div className="flex items-center justify-between flex-wrap gap-3 mb-2">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-teal">
              <Activity size={13} className={weather.abort_recommended ? "text-plasma pulse-alert" : "text-volt pulse-glow"}/>
              Live Weather Pulse · Polled every 30s
            </div>
            {weather.abort_recommended ? (
              <span data-testid="op-weather-abort-badge" className="font-mono text-[10px] uppercase tracking-widest text-plasma border border-[#FF5500]/40 px-2 py-0.5 flex items-center gap-1">
                <CloudRain size={11}/> ABORT RECOMMENDED
              </span>
            ) : (
              <span className="font-mono text-[10px] uppercase tracking-widest text-volt border border-[#39FF14]/40 px-2 py-0.5">NOMINAL</span>
            )}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
            <div>Past 24h precip: <span className="text-silver">{weather.past_24h_precip_in}"</span></div>
            <div>Cloud 12h: <span className="text-silver">{weather.avg_cloud_12h_pct}%</span></div>
            <div>Next 2h precip prob: <span className="text-silver">{weather.next2h_precip_prob_pct}%</span></div>
            <div>Wind: <span className="text-silver">{weather.current_wind_mph} mph</span></div>
          </div>
          <div className="text-[10px] font-mono text-muted-hud uppercase tracking-widest mt-2">as of {weather.as_of} · ASTM C1153</div>
        </HudCard>
      )}

      {job.status === "PENDING_FIELD_CAPTURE" && (
        <>
          <HudCard className="p-3 mb-4">
            <div className="font-mono text-[11px] uppercase tracking-widest text-plasma flex items-center gap-2 mb-2"><MapPin size={12}/> DISPATCH TARGET</div>
            <div className="relative border border-[#FF5500]/40 overflow-hidden" style={{ height: 240 }}>
              <span className="corner-bl"/><span className="corner-br"/>
              {Number.isFinite(job.lat) && Number.isFinite(job.lon) && (
                <MapContainer center={[job.lat, job.lon]} zoom={18} style={{ height: "100%", width: "100%", background: "#06080B" }} scrollWheelZoom={false} dragging={!isMobile}>
                  <TileLayer attribution='Imagery &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" maxZoom={19}/>
                  <Marker position={[job.lat, job.lon]} icon={OP_ICON}/>
                </MapContainer>
              )}
            </div>
            <div className="mt-2 font-mono text-[10px] text-muted-hud">TARGET: <span className="text-teal">{job.lat?.toFixed?.(5)}, {job.lon?.toFixed?.(5)}</span> • RTK acquisition will resolve to centimeter precision on launch.</div>
          </HudCard>

          {/* PHASE 2 — On-Site Physical Safety */}
          <HudCard scanline className="p-5 mb-3" data-testid="phase2-card">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <div className="flex items-center gap-2 text-plasma font-mono text-[11px] uppercase tracking-widest"><AlertTriangle size={13}/> Phase 2 · On-Site Physical Safety</div>
              <span className={`font-mono text-[10px] uppercase tracking-widest ${phase2OK?"text-volt":"text-plasma"}`}>{phase2OK?"CLEARED":"PENDING"}</span>
            </div>
            <div className="space-y-2 mb-2">
              {phase2.map((c) => {
                const v = preflight[c.k];
                const Icon = c.icon;
                return (
                  <div key={c.k} data-testid={`op-pre-${c.k}`} className={`hud-card p-3 flex items-center justify-between gap-3 ${!v?"hud-card-alert":""}`}>
                    <span className="corner-bl"/><span className="corner-br"/>
                    <Icon size={14} className={v?"text-volt":"text-plasma"}/>
                    <div className="min-w-0 flex-1">
                      <div className="font-heading text-silver text-sm">{c.label}</div>
                      <div className="font-mono text-[10px] text-muted-hud">{c.sub}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`led ${v?"led-ok pulse-glow":"led-alert pulse-alert"}`}/>
                      <button onClick={()=>setPreflight({...preflight,[c.k]: !v})} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2">{v?"UNDO":"SIGN OFF"}</button>
                    </div>
                  </div>
                );
              })}
            </div>
            <p className="font-mono text-[10px] text-muted-hud uppercase tracking-widest mt-2">Pilot tablet sign-off · liability mitigation</p>
          </HudCard>

          {/* PHASE 3 — Hardware & Telemetry */}
          <HudCard scanline className="p-5 mb-3" data-testid="phase3-card">
            <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
              <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest"><Radar size={13}/> Phase 3 · Hardware Diagnostic Lock</div>
              <span className={`font-mono text-[10px] uppercase tracking-widest ${phase3OK?"text-volt":"text-plasma"}`}>{phase3OK?"NOMINAL":"FAULT"}</span>
            </div>
            <div className="grid sm:grid-cols-2 gap-2">
              {phase3.map((c) => {
                const v = preflight[c.k];
                const ok = c.ok ? c.ok(v) : v === true;
                const Icon = c.icon;
                return (
                  <div key={c.k} data-testid={`op-pre-${c.k}`} className={`hud-card p-3 flex items-center justify-between gap-3 ${!ok?"hud-card-alert":""}`}>
                    <span className="corner-bl"/><span className="corner-br"/>
                    <Icon size={14} className={ok?"text-volt":"text-plasma"}/>
                    <div className="min-w-0 flex-1">
                      <div className="font-heading text-silver text-sm">{c.label}</div>
                      <div className="font-mono text-[10px] text-muted-hud truncate">{c.fmt ? c.fmt(v) : (v?"OK":"FAIL")} · {c.sub}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`led ${ok?"led-ok pulse-glow":"led-alert pulse-alert"}`}/>
                      <button onClick={()=>{
                        if (c.k === "drone_battery_percentage") setPreflight({...preflight, [c.k]: v>=90 ? 78 : 100});
                        else if (c.k === "battery_cell_variance_v") setPreflight({...preflight, [c.k]: v<0.02 ? 0.035 : 0.015});
                        else if (c.k === "rtk_gps_signal") setPreflight({...preflight, [c.k]: ok ? "Drifting" : "Centimeter-Level Locked"});
                        else if (c.k === "communication_uplink") setPreflight({...preflight, [c.k]: ok ? "Degraded" : "Strong / Starlink Verified"});
                        else setPreflight({...preflight, [c.k]: !v});
                      }} className="btn-hud btn-hud-ghost text-[10px] py-1 px-2">TOGGLE</button>
                    </div>
                  </div>
                );
              })}
            </div>
          </HudCard>

          <HudCard className="p-4 flex flex-wrap items-center justify-between gap-3">
            <div className="font-mono text-[11px] uppercase tracking-widest text-teal">
              ALL PHASES: <span className={allClear?"text-volt":"text-plasma"}>{allClear?"READY FOR AUTONOMOUS LAUNCH":"SOFTWARE LOCK ENGAGED"}</span>
            </div>
            <div className="flex gap-2 flex-wrap">
              <button onClick={()=>setDryRunOpen(true)} className="btn-hud btn-hud-ghost" data-testid="dry-run-open"><XCircle size={14}/> Flag Dry-Run</button>
              <button onClick={launch} disabled={!allClear||busy} className="btn-hud btn-hud-alert pulse-alert" data-testid="authorize-launch-btn">
                <Rocket size={16}/> {busy?"TRANSMITTING…":"AUTHORIZE AERIAL RECON"}
              </button>
            </div>
          </HudCard>

          {dryRunOpen && (
            <HudCard alert className="p-5 mt-3" data-testid="dry-run-dialog">
              <div className="font-mono text-[11px] uppercase tracking-widest text-plasma flex items-center gap-2 mb-3"><AlertTriangle size={13}/> Flag Dispatch as Dry-Run · $150 Penalty</div>
              <p className="text-[12px] text-muted-hud mb-3">This adds $150 to the contractor's next invoice and aborts the mission. Use only if site access is physically impossible right now.</p>
              <label className="hud-label">Reason</label>
              <select data-testid="dry-run-reason" className="hud-input mb-3" value={dryRunReason} onChange={(e)=>setDryRunReason(e.target.value)}>
                <option value="locked_gate">Locked Gate</option>
                <option value="unnotified_homeowner">Unnotified / Hostile Homeowner</option>
                <option value="aggressive_animal">Aggressive Animal</option>
                <option value="wrong_address">Wrong Address</option>
                <option value="other">Other</option>
              </select>
              <label className="hud-label">Notes (optional)</label>
              <textarea data-testid="dry-run-notes" className="hud-input mb-3" rows={2} value={dryRunNotes} onChange={(e)=>setDryRunNotes(e.target.value)}/>
              <div className="flex gap-2 flex-wrap">
                <button onClick={flagDryRun} disabled={busy} className="btn-hud btn-hud-alert" data-testid="dry-run-confirm"><AlertTriangle size={14}/> Confirm Dry-Run</button>
                <button onClick={()=>setDryRunOpen(false)} className="btn-hud btn-hud-ghost">Cancel</button>
              </div>
            </HudCard>
          )}
        </>
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
