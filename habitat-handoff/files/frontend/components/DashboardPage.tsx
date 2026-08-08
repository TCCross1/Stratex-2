/**
 * Full Habitat Dashboard page — desktop IA from approved mockup.
 * Fetches /api/habitat/dashboard/projection and /api/habitat/openings
 * via REACT_APP_BACKEND_URL so responses are JSON (not SPA HTML).
 */
import React, { useEffect, useState } from "react";
import { HabitatDashboardShell, OpeningDetailPanel } from "./HabitatDashboardShell";

const API = `${process.env.REACT_APP_BACKEND_URL || ""}/api`;

async function fetchJson(path: string) {
  const r = await fetch(`${API}${path}`, { credentials: "include" });
  const ctype = r.headers.get("content-type") || "";
  if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`);
  if (!ctype.includes("application/json")) {
    throw new Error(
      `Expected JSON from ${path}, got ${ctype || "unknown"} (check REACT_APP_BACKEND_URL)`
    );
  }
  return r.json();
}

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [openings, setOpenings] = useState<any[]>([]);
  const [selected, setSelected] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([
      fetchJson("/habitat/dashboard/projection"),
      fetchJson("/habitat/openings"),
    ])
      .then(([dash, opens]) => {
        setData(dash);
        setOpenings(opens.openings || []);
        if (opens.openings?.[0]) setSelected(opens.openings[0]);
      })
      .catch((e) => setError(String(e)));
  }, []);

  if (error) {
    return <div style={{ color: "#ef4444", padding: 24 }}>Failed to load Habitat projection: {error}</div>;
  }
  if (!data) {
    return <div style={{ color: "#8b9bb0", padding: 24 }}>Loading Property Passport…</div>;
  }

  return (
    <div>
      <HabitatDashboardShell data={data} />
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px", gap: 16, padding: 16, background: "#0b0e14" }}>
        <section className="habitat-card">
          <h2 style={{ color: "#f3f6fa" }}>Exterior Openings</h2>
          <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
            {openings.map((o) => (
              <li
                key={o.id}
                onClick={() => setSelected(o)}
                style={{
                  padding: "10px 0",
                  borderBottom: "1px solid rgba(0,229,255,0.18)",
                  cursor: "pointer",
                  color: selected?.id === o.id ? "#00e5ff" : "#f3f6fa",
                }}
              >
                {o.label} · {o.unit_display} · RO {o.rough_opening_display}
              </li>
            ))}
          </ul>
        </section>
        {selected && <OpeningDetailPanel opening={selected} />}
      </div>
      <div
        data-testid="projection-authority-footer"
        style={{ padding: 12, color: "#8b9bb0", fontSize: 12, textAlign: "center" }}
      >
        Passport status: {data.passport_status || (data.authoritative ? "OK" : "PROJECTED")}
        {data.authoritative
          ? " · official Passport projection"
          : " · preview / non-authoritative projection"}
        {data.source === "HABITAT_PROJECTION_PATH" ? " · file handoff" : ""}
      </div>
    </div>
  );
}
