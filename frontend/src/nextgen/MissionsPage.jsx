import React, { useEffect, useState } from "react";
import { Link, useSearchParams, useNavigate, useParams } from "react-router-dom";
import {
  nxListMissions, nxCreateMission, nxCatalog,
  nxListProperties, nxAdvanceMission, nxGetMission,
} from "@/nextgen/api";

/* Mission Control workspace — SD-003 + SD-004 + partial SD-024 progression. */

export function MissionsList() {
  const [items, setItems] = useState([]);
  const load = () => nxListMissions().then((d) => setItems(d.items || []));
  useEffect(() => { load(); }, []);
  return (
    <div data-testid="nx-missions">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
        <div>
          <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// MISSION CONTROL</div>
          <h1 className="nx-h1">Missions</h1>
          <div className="nx-sub">
            Every mission is bound to one canonical property, one product, and progresses through the 15-stage
            operational chain (Blueprint v1.2 §22). Stage transitions are audited on every advance.
          </div>
        </div>
        <Link to="/nextgen/missions/new" className="nx-btn" data-testid="nx-new-mission-btn">New Mission</Link>
      </div>

      {items.length === 0 ? (
        <div className="nx-empty">No missions yet</div>
      ) : (
        <div className="nx-panel" style={{ padding: 0 }}>
          <table className="nx-table" data-testid="nx-missions-table">
            <thead><tr>
              <th>// Mission Id</th><th>Product</th><th>Stage</th><th>State</th><th>Price</th><th>Created</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((m) => (
                <tr key={m.canonical_id}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF", fontSize: 11 }}>
                    {m.canonical_id.slice(0, 12)}…
                  </td>
                  <td><span className="nx-pill gold">{m.product}</span></td>
                  <td>
                    <span className="nx-pill">STAGE {m.stage}/15</span>
                  </td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{m.state}</td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", color: "#FFB020" }}>
                    ${(m.price.amount_cents / 100).toFixed(0)}
                  </td>
                  <td style={{ fontSize: 11, color: "#8A9BAE" }}>{m.created_at.slice(0, 10)}</td>
                  <td>
                    <Link to={`/nextgen/missions/${m.canonical_id}`} className="nx-btn ghost small"
                      data-testid={`nx-mission-open-${m.canonical_id}`}>Open</Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export function NewMission() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [catalog, setCatalog] = useState([]);
  const [props, setProps] = useState([]);
  const [propertyId, setPropertyId] = useState(sp.get("property") || "");
  const [product, setProduct] = useState("");
  const [notes, setNotes] = useState("");
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    nxCatalog().then((d) => setCatalog(d.products));
    nxListProperties().then((d) => setProps(d.items || []));
  }, []);

  const create = async () => {
    setErr(null); setBusy(true);
    try {
      const r = await nxCreateMission({
        property_id: propertyId,
        product,
        notes: notes || null,
      });
      nav(`/nextgen/missions/${r.mission.canonical_id}`);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="nx-new-mission">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// SD-003 · PRODUCT SELECTION & MISSION CREATION</div>
      <h1 className="nx-h1">New Mission</h1>

      <h2 className="nx-h2"><span className="num">§01</span>Property</h2>
      {props.length === 0 ? (
        <div className="nx-empty">
          No properties yet · <Link to="/nextgen/properties" style={{ color: "#4DF6FF" }}>create one first</Link>
        </div>
      ) : (
        <select className="nx-select" value={propertyId} onChange={(e) => setPropertyId(e.target.value)}
          data-testid="nx-mission-property">
          <option value="">— Select property —</option>
          {props.map((p) => (
            <option key={p.canonical_id} value={p.canonical_id}>
              {p.address.line1}, {p.address.city} {p.address.region}
            </option>
          ))}
        </select>
      )}

      <h2 className="nx-h2"><span className="num">§02</span>Product</h2>
      <div className="nx-grid cols-3">
        {catalog.map((p) => (
          <div key={p.product_key}
            className={`nx-product-card ${product === p.product_key ? "selected" : ""}`}
            onClick={() => setProduct(p.product_key)}
            data-testid={`nx-product-select-${p.product_key}`}
          >
            <div className="k">// {p.product_key.replace("_", " ")}</div>
            <div className="n">{p.display_name}</div>
            <ul>
              <li>QA · {p.human_qa_tier.replace(/_/g, " ")}</li>
              <li>Sensors · {p.sensor_requirements.slice(0, 2).join(", ")}</li>
            </ul>
            <div className="p">${(p.contractor_price_cents / 100).toFixed(0)}</div>
          </div>
        ))}
      </div>

      <h2 className="nx-h2"><span className="num">§03</span>Notes</h2>
      <textarea className="nx-input" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional briefing notes for dispatcher…" data-testid="nx-mission-notes" />

      <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
        <button className="nx-btn" disabled={!propertyId || !product || busy}
          onClick={create} data-testid="nx-mission-create-btn">
          Create Mission
        </button>
        <Link to="/nextgen/missions" className="nx-btn ghost">Cancel</Link>
      </div>
      {err && <div style={{ color: "#FF5A5F", marginTop: 12, fontSize: 12 }}>{String(err)}</div>}
    </div>
  );
}

export function MissionDetail({ id }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [advBusy, setAdvBusy] = useState(false);
  const load = () => nxGetMission(id).then(setData).catch((e) => setErr(e?.response?.data?.detail || e.message));
  useEffect(() => { load(); }, [id]);

  const advance = async () => {
    setAdvBusy(true);
    try {
      await nxAdvanceMission(id, data.mission.stage + 1, "Manual advance from Mission Detail");
      load();
    } finally { setAdvBusy(false); }
  };

  if (err) return <div className="nx-panel" style={{ borderColor: "#FF5A5F" }}>{String(err)}</div>;
  if (!data) return <div className="nx-empty">Loading mission…</div>;
  const { mission: m, property: p, product, stage_labels } = data;

  return (
    <div data-testid="nx-mission-detail">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// MISSION · {m.canonical_id}</div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 18 }}>
        <div>
          <h1 className="nx-h1">{product.display_name}</h1>
          <div className="nx-sub">
            {p?.address.line1}, {p?.address.city} {p?.address.region} · Mission created {m.created_at.slice(0, 10)}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <span className="nx-pill gold">STAGE {m.stage}/15 · {stage_labels[m.stage - 1]}</span>
          <Link to={`/nextgen/missions/${m.canonical_id}/evidence`} className="nx-btn ghost"
            data-testid="nx-mission-evidence-tab">Evidence</Link>
          {m.stage < 15 && (
            <button className="nx-btn" onClick={advance} disabled={advBusy} data-testid="nx-mission-advance-btn">
              Advance to Stage {m.stage + 1}
            </button>
          )}
        </div>
      </div>

      <div className="nx-grid cols-4">
        <div className="nx-stat"><div className="k">// State</div><div className="v" style={{ fontSize: 22 }}>{m.state}</div></div>
        <div className="nx-stat"><div className="k">// QA Tier</div><div className="v" style={{ fontSize: 18 }}>{product.human_qa_tier.replace(/_/g, " ")}</div></div>
        <div className="nx-stat"><div className="k">// Price</div><div className="v gd">${(m.price.amount_cents / 100).toFixed(0)}</div></div>
        <div className="nx-stat"><div className="k">// Est. Cost</div><div className="v" style={{ fontSize: 22 }}>${(m.estimated_cost.amount_cents / 100).toFixed(0)}</div></div>
      </div>

      <h2 className="nx-h2"><span className="num">§01</span>Operational Chain Position</h2>
      <div className="nx-panel">
        <div className="corner">// Blueprint §22</div>
        <div className="nx-stage-bar">
          {stage_labels.map((label, idx) => (
            <div key={idx} className={`nx-stage-cell ${idx + 1 === m.stage ? "active" : ""}`}
              data-testid={`nx-mission-stage-${idx + 1}`}>
              <span className="n">{String(idx + 1).padStart(2, "0")}</span>{label}
            </div>
          ))}
        </div>
      </div>

      <h2 className="nx-h2"><span className="num">§02</span>Product Envelope</h2>
      <div className="nx-panel">
        <div className="corner">// Blueprint §16</div>
        <div className="nx-grid cols-2">
          <div>
            <div className="nx-label">Capture Conditions</div>
            <pre style={{ background: "#06090F", padding: 10, borderRadius: 3, color: "#4DF6FF", fontSize: 11 }}>
{JSON.stringify(product.capture_conditions, null, 2)}
            </pre>
          </div>
          <div>
            <div className="nx-label">Processing Engines</div>
            <ul>
              {product.processing_engines.map((e) => (
                <li key={e} style={{ color: "#E6EEF6", fontSize: 12, fontFamily: "'JetBrains Mono', monospace" }}>
                  › {e}
                </li>
              ))}
            </ul>
            <div className="nx-label" style={{ marginTop: 12 }}>Habitat Entitlement</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {product.habitat_entitlement.map((h) => (
                <span key={h} className="nx-pill dim" style={{ fontSize: 9 }}>{h.replace(/_/g, " ")}</span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Route wrapper reads :id from useParams */
export function MissionDetailRoute() {
  const { id } = useParams();
  if (!id) return null;
  return <MissionDetail id={id} />;
}
