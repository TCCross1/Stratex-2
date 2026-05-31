/**
 * ConsensusValidationCore — LIVE 4-agent verdict tile.
 *
 * Pure addition (global preservation lock). Lives next to the existing static
 * `ConsensusValidationCard` inside `/ceo/command`. Pulls real-time verdicts
 * from `/api/ceo/consensus/recent` and lets the CEO re-run the panel on
 * demand against the demo job.
 */
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { ShieldCheck, RefreshCw, AlertTriangle, CheckCircle2, Zap, XCircle } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const FN_GREEN = "#10b981";
const FN_AMBER = "#f59e0b";
const FN_RED = "#ef4444";
const FN_TEAL = "#06b6d4";

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch (_) { return iso; }
};

export default function ConsensusValidationCore({ token }) {
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [reverify, setReverify] = useState(false);
  const [injecting, setInjecting] = useState(false);
  const [flash, setFlash] = useState(false);
  const [err, setErr] = useState("");

  const headers = token ? { Authorization: `Bearer ${token}` } : {};

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const { data } = await axios.get(`${API}/ceo/consensus/recent?limit=8`, { headers });
      setItems(data?.items || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Failed to load");
    } finally {
      setBusy(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const rerunDemo = async () => {
    setReverify(true);
    try {
      await axios.post(`${API}/ceo/consensus/verify-job/crown-demo`, {}, { headers });
      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Re-verify failed");
    } finally {
      setReverify(false);
    }
  };

  const injectVariance = async () => {
    setInjecting(true);
    setErr("");
    try {
      await axios.post(`${API}/ceo/consensus/inject-variance`,
        { job_id: "crown-demo", surface_area_sqft: 3420.50,
          pitch_angles_degrees: [22.5, 22.5, 22.4, 22.6],
          moisture_retention_zones_sqft: 148.20,
          valley_linear_footage: 86, calculated_bom_cost: 8742.18 },
        { headers });
      setFlash(true);
      setTimeout(() => setFlash(false), 1800);
      await load();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Variance injection failed");
    } finally {
      setInjecting(false);
    }
  };

  const latest = items[0];
  const authenticated = latest?.verification_status === "AUTHENTICATED";
  const rejected = latest?.verification_status === "REJECTED_VARIANCE_CRITICAL";

  // Compute which agents diverged from base for color-coding
  const baseRec = latest?.audit_records?.[0];
  const agentDivergence = (r) => {
    if (!baseRec || !r) return false;
    return r.calculated_area !== baseRec.calculated_area
        || r.primary_angle_mean !== baseRec.primary_angle_mean
        || r.moisture_footprint !== baseRec.moisture_footprint
        || r.bom_cost_evaluation !== baseRec.bom_cost_evaluation;
  };

  return (
    <div className={`ceo-card ${flash ? "stx-variance-flash" : ""}`} data-testid="ceo-consensus-live-tile"
         style={{
           borderLeft: `4px solid ${authenticated ? FN_GREEN : rejected ? FN_RED : FN_AMBER}`,
           padding: 14,
           boxShadow: rejected ? `0 0 28px ${FN_RED}55, inset 0 0 0 1px ${FN_RED}33` : "none",
           transition: "box-shadow 400ms ease",
         }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {rejected ? <XCircle size={14} color={FN_RED}/> : <ShieldCheck size={14} color={FN_GREEN}/>}
          <span className="ceo-mono" style={{
            fontSize: 11, letterSpacing: "0.18em", textTransform: "uppercase",
            color: "#94a3b8",
          }}>
            // LIVE · CONSENSUS AI · 4-AGENT MATRIX
            {rejected && <span style={{ color: FN_RED, marginLeft: 8 }}>· VARIANCE CAUGHT</span>}
          </span>
        </div>
        <span data-testid="ceo-consensus-live-state" className="ceo-pill" style={{
          background: authenticated ? "rgba(16,185,129,0.12)"
                                    : rejected ? "rgba(239,68,68,0.16)"
                                               : "rgba(245,158,11,0.12)",
          border: `1px solid ${authenticated ? FN_GREEN : rejected ? FN_RED : FN_AMBER}88`,
          color: authenticated ? FN_GREEN : rejected ? FN_RED : FN_AMBER,
          padding: "3px 10px", borderRadius: 4, fontSize: 10,
          letterSpacing: "0.2em", textTransform: "uppercase", fontFamily: "monospace",
          animation: rejected ? "stx-rej-pulse 1.4s ease-in-out infinite" : "none",
        }}>
          {authenticated ? "AUTHENTICATED"
                         : rejected ? "REJECTED · RE-SCAN"
                                    : (latest?.verification_status || "AWAITING SCAN")}
        </span>
      </div>

      {err && (
        <div style={{ color: FN_RED, fontSize: 11, fontFamily: "monospace", marginBottom: 8 }}>
          ⚠ {err}
        </div>
      )}

      {latest && (
        <div style={{
          background: "rgba(6,182,212,0.04)",
          border: "1px solid rgba(6,182,212,0.18)",
          borderRadius: 3, padding: 10, marginBottom: 10,
          fontFamily: "monospace", fontSize: 11, color: "#cbd5e1",
        }} data-testid="ceo-consensus-live-latest">
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span style={{ color: FN_TEAL }}>JOB · {latest.job_id}</span>
            <span style={{ color: "#64748b" }}>{fmtTime(latest.created_at)}</span>
          </div>
          <div style={{ marginTop: 6, color: "#94a3b8" }}>
            CONSENSUS SCORE <span style={{ color: authenticated ? FN_GREEN : FN_AMBER }}>{(latest.consensus_score ?? 0).toFixed(1)}%</span>
            {" · "}
            AREA <span style={{ color: "#e2e8f0" }}>{latest.committed_payload?.calculated_area ?? "—"} ft²</span>
            {" · "}
            PITCH <span style={{ color: "#e2e8f0" }}>{latest.committed_payload?.primary_angle_mean ?? "—"}°</span>
          </div>
          <div style={{ marginTop: 4, color: "#64748b", fontSize: 10 }}>
            BOM ${latest.committed_payload?.bom_cost_evaluation ?? "—"} · MOISTURE {latest.committed_payload?.moisture_footprint ?? "—"} ft²
          </div>
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6, marginBottom: 10 }}
           data-testid="ceo-consensus-live-grid">
        {(latest?.audit_records || []).map((r, i) => {
          const diverged = agentDivergence(r);
          const c = diverged ? FN_RED : FN_GREEN;
          const Icon = diverged ? XCircle : CheckCircle2;
          return (
            <div key={i} style={{
              border: `1px solid ${c}55`,
              background: diverged ? "rgba(239,68,68,0.08)" : "rgba(16,185,129,0.04)",
              padding: 6, borderRadius: 3, fontFamily: "monospace",
              display: "flex", flexDirection: "column", gap: 3,
              transition: "all 400ms ease",
            }}>
              <Icon size={11} color={c}/>
              <span style={{ fontSize: 9, color: "#94a3b8", letterSpacing: "0.08em" }}>
                {r.agent.replace("AI_VALIDATOR_", "V").replace(/_/g, " ")}
              </span>
              <span style={{ fontSize: 9, color: c, letterSpacing: "0.1em" }}>
                {diverged ? "VARIANCE" : r.status}
              </span>
            </div>
          );
        })}
        {!latest && Array.from({ length: 4 }).map((_, i) => (
          <div key={i} style={{
            border: "1px dashed #334155", padding: 6, borderRadius: 3,
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#475569", fontFamily: "monospace", fontSize: 9,
          }}>
            <AlertTriangle size={10}/> NO DATA
          </div>
        ))}
      </div>

      {rejected && latest?.error_logs?.length > 0 && (
        <div data-testid="ceo-consensus-variance-logs" style={{
          marginBottom: 10, padding: 8, borderRadius: 3,
          border: `1px solid ${FN_RED}55`, background: `${FN_RED}10`,
          fontFamily: "monospace", fontSize: 9, color: "#fca5a5",
          lineHeight: 1.55, letterSpacing: "0.02em",
        }}>
          <div style={{ color: FN_RED, letterSpacing: "0.2em", fontSize: 9,
                        textTransform: "uppercase", marginBottom: 4 }}>
            ⚠ VARIANCE LOG · DRONE HOLD · RE-SCAN LOOP ENGAGED
          </div>
          {latest.error_logs.slice(0, 3).map((line, i) => (
            <div key={i} style={{ marginTop: 2 }}>· {line}</div>
          ))}
        </div>
      )}

      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={rerunDemo} disabled={reverify || busy || injecting}
                data-testid="ceo-consensus-rerun"
                style={{
                  flex: 1, background: rejected ? `${FN_GREEN}18` : "transparent",
                  border: `1px solid ${rejected ? FN_GREEN : FN_TEAL}88`,
                  color: rejected ? FN_GREEN : FN_TEAL,
                  padding: "6px 10px", borderRadius: 3, fontFamily: "monospace",
                  fontSize: 10, letterSpacing: "0.18em",
                  cursor: reverify ? "wait" : "pointer", textTransform: "uppercase",
                  fontWeight: rejected ? 800 : 500,
                  animation: rejected ? "stx-rej-pulse 1.4s ease-in-out infinite" : "none",
                }}>
          <RefreshCw size={10} style={{ marginRight: 6, verticalAlign: "middle" }}/>
          {reverify ? "VERIFYING…" : (rejected ? "RESOLVE · RE-SCAN COMPLETE" : "RE-RUN CONSENSUS · crown-demo")}
        </button>
        <button onClick={injectVariance} disabled={injecting || reverify || busy}
                data-testid="ceo-consensus-inject-variance"
                title="Demo only — fabricates a REJECTED verdict so you can showcase the safety net"
                style={{
                  background: "transparent", border: `1px solid ${FN_AMBER}77`,
                  color: FN_AMBER, padding: "6px 10px", borderRadius: 3,
                  fontFamily: "monospace", fontSize: 10, letterSpacing: "0.18em",
                  cursor: injecting ? "wait" : "pointer", textTransform: "uppercase",
                }}>
          <Zap size={10} style={{ marginRight: 6, verticalAlign: "middle" }}/>
          {injecting ? "INJECTING…" : "INJECT VARIANCE"}
        </button>
        <button onClick={load} disabled={busy}
                data-testid="ceo-consensus-refresh"
                style={{
                  background: "transparent", border: "1px solid #334155",
                  color: "#94a3b8", padding: "6px 10px", borderRadius: 3,
                  fontSize: 10, fontFamily: "monospace", cursor: "pointer",
                }}>
          {busy ? "…" : "↻"}
        </button>
      </div>

      {items.length > 1 && (
        <div style={{ marginTop: 10, fontFamily: "monospace", fontSize: 9, color: "#475569" }}>
          {items.length - 1} earlier verdict(s) · open /admin/consensus for the full audit feed
        </div>
      )}

      <style>{`
        @keyframes stx-rej-pulse {
          0%, 100% { box-shadow: 0 0 0 0 ${FN_RED}66; opacity: 1; }
          50% { box-shadow: 0 0 12px 4px ${FN_RED}55; opacity: 0.85; }
        }
        @keyframes stx-flash {
          0% { background-color: ${FN_RED}33; }
          100% { background-color: transparent; }
        }
        .stx-variance-flash { animation: stx-flash 1.6s ease-out forwards; }
      `}</style>
    </div>
  );
}
