// STRATEX™ — PUBLIC PROPERTY PASSPORT VIEWER
//
// This is the page an insurance adjuster, future home-buyer, or homeowner
// loads from the Carrier Link printed on the Property Passport certificate.
// It is **unauthenticated by design** — the URL hash IS the access token.
//
// What it shows
//   • Co-branded lockup (contractor logo + STRATEX glyph)
//   • Big circular Certified-Healthy / Action-Required seal
//   • Property facts (facets, squares, year built, accuracy)
//   • Hash-chained ledger of every storm, audit, claim, checkup, transfer
//   • Live 30-day Weather Shield ribbon (Open-Meteo, real GPS)
//   • Chain integrity verifier — "One-Click Tamper Check"
//   • Direct download of the PDF certificate
//   • Adjuster CTA — "Open Adjuster Review Mode" (read-only forensic binder)

import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { StratexLogo } from "@/components/StratexBrand";
import {
  ShieldCheck, ShieldAlert, ShieldQuestion, Wind, Droplets, CloudRain,
  Loader2, ExternalLink, FileDown, BadgeCheck, Lock, AlertOctagon,
  Hash, ChevronRight,
} from "lucide-react";

const ACCENTS = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  green:   "#00FF9C",
  magenta: "#FF2D78",
  gold:    "#D4B86A",
};

function StatusSeal({ status }) {
  let color = ACCENTS.green;
  let label = "CERTIFIED HEALTHY";
  let Icon  = ShieldCheck;
  if (status === "ACTION REQUIRED") { color = ACCENTS.magenta; label = "ACTION REQUIRED"; Icon = ShieldAlert; }
  else if (status?.startsWith("MONITOR")) { color = ACCENTS.amber; label = "MONITOR · TIER B"; Icon = ShieldQuestion; }

  return (
    <div className="relative w-[210px] h-[210px] grid place-items-center">
      <svg viewBox="0 0 220 220" className="absolute inset-0">
        <defs>
          <radialGradient id="sealGlow" cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor={color} stopOpacity="0.35"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </radialGradient>
          <path id="topArc" d="M 32 110 a 78 78 0 0 1 156 0"/>
          <path id="botArc" d="M 32 110 a 78 78 0 0 0 156 0"/>
        </defs>
        <circle cx="110" cy="110" r="100" fill="url(#sealGlow)"/>
        <circle cx="110" cy="110" r="92" fill="none" stroke={color} strokeWidth="2"/>
        <circle cx="110" cy="110" r="82" fill="none" stroke={color} strokeWidth="0.6" strokeDasharray="2 3" opacity="0.7"/>
        {Array.from({length: 24}).map((_, i) => (
          <line key={i} x1="110" y1="10" x2="110" y2="20"
                transform={`rotate(${i * 15} 110 110)`}
                stroke={color} strokeWidth="1.6"/>
        ))}
        <text fontFamily="'Cinzel', serif" fontWeight="700" fontSize="11"
              fill={color} letterSpacing="6">
          <textPath xlinkHref="#topArc" startOffset="50%" textAnchor="middle">
            STRATEX · PROPERTY GUARDIAN
          </textPath>
        </text>
        <text fontFamily="'JetBrains Mono', monospace" fontSize="8"
              fill={color} letterSpacing="6">
          <textPath xlinkHref="#botArc" startOffset="50%" textAnchor="middle">
            FORENSIC AUDIT · SEALED
          </textPath>
        </text>
      </svg>
      <div className="relative text-center" style={{ filter: `drop-shadow(0 0 12px ${color})` }}>
        <Icon size={36} color={color} strokeWidth={1.6} className="mx-auto"/>
        <div className="font-display font-bold text-lg tracking-[0.04em] text-white mt-1 leading-tight">
          {label.split(" ")[0]}
        </div>
        <div className="font-mono text-[9px] tracking-[0.22em] mt-0.5" style={{ color }}>
          {label.split(" ").slice(1).join(" ") || "CERTIFIED"}
        </div>
      </div>
    </div>
  );
}

