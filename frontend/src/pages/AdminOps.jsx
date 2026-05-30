/**
 * /admin/ops — STRATEX™ Supplier Ops Command
 *
 * Three operational surfaces for the roofing-material supplier (platform tenant)
 * who offers STRATEX to their contractor customers:
 *
 *   1. Fleet Allocation       — assign drone hardware nodes to contractor leads
 *   2. Supplier Material Catalog — global SKU ledger with Tier 1/2/3 wholesale pricing
 *   3. Account Coverage       — sales reps, monthly quotas vs realized volume,
 *                               + the softened Sales Strategy Playbook
 *
 * Aesthetic: locked PBR Luxury-Corporate (electric teal #00F5D4, neon orange #FF5400,
 * metallic nickel #3A4350).
 */
import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Radar, Layers, Users, Trash2, Pencil, Save, X, Plus, Send, Truck,
  Lock, ChevronRight, BookOpen, TrendingUp, AlertTriangle, BarChart3,
} from "lucide-react";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";

const TIERS = [
  { id: "tier1", label: "Tier 1 · Builder" },
  { id: "tier2", label: "Tier 2 · Volume" },
  { id: "tier3", label: "Tier 3 · Enterprise" },
];

const SECTIONS = [
  { id: "fleet",    label: "Fleet Allocation",   icon: Radar },
  { id: "catalog",  label: "Material Catalog",   icon: Layers },
  { id: "accounts", label: "Account Coverage",   icon: Users },
  { id: "forecast", label: "SKU Forecast",       icon: BarChart3 },
];

const fmtMoney = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD",
    minimumFractionDigits: Number.isInteger(n) ? 0 : 2 }).format(Number(n || 0));

// ---------------------------------------------------------------------------
// Shared atoms
// ---------------------------------------------------------------------------
const Panel = ({ title, right, span = 12, children, testid }) => (
  <div
    data-testid={testid}
    style={{
      gridColumn: `span ${span}`,
      background: "#10141D",
      border: `1px solid ${NICKEL}55`,
      borderRadius: 6,
      padding: "1.75rem",
      position: "relative",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
    }}>
    <div style={{
      position: "absolute", top: 0, left: 0, right: 0, height: 2,
      background: `linear-gradient(90deg, transparent, ${TEAL}, transparent)`, opacity: 0.35,
    }} />
    <div className="flex items-center justify-between mb-5">
      <h3 className="font-heading text-[15px] uppercase tracking-[0.18em] text-silver">{title}</h3>
      {right}
    </div>
    {children}
  </div>
);

const Badge = ({ children, color = NICKEL, testid }) => (
  <span data-testid={testid}
    style={{
      display: "inline-flex", padding: "0.2rem 0.55rem", borderRadius: 3,
      fontSize: 10, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase",
      background: `${color}1A`, border: `1px solid ${color}55`, color,
    }}>
    {children}
  </span>
);

const TextInput = (props) => (
  <input {...props}
    className="bg-obsidian/80 border border-[#3A4350]/60 rounded px-3 py-2 text-silver text-sm focus:border-[#00F5D4] focus:shadow-[0_0_10px_rgba(0,245,212,0.2)] outline-none w-full font-mono"
  />
);

const Select = (props) => (
  <select {...props}
    className="bg-obsidian/80 border border-[#3A4350]/60 rounded px-3 py-2 text-silver text-sm focus:border-[#00F5D4] focus:shadow-[0_0_10px_rgba(0,245,212,0.2)] outline-none w-full font-mono"
  />
);

const Btn = ({ orange, ghost, disabled, children, ...rest }) => {
  const c = orange ? ORANGE : TEAL;
  return (
    <button
      {...rest} disabled={disabled}
      style={{
        background: ghost ? "transparent" : `${c}15`,
        border: `1px solid ${c}`, color: c,
        padding: "0.6rem 1rem", borderRadius: 4,
        fontSize: 11, fontWeight: 700, letterSpacing: "0.18em",
        textTransform: "uppercase", cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.4 : 1, transition: "all 0.18s ease",
        display: "inline-flex", alignItems: "center", gap: 8,
      }}
      onMouseEnter={(e) => !disabled && (e.currentTarget.style.boxShadow = `0 0 12px ${c}55`)}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
    >
      {children}
    </button>
  );
};

