import React, { useEffect, useState } from "react";
import { Link, useParams, useNavigate } from "react-router-dom";
import { HudCard, DataReadout } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ForensicOverlay, { AnomalySelector } from "@/components/ForensicOverlay";
import useIsMobile from "@/hooks/use-is-mobile";
import { useAuth } from "@/lib/auth";
import {
  listContractorJobs, createJob, getContractorJob, computeProposal, auditApprove, markSent, contractorPdfUrl,
  getMaterials, saveMaterials,
} from "@/lib/api";
import { Plus, MapPin, Lock, FileText, Download, Shield, DollarSign, CheckCircle2, Send, Layers, Box, ChevronRight, Calculator } from "lucide-react";
import { toast } from "sonner";

const STATUS_LABEL = {
  DRAFT: "Draft", PENDING_FIELD_CAPTURE: "Awaiting Field Capture",
  IN_FLIGHT: "Aerial Recon In Progress", DATA_CAPTURE_COMPLETE: "Capture Complete",
  PROPOSAL_READY: "Proposal Ready", AUDIT_APPROVED: "Audit Approved", SENT_TO_HOMEOWNER: "Sent",
};
const STATUS_COLOR = {
  PENDING_FIELD_CAPTURE: "text-teal", IN_FLIGHT: "text-teal", DATA_CAPTURE_COMPLETE: "text-volt",
  PROPOSAL_READY: "text-teal", AUDIT_APPROVED: "text-volt", SENT_TO_HOMEOWNER: "text-muted-hud",
};

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
                      <td className="text-silver whitespace-nowrap">{j.homeowner_name}</td>
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
    roof_style: "cross_hip", notes: "",
  });
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try { const j = await createJob(form); toast.success("Job dispatched to operator queue"); navigate(`/contractor/jobs/${j.id}`); }
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
          <div><label className="hud-label">Property Address</label><input data-testid="job-address" className="hud-input" value={form.property_address} onChange={(e)=>setForm({...form, property_address: e.target.value})}/></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="hud-label">Latitude</label><input data-testid="job-lat" type="number" step="0.0001" className="hud-input" value={form.lat} onChange={(e)=>setForm({...form, lat:parseFloat(e.target.value)})}/></div>
            <div><label className="hud-label">Longitude</label><input data-testid="job-lon" type="number" step="0.0001" className="hud-input" value={form.lon} onChange={(e)=>setForm({...form, lon:parseFloat(e.target.value)})}/></div>
          </div>
          <div><label className="hud-label">Homeowner Name</label><input data-testid="job-homeowner" className="hud-input" value={form.homeowner_name} onChange={(e)=>setForm({...form, homeowner_name: e.target.value})}/></div>
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
              <option value="cross_hip">Cross-Hip</option><option value="hip">Hip</option><option value="gable">Front Gable</option><option value="l_shape">L-Shape</option><option value="dutch_gable">Dutch Gable</option>
            </select>
          </div>
          <button onClick={submit} disabled={busy} className="btn-hud w-full sm:w-auto" data-testid="job-submit"><Plus size={14}/> {busy?"Dispatching…":"DISPATCH TO FLEET"}</button>
        </HudCard>
      </div>
    </>
  );
}

