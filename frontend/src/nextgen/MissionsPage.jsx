import React, { useEffect, useState, useMemo } from "react";
import { Link, useSearchParams, useNavigate, useParams } from "react-router-dom";
import {
  Compass, ArrowUpRight, Plus, Search, Filter, MapPin,
  Camera, Cpu, ShieldCheck, ChevronRight, Package,
} from "lucide-react";
import {
  nxListMissions, nxCreateMission, nxCatalog,
  nxListProperties, nxAdvanceMission, nxGetMission,
} from "@/nextgen/api";

/* Mission Control workspace — SD-003 + SD-004 (styled for Directive 009).
   Cards replace legacy table. Filters. Real routes reused. */

const STATE_LABELS = {
  DRAFT: { label: "Draft", pill: "dim" },
  ACTIVE: { label: "Active", pill: "cyan" },
  IN_PROGRESS: { label: "In Progress", pill: "cyan" },
  COMPLETED: { label: "Completed", pill: "ok" },
  BLOCKED: { label: "Blocked", pill: "danger" },
};

const FILTERS = [
  { key: "all", label: "All" },
  { key: "active", label: "Active" },
  { key: "evidence", label: "Awaiting Evidence" },
  { key: "qa", label: "Awaiting QA" },
  { key: "delivery", label: "Ready for Delivery" },
  { key: "completed", label: "Completed" },
];

function classifyMission(m) {
  if (m.state === "COMPLETED" || m.stage >= 14) return "completed";
  if (m.stage < 5) return "evidence";
  if (m.stage < 8) return "qa";
  if (m.stage < 10) return "delivery";
  return "active";
}

export function MissionsList() {
  const [items, setItems] = useState([]);
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const load = () => nxListMissions().then((d) => { setItems(d.items || []); setLoading(false); });
  useEffect(() => { load(); }, []);

  const filtered = useMemo(() => {
    let out = items;
    if (filter !== "all") out = out.filter((m) => classifyMission(m) === filter);
    if (q) {
      const t = q.toLowerCase();
      out = out.filter((m) =>
        m.canonical_id.toLowerCase().includes(t) ||
        m.product.toLowerCase().includes(t)
      );
    }
    return out;
  }, [items, q, filter]);

  return (
    <div data-testid="nx-missions">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// MISSION CONTROL</div>
          <h1 className="nx-page-title">Missions</h1>
          <div className="nx-page-sub">
            Every mission is bound to one canonical property, one product, and progresses through the 15-stage
            operational chain. Stage transitions are audited on every advance.
          </div>
        </div>
        <Link to="/nextgen/missions/new" className="nx-btn" data-testid="nx-new-mission-btn">
          <Plus size={16} strokeWidth={2} /> New Mission
        </Link>
      </div>

      {/* Filters */}
      <div className="nx-missions-toolbar">
        <div className="nx-search-wrap">
          <Search size={16} strokeWidth={1.6} />
          <input
            className="nx-input"
            placeholder="Search missions by id or product…"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            data-testid="nx-missions-search"
            style={{ paddingLeft: 40 }}
          />
        </div>
        <div className="nx-mobile-tabs" data-testid="nx-missions-filters">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`nx-filter-chip ${filter === f.key ? "active" : ""}`}
              onClick={() => setFilter(f.key)}
              data-testid={`nx-missions-filter-${f.key}`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="nx-empty">Loading missions…</div>
      ) : filtered.length === 0 ? (
        <EmptyMissions hasAny={items.length > 0} />
      ) : (
        <div className="nx-mission-grid" data-testid="nx-mission-grid">
          {filtered.map((m) => (
            <MissionCard key={m.canonical_id} mission={m} />
          ))}
        </div>
      )}

      <MissionsStyles />
    </div>
  );
}

function EmptyMissions({ hasAny }) {
  return (
    <div className="nx-card elevated" style={{ padding: 40, textAlign: "center" }} data-testid="nx-missions-empty">
      <Compass size={44} strokeWidth={1.4} color="var(--nx-cyan)" style={{ opacity: 0.7 }} />
      <div style={{ fontSize: 18, color: "#fff", marginTop: 14, fontWeight: 600 }}>
        {hasAny ? "No missions match this filter" : "No missions yet"}
      </div>
      <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 6, maxWidth: 380, marginInline: "auto" }}>
        {hasAny
          ? "Adjust the filter or clear your search to see all missions."
          : "Create your first mission to bind a property to a Stratex product and begin the 15-stage operational chain."}
      </div>
      <Link to="/nextgen/missions/new" className="nx-btn" style={{ marginTop: 22 }} data-testid="nx-missions-empty-cta">
        <Plus size={16} /> New Mission
      </Link>
    </div>
  );
}

