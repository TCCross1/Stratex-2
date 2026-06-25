// STRATEX™ — Contractor 3-Contact Verification Wall (Phase 4)
//
// New contractors must submit three verifiable references — supplier rep,
// past client, GC — before the operational dashboard unlocks. While they
// are at < 3 verified, a gated wall is rendered. Once unlocked, they pass
// through into the existing Contractor Portal.

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { StratexLogo } from "@/components/StratexBrand";
import { toast } from "sonner";
import {
  ShieldCheck, ShieldAlert, Loader2, Phone, Mail, Briefcase,
  CheckCircle2, Circle, ChevronRight, ArrowLeft, Lock,
} from "lucide-react";

const ACCENTS = {
  cyan: "#00E5FF", amber: "#FFB020", green: "#00FF9C",
  magenta: "#FF2D78", gold: "#D4B86A",
};

const EMPTY_REF = { name: "", relationship: "", phone: "", email: "", years_known: "", notes: "" };

export default function ContractorVerify() {
  const API = process.env.REACT_APP_BACKEND_URL;
  const nav = useNavigate();
  const [email, setEmail] = useState(() => localStorage.getItem("stratex.contractor.email") || "anthony@americanroofing.co");
  const [status, setStatus] = useState(null);
  const [refs, setRefs] = useState([{ ...EMPTY_REF }, { ...EMPTY_REF }, { ...EMPTY_REF }]);
  const [submitting, setSubmitting] = useState(false);

  const fetchStatus = async (e) => {
    if (!e) return;
    try {
      const r = await fetch(`${API}/api/contractor/verify/status?contractor_email=${encodeURIComponent(e)}`);
      const j = await r.json();
      setStatus(j);
      if (j.submitted > 0) {
        setRefs(j.references.map((rr) => ({
          name: rr.name || "", relationship: rr.relationship || "",
          phone: rr.phone || "", email: rr.email || "",
          years_known: rr.years_known ?? "", notes: rr.notes || "",
        })));
      }
    } catch {
      setStatus(null);
    }
  };

  useEffect(() => { fetchStatus(email); }, [email]);

  const progress = status ? (status.verified / status.required) * 100 : 0;
  const unlocked = status?.unlocked;

  const update = (idx, patch) =>
    setRefs((rs) => rs.map((r, i) => i === idx ? { ...r, ...patch } : r));

  const allFilled = useMemo(() =>
    refs.every((r) => r.name && r.relationship && r.phone), [refs]);

  const submit = async () => {
    if (!allFilled) {
      toast.error("Each reference needs name, relationship and phone.");
      return;
    }
    setSubmitting(true);
    try {
      localStorage.setItem("stratex.contractor.email", email);
      const body = {
        contractor_email: email,
        references: refs.map((r) => ({
          ...r,
          years_known: r.years_known === "" ? null : Number(r.years_known),
          email: r.email || null,
        })),
      };
      const r = await fetch(`${API}/api/contractor/verify/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error("submit failed");
      toast.success("References submitted. STRATEX Verification Desk will reach out.");
      await fetchStatus(email);
    } catch {
      toast.error("Network error — try again.");
    } finally {
      setSubmitting(false);
    }
  };

  const markVerified = async (idx) => {
    try {
      await fetch(`${API}/api/contractor/verify/mark?contractor_email=${encodeURIComponent(email)}&reference_index=${idx}`, {
        method: "POST",
      });
      await fetchStatus(email);
    } catch {
      /* ignore */
    }
  };

  return (
    <div data-testid="contractor-verify" className="min-h-screen text-slate-100"
         style={{
           background:
             "radial-gradient(ellipse at 75% 0%, rgba(0,229,255,0.12) 0%, transparent 50%)," +
             "radial-gradient(ellipse at 5% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
             "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
           fontFamily: "'Sora', sans-serif",
         }}>
      <div aria-hidden className="pointer-events-none fixed inset-0 opacity-[0.04]"
           style={{ backgroundImage:
             "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px),linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
             backgroundSize: "60px 60px" }}/>

      <header className="max-w-[1200px] mx-auto px-4 sm:px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => nav("/deck")}
                  data-testid="back-deck"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                  style={{ background: "rgba(0,229,255,0.10)", border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
            <ArrowLeft size={12}/> Command Deck
          </button>
          <StratexLogo height={28}/>
        </div>
        <div className="font-mono text-[10px] tracking-[0.32em] uppercase text-cyan-400">// PHASE 4 · VERIFICATION WALL</div>
      </header>

      <main className="max-w-[1200px] mx-auto px-4 sm:px-6 pb-10">
        <h1 className="font-display uppercase tracking-[0.04em] text-3xl sm:text-5xl leading-[1.05]">
          Three-Contact <span style={{ color: ACCENTS.gold, textShadow: `0 0 18px ${ACCENTS.gold}55` }}>Verification</span> Wall
        </h1>
        <p className="font-mono text-[11px] tracking-[0.14em] uppercase text-slate-400 mt-3 max-w-2xl">
          STRATEX validates every contractor through a 3-reference handshake before the operational dashboard unlocks — supplier, past client, GC.
        </p>

        {/* STATUS BAR */}
        <div className="mt-6 rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)",
                      border: `1.5px solid ${unlocked ? ACCENTS.green : ACCENTS.amber}88`,
                      boxShadow: `inset 0 0 24px ${unlocked ? ACCENTS.green : ACCENTS.amber}12` }}>
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="flex items-center gap-3 min-w-0">
              {unlocked ? <ShieldCheck size={26} style={{ color: ACCENTS.green }}/>
                        : <ShieldAlert size={26} style={{ color: ACCENTS.amber }}/>}
              <div>
                <div className="font-display text-base uppercase tracking-[0.12em] text-white">
                  {unlocked ? "Wall Cleared · Dashboard Unlocked"
                            : status?.submitted ? "Awaiting Reference Verification"
                            : "Wall Pending · Submit 3 References"}
                </div>
                <div className="font-mono text-[10px] tracking-[0.16em] uppercase text-slate-400 mt-0.5">
                  {status ? `${status.verified} of ${status.required} verified` : "Loading…"}
                </div>
              </div>
            </div>
            <input
              data-testid="contractor-email-field"
              type="email" value={email}
              onChange={(e) => setEmail(e.target.value)}
              onBlur={() => fetchStatus(email)}
              placeholder="Contractor email"
              className="font-mono text-[11px] tracking-[0.06em] px-3 py-2 rounded-md outline-none bg-transparent text-white min-w-[260px]"
              style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}55` }}
            />
            {unlocked && (
              <button
                data-testid="enter-dashboard-btn"
                onClick={() => nav("/contractor/dashboard")}
                className="font-mono text-[11px] tracking-[0.22em] uppercase px-4 py-2.5 rounded-md flex items-center gap-2 transition hover:brightness-125"
                style={{ background: ACCENTS.green, color: "#02060B", boxShadow: `0 0 18px ${ACCENTS.green}66` }}>
                Enter Dashboard <ChevronRight size={14}/>
              </button>
            )}
          </div>
          <div className="mt-3 h-1.5 rounded-full" style={{ background: "rgba(255,255,255,0.08)" }}>
            <div className="h-full rounded-full transition-all"
                 style={{ width: `${progress}%`,
                          background: unlocked
                            ? `linear-gradient(90deg, ${ACCENTS.green} 0%, ${ACCENTS.cyan} 100%)`
                            : `linear-gradient(90deg, ${ACCENTS.amber} 0%, ${ACCENTS.gold} 100%)`,
                          boxShadow: `0 0 10px ${unlocked ? ACCENTS.green : ACCENTS.amber}` }}/>
          </div>
        </div>

        {/* REFERENCE TILES */}
        <div className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
          {refs.map((r, i) => {
            const persisted = status?.references?.[i];
            const verified = persisted?.verified;
            const c = verified ? ACCENTS.green : ACCENTS.cyan;
            return (
              <div key={i} className="rounded-xl p-4"
                   data-testid={`reference-${i + 1}`}
                   style={{ background: "rgba(8,14,24,0.86)", border: `1.5px solid ${c}66`,
                            boxShadow: `inset 0 0 24px ${c}10` }}>
                <div className="flex items-center justify-between mb-3">
                  <div className="font-mono text-[10px] tracking-[0.28em] uppercase" style={{ color: c }}>
                    // REFERENCE {i + 1} / 3
                  </div>
                  {verified ? <CheckCircle2 size={18} color={ACCENTS.green}/>
                            : <Circle size={18} color={ACCENTS.cyan}/>}
                </div>
                {[
                  { k: "name",         l: "Name",          icon: null },
                  { k: "relationship", l: "Relationship",  icon: Briefcase },
                  { k: "phone",        l: "Phone",         icon: Phone },
                  { k: "email",        l: "Email (opt)",   icon: Mail },
                  { k: "years_known",  l: "Years Known",   icon: null,  type: "number" },
                  { k: "notes",        l: "Notes",         icon: null },
                ].map((f) => (
                  <label key={f.k} className="block mb-2">
                    <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">{f.l}</span>
                    <div className="flex items-center gap-2 mt-0.5 px-2.5 py-1.5 rounded-sm"
                         style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${c}33` }}>
                      {f.icon && <f.icon size={12} color={c} className="shrink-0"/>}
                      <input
                        data-testid={`ref${i + 1}-${f.k}`}
                        type={f.type || "text"}
                        value={r[f.k] ?? ""}
                        disabled={verified}
                        onChange={(e) => update(i, { [f.k]: e.target.value })}
                        className="w-full bg-transparent outline-none font-mono text-[11px] tracking-[0.04em] text-white disabled:opacity-70"
                      />
                    </div>
                  </label>
                ))}
                {persisted && !verified && (
                  <button
                    onClick={() => markVerified(i)}
                    data-testid={`mark-verified-${i + 1}`}
                    className="mt-2 w-full font-mono text-[9.5px] tracking-[0.22em] uppercase py-1.5 rounded-md transition hover:brightness-125"
                    style={{ background: `${ACCENTS.green}14`, border: `1px solid ${ACCENTS.green}66`, color: ACCENTS.green }}>
                    Mark Verified (Admin)
                  </button>
                )}
              </div>
            );
          })}
        </div>

        <div className="mt-6 flex flex-wrap items-center gap-3 justify-end">
          {!unlocked && (
            <button
              data-testid="submit-references-btn"
              onClick={submit}
              disabled={submitting || !allFilled || !email}
              className="font-mono text-[11px] tracking-[0.22em] uppercase px-5 py-3 rounded-md flex items-center gap-2 transition hover:brightness-125 disabled:opacity-50 disabled:cursor-not-allowed"
              style={{ background: ACCENTS.gold, color: "#02060B", boxShadow: `0 0 18px ${ACCENTS.gold}66` }}>
              {submitting ? <Loader2 size={14} className="animate-spin"/> : <Lock size={14}/>}
              Submit References for Verification
            </button>
          )}
        </div>
      </main>
    </div>
  );
}