function WeatherRibbon({ events }) {
  if (!events?.length) {
    return (
      <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-500 py-4 text-center">
        No storm-grade events in the last 30 days · all clear.
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
      {events.map((e, i) => {
        const ok = e.severity === "PASS";
        const c = ok ? ACCENTS.green : ACCENTS.amber;
        const Icon = e.kind === "WIND" ? Wind : e.kind === "RAIN" ? CloudRain : Droplets;
        return (
          <div key={i} data-testid={`shield-${e.kind.toLowerCase()}-${i}`}
               className="rounded-md px-3 py-2.5 text-center"
               style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${c}55`,
                        boxShadow: `inset 0 0 18px ${c}10` }}>
            <Icon size={14} color={c} className="mx-auto"/>
            <div className="font-display text-base text-white tracking-[0.02em] mt-1">{e.value}</div>
            <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase mt-0.5"
                 style={{ color: c }}>
              {e.kind} · {e.severity}
            </div>
            <div className="font-mono text-[8px] tracking-[0.18em] uppercase text-slate-500 mt-0.5">
              {e.date}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function LedgerRow({ entry }) {
  const c = entry.status === "OK" ? ACCENTS.green :
            entry.status === "ACTION" ? ACCENTS.magenta : ACCENTS.amber;
  const eventColor = entry.event === "BASELINE" ? ACCENTS.cyan :
                     entry.event === "STORM"    ? ACCENTS.amber :
                     entry.event === "AUDIT"    ? ACCENTS.green :
                     entry.event === "CLAIM"    ? ACCENTS.magenta :
                     entry.event === "TRANSFER" ? ACCENTS.gold :
                     ACCENTS.cyan;
  return (
    <div className="grid grid-cols-[60px_120px_1fr_auto] gap-3 items-center py-2.5 border-b"
         style={{ borderColor: "rgba(255,255,255,0.06)" }}
         data-testid={`ledger-row-${entry.seq}`}>
      <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
        SEQ · {String(entry.seq).padStart(3, "0")}
      </span>
      <span className="font-mono text-[10px] tracking-[0.22em] uppercase font-bold"
            style={{ color: eventColor, textShadow: `0 0 8px ${eventColor}55` }}>
        {entry.event}
      </span>
      <div className="min-w-0">
        <div className="font-mono text-[11px] text-white truncate">{entry.note || "—"}</div>
        <div className="font-mono text-[8.5px] tracking-[0.16em] text-slate-500 mt-0.5 flex items-center gap-1.5">
          <Hash size={9}/>
          {entry.entry_hash?.slice(0, 16)}…
        </div>
      </div>
      <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase px-2 py-0.5 rounded-full whitespace-nowrap"
            style={{ color: c, border: `1px solid ${c}66`, background: `${c}10` }}>
        {entry.status}
      </span>
    </div>
  );
}

export default function PassportPortal() {
  const { hash } = useParams();
  const nav = useNavigate();
  const API = process.env.REACT_APP_BACKEND_URL;

  const [passport, setPassport] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/passport/${hash}`);
        if (!r.ok) {
          setErr(`Passport "${hash}" not found.`);
          return;
        }
        setPassport(await r.json());
      } catch (e) {
        setErr(`Network error: ${e.message}`);
      } finally {
        setLoading(false);
      }
    })();
  }, [API, hash]);

  const onVerify = async () => {
    setVerifying(true);
    try {
      const r = await fetch(`${API}/api/passport/${hash}/verify`);
      setVerifyResult(await r.json());
    } finally {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center" style={{ background: "#02060B", color: "#fff" }}>
        <Loader2 size={32} className="animate-spin text-cyan-400"/>
      </div>
    );
  }

  if (err || !passport) {
    return (
      <div className="min-h-screen grid place-items-center px-6" style={{ background: "#02060B", color: "#fff" }}>
        <div className="max-w-md text-center">
          <AlertOctagon size={40} className="text-magenta-400 mx-auto mb-4" style={{ color: ACCENTS.magenta }}/>
          <h1 className="font-display text-2xl uppercase tracking-[0.08em]">Passport Not Found</h1>
          <p className="font-mono text-[11px] tracking-[0.14em] text-slate-400 mt-3">{err}</p>
          <button onClick={() => nav("/")}
                  className="mt-6 font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md"
                  style={{ background: "rgba(0,229,255,0.10)", border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
            ← Return Home
          </button>
        </div>
      </div>
    );
  }

  const status = passport.initial_status || "CERTIFIED HEALTHY";
  const tearOff = status === "ACTION REQUIRED";
  const accent = tearOff ? ACCENTS.magenta : status?.startsWith("MONITOR") ? ACCENTS.amber : ACCENTS.green;
  const contractor = passport.contractor || {};

  return (
    <div data-testid="passport-portal" className="min-h-screen text-slate-100"
         style={{
           background:
             "radial-gradient(ellipse at 80% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
             "radial-gradient(ellipse at 10% 100%, rgba(212,184,106,0.07) 0%, transparent 55%)," +
             "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
           fontFamily: "'Sora', sans-serif",
         }}>
      {/* faint grid */}
      <div aria-hidden className="pointer-events-none fixed inset-0 opacity-[0.04]"
           style={{
             backgroundImage:
               "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px)," +
               "linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
             backgroundSize: "60px 60px",
           }}/>

      {/* TOP — Adjuster banner */}
      <div className="border-b" style={{ borderColor: "rgba(0,229,255,0.18)",
                                          background: "rgba(8,14,24,0.85)" }}>
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Lock size={11} className="text-cyan-400"/>
            <span className="font-mono text-[9px] tracking-[0.32em] uppercase text-cyan-400">
              // PUBLIC PORTAL · ADJUSTER REVIEW MODE
            </span>
          </div>
          <div className="flex items-center gap-2 font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
            <span>STRATEX™</span><span>·</span><span>READ-ONLY</span><span>·</span><span>NO AUTH REQUIRED</span>
          </div>
        </div>
      </div>

      {/* HEADER */}
      <header className="max-w-[1280px] mx-auto px-4 sm:px-6 pt-8 pb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <StratexLogo height={32}/>
            <span className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-500 hidden sm:inline">// PROPERTY PASSPORT</span>
          </div>
          {contractor.business_name && (
            <div className="flex items-center gap-2">
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">CO-SIGNED BY</span>
              <span className="font-display text-sm uppercase tracking-[0.1em] text-white">{contractor.business_name}</span>
            </div>
          )}
        </div>
      </header>

      {/* HERO ============================= */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 pb-6">
        <div className="rounded-2xl p-5 sm:p-8 relative overflow-hidden"
             style={{
               background: "linear-gradient(120deg, rgba(215,40,47,0.12) 0%, rgba(8,14,24,0.85) 50%, rgba(0,229,255,0.10) 100%)",
               border: `1.5px solid ${ACCENTS.gold}88`,
               boxShadow: `inset 0 0 60px ${ACCENTS.gold}10, 0 0 36px rgba(212,184,106,0.18)`,
             }}>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_220px] gap-6 items-center">
            <div className="min-w-0">
              <div className="font-mono text-[9px] tracking-[0.32em] uppercase mb-2" style={{ color: ACCENTS.gold }}>
                // STRATEX™ PROPERTY PASSPORT · CERTIFIED RECORD OF CONDITION
              </div>
              <h1 className="font-display uppercase leading-[0.95] tracking-[0.02em]"
                  style={{ fontSize: "clamp(28px, 4vw, 50px)" }}>
                <span style={{ color: ACCENTS.gold, textShadow: `0 0 18px ${ACCENTS.gold}55` }}>
                  {passport.owner}
                </span>
              </h1>
              <div className="font-mono text-[11px] sm:text-[12px] tracking-[0.16em] uppercase text-slate-300 mt-3">
                {passport.address} · {passport.city_state}
              </div>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <div className="rounded-md px-3 py-2"
                     style={{ background: "rgba(0,229,255,0.06)", border: `1px solid ${ACCENTS.cyan}55` }}>
                  <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500">PASSPORT ID</div>
                  <div className="font-mono text-[13px] tracking-[0.12em] text-white mt-0.5">STX-{passport.passport_id}</div>
                </div>
                <div className="rounded-md px-3 py-2"
                     style={{ background: "rgba(0,255,156,0.06)", border: `1px solid ${ACCENTS.green}55` }}>
                  <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500">ACCURACY</div>
                  <div className="font-mono text-[13px] tracking-[0.12em]" style={{ color: ACCENTS.green }}>
                    ±{passport.accuracy_cm} cm
                  </div>
                </div>
                <div className="rounded-md px-3 py-2"
                     style={{ background: "rgba(212,184,106,0.06)", border: `1px solid ${ACCENTS.gold}55` }}>
                  <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500">ISSUED</div>
                  <div className="font-mono text-[13px] tracking-[0.12em] text-white mt-0.5">
                    {passport.scan_date}
                  </div>
                </div>
              </div>
            </div>
            <div className="flex justify-center md:justify-end">
              <StatusSeal status={status}/>
            </div>
          </div>
        </div>
      </section>

      {/* GRID — Property Facts · Weather Shield · Actions */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 pb-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Property facts */}
        <div className="rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.cyan}44`,
                      boxShadow: `inset 0 0 28px ${ACCENTS.cyan}08` }}>
          <div className="font-mono text-[9px] tracking-[0.28em] uppercase mb-3" style={{ color: ACCENTS.cyan }}>
            // PROPERTY · BIG PICTURE
          </div>
          <div className="grid grid-cols-2 gap-y-3">
            {[
              ["FACETS",      passport.facets ?? "—",                    ACCENTS.cyan],
              ["SQUARES",     passport.squares?.toFixed?.(1) ?? "—",     ACCENTS.cyan],
              ["YEAR BUILT",  passport.year_built ?? "—",                "#fff"],
              ["ENVELOPE",    `${passport.envelope_score ?? "—"}/100`,    ACCENTS.green],
              ["MOISTURE",    `${passport.moisture_pct ?? "—"}%`,        ACCENTS.amber],
              ["GPS",         `${passport.lat?.toFixed?.(3)}, ${passport.lon?.toFixed?.(3)}`, ACCENTS.cyan],
            ].map(([k, v, c]) => (
              <div key={k}>
                <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">{k}</div>
                <div className="font-display text-[18px] mt-0.5" style={{ color: c }}>{v}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Weather Shield */}
        <div className="rounded-xl p-5 lg:col-span-2"
             style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.amber}44`,
                      boxShadow: `inset 0 0 28px ${ACCENTS.amber}08` }}>
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: ACCENTS.amber }}>
              // WEATHER SHIELD · LAST 30 DAYS · LIVE GPS CORRELATION
            </div>
            <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
              SOURCE · OPEN-METEO ARCHIVE
            </div>
          </div>
          <WeatherRibbon events={passport.weather_shield || []}/>
          <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-slate-500 mt-4 leading-relaxed">
            EVENTS CORRELATED TO {passport.lat?.toFixed?.(4)}, {passport.lon?.toFixed?.(4)}
            · NEXT VIRTUAL CHECK-UP RECOMMENDED IN 6 MONTHS · STORMS &gt; 60 MPH AUTO-LOG AS LEDGER EVENTS
          </div>
        </div>
      </section>

      {/* IMMUTABLE LEDGER ============================= */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 pb-6">
        <div className="rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.gold}55`,
                      boxShadow: `inset 0 0 36px ${ACCENTS.gold}08` }}>
          <div className="flex items-center justify-between flex-wrap gap-2 mb-4">
            <div className="flex items-center gap-2">
              <BadgeCheck size={14} style={{ color: ACCENTS.gold }}/>
              <span className="font-display text-base uppercase tracking-[0.12em] text-white">
                Immutable Ledger
              </span>
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                // SHA-256 HASH-CHAINED
              </span>
            </div>
            <button
              data-testid="verify-chain-btn"
              onClick={onVerify}
              disabled={verifying}
              className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5 transition hover:brightness-125"
              style={{
                background: verifyResult?.tamper_evident ? `${ACCENTS.green}14` :
                            verifyResult ? `${ACCENTS.magenta}14` : `${ACCENTS.cyan}14`,
                border: `1px solid ${verifyResult?.tamper_evident ? ACCENTS.green :
                                     verifyResult ? ACCENTS.magenta : ACCENTS.cyan}88`,
                color: verifyResult?.tamper_evident ? ACCENTS.green :
                       verifyResult ? ACCENTS.magenta : ACCENTS.cyan,
              }}
            >
              {verifying ? <Loader2 size={12} className="animate-spin"/> : <ShieldCheck size={12}/>}
              {verifyResult?.tamper_evident ? "Chain Verified ✓" :
               verifyResult ? `Tamper detected (seqs ${verifyResult.broken_seqs.join(",")})` :
               "Verify Chain"}
            </button>
          </div>

          {(passport.ledger || []).map((e) => <LedgerRow key={e.seq} entry={e}/>)}

          {!(passport.ledger || []).length && (
            <div className="font-mono text-[10px] tracking-[0.22em] uppercase text-slate-500 py-4 text-center">
              No ledger entries yet.
            </div>
          )}
        </div>
      </section>

      {/* CTAs ============================= */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 pb-12 grid grid-cols-1 md:grid-cols-3 gap-3">
        <a
          data-testid="download-pdf-btn"
          href={`${API}/api/passport/${hash}/pdf`}
          target="_blank"
          rel="noopener noreferrer"
          className="rounded-md px-4 py-3 flex items-center gap-2 transition hover:brightness-125"
          style={{ background: `${ACCENTS.gold}14`, border: `1.5px solid ${ACCENTS.gold}88` }}
        >
          <FileDown size={14} style={{ color: ACCENTS.gold }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Download PDF Certificate</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">11×17 tabloid · signed</div>
          </div>
        </a>
        <button
          data-testid="adjuster-mode-btn"
          onClick={() => nav("/reports/binder")}
          className="rounded-md px-4 py-3 flex items-center gap-2 transition hover:brightness-125 text-left"
          style={{ background: `${ACCENTS.cyan}14`, border: `1.5px solid ${ACCENTS.cyan}88` }}
        >
          <ExternalLink size={14} style={{ color: ACCENTS.cyan }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Open Adjuster Review</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">Full 17-page binder · read-only</div>
          </div>
          <ChevronRight size={14} className="ml-auto" style={{ color: ACCENTS.cyan }}/>
        </button>
        <button
          data-testid="claim-snapshot-btn"
          onClick={() => nav(`/claim-snapshot/${hash}`)}
          className="rounded-md px-4 py-3 flex items-center gap-2 transition hover:brightness-125 text-left"
          style={{ background: `${ACCENTS.magenta}14`, border: `1.5px solid ${ACCENTS.magenta}88` }}
        >
          <Hash size={14} style={{ color: ACCENTS.magenta }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Open Claim Snapshot</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">Before / after diff · LAE bypass</div>
          </div>
          <ChevronRight size={14} className="ml-auto" style={{ color: ACCENTS.magenta }}/>
        </button>
      </section>

      <footer className="max-w-[1280px] mx-auto px-4 sm:px-6 pb-8">
        <div className="border-t pt-4 flex flex-col sm:flex-row items-center justify-between gap-2"
             style={{ borderColor: "rgba(212,184,106,0.20)" }}>
          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
            STRATEX™ · GROUND-TRUTH ±0.78 CM · PATENT PENDING · CHAIN-OF-CUSTODY VERIFIED
          </span>
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color: ACCENTS.gold }}>
            CARRIER LINK · stratex.co/passport/{hash.toLowerCase()}
          </span>
        </div>
      </footer>
    </div>
  );
}
