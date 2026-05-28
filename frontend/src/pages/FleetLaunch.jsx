/**
 * STRATEX™ Fleet Launch Authorization (Step 5)
 *
 * Wire-compatible with both:
 *   - on-site hardware gateway  (/app/hardware-gateway/stratex-gateway.js)
 *   - cloud simulator           (/api/ws/stratex/core in /app/backend/server.py)
 *
 * Two mount points (see App.js):
 *   - /launch                   → standalone demo (no job tie-in)
 *   - /operator/launch/:jobId   → operator portal step 5, transitions job → IN_FLIGHT
 *
 * Aesthetic: STRATEX PBR Luxury-Corporate palette
 *   Electric Teal   #00F5D4
 *   Neon Orange     #FF5400
 *   Metallic Nickel #3A4350
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  Lock,
  Triangle,
  ShieldCheck,
  Battery,
  Satellite,
  RadioTower,
  CloudRain,
  Users,
  Plane,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { useAuth } from "@/lib/auth";

const PALETTE = {
  obsidian: "#0B0F17",
  nickel: "#3A4350",
  nickelSoft: "#212A37",
  teal: "#00F5D4",
  tealDim: "rgba(0,245,212,0.18)",
  orange: "#FF5400",
  orangeDim: "rgba(255,84,0,0.16)",
  silver: "#E2E8F0",
  hud: "#7A8699",
};

function deriveChecks(frame) {
  if (!frame) {
    return {
      trailerHatchSecured: false,
      batteryLevel: 0,
      rtkLocked: false,
      signalStrong: false,
      weatherOptimal: false,
      personnelClear: false,
      isFullyVerified: false,
      raw: null,
    };
  }
  const d = frame.dock || {};
  const drone = frame.drone || {};
  const env = frame.environment || {};
  const trailerHatchSecured = d.hatch_status === "OPEN";
  const batteryLevel = Number(drone.battery_percent ?? 0);
  const rtkLocked = drone.gps_status === "POSITION_OK_FIXED";
  const signalStrong = Number(drone.signal_rssi ?? 0) > 75;
  const weatherOptimal = Number(env.wind_speed_mph ?? 99) < 5 && !env.is_raining;
  const personnelClear = d.perimeter_clear === true;
  const isFullyVerified =
    trailerHatchSecured &&
    batteryLevel >= 100 &&
    rtkLocked &&
    signalStrong &&
    weatherOptimal &&
    personnelClear;
  return {
    trailerHatchSecured,
    batteryLevel,
    rtkLocked,
    signalStrong,
    weatherOptimal,
    personnelClear,
    isFullyVerified,
    raw: frame,
  };
}

function wsUrlFor(path, query = {}) {
  const base = process.env.REACT_APP_BACKEND_URL || window.location.origin;
  const u = new URL(base);
  u.protocol = u.protocol === "https:" ? "wss:" : "ws:";
  u.pathname = (u.pathname || "").replace(/\/+$/, "") + path;
  Object.entries(query).forEach(([k, v]) => {
    if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
  });
  return u.toString();
}

function StatusRow({ icon: Icon, label, valueText, ok, testid }) {
  return (
    <li
      data-testid={testid}
      className="flex items-center justify-between gap-4 py-3 border-b last:border-b-0"
      style={{ borderColor: "rgba(58,67,80,0.55)" }}
    >
      <div className="flex items-center gap-3 min-w-0">
        <span
          className="inline-flex items-center justify-center w-9 h-9 rounded-md flex-shrink-0"
          style={{
            background: ok ? PALETTE.tealDim : PALETTE.orangeDim,
            color: ok ? PALETTE.teal : PALETTE.orange,
            boxShadow: ok ? `0 0 14px ${PALETTE.tealDim}` : "none",
          }}
        >
          <Icon size={18} strokeWidth={2}/>
        </span>
        <div className="min-w-0">
          <div className="text-[11px] font-mono uppercase tracking-[0.22em]" style={{ color: PALETTE.hud }}>
            {label}
          </div>
          <div className="text-sm truncate" style={{ color: PALETTE.silver }}>{valueText}</div>
        </div>
      </div>
      <span
        className="text-[10px] font-mono uppercase tracking-[0.28em] px-2 py-1 rounded"
        style={{
          color: ok ? PALETTE.teal : PALETTE.orange,
          background: ok ? PALETTE.tealDim : PALETTE.orangeDim,
        }}
      >
        {ok ? "Nominal" : "Holding"}
      </span>
    </li>
  );
}

export default function FleetLaunch() {
  const { jobId } = useParams();
  const { token, user } = useAuth();

  const [connState, setConnState] = useState("connecting"); // connecting | live | auth_fail | disconnected
  const [frame, setFrame] = useState(null);
  const [events, setEvents] = useState([]); // [{kind, msg, ts}]
  const [authorizing, setAuthorizing] = useState(false);
  const [launched, setLaunched] = useState(null); // {authorization_id, server_timestamp}
  const wsRef = useRef(null);

  const project = useMemo(
    () => ({
      id: jobId || "PRJ-DEMO-2026-X",
      value: jobId ? "Project value redacted (operator view)" : "$41,298.36",
    }),
    [jobId]
  );

  const checks = useMemo(() => deriveChecks(frame), [frame]);

  useEffect(() => {
    if (!token) return;
    const url = wsUrlFor("/api/ws/stratex/core", { token });
    const ws = new WebSocket(url);
    wsRef.current = ws;
    setConnState("connecting");

    ws.onopen = () => setConnState("live");

    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "HELLO") {
          setEvents((e) => [{ kind: "info", msg: `Linked to ${msg.source}`, ts: msg.server_timestamp }, ...e].slice(0, 8));
          return;
        }
        if (msg.event === "AUTH_FAIL") {
          setConnState("auth_fail");
          setEvents((e) => [{ kind: "err", msg: "WebSocket auth failed", ts: new Date().toISOString() }, ...e].slice(0, 8));
          return;
        }
        if (msg.event === "AUTH_REJECTED") {
          setAuthorizing(false);
          setEvents((e) => [{ kind: "warn", msg: msg.detail || "Pre-flight hold", ts: new Date().toISOString() }, ...e].slice(0, 8));
          return;
        }
        if (msg.event === "MISSION_LAUNCHED") {
          setAuthorizing(false);
          setLaunched({ authorization_id: msg.authorization_id, server_timestamp: msg.server_timestamp, job_status_updated: msg.job_status_updated });
          setEvents((e) => [{ kind: "ok", msg: `Mission launched · ${msg.authorization_id.slice(0, 8)}`, ts: msg.server_timestamp }, ...e].slice(0, 8));
          return;
        }
        if (msg.event === "ERROR") {
          setEvents((e) => [{ kind: "err", msg: msg.detail || "ws error", ts: new Date().toISOString() }, ...e].slice(0, 8));
          return;
        }
        // telemetry frame
        if (msg.dock && msg.drone && msg.environment) {
          setFrame(msg);
        }
      } catch {
        /* ignore non-JSON */
      }
    };

    ws.onclose = () => setConnState((s) => (s === "auth_fail" ? s : "disconnected"));
    ws.onerror = () => setConnState((s) => (s === "auth_fail" ? s : "disconnected"));

    return () => {
      try { ws.close(); } catch {}
    };
  }, [token]);

  const onAuthorize = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return;
    if (!checks.isFullyVerified || authorizing || launched) return;
    setAuthorizing(true);
    wsRef.current.send(
      JSON.stringify({
        command: "AUTHORIZE_FLEET_LAUNCH",
        timestamp: Date.now(),
        payload: {
          project_id: project.id,
          approved_value: project.value,
          job_id: jobId || null,
        },
      })
    );
  };

  const connBadge = {
    connecting: { txt: "Linking…", color: PALETTE.hud, bg: "rgba(122,134,153,0.16)" },
    live: { txt: "Live · 4 Hz", color: PALETTE.teal, bg: PALETTE.tealDim },
    auth_fail: { txt: "Auth Failed", color: PALETTE.orange, bg: PALETTE.orangeDim },
    disconnected: { txt: "Disconnected", color: PALETTE.orange, bg: PALETTE.orangeDim },
  }[connState];

  return (
    <div
      data-testid="fleet-launch-page"
      className="min-h-screen w-full flex items-center justify-center px-6 py-10"
      style={{
        background: `radial-gradient(1100px 600px at 50% -10%, rgba(0,245,212,0.07), transparent 60%), ${PALETTE.obsidian}`,
        color: PALETTE.silver,
      }}
    >
      <div
        className="w-full max-w-3xl rounded-2xl p-7 md:p-9"
        style={{
          background: "linear-gradient(180deg, #131A25 0%, #0D131C 100%)",
          border: `1px solid ${PALETTE.nickel}`,
          boxShadow: "0 30px 80px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.03)",
        }}
      >
        {/* Header */}
        <div className="flex items-center justify-between pb-5" style={{ borderBottom: `1px solid ${PALETTE.nickelSoft}` }}>
          <div className="flex items-center gap-3">
            <span
              className="inline-flex items-center justify-center w-10 h-10 rounded-md"
              style={{ background: PALETTE.tealDim, color: PALETTE.teal }}
            >
              <Triangle size={20} strokeWidth={2.4}/>
            </span>
            <div>
              <div className="text-[10px] font-mono uppercase tracking-[0.32em]" style={{ color: PALETTE.hud }}>
                STRATEX™ · Strategic Thermal Reconnaissance
              </div>
              <div className="text-lg font-semibold" style={{ color: PALETTE.silver }}>
                Step 5 · Fleet Autonomous Launch Authorization
              </div>
            </div>
          </div>
          <div
            data-testid="ws-connection-badge"
            className="text-[10px] font-mono uppercase tracking-[0.28em] px-3 py-1.5 rounded inline-flex items-center gap-2"
            style={{ color: connBadge.color, background: connBadge.bg }}
          >
            <Activity size={12}/> {connBadge.txt}
          </div>
        </div>

        {/* Status block */}
        <ul className="my-6">
          <StatusRow
            testid="check-trailer-hatch"
            icon={ShieldCheck}
            label="Trailer Hatch"
            valueText={checks.trailerHatchSecured ? "Retracted & Secured (Ready)" : "Locked / Retracting…"}
            ok={checks.trailerHatchSecured}
          />
          <StatusRow
            testid="check-battery"
            icon={Battery}
            label="Drone Battery"
            valueText={`${checks.batteryLevel}% ${checks.batteryLevel >= 100 ? "(Cell-Balanced)" : "(Topping Off)"}`}
            ok={checks.batteryLevel >= 100}
          />
          <StatusRow
            testid="check-rtk"
            icon={Satellite}
            label="RTK GPS"
            valueText={checks.rtkLocked ? "Centimeter Locked · High-Precision" : "Acquiring Satellites…"}
            ok={checks.rtkLocked}
          />
          <StatusRow
            testid="check-uplink"
            icon={RadioTower}
            label="Communication Uplink"
            valueText={checks.signalStrong ? `Strong · Starlink Verified (${checks.raw?.drone?.signal_rssi ?? 0} dBm)` : "Attenuated · Checking RF"}
            ok={checks.signalStrong}
          />
          <StatusRow
            testid="check-weather"
            icon={CloudRain}
            label="Weather Envelope"
            valueText={checks.weatherOptimal ? `Optimal · Wind ${checks.raw?.environment?.wind_speed_mph ?? "—"} mph, Dry` : "Adverse Conditions · Holding"}
            ok={checks.weatherOptimal}
          />
          <StatusRow
            testid="check-personnel"
            icon={Users}
            label="Perimeter / Personnel"
            valueText={checks.personnelClear ? "Clear of Deployment Area" : "Proximity Alert · Human Detected"}
            ok={checks.personnelClear}
          />
        </ul>

        {/* Project value lockbox */}
        <div
          data-testid="project-value-lockbox"
          className="flex items-center justify-between px-4 py-3 rounded-lg mb-5"
          style={{
            border: `1px solid ${PALETTE.orange}`,
            background: PALETTE.orangeDim,
          }}
        >
          <div className="flex items-center gap-2 text-xs font-mono uppercase tracking-[0.22em]" style={{ color: PALETTE.orange }}>
            <Lock size={14}/>
            <span>Total Project Value · Approved & Locked</span>
          </div>
          <div className="text-base font-semibold" style={{ color: PALETTE.silver }}>{project.value}</div>
        </div>

        {/* Action button */}
        <button
          data-testid="authorize-launch-btn"
          disabled={!checks.isFullyVerified || authorizing || !!launched || connState !== "live"}
          onClick={onAuthorize}
          className="w-full py-4 rounded-xl text-sm md:text-base font-bold uppercase tracking-[0.22em] transition-all inline-flex items-center justify-center gap-3"
          style={
            launched
              ? {
                  background: PALETTE.tealDim,
                  color: PALETTE.teal,
                  border: `1px solid ${PALETTE.teal}`,
                  cursor: "default",
                }
              : checks.isFullyVerified && connState === "live"
              ? {
                  background: `linear-gradient(135deg, ${PALETTE.teal} 0%, #00BFA6 100%)`,
                  color: PALETTE.obsidian,
                  boxShadow: `0 0 24px rgba(0,245,212,0.45)`,
                  border: `1px solid ${PALETTE.teal}`,
                  cursor: "pointer",
                }
              : {
                  background: PALETTE.nickelSoft,
                  color: PALETTE.hud,
                  border: `1px solid ${PALETTE.nickel}`,
                  cursor: "not-allowed",
                }
          }
        >
          {launched ? (
            <>
              <CheckCircle2 size={18}/> Mission Authorized · {launched.authorization_id.slice(0, 8)}
            </>
          ) : authorizing ? (
            <>
              <Loader2 size={18} className="animate-spin"/> Sequencing Launch…
            </>
          ) : checks.isFullyVerified && connState === "live" ? (
            <>
              <Plane size={18}/> Authorize Aerial Reconnaissance
            </>
          ) : (
            <>
              <AlertTriangle size={18}/> System Pre-Flight Hold
            </>
          )}
        </button>

        {/* Telemetry footer + event log */}
        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg p-3" style={{ background: PALETTE.nickelSoft, border: `1px solid ${PALETTE.nickel}` }}>
            <div className="text-[10px] font-mono uppercase tracking-[0.28em] mb-2" style={{ color: PALETTE.hud }}>
              Mission Brief
            </div>
            <div className="text-xs leading-relaxed" style={{ color: PALETTE.silver }}>
              <div><span style={{ color: PALETTE.hud }}>Project</span> · {project.id}</div>
              <div><span style={{ color: PALETTE.hud }}>Operator</span> · {user?.email || "—"}</div>
              <div><span style={{ color: PALETTE.hud }}>Mode</span> · {jobId ? "Operator-bound (will transition job to IN_FLIGHT)" : "Standalone demo"}</div>
              {jobId && (
                <div className="mt-2">
                  <Link to={`/operator/jobs/${jobId}`} className="text-[10px] font-mono uppercase tracking-[0.28em]" style={{ color: PALETTE.teal }}>
                    ← Back to operator job
                  </Link>
                </div>
              )}
            </div>
          </div>

          <div data-testid="event-log" className="rounded-lg p-3" style={{ background: PALETTE.nickelSoft, border: `1px solid ${PALETTE.nickel}` }}>
            <div className="text-[10px] font-mono uppercase tracking-[0.28em] mb-2" style={{ color: PALETTE.hud }}>
              Telemetry Event Log
            </div>
            {events.length === 0 ? (
              <div className="text-xs italic" style={{ color: PALETTE.hud }}>Awaiting events…</div>
            ) : (
              <ul className="space-y-1.5">
                {events.map((e, i) => (
                  <li key={i} className="text-[11px] font-mono leading-snug">
                    <span style={{
                      color:
                        e.kind === "ok" ? PALETTE.teal :
                        e.kind === "warn" || e.kind === "err" ? PALETTE.orange :
                        PALETTE.hud
                    }}>
                      [{(e.ts || "").slice(11, 19)}]
                    </span>{" "}
                    <span style={{ color: PALETTE.silver }}>{e.msg}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
