import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Plane,
  ShieldCheck,
  Battery,
  Satellite,
  RadioTower,
  CloudRain,
  Users,
  ChevronRight,
  RotateCw,
  ExternalLink,
} from "lucide-react";
import { api } from "@/lib/api";

/**
 * /admin/flight-audit — Compliance audit of every AUTHORIZE_FLEET_LAUNCH
 * persisted to db.flight_authorizations. Admin-only.
 *
 * Visual contract: Electric Teal accents on the authorization rows, Metallic
 * Nickel chrome, telemetry snapshot rendered inline with the same six-check
 * vocabulary as the live /launch dashboard.
 */
const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";

function MicroCheck({ icon: Icon, ok, label, value }) {
  return (
    <div
      className="flex items-center gap-2 px-2.5 py-1.5 rounded border"
      style={{
        borderColor: ok ? `${TEAL}55` : `${ORANGE}55`,
        background: ok ? `${TEAL}14` : `${ORANGE}14`,
      }}
    >
      <Icon size={13} style={{ color: ok ? TEAL : ORANGE }}/>
      <div className="leading-tight">
        <div className="font-mono text-[9px] uppercase tracking-[0.2em]" style={{ color: ok ? TEAL : ORANGE }}>
          {label}
        </div>
        <div className="font-mono text-[10px] text-silver">{value}</div>
      </div>
    </div>
  );
}

