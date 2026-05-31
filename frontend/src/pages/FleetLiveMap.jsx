/**
 * /fleet/live-map — Live tracking map for CEO / GM / Sales Rep / Admin.
 *
 * Plane icons drift across Leaflet satellite tiles. Click a plane → full intel
 * popover (operator, callsign, sales rep + phone, client, phase, job sheet).
 */
import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup, useMap, Polyline } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { PilotShell, NeonBadge, FN_TEAL, FN_GREEN, FN_AMBER, FN_DIM, FN_INK } from "@/components/PilotShell";
import { Plane, Phone, User, Briefcase, Activity, RefreshCw } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const phaseColor = (p) => ({
  TRANSIT_TO_JOB: FN_TEAL,
  PRE_FLIGHT: FN_AMBER,
  LAUNCH: FN_AMBER,
  IN_FLIGHT: FN_TEAL,
  SCAN: FN_TEAL,
  TRANSFER: FN_TEAL,
  CONSENSUS: "#a855f7",
  LANDING: FN_GREEN,
  COMPLETE: FN_GREEN,
}[p] || FN_DIM);

/**
 * Build a heading-aware plane icon. The plane SVG points "up" by default
 * (nose at 0°); we rotate the inner wrapper by `heading_deg` so it points
 * along the unit's current flight bearing. CSS transitions make the rotation
 * smooth instead of a snap on every poll.
 */
const buildPlaneIcon = (color, callsign, headingDeg = 0) => L.divIcon({
  className: "stratex-plane-icon",
  html: `<div style="position:relative;display:flex;flex-direction:column;align-items:center;">
    <div style="width:44px;height:44px;border-radius:50%;background:radial-gradient(circle, ${color}cc, ${color}33);border:2px solid ${color};display:flex;align-items:center;justify-content:center;box-shadow:0 0 28px ${color};">
      <div style="width:24px;height:24px;display:flex;align-items:center;justify-content:center;transform:rotate(${headingDeg}deg);transition:transform 1.2s cubic-bezier(.4,0,.2,1);">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="${color}" stroke="${color}" stroke-width="0.5">
          <path d="M12 2 L14 11 L22 13 L22 15 L14 15 L13 22 L11 22 L10 15 L2 15 L2 13 L10 11 Z"/>
        </svg>
      </div>
    </div>
    <div style="margin-top:4px;padding:2px 6px;background:#020812cc;border:1px solid ${color}88;border-radius:3px;font-family:monospace;font-size:9px;letter-spacing:0.16em;color:${color};white-space:nowrap;">${callsign}</div>
  </div>`,
  iconSize: [44, 70], iconAnchor: [22, 22],
});

function AutoBounds({ units }) {
  const map = useMap();
  useEffect(() => {
    if (!units?.length) return;
    if (units.length === 1) {
      map.setView([units[0].lat, units[0].lng], 16);
    } else {
      const bounds = L.latLngBounds(units.map((u) => [u.lat, u.lng]));
      map.fitBounds(bounds, { padding: [40, 40] });
    }
  }, [units, map]);
  return null;
}

