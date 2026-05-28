import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AlertTriangle, Check, X as XIcon, RotateCw } from "lucide-react";

/**
 * /admin/overseer — Telemetry Anomaly Halt Review Queue
 *
 * Surfaces structured halt payloads dispatched by the BEES Electric Teal
 * watchdog (see RoofModel3D.jsx anomalyWatchdog). Admin-only.
 *
 * Visual contract: open items render with Neon Orange severity bars; reviewed
 * items shift to Electric Teal; dismissed items dim to Metallic Nickel.
 */
const SEVERITY_COLORS = {
  advisory: "#94A3B8",
  warning:  "#FF5400",
  critical: "#FF5400",
};
const STATUS_COLORS = {
  open:      "#FF5400",
  reviewed:  "#00F5D4",
  dismissed: "#3A4350",
};

export default function OverseerQueue() {
  const [items, setItems] = useState([]);
  const [openCount, setOpenCount] = useState(0);
  const [filter, setFilter] = useState("open");
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const r = await api.get(`/admin/overseer-queue?status=${filter}`);
      setItems(r.data?.items || []);
      setOpenCount(r.data?.open_count || 0);
    } catch (err) {
      if (err?.response?.status === 403) setForbidden(true);
    } finally { setLoading(false); }
  }
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [filter]);

  async function reviewItem(id, newStatus, note = "") {
    try {
      await api.put(`/admin/overseer-queue/${id}`, { review_status: newStatus, review_note: note });
      await load();
    } catch (e) { /* silent */ }
  }

  if (forbidden) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center p-8" data-testid="overseer-forbidden">
        <div className="border border-[#FF5400] bg-[#FF5400]/10 p-8 max-w-md">
          <div className="font-mono text-[10px] tracking-widest uppercase text-[#FF5400] mb-2">// 403 — ACCESS DENIED</div>
          <h1 className="font-display text-2xl uppercase tracking-widest mb-2">Admin Privilege Required</h1>
          <p className="font-body text-sm text-muted-hud">The Overseer Queue is restricted to <code className="text-teal">role=admin</code> accounts.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="overseer-root">
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="led led-teal" />
          <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase">// STRATEX VISION • OVERSEER • TELEMETRY HALT REVIEW</div>
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">
          Anomaly Halt Queue
          {openCount > 0 && (
            <span
              className="ml-3 inline-flex items-center gap-1 font-mono text-[11px] tracking-widest px-2 py-1 border"
              style={{ color: "#FF5400", borderColor: "#FF5400", boxShadow: "0 0 12px rgba(255,84,0,0.5)" }}
              data-testid="overseer-open-badge"
            >
              <AlertTriangle size={11}/> {openCount} OPEN
            </span>
          )}
        </h1>
        <p className="font-body text-sm text-muted-hud mb-6 max-w-3xl">
          Structured halt reports from the BEES Electric Teal diagnostic layer. Each event includes the causal log,
          telemetry snapshot at halt, and the user/session that triggered it.
        </p>

        {/* Filter chips */}
        <div className="flex items-center gap-3 mb-3">
          <a
            href="/admin/flight-audit"
            data-testid="overseer-link-flight-audit"
            className="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 hover:bg-[#00F5D4]/10"
            style={{ borderColor: "rgba(0,245,212,0.35)", color: "#00F5D4" }}
          >
            Flight Authorization Audit →
          </a>
        </div>

        <div className="flex flex-wrap gap-2 mb-5">
          {["open", "reviewed", "dismissed", "all"].map((s) => {
            const active = filter === s;
            const color = s === "all" ? "#00F5D4" : STATUS_COLORS[s];
            return (
              <button
                key={s}
                data-testid={`overseer-filter-${s}`}
                onClick={() => setFilter(s)}
                aria-pressed={active}
                className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                style={{
                  background: active ? `${color}22` : "rgba(11,15,25,0.85)",
                  color: active ? color : "#94A3B8",
                  borderColor: active ? color : "rgba(0,240,255,0.25)",
                  boxShadow: active ? `0 0 10px ${color}66` : "none",
                }}
              >
                {s}
              </button>
            );
          })}
          <button
            data-testid="overseer-refresh"
            onClick={load}
            className="ml-auto px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border border-[#00F5D4]/40 text-teal hover:bg-[#00F5D4]/10"
          >
            <RotateCw size={11} className="inline mr-1.5 -mt-0.5"/> Refresh
          </button>
        </div>

        {loading && <div className="font-mono text-teal">// LOADING…</div>}
        {!loading && items.length === 0 && (
          <div className="border border-[#00F0FF]/20 p-12 text-center" data-testid="overseer-empty">
            <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud mb-2">// CLEAN PIPELINE</div>
            <p className="font-body text-sm text-silver">No telemetry halts in this filter. The Electric Teal layer is operating nominally.</p>
          </div>
        )}

        <ul className="space-y-3">
          {items.map((it) => {
            const sev = SEVERITY_COLORS[it.severity] || "#94A3B8";
            const stat = STATUS_COLORS[it.review_status] || "#94A3B8";
            const isExpanded = expanded === it.id;
            return (
              <li
                key={it.id}
                data-testid={`overseer-item-${it.id}`}
                className="border-l-4 border-[#00F0FF]/30 bg-[#0B0F19] border-y border-r border-[#00F0FF]/20"
                style={{ borderLeftColor: sev, boxShadow: it.review_status === "open" ? `0 0 12px ${sev}22` : "none" }}
              >
                <button
                  onClick={() => setExpanded(isExpanded ? null : it.id)}
                  className="w-full text-left px-4 py-3 flex items-center gap-4 flex-wrap"
                >
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5 border"
                    style={{ color: sev, borderColor: sev }}
                  >{it.severity}</span>
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5"
                    style={{ background: `${stat}22`, color: stat, border: `1px solid ${stat}` }}
                  >{it.review_status}</span>
                  <span className="font-mono text-[10px] text-teal">{it.reason_code}</span>
                  <span className="flex-1 font-body text-[12px] text-silver truncate">{it.reason_label}</span>
                  <span className="font-mono text-[9.5px] text-muted-hud">{new Date(it.server_timestamp).toLocaleString()}</span>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t border-[#00F0FF]/15 space-y-3">
                    <div className="grid md:grid-cols-2 gap-4 text-[11px] font-mono">
                      <div>
                        <div className="text-muted-hud mb-1">// REPORTED BY</div>
                        <div className="text-silver">{it.reported_by_email} · <span className="text-teal">{it.reported_by_role}</span></div>
                      </div>
                      <div>
                        <div className="text-muted-hud mb-1">// LAYER</div>
                        <div className="text-silver">{it.layer}</div>
                      </div>
                      {it.fps_observed != null && (
                        <div>
                          <div className="text-muted-hud mb-1">// FPS OBSERVED</div>
                          <div className="text-plasma">{it.fps_observed} fps {it.fps_threshold ? `(threshold ${it.fps_threshold})` : ""}</div>
                        </div>
                      )}
                      {it.project_id && (
                        <div>
                          <div className="text-muted-hud mb-1">// PROJECT</div>
                          <div className="text-silver">{it.project_id}</div>
                        </div>
                      )}
                    </div>

                    <div>
                      <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-1">// TELEMETRY SNAPSHOT</div>
                      <pre className="text-[10.5px] text-silver bg-black/40 border border-[#00F0FF]/15 p-2 overflow-x-auto">
{JSON.stringify(it.telemetry_snapshot, null, 2)}
                      </pre>
                    </div>

                    {it.causal_logs?.length > 0 && (
                      <div>
                        <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-1">// CAUSAL LOG ({it.causal_logs.length})</div>
                        <ul className="text-[10.5px] text-muted-hud font-mono space-y-0.5">
                          {it.causal_logs.map((l, i) => <li key={i}>• {l}</li>)}
                        </ul>
                      </div>
                    )}

                    {it.review_status === "open" && (
                      <div className="flex gap-2 pt-2 border-t border-[#00F0FF]/15">
                        <button
                          data-testid={`overseer-review-${it.id}`}
                          onClick={() => reviewItem(it.id, "reviewed")}
                          className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border border-[#00F5D4] text-teal hover:bg-[#00F5D4]/10"
                        >
                          <Check size={11} className="inline mr-1.5 -mt-0.5"/> Mark Reviewed
                        </button>
                        <button
                          data-testid={`overseer-dismiss-${it.id}`}
                          onClick={() => reviewItem(it.id, "dismissed")}
                          className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border border-muted-hud text-muted-hud hover:bg-muted-hud/10"
                        >
                          <XIcon size={11} className="inline mr-1.5 -mt-0.5"/> Dismiss
                        </button>
                      </div>
                    )}

                    {it.reviewed_at && (
                      <div className="font-mono text-[10px] text-muted-hud">
                        Reviewed {new Date(it.reviewed_at).toLocaleString()} by <span className="text-teal">{it.reviewed_by}</span>
                        {it.review_note && <> · "{it.review_note}"</>}
                      </div>
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
