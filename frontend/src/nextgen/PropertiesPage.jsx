import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { nxListProperties, nxCreateProperty, nxResolveProperty } from "@/nextgen/api";

/* Properties workspace — SD-002 identity resolution + create.
   Every value carries a source (address, coordinate, parcel) per Data Model §4.
*/

const EMPTY = {
  address: { line1: "", line2: "", city: "", region: "", postal_code: "", country_iso: "US" },
  coordinate: { lat: "", lon: "", precision_m: 5.0 },
  parcel: { jurisdiction: "", parcel_number: "" },
  unit_label: "",
};

export default function PropertiesPage() {
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [f, setF] = useState(EMPTY);
  const [candidates, setCandidates] = useState(null);
  const [err, setErr] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => nxListProperties().then((d) => setItems(d.items || []));
  useEffect(() => { load(); }, []);

  const payload = () => {
    const p = { address: { ...f.address }, unit_label: f.unit_label || null };
    if (f.coordinate.lat && f.coordinate.lon) {
      p.coordinate = {
        lat: parseFloat(f.coordinate.lat),
        lon: parseFloat(f.coordinate.lon),
        precision_m: parseFloat(f.coordinate.precision_m) || 5.0,
      };
    }
    if (f.parcel.jurisdiction && f.parcel.parcel_number) p.parcel = { ...f.parcel };
    return p;
  };

  const onResolve = async () => {
    setErr(null); setBusy(true);
    try {
      const r = await nxResolveProperty(payload());
      setCandidates(r);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const onCreate = async () => {
    setErr(null); setBusy(true);
    try {
      await nxCreateProperty(payload());
      setF(EMPTY); setShowForm(false); setCandidates(null);
      load();
    } catch (e) {
      const d = e?.response?.data?.detail;
      setErr(typeof d === "string" ? d : (d?.message || e.message));
    }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="nx-properties">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
        <div>
          <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// PROPERTY REGISTRY</div>
          <h1 className="nx-h1">Properties</h1>
          <div className="nx-sub">
            Canonical property identity is a composite of normalized address, coordinate, parcel identifier, and
            unit label (Blueprint v1.2 §11.2). Ownership is never identity. Duplicate identities are surfaced for
            review before a new record is minted.
          </div>
        </div>
        <button className="nx-btn" onClick={() => setShowForm(!showForm)} data-testid="nx-toggle-property-form">
          {showForm ? "Close" : "New Property"}
        </button>
      </div>

      {showForm && (
        <div className="nx-panel" style={{ marginBottom: 20 }}>
          <div className="corner">// SD-002 IDENTITY RESOLUTION</div>
          <div className="nx-grid cols-3">
            <div>
              <label className="nx-label">Address Line 1</label>
              <input className="nx-input" data-testid="nx-prop-line1" value={f.address.line1}
                onChange={(e) => setF({ ...f, address: { ...f.address, line1: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">City</label>
              <input className="nx-input" data-testid="nx-prop-city" value={f.address.city}
                onChange={(e) => setF({ ...f, address: { ...f.address, city: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">Region · State</label>
              <input className="nx-input" data-testid="nx-prop-region" value={f.address.region}
                onChange={(e) => setF({ ...f, address: { ...f.address, region: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">Postal Code</label>
              <input className="nx-input" data-testid="nx-prop-postal" value={f.address.postal_code}
                onChange={(e) => setF({ ...f, address: { ...f.address, postal_code: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">Unit Label</label>
              <input className="nx-input" data-testid="nx-prop-unit" placeholder="(optional)" value={f.unit_label}
                onChange={(e) => setF({ ...f, unit_label: e.target.value })} />
            </div>
            <div>
              <label className="nx-label">Parcel #</label>
              <input className="nx-input" data-testid="nx-prop-parcel" placeholder="Jurisdiction:number"
                value={f.parcel.parcel_number}
                onChange={(e) => setF({ ...f, parcel: { ...f.parcel, parcel_number: e.target.value, jurisdiction: f.address.region || "US" } })} />
            </div>
            <div>
              <label className="nx-label">Latitude</label>
              <input className="nx-input" data-testid="nx-prop-lat" value={f.coordinate.lat}
                onChange={(e) => setF({ ...f, coordinate: { ...f.coordinate, lat: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">Longitude</label>
              <input className="nx-input" data-testid="nx-prop-lon" value={f.coordinate.lon}
                onChange={(e) => setF({ ...f, coordinate: { ...f.coordinate, lon: e.target.value } })} />
            </div>
            <div>
              <label className="nx-label">Coord Precision (m)</label>
              <input className="nx-input" value={f.coordinate.precision_m}
                onChange={(e) => setF({ ...f, coordinate: { ...f.coordinate, precision_m: e.target.value } })} />
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
            <button className="nx-btn ghost" onClick={onResolve} disabled={busy} data-testid="nx-prop-resolve-btn">
              Resolve Identity
            </button>
            <button className="nx-btn" onClick={onCreate} disabled={busy} data-testid="nx-prop-create-btn">
              Create Property
            </button>
          </div>
          {candidates && (
            <div style={{ marginTop: 14, fontSize: 12, color: "#4DF6FF", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.16em" }}>
              // DECISION: {candidates.decision.toUpperCase()} · {candidates.candidates?.length || 0} CANDIDATES
            </div>
          )}
          {err && (
            <div style={{ marginTop: 14, color: "#FF5A5F", fontSize: 12 }} data-testid="nx-prop-error">
              {typeof err === "string" ? err : JSON.stringify(err)}
            </div>
          )}
        </div>
      )}

      {items.length === 0 ? (
        <div className="nx-empty" data-testid="nx-props-empty">
          No properties yet · Click &quot;New Property&quot; to begin the identity-resolution flow
        </div>
      ) : (
        <div className="nx-panel" style={{ padding: 0 }}>
          <table className="nx-table" data-testid="nx-props-table">
            <thead><tr>
              <th>// Canonical Id</th><th>Address</th><th>Coord</th><th>Truth Band</th><th>Created</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((p) => (
                <tr key={p.canonical_id}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF", fontSize: 11 }}>
                    {p.canonical_id.slice(0, 12)}…
                  </td>
                  <td>
                    <div>{p.address.line1}{p.unit_label ? ` · ${p.unit_label}` : ""}</div>
                    <div style={{ color: "#8A9BAE", fontSize: 11 }}>{p.address.city}, {p.address.region} {p.address.postal_code}</div>
                  </td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                    {p.coordinate ? `${p.coordinate.lat.toFixed(4)}, ${p.coordinate.lon.toFixed(4)}` : "—"}
                  </td>
                  <td><span className="nx-pill dim">BAND {p.truth_score_band}/10</span></td>
                  <td style={{ fontSize: 11, color: "#8A9BAE" }}>{p.created_at.slice(0, 10)}</td>
                  <td>
                    <div className="nx-flex nx-gap-2" style={{ flexWrap: "wrap" }}>
                      <Link to={`/nextgen/properties/${p.canonical_id}/overview`}
                        className="nx-btn small" data-testid={`nx-prop-open-${p.canonical_id}`}>
                        Open Workspace
                      </Link>
                      <Link to={`/nextgen/missions/new?property=${p.canonical_id}`}
                        className="nx-btn ghost small" data-testid={`nx-prop-mission-${p.canonical_id}`}>
                        New Job
                      </Link>
                    </div>
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
