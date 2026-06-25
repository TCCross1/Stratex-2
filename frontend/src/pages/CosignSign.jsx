// STRATEX™ — Carrier Co-Sign Surface
//
// The adjuster lands here from a magic link (`/cosign/:token`). They
// see a summary of the Claim Snapshot, fill the signature form, and
// submit. Backend records a SHA-256 receipt + appends a COSIGN entry
// to the Property Passport's immutable ledger.

import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Loader2, ShieldCheck, ShieldAlert, PenLine, FileSignature,
  Lock, ChevronRight, AlertOctagon, Hash,
} from "lucide-react";
import { StratexLogo } from "@/components/StratexBrand";

const ACCENTS = {
  cyan: "#00E5FF", amber: "#FFB020", green: "#00FF9C",
  magenta: "#FF2D78", gold: "#D4B86A",
};

function Pill({ children, color }) {
  return (
    <span className="px-2 py-0.5 rounded-full font-mono text-[9px] tracking-[0.22em] uppercase"
          style={{ color, border: `1px solid ${color}66`, background: `${color}10` }}>
      {children}
    </span>
  );
}

function Field({ label, ...rest }) {
  return (
    <label className="block">
      <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400 mb-1">
        {label}
      </div>
      <input
        {...rest}
        className="w-full rounded-md bg-[rgba(8,14,24,0.86)] text-white px-3 py-2
                   font-mono text-[12px] tracking-[0.06em] outline-none focus:ring-2"
        style={{
          border: `1px solid ${ACCENTS.cyan}44`,
        }}
      />
    </label>
  );
}

