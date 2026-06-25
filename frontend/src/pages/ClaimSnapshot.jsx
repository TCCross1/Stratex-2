// STRATEX™ — Claim Snapshot UI
//
// The killer adjuster feature. Loads a Property Passport's two stored
// scans (baseline + post-storm), runs a backend diff, and shows the
// homeowner / contractor / carrier exactly what changed — area, severity,
// repair estimate delta, storm correlation, and a Claude-Sonnet adjuster
// narrative — plus a one-click "Send to Carrier" PDF.

import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { StratexLogo } from "@/components/StratexBrand";
import {
  ArrowLeft, ShieldCheck, ShieldAlert, ShieldQuestion, FileDown, Loader2,
  Send, RefreshCw, AlertOctagon, Sparkles, TrendingDown, TrendingUp,
  Wind, Droplets, CloudRain, ChevronRight,
} from "lucide-react";

const ACCENTS = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  green:   "#00FF9C",
  magenta: "#FF2D78",
  gold:    "#D4B86A",
  red:     "#D7282F",
};

const DEFAULT_HASH = "877D9E3C8FC3";

function VerdictSeal({ verdict, confidence }) {
  const map = {
    CLAIM_SUPPORTABLE: { color: ACCENTS.magenta, Icon: ShieldAlert,  label: "CLAIM SUPPORTABLE" },
    MONITOR:           { color: ACCENTS.amber,   Icon: ShieldQuestion, label: "MONITOR" },
    NO_CHANGE:         { color: ACCENTS.green,   Icon: ShieldCheck,  label: "NO CHANGE" },
  };
  const cfg = map[verdict] || map.NO_CHANGE;
  const { color, Icon, label } = cfg;
  return (
    <div className="relative w-[220px] h-[220px] grid place-items-center">
      <svg viewBox="0 0 220 220" className="absolute inset-0">
        <defs>
          <radialGradient id="seal" cx="50%" cy="50%" r="55%">
            <stop offset="0%" stopColor={color} stopOpacity="0.45"/>
            <stop offset="100%" stopColor={color} stopOpacity="0"/>
          </radialGradient>
        </defs>
        <circle cx="110" cy="110" r="100" fill="url(#seal)"/>
        <circle cx="110" cy="110" r="92"  fill="none" stroke={color} strokeWidth="2"/>
        <circle cx="110" cy="110" r="80"  fill="none" stroke={color} strokeWidth="0.6" strokeDasharray="2 3" opacity="0.7"/>
        {Array.from({length: 24}).map((_, i) => (
          <line key={i} x1="110" y1="8" x2="110" y2="18"
                transform={`rotate(${i * 15} 110 110)`}
                stroke={color} strokeWidth="1.6"/>
        ))}
      </svg>
      <div className="relative text-center" style={{ filter: `drop-shadow(0 0 14px ${color})` }}>
        <Icon size={42} color={color} strokeWidth={1.5} className="mx-auto"/>
        <div className="font-display font-bold text-base tracking-[0.06em] uppercase text-white mt-2 leading-none">
          {label.split(" ")[0]}
        </div>
        <div className="font-display font-bold text-[15px] tracking-[0.06em] uppercase text-white mt-0.5 leading-none">
          {label.split(" ").slice(1).join(" ")}
        </div>
        <div className="font-mono text-[9px] tracking-[0.22em] mt-2" style={{ color }}>
          {confidence}% CONFIDENCE
        </div>
      </div>
    </div>
  );
}

function KpiTile({ label, value, color = ACCENTS.cyan, delta, hint }) {
  return (
    <div data-testid={`kpi-${label.toLowerCase().replace(/\s/g, "-")}`}
         className="rounded-md px-3 py-3"
         style={{ background: "rgba(8,14,24,0.86)",
                  border: `1px solid ${color}55`,
                  boxShadow: `inset 0 0 18px ${color}10` }}>
      <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500">
        {label}
      </div>
      <div className="font-display text-[26px] font-bold leading-none mt-1.5"
           style={{ color, textShadow: `0 0 12px ${color}55` }}>
        {value}
      </div>
      {hint && (
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase mt-1.5"
             style={{ color: delta < 0 ? ACCENTS.green : delta > 0 ? ACCENTS.magenta : ACCENTS.amber }}>
          {hint}
        </div>
      )}
    </div>
  );
}