function MissionCard({ mission: m }) {
  const pct = Math.round((m.stage / 15) * 100);
  const state = STATE_LABELS[m.state] || { label: m.state, pill: "dim" };
  return (
    <Link
      to={`/nextgen/missions/${m.canonical_id}`}
      className="nx-mission-card"
      data-testid={`nx-mission-card-${m.canonical_id}`}
    >
      <div className="nx-mission-card-top">
        <div>
          <div className="nx-label" style={{ color: "var(--nx-cyan)" }}>
            MSN · {m.canonical_id.slice(0, 8).toUpperCase()}
          </div>
          <div className="nx-mission-card-name">{m.product.replace(/_/g, " ")}</div>
        </div>
        <span className={`nx-pill ${state.pill}`}>{state.label}</span>
      </div>

      <div className="nx-mission-card-meta">
        <span className="nx-pill cyan">STAGE {m.stage}/15</span>
        <span className="nx-pill gold">${((m.price?.amount_cents || 0) / 100).toFixed(0)}</span>
        <span className="nx-pill dim">{new Date(m.created_at).toLocaleDateString()}</span>
      </div>

      <div style={{ marginTop: 14 }}>
        <div className="nx-progress"><div className="fill" style={{ width: `${pct}%` }} /></div>
      </div>

      <div className="nx-mission-card-foot">
        <span className="nx-label">Open mission command</span>
        <ChevronRight size={18} strokeWidth={1.6} color="var(--nx-cyan)" />
      </div>
    </Link>
  );
}

function MissionsStyles() {
  return (
    <style>{`
      .nx-missions-toolbar {
        display: flex; gap: 14px; align-items: center; margin-bottom: 18px;
        flex-wrap: wrap;
      }
      .nx-search-wrap { position: relative; flex: 1; min-width: 220px; max-width: 460px; }
      .nx-search-wrap > svg {
        position: absolute; left: 14px; top: 50%; transform: translateY(-50%);
        color: var(--nx-text-muted);
      }
      .nx-filter-chip {
        padding: 8px 14px; border-radius: var(--nx-r-pill);
        border: 1px solid var(--nx-border-strong);
        background: transparent; color: var(--nx-text-secondary);
        font-family: var(--nx-font-tech); font-size: 10.5px;
        letter-spacing: 0.22em; text-transform: uppercase;
        cursor: pointer; white-space: nowrap; min-height: 36px;
      }
      .nx-filter-chip:hover { border-color: var(--nx-cyan-line); color: var(--nx-text); }
      .nx-filter-chip.active {
        border-color: var(--nx-cyan); color: #fff; background: rgba(77,246,255,0.09);
      }
      .nx-mission-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
        gap: 16px;
      }
      .nx-mission-card {
        display: block;
        background: linear-gradient(180deg, var(--nx-panel), var(--nx-panel-2));
        border: 1px solid var(--nx-border);
        border-radius: var(--nx-r-md);
        padding: 20px;
        text-decoration: none; color: inherit;
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.2s ease;
        min-height: 180px;
      }
      .nx-mission-card:hover { transform: translateY(-2px); border-color: var(--nx-cyan-line); box-shadow: 0 10px 30px rgba(0,0,0,0.4); }
      .nx-mission-card-top {
        display: flex; justify-content: space-between; align-items: flex-start; gap: 12px;
      }
      .nx-mission-card-name {
        font-size: 17px; font-weight: 700; color: #fff; margin-top: 6px;
      }
      .nx-mission-card-meta {
        display: flex; gap: 6px; flex-wrap: wrap; margin-top: 12px;
      }
      .nx-mission-card-foot {
        display: flex; justify-content: space-between; align-items: center;
        margin-top: 14px; padding-top: 12px;
        border-top: 1px solid var(--nx-border);
      }
    `}</style>
  );
}

