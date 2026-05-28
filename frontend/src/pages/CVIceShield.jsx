/**
 * /admin/cv-ice-shield — Sub-Surface Ice & Water Shield CV Analysis browser.
 *
 * Admin-facing dashboard for the strict-typed validator in
 * /app/backend/roof_cv_ice_shield.py. Cross-references db.cv_ice_shield_analyses
 * with db.telemetry_halts so reviewers can jump straight from a halted frame
 * into the Overseer queue.
 */
import React, { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck,
  Droplets,
  AlertOctagon,
  RotateCw,
  ChevronRight,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";

const CLASSIFICATIONS = [
  { key: "all", label: "All" },
  { key: "Ice_Water_Shield_Present", label: "I&WS Confirmed", color: TEAL, icon: ShieldCheck },
  { key: "Moisture_Anomaly", label: "Moisture", color: ORANGE, icon: Droplets },
  { key: "Unverified_Halt", label: "Halted", color: ORANGE, icon: AlertOctagon },
];

const classMeta = (c) => CLASSIFICATIONS.find((x) => x.key === c) || CLASSIFICATIONS[0];

export default function CVIceShield() {
  const [data, setData] = useState({ items: [], counts: {}, count: 0 });
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [forbidden, setForbidden] = useState(false);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const r = await api.get("/cv/ice-shield/recent?limit=100");
      setData(r.data || { items: [], counts: {}, count: 0 });
    } catch (err) {
      if (err?.response?.status === 403) setForbidden(true);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  const rows = useMemo(() => {
    if (filter === "all") return data.items;
    return data.items.filter((d) => d.analysis.classification === filter);
  }, [data, filter]);

  if (forbidden) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center p-8" data-testid="cv-ice-shield-forbidden">
        <div className="border p-8 max-w-md" style={{ borderColor: ORANGE, background: `${ORANGE}10` }}>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: ORANGE }}>
            // 403 — ACCESS DENIED
          </div>
          <h1 className="font-display text-2xl uppercase tracking-widest mb-2">Admin Privilege Required</h1>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="cv-ice-shield-root">
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="led led-teal"/>
          <div className="font-mono text-[11px] tracking-[0.36em] uppercase" style={{ color: TEAL }}>
            // STRATEX VISION • CV PIPELINE • ICE &amp; WATER SHIELD
          </div>
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">Sub-Surface I&amp;WS Analyses</h1>
        <p className="font-body text-sm text-muted-hud mb-6 max-w-3xl">
          Every parsed thermal-IR valley frame passed through{" "}
          <span className="font-mono" style={{ color: TEAL }}>analyze_valley_frame</span>: ε=0.92, ΔT∈[0.5°C, 1.5°C],
          VALLEY_MASK 36"±2", post-sunset T+2h…T+6h. Frames with composite confidence &lt; 0.90 are auto-halted into
          the Overseer queue.
        </p>

        {/* Counts strip */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5" data-testid="cv-ice-shield-counts">
          <Stat label="Total frames" value={data.count} accent={TEAL}/>
          <Stat label="I&amp;WS Confirmed" value={data.counts.ice_water_shield_present || 0} accent={TEAL}/>
          <Stat label="Moisture Anomalies" value={data.counts.moisture_anomaly || 0} accent={ORANGE}/>
          <Stat label="Halted to Overseer" value={data.counts.unverified_halt || 0} accent={ORANGE}/>
        </div>

        {/* Filter chips + refresh */}
        <div className="flex items-center gap-2 mb-4 flex-wrap" data-testid="cv-ice-shield-filters">
          {CLASSIFICATIONS.map((c) => {
            const active = filter === c.key;
            const accent = c.color || TEAL;
            return (
              <button
                key={c.key}
                onClick={() => setFilter(c.key)}
                data-testid={`cv-filter-${c.key}`}
                className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border"
                style={{
                  color: active ? "#0B0F17" : accent,
                  background: active ? accent : `${accent}10`,
                  borderColor: accent,
                }}
              >
                {c.label}
              </button>
            );
          })}
          <button
            onClick={load}
            data-testid="cv-refresh"
            className="ml-auto font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border inline-flex items-center gap-2"
            style={{ borderColor: `${TEAL}55`, color: TEAL }}
          >
            <RotateCw size={11}/> Refresh
          </button>
          <Link
            to="/admin/overseer"
            data-testid="cv-link-overseer"
            className="font-mono text-[10px] uppercase tracking-widest px-3 py-1.5 border inline-flex items-center gap-1"
            style={{ borderColor: `${ORANGE}55`, color: ORANGE }}
          >
            Overseer Queue <ExternalLink size={10}/>
          </Link>
        </div>

        {loading && <div className="font-mono" style={{ color: TEAL }}>// LOADING…</div>}

        {!loading && rows.length === 0 && (
          <div className="border p-12 text-center" style={{ borderColor: NICKEL }} data-testid="cv-ice-shield-empty">
            <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud mb-2">// NO ANALYSES IN THIS BAND</div>
            <p className="font-body text-sm text-silver">
              Submit frames to <span className="font-mono" style={{ color: TEAL }}>POST /api/cv/ice-shield/analyze</span> to populate this view.
            </p>
          </div>
        )}

        <ul className="space-y-3" data-testid="cv-ice-shield-rows">
          {rows.map((d) => {
            const meta = classMeta(d.analysis.classification);
            const Icon = meta.icon || ShieldCheck;
            const isHalt = d.analysis.classification === "Unverified_Halt";
            const accent = meta.color || TEAL;
            const isExpanded = expanded === d.frame_id;
            return (
              <li
                key={`${d.id || d.frame_id}-${d.created_at}`}
                data-testid={`cv-row-${d.frame_id}`}
                className="border-l-4 bg-[#0B0F19] border-y border-r"
                style={{ borderLeftColor: accent, borderColor: NICKEL }}
              >
                <button
                  onClick={() => setExpanded(isExpanded ? null : d.frame_id)}
                  className="w-full text-left px-4 py-3 flex items-center gap-3 flex-wrap"
                >
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5 border inline-flex items-center gap-1.5"
                    style={{ color: accent, borderColor: accent }}
                  >
                    <Icon size={11}/> {meta.label}
                  </span>
                  <span className="font-mono text-[10px]" style={{ color: TEAL }}>{d.frame_id}</span>
                  <span className="font-mono text-[10px] text-silver">job {(d.job_id || "").slice(0, 10)}</span>
                  <span className="font-mono text-[10px] text-muted-hud">valley {d.valley_track_id}</span>
                  <span
                    className="font-mono text-[10px] ml-2 px-2 py-0.5 border"
                    style={{ color: accent, borderColor: `${accent}55` }}
                  >
                    conf {Number(d.analysis.confidence || 0).toFixed(3)}
                  </span>
                  {isHalt && (
                    <Link
                      to="/admin/overseer"
                      onClick={(e) => e.stopPropagation()}
                      data-testid={`cv-jump-overseer-${d.frame_id}`}
                      className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5 border inline-flex items-center gap-1"
                      style={{ color: ORANGE, borderColor: ORANGE }}
                    >
                      Open in Overseer <ExternalLink size={9}/>
                    </Link>
                  )}
                  <span className="ml-auto font-mono text-[9.5px] text-muted-hud">
                    {new Date(d.created_at).toLocaleString()}
                  </span>
                  <ChevronRight size={14} className="text-muted-hud" style={{ transform: isExpanded ? "rotate(90deg)" : "none", transition: "transform .18s" }}/>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t" style={{ borderColor: NICKEL }} data-testid={`cv-detail-${d.frame_id}`}>
                    <div className="grid md:grid-cols-2 gap-4 text-[11px] font-mono">
                      <div className="space-y-1">
                        <div className="text-muted-hud">// ANALYSIS</div>
                        <div><span className="text-muted-hud">classification</span> · <span style={{ color: accent }}>{d.analysis.classification}</span></div>
                        <div><span className="text-muted-hud">confidence</span> · {Number(d.analysis.confidence).toFixed(4)}</div>
                        <div><span className="text-muted-hud">has_ice_and_water_shield</span> · {String(d.analysis.has_ice_and_water_shield)}</div>
                        <div><span className="text-muted-hud">code_compliant_underlayment</span> · {String(d.analysis.code_compliant_underlayment)}</div>
                        <div><span className="text-muted-hud">flag_for_estimation_pipeline</span> · {String(d.analysis.flag_for_estimation_pipeline)}</div>
                        <div className="text-muted-hud mt-2">// PRECONDITIONS</div>
                        {(d.analysis.preconditions || []).map((p) => (
                          <div key={p.name}>
                            <span style={{ color: p.passed ? TEAL : ORANGE }}>[{p.passed ? "PASS" : "FAIL"}]</span>{" "}
                            <span className="text-muted-hud">{p.name}</span>{" "}
                            <span className="text-silver">{p.detail}</span>
                          </div>
                        ))}
                      </div>
                      <div className="space-y-1">
                        <div className="text-muted-hud">// FRAME</div>
                        <div><span className="text-muted-hud">frame_id</span> · {d.frame_id}</div>
                        <div><span className="text-muted-hud">contractor_id</span> · {d.contractor_id}</div>
                        <div><span className="text-muted-hud">job_id</span> · {d.job_id}</div>
                        <div><span className="text-muted-hud">valley_track_id</span> · {d.valley_track_id}</div>
                        <div><span className="text-muted-hud">submitted_by</span> · {d.submitted_role}</div>
                        {d.halt_record && (
                          <>
                            <div className="text-muted-hud mt-2">// HALT RECORD</div>
                            <div><span className="text-muted-hud">error_state</span> · <span style={{ color: ORANGE }}>{d.halt_record.error_state}</span></div>
                            <div><span className="text-muted-hud">review_priority</span> · {d.halt_record.review_priority}</div>
                            <div><span className="text-muted-hud">status</span> · {d.halt_record.status}</div>
                          </>
                        )}
                      </div>
                    </div>
                    {d.analysis.reasoning && (
                      <p className="mt-3 font-body text-[12px] leading-relaxed" style={{ color: accent }}>
                        {d.analysis.reasoning}
                      </p>
                    )}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="border p-3" style={{ borderColor: `${accent}55`, background: `${accent}0C` }}>
      <div className="font-mono text-[9.5px] uppercase tracking-[0.22em]" style={{ color: accent }}>{label}</div>
      <div className="font-display text-2xl mt-1 text-silver">{value}</div>
    </div>
  );
}