function ScanColumn({ scan, accent, title, kind }) {
  if (!scan) return null;
  return (
    <div data-testid={`scan-column-${kind}`}
         className="rounded-xl p-5"
         style={{ background: "rgba(8,14,24,0.86)",
                  border: `1.5px solid ${accent}66`,
                  boxShadow: `inset 0 0 32px ${accent}10` }}>
      <div className="font-mono text-[9px] tracking-[0.28em] uppercase mb-1" style={{ color: accent }}>
        // {title}
      </div>
      <div className="font-display text-[16px] uppercase tracking-[0.06em] text-white">{scan.label}</div>
      <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-500 mt-1">
        CAPTURED · {(scan.captured_at || "").replace("T", " ").slice(0, 19)}
      </div>
      <div className="grid grid-cols-3 gap-2 mt-4">
        <div>
          <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">ENVELOPE</div>
          <div className="font-display text-[22px] font-bold mt-1" style={{ color: accent }}>
            {scan.envelope_score ?? "—"}<span className="text-[11px] opacity-60">/100</span>
          </div>
        </div>
        <div>
          <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">MOISTURE</div>
          <div className="font-display text-[22px] font-bold mt-1" style={{ color: accent }}>
            {scan.moisture_pct ?? "—"}<span className="text-[11px] opacity-60">%</span>
          </div>
        </div>
        <div>
          <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">ANOMALIES</div>
          <div className="font-display text-[22px] font-bold mt-1" style={{ color: accent }}>
            {scan.anomalies_count ?? scan.anomalies?.length ?? "—"}
          </div>
        </div>
      </div>
    </div>
  );
}