export default function FlightAudit() {
  const [items, setItems] = useState([]);
  const [forbidden, setForbidden] = useState(false);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);

  async function load() {
    setLoading(true);
    try {
      const r = await api.get("/flight-authorizations/recent?limit=50");
      setItems(r.data?.items || []);
    } catch (err) {
      if (err?.response?.status === 403) setForbidden(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { load(); }, []);

  if (forbidden) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center p-8" data-testid="flight-audit-forbidden">
        <div className="border p-8 max-w-md" style={{ borderColor: ORANGE, background: `${ORANGE}10` }}>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: ORANGE }}>
            // 403 — ACCESS DENIED
          </div>
          <h1 className="font-display text-2xl uppercase tracking-widest mb-2">Admin Privilege Required</h1>
          <p className="font-body text-sm text-muted-hud">Flight Authorization Audit is restricted to admin accounts.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="flight-audit-root">
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="led led-teal"/>
          <div className="font-mono text-[11px] tracking-[0.36em] uppercase" style={{ color: TEAL }}>
            // STRATEX VISION • OVERSEER • FLIGHT AUTHORIZATION AUDIT
          </div>
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">Flight Authorization Audit</h1>
        <p className="font-body text-sm text-muted-hud mb-6 max-w-3xl">
          Every <span className="font-mono" style={{ color: TEAL }}>AUTHORIZE_FLEET_LAUNCH</span> command accepted by the cloud
          simulator or the on-site hardware gateway is recorded here with its telemetry snapshot, operator identity, and the
          job linkage (when bound).
        </p>

        <div className="flex items-center gap-3 mb-5">
          <Link
            to="/admin/overseer"
            data-testid="flight-audit-link-overseer"
            className="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 hover:bg-[#00F5D4]/10"
            style={{ borderColor: `${TEAL}55`, color: TEAL }}
          >
            ← Overseer Queue
          </Link>
          <button
            data-testid="flight-audit-refresh"
            onClick={load}
            className="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 hover:bg-[#00F5D4]/10 inline-flex items-center gap-2"
            style={{ borderColor: `${TEAL}55`, color: TEAL }}
          >
            <RotateCw size={11}/> Refresh
          </button>
          <div className="ml-auto font-mono text-[10px] uppercase tracking-[0.2em] text-muted-hud">
            {items.length} authorization{items.length === 1 ? "" : "s"}
          </div>
        </div>

        {loading && <div className="font-mono" style={{ color: TEAL }}>// LOADING…</div>}

        {!loading && items.length === 0 && (
          <div className="border p-12 text-center" style={{ borderColor: `${NICKEL}` }} data-testid="flight-audit-empty">
            <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud mb-2">// NO AUTHORIZATIONS YET</div>
            <p className="font-body text-sm text-silver">
              Trigger one from <Link to="/launch" className="underline" style={{ color: TEAL }}>/launch</Link> or the operator portal step 5.
            </p>
          </div>
        )}

        <ul className="space-y-3">
          {items.map((it) => {
            const t = it.telemetry_snapshot || {};
            const dock = t.dock || {};
            const drone = t.drone || {};
            const env = t.environment || {};
            const isExpanded = expanded === it.id;
            return (
              <li
                key={it.id}
                data-testid={`flight-audit-item-${it.id}`}
                className="border-l-4 bg-[#0B0F19] border-y border-r"
                style={{ borderLeftColor: TEAL, borderColor: `${NICKEL}` }}
              >
                <button
                  onClick={() => setExpanded(isExpanded ? null : it.id)}
                  className="w-full text-left px-4 py-3 flex items-center gap-4 flex-wrap"
                >
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5 border inline-flex items-center gap-1.5"
                    style={{ color: TEAL, borderColor: TEAL }}
                  >
                    <Plane size={11}/> AUTHORIZED
                  </span>
                  <span className="font-mono text-[10px]" style={{ color: TEAL }}>{it.id.slice(0, 8)}</span>
                  <span className="font-mono text-[10px] text-silver">{it.project_id || "—"}</span>
                  <span className="flex-1 font-body text-[12px] text-silver truncate">
                    {it.operator_email} <span className="text-muted-hud">·</span> {it.source}
                  </span>
                  {it.job_id && (
                    <Link
                      to={`/operator/jobs/${it.job_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-mono text-[9.5px] uppercase tracking-widest inline-flex items-center gap-1 px-2 py-0.5 border"
                      style={{ color: TEAL, borderColor: `${TEAL}55` }}
                    >
                      Job <ExternalLink size={9}/>
                    </Link>
                  )}
                  <span className="font-mono text-[9.5px] text-muted-hud">
                    {new Date(it.server_timestamp).toLocaleString()}
                  </span>
                  <ChevronRight size={14} className="text-muted-hud" style={{ transform: isExpanded ? "rotate(90deg)" : "none", transition: "transform .18s" }}/>
                </button>

                {isExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t space-y-3" style={{ borderColor: `${NICKEL}` }} data-testid={`flight-audit-snapshot-${it.id}`}>
                    <div className="font-mono text-[9.5px] uppercase tracking-[0.28em] text-muted-hud">Telemetry Snapshot at Authorization</div>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                      <MicroCheck icon={ShieldCheck} ok={dock.hatch_status === "OPEN"} label="Hatch" value={dock.hatch_status || "—"}/>
                      <MicroCheck icon={Battery} ok={(drone.battery_percent ?? 0) >= 100} label="Battery" value={`${drone.battery_percent ?? 0}%`}/>
                      <MicroCheck icon={Satellite} ok={drone.gps_status === "POSITION_OK_FIXED"} label="RTK GPS" value={drone.gps_status || "—"}/>
                      <MicroCheck icon={RadioTower} ok={(drone.signal_rssi ?? 0) > 75} label="Signal" value={`${drone.signal_rssi ?? 0} dBm`}/>
                      <MicroCheck icon={CloudRain} ok={(env.wind_speed_mph ?? 99) < 5 && !env.is_raining} label="Weather" value={`${env.wind_speed_mph ?? "—"} mph ${env.is_raining ? "· rain" : "· dry"}`}/>
                      <MicroCheck icon={Users} ok={dock.perimeter_clear === true} label="Perimeter" value={dock.perimeter_clear ? "Clear" : "Alert"}/>
                    </div>
                    <div className="grid md:grid-cols-2 gap-3 text-[11px] font-mono">
                      <div className="space-y-1">
                        <div className="text-muted-hud">// AUTHORIZATION META</div>
                        <div><span className="text-muted-hud">id</span> · {it.id}</div>
                        <div><span className="text-muted-hud">project_id</span> · {it.project_id || "—"}</div>
                        <div><span className="text-muted-hud">approved_value</span> · {it.approved_value || "—"}</div>
                        <div><span className="text-muted-hud">job_id</span> · {it.job_id || "(standalone)"}</div>
                      </div>
                      <div className="space-y-1">
                        <div className="text-muted-hud">// OPERATOR</div>
                        <div><span className="text-muted-hud">email</span> · {it.operator_email}</div>
                        <div><span className="text-muted-hud">role</span> · {it.operator_role}</div>
                        <div><span className="text-muted-hud">source</span> · {it.source}</div>
                        <div><span className="text-muted-hud">timestamp</span> · {it.server_timestamp}</div>
                      </div>
                    </div>
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
