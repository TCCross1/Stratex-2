import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { nxOverview, nxHealth, nxMe, nxCatalog } from "@/nextgen/api";

/* Overview / Mission Control shell — SD-024 executive view.
   15-stage strip + tenant KPIs + product catalog + gate list. */

export default function OverviewPage() {
  const [ov, setOv] = useState(null);
  const [health, setHealth] = useState(null);
  const [me, setMe] = useState(null);
  const [catalog, setCatalog] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([nxOverview(), nxHealth(), nxMe(), nxCatalog()])
      .then(([o, h, m, c]) => { setOv(o); setHealth(h); setMe(m); setCatalog(c.products); })
      .catch((e) => setErr(e?.response?.data?.detail || e.message));
  }, []);

  if (err) return (
    <div className="nx-panel" style={{ borderColor: "#FF5A5F", color: "#FF5A5F" }} data-testid="nx-error">
      Error: {String(err)}
    </div>
  );
  if (!ov) return <div className="nx-empty">Loading overview…</div>;

  const activeStages = ov.missions_by_stage.filter((s) => s.count > 0).map((s) => s.stage);

  return (
    <div data-testid="nx-overview">
      <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", marginBottom: 24 }}>
        <div>
          <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// COMMAND CENTER</div>
          <h1 className="nx-h1">Mission Control</h1>
          <div className="nx-sub">
            Residential Property Intelligence Operating System · 15-stage operational chain per Blueprint v1.2 §22 ·
            capture → intelligence → passport → habitat → delivery.
          </div>
        </div>
        <Link to="/nextgen/missions/new" className="nx-btn" data-testid="nx-new-mission-cta">New Mission</Link>
      </div>

      {/* KPI STRIP */}
      <div className="nx-grid cols-4">
        <div className="nx-stat">
          <div className="k">// Active Properties</div>
          <div className="v cy">{ov.counts.properties_active}</div>
          <div className="s">Canonical Passport identities</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Missions</div>
          <div className="v gd">{ov.counts.missions_total}</div>
          <div className="s">Across all products</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Stages in Flight</div>
          <div className="v">{activeStages.length}<span style={{ fontSize: 16, color: "#8A9BAE", marginLeft: 6 }}>/ 15</span></div>
          <div className="s">Blueprint §22 progression</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Phase</div>
          <div className="v" style={{ fontSize: 26 }}>{health?.phase || "—"}</div>
          <div className="s">Legacy Freeze · Foundation</div>
        </div>
      </div>

      {/* STAGE STRIP */}
      <h2 className="nx-h2"><span className="num">§01</span>Operational Chain — 15 Stages</h2>
      <div className="nx-panel">
        <div className="corner">// Blueprint §22</div>
        <div className="nx-stage-bar">
          {ov.missions_by_stage.map((s) => (
            <div key={s.stage} className={`nx-stage-cell ${s.count > 0 ? "active" : ""}`} data-testid={`nx-stage-${s.stage}`}>
              <span className="n">{String(s.stage).padStart(2, "0")}</span>
              {s.label}
              {s.count > 0 && <span className="c">{s.count}</span>}
            </div>
          ))}
        </div>
      </div>

      {/* PRODUCT CATALOG */}
      <h2 className="nx-h2"><span className="num">§02</span>Product Catalog</h2>
      <div className="nx-grid cols-3">
        {catalog.map((p) => (
          <div key={p.product_key} className="nx-product-card" data-testid={`nx-product-${p.product_key}`}>
            <div className="k">// {p.product_key.replace("_", " ")} · {p.version}</div>
            <div className="n">{p.display_name}</div>
            <ul>
              <li>Capture · {Object.entries(p.capture_conditions).slice(0, 2).map(([k, v]) => `${k}=${v}`).join(" · ")}</li>
              <li>QA Tier · {p.human_qa_tier.replace(/_/g, " ")}</li>
              <li>Report · {p.report_template}</li>
              <li>Sensors · {p.sensor_requirements.slice(0, 3).join(", ")}</li>
            </ul>
            <div className="p">${(p.contractor_price_cents / 100).toFixed(0)}</div>
            <div style={{ fontSize: 10, color: "#8A9BAE", letterSpacing: "0.24em", textTransform: "uppercase", marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>
              Contractor Price · Estimated Internal ${(p.internal_cost_estimate_cents / 100).toFixed(0)}
            </div>
          </div>
        ))}
      </div>

      {/* GATES */}
      <h2 className="nx-h2"><span className="num">§03</span>Executive Approval Gates</h2>
      <div className="nx-panel">
        <div className="corner">// Withheld · Directive 005</div>
        <div style={{ fontSize: 13, color: "#8A9BAE", lineHeight: 1.7 }}>
          The following actions remain strictly gated to explicit executive authorization:
          <ul style={{ marginTop: 10 }}>
            {(health?.requires_executive_approval || []).map((g) => (
              <li key={g} style={{ color: "#FFB020", fontFamily: "'JetBrains Mono', monospace", fontSize: 12, letterSpacing: "0.14em" }}>
                › {g.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