/* ── NewMission ─────────────────────────────────────────────── */
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
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// PRODUCT SELECTION</div>
          <h1 className="nx-page-title">New Mission</h1>
          <div className="nx-page-sub">
            Bind a canonical property to a Stratex product. The 15-stage operational chain begins on creation.
          </div>
        </div>
      </div>

      <div className="nx-section-title">
        <span className="num">§01</span>
        <span className="label">Property</span>
        <span className="rule" />
      </div>
      {props.length === 0 ? (
        <div className="nx-empty">
          No properties yet · <Link to="/nextgen/properties" style={{ color: "var(--nx-cyan)" }}>create one first</Link>
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

      <div className="nx-section-title">
        <span className="num">§02</span>
        <span className="label">Product</span>
        <span className="rule" />
      </div>
      <div className="nx-grid cols-3">
        {catalog.map((p) => (
          <div key={p.product_key}
            className={`nx-product-card ${product === p.product_key ? "selected" : ""}`}
            onClick={() => setProduct(p.product_key)}
            data-testid={`nx-product-select-${p.product_key}`}
          >
            <div className="k">// {p.product_key.replace(/_/g, " ")}</div>
            <div className="n">{p.display_name}</div>
            <ul>
              <li>QA · {p.human_qa_tier.replace(/_/g, " ")}</li>
              <li>Sensors · {p.sensor_requirements.slice(0, 2).join(", ")}</li>
            </ul>
            <div className="p">${(p.contractor_price_cents / 100).toFixed(0)}</div>
          </div>
        ))}
      </div>

      <div className="nx-section-title">
        <span className="num">§03</span>
        <span className="label">Notes</span>
        <span className="rule" />
      </div>
      <textarea className="nx-textarea" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)}
        placeholder="Optional briefing notes for dispatcher…" data-testid="nx-mission-notes" />

      <div style={{ display: "flex", gap: 10, marginTop: 22 }}>
        <button className="nx-btn" disabled={!propertyId || !product || busy}
          onClick={create} data-testid="nx-mission-create-btn">
          {busy ? "Creating…" : "Create Mission"}
        </button>
        <Link to="/nextgen/missions" className="nx-btn ghost">Cancel</Link>
      </div>
      {err && <div style={{ color: "var(--nx-critical)", marginTop: 12, fontSize: 13 }}>{String(err)}</div>}
    </div>
  );
}

