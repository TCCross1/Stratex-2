/**
 * /pilot/job/:jobId — Pilot Job Sheet.
 *
 * Contractor's full job info, client info, map of property + GO directions button,
 * and Pre-Flight CTA to launch the cockpit screen.
 */
import React, { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { PilotShell, NeonBadge, FN_TEAL, FN_GREEN, FN_DIM, FN_INK, FN_AMBER } from "@/components/PilotShell";
import { Navigation, Home, User, Phone, Building2, Briefcase, Hammer, ShieldCheck, Layers, Maximize2 } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

// Fix default Leaflet icon paths (Webpack-safe)
const houseIcon = L.divIcon({
  className: "pilot-house-icon",
  html: `<div style="width:34px;height:34px;border-radius:50%;background:radial-gradient(circle, ${FN_TEAL}cc, ${FN_TEAL}33);border:2px solid ${FN_TEAL};display:flex;align-items:center;justify-content:center;box-shadow:0 0 24px ${FN_TEAL};">
           <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="${FN_INK}" stroke-width="2"><path d="M3 12 12 3l9 9"/><path d="M5 10v10h14V10"/></svg>
         </div>`,
  iconSize: [34, 34], iconAnchor: [17, 17],
});

const fmtMoney = (n) => "$" + (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function PilotJobSheet() {
  const { jobId } = useParams();
  const nav = useNavigate();
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(true);
  const token = typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null;

  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API}/pilot/jobs/${jobId}`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setJob(data);
      } finally { setBusy(false); }
    })();
  }, [jobId, token]);

  const launchDirections = () => {
    if (!job) return;
    const url = `https://www.google.com/maps/dir/?api=1&destination=${job.lat},${job.lng}`;
    window.open(url, "_blank");
  };

  if (busy || !job) {
    return <PilotShell title="Job Sheet" back="/pilot"><div style={{ color: FN_DIM, fontFamily: "monospace" }}>LOADING…</div></PilotShell>;
  }

  return (
    <PilotShell
      title={job.client_name}
      subtitle={`SAT# ${job.node_link?.node_id || "AWAITING NODE LINK"} · SLOT ${String(job.slot_index + 1).padStart(2, "0")}`}
      back="/pilot"
      rightSlot={<NeonBadge ok={job.weather_cleared} value={job.weather_cleared ? "WX CLEAR" : "WX HOLD"}/>}
    >
      <div style={{ maxWidth: 1200, margin: "0 auto", display: "grid",
                    gridTemplateColumns: "minmax(320px, 1fr) 1.4fr", gap: 18 }}>
        {/* LEFT — client + job intel */}
        <div data-testid="pilot-job-intel" style={{
          background: "linear-gradient(155deg, rgba(15,30,55,0.7), rgba(8,18,34,0.85))",
          border: `1px solid ${FN_TEAL}33`, borderRadius: 6, padding: 18,
        }}>
          <SectionTitle icon={<User size={12}/>} text="CLIENT · POINT OF CONTACT"/>
          <KV k="NAME" v={job.client_name}/>
          <KV k="PHONE" v={<a href={`tel:${job.phone}`} style={{ color: FN_TEAL }}>{job.phone}</a>}/>
          <KV k="ADDRESS" v={job.property_address}/>

          <SectionTitle icon={<Briefcase size={12}/>} text="CONTRACTOR" top={18}/>
          <KV k="FIRM" v={job.contractor_name}/>
          <KV k="SALES REP" v={`${job.sales_rep} · ${job.sales_rep_phone}`}/>

          <SectionTitle icon={<Hammer size={12}/>} text="STRUCTURE" top={18}/>
          <KV k="ROOF" v={job.roof_type}/>
          <KV k="STORIES" v={job.stories}/>
          <KV k="APPROX SQFT" v={job.approx_sqft?.toLocaleString()}/>

          <SectionTitle icon={<ShieldCheck size={12}/>} text="PROJECT VALUE" top={18}/>
          <div style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            padding: "10px 12px", borderRadius: 4,
            border: `1px solid ${FN_AMBER}55`, background: `${FN_AMBER}10`,
            fontFamily: "monospace", marginTop: 4,
          }}>
            <span style={{ color: FN_AMBER, fontSize: 10, letterSpacing: "0.22em" }}>🔒 LOCKED</span>
            <span style={{ color: FN_AMBER, fontWeight: 700 }}>{fmtMoney(job.project_value_locked_usd)}</span>
          </div>
        </div>

        {/* RIGHT — Map + actions */}
        <div data-testid="pilot-job-map-col">
          <div style={{
            border: `1px solid ${FN_TEAL}55`, borderRadius: 6, overflow: "hidden",
            boxShadow: `0 20px 50px -25px ${FN_TEAL}88`,
            background: "#020812", marginBottom: 14,
          }}>
            <MapContainer center={[job.lat, job.lng]} zoom={17} style={{ height: 360, width: "100%" }}
                          scrollWheelZoom={true}>
              <TileLayer
                attribution='Esri'
                url='https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
              />
              <Marker position={[job.lat, job.lng]} icon={houseIcon}>
                <Popup>{job.property_address}</Popup>
              </Marker>
            </MapContainer>
            <div style={{
              display: "flex", alignItems: "center", justifyContent: "space-between",
              padding: "10px 14px", borderTop: `1px solid ${FN_TEAL}33`,
              background: "rgba(8,18,34,0.7)",
              fontFamily: "monospace", fontSize: 10, letterSpacing: "0.2em",
              color: FN_DIM, textTransform: "uppercase",
            }}>
              <span>SAT IMAGERY · LIVE · {job.lat.toFixed(4)},{job.lng.toFixed(4)}</span>
              <span style={{ color: FN_TEAL, display: "flex", alignItems: "center", gap: 4 }}>
                <Maximize2 size={10}/> PINCH TO ZOOM
              </span>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <button onClick={launchDirections}
                    data-testid="pilot-go-btn"
                    style={{
                      cursor: "pointer", background: `linear-gradient(135deg, ${FN_TEAL}, #0891b2)`,
                      color: "#020812", border: "none", borderRadius: 6, padding: "16px 18px",
                      fontFamily: "monospace", fontSize: 14, fontWeight: 800,
                      letterSpacing: "0.24em", textTransform: "uppercase",
                      boxShadow: `0 14px 32px -10px ${FN_TEAL}cc`,
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
                    }}>
              <Navigation size={18}/> GO · DIRECTIONS
            </button>
            <button onClick={() => nav(`/pilot/preflight/${jobId}`)}
                    data-testid="pilot-preflight-btn"
                    style={{
                      cursor: "pointer", background: "transparent",
                      color: FN_GREEN, border: `2px solid ${FN_GREEN}`,
                      borderRadius: 6, padding: "16px 18px",
                      fontFamily: "monospace", fontSize: 14, fontWeight: 800,
                      letterSpacing: "0.24em", textTransform: "uppercase",
                      boxShadow: `0 14px 32px -16px ${FN_GREEN}aa`,
                      display: "flex", alignItems: "center", justifyContent: "center", gap: 10,
                    }}>
              <ShieldCheck size={18}/> BEGIN PRE-FLIGHT
            </button>
          </div>

          {job.node_link && (
            <div style={{
              marginTop: 14, padding: "10px 14px", borderRadius: 4,
              border: `1px solid ${FN_GREEN}55`, background: `${FN_GREEN}10`,
              fontFamily: "monospace", color: FN_GREEN, fontSize: 11, letterSpacing: "0.2em",
            }}>
              ● NODE LINK ACTIVE · SAT# {job.node_link.node_id}
              {job.node_link.deployed_at && " · DEPLOYED ✓"}
            </div>
          )}
        </div>
      </div>
    </PilotShell>
  );
}

function SectionTitle({ icon, text, top = 0 }) {
  return (
    <div style={{ marginTop: top, marginBottom: 8,
                  color: FN_TEAL, fontFamily: "monospace", fontSize: 10,
                  letterSpacing: "0.28em", textTransform: "uppercase",
                  display: "flex", alignItems: "center", gap: 6 }}>
      {icon} {text}
    </div>
  );
}

function KV({ k, v }) {
  return (
    <div style={{ display: "grid", gridTemplateColumns: "110px 1fr", gap: 12, padding: "4px 0",
                  borderBottom: "1px dashed #1e293b", fontFamily: "monospace" }}>
      <span style={{ color: FN_DIM, fontSize: 10, letterSpacing: "0.16em",
                     textTransform: "uppercase", paddingTop: 2 }}>{k}</span>
      <span style={{ color: FN_INK, fontSize: 13 }}>{v}</span>
    </div>
  );
}
