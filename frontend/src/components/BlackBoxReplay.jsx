/**
 * BlackBoxReplay — post-mortem flight replay modal.
 *
 * Triggered from /admin/consensus when an auditor clicks a verdict row.
 * Renders an immutable mini-map of the flight at the time the verdict was
 * committed (snapshot is embedded on the audit doc as `flight_trail`),
 * animates a moving cursor along the path, draws an altitude sparkline,
 * and exposes verdict + variance details.
 *
 * Pure addition; no existing component touched.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, Polyline, Marker, useMap, CircleMarker } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Play, Pause, RotateCcw, X, ShieldCheck, AlertTriangle } from "lucide-react";

const FN_GREEN = "#10b981";
const FN_AMBER = "#f59e0b";
const FN_TEAL = "#22d3ee";
const FN_RED = "#ef4444";
const FN_INK = "#e2e8f0";
const FN_DIM = "#64748b";

const altSegColor = (a, b) => {
  const da = (b ?? 0) - (a ?? 0);
  if (da > 0.5) return FN_GREEN;
  if (da < -0.5) return FN_AMBER;
  return FN_TEAL;
};

const fmt = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
};

function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (!points?.length) return;
    if (points.length === 1) { map.setView([points[0][0], points[0][1]], 17); return; }
    map.fitBounds(L.latLngBounds(points.map(p => [p[0], p[1]])), { padding: [22, 22] });
  }, [points, map]);
  return null;
}

export default function BlackBoxReplay({ verdict, onClose }) {
  const trail = useMemo(() => (verdict?.flight_trail || []).filter(p => Array.isArray(p) && p.length >= 2), [verdict]);
  const hasTrail = trail.length >= 2;
  const [idx, setIdx] = useState(0);
  const [playing, setPlaying] = useState(true);
  const timerRef = useRef(null);

  useEffect(() => { setIdx(0); }, [verdict]);

  useEffect(() => {
    if (!playing || !hasTrail) return;
    timerRef.current = setInterval(() => {
      setIdx((i) => (i >= trail.length - 1 ? 0 : i + 1));
    }, 320);
    return () => clearInterval(timerRef.current);
  }, [playing, hasTrail, trail.length]);

  if (!verdict) return null;

  const ok = verdict.verification_status === "AUTHENTICATED";
  const cursor = hasTrail ? trail[idx] : null;
  const minAlt = Math.min(...trail.map(p => p[2] ?? 0));
  const maxAlt = Math.max(...trail.map(p => p[2] ?? 0));
  const altRange = Math.max(0.5, maxAlt - minAlt);

  return (
    <div data-testid="black-box-replay-modal"
         onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
         style={{
           position: "fixed", inset: 0, zIndex: 9000,
           background: "radial-gradient(ellipse at center, rgba(2,8,16,0.85), rgba(2,8,16,0.96))",
           backdropFilter: "blur(8px)",
           display: "flex", alignItems: "center", justifyContent: "center",
           padding: 24,
         }}>
      <div style={{
        width: "min(1100px, 100%)", maxHeight: "92vh", overflowY: "auto",
        background: "linear-gradient(155deg, rgba(15,30,55,0.96), rgba(6,12,24,0.98))",
        border: `1px solid ${FN_TEAL}55`, borderRadius: 10,
        boxShadow: `0 40px 90px -20px ${FN_TEAL}55, 0 0 0 1px ${FN_TEAL}22 inset`,
        padding: "22px 26px",
      }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 14 }}>
          <div>
            <div style={{ fontFamily: "monospace", fontSize: 10, letterSpacing: "0.32em",
                          color: FN_TEAL, textTransform: "uppercase" }}>
              // BLACK BOX · FLIGHT REPLAY
            </div>
            <div style={{ fontSize: 18, fontWeight: 700, marginTop: 4, letterSpacing: 0.4 }}>
              {verdict.job_id} · <span style={{ color: ok ? FN_GREEN : FN_AMBER }}>
                {ok ? "AUTHENTICATED" : verdict.verification_status}
              </span>
            </div>
            <div style={{ marginTop: 4, fontFamily: "monospace", fontSize: 11,
                          color: FN_DIM, letterSpacing: "0.06em" }}>
              {fmt(verdict.created_at)} · CONSENSUS {(verdict.consensus_score ?? 0).toFixed(1)}%
              {verdict.injected_for_demo && (
                <span style={{ marginLeft: 10, padding: "1px 6px", borderRadius: 2,
                               border: "1px solid #ec489955", background: "rgba(236,72,153,0.10)",
                               color: "#f472b6", fontSize: 9, letterSpacing: "0.22em",
                               textTransform: "uppercase", fontWeight: 700 }}>DEMO</span>
              )}
            </div>
          </div>
          <button onClick={onClose} data-testid="black-box-close" style={{
            background: "transparent", border: "1px solid #334155", color: FN_DIM,
            padding: "6px 8px", borderRadius: 4, cursor: "pointer",
          }}><X size={14}/></button>
        </div>

        {/* Body */}
        <div style={{ display: "grid", gridTemplateColumns: "1.6fr 1fr", gap: 16 }}>
          {/* Map column */}
          <div data-testid="black-box-map" style={{
            border: `1px solid ${FN_TEAL}44`, borderRadius: 6, overflow: "hidden", background: "#020812",
          }}>
            {hasTrail ? (
              <MapContainer center={[trail[0][0], trail[0][1]]} zoom={17}
                            style={{ height: 380, width: "100%", background: "#020812" }}>
                <TileLayer
                  attribution='Esri'
                  url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
                />
                <FitBounds points={trail}/>
                {/* halo */}
                <Polyline positions={trail.map(p => [p[0], p[1]])}
                          pathOptions={{ color: FN_TEAL, weight: 6, opacity: 0.14 }}/>
                {/* per-segment altitude trail */}
                {trail.slice(0, -1).map((pt, i) => (
                  <Polyline key={i}
                            positions={[[pt[0], pt[1]], [trail[i+1][0], trail[i+1][1]]]}
                            pathOptions={{
                              color: altSegColor(pt[2], trail[i+1][2]),
                              weight: i < idx ? 3.2 : 1.6,
                              opacity: i < idx ? 1 : 0.45,
                              dashArray: i < idx ? null : "1 5",
                            }}/>
                ))}
                {/* animated playhead */}
                {cursor && (
                  <CircleMarker center={[cursor[0], cursor[1]]} radius={7}
                                pathOptions={{ color: FN_TEAL, fillColor: FN_TEAL,
                                               fillOpacity: 1, weight: 2 }}/>
                )}
              </MapContainer>
            ) : (
              <div style={{ height: 380, display: "flex", flexDirection: "column",
                            alignItems: "center", justifyContent: "center",
                            color: FN_DIM, fontFamily: "monospace", textAlign: "center", padding: 24 }}>
                <AlertTriangle size={28}/>
                <div style={{ marginTop: 10, letterSpacing: "0.2em", textTransform: "uppercase", fontSize: 12 }}>
                  No flight trail snapshot
                </div>
                <div style={{ marginTop: 6, fontSize: 11, color: "#475569", maxWidth: 360 }}>
                  This verdict was committed before the Black Box snapshot system was wired in. Trigger a fresh consensus run to capture flight data on the next verdict.
                </div>
              </div>
            )}
            {/* altitude sparkline */}
            {hasTrail && (
              <div data-testid="black-box-altitude-sparkline" style={{
                padding: "10px 14px", borderTop: `1px solid ${FN_TEAL}33`,
                background: "rgba(8,18,34,0.7)",
              }}>
                <div style={{ display: "flex", justifyContent: "space-between",
                              fontFamily: "monospace", fontSize: 9, letterSpacing: "0.22em",
                              color: FN_DIM, textTransform: "uppercase", marginBottom: 6 }}>
                  <span>ALTITUDE PROFILE · {trail.length} POINTS</span>
                  <span>{minAlt.toFixed(1)}m → {maxAlt.toFixed(1)}m</span>
                </div>
                <div style={{ display: "flex", gap: 2, alignItems: "flex-end", height: 38 }}>
                  {trail.map((p, i) => {
                    const h = Math.max(3, ((p[2] ?? 0) - minAlt) / altRange * 34);
                    const seg = i > 0 ? altSegColor(trail[i-1][2], p[2]) : FN_TEAL;
                    const isPlayed = i <= idx;
                    return (
                      <div key={i} style={{
                        flex: 1, height: h,
                        background: isPlayed ? seg : `${seg}33`,
                        borderRadius: 1,
                        boxShadow: i === idx ? `0 0 8px ${seg}` : "none",
                        transition: "background-color 120ms, box-shadow 120ms",
                      }}/>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Details column */}
          <div data-testid="black-box-details" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            <DetailBlock label="ACTION" value={verdict.action || "—"}/>
            <DetailBlock label="FINAL ALTITUDE"
                         value={verdict.flight_meta?.final_altitude_m
                                ? `${verdict.flight_meta.final_altitude_m.toFixed(1)} m · ${verdict.flight_meta.final_climb_state || "—"}`
                                : "—"}/>
            <DetailBlock label="FINAL HEADING"
                         value={verdict.flight_meta?.final_heading_deg
                                ? `${verdict.flight_meta.final_heading_deg.toFixed(0)}°`
                                : "—"}/>

            <div style={{ marginTop: 4 }}>
              <div style={{ color: FN_TEAL, fontFamily: "monospace", fontSize: 9,
                            letterSpacing: "0.24em", textTransform: "uppercase", marginBottom: 6 }}>
                AGENT MATRIX
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                {(verdict.audit_records || []).map((r, i) => {
                  const base = verdict.audit_records?.[0];
                  const diverged = base && r !== base && (
                    r.calculated_area !== base.calculated_area ||
                    r.moisture_footprint !== base.moisture_footprint ||
                    r.bom_cost_evaluation !== base.bom_cost_evaluation
                  );
                  const c = diverged ? FN_RED : FN_GREEN;
                  return (
                    <div key={i} style={{
                      border: `1px solid ${c}55`, background: `${c}10`,
                      borderRadius: 3, padding: 6, fontFamily: "monospace",
                      fontSize: 9, color: FN_INK,
                    }}>
                      <div style={{ color: c, letterSpacing: "0.1em", marginBottom: 2 }}>
                        {diverged ? "✕ VARIANCE" : "✓ NOMINAL"}
                      </div>
                      <div style={{ color: FN_DIM, letterSpacing: "0.06em" }}>
                        {r.agent.replace("AI_VALIDATOR_", "V").replace(/_/g, " ")}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {verdict.error_logs?.length > 0 && (
              <div style={{
                marginTop: 4, padding: 8, borderRadius: 3,
                border: `1px solid ${FN_RED}55`, background: `${FN_RED}10`,
                fontFamily: "monospace", fontSize: 9, color: "#fca5a5", lineHeight: 1.55,
              }}>
                <div style={{ color: FN_RED, letterSpacing: "0.2em", fontSize: 9, marginBottom: 4 }}>
                  ⚠ VARIANCE LOG
                </div>
                {verdict.error_logs.slice(0, 3).map((l, i) => <div key={i}>· {l}</div>)}
              </div>
            )}

            {/* Transport controls */}
            <div style={{ marginTop: "auto", display: "flex", gap: 6, alignItems: "center",
                          padding: 8, border: `1px solid ${FN_TEAL}33`, borderRadius: 4,
                          background: "rgba(34,211,238,0.05)" }}>
              <button onClick={() => setPlaying(p => !p)} disabled={!hasTrail}
                      data-testid="black-box-play-toggle"
                      style={{ background: FN_TEAL, color: "#020812", border: "none",
                               padding: "5px 9px", borderRadius: 3, cursor: hasTrail ? "pointer" : "not-allowed",
                               opacity: hasTrail ? 1 : 0.4 }}>
                {playing ? <Pause size={11}/> : <Play size={11}/>}
              </button>
              <button onClick={() => setIdx(0)} disabled={!hasTrail}
                      data-testid="black-box-reset"
                      style={{ background: "transparent", border: `1px solid ${FN_TEAL}55`,
                               color: FN_TEAL, padding: "5px 9px", borderRadius: 3,
                               cursor: hasTrail ? "pointer" : "not-allowed" }}>
                <RotateCcw size={11}/>
              </button>
              <input type="range" min={0} max={Math.max(0, trail.length - 1)} value={idx}
                     disabled={!hasTrail}
                     data-testid="black-box-scrubber"
                     onChange={(e) => { setIdx(Number(e.target.value)); setPlaying(false); }}
                     style={{ flex: 1, accentColor: FN_TEAL }}/>
              <span style={{ fontFamily: "monospace", fontSize: 9, color: FN_DIM,
                             letterSpacing: "0.1em", minWidth: 50, textAlign: "right" }}>
                {hasTrail ? `${idx + 1} / ${trail.length}` : "—"}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DetailBlock({ label, value }) {
  return (
    <div style={{ padding: 8, border: "1px solid #1e293b", borderRadius: 3,
                  background: "rgba(15,23,42,0.4)" }}>
      <div style={{ color: FN_DIM, fontFamily: "monospace", fontSize: 9,
                    letterSpacing: "0.24em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ color: FN_INK, fontSize: 12, marginTop: 3 }}>{value}</div>
    </div>
  );
}