// ---------------------------------------------------------------------------
// Section 1 — Fleet Allocation
// ---------------------------------------------------------------------------
function FleetAllocationView({ dashboard, refresh }) {
  const { hardware_nodes = [], contractors = [], summary = {} } = dashboard;

  const [contractorId, setContractorId] = useState("");
  const [jobId, setJobId] = useState("");
  const [nodeId, setNodeId] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const availableLeads = useMemo(() => {
    const c = contractors.find((x) => x.id === contractorId);
    return (c?.leads || []).filter((l) => !l.assigned_node_id);
  }, [contractors, contractorId]);

  const availableNodes = hardware_nodes.filter((n) => n.status === "available" && !n.assigned_job_id);

  async function assign(e) {
    e.preventDefault();
    if (!nodeId || !jobId) return;
    setSubmitting(true);
    try {
      await api.post("/admin/ops/hardware-nodes/assign", { node_id: nodeId, job_id: jobId });
      toast.success(`Node assigned · intercept route initialized`);
      setContractorId(""); setJobId(""); setNodeId("");
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Assignment failed");
    } finally {
      setSubmitting(false);
    }
  }

  async function releaseNode(nid) {
    if (!window.confirm(`Release node ${nid}? Its current job will be unassigned.`)) return;
    try {
      await api.post(`/admin/ops/hardware-nodes/${nid}/release`);
      toast.success(`Node ${nid} released back to fleet pool`);
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Release failed");
    }
  }

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Stat strip */}
      <Panel title="Fleet Snapshot" span={12} testid="fleet-snapshot">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Contractor Accounts",  value: summary.contractor_count ?? "—" },
            { label: "Open Lead Vectors",    value: summary.lead_count ?? "—" },
            { label: "Nodes Available",      value: summary.node_available ?? "—",  color: TEAL },
            { label: "Nodes Total",          value: summary.node_total ?? "—" },
          ].map((s) => (
            <div key={s.label}
              style={{ background: "#0A0F12", borderLeft: `3px solid ${s.color || TEAL}`, padding: "1rem", borderRadius: "0 4px 4px 0" }}>
              <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{s.label}</div>
              <div className="text-2xl font-bold font-mono text-silver mt-1">{s.value}</div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Routing Engine */}
      <Panel title="Node Routing Engine" span={5} testid="fleet-routing-engine">
        <form onSubmit={assign} className="space-y-4">
          <div>
            <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">
              Target Contractor Profile
            </label>
            <Select value={contractorId} onChange={(e) => { setContractorId(e.target.value); setJobId(""); }} required
              data-testid="fleet-contractor-select">
              <option value="">Select contractor…</option>
              {contractors.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.company_name || c.email} {c.lead_count ? `· ${c.lead_count} open lead${c.lead_count > 1 ? "s" : ""}` : "· no open leads"}
                </option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">
              Target Address Vector
            </label>
            <Select value={jobId} onChange={(e) => setJobId(e.target.value)} required disabled={!contractorId}
              data-testid="fleet-lead-select">
              <option value="">{contractorId ? (availableLeads.length ? "Select address…" : "No open leads — all assigned") : "Select contractor first"}</option>
              {availableLeads.map((l) => (
                <option key={l.job_id} value={l.job_id}>{l.address} {l.client_name && l.client_name !== "—" ? `· ${l.client_name}` : ""}</option>
              ))}
            </Select>
          </div>
          <div>
            <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">
              Hardware Node
            </label>
            <Select value={nodeId} onChange={(e) => setNodeId(e.target.value)} required
              data-testid="fleet-node-select">
              <option value="">{availableNodes.length ? "Select unassigned node…" : "No nodes available"}</option>
              {availableNodes.map((n) => (
                <option key={n.id} value={n.id}>{n.label} · {n.dock_address}</option>
              ))}
            </Select>
          </div>
          <Btn type="submit" disabled={submitting || !nodeId || !jobId}
            data-testid="fleet-assign-submit">
            <Send size={14} /> Initialize Intercept Route
          </Btn>
        </form>
      </Panel>

      {/* Contractor Target Matrix */}
      <Panel title="Contractor Target Matrix" span={7} testid="fleet-target-matrix">
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-left font-mono">
            <thead>
              <tr className="border-b-2 border-white/5">
                {["Contractor", "Sales Rep", "Open Leads (by address)"].map((h) => (
                  <th key={h} className="px-3 py-3 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contractors.map((c) => {
                const rep = (dashboard.sales_reps || []).find((r) => r.id === c.assigned_rep_id);
                return (
                  <tr key={c.id} className="border-b border-white/5 hover:bg-white/[0.02]">
                    <td className="px-3 py-3 text-silver text-sm">
                      <div className="font-semibold">{c.company_name || c.email}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{c.email}</div>
                    </td>
                    <td className="px-3 py-3 text-sm">
                      {rep
                        ? <Badge color={TEAL} testid={`fleet-rep-${c.id}`}>{rep.name}</Badge>
                        : <Badge color={NICKEL}>Unassigned</Badge>}
                    </td>
                    <td className="px-3 py-3 text-sm">
                      {(c.leads || []).length === 0
                        ? <span className="text-slate-500 text-xs">No open leads</span>
                        : (
                          <ul className="space-y-1.5">
                            {c.leads.map((l) => (
                              <li key={l.job_id}
                                className="flex items-center justify-between gap-3 px-3 py-2 rounded-r"
                                style={{
                                  background: l.assigned_node_id ? "rgba(255,84,0,0.04)" : "rgba(255,255,255,0.02)",
                                  borderLeft: `2px solid ${l.assigned_node_id ? ORANGE : NICKEL}`,
                                }}>
                                <span className="text-silver text-xs">{l.address}</span>
                                {l.assigned_node_id
                                  ? (
                                    <button onClick={() => releaseNode(l.assigned_node_id)}
                                      className="cursor-pointer"
                                      data-testid={`fleet-release-${l.assigned_node_id}`}>
                                      <Badge color={ORANGE}>{(hardware_nodes.find(n => n.id === l.assigned_node_id) || {}).label || l.assigned_node_id}</Badge>
                                    </button>
                                  )
                                  : <Badge color={NICKEL}>Unassigned</Badge>}
                              </li>
                            ))}
                          </ul>
                        )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Hardware Node fleet listing */}
      <Panel title="Hardware Node Fleet" span={12} testid="fleet-node-list">
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {hardware_nodes.map((n) => (
            <div key={n.id}
              data-testid={`fleet-node-card-${n.id}`}
              style={{
                background: "#0A0F12", padding: "1rem", borderRadius: 4,
                border: `1px solid ${n.status === "available" ? `${TEAL}55` : n.status === "assigned" ? `${ORANGE}55` : `${NICKEL}55`}`,
              }}>
              <div className="flex items-center justify-between mb-2">
                <Truck size={14} color={n.status === "available" ? TEAL : n.status === "assigned" ? ORANGE : NICKEL} />
                <Badge color={n.status === "available" ? TEAL : n.status === "assigned" ? ORANGE : NICKEL}>{n.status}</Badge>
              </div>
              <div className="text-[11px] tracking-[0.18em] uppercase text-silver font-heading font-bold">{n.label}</div>
              <div className="text-[10px] text-slate-500 mt-1">{n.dock_address}</div>
              {n.assigned_job_id && (
                <div className="text-[10px] text-[#FF5400] mt-2 font-mono">→ {n.assigned_job_id}</div>
              )}
            </div>
          ))}
        </div>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 2 — Supplier Material Catalog
// ---------------------------------------------------------------------------
const BLANK_MATERIAL = {
  sku: "", name: "", category: "Shingles", unit_label: "Each",
  stock_units: 0, tier1_usd: 0, tier2_usd: 0, tier3_usd: 0,
};

function MaterialCatalogView({ dashboard, refresh }) {
  const { materials = [] } = dashboard;
  const [editId, setEditId] = useState(null);
  const [draft, setDraft] = useState(BLANK_MATERIAL);
  const [adding, setAdding] = useState(false);

  function startEdit(m) {
    setEditId(m.id);
    setDraft({ ...m });
    setAdding(false);
  }
  function startAdd() {
    setEditId(null);
    setDraft({ ...BLANK_MATERIAL });
    setAdding(true);
  }
  function cancel() { setEditId(null); setAdding(false); setDraft(BLANK_MATERIAL); }

  async function save() {
    try {
      if (adding) {
        await api.post("/admin/ops/materials", draft);
        toast.success(`Added ${draft.name} to ledger`);
      } else {
        await api.put(`/admin/ops/materials/${editId}`, draft);
        toast.success(`Updated ${draft.name}`);
      }
      cancel();
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Save failed");
    }
  }
  async function purge(m) {
    if (!window.confirm(`Purge "${m.name}" from the ledger? This cannot be undone.`)) return;
    try {
      await api.delete(`/admin/ops/materials/${m.id}`);
      toast.success(`Purged ${m.name}`);
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Delete failed");
    }
  }

  const editing = !!editId || adding;
  const editingRowId = adding ? "__new__" : editId;

  return (
    <div className="grid grid-cols-12 gap-6">
      <Panel title="Supplier Material Ledger"
        right={!editing && (
          <Btn orange onClick={startAdd} data-testid="catalog-add-btn"><Plus size={14}/> Add Line Item</Btn>
        )}
        testid="catalog-panel">
        <p className="text-xs text-slate-400 mb-4 max-w-3xl leading-relaxed">
          Supplier-owned wholesale catalog. Each contractor account is assigned a tier
          (set on the <span className="text-[#00F5D4]">Account Coverage</span> tab); the matrix below is what the contractor sees
          at <span className="text-[#00F5D4]">their</span> tier when ordering through STRATEX.
        </p>
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b-2 border-white/5">
                {["SKU · Material", "Stock", "Tier 1 · Builder", "Tier 2 · Volume", "Tier 3 · Enterprise", "Controls"]
                  .map((h, i) => (
                    <th key={h} className={`px-3 py-3 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading ${i === 5 ? "text-right" : ""}`}>{h}</th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {adding && (
                <MaterialEditRow draft={draft} setDraft={setDraft} save={save} cancel={cancel} adding />
              )}
              {materials.map((m) => editingRowId === m.id ? (
                <MaterialEditRow key={m.id} draft={draft} setDraft={setDraft} save={save} cancel={cancel} />
              ) : (
                <tr key={m.id} className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`catalog-row-${m.id}`}>
                  <td className="px-3 py-3">
                    <div className="text-silver text-sm font-semibold">{m.name}</div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">{m.sku} · {m.category}</div>
                  </td>
                  <td className="px-3 py-3"><Badge color={NICKEL}>{m.stock_units} {m.unit_label}{m.stock_units !== 1 ? "s" : ""}</Badge></td>
                  <td className="px-3 py-3 text-slate-400 font-mono text-sm">{fmtMoney(m.tier1_usd)}</td>
                  <td className="px-3 py-3 text-[#00F5D4] font-mono text-sm">{fmtMoney(m.tier2_usd)}</td>
                  <td className="px-3 py-3 text-[#FF5400] font-mono text-sm font-bold">{fmtMoney(m.tier3_usd)}</td>
                  <td className="px-3 py-3 text-right space-x-2">
                    <button onClick={() => startEdit(m)} disabled={editing}
                      className="text-[#00F5D4] text-[10px] uppercase tracking-[0.18em] font-heading font-bold hover:opacity-80 disabled:opacity-30"
                      data-testid={`catalog-edit-${m.id}`}><Pencil size={11} className="inline mr-1"/>Edit</button>
                    <button onClick={() => purge(m)} disabled={editing}
                      className="text-red-500 text-[10px] uppercase tracking-[0.18em] font-heading font-bold hover:opacity-80 disabled:opacity-30"
                      data-testid={`catalog-purge-${m.id}`}><Trash2 size={11} className="inline mr-1"/>Purge</button>
                  </td>
                </tr>
              ))}
              {materials.length === 0 && !adding && (
                <tr><td colSpan={6} className="px-3 py-8 text-center text-slate-500 text-sm">No materials. Add one to begin.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

function MaterialEditRow({ draft, setDraft, save, cancel, adding }) {
  const ip = (k, type = "text") => (
    <TextInput type={type} value={draft[k] ?? ""}
      onChange={(e) => setDraft({ ...draft, [k]: type === "number" ? parseFloat(e.target.value) || 0 : e.target.value })}
      data-testid={`catalog-input-${k}`}
    />
  );
  return (
    <tr className="border-b border-[#00F5D4]/30 bg-[#00F5D4]/[0.02]" data-testid={adding ? "catalog-add-row" : "catalog-edit-row"}>
      <td className="px-3 py-3 space-y-2">
        {ip("name")}
        <div className="grid grid-cols-2 gap-2">{ip("sku")}{ip("category")}</div>
      </td>
      <td className="px-3 py-3 space-y-2">
        {ip("stock_units", "number")}
        {ip("unit_label")}
      </td>
      <td className="px-3 py-3">{ip("tier1_usd", "number")}</td>
      <td className="px-3 py-3">{ip("tier2_usd", "number")}</td>
      <td className="px-3 py-3">{ip("tier3_usd", "number")}</td>
      <td className="px-3 py-3 text-right space-y-2">
        <Btn onClick={save} data-testid="catalog-save-btn"><Save size={12}/>Save</Btn>
        <Btn ghost orange onClick={cancel} data-testid="catalog-cancel-btn"><X size={12}/>Cancel</Btn>
      </td>
    </tr>
  );
}

// ---------------------------------------------------------------------------
// Section 3 — Account Coverage
// ---------------------------------------------------------------------------
function AccountCoverageView({ dashboard, refresh, playbook }) {
  const { sales_reps = [], contractors = [] } = dashboard;
  const [showAddRep, setShowAddRep] = useState(false);
  const [newRep, setNewRep] = useState({ name: "", email: "", monthly_quota_usd: 250000, territory: "" });

  async function addRep(e) {
    e.preventDefault();
    if (!newRep.name) return;
    try {
      await api.post("/admin/ops/sales-reps", newRep);
      toast.success(`Deployed sales operative: ${newRep.name}`);
      setNewRep({ name: "", email: "", monthly_quota_usd: 250000, territory: "" });
      setShowAddRep(false);
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to add rep");
    }
  }

  async function updateTier(contractor_id, tier) {
    try {
      await api.put(`/admin/ops/contractors/${contractor_id}/tier`, { tier });
      toast.success(`Tier updated`);
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  }
  async function updateRep(contractor_id, rep_id) {
    try {
      await api.put(`/admin/ops/contractors/${contractor_id}/rep`, { rep_id });
      toast.success(`Rep reassigned`);
      await refresh();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed");
    }
  }

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Sales Strategy Playbook */}
      <Panel title="Sales Strategy Playbook" span={12} testid="playbook-panel"
        right={<Badge color={ORANGE}><BookOpen size={10} className="inline mr-1"/>v1.0</Badge>}>
        <div className="space-y-4">
          {playbook.map((p) => (
            <div key={p.code}
              className="flex gap-4 p-4 rounded border border-white/5"
              style={{ background: "rgba(255,255,255,0.01)" }}
              data-testid={`playbook-${p.code.replace(/[^a-z0-9]/gi, "-")}`}>
              <span className="text-[#FF5400] font-mono font-bold text-xs whitespace-nowrap tracking-[0.15em]">{p.code}</span>
              <div>
                <div className="text-silver font-heading text-sm font-bold tracking-wide mb-1.5">{p.title}</div>
                <div className="text-xs text-slate-400 leading-relaxed">{p.body}</div>
              </div>
            </div>
          ))}
        </div>
      </Panel>

      {/* Sales Reps with progress bars */}
      <Panel title="Sales Force Real-Time Telemetry" span={12} testid="reps-panel"
        right={
          !showAddRep
            ? <Btn orange onClick={() => setShowAddRep(true)} data-testid="reps-add-toggle"><Plus size={14}/>Deploy Rep</Btn>
            : <Btn ghost onClick={() => setShowAddRep(false)}><X size={14}/>Cancel</Btn>
        }>
        {showAddRep && (
          <form onSubmit={addRep} className="grid grid-cols-1 md:grid-cols-5 gap-3 mb-5 p-4 rounded border border-[#FF5400]/30 bg-[#FF5400]/[0.03]" data-testid="reps-add-form">
            <TextInput placeholder="Full name" value={newRep.name}
              onChange={(e) => setNewRep({ ...newRep, name: e.target.value })} required data-testid="reps-add-name"/>
            <TextInput placeholder="email@stratex.io" value={newRep.email}
              onChange={(e) => setNewRep({ ...newRep, email: e.target.value })} data-testid="reps-add-email"/>
            <TextInput placeholder="Territory" value={newRep.territory}
              onChange={(e) => setNewRep({ ...newRep, territory: e.target.value })} data-testid="reps-add-territory"/>
            <TextInput type="number" placeholder="Monthly quota ($)" value={newRep.monthly_quota_usd}
              onChange={(e) => setNewRep({ ...newRep, monthly_quota_usd: parseFloat(e.target.value) || 0 })} data-testid="reps-add-quota"/>
            <Btn orange type="submit" data-testid="reps-add-submit"><Send size={14}/>Deploy</Btn>
          </form>
        )}
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b-2 border-white/5">
                {["Representative", "MTD Volume", "Quota", "Velocity", "Account Coverage"].map((h) => (
                  <th key={h} className="px-3 py-3 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {sales_reps.map((r) => {
                const vel = r.monthly_quota_usd > 0 ? (r.current_volume_usd / r.monthly_quota_usd) * 100 : 0;
                const accounts = contractors.filter((c) => c.assigned_rep_id === r.id);
                return (
                  <tr key={r.id} className="border-b border-white/5" data-testid={`rep-row-${r.id}`}>
                    <td className="px-3 py-4">
                      <div className="font-bold text-silver text-sm">{r.name}</div>
                      <div className="text-[10px] text-slate-500 mt-0.5">{r.territory || r.email}</div>
                    </td>
                    <td className="px-3 py-4 font-mono text-silver text-sm">{fmtMoney(r.current_volume_usd)}</td>
                    <td className="px-3 py-4 font-mono text-slate-400 text-sm">{fmtMoney(r.monthly_quota_usd)}</td>
                    <td className="px-3 py-4 min-w-[180px]">
                      <div className="text-xs font-mono mb-1">{vel.toFixed(1)}%</div>
                      <div className="w-full h-1 rounded bg-white/5 overflow-hidden">
                        <div style={{
                          width: `${Math.min(vel, 100)}%`, height: "100%",
                          background: `linear-gradient(90deg, ${ORANGE}, ${TEAL})`,
                        }}/>
                      </div>
                    </td>
                    <td className="px-3 py-4">
                      {accounts.length === 0
                        ? <span className="text-slate-500 text-xs">No accounts assigned</span>
                        : (
                          <div className="flex flex-wrap gap-1.5">
                            {accounts.map((a) => <Badge key={a.id} color={TEAL}>{a.company_name || a.email}</Badge>)}
                          </div>
                        )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Panel>

      {/* Contractor → tier/rep mapping */}
      <Panel title="Contractor Account Configuration" span={12} testid="contractor-config-panel">
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b-2 border-white/5">
                {["Contractor", "Assigned Tier", "Assigned Rep", "Subscription"].map((h) => (
                  <th key={h} className="px-3 py-3 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {contractors.map((c) => (
                <tr key={c.id} className="border-b border-white/5" data-testid={`contractor-config-${c.id}`}>
                  <td className="px-3 py-4">
                    <div className="font-bold text-silver text-sm">{c.company_name || c.email}</div>
                    <div className="text-[10px] text-slate-500 font-mono mt-0.5">{c.email}</div>
                  </td>
                  <td className="px-3 py-4">
                    <Select value={c.assigned_tier || ""} onChange={(e) => updateTier(c.id, e.target.value)}
                      data-testid={`tier-select-${c.id}`} style={{ width: "auto", padding: "0.35rem 0.6rem", fontSize: 12 }}>
                      <option value="">— select tier —</option>
                      {TIERS.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
                    </Select>
                  </td>
                  <td className="px-3 py-4">
                    <Select value={c.assigned_rep_id || ""} onChange={(e) => updateRep(c.id, e.target.value)}
                      data-testid={`rep-select-${c.id}`} style={{ width: "auto", padding: "0.35rem 0.6rem", fontSize: 12 }}>
                      <option value="">— select rep —</option>
                      {sales_reps.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                    </Select>
                  </td>
                  <td className="px-3 py-4">
                    {c.subscription_status === "active"
                      ? <Badge color={TEAL}>{c.subscription_tier || "active"}</Badge>
                      : <Badge color={NICKEL}>{c.subscription_status || "—"}</Badge>}
                  </td>
                </tr>
              ))}
              {contractors.length === 0 && (
                <tr><td colSpan={4} className="px-3 py-8 text-center text-slate-500 text-sm">No contractor accounts.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section 4 — SKU Forecast (supplier-side demand intelligence)
// ---------------------------------------------------------------------------
function SkuForecastView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function load() {
    setLoading(true);
    try {
      const r = await api.get("/admin/ops/sku-forecast");
      setData(r.data);
      setErr("");
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-8 text-center text-slate-400 font-mono text-sm">// Computing forecast…</div>;
  if (err) return <div className="p-8 text-center text-[#FF5400] font-mono text-sm">// {err}</div>;

  const summary = data?.summary || {};
  const rows = data?.rows || [];
  const maxValue = Math.max(...rows.map((r) => r.quote_value_usd), 1);

  return (
    <div className="grid grid-cols-12 gap-6">
      {/* Stat strip */}
      <Panel title="Forecast Snapshot" span={12} testid="forecast-snapshot">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: "Total SKUs",               value: summary.total_skus ?? "—" },
            { label: "SKUs with demand",         value: summary.skus_with_demand ?? "—", color: TEAL },
            { label: "Reorder alerts",           value: summary.reorder_alerts ?? 0, color: (summary.reorder_alerts ?? 0) > 0 ? ORANGE : NICKEL },
            { label: "Forecast Value · 30d",     value: fmtMoney(summary.total_forecast_value_usd || 0), color: TEAL },
          ].map((s) => (
            <div key={s.label}
              style={{ background: "#0A0F12", borderLeft: `3px solid ${s.color || TEAL}`, padding: "1rem", borderRadius: "0 4px 4px 0" }}>
              <div className="text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{s.label}</div>
              <div className="text-2xl font-bold font-mono text-silver mt-1">{s.value}</div>
            </div>
          ))}
        </div>
      </Panel>

      <Panel title="Per-SKU Demand · Pending Quotes" span={12} testid="forecast-table"
        right={<Badge color={ORANGE}><TrendingUp size={11} className="inline mr-1"/>Live Aggregation</Badge>}>
        <p className="text-xs text-slate-400 mb-4 max-w-3xl leading-relaxed">
          Aggregates every draft + promoted quote across all contractors. The forecast
          quantity is what's <span className="text-[#00F5D4]">committed but not yet ordered</span> — your forward
          stock signal. Reorder alert fires when current stock covers less than 14 days
          at the current burn rate.
        </p>
        <div style={{ overflowX: "auto" }}>
          <table className="w-full text-left">
            <thead>
              <tr className="border-b-2 border-white/5">
                {["SKU · Material", "Quotes", "Forecast Qty", "Stock", "Days of Supply", "Quote Value", "Demand Distribution", ""]
                  .map((h, i) => (
                    <th key={i} className={`px-3 py-3 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading ${i === 7 ? "text-right" : ""}`}>{h}</th>
                  ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const widthPct = Math.min(100, (r.quote_value_usd / maxValue) * 100);
                const dosColor = r.reorder_signal ? ORANGE : r.days_of_supply == null ? NICKEL : TEAL;
                return (
                  <tr key={r.material_id} className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`forecast-row-${r.material_id}`}>
                    <td className="px-3 py-3">
                      <div className="text-silver text-sm font-semibold">{r.name}</div>
                      <div className="text-[10px] text-slate-500 font-mono mt-0.5">{r.sku} · {r.category}</div>
                    </td>
                    <td className="px-3 py-3"><Badge color={r.quote_count > 0 ? TEAL : NICKEL}>{r.quote_count}</Badge></td>
                    <td className="px-3 py-3 font-mono text-sm text-[#00F5D4]">{r.qty_demanded}<span className="text-slate-500 text-[10px] ml-1">{r.unit_label}{r.qty_demanded !== 1 ? "s" : ""}</span></td>
                    <td className="px-3 py-3 font-mono text-sm text-slate-400">{r.stock_units}</td>
                    <td className="px-3 py-3">
                      {r.days_of_supply == null
                        ? <span className="text-slate-500 text-xs">—</span>
                        : <Badge color={dosColor}>{r.days_of_supply}d</Badge>}
                    </td>
                    <td className="px-3 py-3 font-mono text-sm text-silver">{fmtMoney(r.quote_value_usd)}</td>
                    <td className="px-3 py-3 min-w-[180px]">
                      <div className="w-full h-1 rounded bg-white/5 overflow-hidden">
                        <div style={{
                          width: `${widthPct}%`, height: "100%",
                          background: r.reorder_signal ? ORANGE : `linear-gradient(90deg, ${NICKEL}, ${TEAL})`,
                        }}/>
                      </div>
                      <div className="text-[10px] text-slate-500 mt-1 font-mono">
                        T1:{r.tier_breakdown.tier1} · T2:{r.tier_breakdown.tier2} · T3:{r.tier_breakdown.tier3}
                      </div>
                    </td>
                    <td className="px-3 py-3 text-right">
                      {r.reorder_signal && (
                        <Badge color={ORANGE} testid={`forecast-reorder-${r.material_id}`}>
                          <AlertTriangle size={10} className="inline mr-1"/>Reorder
                        </Badge>
                      )}
                    </td>
                  </tr>
                );
              })}
              {rows.length === 0 && (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500 text-sm">No materials in ledger.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page shell
// ---------------------------------------------------------------------------
export default function AdminOps() {
  const [section, setSection] = useState("fleet");
  const [dashboard, setDashboard] = useState(null);
  const [playbook, setPlaybook] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");

  async function load() {
    try {
      const [d, p] = await Promise.all([
        api.get("/admin/ops/dashboard"),
        api.get("/admin/ops/playbook"),
      ]);
      setDashboard(d.data);
      setPlaybook(p.data.playbook || []);
      setErr("");
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  if (loading) return <div className="p-12 text-center text-slate-400 font-mono text-sm">// Loading ops dashboard…</div>;
  if (err) return <div className="p-12 text-center text-[#FF5400] font-mono text-sm">// Error: {err}</div>;

  const activeSection = SECTIONS.find((s) => s.id === section);
  const ActiveIcon = activeSection?.icon || Radar;

  return (
    <div className="min-h-screen bg-obsidian">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        {/* Header */}
        <div className="border-b border-white/5 pb-6 mb-8 flex items-end justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-[#00F5D4] font-heading font-semibold">
              <Lock size={12}/> Stratex Engine · Admin Operations
            </div>
            <h1 className="text-4xl md:text-5xl font-heading font-bold tracking-tight text-silver mt-2"
              style={{ background: "linear-gradient(135deg, #FFFFFF 0%, #94a3b8 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Ops Command
            </h1>
            <p className="text-sm text-slate-400 mt-2 max-w-2xl leading-relaxed">
              The supplier control room: assign drone fleet to contractor leads,
              manage the global material catalog with tiered pricing, and steer
              your sales team's account coverage.
            </p>
          </div>
          <Badge color={TEAL} testid="ops-active-section">
            <ActiveIcon size={11} className="inline mr-1.5"/>{activeSection?.label}
          </Badge>
        </div>

        {/* Inner tab nav */}
        <nav className="flex gap-2 mb-8" data-testid="ops-tabs">
          {SECTIONS.map((s) => {
            const Icon = s.icon;
            const active = s.id === section;
            return (
              <button key={s.id} onClick={() => setSection(s.id)}
                data-testid={`ops-tab-${s.id}`}
                style={{
                  display: "flex", alignItems: "center", gap: 8,
                  padding: "0.75rem 1.25rem", borderRadius: 4, cursor: "pointer",
                  background: active ? `${TEAL}10` : "transparent",
                  border: `1px solid ${active ? TEAL : NICKEL + "55"}`,
                  color: active ? TEAL : "#94a3b8",
                  fontSize: 11, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase",
                  fontFamily: "var(--font-heading, sans-serif)",
                  boxShadow: active ? `0 0 16px ${TEAL}33` : "none",
                  borderLeft: active ? `3px solid ${TEAL}` : `1px solid ${NICKEL}55`,
                }}>
                <Icon size={13}/>
                {s.label}
                {active && <ChevronRight size={11}/>}
              </button>
            );
          })}
        </nav>

        {/* Section views */}
        {section === "fleet"    && <FleetAllocationView   dashboard={dashboard} refresh={load}/>}
        {section === "catalog"  && <MaterialCatalogView   dashboard={dashboard} refresh={load}/>}
        {section === "accounts" && <AccountCoverageView   dashboard={dashboard} refresh={load} playbook={playbook}/>}
        {section === "forecast" && <SkuForecastView/>}
      </div>
    </div>
  );
}
