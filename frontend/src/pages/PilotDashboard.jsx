/**
 * /pilot — Pilot Dashboard: today's 4 weather-cleared jobs.
 * Future-Noire aesthetic. Tappable cards open job sheet.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { PilotShell, NeonBadge, FN_TEAL, FN_GREEN, FN_DIM, FN_INK } from "@/components/PilotShell";
import { Calendar, MapPin, Clock, ChevronRight, Cloud } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtMoney = (n) => "$" + (n ?? 0).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function PilotDashboard() {
  const nav = useNavigate();
  const [data, setData] = useState({ items: [], pilot: "", callsign: "" });
  const [busy, setBusy] = useState(true);
  const token = typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null;

  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API}/pilot/calendar`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(data);
      } finally { setBusy(false); }
    })();
  }, [token]);

  const day = new Date().toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric", year: "numeric" });

  return (
    <PilotShell
      title="Today's Sortie"
      subtitle={`${data.callsign || "Alpha-08"} · ${day}`}
      rightSlot={<NeonBadge ok value={`${data.items?.length || 0} JOBS · WEATHER GREEN`}/>}
    >
      <div style={{
        maxWidth: 1180, margin: "0 auto",
        display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
        gap: 16,
      }} data-testid="pilot-calendar-grid">
        {busy && <SkeletonCard/>}
        {!busy && data.items?.map((j, idx) => (
          <button key={j.id}
                  data-testid={`pilot-job-card-${idx}`}
                  onClick={() => nav(`/pilot/job/${j.id}`)}
                  style={{
                    textAlign: "left", cursor: "pointer",
                    background: "linear-gradient(155deg, rgba(15,30,55,0.7) 0%, rgba(8,18,34,0.85) 100%)",
                    border: `1px solid ${FN_TEAL}33`, borderRadius: 6,
                    padding: 18, color: FN_INK,
                    transition: "transform 200ms ease, box-shadow 200ms ease, border-color 200ms ease",
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.transform = "translateY(-2px)";
                    e.currentTarget.style.borderColor = FN_TEAL;
                    e.currentTarget.style.boxShadow = `0 16px 40px -20px ${FN_TEAL}88`;
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.transform = "translateY(0)";
                    e.currentTarget.style.borderColor = `${FN_TEAL}33`;
                    e.currentTarget.style.boxShadow = "none";
                  }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <span style={{
                  width: 30, height: 30, borderRadius: 4,
                  background: `${FN_TEAL}22`, color: FN_TEAL,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  fontFamily: "monospace", fontSize: 12, fontWeight: 700,
                }}>{String(idx + 1).padStart(2, "0")}</span>
                <span style={{
                  fontFamily: "monospace", fontSize: 10, letterSpacing: "0.22em",
                  color: FN_DIM, textTransform: "uppercase",
                }}>SORTIE · SLOT {j.slot_index}</span>
              </div>
              <NeonBadge ok={j.weather_cleared} value={j.weather_cleared ? "WX CLEAR" : "HOLD"}/>
            </div>

            <div style={{ fontSize: 18, fontWeight: 700, letterSpacing: 0.3 }}>
              {j.client_name}
            </div>
            <div style={{ color: FN_DIM, fontSize: 12, marginTop: 4,
                          display: "flex", alignItems: "center", gap: 6 }}>
              <MapPin size={12}/> {j.property_address}
            </div>

            <div style={{
              marginTop: 14, paddingTop: 12, borderTop: `1px dashed ${FN_TEAL}22`,
              display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10,
              fontFamily: "monospace", fontSize: 11,
            }}>
              <Field icon={<Clock size={11}/>} label="WINDOW" value={j.scheduled_window}/>
              <Field icon={<Cloud size={11}/>} label="ROOF" value={j.roof_type?.split(" (")[0] || "—"}/>
              <Field label="CONTRACTOR" value={j.contractor_name}/>
              <Field label="VALUE (LOCKED)" value={fmtMoney(j.project_value_locked_usd)} accent/>
            </div>

            <div style={{ marginTop: 14, display: "flex", alignItems: "center", justifyContent: "space-between",
                          fontFamily: "monospace", fontSize: 11, letterSpacing: "0.2em",
                          color: FN_TEAL, textTransform: "uppercase" }}>
              <span>OPEN JOB SHEET</span>
              <ChevronRight size={14}/>
            </div>
          </button>
        ))}
      </div>
    </PilotShell>
  );
}

function Field({ icon, label, value, accent }) {
  return (
    <div>
      <div style={{ color: "#475569", letterSpacing: "0.16em", fontSize: 9 }}>
        {icon && <span style={{ marginRight: 4, verticalAlign: "middle" }}>{icon}</span>}
        {label}
      </div>
      <div style={{ color: accent ? FN_GREEN : FN_INK, marginTop: 2, fontWeight: accent ? 700 : 400 }}>
        {value || "—"}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <div style={{
      border: "1px dashed #1e293b", borderRadius: 6, padding: 24,
      color: FN_DIM, fontFamily: "monospace", fontSize: 11, letterSpacing: "0.2em",
      textTransform: "uppercase", textAlign: "center",
    }}>
      LOADING SORTIE…
    </div>
  );
}