export default function CosignSign() {
  const { token } = useParams();
  const nav = useNavigate();
  const API = process.env.REACT_APP_BACKEND_URL;
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [verify, setVerify] = useState(null);
  const [form, setForm] = useState({
    adjuster_name: "", adjuster_company: "",
    adjuster_license: "", decision: "APPROVED", notes: "",
  });
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/claim-snapshot/cosign/verify/${token}`);
      if (!r.ok) { setErr(`Token invalid or expired (${r.status})`); return; }
      const j = await r.json();
      setVerify(j);
      if (j.signed_at) {
        setResult({
          signed_at: j.signed_at,
          decision: j.decision,
          receipt_hash: j.receipt_hash,
          signer: j.signer,
        });
      }
    } catch (e) {
      setErr(`Network error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, [token]);  // eslint-disable-line

  const submit = async () => {
    if (!form.adjuster_name.trim() || !form.adjuster_company.trim()) {
      toast.error("Adjuster name and company are required to co-sign");
      return;
    }
    setSubmitting(true);
    try {
      const r = await fetch(`${API}/api/claim-snapshot/cosign/submit/${token}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(form),
      });
      if (!r.ok) {
        const t = await r.text();
        toast.error(`Submit failed: ${t.slice(0, 160)}`);
        return;
      }
      const j = await r.json();
      setResult({ ...j, signer: form });
      toast.success("Co-sign locked into the passport ledger");
    } catch (e) {
      toast.error(`Network error: ${e.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center" style={{ background: "#02060B" }}>
        <Loader2 size={28} className="animate-spin text-cyan-400"/>
      </div>
    );
  }

  if (err || !verify) {
    return (
      <div className="min-h-screen grid place-items-center px-6 text-center"
           style={{ background: "#02060B", color: "#fff" }}>
        <div className="max-w-md">
          <AlertOctagon size={36} color={ACCENTS.magenta} className="mx-auto mb-4"/>
          <h1 className="font-display text-xl uppercase tracking-[0.08em]">Token Unavailable</h1>
          <p className="font-mono text-[11px] tracking-[0.14em] text-slate-400 mt-3">{err}</p>
          <button onClick={() => nav("/")}
                  className="mt-5 font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md"
                  style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
            Return Home
          </button>
        </div>
      </div>
    );
  }

  const diff = verify.diff;
  const pp = diff.passport || {};
  const d = diff.deltas || {};
  const accent =
    diff.verdict === "CLAIM_SUPPORTABLE" ? ACCENTS.magenta :
    diff.verdict === "MONITOR"           ? ACCENTS.amber : ACCENTS.green;
  const alreadySigned = !!result;

  return (
    <div data-testid="cosign-page" className="min-h-screen text-slate-100"
         style={{
           background:
             "radial-gradient(ellipse at 80% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
             "radial-gradient(ellipse at 10% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
             "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
           fontFamily: "'Sora', sans-serif",
         }}>
      <div className="border-b" style={{ borderColor: "rgba(0,229,255,0.18)", background: "rgba(8,14,24,0.85)" }}>
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Lock size={11} style={{ color: ACCENTS.gold }}/>
            <span className="font-mono text-[9px] tracking-[0.32em] uppercase" style={{ color: ACCENTS.gold }}>
              // CARRIER CO-SIGN GATEWAY · STRATEX™ CHAIN OF CUSTODY
            </span>
          </div>
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
            TOKEN …{token.slice(-8)} · PASSPORT STX-{verify.passport_id}
          </span>
        </div>
      </div>

      <header className="max-w-[1200px] mx-auto px-4 sm:px-6 pt-6 pb-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <StratexLogo height={28}/>
          <span className="font-display text-sm uppercase tracking-[0.1em] text-white">
            · Claim Snapshot Counter-Signature
          </span>
        </div>
        <button onClick={() => nav(`/claim-snapshot/${verify.passport_id}`)}
                data-testid="open-snapshot"
                className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
          Open Snapshot <ChevronRight size={12}/>
        </button>
      </header>

      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 pb-4">
        <div className="rounded-2xl p-5 sm:p-6"
             style={{
               background: `linear-gradient(120deg, ${accent}18 0%, rgba(8,14,24,0.85) 55%, rgba(212,184,106,0.06) 100%)`,
               border: `1.5px solid ${accent}88`,
               boxShadow: `inset 0 0 56px ${accent}10`,
             }}>
          <div className="font-mono text-[9px] tracking-[0.32em] uppercase mb-2" style={{ color: accent }}>
            // STRATEX™ VERDICT
          </div>
          <h1 className="font-display uppercase leading-[0.95] tracking-[0.02em]"
              style={{ fontSize: "clamp(26px, 4vw, 42px)", color: "#fff" }}>
            {pp.owner}
          </h1>
          <div className="font-mono text-[11px] tracking-[0.16em] uppercase text-slate-300 mt-1.5">
            {pp.address} · {pp.city_state}
          </div>

          <div className="flex items-center gap-2 mt-4 flex-wrap">
            <Pill color={accent}>{(diff.verdict || "—").replace("_", " ")}</Pill>
            <Pill color={ACCENTS.cyan}>{diff.confidence_pct}% confidence</Pill>
            {diff.storm_correlated && (
              <Pill color={ACCENTS.magenta}>
                Storm · {diff.storm_correlated.kind} · {diff.storm_correlated.value}
              </Pill>
            )}
          </div>

          <p className="mt-4 text-[13px] leading-[1.6] text-slate-200 max-w-3xl">
            {diff.narrative}
          </p>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-5">
            {[
              ["NEW DAMAGE", d.new_damage_count, ACCENTS.magenta],
              ["WORSENED", d.worsened_count, ACCENTS.amber],
              ["AREA Δ (SF)", d.total_new_damage_area_sqft, ACCENTS.magenta],
              ["REPAIR Δ", `$${(d.repair_estimate_delta_usd || 0).toLocaleString()}`, ACCENTS.gold],
            ].map(([k, v, c]) => (
              <div key={k} className="rounded-md p-3"
                   style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${c}55` }}>
                <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500">{k}</div>
                <div className="font-display text-[22px] font-bold leading-none mt-1.5"
                     style={{ color: c, textShadow: `0 0 12px ${c}55` }}>
                  {v}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* SIGNATURE PANEL */}
      <section className="max-w-[1200px] mx-auto px-4 sm:px-6 pb-10">
        {alreadySigned ? (
          <div data-testid="cosign-receipt" className="rounded-2xl p-6"
               style={{
                 background: "rgba(8,14,24,0.92)",
                 border: `1.5px solid ${ACCENTS.green}88`,
                 boxShadow: `inset 0 0 32px ${ACCENTS.green}15, 0 0 36px ${ACCENTS.green}30`,
               }}>
            <div className="flex items-center gap-3 mb-3">
              <ShieldCheck size={20} color={ACCENTS.green}/>
              <span className="font-mono text-[9px] tracking-[0.32em] uppercase" style={{ color: ACCENTS.green }}>
                // SIGNED · LOCKED INTO IMMUTABLE LEDGER
              </span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <div>
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">Adjuster</div>
                <div className="font-display text-[16px] uppercase tracking-[0.06em] text-white mt-1">
                  {(result.signer || form).adjuster_name}
                </div>
              </div>
              <div>
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">Company</div>
                <div className="font-display text-[16px] uppercase tracking-[0.06em] text-white mt-1">
                  {(result.signer || form).adjuster_company}
                </div>
              </div>
              <div>
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">Decision</div>
                <div className="font-display text-[16px] uppercase tracking-[0.06em] mt-1"
                     style={{ color: result.decision === "APPROVED" ? ACCENTS.green :
                                       result.decision === "DENIED"   ? ACCENTS.magenta : ACCENTS.amber }}>
                  {result.decision}
                </div>
              </div>
              <div>
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">Signed At</div>
                <div className="font-mono text-[12px] text-slate-200 mt-1">
                  {(result.signed_at || "").slice(0, 19).replace("T", " ")}
                </div>
              </div>
            </div>
            <div className="mt-5 rounded-md p-3"
                 style={{ background: `${ACCENTS.gold}10`, border: `1px solid ${ACCENTS.gold}66` }}>
              <div className="flex items-center gap-2">
                <Hash size={12} color={ACCENTS.gold}/>
                <span className="font-mono text-[8.5px] tracking-[0.26em] uppercase" style={{ color: ACCENTS.gold }}>
                  Receipt Hash · SHA-256
                </span>
              </div>
              <div data-testid="receipt-hash"
                   className="font-mono text-[10.5px] tracking-[0.06em] text-cyan-300 mt-1.5 break-all">
                {result.receipt_hash}
              </div>
            </div>
            <div className="mt-5 flex items-center gap-2">
              <button onClick={() => nav(`/passport/${verify.passport_id}`)}
                      data-testid="goto-passport"
                      className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                      style={{ background: `${ACCENTS.gold}14`, border: `1px solid ${ACCENTS.gold}66`, color: ACCENTS.gold }}>
                View Passport Ledger <ChevronRight size={12}/>
              </button>
              <button onClick={() => nav(`/claim-snapshot/${verify.passport_id}`)}
                      data-testid="goto-snapshot"
                      className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                      style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
                Return to Claim Snapshot <ChevronRight size={12}/>
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded-2xl p-6"
               style={{
                 background: "rgba(8,14,24,0.92)",
                 border: `1.5px solid ${ACCENTS.gold}88`,
                 boxShadow: `inset 0 0 32px ${ACCENTS.gold}10, 0 0 28px ${ACCENTS.gold}25`,
               }}>
            <div className="flex items-center gap-3 mb-4">
              <FileSignature size={18} color={ACCENTS.gold}/>
              <span className="font-mono text-[10px] tracking-[0.32em] uppercase" style={{ color: ACCENTS.gold }}>
                // ADJUSTER COUNTER-SIGNATURE
              </span>
              <Pill color={ACCENTS.cyan}>One-time use</Pill>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              <Field label="Adjuster Name" data-testid="input-adjuster-name"
                     placeholder="Jane Reyes"
                     value={form.adjuster_name}
                     onChange={(e) => setForm({ ...form, adjuster_name: e.target.value })}/>
              <Field label="Carrier Company" data-testid="input-adjuster-company"
                     placeholder="State Farm Claims"
                     value={form.adjuster_company}
                     onChange={(e) => setForm({ ...form, adjuster_company: e.target.value })}/>
              <Field label="Adjuster License #" data-testid="input-adjuster-license"
                     placeholder="KY-CL-XXXXXX"
                     value={form.adjuster_license}
                     onChange={(e) => setForm({ ...form, adjuster_license: e.target.value })}/>
              <label className="block">
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400 mb-1">
                  Decision
                </div>
                <select data-testid="input-decision"
                        value={form.decision}
                        onChange={(e) => setForm({ ...form, decision: e.target.value })}
                        className="w-full rounded-md bg-[rgba(8,14,24,0.86)] text-white px-3 py-2
                                   font-mono text-[12px] tracking-[0.1em] uppercase outline-none"
                        style={{ border: `1px solid ${ACCENTS.cyan}44` }}>
                  <option value="APPROVED">Approved · Settle</option>
                  <option value="NEEDS_INSPECTION">Needs On-Site Inspection</option>
                  <option value="DENIED">Denied</option>
                </select>
              </label>
              <label className="block md:col-span-2">
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400 mb-1">
                  Notes (optional)
                </div>
                <textarea data-testid="input-notes"
                          value={form.notes}
                          onChange={(e) => setForm({ ...form, notes: e.target.value })}
                          placeholder="E.g. policy #BX-554-2026; HOH deductible applied."
                          rows={3}
                          className="w-full rounded-md bg-[rgba(8,14,24,0.86)] text-white px-3 py-2
                                     font-mono text-[12px] tracking-[0.06em] outline-none"
                          style={{ border: `1px solid ${ACCENTS.cyan}44` }}/>
              </label>
            </div>

            <div className="flex items-center justify-between mt-5 flex-wrap gap-3">
              <div className="flex items-center gap-2">
                <Lock size={11} color={ACCENTS.gold}/>
                <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                  Receipt SHA-256 written to immutable passport ledger
                </span>
              </div>
              <button onClick={submit} disabled={submitting}
                      data-testid="submit-cosign"
                      className="font-display text-[13px] tracking-[0.1em] uppercase px-5 py-2.5 rounded-md flex items-center gap-2
                                 disabled:opacity-50"
                      style={{
                        background: ACCENTS.gold,
                        color: "#02060B",
                        boxShadow: `0 0 18px ${ACCENTS.gold}88`,
                      }}>
                {submitting ? <Loader2 size={14} className="animate-spin"/> : <PenLine size={14}/>}
                Lock Signature
              </button>
            </div>
          </div>
        )}
      </section>

      <footer className="max-w-[1200px] mx-auto px-4 sm:px-6 pb-8">
        <div className="border-t pt-4 flex flex-col sm:flex-row items-center justify-between gap-2"
             style={{ borderColor: "rgba(212,184,106,0.20)" }}>
          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
            STRATEX™ · CARRIER GATEWAY · COSIGN TOKENS ARE ONE-TIME USE · TAMPER-EVIDENT
          </span>
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color: ACCENTS.gold }}>
            stratex.co/cosign/{token.slice(0, 8)}…
          </span>
        </div>
      </footer>
    </div>
  );
}
