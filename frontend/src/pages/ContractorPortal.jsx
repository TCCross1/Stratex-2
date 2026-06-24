import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ForensicOverlay, { AnomalySelector, ProjectIdentityCard, QuantEstimationCard, AnomalyMonetizationCard } from "@/components/ForensicOverlay";
import useIsMobile from "@/hooks/use-is-mobile";
import { useAuth } from "@/lib/auth";
import {
  listContractorJobs, createJob, getContractorJob, computeProposal, auditApprove, markSent, contractorPdfUrl,
  getMaterials, saveMaterials,
} from "@/lib/api";
import { Plus, MapPin, Lock, FileText, Download, Shield, DollarSign, CheckCircle2, Send, Layers, Box, ChevronRight, Calculator, Mail, Loader2, AlertTriangle, Wind, Cloud, Radio, Zap, ScrollText, Home, Activity, Calendar } from "lucide-react";
import { toast } from "sonner";
import MapPicker from "@/components/MapPicker";
import { emailProposal, runPhase1, getJobAuditLog, rescheduleSuggestions, weatherMonitor, notifyHomeownerDelay } from "@/lib/api";
import LaunchCountdownBadge from "@/components/LaunchCountdownBadge";
import CaliperUpload from "@/components/CaliperUpload";
import ValidationReport from "@/components/ValidationReport";

const STATUS_LABEL = {
  DRAFT: "Draft", PENDING_PHASE1: "Phase 1 Pending", PHASE1_BLOCKED: "Phase 1 Blocked",
  PENDING_FIELD_CAPTURE: "Awaiting Field Capture",
  IN_FLIGHT: "Aerial Recon In Progress", DATA_CAPTURE_COMPLETE: "Capture Complete",
  PROPOSAL_READY: "Proposal Ready", AUDIT_APPROVED: "Audit Approved", SENT_TO_HOMEOWNER: "Sent",
  DRY_RUN_PENALTY: "Dry-Run Penalty",
  RESCHEDULED_CONFIRMED: "Reschedule Confirmed",
};
const STATUS_COLOR = {
  PENDING_PHASE1: "text-teal", PHASE1_BLOCKED: "text-plasma",
  PENDING_FIELD_CAPTURE: "text-teal", IN_FLIGHT: "text-teal", DATA_CAPTURE_COMPLETE: "text-volt",
  PROPOSAL_READY: "text-teal", AUDIT_APPROVED: "text-volt", SENT_TO_HOMEOWNER: "text-muted-hud",
  DRY_RUN_PENALTY: "text-plasma",
  RESCHEDULED_CONFIRMED: "text-volt",
};