/* ── MissionDetail (Command view w/ tabs) ─────────────────────── */
export function MissionDetail({ id }) {
  const [data, setData] = useState(null);
  const [err, setErr] = useState(null);
  const [advBusy, setAdvBusy] = useState(false);
  const [tab, setTab] = useState("overview");
  const load = () => nxGetMission(id).then(setData).catch((e) => setErr(e?.response?.data?.detail || e.message));
  useEffect(() => { load(); }, [id]);

  const advance = async () => {
    setAdvBusy(true);
    try {
      await nxAdvanceMission(id, data.mission.stage + 1, "Manual advance from mission command");
      load();
    } finally { setAdvBusy(false); }
  };

  if (err) return <div className="nx-card" style={{ borderColor: "var(--nx-critical)" }}>{String(err)}</div>;
  if (!data) return <div className="nx-empty">Loading mission…</div>;
  const { mission: m, property: p, product, stage_labels } = data;
  const pct = Math.round((m.stage / 15) * 100);

  return (
    <div data-testid="nx-mission-detail">
      <div className="nx-page-header">
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="nx-page-eyebrow">MISSION · {m.canonical_id.slice(0, 12)}…</div>
          <h1 className="nx-page-title">{product.display_name}</h1>
          <div className="nx-page-sub">
            {p?.address.line1}, {p?.address.city} {p?.address.region} · Created {m.created_at.slice(0, 10)}
          </div>
        </div>
      </div>

      {/* Command Card */}
      <div className="nx-card elevated" data-testid="nx-mission-command">
        <div className="nx-mission-command-grid">
          <div style={{ display: "flex", alignItems: "center", gap: 22 }}>
            <div className="nx-ring" style={{ ["--size"]: "112px" }}>
              <svg width="112" height="112" viewBox="0 0 112 112">
                <circle cx="56" cy="56" r="46" stroke="rgba(77,246,255,0.08)" strokeWidth="10" fill="none" />
                <circle cx="56" cy="56" r="46" stroke="#4DF6FF" strokeWidth="10" fill="none"
                  strokeLinecap="round" strokeDasharray={2 * Math.PI * 46}
                  strokeDashoffset={2 * Math.PI * 46 - (pct / 100) * 2 * Math.PI * 46}
                  style={{ transition: "stroke-dashoffset 0.6s ease" }} />
              </svg>
              <div className="ring-value">{pct}%</div>
              <div className="ring-caption">Complete</div>
            </div>
            <div>
              <div className="nx-label">Current Stage</div>
              <div style={{ color: "#fff", fontWeight: 700, fontSize: 22, marginTop: 4 }}>
                {stage_labels[m.stage - 1]}
              </div>
              <div style={{ display: "flex", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                <span className="nx-pill cyan">STAGE {m.stage}/15</span>
                <span className="nx-pill dim">{m.state}</span>
              </div>
            </div>
          </div>

          <div className="nx-mission-checklist">
            <ChecklistRow icon={<Camera size={16} />} label="Evidence" value={m.stage >= 5 ? "Captured" : "Pending"} ok={m.stage >= 5} />
            <ChecklistRow icon={<Cpu size={16} />} label="Intelligence" value={m.stage >= 7 ? "Processed" : "Pending"} ok={m.stage >= 7} />
            <ChecklistRow icon={<ShieldCheck size={16} />} label="QA Review" value={m.stage >= 8 ? "Approved" : "Pending"} ok={m.stage >= 8} />
            <ChecklistRow icon={<Package size={16} />} label="Passport" value={m.stage >= 10 ? "Ready" : "Pending"} ok={m.stage >= 10} />
          </div>
        </div>

        <div className="nx-mission-command-actions">
          {m.stage < 15 && (
            <button className="nx-btn" onClick={advance} disabled={advBusy} data-testid="nx-mission-advance-btn">
              {advBusy ? "Advancing…" : `Advance to Stage ${m.stage + 1}`}
            </button>
          )}
          <Link to={`/nextgen/missions/${m.canonical_id}/evidence`} className="nx-btn ghost" data-testid="nx-mission-evidence-tab">
            <Camera size={15} /> Evidence
          </Link>
          <Link to={`/nextgen/missions/${m.canonical_id}/intelligence`} className="nx-btn ghost" data-testid="nx-mission-intelligence-tab">
            <Cpu size={15} /> Intelligence
          </Link>
        </div>
      </div>

      {/* Tabbed content */}
      <div className="nx-mission-tabs" data-testid="nx-mission-tabs" role="tablist">
        {[
          { key: "overview", label: "Overview" },
          { key: "evidence", label: "Evidence" },
          { key: "intelligence", label: "Intelligence" },
          { key: "timeline", label: "Timeline" },
        ].map((t) => (
          <button
            key={t.key}
            role="tab"
            aria-selected={tab === t.key}
            className={`nx-mission-tab ${tab === t.key ? "active" : ""}`}
            onClick={() => setTab(t.key)}
            data-testid={`nx-mission-tab-${t.key}`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === "overview" && (
        <>
          <div className="nx-section-title">
            <span className="num">§A</span><span className="label">Operational Chain</span><span className="rule" />
          </div>
          <div className="nx-card">
            <div className="nx-stage-strip">
              {stage_labels.map((label, idx) => (
                <div key={idx} className={`cell ${idx + 1 === m.stage ? "active" : ""}`}
                  data-testid={`nx-mission-stage-${idx + 1}`}>
                  <span className="n">{String(idx + 1).padStart(2, "0")}</span>{label}
                </div>
              ))}
            </div>
          </div>

          <div className="nx-section-title">
            <span className="num">§B</span><span className="label">Product Envelope</span><span className="rule" />
          </div>
          <div className="nx-card">
            <div className="nx-grid cols-2">
              <div>
                <div className="nx-label">Capture Conditions</div>
                <pre style={{ background: "#05090F", padding: 12, borderRadius: 8, color: "var(--nx-cyan)", fontSize: 11, fontFamily: "var(--nx-font-mono)", overflowX: "auto" }}>
{JSON.stringify(product.capture_conditions, null, 2)}
                </pre>
              </div>
              <div>
                <div className="nx-label">Processing Engines</div>
                <ul style={{ paddingLeft: 16 }}>
                  {product.processing_engines.map((e) => (
                    <li key={e} style={{ color: "#E6EEF6", fontSize: 12, fontFamily: "var(--nx-font-mono)", marginBottom: 3 }}>
                      › {e}
                    </li>
                  ))}
                </ul>
                <div className="nx-label" style={{ marginTop: 16 }}>Habitat Entitlement</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
                  {product.habitat_entitlement.map((h) => (
                    <span key={h} className="nx-pill">{h.replace(/_/g, " ")}</span>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </>
      )}

      {tab === "evidence" && (
        <div className="nx-card" style={{ padding: 40, textAlign: "center" }} data-testid="nx-mission-evidence-panel">
          <Camera size={40} strokeWidth={1.4} color="var(--nx-cyan)" style={{ opacity: 0.7 }} />
          <div style={{ marginTop: 14, color: "#fff", fontSize: 16, fontWeight: 600 }}>Evidence Workspace</div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 6 }}>
            Full evidence capture, validation and package finalization surface.
          </div>
          <Link to={`/nextgen/missions/${m.canonical_id}/evidence`} className="nx-btn" style={{ marginTop: 18 }} data-testid="nx-mission-open-evidence">
            Open Evidence <ArrowUpRight size={15} />
          </Link>
        </div>
      )}

      {tab === "intelligence" && (
        <div className="nx-card" style={{ padding: 40, textAlign: "center" }} data-testid="nx-mission-intelligence-panel">
          <Cpu size={40} strokeWidth={1.4} color="var(--nx-cyan)" style={{ opacity: 0.7 }} />
          <div style={{ marginTop: 14, color: "#fff", fontSize: 16, fontWeight: 600 }}>Property Intelligence</div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 6 }}>
            Findings drafted from approved evidence · reviewed under Blueprint tiers.
          </div>
          <Link to={`/nextgen/missions/${m.canonical_id}/intelligence`} className="nx-btn" style={{ marginTop: 18 }} data-testid="nx-mission-open-intelligence">
            Open Intelligence <ArrowUpRight size={15} />
          </Link>
        </div>
      )}

      {tab === "timeline" && (
        <div className="nx-card">
          <div className="nx-label">Mission Timeline</div>
          <div style={{ marginTop: 12, color: "var(--nx-text-secondary)", fontSize: 13 }}>
            Created · {m.created_at.slice(0, 19).replace("T", " ")} · Current stage {m.stage}/15.
            Advance transitions are appended to the property Passport ledger.
          </div>
          <Link to="/nextgen/passport" className="nx-btn ghost small" style={{ marginTop: 12 }} data-testid="nx-mission-open-passport">
            Open Passport <ArrowUpRight size={13} />
          </Link>
        </div>
      )}

      <MissionDetailStyles />
    </div>
  );
}

function ChecklistRow({ icon, label, value, ok }) {
  return (
    <div className="nx-checklist-row" data-testid={`nx-check-${label.toLowerCase()}`}>
      <span className="ico" style={{ color: ok ? "var(--nx-success)" : "var(--nx-text-muted)" }}>{icon}</span>
      <span className="k">{label}</span>
      <span className={`v ${ok ? "ok" : ""}`}>{value}</span>
    </div>
  );
}

function MissionDetailStyles() {
  return (
    <style>{`
      .nx-mission-command-grid {
        display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
      }
      .nx-mission-checklist {
        display: flex; flex-direction: column; gap: 8px;
        border-left: 1px solid var(--nx-border);
        padding-left: 20px;
      }
      .nx-checklist-row {
        display: grid; grid-template-columns: 22px 1fr auto; gap: 10px;
        align-items: center; padding: 8px 0;
      }
      .nx-checklist-row .k {
        font-family: var(--nx-font-tech); font-size: 11px;
        color: var(--nx-text-secondary); letter-spacing: 0.24em; text-transform: uppercase;
      }
      .nx-checklist-row .v {
        font-family: var(--nx-font-tech); font-size: 11px;
        color: var(--nx-text-muted); letter-spacing: 0.18em; text-transform: uppercase;
      }
      .nx-checklist-row .v.ok { color: var(--nx-success); }
      .nx-mission-command-actions {
        display: flex; gap: 10px; flex-wrap: wrap; margin-top: 20px;
        padding-top: 16px; border-top: 1px solid var(--nx-border);
      }
      .nx-mission-tabs {
        display: flex; gap: 4px; margin: 22px 0 14px 0;
        border-bottom: 1px solid var(--nx-border); overflow-x: auto;
      }
      .nx-mission-tab {
        padding: 12px 16px; background: transparent; border: none;
        color: var(--nx-text-muted);
        font-family: var(--nx-font-tech); font-size: 11px;
        letter-spacing: 0.24em; text-transform: uppercase;
        cursor: pointer; border-bottom: 2px solid transparent;
        min-height: 44px; white-space: nowrap;
      }
      .nx-mission-tab.active { color: #fff; border-bottom-color: var(--nx-cyan); }
      .nx-mission-tab:hover { color: var(--nx-text); }
      @media (max-width: 820px) {
        .nx-mission-command-grid { grid-template-columns: 1fr; gap: 18px; }
        .nx-mission-checklist { border-left: none; border-top: 1px solid var(--nx-border); padding-left: 0; padding-top: 14px; }
      }
    `}</style>
  );
}

/* Route wrapper */
export function MissionDetailRoute() {
  const { id } = useParams();
  if (!id) return null;
  return <MissionDetail id={id} />;
}
