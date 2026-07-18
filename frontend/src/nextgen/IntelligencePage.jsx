import React, { useEffect, useMemo, useState } from "react";
import { useParams, Link } from "react-router-dom";
import {
  nxGetMission, nxTaxonomy, nxListEvidence, nxListIntelligence,
  nxCreateIntelligence, nxReviewIntelligence, nxGetIntelligence,
} from "@/nextgen/api";

/* Property Intelligence workspace — Directive 007 · Wave 2B.
   Route: /nextgen/missions/:missionId/intelligence

   Structured intelligence is the single source of truth for reports,
   passport, twin, and downstream recommendations. */

const SEVERITY_COLOR = {
  INFORMATIONAL: "dim", MINOR: "ok", MODERATE: "gold",
  MAJOR: "warn", CRITICAL: "warn",
};

function Pill({ children, kind = "" }) {
  return <span className={`nx-pill ${kind}`}>{children}</span>;
}

const EMPTY = {
  building_system: "ROOF",
  building_component: "SHINGLES",
  observation: "",
  severity: "MODERATE",
  priority: "IMPORTANT",
  risk_level: "ELEVATED",
  awe_impact: { air: false, water: true, energy: false, rationale: "" },
  recommended_action: "",
  maintenance_recommendation: "",
  repair_recommendation: "",
  replacement_recommendation: "",
  estimated_remaining_life_years: "",
  warranty_impact: "",
  insurance_relevance: "",
  code_compliance_flag: false,
  estimated_cost_placeholder_usd: "",
  notes: "",
  visibility: { contractor: true, homeowner: true, adjuster: true, insurer: false, public: false, internal: true },
  ai_confidence_pct: "",
};

