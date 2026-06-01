/**
 * YellowTriangleWidget — Tactical perimeter-breach caution widget.
 *
 * Phase 1B of the v3.40 spec, restored in v3.42.0. Mounts in the dashboard
 * header of CEO Command Center, GM (= CEO portal in our arch), and the
 * Supplier Sales Hub. Polls /api/geofence/alerts every 12s; surfaces the
 * count of UNAUTHORIZED_SITE_BREACH events + blacklist size; click to expand
 * a compact drawer with the latest 6 alerts.
 *
 * Pure additive — no existing dashboard module moved or altered.
 */
import React, { useEffect, useState } from "react";
import { AlertTriangle, X, Radio } from "lucide-react";
import { api } from "@/lib/api";

const FN = {
  amber:  "#F59E0B",
  green:  "#10B981",
  text:   "#E2E8F0",
  muted:  "#64748B",
  bg:     "rgba(11,15,25,0.92)",
  border: "rgba(245,158,11,0.45)",
};

const fmtTime = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleTimeString("en-US", {
      hour: "2-digit", minute: "2-digit", second: "2-digit",
    });
  } catch { return iso; }
};

export default function YellowTriangleWidget({ portal = "ceo" }) {
  const [data, setData] = useState({ alerts: [], count: 0, blacklist: [] });
  const [open, setOpen] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const r = await api.get("/geofence/alerts?limit=6");
        if (alive) { setData(r.data || { alerts: [], count: 0, blacklist: [] }); setFailed(false); }
      } catch {
        if (alive) setFailed(true);
      }
    };
    tick();
    const id = setInterval(tick, 12_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const count = data.count || 0;
  const blacklistCount = (data.blacklist || []).length;
  const hot = count > 0 || blacklistCount > 0;

  if (failed) return null; // gracefully hide when endpoint unavailable

  return (
    <div className="yt-widget-root" data-testid={`yellow-triangle-${portal}`}>
      <button
        className={`yt-btn ${hot ? "hot" : ""}`}
        onClick={() => setOpen((v) => !v)}
        data-testid={`yellow-triangle-${portal}-btn`}
        aria-label="Perimeter breach alerts"
      >
        <AlertTriangle size={14} color={hot ? FN.amber : FN.muted}/>
        <span className="yt-label">PERIMETER</span>
        <span className={`yt-count ${hot ? "hot" : ""}`}>{count}</span>
        {blacklistCount > 0 && (
          <span className="yt-blacklist" title={`${blacklistCount} restricted contractor(s)`}>
            <Radio size={9}/> {blacklistCount}
          </span>
        )}
      </button>

      {open && (
        <div className="yt-drawer" data-testid={`yellow-triangle-${portal}-drawer`}>
          <div className="yt-drawer-head">
            <span className="yt-drawer-title">
              <AlertTriangle size={12} color={FN.amber}/>
              UNAUTHORIZED SITE BREACH · LIVE FEED
            </span>
            <button className="yt-close" onClick={() => setOpen(false)}>
              <X size={11}/>
            </button>
          </div>
          {data.alerts.length === 0 ? (
            <div className="yt-empty">
              <span style={{ color: FN.muted }}>// No active breaches — perimeter clean.</span>
            </div>
          ) : (
            <ol className="yt-list">
              {data.alerts.slice(0, 6).map((a) => (
                <li key={a.breach_id} className="yt-row" data-testid={`yt-row-${a.breach_id}`}>
                  <div className="yt-row-head">
                    <span className="yt-tag" style={{ color: FN.amber, borderColor: FN.amber }}>
                      STRIKE
                    </span>
                    <span className="yt-name">{a.matched_contact?.name || "—"}</span>
                    <span className="yt-role">{a.matched_contact?.role}</span>
                    <span className="yt-time">{fmtTime(a.timestamp)}</span>
                  </div>
                  <div className="yt-row-meta">
                    job <strong style={{ color: FN.text }}>{a.job_id}</strong>
                    <span className="yt-sep">·</span>
                    no invoice <strong style={{ color: FN.amber }}>UNAUTHORIZED</strong>
                  </div>
                </li>
              ))}
            </ol>
          )}
          {blacklistCount > 0 && (
            <div className="yt-blacklist-strip">
              <Radio size={10} color={FN.amber}/>
              <span style={{ color: FN.amber }}>
                {blacklistCount} contractor{blacklistCount === 1 ? "" : "s"} in RESTRICTED_PERIMETER_VIOLATION · deliverables frozen
              </span>
            </div>
          )}
        </div>
      )}

      <style>{`
        .yt-widget-root { position: relative; display: inline-block; }
        .yt-btn {
          display: inline-flex; align-items: center; gap: 6px;
          background: transparent; border: 1px solid ${FN.border};
          color: ${FN.text}; padding: 5px 10px; border-radius: 4px;
          font-family: 'JetBrains Mono', monospace; font-size: 10px;
          letter-spacing: 0.16em; text-transform: uppercase; cursor: pointer;
          transition: all 160ms ease;
        }
        .yt-btn.hot {
          border-color: ${FN.amber}; box-shadow: 0 0 12px ${FN.amber}55;
          animation: yt-pulse 2.2s ease-in-out infinite;
        }
        .yt-btn:hover { filter: brightness(1.18); }
        @keyframes yt-pulse {
          0%,100% { box-shadow: 0 0 10px ${FN.amber}33; }
          50%     { box-shadow: 0 0 18px ${FN.amber}80; }
        }
        .yt-label { color: ${FN.muted}; }
        .yt-count {
          color: ${FN.muted}; font-weight: 700;
          background: rgba(100,116,139,0.15); padding: 1px 6px; border-radius: 2px;
        }
        .yt-count.hot { color: ${FN.amber}; background: rgba(245,158,11,0.15); }
        .yt-blacklist {
          color: ${FN.amber}; font-weight: 700;
          display: inline-flex; align-items: center; gap: 3px;
          padding: 1px 5px; background: rgba(245,158,11,0.12); border-radius: 2px;
        }
        .yt-drawer {
          position: absolute; top: calc(100% + 6px); right: 0; z-index: 60;
          width: 360px; max-width: 92vw;
          background: ${FN.bg}; border: 1px solid ${FN.border}; border-radius: 5px;
          padding: 10px 11px; backdrop-filter: blur(14px);
          box-shadow: 0 12px 36px rgba(0,0,0,0.45);
        }
        .yt-drawer-head {
          display: flex; align-items: center; justify-content: space-between;
          padding-bottom: 8px; border-bottom: 1px dashed rgba(245,158,11,0.25);
          margin-bottom: 8px;
        }
        .yt-drawer-title {
          font-family: 'JetBrains Mono', monospace; font-size: 9px; font-weight: 700;
          color: ${FN.amber}; letter-spacing: 0.16em;
          display: inline-flex; align-items: center; gap: 6px;
        }
        .yt-close { background: transparent; border: none; color: ${FN.muted}; cursor: pointer; padding: 2px; }
        .yt-close:hover { color: ${FN.text}; }
        .yt-empty {
          padding: 14px 8px; text-align: center;
          font-family: 'JetBrains Mono', monospace; font-size: 10px;
        }
        .yt-list { list-style: none; padding: 0; margin: 0; }
        .yt-row {
          padding: 7px 4px; border-bottom: 1px dashed rgba(100,116,139,0.2);
        }
        .yt-row:last-child { border-bottom: 0; }
        .yt-row-head {
          display: flex; flex-wrap: wrap; align-items: center; gap: 6px;
        }
        .yt-tag {
          font-family: 'JetBrains Mono', monospace; font-size: 8px; font-weight: 700;
          letter-spacing: 0.16em; padding: 1px 5px; border: 1px solid; border-radius: 2px;
        }
        .yt-name {
          color: ${FN.text}; font-family: 'JetBrains Mono', monospace; font-size: 11px; font-weight: 700;
        }
        .yt-role {
          color: ${FN.muted}; font-family: 'JetBrains Mono', monospace; font-size: 9px;
          text-transform: uppercase; letter-spacing: 0.12em;
        }
        .yt-time {
          color: ${FN.muted}; font-family: 'JetBrains Mono', monospace; font-size: 9px;
          margin-left: auto;
        }
        .yt-row-meta {
          color: ${FN.muted}; font-family: 'JetBrains Mono', monospace; font-size: 9px;
          margin-top: 3px;
        }
        .yt-sep { margin: 0 5px; opacity: 0.6; }
        .yt-blacklist-strip {
          margin-top: 8px; padding-top: 7px; border-top: 1px dashed rgba(245,158,11,0.25);
          display: flex; align-items: center; gap: 5px;
          font-family: 'JetBrains Mono', monospace; font-size: 9px;
          letter-spacing: 0.1em; text-transform: uppercase;
        }
      `}</style>
    </div>
  );
}
