import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { nxHabitatPublicRead } from "@/nextgen/api";
import "@/nextgen/nextgen.css";

/* Homeowner Habitat surface — public, token-gated, no auth. Directive 008. */

function Dial({ score, label, big = false }) {
  const color = score >= 80 ? "#00FF9C" : score >= 60 ? "#FFB020" : "#FF5A5F";
  return (
    <div style={{
      background: "#0B111A", border: "1px solid #1D2836", borderRadius: 6,
      padding: big ? 22 : 16, textAlign: "center",
    }}>
      <div style={{
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 10, letterSpacing: "0.28em", textTransform: "uppercase",
        color: "#8A9BAE",
      }}>{label}</div>
      <div style={{
        fontSize: big ? 72 : 44, fontWeight: 700, color,
        margin: "8px 0", lineHeight: 1,
      }}>{score}</div>
      <div style={{ fontFamily: "'JetBrains Mono', monospace",
        fontSize: 9, letterSpacing: "0.24em", color: "#8A9BAE" }}>/ 100</div>
    </div>
  );
}

export default function HabitatPublic() {
  const { token } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    nxHabitatPublicRead(token).then((d) => {
      if (d?.detail) setErr(d.detail); else setData(d);
    }).catch((e) => setErr(e.message));
  }, [token]);

  if (err) return (
    <div style={{ background: "#05080D", color: "#FF5A5F", minHeight: "100vh",
      padding: 40, fontFamily: "Helvetica" }} data-testid="habitat-error">
      <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
        letterSpacing: "0.32em", color: "#4DF6FF", textTransform: "uppercase" }}>
        // STRATEX HABITAT
      </div>
      <h1 style={{ color: "#fff" }}>Link unavailable</h1>
      <p>{String(err)}</p>
    </div>
  );
  if (!data) return (
    <div style={{ background: "#05080D", color: "#8A9BAE", minHeight: "100vh",
      padding: 40, fontFamily: "Helvetica" }}>Loading your property…</div>
  );

  const { property_summary, inspection_date, awe, key_findings, priority_items,
    maintenance, timeline } = data;

  const sevColor = { CRITICAL: "#FF5A5F", MAJOR: "#FFB020",
    MODERATE: "#FFB020", MINOR: "#00FF9C", INFORMATIONAL: "#8A9BAE" };

  return (
    <div style={{ background: "#05080D", color: "#E6EEF6", minHeight: "100vh",
      fontFamily: "Helvetica Neue, Arial, sans-serif" }} data-testid="habitat-public">
      <div style={{ maxWidth: 1200, margin: "0 auto", padding: "28px 24px 60px" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
          letterSpacing: "0.32em", color: "#4DF6FF", textTransform: "uppercase" }}>
          // STRATEX HABITAT · YOUR PROPERTY
        </div>
        <h1 style={{ fontSize: 36, fontWeight: 700, color: "#fff", margin: "6px 0 4px" }}>
          {property_summary.address.line1}
        </h1>
        <div style={{ color: "#8A9BAE", fontSize: 14 }}>
          {property_summary.address.city}, {property_summary.address.region}
          {" "}{property_summary.address.postal_code}
        </div>
        <div style={{ color: "#8A9BAE", fontSize: 12, marginTop: 8,
          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.16em" }}>
          Latest inspection · {inspection_date?.slice(0, 10) || "—"}
        </div>

        {/* AWE composite */}
        <h2 style={{ marginTop: 32, color: "#4DF6FF", fontSize: 13,
          letterSpacing: "0.18em", textTransform: "uppercase",
          borderBottom: "1px solid #1D2836", paddingBottom: 6 }}>
          <span style={{ color: "#FFB020", fontFamily: "'JetBrains Mono', monospace" }}>§01 </span>
          AWE Composite Intelligence
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 14, marginTop: 14 }}>
          <Dial score={awe.air.score} label="Air" />
          <Dial score={awe.water.score} label="Water" />
          <Dial score={awe.energy.score} label="Energy" />
          <Dial score={awe.composite_index} label="Composite" big />
        </div>
        <div style={{ marginTop: 14, padding: "12px 16px", background: "#0B111A",
          border: "1px solid #1D2836", borderRadius: 4, fontSize: 12, color: "#8A9BAE" }}>
          Release state · <b style={{ color: "#FFB020" }}>{awe.release_state}</b>
          &nbsp;· Confidence <b style={{ color: "#E6EEF6" }}>{awe.confidence_pct}%</b>
          &nbsp;· Evidence completeness <b style={{ color: "#E6EEF6" }}>{awe.evidence_completeness_pct}%</b>
        </div>

        {/* Priority items */}
        <h2 style={{ marginTop: 32, color: "#4DF6FF", fontSize: 13,
          letterSpacing: "0.18em", textTransform: "uppercase",
          borderBottom: "1px solid #1D2836", paddingBottom: 6 }}>
          <span style={{ color: "#FFB020", fontFamily: "'JetBrains Mono', monospace" }}>§02 </span>
          Priority Items
        </h2>
        {priority_items.length === 0 ? (
          <div style={{ padding: 24, color: "#8A9BAE", fontStyle: "italic" }}>
            No priority items · your property looks good on the essentials.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 10, marginTop: 12 }}>
            {priority_items.map((p, i) => (
              <div key={i} style={{ background: "#0B111A", border: "1px solid #1D2836",
                borderRadius: 4, padding: 14 }} data-testid="habitat-priority-card">
                <div style={{ display: "flex", justifyContent: "space-between",
                  alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                  <div style={{ fontFamily: "'JetBrains Mono', monospace",
                    color: "#4DF6FF", fontSize: 11, letterSpacing: "0.16em" }}>
                    {p.building_system} / {p.building_component}
                  </div>
                  <div style={{ display: "flex", gap: 6 }}>
                    <span style={{ padding: "3px 10px", border: `1px solid ${sevColor[p.severity]}`,
                      color: sevColor[p.severity], fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 9, letterSpacing: "0.2em", borderRadius: 999 }}>
                      {p.severity}
                    </span>
                    <span style={{ padding: "3px 10px", border: "1px solid #FFB020",
                      color: "#FFB020", fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 9, letterSpacing: "0.2em", borderRadius: 999 }}>
                      {p.priority}
                    </span>
                  </div>
                </div>
                <div style={{ marginTop: 8, color: "#E6EEF6", fontSize: 14 }}>{p.observation}</div>
                {p.recommended_action && (
                  <div style={{ marginTop: 6, color: "#8A9BAE", fontSize: 12 }}>
                    <b style={{ color: "#4DF6FF" }}>Recommended · </b>{p.recommended_action}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Maintenance */}
        {maintenance.length > 0 && (
          <>
            <h2 style={{ marginTop: 32, color: "#4DF6FF", fontSize: 13,
              letterSpacing: "0.18em", textTransform: "uppercase",
              borderBottom: "1px solid #1D2836", paddingBottom: 6 }}>
              <span style={{ color: "#FFB020", fontFamily: "'JetBrains Mono', monospace" }}>§03 </span>
              Maintenance Recommendations
            </h2>
            <ul style={{ marginTop: 12, listStyle: "none", padding: 0 }}>
              {maintenance.map((m, i) => (
                <li key={i} style={{ background: "#0B111A", border: "1px solid #1D2836",
                  borderRadius: 4, padding: 12, marginBottom: 8, fontSize: 13 }}>
                  <b style={{ color: "#4DF6FF", fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 11, letterSpacing: "0.14em" }}>
                    {m.building_system} / {m.building_component}
                  </b>
                  <div style={{ color: "#E6EEF6", marginTop: 4 }}>{m.maintenance_recommendation}</div>
                </li>
              ))}
            </ul>
          </>
        )}

        {/* Timeline */}
        <h2 style={{ marginTop: 32, color: "#4DF6FF", fontSize: 13,
          letterSpacing: "0.18em", textTransform: "uppercase",
          borderBottom: "1px solid #1D2836", paddingBottom: 6 }}>
          <span style={{ color: "#FFB020", fontFamily: "'JetBrains Mono', monospace" }}>§04 </span>
          Property Timeline
        </h2>
        <div style={{ marginTop: 12 }}>
          {timeline.map((t, i) => (
            <div key={i} style={{ display: "grid",
              gridTemplateColumns: "160px 200px 1fr", gap: 12,
              padding: "8px 0", borderBottom: "1px solid #1D2836",
              fontSize: 12, alignItems: "center" }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace",
                color: "#8A9BAE", fontSize: 10 }}>{t.at.slice(0, 19).replace("T", " ")}</span>
              <span style={{ padding: "3px 10px", border: "1px solid #4DF6FF",
                color: "#4DF6FF", fontFamily: "'JetBrains Mono', monospace",
                fontSize: 9, letterSpacing: "0.2em", borderRadius: 999,
                width: "fit-content" }}>{t.kind}</span>
              <span style={{ color: "#E6EEF6" }}>{t.summary}</span>
            </div>
          ))}
        </div>

        <div style={{ marginTop: 40, fontFamily: "'JetBrains Mono', monospace",
          fontSize: 9, letterSpacing: "0.28em", color: "#8A9BAE",
          textTransform: "uppercase", textAlign: "center" }}>
          // STRATEX™ HABITAT · READ-ONLY · YOUR PROPERTY INTELLIGENCE
        </div>
      </div>
    </div>
  );
}