export default function IntelligencePage() {
  const { missionId } = useParams();
  const [missionData, setMissionData] = useState(null);
  const [tax, setTax] = useState(null);
  const [evidence, setEvidence] = useState([]);
  const [items, setItems] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [selectedEv, setSelectedEv] = useState([]);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  const [drawer, setDrawer] = useState(null);
  const [decisionBusy, setDecisionBusy] = useState(false);

  const load = async () => {
    try {
      const m = await nxGetMission(missionId);
      setMissionData(m);
      setTax(await nxTaxonomy());
      const ev = await nxListEvidence(missionId);
      setEvidence(ev.items);
      const ints = await nxListIntelligence(missionId);
      setItems(ints.items);
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
  };
  useEffect(() => { load(); }, [missionId]);

  const components = useMemo(() => {
    if (!tax) return [];
    return tax.systems[f.building_system] || [];
  }, [tax, f.building_system]);

  const create = async () => {
    setBusy(true); setErr(null);
    try {
      if (selectedEv.length === 0) throw new Error("Select at least one evidence item");
      const payload = { ...f,
        mission_id: missionId,
        evidence_ids: selectedEv,
        estimated_remaining_life_years: f.estimated_remaining_life_years === ""
          ? null : parseFloat(f.estimated_remaining_life_years),
        estimated_cost_placeholder_usd: f.estimated_cost_placeholder_usd === ""
          ? null : parseFloat(f.estimated_cost_placeholder_usd),
        ai_confidence_pct: f.ai_confidence_pct === "" ? null : parseFloat(f.ai_confidence_pct),
      };
      await nxCreateIntelligence(payload);
      setShowForm(false); setF(EMPTY); setSelectedEv([]);
      await load();
    } catch (e) { setErr(e?.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  const openDrawer = async (id) => {
    setDrawer({ loading: true });
    try { setDrawer(await nxGetIntelligence(id)); }
    catch (e) { setDrawer({ error: e.message }); }
  };

  const review = async (id, decision) => {
    setDecisionBusy(true);
    try {
      await nxReviewIntelligence(id, { decision });
      await load();
      if (drawer?.intelligence?.canonical_id === id) await openDrawer(id);
    } catch (e) {
      const d = e?.response?.data?.detail;
      alert(typeof d === "string" ? d : JSON.stringify(d));
    } finally { setDecisionBusy(false); }
  };

  if (!missionData || !tax) return <div className="nx-empty">Loading…</div>;
  const { mission: m, property: prop, product, stage_labels } = missionData;

  const counts = items.reduce((a, i) => {
    a[i.state] = (a[i.state] || 0) + 1;
    a.total++;
    return a;
  }, { total: 0 });

  return (
    <div data-testid="nx-intelligence">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>
        // PROPERTY INTELLIGENCE ENGINE · WAVE 2B · DIRECTIVE 007
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 18 }}>
        <div>
          <h1 className="nx-h1">{product.display_name}</h1>
          <div className="nx-sub">
            {prop?.address.line1}, {prop?.address.city} {prop?.address.region} ·
            Mission <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF" }}>
              {m.canonical_id.slice(0, 12)}…
            </span>
            &nbsp;· Structured intelligence powers every downstream artifact.
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <Link to={`/nextgen/missions/${missionId}/evidence`} className="nx-btn ghost">Evidence</Link>
          <Link to={`/nextgen/missions/${missionId}`} className="nx-btn ghost">Mission</Link>
          <Pill kind="gold">STAGE {m.stage}/15 · {stage_labels[m.stage - 1]}</Pill>
        </div>
      </div>

      {/* KPI strip */}
      <div className="nx-grid cols-4">
        <div className="nx-stat">
          <div className="k">// Objects</div><div className="v">{counts.total || 0}</div>
          <div className="s">Structured intelligence</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Approved</div>
          <div className="v" style={{ color: "#00FF9C" }}>{(counts.approved || 0) + (counts.passport_committed || 0)}</div>
          <div className="s">Passport-eligible</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Candidate</div>
          <div className="v cy">{counts.candidate || 0}</div>
          <div className="s">Awaiting review</div>
        </div>
        <div className="nx-stat">
          <div className="k">// Rejected</div>
          <div className="v" style={{ color: "#FF5A5F" }}>{counts.rejected || 0}</div>
          <div className="s">Not passport-committed</div>
        </div>
      </div>

      <h2 className="nx-h2"><span className="num">§01</span>Create Property Intelligence</h2>
      <div className="nx-panel">
        <div className="corner">// SD-008 / SD-012</div>
        {!showForm ? (
          <button className="nx-btn" onClick={() => setShowForm(true)}
            data-testid="nx-intel-open-form">New Intelligence Object</button>
        ) : (
          <>
            <div className="nx-grid cols-3">
              <div>
                <label className="nx-label">Building System</label>
                <select className="nx-select" value={f.building_system}
                  onChange={(e) => setF({ ...f, building_system: e.target.value,
                    building_component: (tax.systems[e.target.value] || ["OTHER"])[0] })}
                  data-testid="nx-intel-system">
                  {Object.keys(tax.systems).map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="nx-label">Component</label>
                <select className="nx-select" value={f.building_component}
                  onChange={(e) => setF({ ...f, building_component: e.target.value })}
                  data-testid="nx-intel-component">
                  {components.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="nx-label">Severity</label>
                <select className="nx-select" value={f.severity}
                  onChange={(e) => setF({ ...f, severity: e.target.value })}
                  data-testid="nx-intel-severity">
                  {tax.severity.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="nx-label">Priority</label>
                <select className="nx-select" value={f.priority}
                  onChange={(e) => setF({ ...f, priority: e.target.value })}>
                  {tax.priority.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="nx-label">Risk Level</label>
                <select className="nx-select" value={f.risk_level}
                  onChange={(e) => setF({ ...f, risk_level: e.target.value })}>
                  {tax.risk_level.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className="nx-label">AI Confidence %</label>
                <input className="nx-input" type="number" min="0" max="100" step="0.1"
                  value={f.ai_confidence_pct}
                  onChange={(e) => setF({ ...f, ai_confidence_pct: e.target.value })} />
              </div>
            </div>

            <label className="nx-label" style={{ marginTop: 14 }}>Observation</label>
            <textarea className="nx-input" rows={2} value={f.observation}
              onChange={(e) => setF({ ...f, observation: e.target.value })}
              data-testid="nx-intel-observation"
              placeholder="Short human-readable statement of what the evidence shows" />

            <label className="nx-label" style={{ marginTop: 14 }}>Recommended Action</label>
            <textarea className="nx-input" rows={2} value={f.recommended_action}
              onChange={(e) => setF({ ...f, recommended_action: e.target.value })} />

            <div className="nx-grid cols-3" style={{ marginTop: 14 }}>
              <div>
                <label className="nx-label">Remaining Life (years)</label>
                <input className="nx-input" value={f.estimated_remaining_life_years}
                  onChange={(e) => setF({ ...f, estimated_remaining_life_years: e.target.value })} />
              </div>
              <div>
                <label className="nx-label">Est. Cost Placeholder ($)</label>
                <input className="nx-input" value={f.estimated_cost_placeholder_usd}
                  onChange={(e) => setF({ ...f, estimated_cost_placeholder_usd: e.target.value })} />
              </div>
              <div>
                <label className="nx-label">Insurance Relevance</label>
                <input className="nx-input" value={f.insurance_relevance}
                  onChange={(e) => setF({ ...f, insurance_relevance: e.target.value })} />
              </div>
            </div>

            <label className="nx-label" style={{ marginTop: 14 }}>AWE Impact</label>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              {["air", "water", "energy"].map((k) => (
                <label key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#E6EEF6" }}>
                  <input type="checkbox" checked={f.awe_impact[k]}
                    onChange={(e) => setF({ ...f, awe_impact: { ...f.awe_impact, [k]: e.target.checked } })}
                    data-testid={`nx-intel-awe-${k}`} />
                  {k.toUpperCase()}
                </label>
              ))}
              <input className="nx-input" style={{ flex: 1, marginLeft: 12 }}
                placeholder="AWE rationale (why)"
                value={f.awe_impact.rationale}
                onChange={(e) => setF({ ...f, awe_impact: { ...f.awe_impact, rationale: e.target.value } })} />
            </div>

            <label className="nx-label" style={{ marginTop: 14 }}>Visibility</label>
            <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
              {Object.keys(f.visibility).map((k) => (
                <label key={k} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12, color: "#E6EEF6" }}>
                  <input type="checkbox" checked={f.visibility[k]}
                    onChange={(e) => setF({ ...f, visibility: { ...f.visibility, [k]: e.target.checked } })} />
                  {k}
                </label>
              ))}
            </div>

            <label className="nx-label" style={{ marginTop: 14 }}>Evidence References (required)</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))", gap: 6 }}>
              {evidence.map((ev) => {
                const on = selectedEv.includes(ev.canonical_id);
                return (
                  <label key={ev.canonical_id} style={{
                    display: "flex", alignItems: "center", gap: 6, fontSize: 11,
                    background: on ? "rgba(77,246,255,0.08)" : "#06090F",
                    border: `1px solid ${on ? "#4DF6FF" : "#1D2836"}`,
                    borderRadius: 3, padding: "6px 8px", cursor: "pointer",
                  }}>
                    <input type="checkbox" checked={on}
                      onChange={(e) => setSelectedEv(e.target.checked
                        ? [...selectedEv, ev.canonical_id]
                        : selectedEv.filter((x) => x !== ev.canonical_id))} />
                    <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF" }}>
                      {ev.kind}
                    </span>
                    <span style={{ color: "#8A9BAE" }}>{ev.original_filename.slice(0, 20)}</span>
                  </label>
                );
              })}
            </div>

            <div style={{ display: "flex", gap: 10, marginTop: 16 }}>
              <button className="nx-btn" onClick={create} disabled={busy}
                data-testid="nx-intel-create-btn">Create</button>
              <button className="nx-btn ghost" onClick={() => { setShowForm(false); setF(EMPTY); }}>Cancel</button>
            </div>
          </>
        )}
        {err && <div style={{ color: "#FF5A5F", marginTop: 10, fontSize: 12 }}>
          {typeof err === "string" ? err : JSON.stringify(err)}
        </div>}
      </div>

      <h2 className="nx-h2"><span className="num">§02</span>Intelligence Inventory</h2>
      {items.length === 0 ? (
        <div className="nx-empty">No intelligence objects yet</div>
      ) : (
        <div className="nx-panel" style={{ padding: 0 }}>
          <table className="nx-table" data-testid="nx-intel-table">
            <thead><tr>
              <th>System · Component</th><th>Observation</th><th>Severity</th>
              <th>AWE</th><th>State</th><th>Tier</th><th></th>
            </tr></thead>
            <tbody>
              {items.map((it) => (
                <tr key={it.canonical_id}>
                  <td style={{ fontSize: 11 }}>
                    <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#4DF6FF" }}>{it.building_system}</div>
                    <div style={{ color: "#8A9BAE" }}>{it.building_component}</div>
                  </td>
                  <td style={{ fontSize: 12, maxWidth: 400 }}>{it.observation}</td>
                  <td><Pill kind={SEVERITY_COLOR[it.severity]}>{it.severity}</Pill></td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
                    {["air", "water", "energy"].filter((k) => it.awe_impact?.[k])
                      .map((k) => k.toUpperCase()).join(" · ") || "—"}
                  </td>
                  <td>
                    <Pill kind={it.state === "passport_committed" ? "ok" :
                      it.state === "rejected" ? "warn" : "dim"}>
                      {it.state}
                    </Pill>
                  </td>
                  <td style={{ fontSize: 10, fontFamily: "'JetBrains Mono', monospace", color: "#FFB020" }}>
                    {it.risk_tier.replace(/^tier_/, "T").slice(0, 6)}
                  </td>
                  <td>
                    <button className="nx-btn ghost small" onClick={() => openDrawer(it.canonical_id)}
                      data-testid={`nx-intel-open-${it.canonical_id}`}>Inspect</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {drawer && (
        <div onClick={() => setDrawer(null)} style={{
          position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)", zIndex: 40,
        }}>
          <div onClick={(e) => e.stopPropagation()} style={{
            position: "absolute", right: 0, top: 0, bottom: 0, width: "min(640px, 92vw)",
            background: "#0B111A", borderLeft: "1px solid #2A3A4E", padding: 22, overflowY: "auto",
          }} data-testid="nx-intel-drawer">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
              <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// INTELLIGENCE DETAIL</div>
              <button className="nx-btn ghost small" onClick={() => setDrawer(null)}>Close</button>
            </div>
            {drawer.loading && <div className="nx-empty">Loading…</div>}
            {drawer.intelligence && (
              <>
                <h3 style={{ color: "#fff", marginBottom: 8 }}>
                  {drawer.intelligence.building_system} · {drawer.intelligence.building_component}
                </h3>
                <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
                  <Pill kind={SEVERITY_COLOR[drawer.intelligence.severity]}>{drawer.intelligence.severity}</Pill>
                  <Pill kind="gold">{drawer.intelligence.priority}</Pill>
                  <Pill>{drawer.intelligence.risk_level}</Pill>
                  <Pill kind="dim">{drawer.intelligence.risk_tier}</Pill>
                  <Pill kind={drawer.intelligence.state === "passport_committed" ? "ok" : "dim"}>
                    {drawer.intelligence.state}
                  </Pill>
                </div>
                <div className="nx-label">Observation</div>
                <p style={{ color: "#E6EEF6", fontSize: 13 }}>{drawer.intelligence.observation}</p>

                <div className="nx-label" style={{ marginTop: 10 }}>Recommended Action</div>
                <p style={{ color: "#E6EEF6", fontSize: 13 }}>{drawer.intelligence.recommended_action || "—"}</p>

                <div className="nx-grid cols-2" style={{ marginTop: 12 }}>
                  <div>
                    <div className="nx-label">Remaining Life</div>
                    {drawer.intelligence.estimated_remaining_life_years ?? "—"} yr
                  </div>
                  <div>
                    <div className="nx-label">Est. Cost</div>
                    ${drawer.intelligence.estimated_cost_placeholder_usd ?? "—"}
                  </div>
                  <div>
                    <div className="nx-label">Insurance</div>
                    {drawer.intelligence.insurance_relevance || "—"}
                  </div>
                  <div>
                    <div className="nx-label">AI Confidence</div>
                    {drawer.intelligence.ai_confidence_pct ?? "—"}%
                  </div>
                </div>

                <div className="nx-label" style={{ marginTop: 12 }}>AWE Impact</div>
                <div style={{ display: "flex", gap: 8, marginBottom: 6 }}>
                  {["air", "water", "energy"].map((k) => (
                    <Pill key={k} kind={drawer.intelligence.awe_impact?.[k] ? "ok" : "dim"}>
                      {k.toUpperCase()}: {drawer.intelligence.awe_impact?.[k] ? "Y" : "N"}
                    </Pill>
                  ))}
                </div>
                {drawer.intelligence.awe_impact?.rationale && (
                  <p style={{ fontSize: 11, color: "#8A9BAE" }}>{drawer.intelligence.awe_impact.rationale}</p>
                )}

                {drawer.intelligence.historical_comparison && (
                  <>
                    <div className="nx-label" style={{ marginTop: 12 }}>Historical Comparison</div>
                    <p style={{ fontSize: 11, color: "#8A9BAE" }}>
                      Previous: <span style={{ color: "#4DF6FF" }}>
                        {drawer.intelligence.historical_comparison.previous_severity}
                      </span>
                      &nbsp;· Δ severity {drawer.intelligence.historical_comparison.delta_severity}
                    </p>
                  </>
                )}

                {drawer.intelligence.passport_entry_id && (
                  <>
                    <div className="nx-label" style={{ marginTop: 12 }}>Passport Entry</div>
                    <p style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: "#00FF9C" }}>
                      {drawer.intelligence.passport_entry_id}
                    </p>
                  </>
                )}

                <div className="nx-label" style={{ marginTop: 12 }}>Reviews</div>
                {drawer.reviews?.length === 0 ? (
                  <div style={{ fontSize: 11, color: "#8A9BAE" }}>None yet</div>
                ) : (
                  drawer.reviews?.map((r) => (
                    <div key={r.canonical_id} style={{
                      fontSize: 11, padding: 6, borderBottom: "1px solid #1D2836",
                    }}>
                      <Pill kind={r.decision === "approve" ? "ok" : "warn"}>{r.decision}</Pill>
                      &nbsp;<span style={{ color: "#8A9BAE" }}>{r.at.slice(0, 19).replace("T", " ")}</span>
                      &nbsp;{r.notes && <span style={{ color: "#E6EEF6" }}>· {r.notes}</span>}
                    </div>
                  ))
                )}

                {["candidate", "requires_field_verification"].includes(drawer.intelligence.state) && (
                  <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
                    <button className="nx-btn" disabled={decisionBusy}
                      onClick={() => review(drawer.intelligence.canonical_id, "approve")}
                      data-testid="nx-intel-approve">
                      Approve · Passport
                    </button>
                    <button className="nx-btn ghost" style={{ borderColor: "#FFB020", color: "#FFB020" }}
                      disabled={decisionBusy}
                      onClick={() => review(drawer.intelligence.canonical_id, "request_rework")}>
                      Rework
                    </button>
                    <button className="nx-btn ghost" style={{ borderColor: "#FF5A5F", color: "#FF5A5F" }}
                      disabled={decisionBusy}
                      onClick={() => review(drawer.intelligence.canonical_id, "reject")}
                      data-testid="nx-intel-reject">
                      Reject
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