// PHASE 1 — Digital Gatekeeping card
const PHASE1_ICONS = {
  "FAA / LAANC Airspace": Radio,
  "Pre-Rain 24h Lookback (ASTM C1153)": Cloud,
  "Solar Loading (12h Cloud Cover)": Wind,
  "Forecast 2h Buffer (Incoming Front)": Cloud,
  "Sustained Wind": Wind,
  "Utility & Power-Line GIS": Zap,
};
function Phase1Card({ job, onRun, busy }) {
  const ph = job.phase1_status;
  return (
    <HudCard scanline className="p-5 mb-4" data-testid="phase1-card">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest"><Shield size={13}/> Phase 1 · Digital Gatekeeping</div>
        {ph ? (
          <span className={`font-mono text-[10px] uppercase tracking-widest px-2 py-0.5 border ${ph.overall==="PASS"?"text-volt border-[#39FF14]/40":"text-plasma border-[#FF5500]/40"}`} data-testid="phase1-overall">{ph.overall}</span>
        ) : (
          <span className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">Not yet executed</span>
        )}
      </div>
      <p className="text-[12px] text-muted-hud font-body mb-3">Automatic cloud checks running against FAA UAS Data Exchange, Doppler radar, and GIS utility plane. The launch button stays software-locked until all three pass.</p>
      {ph && (
        <div className="space-y-2 mb-3">
          {ph.checks.map((c, i) => {
            const Icon = PHASE1_ICONS[c.name] || Shield;
            const accent = c.status==="PASS"?"text-volt":c.status==="WARN"?"text-teal":"text-plasma";
            return (
              <div key={i} className="hud-card p-3 flex items-start gap-3" data-testid={`phase1-check-${i}`}>
                <span className="corner-bl"/><span className="corner-br"/>
                <Icon size={14} className={`${accent} mt-0.5 shrink-0`}/>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-[11px] uppercase tracking-widest text-silver">{c.name}</span>
                    <span className={`font-mono text-[10px] uppercase tracking-widest ${accent}`}>{c.status}</span>
                  </div>
                  <div className="text-[11px] text-muted-hud font-body mt-0.5">{c.details}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <button onClick={onRun} disabled={busy} className="btn-hud" data-testid="run-phase1-btn">
        <Shield size={14}/> {busy ? "Querying clearance APIs…" : ph ? "RE-RUN PHASE 1" : "EXECUTE PHASE 1 CHECKS"}
      </button>
    </HudCard>
  );
}

// Compliance Audit Trail (immutable log viewer)
function AuditLogPanel({ jobId }) {
  const [log, setLog] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { if (open && !log) getJobAuditLog(jobId).then(setLog).catch(()=>setLog({events:[]})); }, [open, log, jobId]);
  return (
    <HudCard className="p-4 mb-4" data-testid="audit-log-panel">
      <button onClick={()=>setOpen(!open)} className="w-full flex items-center justify-between font-mono text-[11px] uppercase tracking-widest text-volt" data-testid="audit-toggle">
        <span className="flex items-center gap-2"><ScrollText size={13}/> Compliance Audit Trail — Immutable Log</span>
        <ChevronRight size={14} className={open?"rotate-90 transition-transform":"transition-transform"}/>
      </button>
      {open && (
        <div className="mt-3 space-y-1.5" data-testid="audit-events">
          {!log && <div className="font-mono text-[11px] text-muted-hud">Loading log…</div>}
          {log && log.events.length === 0 && <div className="font-mono text-[11px] text-muted-hud">No events recorded yet.</div>}
          {log && log.events.map((e, i) => (
            <div key={e.id} className="border border-[#00F0FF]/15 px-2 py-1 font-mono text-[10px] flex items-center justify-between gap-2">
              <span className="text-teal uppercase tracking-widest">{e.event}</span>
              <span className="text-muted-hud">{e.ts}</span>
            </div>
          ))}
          <div className="mt-2 font-mono text-[10px] text-volt uppercase tracking-widest">↑ Append-only · SOC2 exportable · No mutation allowed</div>
        </div>
      )}
    </HudCard>
  );
}

function SecurityBanner() {
  return (
    <div data-testid="security-banner" className="bg-[#10141D] border-y border-[#39FF14]/30 px-4 py-2 flex items-start gap-2 text-[11px] font-mono text-volt">
      <Shield size={12} className="mt-0.5 shrink-0"/>
      <div>
        <span className="text-volt font-bold">STRATEX™ SECURITY PROTOCOL ACTIVE:</span>
        <span className="text-silver"> Material costs, profit margins, overhead multipliers, and client financial data are subject to strict hardware-isolated AES-256 encryption. STRATEX operators and administrators have ZERO visibility into your proprietary business rules.</span>
      </div>
    </div>
  );
}

export default function ContractorPortal() {
  return <SecurityBanner />;
}

// JOBS LIST
export function ContractorJobs() {
  const [items, setItems] = useState(null);
  useEffect(()=>{ listContractorJobs().then(setItems).catch(()=>setItems([])); }, []);
  return (
    <>
      <SecurityBanner/>
      <div data-testid="contractor-jobs-page" className="px-4 md:px-10 py-6 max-w-[1500px] mx-auto">
        <div className="flex items-center justify-between mb-5 flex-wrap gap-3">
          <div>
            <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// CONTRACTOR PORTAL</div>
            <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.06em] md:tracking-[0.14em] text-silver">Job Pipeline</h1>
          </div>
          <Link to="/contractor/jobs/new" className="btn-hud" data-testid="new-job-btn"><Plus size={14}/> New Job</Link>
        </div>
        {items === null && <div className="text-muted-hud font-mono">Loading…</div>}
        {items && items.length === 0 && (
          <HudCard className="p-8 text-center">
            <p className="text-muted-hud">No jobs yet. Tap "New Job" to dispatch a drone capture.</p>
          </HudCard>
        )}
        {items && items.length > 0 && (
          <HudCard className="p-0 overflow-hidden">
            <div className="overflow-x-auto">
              <table className="hud-table">
                <thead><tr><th>Homeowner</th><th>Address</th><th>Type</th><th>Status</th><th>Total</th><th></th></tr></thead>
                <tbody data-testid="contractor-jobs-table">
                  {items.map((j)=>(
                    <tr key={j.id}>
                      <td className="text-silver whitespace-nowrap">
                        {j.homeowner_name}
                        <LaunchCountdownBadge scheduledAt={j.scheduled_launch_at} compact/>
                      </td>
                      <td className="text-muted-hud whitespace-nowrap">{j.property_address}</td>
                      <td><span className="tag-pill">{j.project_type}</span></td>
                      <td><span className={`font-mono uppercase tracking-widest text-[10px] ${STATUS_COLOR[j.status]||"text-muted-hud"}`}>{STATUS_LABEL[j.status]||j.status}</span></td>
                      <td className="text-teal whitespace-nowrap">{j.pricing?.final_total ? `$${j.pricing.final_total.toLocaleString(undefined,{minimumFractionDigits:2})}` : "—"}</td>
                      <td><Link to={`/contractor/jobs/${j.id}`} className="text-teal flex items-center gap-1 whitespace-nowrap" data-testid={`open-job-${j.id.slice(0,8)}`}>Open <ChevronRight size={12}/></Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </HudCard>
        )}
      </div>
    </>
  );
}

// NEW JOB
export function NewJob() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    property_address: "1411 Lexington Ave, Lexington, KY",
    lat: 38.0406, lon: -84.5037,
    homeowner_name: "Jane Smith",
    homeowner_email: "", homeowner_phone: "",
    project_type: "Insurance Claim", insurance_carrier: "State Farm",
    roof_style: "stratex_demo", notes: "",
  });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const payload = { ...form, homeowner_email: form.homeowner_email?.trim() || null };
      const j = await createJob(payload);
      toast.success("Job dispatched — running Phase 1 gatekeeping");
      navigate(`/contractor/jobs/${j.id}`);
    }
    catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };
  return (
    <>
      <SecurityBanner/>
      <div data-testid="new-job-page" className="px-4 md:px-10 py-6 max-w-3xl mx-auto">
        <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.08em] text-silver mb-1">New Job Dispatch</h1>
        <p className="text-sm text-muted-hud font-body mb-5">Enter the property + homeowner details. The drone job is queued to the STRATEX operator fleet immediately.</p>
        <HudCard scanline className="p-5 space-y-3">
          <div className="font-mono text-[11px] uppercase tracking-widest text-teal flex items-center gap-2 mb-1"><MapPin size={12}/> Property Location (Map Dispatch)</div>
          <MapPicker
            lat={form.lat}
            lon={form.lon}
            address={form.property_address}
            onChange={({ lat, lon, address }) => setForm((f)=>({ ...f, lat, lon, property_address: address || f.property_address }))}
          />
          <div><label className="hud-label">Property Address</label><input data-testid="job-address" className="hud-input" value={form.property_address} onChange={(e)=>setForm({...form, property_address: e.target.value})}/></div>
          <div><label className="hud-label">Homeowner Name</label><input data-testid="job-homeowner" className="hud-input" value={form.homeowner_name} onChange={(e)=>setForm({...form, homeowner_name: e.target.value})}/></div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="hud-label">Homeowner Email <span className="text-muted-hud">(optional)</span></label>
              <input data-testid="job-homeowner-email" className="hud-input" type="email" placeholder="homeowner@example.com" value={form.homeowner_email} onChange={(e)=>setForm({...form, homeowner_email: e.target.value})}/>
            </div>
            <div>
              <label className="hud-label">Homeowner Phone <span className="text-muted-hud">(E.164, optional)</span></label>
              <input data-testid="job-homeowner-phone" className="hud-input" type="tel" placeholder="+14155551234" value={form.homeowner_phone} onChange={(e)=>setForm({...form, homeowner_phone: e.target.value})}/>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="hud-label">Project Type</label>
              <select data-testid="job-type" className="hud-input" value={form.project_type} onChange={(e)=>setForm({...form, project_type:e.target.value})}>
                <option>Insurance Claim</option><option>Private Cash Pay</option>
              </select>
            </div>
            <div><label className="hud-label">Carrier</label><input className="hud-input" value={form.insurance_carrier} onChange={(e)=>setForm({...form, insurance_carrier: e.target.value})}/></div>
          </div>
          <div><label className="hud-label">Roof Topology</label>
            <select data-testid="job-roof-style" className="hud-input" value={form.roof_style} onChange={(e)=>setForm({...form, roof_style: e.target.value})}>
              <option value="stratex_demo">STRATEX Compound Demo (recommended)</option><option value="cross_hip">Cross-Hip</option><option value="hip">Hip</option><option value="gable">Front Gable</option><option value="l_shape">L-Shape</option><option value="dutch_gable">Dutch Gable</option>
            </select>
          </div>
          <button onClick={submit} disabled={busy} className="btn-hud w-full sm:w-auto" data-testid="job-submit"><Plus size={14}/> {busy?"Dispatching…":"DISPATCH TO FLEET"}</button>
        </HudCard>
      </div>
    </>
  );
}

// JOB DETAIL — captures + proposal + actions
const AGENT_PHASES = [
  { key: "forensic",       label: "FORENSIC AGENT",       sub: "Analyzing thermal δ + anomaly footprints" },
  { key: "validation",     label: "VALIDATION AGENT",     sub: "Cross-referencing facets ↔ telemetry mesh" },
  { key: "reconciliation", label: "RECONCILIATION AGENT", sub: "Applying Business Brain (AES-256 decrypt)" },
  { key: "jurisprudential",label: "JURISPRUDENTIAL AGENT",sub: "Overlaying local code + Xactimate tags" },
];

function AgentStream({ phaseIdx }) {
  return (
    <div data-testid="agent-stream" className="space-y-2 mt-4 text-left max-w-md mx-auto">
      {AGENT_PHASES.map((p, i) => {
        const done = i < phaseIdx;
        const active = i === phaseIdx;
        return (
          <div key={p.key} className={`hud-card p-3 flex items-center gap-3 transition-all ${active ? "border-[#00F0FF]" : ""}`}>
            <span className="corner-bl"/><span className="corner-br"/>
            <div className="w-6 h-6 flex items-center justify-center shrink-0">
              {done ? <CheckCircle2 size={18} className="text-volt"/> :
               active ? <Loader2 size={18} className="text-teal animate-spin"/> :
               <span className="w-2 h-2 bg-muted-hud/40 rounded-full"/>}
            </div>
            <div className="min-w-0">
              <div className={`font-mono text-[11px] tracking-widest uppercase ${done?"text-volt":active?"text-teal":"text-muted-hud"}`}>{p.label}</div>
              <div className="text-[11px] text-muted-hud font-body truncate">{p.sub}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function JobDetail() {
  const { id } = useParams();
  const isMobile = useIsMobile(900);
  const [job, setJob] = useState(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [busy, setBusy] = useState(false);
  const [streamPhase, setStreamPhase] = useState(-1);
  const [emailOpen, setEmailOpen] = useState(false);
  const [emailTo, setEmailTo] = useState("");
  const [emailBusy, setEmailBusy] = useState(false);
  const [primaryLayer, setPrimaryLayer] = useState("shingle"); // BEES: framing | shingle | metal | slate
  const [showGutters, setShowGutters] = useState(true);
  const [reschedule, setReschedule] = useState(null);
  const [weather, setWeather] = useState(null);
  const [notifyBusy, setNotifyBusy] = useState(false);

  const load = async () => { const j = await getContractorJob(id); setJob(j); const an=(j.mission?.anomalies||j.anomalies||[]); if(an[0]) setSelectedAnomaly(an[0]); };
  useEffect(()=>{ load().catch(()=>{}); }, [id]);

  // Auto-fetch reschedule suggestions when Phase 1 is blocked
  useEffect(() => {
    if (job?.status === "PHASE1_BLOCKED" && !reschedule) {
      rescheduleSuggestions(id).then(setReschedule).catch(()=>{});
    }
  }, [job?.status, id, reschedule]);

  // Mid-mission live weather pulse (poll every 30s while IN_FLIGHT)
  useEffect(() => {
    if (job?.status !== "IN_FLIGHT") { setWeather(null); return; }
    const fetchIt = () => weatherMonitor(id).then(setWeather).catch(()=>{});
    fetchIt();
    const t = setInterval(fetchIt, 30000);
    return () => clearInterval(t);
  }, [job?.status, id]);

  if (!job) return <><SecurityBanner/><div className="p-10 text-muted-hud font-mono">Loading…</div></>;

  const tele = job.roof_telemetry || {};
  const anomalies = job.mission?.anomalies || job.anomalies || [];
  const pricing = job.pricing;

  const run = async (fn, label) => { setBusy(true); try { await fn(); toast.success(label); await load(); } catch(e){ toast.error(e.response?.data?.detail || e.message); } finally { setBusy(false); } };

  const computeWithStream = async () => {
    setBusy(true);
    setStreamPhase(0);
    // Pace the visual through 4 agents while the (fast) compute call runs in parallel
    let phaseTimer = null;
    let phase = 0;
    const advance = () => {
      phase += 1;
      if (phase < AGENT_PHASES.length) {
        setStreamPhase(phase);
        phaseTimer = setTimeout(advance, 900);
      }
    };
    phaseTimer = setTimeout(advance, 900);
    try {
      await computeProposal(id);
      // ensure all phases show as done
      if (phaseTimer) clearTimeout(phaseTimer);
      setStreamPhase(AGENT_PHASES.length);
      // brief delay so user sees the volt-green completion
      await new Promise((r)=>setTimeout(r, 500));
      toast.success("PROPOSAL LOCKED");
      await load();
    } catch (e) {
      if (phaseTimer) clearTimeout(phaseTimer);
      toast.error(e.response?.data?.detail || e.message);
    } finally {
      setStreamPhase(-1);
      setBusy(false);
    }
  };

  const sendEmail = async () => {
    setEmailBusy(true);
    try {
      const r = await emailProposal(id, emailTo || job.homeowner_email || "", true);
      toast.success(r.mocked ? "EMAIL LOGGED (set RESEND_API_KEY to send)" : `Sent to ${r.to}`);
      setEmailOpen(false);
      await load();
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setEmailBusy(false); }
  };

  return (
    <>
      <SecurityBanner/>
      <div data-testid="job-detail-page" className="px-4 md:px-10 py-6 max-w-[1700px] mx-auto">
        <Link to="/contractor" className="font-mono text-[11px] uppercase tracking-widest text-muted-hud flex items-center gap-1 mb-2 hover:text-teal">← Pipeline</Link>
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// JOB {job.id.slice(0,8)}</div>
            <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.06em] text-silver" style={{ overflowWrap: "anywhere" }}>
              {job.homeowner_name}
              <LaunchCountdownBadge scheduledAt={job.scheduled_launch_at}/>
            </h1>
            <div className="font-mono text-xs text-muted-hud flex items-center gap-1 mt-1"><MapPin size={11}/>{job.property_address}</div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
            <span className={`led ${job.status==="PENDING_FIELD_CAPTURE"?"led-teal":(job.status==="DATA_CAPTURE_COMPLETE"||job.status==="PROPOSAL_READY")?"led-ok":"led-teal"} pulse-glow`}/>
            <span className={STATUS_COLOR[job.status]||"text-muted-hud"}>{STATUS_LABEL[job.status]||job.status}</span>
          </div>
        </div>

        {/* PHASE 1 — always show on pending/blocked or as a passed badge once captured */}
        {(job.status === "PENDING_PHASE1" || job.status === "PHASE1_BLOCKED" || job.status === "PENDING_FIELD_CAPTURE") && (
          <Phase1Card job={job} busy={busy} onRun={async ()=>{
            setBusy(true);
            try { await runPhase1(id); await load(); toast.success("Phase 1 complete"); }
            catch(e){ toast.error(e.response?.data?.detail || e.message); }
            finally { setBusy(false); }
          }}/>
        )}

        {/* RESCHEDULE — when Phase 1 blocked on weather */}
        {job.status === "PHASE1_BLOCKED" && reschedule && (
          <HudCard scanline className="p-5 mb-4" data-testid="reschedule-card">
            {job.scheduled_window_label && (
              <div data-testid="homeowner-scheduled-banner" className="mb-3 px-3 py-2 border border-[#39FF14]/60 flex items-center gap-2"
                   style={{ background: "rgba(57,255,20,0.06)", boxShadow: "0 0 12px rgba(57,255,20,0.18)" }}>
                <CheckCircle2 size={14} className="text-volt"/>
                <span className="font-mono text-[11px] uppercase tracking-widest text-volt">HOMEOWNER LOCKED IN: <span className="text-silver">{job.scheduled_window_label}</span></span>
                <span className="ml-auto font-mono text-[9px] text-muted-hud uppercase tracking-widest">via {job.scheduled_via === "homeowner_sms_reply" ? "SMS reply" : "manual"}</span>
              </div>
            )}
            <div className="flex items-center justify-between gap-2 flex-wrap mb-3">
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-teal">
                <Calendar size={13}/> Auto-Reschedule · Open-Meteo 7-day Forecast
              </div>
              <button
                onClick={async () => {
                  if (!job.homeowner_email && !job.homeowner_phone) {
                    toast.error("Add a homeowner email or phone number to this job first");
                    return;
                  }
                  setNotifyBusy(true);
                  try {
                    const r = await notifyHomeownerDelay(id, job.homeowner_email || null, job.homeowner_phone || null);
                    const parts = [];
                    if (r.to_email) parts.push(r.email?.mocked ? `email LOGGED (${r.to_email})` : `email sent to ${r.to_email}`);
                    if (r.to_phone) parts.push(r.sms?.mocked ? `SMS LOGGED (${r.to_phone})` : `SMS sent to ${r.to_phone}`);
                    toast.success(`${parts.join(" · ")} · ${r.windows_count} window${r.windows_count===1?"":"s"}`);
                    await load();
                  } catch (e) {
                    toast.error(e.response?.data?.detail || e.message);
                  } finally { setNotifyBusy(false); }
                }}
                disabled={notifyBusy || (job.delay_notified_to && job.delay_notified_sms)}
                className="btn-hud btn-hud-ghost text-[10px]"
                data-testid="notify-homeowner-delay-btn"
                title={job.delay_notified_to || job.delay_notified_sms ? "Already notified" : "Email + SMS the homeowner the next safe launch window"}
              >
                {notifyBusy
                  ? <><Loader2 size={12} className="animate-spin"/> SENDING…</>
                  : (job.delay_notified_to || job.delay_notified_sms)
                    ? <><CheckCircle2 size={12}/> NOTIFIED</>
                    : <><Mail size={12}/> Notify Homeowner of Delay</>}
              </button>
            </div>
            {reschedule.windows.length === 0 ? (
              <div className="font-mono text-[12px] text-plasma">No safe ASTM-compliant launch windows detected in the next 7 days for this property. Manual override or extended forecast review required.</div>
            ) : (
              <div className="space-y-2">
                <p className="text-[12px] text-muted-hud mb-2">The system identified the next {reschedule.windows.length} evening slots (19:00–22:00 local) where all 4 ASTM gates pass:</p>
                {reschedule.windows.map((w, i) => (
                  <div key={i} data-testid={`reschedule-window-${i}`} className="hud-card p-3 flex items-center justify-between gap-3">
                    <span className="corner-bl"/><span className="corner-br"/>
                    <div>
                      <div className="font-display text-sm uppercase tracking-widest text-volt">{w.label}</div>
                      <div className="font-mono text-[10px] text-muted-hud mt-0.5">
                        precip 24h: <span className="text-silver">{w.past_24h_precip_in}"</span> · clouds 12h: <span className="text-silver">{w.avg_cloud_12h_pct}%</span> · wind: <span className="text-silver">{w.wind_mph}mph</span>
                      </div>
                    </div>
                    <Calendar size={16} className="text-volt"/>
                  </div>
                ))}
              </div>
            )}
          </HudCard>
        )}

        {/* MID-MISSION LIVE WEATHER MONITOR — while IN_FLIGHT */}
        {weather && job.status === "IN_FLIGHT" && (
          <HudCard scanline alert={weather.abort_recommended} className="p-4 mb-4" data-testid="weather-monitor-card">
            <div className="flex items-center justify-between flex-wrap gap-3 mb-2">
              <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-teal">
                <Activity size={13} className={weather.abort_recommended ? "text-plasma pulse-alert" : "text-volt pulse-glow"}/>
                Live Weather Monitor · Polled every 30s
              </div>
              {weather.abort_recommended && (
                <span className="font-mono text-[10px] uppercase tracking-widest text-plasma border border-[#FF5500]/40 px-2 py-0.5">ABORT RECOMMENDED</span>
              )}
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-[11px]">
              <div>Past 24h precip: <span className="text-silver">{weather.past_24h_precip_in}"</span></div>
              <div>Cloud 12h: <span className="text-silver">{weather.avg_cloud_12h_pct}%</span></div>
              <div>Next 2h precip prob: <span className="text-silver">{weather.next2h_precip_prob_pct}%</span></div>
              <div>Wind: <span className="text-silver">{weather.current_wind_mph} mph</span></div>
            </div>
            <div className="text-[10px] font-mono text-muted-hud uppercase tracking-widest mt-2">as of {weather.as_of}</div>
          </HudCard>
        )}

        {/* Dry-run penalty banner */}
        {job.status === "DRY_RUN_PENALTY" && job.dry_run && (
          <HudCard alert className="p-5 mb-4" data-testid="dry-run-banner">
            <div className="flex items-center gap-2 font-mono text-[11px] uppercase tracking-widest text-plasma mb-2">
              <AlertTriangle size={14}/> Dry-Run Penalty · ${(job.dry_run.penalty_usd||150).toFixed(2)}
            </div>
            <p className="text-[13px] text-silver">Operator flagged this dispatch as <span className="text-plasma uppercase tracking-widest font-mono">{job.dry_run.reason.replace(/_/g," ")}</span>. The penalty has been added to next month's invoice. Audit recorded {job.dry_run.flagged_at}.</p>
            {job.dry_run.notes && <p className="text-[11px] text-muted-hud font-mono mt-2">NOTES: {job.dry_run.notes}</p>}
          </HudCard>
        )}

        {/* Audit log panel — always available once phase1 executed */}
        {job.phase1_status && <AuditLogPanel jobId={id}/>}

        {/* Awaiting capture */}
        {job.status === "PENDING_FIELD_CAPTURE" && (
          <HudCard scanline className="p-8 text-center">
            <p className="text-silver font-heading text-lg">Awaiting Operator Capture</p>
            <p className="text-muted-hud text-sm mt-2">Phase 1 cleared. Your STRATEX fleet operator will pick up this job from their terminal, run the on-site safety checks (Phase 2) and hardware diagnostics (Phase 3), and authorize the aerial reconnaissance.</p>
          </HudCard>
        )}

        {/* Capture complete views */}
        {(job.status === "DATA_CAPTURE_COMPLETE" || job.status === "PROPOSAL_READY" || job.status === "AUDIT_APPROVED" || job.status === "SENT_TO_HOMEOWNER") && (
          <>
            {/* === STRATEX VISION ADVANCED DIAGNOSTICS === */}
            <HudCard scanline className="p-0 mb-4 overflow-hidden" style={{ background: "#0B0F19" }}>
              {/* Canvas header bar */}
              <div className="absolute top-2 left-1/2 -translate-x-1/2 z-20 pointer-events-none border border-[#00F0FF]/40 px-4 py-1.5"
                   style={{ background: "rgba(11,15,25,0.85)", backdropFilter: "blur(8px)", boxShadow: "0 0 16px rgba(0,240,255,0.25)" }}>
                <span className="font-display text-[13px] tracking-[0.18em] uppercase text-silver">STRATEX™ Vision: <span className="text-teal">Advanced Diagnostics</span></span>
              </div>

              <div className="relative" style={{ minHeight: isMobile ? 520 : 620 }}>
                {/* 3D canvas fills the entire HudCard */}
                <RoofModel3D
                  telemetry={tele}
                  anomalies={anomalies}
                  highlightAnomalyId={selectedAnomaly?.id}
                  onSelectAnomaly={(a)=>setSelectedAnomaly(a)}
                  height={isMobile ? 520 : 620}
                  showLabels={!isMobile}
                  showDimensions={!isMobile}
                  layers={null}
                  primaryLayer={primaryLayer}
                  showGutters={showGutters}
                />

                {/* BEES Layer Controller — 4 mutually-exclusive primary radios + 1 secondary gutter toggle */}
                <div className="absolute top-14 left-1/2 -translate-x-1/2 z-20 flex gap-1.5 mt-12 pointer-events-auto items-center" data-testid="layer-toggle-bar">
                  {[
                    { k: "framing", label: "FRAMING", color: "#5FF4FF" },
                    { k: "shingle", label: "SHINGLE", color: "#4CC3FF" },
                    { k: "metal",   label: "METAL",   color: "#5FF4FF" },
                    { k: "slate",   label: "SLATE",   color: "#D99DFF" },
                  ].map((t) => {
                    const active = primaryLayer === t.k;
                    return (
                      <button
                        key={t.k}
                        data-testid={`layer-toggle-${t.k}`}
                        aria-pressed={active}
                        onClick={() => setPrimaryLayer(t.k)}
                        className="px-2 py-1 font-mono text-[10px] uppercase tracking-widest border transition-all"
                        style={{
                          background: active ? `${t.color}22` : "rgba(11,15,25,0.85)",
                          color: active ? t.color : "#94A3B8",
                          borderColor: active ? t.color : "rgba(0,240,255,0.25)",
                          boxShadow: active ? `0 0 10px ${t.color}66, inset 0 0 6px ${t.color}33` : "none",
                          textShadow: active ? `0 0 6px ${t.color}` : "none",
                          backdropFilter: "blur(8px)",
                        }}
                      >
                        <span className="w-1.5 h-1.5 inline-block mr-1 align-middle" style={{ background: t.color, boxShadow: `0 0 4px ${t.color}` }}/>
                        {t.label}
                      </button>
                    );
                  })}
                  {/* Vertical divider */}
                  <span className="h-4 w-px bg-[#00F0FF]/30 mx-1"/>
                  {/* Secondary gutter overlay — independent of primary */}
                  <button
                    data-testid="layer-toggle-gutters"
                    aria-pressed={showGutters}
                    onClick={() => setShowGutters((g) => !g)}
                    className="px-2 py-1 font-mono text-[10px] uppercase tracking-widest border transition-all"
                    style={{
                      background: showGutters ? "#FF8A1F22" : "rgba(11,15,25,0.85)",
                      color: showGutters ? "#FF8A1F" : "#94A3B8",
                      borderColor: showGutters ? "#FF8A1F" : "rgba(0,240,255,0.25)",
                      boxShadow: showGutters ? "0 0 10px #FF8A1F66, inset 0 0 6px #FF8A1F33" : "none",
                      textShadow: showGutters ? "0 0 6px #FF8A1F" : "none",
                      backdropFilter: "blur(8px)",
                    }}
                  >
                    <span className="w-1.5 h-1.5 inline-block mr-1 align-middle" style={{ background: "#FF8A1F", boxShadow: "0 0 4px #FF8A1F" }}/>
                    GUTTERS {showGutters ? "ON" : "OFF"}
                  </button>
                </div>

                {/* Top-left: Project Identity card */}
                <div className="absolute top-14 left-4 z-10 pointer-events-none">
                  <ProjectIdentityCard project={{
                    id_short: `AD-${job.id.slice(0,5).toUpperCase()}`,
                    principal: job.contractor_company || "STRATEX Contractor",
                    property: job.property_address || "—",
                  }}/>
                </div>

                {/* Top-right: Forensic Overlay PiP */}
                {selectedAnomaly && !isMobile && (
                  <div className="absolute top-14 right-4 z-10 w-[320px] max-w-[34vw]">
                    <ForensicOverlay anomaly={selectedAnomaly}/>
                  </div>
                )}

                {/* Bottom-left: STRATEX Quant Estimation */}
                <div className="absolute bottom-12 left-4 z-10 pointer-events-none">
                  <QuantEstimationCard telemetry={tele}/>
                </div>

                {/* Bottom-right: Anomaly Monetization */}
                <div className="absolute bottom-12 right-4 z-10 pointer-events-none">
                  <AnomalyMonetizationCard
                    anomaly={selectedAnomaly}
                    lineItem={selectedAnomaly && pricing ? {
                      total: (anomalies.reduce((s, a) => s + (a.area_affected_sf || 0), 0) > 0)
                        ? (pricing.final_total || 0) * ((selectedAnomaly.area_affected_sf || 0) / anomalies.reduce((s, a) => s + (a.area_affected_sf || 0), 0))
                        : 0
                    } : null}
                  />
                </div>

                {/* Anomaly ID floating tag (top-center upper third) */}
                {selectedAnomaly && (
                  <div className="absolute top-14 left-1/2 -translate-x-1/2 z-10 pointer-events-none border border-[#00F0FF]/60 px-3 py-1 font-mono text-[11px] uppercase tracking-widest text-teal"
                       style={{ background: "rgba(11,15,25,0.85)", backdropFilter: "blur(8px)", boxShadow: "0 0 12px rgba(0,240,255,0.35)" }}>
                    Anomaly ID: <span className="text-silver">{selectedAnomaly.id}</span>
                  </div>
                )}
              </div>
            </HudCard>

            {/* Expert Panel Certification (validation gates from roof_telemetry) */}
            {tele?.validation && (
              <div className="mb-4" data-testid="contractor-validation-block">
                <ValidationReport validation={tele.validation} />
              </div>
            )}

            {/* === Anomaly field & spatial mesh details (collapsed beneath) === */}
            <div className={`grid ${isMobile ? "grid-cols-1" : "grid-cols-[1fr_320px]"} gap-3 mb-4`}>
              <HudCard className="p-4">
                <div className="flex items-center gap-2 mb-2 text-teal"><Box size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">Spatial Mesh Telemetry</span></div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 font-mono text-sm">
                  <Row label="Total SF" v={tele.totals?.total_sf}/>
                  <Row label="Squares" v={tele.totals?.squares}/>
                  <Row label="Ridges LF" v={tele.totals?.ridges_lf}/>
                  <Row label="Valleys LF" v={tele.totals?.valleys_lf} accent="orange"/>
                  <Row label="Hips LF" v={tele.totals?.hips_lf}/>
                  <Row label="Eaves LF" v={tele.totals?.eaves_lf}/>
                  <Row label="Primary Pitch" v={tele.pitch}/>
                  <Row label="RTK Precision" v={`${tele.rtk_precision_cm} cm`} accent="volt"/>
                </div>
              </HudCard>
              <HudCard className="p-3">
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Anomaly Field — Tap to inspect</div>
                <AnomalySelector anomalies={anomalies} selectedId={selectedAnomaly?.id} onSelect={setSelectedAnomaly}/>
                {selectedAnomaly && isMobile && (
                  <div className="mt-3">
                    <ForensicOverlay anomaly={selectedAnomaly}/>
                  </div>
                )}
              </HudCard>
            </div>

            {/* Pricing actions */}
            {!pricing && job.status === "DATA_CAPTURE_COMPLETE" && (
              <HudCard className="p-6 mb-4 text-center">
                <div className="flex items-center justify-center gap-2 mb-3 text-teal"><Lock size={14}/><span className="font-mono text-[11px] uppercase tracking-widest">Encrypted Business Brain Standing By</span></div>
                <p className="text-muted-hud text-sm mb-4">Apply your private Materials Configuration (overhead %, profit margin, labor rate, insurance supplement) to generate the binding homeowner proposal.</p>
                <button onClick={computeWithStream} disabled={busy} className="btn-hud" data-testid="compute-proposal-btn">
                  <Calculator size={14}/> {busy?"COMPUTING…":"COMPUTE PROPOSAL"}
                </button>
                {streamPhase >= 0 && <AgentStream phaseIdx={streamPhase}/>}
              </HudCard>
            )}

            {pricing && (
              <HudCard scanline className="p-5 mb-4">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                  <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest"><DollarSign size={14}/> Locked Proposal — {pricing.lock_mode}</div>
                  <div className="flex gap-2 flex-wrap">
                    <a href={contractorPdfUrl(id)} target="_blank" rel="noreferrer" className="btn-hud btn-hud-ghost" data-testid="job-pdf-btn"><Download size={14}/> PDF</a>
                    <button onClick={()=>{setEmailTo(job.homeowner_email||""); setEmailOpen(true);}} className="btn-hud btn-hud-ghost" data-testid="email-proposal-btn"><Mail size={14}/> Email</button>
                    {job.status === "PROPOSAL_READY" && <button onClick={()=>run(()=>auditApprove(id), "Audit approved")} disabled={busy} className="btn-hud" data-testid="audit-approve-btn"><CheckCircle2 size={14}/> Audit Approved</button>}
                    {job.status === "AUDIT_APPROVED" && <button onClick={()=>run(()=>markSent(id), "Marked sent")} disabled={busy} className="btn-hud btn-hud-alert" data-testid="mark-sent-btn"><Send size={14}/> Mark Sent</button>}
                  </div>
                </div>

                {emailOpen && (
                  <HudCard alert className="p-4 mb-3" data-testid="email-dialog">
                    <div className="font-mono text-[11px] uppercase tracking-widest text-plasma mb-2 flex items-center gap-2"><Mail size={12}/> Email Proposal to Homeowner</div>
                    <input data-testid="email-to-input" className="hud-input mb-3" placeholder="homeowner@example.com" value={emailTo} onChange={(e)=>setEmailTo(e.target.value)}/>
                    <div className="flex gap-2">
                      <button onClick={sendEmail} disabled={emailBusy || !emailTo} className="btn-hud" data-testid="email-send-confirm">{emailBusy?"Sending…":"Send Proposal PDF"}</button>
                      <button onClick={()=>setEmailOpen(false)} className="btn-hud btn-hud-ghost">Cancel</button>
                    </div>
                    {job.emailed_to && <div className="mt-2 text-[10px] font-mono text-muted-hud uppercase tracking-widest">Last sent: {job.emailed_to} • {job.emailed_at}</div>}
                  </HudCard>
                )}

                <div className="overflow-x-auto">
                  <table className="hud-table">
                    <thead><tr><th>Line Item</th><th>Qty</th><th>Unit</th><th>$/Unit</th><th>Total</th><th>Tag</th></tr></thead>
                    <tbody data-testid="proposal-table">
                      {pricing.line_items.map((li, i)=>(
                        <tr key={i}><td className="text-silver">{li.description}</td><td>{li.qty}</td><td className="text-muted-hud">{li.unit}</td><td>${li.unit_price.toFixed(2)}</td><td className="text-teal">${li.total.toLocaleString(undefined,{minimumFractionDigits:2})}</td><td><span className="tag-pill">{li.xactimate_tag}</span></td></tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="hud-divider my-3"/>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                  <DataReadout label="Subtotal" value={`$${pricing.subtotal.toLocaleString(undefined,{minimumFractionDigits:2})}`} testid="sum-subtotal"/>
                  <DataReadout label={`Overhead ${(pricing.overhead_rate*100).toFixed(0)}%`} value={`$${pricing.overhead.toLocaleString(undefined,{minimumFractionDigits:2})}`}/>
                  <DataReadout label={`Profit ${(pricing.profit_rate*100).toFixed(0)}%`} value={`$${pricing.profit.toLocaleString(undefined,{minimumFractionDigits:2})}`}/>
                  {pricing.insurance_supplement_rate>0 && <DataReadout label={`Ins Supp ${(pricing.insurance_supplement_rate*100).toFixed(0)}%`} value={`$${pricing.insurance_supplement.toLocaleString(undefined,{minimumFractionDigits:2})}`} accent="orange"/>}
                  <DataReadout label="Final Total" value={`$${pricing.final_total.toLocaleString(undefined,{minimumFractionDigits:2})}`} accent="orange" testid="sum-final"/>
                </div>
              </HudCard>
            )}
          </>
        )}
      </div>
    </>
  );
}

function Row({ label, v, accent }) {
  const c = accent==="orange"?"text-plasma":accent==="volt"?"text-volt":"text-teal";
  return (<div className="flex justify-between"><span className="text-muted-hud uppercase text-[10px] tracking-widest">{label}</span><span className={`${c} font-mono`}>{v ?? "—"}</span></div>);
}

// MATERIALS / BUSINESS BRAIN
import MaterialConfigurator from "@/components/MaterialConfigurator";

export function MaterialsConfig() {
  const [m, setM] = useState(null);
  const [busy, setBusy] = useState(false);
  const [tab, setTab] = useState("expert"); // "expert" | "legacy" | "pricing"
  useEffect(()=>{ getMaterials().then(setM).catch(()=>setM({})); }, []);
  const set = (k, v) => setM({ ...m, [k]: v });
  const save = async () => { setBusy(true); try { await saveMaterials(m); toast.success("Business Brain saved (encrypted at rest)"); } catch(e){ toast.error(e.response?.data?.detail || e.message); } finally { setBusy(false); } };
  if (!m) return <><SecurityBanner/><div className="p-10 text-muted-hud font-mono">Loading…</div></>;

  // Material picks live alongside existing free-text fields, under a structured key
  // so the legacy form fields (brand strings) stay queryable for backwards compatibility.
  const matSelection = m.materials_selection || { system: "asphalt_shingle_system", picks: {}, custom_text: "" };

  return (
    <>
      <SecurityBanner/>
      <div data-testid="materials-config-page" className="px-4 md:px-10 py-6 max-w-5xl mx-auto">
        <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest mb-2"><Lock size={14}/> ENCRYPTED BUSINESS BRAIN</div>
        <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.06em] text-silver mb-4">Business Brain</h1>

        {/* TABBED INTERFACE — Expert Configurator (new primary) · Legacy Free-Text · Encrypted Pricing */}
        <div className="flex flex-wrap gap-2 mb-5 border-b border-[#00F0FF]/20 pb-3" data-testid="business-brain-tabs">
          <TabButton active={tab==="expert"}  onClick={()=>setTab("expert")}  testid="bb-tab-expert">
            🧠 MATERIAL EXPERT CONFIGURATOR
          </TabButton>
          <TabButton active={tab==="pricing"} onClick={()=>setTab("pricing")} testid="bb-tab-pricing">
            🔒 ENCRYPTED PRICING & MULTIPLIERS
          </TabButton>
          <TabButton active={tab==="legacy"}  onClick={()=>setTab("legacy")}  testid="bb-tab-legacy">
            ⚠ LEGACY FREE-TEXT BRANDS (DEPRECATED)
          </TabButton>
        </div>

        {/* ============ TAB 1 — EXPERT CONFIGURATOR ============ */}
        {tab === "expert" && (
          <div data-testid="bb-tab-content-expert">
            <div data-testid="material-configurator">
              <MaterialConfigurator
                initialSelection={matSelection}
                onChange={(sel) => set("materials_selection", sel)}
              />
            </div>
            <div className="mt-4">
              <CaliperUpload onReading={(r) => set("measured_thickness_mm", r.thickness_mm)} />
            </div>
            {/* Live "active selections" mini-summary */}
            <HudCard className="p-4 mt-4">
              <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-2">// ACTIVE EXPERT SELECTIONS</div>
              <div className="grid md:grid-cols-2 gap-2 text-[11px] font-mono">
                <div><span className="text-muted-hud">SYSTEM:</span> <span className="text-silver">{matSelection.system}</span></div>
                <div><span className="text-muted-hud">PICKS:</span> <span className="text-silver">{Object.keys(matSelection.picks || {}).length} fields</span></div>
                {matSelection.picks && Object.entries(matSelection.picks).filter(([,v])=>v).slice(0, 6).map(([k,v]) => (
                  <div key={k}><span className="text-muted-hud">{k}:</span> <span className="text-silver">{String(v).slice(0,42)}</span></div>
                ))}
              </div>
            </HudCard>
          </div>
        )}

        {/* ============ TAB 2 — ENCRYPTED PRICING ============ */}
        {tab === "pricing" && (
          <div data-testid="bb-tab-content-pricing">
            <HudCard alert className="p-5 mb-4">
              <div className="font-mono text-[11px] uppercase tracking-widest text-plasma mb-3 flex items-center gap-2"><Lock size={12}/> Private Wholesale Unit Prices (AES-256 encrypted)</div>
              <div className="grid md:grid-cols-2 gap-3">
                <NumField label="Shingle / Bundle ($)" value={m.shingle_bundle_price} onChange={(v)=>set("shingle_bundle_price", v)} testid="mat-shingle-price"/>
                <NumField label="Underlayment / Square ($)" value={m.underlayment_square_price} onChange={(v)=>set("underlayment_square_price", v)}/>
                <NumField label="Ice & Water / Roll ($)" value={m.ice_water_roll_price} onChange={(v)=>set("ice_water_roll_price", v)}/>
                <NumField label="Ridge Cap / Bundle ($)" value={m.ridge_cap_bundle_price} onChange={(v)=>set("ridge_cap_bundle_price", v)}/>
                <NumField label="Starter / Bundle ($)" value={m.starter_bundle_price} onChange={(v)=>set("starter_bundle_price", v)}/>
                <NumField label="Drip Edge / LF ($)" value={m.drip_edge_lf_price} onChange={(v)=>set("drip_edge_lf_price", v)}/>
                <NumField label="Fasteners / Square ($)" value={m.fastener_square_price} onChange={(v)=>set("fastener_square_price", v)}/>
                <NumField label="OSB Sheet ($)" value={m.osb_sheet_price} onChange={(v)=>set("osb_sheet_price", v)}/>
              </div>
            </HudCard>
            <HudCard alert className="p-5 mb-4">
              <div className="font-mono text-[11px] uppercase tracking-widest text-plasma mb-3 flex items-center gap-2"><Lock size={12}/> Confidential Business Multipliers (Blind Multipliers)</div>
              <div className="grid md:grid-cols-2 gap-3">
                <NumField label="Overhead (%)" value={m.overhead_pct} onChange={(v)=>set("overhead_pct", v)} testid="mat-overhead"/>
                <NumField label="Net Profit Margin (%)" value={m.profit_margin_pct} onChange={(v)=>set("profit_margin_pct", v)} testid="mat-profit"/>
                <NumField label="Labor Rate / Hour ($)" value={m.labor_rate_per_hour} onChange={(v)=>set("labor_rate_per_hour", v)}/>
                <NumField label="Labor Rate / Square ($)" value={m.labor_rate_per_square} onChange={(v)=>set("labor_rate_per_square", v)}/>
                <NumField label="Insurance Supplement (%)" value={m.insurance_supplement_multiplier_pct} onChange={(v)=>set("insurance_supplement_multiplier_pct", v)} testid="mat-supp"/>
              </div>
            </HudCard>
          </div>
        )}

        {/* ============ TAB 3 — LEGACY (DEPRECATED) ============ */}
        {tab === "legacy" && (
          <div data-testid="bb-tab-content-legacy">
            <HudCard alert className="p-4 mb-4 border-2" style={{borderColor:"#FF5400"}}>
              <div className="font-mono text-[10px] uppercase tracking-widest text-plasma mb-1">⚠ DEPRECATION NOTICE</div>
              <p className="text-[12px] text-silver font-body">
                This free-text catalog has been superseded by the <b className="text-teal">Material Expert Configurator</b>.
                Existing values are preserved for backwards compatibility but will be removed in v4.0. Please migrate your
                selections to the Expert tab.
              </p>
            </HudCard>
            <HudCard className="p-5 mb-4 opacity-80">
              <div className="font-mono text-[11px] uppercase tracking-widest text-muted-hud mb-3 flex items-center gap-2"><Layers size={12}/> Legacy Product Catalog</div>
              <div className="grid md:grid-cols-2 gap-3">
                <Field label="Shingle Brand" value={m.shingle_brand} onChange={(v)=>set("shingle_brand", v)} testid="mat-shingle-brand"/>
                <Field label="Underlayment Brand" value={m.underlayment_brand} onChange={(v)=>set("underlayment_brand", v)}/>
                <Field label="Ice & Water Shield" value={m.ice_water_brand} onChange={(v)=>set("ice_water_brand", v)}/>
                <Field label="Ridge Vent" value={m.ridge_vent_brand} onChange={(v)=>set("ridge_vent_brand", v)}/>
                <Field label="Starter Strip" value={m.starter_brand} onChange={(v)=>set("starter_brand", v)}/>
                <Field label="Drip Edge Color" value={m.drip_edge_color} onChange={(v)=>set("drip_edge_color", v)}/>
                <Field label="Fastener Type" value={m.fastener_type} onChange={(v)=>set("fastener_type", v)}/>
                <NumField label="Measured Shingle Thickness (mm)" value={m.measured_thickness_mm} onChange={(v)=>set("measured_thickness_mm", v)} testid="mat-thickness-mm"/>
              </div>
            </HudCard>
          </div>
        )}

        <button onClick={save} disabled={busy} className="btn-hud mt-2" data-testid="mat-save"><FileText size={14}/> {busy?"Encrypting…":"SAVE BUSINESS BRAIN"}</button>
      </div>
    </>
  );
}

function TabButton({ active, onClick, testid, children }) {
  return (
    <button
      data-testid={testid}
      aria-pressed={active}
      onClick={onClick}
      className="px-4 py-2 font-mono text-[10.5px] uppercase tracking-widest border transition-all"
      style={{
        background: active ? "rgba(0,245,212,0.10)" : "rgba(11,15,25,0.85)",
        color: active ? "#00F5D4" : "#94A3B8",
        borderColor: active ? "#00F5D4" : "rgba(0,240,255,0.25)",
        boxShadow: active ? "0 0 10px rgba(0,245,212,0.35), inset 0 0 6px rgba(0,245,212,0.18)" : "none",
      }}
    >
      {children}
    </button>
  );
}

function Field({ label, value, onChange, testid }) {
  return (<div><label className="hud-label">{label}</label><input data-testid={testid} className="hud-input" value={value || ""} onChange={(e)=>onChange(e.target.value)}/></div>);
}
function NumField({ label, value, onChange, testid }) {
  return (<div><label className="hud-label">{label}</label><input data-testid={testid} type="number" step="0.01" className="hud-input font-mono" value={value ?? 0} onChange={(e)=>onChange(parseFloat(e.target.value)||0)}/></div>);
}
