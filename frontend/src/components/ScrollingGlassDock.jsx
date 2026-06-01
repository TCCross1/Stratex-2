/**
 * ScrollingGlassDock — v4.0-PROD luxury cyber-tactical app launcher.
 *
 * Frosted-glass horizontally scrolling dock anchored at the lower margin of
 * the viewport. Hosts the three executive launcher apps requested in the
 * v4.0 disruption blueprint:
 *
 *   • Yellow-Triangle Caution App   → live geofence/node breach vectors
 *   • MDU Fleet Management Portal   → Mobile Drone Unit capital ledger & ops
 *   • System Blacklist Matrix       → RESTRICTED_PERIMETER_VIOLATION ledger
 *
 * Strict aesthetic compliance (brand palette):
 *   – Cyan       #00F0FF
 *   – Amber      #FF9900
 *   – Matrix Grn #00FF66
 *
 * Implementation notes:
 *   – position: fixed; bottom: 18px; horizontally centered, max-width 92vw
 *   – backdrop-filter: blur(22px) saturate(150%)
 *   – overflow-x: auto with custom thin scrollbar so the dock can grow
 *   – polls /api/geofence/alerts every 12 s to surface live badge counts
 *   – clicking a tile uses react-router useNavigate (no full reload)
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { AlertTriangle, Truck, Radio } from "lucide-react";

const C = {
  cyan:   "#00F0FF",
  amber:  "#FF9900",
  green:  "#00FF66",
  ink:    "rgba(6, 10, 18, 0.55)",
  border: "rgba(0, 240, 255, 0.22)",
  text:   "#E2E8F0",
  muted:  "#64748B",
};

const DEFAULT_APPS = (counts) => [
  {
    key:      "yellow-triangle",
    label:    "Yellow Triangle",
    sub:      "Perimeter Breach Vectors",
    Icon:     AlertTriangle,
    color:    C.amber,
    route:    "/ceo/blacklist",
    badge:    counts.breaches,
  },
  {
    key:      "mdu-fleet",
    label:    "MDU Fleet Portal",
    sub:      "Mobile Drone Unit · Capital Ledger",
    Icon:     Truck,
    color:    C.cyan,
    route:    "/ceo/fleet",
    badge:    0,
  },
  {
    key:      "blacklist-matrix",
    label:    "Blacklist Matrix",
    sub:      "Restricted Contractor Ledger",
    Icon:     Radio,
    color:    C.green,
    route:    "/ceo/blacklist",
    badge:    counts.blacklist,
  },
];

export default function ScrollingGlassDock({
  portal = "ceo",
  routePrefix = "/ceo",  // pass "/admin" for GM/branch portal to relocalize routes
}) {
  const nav = useNavigate();
  const [counts, setCounts] = useState({ breaches: 0, blacklist: 0 });

  useEffect(() => {
    let alive = true;
    const tick = async () => {
      try {
        const { data } = await api.get("/geofence/alerts?limit=6");
        if (!alive) return;
        setCounts({
          breaches:  data?.count ?? 0,
          blacklist: (data?.blacklist || []).length,
        });
      } catch (_) { /* graceful — keep zeros */ }
    };
    tick();
    const id = setInterval(tick, 12_000);
    return () => { alive = false; clearInterval(id); };
  }, []);

  const apps = DEFAULT_APPS(counts).map(a => ({
    ...a,
    route: a.route.replace(/^\/ceo/, routePrefix),
  }));

  return (
    <div className="sgd-root" data-testid={`scrolling-glass-dock-${portal}`}>
      <div className="sgd-shell">
        <div className="sgd-rail">
          {apps.map(({ key, label, sub, Icon, color, route, badge }) => (
            <button
              key={key}
              data-testid={`sgd-tile-${key}`}
              onClick={() => nav(route)}
              className="sgd-tile"
              style={{ borderColor: `${color}55` }}
            >
              <div className="sgd-icon-ring" style={{ borderColor: color, boxShadow: `0 0 14px ${color}55` }}>
                <Icon size={18} color={color}/>
                {!!badge && (
                  <span className="sgd-badge" style={{ background: color, color: "#06080B" }}>
                    {badge > 99 ? "99+" : badge}
                  </span>
                )}
              </div>
              <div className="sgd-meta">
                <div className="sgd-label" style={{ color }}>{label}</div>
                <div className="sgd-sub">{sub}</div>
              </div>
            </button>
          ))}
        </div>
      </div>

      <style>{`
        .sgd-root {
          position: fixed; left: 50%; bottom: 18px;
          transform: translateX(-50%);
          z-index: 70; max-width: 92vw; pointer-events: none;
        }
        .sgd-shell {
          pointer-events: auto;
          background: ${C.ink};
          backdrop-filter: blur(22px) saturate(150%);
          -webkit-backdrop-filter: blur(22px) saturate(150%);
          border: 1px solid ${C.border};
          border-radius: 14px;
          padding: 9px 11px;
          box-shadow: 0 24px 60px -18px rgba(0,0,0,0.65),
                      inset 0 1px 0 rgba(255,255,255,0.04);
        }
        .sgd-rail {
          display: flex; gap: 8px;
          overflow-x: auto; overflow-y: hidden;
          scroll-snap-type: x proximity;
          padding-bottom: 2px;
        }
        .sgd-rail::-webkit-scrollbar { height: 4px; }
        .sgd-rail::-webkit-scrollbar-thumb {
          background: ${C.cyan}44; border-radius: 4px;
        }
        .sgd-tile {
          flex: 0 0 auto;
          display: flex; align-items: center; gap: 10px;
          padding: 9px 14px 9px 10px;
          background: rgba(11, 16, 28, 0.55);
          border: 1px solid;
          border-radius: 10px;
          cursor: pointer;
          transition: transform 160ms ease, background 160ms ease, box-shadow 160ms ease;
          scroll-snap-align: start;
          min-width: 220px;
        }
        .sgd-tile:hover {
          transform: translateY(-1px);
          background: rgba(11, 16, 28, 0.85);
        }
        .sgd-icon-ring {
          position: relative;
          width: 38px; height: 38px; border-radius: 50%;
          display: grid; place-items: center;
          border: 1px solid; background: rgba(6,10,18,0.6);
          flex: 0 0 38px;
        }
        .sgd-badge {
          position: absolute; top: -4px; right: -6px;
          min-width: 16px; height: 16px; padding: 0 4px;
          border-radius: 8px;
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px; font-weight: 800;
          display: grid; place-items: center;
        }
        .sgd-meta {
          display: flex; flex-direction: column;
          text-align: left; min-width: 0;
        }
        .sgd-label {
          font-family: 'JetBrains Mono', monospace;
          font-size: 11px; font-weight: 700;
          letter-spacing: 0.12em; text-transform: uppercase;
          line-height: 1.05;
        }
        .sgd-sub {
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px; color: ${C.muted};
          letter-spacing: 0.08em; text-transform: uppercase;
          margin-top: 2px;
          white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
          max-width: 220px;
        }
        @media (max-width: 720px) {
          .sgd-tile { min-width: 200px; }
        }
      `}</style>
    </div>
  );
}
