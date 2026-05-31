/**
 * PricingAuditTimeline — Future-Noire timeline view for the unified pricing
 * audit ledger (siding global + contractor roofing/gutter per-user).
 *
 * Append-only addition to the GM Command Center per the preservation rule:
 * does not relocate, drop, or alter any existing telemetry card, the KY
 * Doppler map, or the core return matrices. Mounts as a new <section> after
 * the live pricing slider.
 *
 * Wires to:
 *   GET  /api/contractor/materials-brain/siding-prices/history
 *   POST /api/contractor/materials-brain/siding-prices/revert/{id}
 *   GET  /api/contractor/materials-brain/contractor-prices/history
 *   POST /api/contractor/materials-brain/contractor-prices/revert/{id}
 *
 * Visual contract: pure Future-Noire (cyan/purple/green/magenta + JetBrains
 * Mono). Inherits the parent's color tokens by importing them as a prop so
 * the host page owns the palette.
 */
import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { History, RotateCcw, ShieldCheck, CheckCircle2, AlertCircle, ChevronDown, ChevronRight } from "lucide-react";

const fmtUSD = (n) =>
  n == null ? "—" : `$${Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 })}`;

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short", day: "2-digit",
      hour: "2-digit", minute: "2-digit",
    });
  } catch { return iso; }
};

const ACTION_STYLE = {
  put_override:         { color: "#06b6d4", label: "OVERRIDE" },
  put_materials:        { color: "#06b6d4", label: "SAVE" },
  pre_revert_snapshot:  { color: "#f59e0b", label: "PRE-REVERT" },
};