export default function FleetLiveMap() {
  const [units, setUnits] = useState([]);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const token = typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null;

  const load = async () => {
    try {
      const { data } = await axios.get(`${API}/fleet/live`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setUnits(data?.units || []);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally { setBusy(false); }
  };

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []); // eslint-disable-line

  const center = useMemo(() => units[0] ? [units[0].lat, units[0].lng] : [38.0011, -84.5436], [units]);

  return (
    <PilotShell
      title="Fleet · Live Theater"
      subtitle="REAL-TIME UNIT TELEMETRY · CEO · GM · SALES OPS"
      back="/ceo/command"
      rightSlot={
        <span style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
          <NeonBadge ok value={`${units.length} ACTIVE`}/>
          <button onClick={load} data-testid="fleet-live-refresh" style={{
            background: "transparent", border: `1px solid ${FN_TEAL}55`, color: FN_TEAL,
            padding: "5px 10px", borderRadius: 4, cursor: "pointer", fontFamily: "monospace",
            fontSize: 10, letterSpacing: "0.18em", textTransform: "uppercase",
          }}>
            <RefreshCw size={11} style={{ verticalAlign: "middle", marginRight: 4 }}/>SYNC
          </button>
        </span>
      }
    >
      <div style={{ maxWidth: 1400, margin: "0 auto", display: "grid",
                    gridTemplateColumns: "1fr 360px", gap: 18 }}>
        <div data-testid="fleet-live-map" style={{
          border: `1px solid ${FN_TEAL}55`, borderRadius: 8, overflow: "hidden",
          boxShadow: `0 30px 60px -30px ${FN_TEAL}99`,
        }}>
          <MapContainer center={center} zoom={13} style={{ height: 640, width: "100%", background: "#020812" }}>
            <TileLayer
              attribution='Esri'
              url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
            />
            <AutoBounds units={units}/>
            {units.map((u) => {
              const color = phaseColor(u.phase);
              const trail = Array.isArray(u.trail) ? u.trail : [];
              return (
                <React.Fragment key={u.unit_id}>
                  {/* Breadcrumb trail — fades from dim glow to neon at the head */}
                  {trail.length >= 2 && (
                    <>
                      <Polyline
                        positions={trail}
                        pathOptions={{ color, weight: 6, opacity: 0.18 }}
                      />
                      <Polyline
                        positions={trail}
                        pathOptions={{ color, weight: 2.2, opacity: 0.95, dashArray: "1 6" }}
                      />
                    </>
                  )}
                  <Marker position={[u.lat, u.lng]}
                          icon={buildPlaneIcon(color, u.unit_id, u.heading_deg || 0)}>
                    <Popup>
                      <UnitPopover u={u}/>
                    </Popup>
                  </Marker>
                </React.Fragment>
              );
            })}
          </MapContainer>
        </div>

        <aside data-testid="fleet-live-roster" style={{
          background: "linear-gradient(155deg, rgba(15,30,55,0.7), rgba(8,18,34,0.85))",
          border: `1px solid ${FN_TEAL}33`, borderRadius: 8, padding: 14,
        }}>
          <div style={{ fontFamily: "monospace", fontSize: 10, letterSpacing: "0.28em",
                        color: FN_TEAL, textTransform: "uppercase", marginBottom: 12 }}>
            // ACTIVE ROSTER
          </div>
          {busy && <div style={{ color: FN_DIM, fontFamily: "monospace" }}>LOADING…</div>}
          {err && <div style={{ color: FN_AMBER, fontSize: 11 }}>{err}</div>}
          {units.map((u) => (
            <div key={u.unit_id} style={{
              border: `1px solid ${phaseColor(u.phase)}55`,
              background: `${phaseColor(u.phase)}10`,
              borderRadius: 4, padding: 12, marginBottom: 10,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontWeight: 700, fontSize: 14 }}>{u.unit_id}</span>
                <span style={{ color: phaseColor(u.phase), fontFamily: "monospace", fontSize: 9,
                               letterSpacing: "0.2em" }}>● {u.phase}</span>
              </div>
              <div style={{ marginTop: 4, fontFamily: "monospace", fontSize: 11, color: FN_INK }}>
                {u.callsign_pilot}
              </div>
              {u.job?.client_name && (
                <div style={{ marginTop: 2, color: FN_DIM, fontSize: 11 }}>{u.job.client_name}</div>
              )}
              <div style={{ marginTop: 6, color: FN_DIM, fontSize: 10, fontFamily: "monospace" }}>
                {u.telemetry?.charge_level?.toFixed?.(0) ?? "100"}% · {u.telemetry?.wifi_signal} · {u.lifetime_scans ?? 0} scans
              </div>
            </div>
          ))}
        </aside>
      </div>
    </PilotShell>
  );
}

function UnitPopover({ u }) {
  return (
    <div style={{ minWidth: 260, fontFamily: "system-ui, sans-serif" }}>
      <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 4 }}>
        <Plane size={14} style={{ verticalAlign: "middle", marginRight: 6 }}/>
        {u.unit_id} · {u.callsign_pilot}
      </div>
      <div style={{ fontSize: 11, color: "#475569", marginBottom: 6 }}>
        PHASE: <b style={{ color: phaseColor(u.phase) }}>{u.phase}</b>
      </div>
      <Row icon={<Briefcase size={11}/>} label="Sales Rep" value={`${u.sales_rep || "—"}`}/>
      <Row icon={<Phone size={11}/>} label="Sales Rep Cell" value={u.sales_rep_phone || "—"}/>
      {u.job && (
        <>
          <Row icon={<User size={11}/>} label="Client" value={u.job.client_name}/>
          <Row label="Address" value={u.job.property_address}/>
          <Row label="Contractor" value={u.job.contractor_name}/>
        </>
      )}
      <Row icon={<Activity size={11}/>} label="Lifetime Scans" value={u.lifetime_scans ?? 0}/>
      {u.job_id && (
        <Link to={`/pilot/job/${u.job_id}`} style={{
          display: "inline-block", marginTop: 8, color: FN_TEAL,
          fontFamily: "monospace", fontSize: 11, letterSpacing: "0.18em",
          textDecoration: "none", textTransform: "uppercase",
        }}>OPEN JOB SHEET →</Link>
      )}
    </div>
  );
}

function Row({ icon, label, value }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", padding: "2px 0",
                  fontSize: 11, borderBottom: "1px dashed #e5e7eb" }}>
      <span style={{ color: "#475569" }}>{icon && <span style={{ marginRight: 4 }}>{icon}</span>}{label}</span>
      <span style={{ color: "#0f172a", textAlign: "right", marginLeft: 10 }}>{value}</span>
    </div>
  );
}