// JOB DETAIL — captures + proposal + actions
export function JobDetail() {
  const { id } = useParams();
  const isMobile = useIsMobile(900);
  const [job, setJob] = useState(null);
  const [selectedAnomaly, setSelectedAnomaly] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = async () => { const j = await getContractorJob(id); setJob(j); const an=(j.mission?.anomalies||j.anomalies||[]); if(an[0]) setSelectedAnomaly(an[0]); };
  useEffect(()=>{ load().catch(()=>{}); }, [id]);

  if (!job) return <><SecurityBanner/><div className="p-10 text-muted-hud font-mono">Loading…</div></>;

  const tele = job.roof_telemetry || {};
  const anomalies = job.mission?.anomalies || job.anomalies || [];
  const pricing = job.pricing;

  const run = async (fn, label) => { setBusy(true); try { await fn(); toast.success(label); await load(); } catch(e){ toast.error(e.response?.data?.detail || e.message); } finally { setBusy(false); } };

  return (
    <>
      <SecurityBanner/>
      <div data-testid="job-detail-page" className="px-4 md:px-10 py-6 max-w-[1700px] mx-auto">
        <Link to="/contractor" className="font-mono text-[11px] uppercase tracking-widest text-muted-hud flex items-center gap-1 mb-2 hover:text-teal">← Pipeline</Link>
        <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
          <div>
            <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// JOB {job.id.slice(0,8)}</div>
            <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.06em] text-silver" style={{ overflowWrap: "anywhere" }}>{job.homeowner_name}</h1>
            <div className="font-mono text-xs text-muted-hud flex items-center gap-1 mt-1"><MapPin size={11}/>{job.property_address}</div>
          </div>
          <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
            <span className={`led ${job.status==="PENDING_FIELD_CAPTURE"?"led-teal":(job.status==="DATA_CAPTURE_COMPLETE"||job.status==="PROPOSAL_READY")?"led-ok":"led-teal"} pulse-glow`}/>
            <span className={STATUS_COLOR[job.status]||"text-muted-hud"}>{STATUS_LABEL[job.status]||job.status}</span>
          </div>
        </div>

        {/* Awaiting capture */}
        {job.status === "PENDING_FIELD_CAPTURE" && (
          <HudCard scanline className="p-8 text-center">
            <p className="text-silver font-heading text-lg">Awaiting Operator Capture</p>
            <p className="text-muted-hud text-sm mt-2">Your STRATEX fleet operator will pick up this job from their terminal, run the pre-flight checklist, and authorize the aerial reconnaissance.</p>
          </HudCard>
        )}

        {/* Capture complete views */}
        {(job.status === "DATA_CAPTURE_COMPLETE" || job.status === "PROPOSAL_READY" || job.status === "AUDIT_APPROVED" || job.status === "SENT_TO_HOMEOWNER") && (
          <>
            <HudCard scanline className="p-3 mb-4">
              <div className={`grid ${isMobile ? "grid-cols-1" : "grid-cols-[260px_1fr_310px]"} gap-3`}>
                <div className="space-y-3">
                  <HudCard className="p-4">
                    <div className="flex items-center gap-2 mb-2 text-teal"><Box size={14}/><span className="font-mono text-[10px] uppercase tracking-widest">Spatial Mesh</span></div>
                    <div className="space-y-1 font-mono text-sm">
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
                </div>
                <div className="hud-card overflow-hidden">
                  <span className="corner-bl"/><span className="corner-br"/>
                  <RoofModel3D telemetry={tele} anomalies={anomalies} highlightAnomalyId={selectedAnomaly?.id} onSelectAnomaly={(a)=>setSelectedAnomaly(a)} height={isMobile?380:560} showLabels={!isMobile}/>
                </div>
                <div className="space-y-3">
                  <ForensicOverlay anomaly={selectedAnomaly}/>
                  <HudCard className="p-3">
                    <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud mb-2">Anomaly Field</div>
                    <AnomalySelector anomalies={anomalies} selectedId={selectedAnomaly?.id} onSelect={setSelectedAnomaly}/>
                  </HudCard>
                </div>
              </div>
            </HudCard>

            {/* Pricing actions */}
            {!pricing && job.status === "DATA_CAPTURE_COMPLETE" && (
              <HudCard className="p-6 mb-4 text-center">
                <div className="flex items-center justify-center gap-2 mb-3 text-teal"><Lock size={14}/><span className="font-mono text-[11px] uppercase tracking-widest">Encrypted Business Brain Standing By</span></div>
                <p className="text-muted-hud text-sm mb-4">Apply your private Materials Configuration (overhead %, profit margin, labor rate, insurance supplement) to generate the binding homeowner proposal.</p>
                <button onClick={()=>run(()=>computeProposal(id), "Proposal computed")} disabled={busy} className="btn-hud" data-testid="compute-proposal-btn">
                  <Calculator size={14}/> {busy?"…":"COMPUTE PROPOSAL"}
                </button>
              </HudCard>
            )}

            {pricing && (
              <HudCard scanline className="p-5 mb-4">
                <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
                  <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest"><DollarSign size={14}/> Locked Proposal — {pricing.lock_mode}</div>
                  <div className="flex gap-2">
                    <a href={contractorPdfUrl(id)} target="_blank" rel="noreferrer" className="btn-hud btn-hud-ghost" data-testid="job-pdf-btn"><Download size={14}/> PDF</a>
                    {job.status === "PROPOSAL_READY" && <button onClick={()=>run(()=>auditApprove(id), "Audit approved")} disabled={busy} className="btn-hud" data-testid="audit-approve-btn"><CheckCircle2 size={14}/> Audit Approved</button>}
                    {job.status === "AUDIT_APPROVED" && <button onClick={()=>run(()=>markSent(id), "Marked sent")} disabled={busy} className="btn-hud btn-hud-alert" data-testid="mark-sent-btn"><Send size={14}/> Mark Sent</button>}
                  </div>
                </div>
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
export function MaterialsConfig() {
  const [m, setM] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(()=>{ getMaterials().then(setM).catch(()=>setM({})); }, []);
  const set = (k, v) => setM({ ...m, [k]: v });
  const save = async () => { setBusy(true); try { await saveMaterials(m); toast.success("Business Brain saved (encrypted at rest)"); } catch(e){ toast.error(e.response?.data?.detail || e.message); } finally { setBusy(false); } };
  if (!m) return <><SecurityBanner/><div className="p-10 text-muted-hud font-mono">Loading…</div></>;
  return (
    <>
      <SecurityBanner/>
      <div data-testid="materials-config-page" className="px-4 md:px-10 py-6 max-w-4xl mx-auto">
        <div className="flex items-center gap-2 text-teal font-mono text-[11px] uppercase tracking-widest mb-2"><Lock size={14}/> ENCRYPTED BUSINESS BRAIN</div>
        <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.06em] text-silver mb-4">Materials Configuration</h1>

        <HudCard className="p-5 mb-4">
          <div className="font-mono text-[11px] uppercase tracking-widest text-teal mb-3 flex items-center gap-2"><Layers size={12}/> Product Catalog</div>
          <div className="grid md:grid-cols-2 gap-3">
            <Field label="Shingle Brand" value={m.shingle_brand} onChange={(v)=>set("shingle_brand", v)} testid="mat-shingle-brand"/>
            <Field label="Underlayment Brand" value={m.underlayment_brand} onChange={(v)=>set("underlayment_brand", v)}/>
            <Field label="Ice & Water Shield" value={m.ice_water_brand} onChange={(v)=>set("ice_water_brand", v)}/>
            <Field label="Ridge Vent" value={m.ridge_vent_brand} onChange={(v)=>set("ridge_vent_brand", v)}/>
            <Field label="Starter Strip" value={m.starter_brand} onChange={(v)=>set("starter_brand", v)}/>
            <Field label="Drip Edge Color" value={m.drip_edge_color} onChange={(v)=>set("drip_edge_color", v)}/>
            <Field label="Fastener Type" value={m.fastener_type} onChange={(v)=>set("fastener_type", v)}/>
          </div>
        </HudCard>

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

        <button onClick={save} disabled={busy} className="btn-hud" data-testid="mat-save"><FileText size={14}/> {busy?"Encrypting…":"SAVE BUSINESS BRAIN"}</button>
      </div>
    </>
  );
}

function Field({ label, value, onChange, testid }) {
  return (<div><label className="hud-label">{label}</label><input data-testid={testid} className="hud-input" value={value || ""} onChange={(e)=>onChange(e.target.value)}/></div>);
}
function NumField({ label, value, onChange, testid }) {
  return (<div><label className="hud-label">{label}</label><input data-testid={testid} type="number" step="0.01" className="hud-input font-mono" value={value ?? 0} onChange={(e)=>onChange(parseFloat(e.target.value)||0)}/></div>);
}
