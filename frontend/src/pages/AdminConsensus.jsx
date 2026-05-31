/**
 * /admin/consensus — admin audit feed for the Consensus AI Validation Core.
 *
 * Pure addition. Reads /api/admin/consensus. Filterable by status.
 */
import React, { useEffect, useState, useCallback } from "react";
import axios from "axios";
import { ShieldCheck, AlertTriangle, RefreshCw } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmt = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString(); } catch { return iso; }
};

export default function AdminConsensus() {
  const [items, setItems] = useState([]);
  const [totals, setTotals] = useState({ authenticated: 0, rejected: 0 });
  const [status, setStatus] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const token = typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null;

  const load = useCallback(async () => {
    setBusy(true);
    setErr("");
    try {
      const q = status ? `?status=${encodeURIComponent(status)}` : "";
      const { data } = await axios.get(`${API}/admin/consensus${q}`, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      });
      setItems(data?.items || []);
      setTotals(data?.totals || { authenticated: 0, rejected: 0 });
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message || "Failed to load");
    } finally {
      setBusy(false);
    }
  }, [status, token]);

  useEffect(() => { load(); }, [load]);

  return (
    <div data-testid="admin-consensus-page"
         style={{ minHeight: "100vh", padding: "32px 28px", color: "#e2e8f0",
                  background: "radial-gradient(ellipse at top, #0f172a 0%, #080c14 80%)" }}>
      <div style={{ maxWidth: 1240, margin: "0 auto" }}>
        <div style={{ marginBottom: 18, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <div style={{ fontFamily: "monospace", fontSize: 10, letterSpacing: "0.3em",
                          color: "#10b981", textTransform: "uppercase" }}>
              // STRATEX // CONSENSUS AUDIT LEDGER
            </div>
            <h1 style={{ fontSize: 22, fontWeight: 700, letterSpacing: 0.5, marginTop: 4 }}>
              Consensus AI Validation Core — Audit Trail
            </h1>
          </div>
          <button onClick={load} disabled={busy} data-testid="admin-consensus-refresh"
                  style={{ background: "transparent", border: "1px solid #06b6d488",
                           color: "#06b6d4", padding: "6px 14px", borderRadius: 3,
                           fontFamily: "monospace", fontSize: 11, letterSpacing: "0.18em",
                           textTransform: "uppercase", cursor: "pointer" }}>
            <RefreshCw size={11} style={{ marginRight: 6, verticalAlign: "middle" }}/>
            {busy ? "Loading" : "Refresh"}
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 18 }}>
          <Stat label="Authenticated" value={totals.authenticated} color="#10b981"/>
          <Stat label="Rejected · Variance" value={totals.rejected} color="#f59e0b"/>
          <Stat label="Total Audits" value={totals.authenticated + totals.rejected} color="#06b6d4"/>
        </div>

        <div style={{ marginBottom: 12, display: "flex", gap: 6 }}>
          {["", "AUTHENTICATED", "REJECTED_VARIANCE_CRITICAL"].map((s) => (
            <button key={s || "all"} onClick={() => setStatus(s)}
                    data-testid={`admin-consensus-filter-${s || "all"}`}
                    style={{
                      background: status === s ? "rgba(6,182,212,0.18)" : "transparent",
                      border: `1px solid ${status === s ? "#06b6d4" : "#334155"}`,
                      color: status === s ? "#06b6d4" : "#94a3b8",
                      padding: "5px 12px", borderRadius: 3, fontFamily: "monospace",
                      fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase",
                      cursor: "pointer",
                    }}>
              {s || "All"}
            </button>
          ))}
        </div>

        {err && (
          <div style={{ color: "#ef4444", fontFamily: "monospace", fontSize: 12, marginBottom: 12 }}>
            ⚠ {err}
          </div>
        )}

        <div style={{ border: "1px solid #1e293b", borderRadius: 4, overflow: "hidden" }}
             data-testid="admin-consensus-table">
          <div style={{ display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr 2fr",
                        background: "#0f172a", padding: "10px 12px",
                        fontFamily: "monospace", fontSize: 10, letterSpacing: "0.18em",
                        color: "#64748b", textTransform: "uppercase" }}>
            <span>Job</span>
            <span>Status</span>
            <span>Score</span>
            <span>Timestamp</span>
            <span>Action</span>
          </div>
          {items.length === 0 && !busy && (
            <div style={{ padding: 24, textAlign: "center", color: "#475569", fontFamily: "monospace", fontSize: 12 }}>
              No audits yet for this filter.
            </div>
          )}
          {items.map((it) => {
            const ok = it.verification_status === "AUTHENTICATED";
            const demo = it.injected_for_demo === true;
            return (
              <div key={it.id} data-testid={`admin-consensus-row-${it.id}`} style={{
                display: "grid", gridTemplateColumns: "1.5fr 1fr 1fr 1fr 2fr",
                padding: "10px 12px", borderTop: "1px solid #1e293b",
                fontFamily: "monospace", fontSize: 11, alignItems: "center",
              }}>
                <span style={{ color: "#06b6d4", display: "flex", alignItems: "center", gap: 8 }}>
                  {it.job_id}
                  {demo && (
                    <span data-testid="admin-consensus-demo-tag" title="Verdict generated by Demo · Inject Variance — excluded from compliance reporting" style={{
                      padding: "1px 6px", borderRadius: 2,
                      border: "1px solid #ec489955", background: "rgba(236,72,153,0.10)",
                      color: "#f472b6", fontSize: 8, letterSpacing: "0.22em",
                      textTransform: "uppercase", fontWeight: 700,
                    }}>DEMO</span>
                  )}
                </span>
                <span style={{ color: ok ? "#10b981" : "#f59e0b", display: "flex", alignItems: "center", gap: 6 }}>
                  {ok ? <ShieldCheck size={12}/> : <AlertTriangle size={12}/>}
                  {it.verification_status}
                </span>
                <span style={{ color: "#e2e8f0" }}>{(it.consensus_score ?? 0).toFixed(1)}%</span>
                <span style={{ color: "#64748b" }}>{fmt(it.created_at)}</span>
                <span style={{ color: "#94a3b8", fontSize: 10 }}>{it.action || "—"}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, color }) {
  return (
    <div style={{ border: "1px solid #1e293b", padding: 16, borderRadius: 4,
                  background: "rgba(15,23,42,0.6)" }}>
      <div style={{ color: "#64748b", fontFamily: "monospace", fontSize: 10,
                    letterSpacing: "0.22em", textTransform: "uppercase" }}>{label}</div>
      <div style={{ color, fontSize: 28, fontWeight: 700, marginTop: 6 }}>{value}</div>
    </div>
  );
}