export default function PricingAuditTimeline({ FN }) {
  const [tab, setTab] = useState("siding"); // "siding" | "contractor"
  const [siding, setSiding] = useState({ history: [], loading: true, error: null });
  const [contractor, setContractor] = useState({ history: [], loading: true, error: null });
  const [expanded, setExpanded] = useState({}); // snapshot_id -> bool
  const [reverting, setReverting] = useState(null); // snapshot_id while in-flight
  const [toast, setToast] = useState(null);

  const loadSiding = async () => {
    setSiding((s) => ({ ...s, loading: true, error: null }));
    try {
      const r = await api.get("/contractor/materials-brain/siding-prices/history?limit=25");
      setSiding({ history: r.data?.history || [], loading: false, error: null });
    } catch (e) {
      setSiding({ history: [], loading: false, error: e?.response?.data?.detail || "Failed to load siding ledger" });
    }
  };

  const loadContractor = async () => {
    setContractor((s) => ({ ...s, loading: true, error: null }));
    try {
      const r = await api.get("/contractor/materials-brain/contractor-prices/history?limit=25");
      setContractor({ history: r.data?.history || [], loading: false, error: null });
    } catch (e) {
      setContractor({ history: [], loading: false, error: e?.response?.data?.detail || "Failed to load contractor ledger" });
    }
  };

  useEffect(() => { loadSiding(); loadContractor(); }, []);

  const fireToast = (msg, kind = "ok") => {
    setToast({ msg, kind });
    setTimeout(() => setToast(null), 3500);
  };

  const handleRevert = async (snapshotId, channel) => {
    if (!window.confirm(`Revert to snapshot ${snapshotId.slice(0, 8)}…? Current state will be auto-snapshotted first.`)) return;
    setReverting(snapshotId);
    try {
      const path = channel === "siding"
        ? `/contractor/materials-brain/siding-prices/revert/${snapshotId}`
        : `/contractor/materials-brain/contractor-prices/revert/${snapshotId}`;
      const r = await api.post(path);
      fireToast(`Reverted · pre-revert snapshot ${r.data?.pre_revert_snapshot_id?.slice(0, 8) || "—"}`, "ok");
      if (channel === "siding") loadSiding(); else loadContractor();
    } catch (e) {
      fireToast(e?.response?.data?.detail || "Revert failed", "err");
    } finally {
      setReverting(null);
    }
  };

  const active = tab === "siding" ? siding : contractor;
  const rows = active.history;

  return (
    <section
      className="ceo-card pat-shell"
      data-testid="ceo-pricing-audit-timeline"
      style={{ borderLeft: `4px solid ${FN.magenta}`, marginTop: 16, padding: 18 }}
    >
      <div className="pat-header">
        <div className="pat-title">
          <History size={16} color={FN.magenta}/>
          <span>Pricing Audit Ledger</span>
          <span className="pat-pill" style={{ color: FN.green, borderColor: FN.green }}>
            <ShieldCheck size={9}/> Fernet/AES-256 sealed at rest
          </span>
        </div>
        <div className="pat-tabs" role="tablist">
          <button
            role="tab"
            data-testid="pat-tab-siding"
            className={`pat-tab ${tab === "siding" ? "active" : ""}`}
            onClick={() => setTab("siding")}
            style={tab === "siding" ? { color: FN.cyan, borderColor: FN.cyan } : {}}
          >
            Siding Book · global
          </button>
          <button
            role="tab"
            data-testid="pat-tab-contractor"
            className={`pat-tab ${tab === "contractor" ? "active" : ""}`}
            onClick={() => setTab("contractor")}
            style={tab === "contractor" ? { color: FN.purple, borderColor: FN.purple } : {}}
          >
            Roofing / Gutter · per-contractor
          </button>
        </div>
      </div>

      <div className="pat-body" data-testid={`pat-body-${tab}`}>
        {active.loading && (
          <div className="pat-empty">
            <span className="pat-mono" style={{ color: FN.muted }}>Loading ledger…</span>
          </div>
        )}
        {!active.loading && active.error && (
          <div className="pat-empty">
            <AlertCircle size={14} color={FN.magenta}/>
            <span className="pat-mono" style={{ color: FN.magenta }}>{active.error}</span>
          </div>
        )}
        {!active.loading && !active.error && rows.length === 0 && (
          <div className="pat-empty">
            <span className="pat-mono" style={{ color: FN.muted }}>
              No history yet — every price save will appear here.
            </span>
          </div>
        )}
        {!active.loading && !active.error && rows.length > 0 && (
          <ol className="pat-timeline">
            {rows.map((row, idx) => {
              const id = row.snapshot_id;
              const isOpen = !!expanded[id];
              const style = ACTION_STYLE[row.trigger_action] || { color: FN.muted, label: row.trigger_action || "?" };
              const priceDict = tab === "siding" ? row.prices : row.encrypted_prices;
              const priceCount = priceDict ? Object.keys(priceDict).length : 0;
              return (
                <li key={id || idx} className="pat-row" data-testid={`pat-row-${idx}`}>
                  <div className="pat-bullet" style={{ background: style.color }}/>
                  <div className="pat-card">
                    <div className="pat-card-head">
                      <button
                        className="pat-disclose"
                        onClick={() => setExpanded((p) => ({ ...p, [id]: !p[id] }))}
                        data-testid={`pat-toggle-${idx}`}
                        aria-expanded={isOpen}
                      >
                        {isOpen ? <ChevronDown size={12}/> : <ChevronRight size={12}/>}
                      </button>
                      <span className="pat-tag" style={{ color: style.color, borderColor: style.color }}>
                        {style.label}
                      </span>
                      <span className="pat-mono pat-snap">{(id || "").slice(0, 8)}…</span>
                      {tab === "siding" && row.tune_version && (
                        <span className="pat-mono pat-tune" style={{ color: FN.cyan }}>
                          {row.tune_version}
                        </span>
                      )}
                      {tab === "contractor" && row.user_id && (
                        <span className="pat-mono pat-tune" style={{ color: FN.purple }}>
                          ctr {(row.user_id || "").slice(0, 8)}…
                        </span>
                      )}
                      <span className="pat-mono pat-time">{fmtTime(row.snapshotted_at)}</span>
                      <span className="pat-fill"/>
                      <span className="pat-mono pat-keys">{priceCount} fields</span>
                      {row.trigger_action !== "pre_revert_snapshot" && (
                        <button
                          className="pat-revert-btn"
                          onClick={() => handleRevert(id, tab)}
                          disabled={reverting === id}
                          data-testid={`pat-revert-${idx}`}
                          style={{ color: FN.amber, borderColor: FN.amber }}
                        >
                          <RotateCcw size={10}/> {reverting === id ? "REVERTING…" : "REVERT"}
                        </button>
                      )}
                    </div>
                    {isOpen && (
                      <div className="pat-card-body" data-testid={`pat-detail-${idx}`}>
                        {!priceDict ? (
                          <span className="pat-mono" style={{ color: FN.muted }}>
                            Snapshot blob present but decryption failed (key rotation?).
                          </span>
                        ) : (
                          <div className="pat-pricegrid">
                            {Object.entries(priceDict).slice(0, 30).map(([k, v]) => (
                              <div className="pat-priceitem" key={k}>
                                <span className="pat-mono pat-priceitem-k">{k}</span>
                                <span className="pat-mono pat-priceitem-v" style={{ color: FN.green }}>
                                  {typeof v === "number" ? fmtUSD(v) : String(v)}
                                </span>
                              </div>
                            ))}
                            {Object.keys(priceDict).length > 30 && (
                              <span className="pat-mono" style={{ color: FN.muted }}>
                                +{Object.keys(priceDict).length - 30} more fields…
                              </span>
                            )}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
        )}
      </div>

      {toast && (
        <div
          className="pat-toast"
          data-testid="pat-toast"
          style={{
            borderColor: toast.kind === "ok" ? FN.green : FN.magenta,
            color: toast.kind === "ok" ? FN.green : FN.magenta,
          }}
        >
          {toast.kind === "ok" ? <CheckCircle2 size={12}/> : <AlertCircle size={12}/>}
          <span className="pat-mono">{toast.msg}</span>
        </div>
      )}

      <style>{`
        .pat-shell { position: relative; }
        .pat-header {
          display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
          gap: 12px; margin-bottom: 14px;
        }
        .pat-title {
          display: flex; align-items: center; gap: 8px;
          font-family: 'JetBrains Mono', monospace; font-size: 12px;
          letter-spacing: 0.18em; text-transform: uppercase; color: ${FN.text}; font-weight: 700;
        }
        .pat-pill {
          display: inline-flex; align-items: center; gap: 4px;
          font-family: 'JetBrains Mono', monospace; font-size: 9px;
          padding: 3px 7px; border: 1px solid; border-radius: 999px;
          letter-spacing: 0.1em; text-transform: uppercase; font-weight: 700;
        }
        .pat-tabs { display: inline-flex; gap: 6px; }
        .pat-tab {
          background: transparent; border: 1px solid ${FN.divider};
          color: ${FN.muted}; cursor: pointer;
          font-family: 'JetBrains Mono', monospace; font-size: 10px;
          padding: 6px 12px; border-radius: 4px;
          letter-spacing: 0.14em; text-transform: uppercase; font-weight: 700;
          transition: color 120ms ease, border-color 120ms ease;
        }
        .pat-tab.active { background: ${FN.bgInput}; }
        .pat-tab:hover:not(.active) { color: ${FN.text}; border-color: ${FN.text}; }
        .pat-body { min-height: 80px; }
        .pat-empty {
          display: flex; align-items: center; gap: 8px;
          padding: 24px 8px; justify-content: center;
        }
        .pat-mono { font-family: 'JetBrains Mono', monospace; font-size: 11px; }
        .pat-timeline {
          list-style: none; padding: 0; margin: 0;
          position: relative;
        }
        .pat-timeline::before {
          content: ''; position: absolute; top: 14px; bottom: 14px; left: 6px;
          width: 1px; background: ${FN.divider};
        }
        .pat-row {
          display: flex; align-items: stretch; gap: 14px;
          padding: 6px 0; position: relative;
        }
        .pat-bullet {
          width: 13px; height: 13px; border-radius: 50%;
          margin-top: 14px; flex-shrink: 0; z-index: 1;
          box-shadow: 0 0 0 3px ${FN.bgCard}, 0 0 8px currentColor;
        }
        .pat-card {
          flex: 1; background: ${FN.bgInput}; border: 1px solid ${FN.divider};
          border-radius: 4px; padding: 10px 12px;
        }
        .pat-card-head {
          display: flex; flex-wrap: wrap; align-items: center; gap: 8px;
        }
        .pat-disclose {
          background: transparent; border: none; color: ${FN.muted}; cursor: pointer;
          padding: 0; display: inline-flex; align-items: center;
        }
        .pat-tag {
          font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 700;
          letter-spacing: 0.12em; text-transform: uppercase;
          padding: 2px 6px; border: 1px solid; border-radius: 3px;
        }
        .pat-snap { color: ${FN.text}; font-weight: 700; }
        .pat-tune { font-size: 10px; font-weight: 700; }
        .pat-time { color: ${FN.muted}; font-size: 10px; }
        .pat-fill { flex: 1; }
        .pat-keys { color: ${FN.muted}; }
        .pat-revert-btn {
          background: transparent; border: 1px solid;
          font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 700;
          letter-spacing: 0.14em; text-transform: uppercase;
          padding: 4px 9px; border-radius: 3px; cursor: pointer;
          display: inline-flex; align-items: center; gap: 4px;
          transition: filter 120ms ease;
        }
        .pat-revert-btn:hover { filter: brightness(1.3); }
        .pat-revert-btn:disabled { opacity: 0.5; cursor: progress; }
        .pat-card-body {
          margin-top: 10px; padding-top: 10px; border-top: 1px dashed ${FN.divider};
        }
        .pat-pricegrid {
          display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
          gap: 4px 14px;
        }
        .pat-priceitem {
          display: flex; align-items: center; justify-content: space-between;
          gap: 8px; padding: 2px 0;
        }
        .pat-priceitem-k { color: ${FN.text}; font-size: 10px; }
        .pat-priceitem-v { font-weight: 700; font-size: 11px; }
        .pat-toast {
          position: absolute; right: 16px; bottom: 12px;
          display: inline-flex; align-items: center; gap: 6px;
          background: ${FN.bgCard}; border: 1px solid; border-radius: 4px;
          padding: 6px 10px;
        }
        @media (max-width: 768px) {
          .pat-header { flex-direction: column; align-items: flex-start; }
          .pat-tabs { width: 100%; }
          .pat-tab { flex: 1; }
        }
      `}</style>
    </section>
  );
}
