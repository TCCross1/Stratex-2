/**
 * BlacklistMatrix — v4.0-PROD System Blacklist Matrix.
 *
 * Renders restricted contractor ledger (RESTRICTED_PERIMETER_VIOLATION)
 * + the latest 25 UNAUTHORIZED_SITE_BREACH alerts in one cyber-tactical
 * grid. Source: GET /api/geofence/alerts (already gated to CEO/Admin/
 * Contractor). Auto-refreshes every 12s.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, AlertTriangle, Radio, Lock, Shield, Activity } from "lucide-react";

const C = { cyan: "#00F0FF", amber: "#FF9900", green: "#00FF66",
            magenta: "#FF3366",
            text: "#E2E8F0", muted: "#64748B", ink: "#06080B" };

const fmtTime = (iso) => {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleString("en-US", { dateStyle: "short", timeStyle: "medium" }); }
  catch { return iso; }
};

export default function BlacklistMatrix() {
  const nav = useNavigate();
  const [data, setData] = useState({ alerts: [], blacklist: [], count: 0 });
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const { data } = await api.get("/geofence/alerts?limit=25");
        if (!alive) return;
        setData(data || { alerts: [], blacklist: [], count: 0 });
        setErr("");
      } catch (e) {
        if (alive) setErr(e?.response?.data?.detail || e.message || "feed unavailable");
      } finally { if (alive) setLoading(false); }
    };
    tick();
    const id = setInterval(tick, 12_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  return (
    <div data-testid="blacklist-matrix-root"
         style={{ minHeight: "100vh", background: C.ink, color: C.text,
                  padding: "32px 24px 140px" }}>
      <div style={{ maxWidth: 1500, margin: "0 auto" }}>
        <button onClick={() => nav(-1)} data-testid="bm-back"
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            background: "transparent", border: `1px solid ${C.cyan}55`,
            color: C.cyan, padding: "5px 11px", borderRadius: 5,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
            letterSpacing: "0.2em", textTransform: "uppercase", cursor: "pointer",
          }}>
          <ArrowLeft size={12}/> Return
        </button>

        <header style={{ marginTop: 18, marginBottom: 22 }}>
          <div style={{ color: C.amber, fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, letterSpacing: "0.32em", textTransform: "uppercase" }}>
            // STRATEX VISION · SYSTEM BLACKLIST MATRIX · v4.0-PROD
          </div>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif",
                       fontSize: 36, lineHeight: 1.05, letterSpacing: "0.08em",
                       textTransform: "uppercase", margin: "6px 0 4px" }}>
            Restricted Contractor Ledger
          </h1>
          <p style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, letterSpacing: "0.12em" }}>
            <Shield size={11} style={{ display: "inline", verticalAlign: -1, marginRight: 4 }}/>
            Live feed of RESTRICTED_PERIMETER_VIOLATION accounts + unauthorized site breach strikes (auto-refresh 12s).
          </p>
        </header>

        <div style={{
          display: "grid", gap: 14,
          gridTemplateColumns: "minmax(0,1fr) minmax(0,1.4fr)",
        }}>
          {/* BLACKLIST */}
          <section data-testid="bm-blacklist"
            style={{
              background: "rgba(11,16,28,0.55)", backdropFilter: "blur(22px) saturate(150%)",
              border: `1px solid ${C.magenta}55`, borderRadius: 12, padding: "16px 18px",
              boxShadow: `0 28px 60px -30px ${C.magenta}88`,
            }}>
            <header className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Lock size={14} color={C.magenta}/>
                <h2 style={{ color: C.magenta, fontFamily: "'JetBrains Mono', monospace",
                             fontSize: 11, letterSpacing: "0.24em", margin: 0,
                             textTransform: "uppercase" }}>
                  RESTRICTED · Deliverables Frozen
                </h2>
              </div>
              <span data-testid="bm-blacklist-count"
                    style={{ color: C.magenta, fontFamily: "'JetBrains Mono', monospace",
                             fontSize: 10, letterSpacing: "0.16em" }}>
                {data.blacklist?.length || 0} ACCOUNTS
              </span>
            </header>
            {(data.blacklist || []).length === 0 ? (
              <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: "16px 0", textAlign: "center" }}>
                // No restricted contractors — perimeter clean.
              </div>
            ) : (
              <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {data.blacklist.map((b, i) => (
                  <li key={b.contractor_user_id || i}
                      data-testid={`bm-blacklist-row-${i}`}
                      style={{
                        padding: "10px 0",
                        borderBottom: "1px dashed rgba(255,51,102,0.18)",
                      }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ color: C.text, fontFamily: "'JetBrains Mono', monospace",
                                     fontSize: 11, fontWeight: 700 }}>
                        {b.contractor_user_id?.slice(0, 12) || "—"}
                      </span>
                      <span style={{ color: C.magenta, fontFamily: "'JetBrains Mono', monospace",
                                     fontSize: 9, letterSpacing: "0.18em", textTransform: "uppercase" }}>
                        Strike × {b.strikes ?? 0}
                      </span>
                    </div>
                    <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                                  fontSize: 9, marginTop: 3 }}>
                      Last breach: {b.last_breach_id || "—"} · Updated {fmtTime(b.last_updated)}
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {/* BREACH STRIKES */}
          <section data-testid="bm-breaches"
            style={{
              background: "rgba(11,16,28,0.55)", backdropFilter: "blur(22px) saturate(150%)",
              border: `1px solid ${C.amber}55`, borderRadius: 12, padding: "16px 18px",
              boxShadow: `0 28px 60px -30px ${C.amber}88`,
            }}>
            <header className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <AlertTriangle size={14} color={C.amber}/>
                <h2 style={{ color: C.amber, fontFamily: "'JetBrains Mono', monospace",
                             fontSize: 11, letterSpacing: "0.24em", margin: 0,
                             textTransform: "uppercase" }}>
                  Unauthorized Site Breach · Live Feed
                </h2>
              </div>
              <span data-testid="bm-breach-count"
                    style={{ color: C.amber, fontFamily: "'JetBrains Mono', monospace",
                             fontSize: 10, letterSpacing: "0.16em" }}>
                {data.count || 0} STRIKES
              </span>
            </header>
            {loading ? (
              <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: "16px 0", textAlign: "center" }}>
                <Activity size={11} style={{ verticalAlign: -1 }}/> Pinging telemetry…
              </div>
            ) : err ? (
              <div style={{ color: C.magenta, fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: "16px 0", textAlign: "center" }}>
                Feed error: {String(err)}
              </div>
            ) : (data.alerts || []).length === 0 ? (
              <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                            fontSize: 10, padding: "16px 0", textAlign: "center" }}>
                // Perimeter clean — no recorded breaches.
              </div>
            ) : (
              <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {data.alerts.map((a) => (
                  <li key={a.breach_id}
                      data-testid={`bm-row-${a.breach_id}`}
                      style={{
                        padding: "10px 0",
                        borderBottom: "1px dashed rgba(255,153,0,0.18)",
                      }}>
                    <div style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 4 }}>
                      <span style={{ color: C.text, fontFamily: "'JetBrains Mono', monospace",
                                     fontSize: 11, fontWeight: 700 }}>
                        {a.matched_contact?.name || "—"}
                        <span style={{ color: C.muted, marginLeft: 6, fontSize: 9, letterSpacing: "0.16em",
                                       textTransform: "uppercase" }}>
                          · {a.matched_contact?.role || ""}
                        </span>
                      </span>
                      <span style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace", fontSize: 9 }}>
                        {fmtTime(a.timestamp)}
                      </span>
                    </div>
                    <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                                  fontSize: 9, marginTop: 3 }}>
                      Job <strong style={{ color: C.cyan }}>{a.job_id}</strong>
                      <span style={{ margin: "0 6px", opacity: 0.6 }}>·</span>
                      Invoice <strong style={{ color: a.invoice_present ? C.green : C.amber }}>
                        {a.invoice_present ? "CLEARED" : "UNAUTHORIZED"}
                      </strong>
                      <span style={{ margin: "0 6px", opacity: 0.6 }}>·</span>
                      Distance <strong style={{ color: C.text }}>{a.distance_ft || "—"} ft</strong>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>
        </div>
      </div>
    </div>
  );
}