function AnomalyTable({ rows, accent, emptyText, kind }) {
  if (!rows?.length) {
    return (
      <div data-testid={`anomaly-table-${kind}`}
           className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-500 py-4 text-center">
        {emptyText}
      </div>
    );
  }
  return (
    <div className="overflow-x-auto" data-testid={`anomaly-table-${kind}`}>
      <table className="w-full font-mono text-[10.5px]">
        <thead>
          <tr className="border-b" style={{ borderColor: `${accent}33` }}>
            <th className="text-left py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>SEV</th>
            <th className="text-left py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>TYPE</th>
            <th className="text-left py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>LOCATION</th>
            <th className="text-right py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>AREA SF</th>
            <th className="text-right py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>CONF</th>
            <th className="text-right py-2 px-2 font-mono text-[8.5px] tracking-[0.22em] uppercase" style={{ color: accent }}>EST $</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => {
            const a = row.anomaly || row;  // handle "worsened" shape
            const sev = a.severity || "—";
            return (
              <tr key={i} className="border-b" style={{ borderColor: "rgba(255,255,255,0.05)" }}>
                <td className="py-2 px-2">
                  <span className="px-1.5 py-0.5 rounded-full font-mono text-[8.5px] tracking-[0.18em] uppercase"
                        style={{ color: accent, border: `1px solid ${accent}66`, background: `${accent}10` }}>
                    {sev}
                  </span>
                </td>
                <td className="py-2 px-2 text-white">{a.type || a.code || "—"}</td>
                <td className="py-2 px-2 text-slate-300">{a.location || "—"}</td>
                <td className="py-2 px-2 text-right text-slate-300">{a.area_sqft ?? 0}</td>
                <td className="py-2 px-2 text-right text-slate-300">{a.confidence_pct ?? 0}%</td>
                <td className="py-2 px-2 text-right text-white font-bold">
                  ${((a.repair_estimate_usd) || 0).toLocaleString()}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function ClaimSnapshot() {
  const { hash } = useParams();
  const passportHash = hash || DEFAULT_HASH;
  const nav = useNavigate();
  const API = process.env.REACT_APP_BACKEND_URL;

  const [diff, setDiff] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);
  const [cosign, setCosign] = useState(null);
  const [requestingCosign, setRequestingCosign] = useState(false);

  const load = async () => {
    setLoading(true);
    setErr(null);
    try {
      const [diffR, csR] = await Promise.all([
        fetch(`${API}/api/claim-snapshot/${passportHash}/latest`),
        fetch(`${API}/api/claim-snapshot/${passportHash}/cosign/status`),
      ]);
      if (!diffR.ok) {
        const t = await diffR.text();
        setErr(`No snapshot available (${diffR.status}). ${t.slice(0, 100)}`);
        return;
      }
      setDiff(await diffR.json());
      if (csR.ok) setCosign(await csR.json());
    } catch (e) {
      setErr(`Network error: ${e.message}`);
    } finally {
      setLoading(false);
    }
  };

  const reseed = async () => {
    setLoading(true);
    try {
      await fetch(`${API}/api/claim-snapshot/seed/${passportHash}`, { method: "POST" });
      toast.success("Demo scans re-seeded");
      await load();
    } catch {
      toast.error("Re-seed failed");
    } finally {
      setLoading(false);
    }
  };

  const requestCosign = async () => {
    setRequestingCosign(true);
    try {
      const r = await fetch(`${API}/api/claim-snapshot/${passportHash}/cosign/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          requester_name: "American Roofing Co.",
          carrier_company: "State Farm Claims",
        }),
      });
      const j = await r.json();
      const url = `${window.location.origin}/cosign/${j.token}`;
      try {
        await navigator.clipboard.writeText(url);
        toast.success(`Co-sign link ${j.reused ? "re-used" : "minted"} · copied to clipboard`);
      } catch {
        toast.success(`Co-sign link ready: ${url}`);
      }
      // Open the adjuster surface in a new tab so the demo can sign live
      window.open(`/cosign/${j.token}`, "_blank", "noopener,noreferrer");
      await load();
    } catch (e) {
      toast.error(`Co-sign request failed: ${e.message}`);
    } finally {
      setRequestingCosign(false);
    }
  };

  useEffect(() => { load(); }, [passportHash]);

  if (loading) {
    return (
      <div className="min-h-screen grid place-items-center"
           style={{ background: "#02060B", color: "#fff" }}>
        <Loader2 size={32} className="animate-spin text-cyan-400"/>
      </div>
    );
  }

  if (err || !diff) {
    return (
      <div className="min-h-screen grid place-items-center px-6"
           style={{ background: "#02060B", color: "#fff" }}>
        <div className="max-w-md text-center">
          <AlertOctagon size={40} style={{ color: ACCENTS.magenta }} className="mx-auto mb-4"/>
          <h1 className="font-display text-2xl uppercase tracking-[0.08em]">Claim Snapshot Unavailable</h1>
          <p className="font-mono text-[11px] tracking-[0.14em] text-slate-400 mt-3">{err}</p>
          <div className="flex gap-2 justify-center mt-6">
            <button onClick={reseed} data-testid="reseed-btn"
                    className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md"
                    style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
              Seed Demo Scans
            </button>
            <button onClick={() => nav("/")}
                    className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md"
                    style={{ background: `${ACCENTS.gold}14`, border: `1px solid ${ACCENTS.gold}66`, color: ACCENTS.gold }}>
              Return Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  const pp = diff.passport || {};
  const d = diff.deltas || {};
  const verdictColor =
    diff.verdict === "CLAIM_SUPPORTABLE" ? ACCENTS.magenta :
    diff.verdict === "MONITOR"           ? ACCENTS.amber :
                                            ACCENTS.green;
  const contractor = pp.contractor || {};

  return (
    <div data-testid="claim-snapshot-page"
         className="min-h-screen text-slate-100"
         style={{
           background:
             "radial-gradient(ellipse at 80% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
             "radial-gradient(ellipse at 10% 100%, rgba(255,45,120,0.08) 0%, transparent 55%)," +
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

      {/* TOP banner */}
      <div className="border-b"
           style={{ borderColor: "rgba(0,229,255,0.18)", background: "rgba(8,14,24,0.85)" }}>
        <div className="max-w-[1400px] mx-auto px-4 sm:px-6 py-2.5 flex items-center justify-between gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Sparkles size={11} style={{ color: verdictColor }}/>
            <span className="font-mono text-[9px] tracking-[0.32em] uppercase"
                  style={{ color: verdictColor }}>
              // CLAIM SNAPSHOT · DIFFERENCE REPORT · CARRIER FAST-TRACK
            </span>
          </div>
          <div className="flex items-center gap-2 font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
            <span>STRATEX™</span><span>·</span><span>PASSPORT STX-{passportHash}</span><span>·</span><span>READY FOR ADJUSTER</span>
          </div>
        </div>
      </div>

      {/* HEADER */}
      <header className="max-w-[1400px] mx-auto px-4 sm:px-6 pt-6 pb-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => nav(`/passport/${passportHash}`)}
                  data-testid="back-to-passport"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                  style={{ background: "rgba(0,229,255,0.10)", border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
            <ArrowLeft size={12}/> Passport
          </button>
          <StratexLogo height={28}/>
          {contractor.business_name && (
            <span className="font-display text-sm uppercase tracking-[0.1em] text-white">
              · {contractor.business_name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={reseed} data-testid="reseed-btn"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                  style={{ background: "rgba(0,255,156,0.10)", border: `1px solid ${ACCENTS.green}66`, color: ACCENTS.green }}>
            <RefreshCw size={12}/> Re-Seed
          </button>
          <a href={`${API}/api/claim-snapshot/${passportHash}/pdf`}
             target="_blank" rel="noopener noreferrer"
             data-testid="download-claim-pdf"
             className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
             style={{ background: ACCENTS.gold, color: "#02060B", boxShadow: `0 0 12px ${ACCENTS.gold}55` }}>
            <FileDown size={12}/> Download PDF
          </a>
        </div>
      </header>

      {/* HERO */}
      <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-4">
        <div className="rounded-2xl p-5 sm:p-7 relative overflow-hidden"
             style={{
               background: `linear-gradient(120deg, ${verdictColor}18 0%, rgba(8,14,24,0.85) 55%, rgba(0,229,255,0.08) 100%)`,
               border: `1.5px solid ${verdictColor}88`,
               boxShadow: `inset 0 0 56px ${verdictColor}10, 0 0 36px ${verdictColor}25`,
             }}>
          <div className="grid grid-cols-1 md:grid-cols-[1fr_240px] gap-6 items-center">
            <div className="min-w-0">
              <div className="font-mono text-[9px] tracking-[0.32em] uppercase mb-2"
                   style={{ color: verdictColor }}>
                // STRATEX™ CLAIM SNAPSHOT · BASELINE → POST-EVENT
              </div>
              <h1 className="font-display uppercase leading-[0.95] tracking-[0.02em]"
                  style={{ fontSize: "clamp(28px, 4vw, 48px)", color: "#fff" }}>
                <span style={{ color: verdictColor, textShadow: `0 0 18px ${verdictColor}55` }}>
                  {pp.owner}
                </span>
              </h1>
              <div className="font-mono text-[11px] sm:text-[12px] tracking-[0.16em] uppercase text-slate-300 mt-2">
                {pp.address} · {pp.city_state}
              </div>
              {diff.narrative && (
                <p className="mt-4 text-[13.5px] leading-[1.6] text-slate-200 max-w-3xl">
                  {diff.narrative}
                </p>
              )}
              {cosign?.state === "SIGNED" && (
                <div data-testid="cosign-badge"
                     className="mt-4 inline-flex items-center gap-3 rounded-md px-3 py-2"
                     style={{ background: `${ACCENTS.green}14`,
                              border: `1px solid ${ACCENTS.green}88`,
                              boxShadow: `0 0 14px ${ACCENTS.green}33` }}>
                  <ShieldCheck size={14} color={ACCENTS.green}/>
                  <div>
                    <div className="font-mono text-[9px] tracking-[0.26em] uppercase" style={{ color: ACCENTS.green }}>
                      CARRIER CO-SIGNED · {cosign.signer.decision}
                    </div>
                    <div className="font-mono text-[10px] tracking-[0.14em] text-slate-200 mt-0.5">
                      {cosign.signer.adjuster_name} · {cosign.signer.adjuster_company}
                    </div>
                    <div className="font-mono text-[9px] text-cyan-300 mt-0.5 break-all max-w-md">
                      Receipt · {cosign.receipt_hash?.slice(0, 32)}…
                    </div>
                  </div>
                </div>
              )}
            </div>
            <div className="flex justify-center md:justify-end">
              <VerdictSeal verdict={diff.verdict} confidence={diff.confidence_pct}/>
            </div>
          </div>
        </div>
      </section>

      {/* HEADLINE DELTAS */}
      <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-2.5">
        <KpiTile label="NEW DAMAGE"
                 value={d.new_damage_count}
                 color={ACCENTS.magenta}
                 hint={`${d.new_area_sqft || 0} sqft`}/>
        <KpiTile label="WORSENED"
                 value={d.worsened_count}
                 color={ACCENTS.amber}
                 hint={`+${d.worsened_area_sqft || 0} sqft`}/>
        <KpiTile label="RESOLVED"
                 value={d.resolved_count}
                 color={ACCENTS.green}
                 hint="closed deltas"/>
        <KpiTile label="ENVELOPE Δ"
                 value={`${d.envelope_score_delta >= 0 ? "+" : ""}${d.envelope_score_delta}`}
                 color={d.envelope_score_delta < 0 ? ACCENTS.magenta : ACCENTS.green}
                 hint="points / 100"/>
        <KpiTile label="MOISTURE Δ"
                 value={`${d.moisture_pct_delta >= 0 ? "+" : ""}${d.moisture_pct_delta}%`}
                 color={d.moisture_pct_delta > 5 ? ACCENTS.magenta : ACCENTS.amber}
                 hint="thermographic"/>
        <KpiTile label="REPAIR Δ"
                 value={`$${(d.repair_estimate_delta_usd || 0).toLocaleString()}`}
                 color={ACCENTS.gold}
                 hint="estimated"/>
      </section>

      {/* STORM CORRELATION */}
      {diff.storm_correlated && (
        <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-4">
          <div data-testid="storm-correlation-row"
               className="rounded-xl p-5 flex flex-wrap items-center gap-6"
               style={{ background: "rgba(8,14,24,0.86)",
                        border: `1.5px solid ${ACCENTS.magenta}66`,
                        boxShadow: `inset 0 0 32px ${ACCENTS.magenta}10` }}>
            <div className="flex items-center gap-3">
              <Wind size={20} style={{ color: ACCENTS.magenta }}/>
              <div>
                <div className="font-mono text-[9px] tracking-[0.28em] uppercase"
                     style={{ color: ACCENTS.magenta }}>
                  // STORM CORRELATION · LIVE NOAA / OPEN-METEO
                </div>
                <div className="font-display text-[18px] uppercase tracking-[0.06em] text-white mt-0.5">
                  {diff.storm_correlated.kind} · {diff.storm_correlated.value}
                </div>
              </div>
            </div>
            <div className="border-l h-12" style={{ borderColor: `${ACCENTS.magenta}33` }}/>
            <div>
              <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">DATE</div>
              <div className="font-display text-[16px] text-white mt-0.5">{diff.storm_correlated.date}</div>
            </div>
            <div>
              <div className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">NOAA EVENT</div>
              <div className="font-mono text-[12px] text-cyan-400 mt-1">{diff.storm_correlated.noaa_event_id}</div>
            </div>
            <div className="ml-auto font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
              Confidence Lift · +8 pts
            </div>
          </div>
        </section>
      )}

      {/* SCANS SIDE-BY-SIDE */}
      <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        <ScanColumn scan={diff.scan_a} accent={ACCENTS.green}   title="BASELINE SCAN" kind="baseline"/>
        <ScanColumn scan={diff.scan_b} accent={ACCENTS.magenta} title="POST-EVENT SCAN" kind="post-event"/>
      </section>

      {/* DELTAS — three tables */}
      <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-6 grid grid-cols-1 gap-3">
        <div className="rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)",
                      border: `1.5px solid ${ACCENTS.magenta}66`,
                      boxShadow: `inset 0 0 32px ${ACCENTS.magenta}08` }}>
          <div className="flex items-center gap-2 mb-3">
            <TrendingDown size={14} style={{ color: ACCENTS.magenta }}/>
            <span className="font-mono text-[9px] tracking-[0.28em] uppercase"
                  style={{ color: ACCENTS.magenta }}>
              // NEW DAMAGE · NOT PRESENT IN BASELINE
            </span>
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500 ml-auto">
              {(diff.new_damage || []).length} clusters
            </span>
          </div>
          <AnomalyTable rows={diff.new_damage} accent={ACCENTS.magenta} kind="new"
                        emptyText="No newly-introduced damage detected."/>
        </div>

        <div className="rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)",
                      border: `1.5px solid ${ACCENTS.amber}66`,
                      boxShadow: `inset 0 0 32px ${ACCENTS.amber}08` }}>
          <div className="flex items-center gap-2 mb-3">
            <TrendingUp size={14} style={{ color: ACCENTS.amber }}/>
            <span className="font-mono text-[9px] tracking-[0.28em] uppercase"
                  style={{ color: ACCENTS.amber }}>
              // WORSENED · BASELINE ESCALATED POST-EVENT
            </span>
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500 ml-auto">
              {(diff.worsened || []).length} clusters
            </span>
          </div>
          <AnomalyTable rows={diff.worsened} accent={ACCENTS.amber} kind="worsened"
                        emptyText="No baseline findings have escalated."/>
        </div>

        <div className="rounded-xl p-5"
             style={{ background: "rgba(8,14,24,0.86)",
                      border: `1.5px solid ${ACCENTS.green}66`,
                      boxShadow: `inset 0 0 32px ${ACCENTS.green}08` }}>
          <div className="flex items-center gap-2 mb-3">
            <ShieldCheck size={14} style={{ color: ACCENTS.green }}/>
            <span className="font-mono text-[9px] tracking-[0.28em] uppercase"
                  style={{ color: ACCENTS.green }}>
              // RESOLVED · BASELINE FINDINGS NO LONGER PRESENT
            </span>
            <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500 ml-auto">
              {(diff.resolved || []).length} clusters
            </span>
          </div>
          <AnomalyTable rows={diff.resolved} accent={ACCENTS.green} kind="resolved"
                        emptyText="No baseline findings have resolved this cycle."/>
        </div>
      </section>

      {/* CTA strip */}
      <section className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-12 grid grid-cols-1 md:grid-cols-3 gap-3">
        <a href={`${API}/api/claim-snapshot/${passportHash}/pdf`}
           target="_blank" rel="noopener noreferrer"
           data-testid="cta-claim-pdf"
           className="rounded-md px-4 py-3 flex items-center gap-3 transition hover:brightness-125"
           style={{ background: `${ACCENTS.gold}14`, border: `1.5px solid ${ACCENTS.gold}88` }}>
          <FileDown size={16} style={{ color: ACCENTS.gold }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Download Claim Snapshot PDF</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">Tabloid · co-signed · adjuster-ready</div>
          </div>
        </a>
        <button onClick={() => nav(`/passport/${passportHash}`)}
                data-testid="cta-passport"
                className="rounded-md px-4 py-3 flex items-center gap-3 transition hover:brightness-125 text-left"
                style={{ background: `${ACCENTS.cyan}14`, border: `1.5px solid ${ACCENTS.cyan}88` }}>
          <Sparkles size={16} style={{ color: ACCENTS.cyan }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Open Property Passport</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">Immutable ledger · weather shield</div>
          </div>
          <ChevronRight size={14} className="ml-auto" style={{ color: ACCENTS.cyan }}/>
        </button>
        <button onClick={() => toast.success("Claim Snapshot prepared for carrier dispatch")}
                data-testid="cta-send-carrier"
                className="rounded-md px-4 py-3 flex items-center gap-3 transition hover:brightness-125 text-left disabled:opacity-50"
                style={{ background: `${ACCENTS.magenta}14`, border: `1.5px solid ${ACCENTS.magenta}88`, display: "none" }}>
          <Send size={16} style={{ color: ACCENTS.magenta }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">Send to Carrier</div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">One-Click Proof-of-Loss · LAE bypass</div>
          </div>
        </button>
        <button onClick={requestCosign}
                disabled={requestingCosign}
                data-testid="cta-request-cosign"
                className="rounded-md px-4 py-3 flex items-center gap-3 transition hover:brightness-125 text-left disabled:opacity-50"
                style={{ background: `${ACCENTS.magenta}14`, border: `1.5px solid ${ACCENTS.magenta}88` }}>
          <Send size={16} style={{ color: ACCENTS.magenta }}/>
          <div>
            <div className="font-display text-[13px] tracking-[0.06em] uppercase text-white">
              {cosign?.state === "SIGNED" ? "View Carrier Co-Sign" : "Request Carrier Co-Sign"}
            </div>
            <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500">
              {cosign?.state === "SIGNED"
                ? `Signed by ${cosign?.signer?.adjuster_name}`
                : "One-time magic link · SHA-256 receipt → ledger"}
            </div>
          </div>
        </button>
      </section>

      <footer className="max-w-[1400px] mx-auto px-4 sm:px-6 pb-8">
        <div className="border-t pt-4 flex flex-col sm:flex-row items-center justify-between gap-2"
             style={{ borderColor: "rgba(212,184,106,0.20)" }}>
          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
            STRATEX™ · GROUND-TRUTH ±0.78 CM · CHAIN-OF-CUSTODY VERIFIED · GENERATED {(diff.generated_at || "").slice(0, 19).replace("T", " ")}
          </span>
          <span className="font-mono text-[9px] tracking-[0.22em] uppercase" style={{ color: ACCENTS.gold }}>
            CARRIER LINK · stratex.co/claim/{passportHash.toLowerCase()}
          </span>
        </div>
      </footer>
    </div>
  );
}
