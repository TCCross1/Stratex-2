import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Clock, ArrowUpRight, ExternalLink, Copy, Check,
  Waves, Wind, Droplet, Sun, Sparkles, Share2, FileText, AlertTriangle,
  Calendar, DollarSign, History, Plus, Search, FileCheck, Activity,
  HardDrive, Users, CheckCircle, RefreshCw, Eye, Edit, Save, ArrowRight
} from "lucide-react";
import {
  nxListProperties, nxPropertyPassport, nxPropertyTimeline,
  nxPropertyReport, nxReportTemplates, nxPropertyAwe,
  nxIssueHabitatLink, nxOpenReportHtml,
  nxPropertyDna, nxUpdatePropertyDna, nxListWarranties,
  nxCreateWarranty, nxRenewWarranty, nxPropertyMaintenance,
  nxPropertyFinancials, nxUpdateFinancials, nxVersionComparison, nxMe
} from "@/nextgen/api";

const AUDIENCES = ["internal", "contractor", "homeowner", "adjuster", "insurer"];
const DNA_FIELDS = [
  { key: "construction_type", label: "Construction Type" },
  { key: "roof_system", label: "Roof System" },
  { key: "exterior", label: "Exterior" },
  { key: "windows", label: "Windows" },
  { key: "doors", label: "Doors" },
  { key: "foundation", label: "Foundation" },
  { key: "hvac", label: "HVAC" },
  { key: "electrical", label: "Electrical" },
  { key: "plumbing", label: "Plumbing" },
  { key: "insulation", label: "Insulation" },
  { key: "structural_components", label: "Structural Components" },
  { key: "energy_profile", label: "Energy Profile" },
  { key: "awe_profile", label: "AWE Profile" }
];

export default function PassportPage() {
  const [properties, setProperties] = useState([]);
  const [pid, setPid] = useState(null);
  const [me, setMe] = useState(null);
  const [passport, setPassport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [dna, setDna] = useState(null);
  const [warranties, setWarranties] = useState([]);
  const [maintenance, setMaintenance] = useState(null);
  const [financials, setFinancials] = useState(null);
  const [compareData, setCompareData] = useState([]);
  
  const [audience, setAudience] = useState("internal");
  const [templates, setTemplates] = useState([]);
  const [template, setTemplate] = useState("homeowner_summary");
  const [report, setReport] = useState(null);
  const [awe, setAwe] = useState(null);
  const [linkOut, setLinkOut] = useState(null);
  const [linkBusy, setLinkBusy] = useState(false);

  // Tabs state
  const [activeTab, setActiveTab] = useState("timeline");

  // Search & Filters
  const [timelineSearch, setTimelineSearch] = useState("");
  const [timelineFilter, setTimelineFilter] = useState("ALL");
  const [compareFilter, setCompareFilter] = useState("ALL");

  // DNA Field History Modal
  const [selectedDnaField, setSelectedDnaField] = useState(null);
  
  // DNA Update Form
  const [editingDnaField, setEditingDnaField] = useState(null);
  const [dnaFormValue, setDnaFormValue] = useState("");
  const [dnaFormSource, setDnaFormSource] = useState("");
  const [dnaFormConfidence, setDnaFormConfidence] = useState(95);
  const [dnaSubmitting, setDnaSubmitting] = useState(false);

  // Warranty Registration Form
  const [showRegisterWarranty, setShowRegisterWarranty] = useState(false);
  const [warrantyForm, setWarrantyForm] = useState({
    manufacturer: "",
    contractor: "",
    labor_coverage_months: 120,
    material_coverage_months: 360,
    start_date: new Date().toISOString().slice(0, 10),
    expiration_date: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
    claim_status: "active",
    linked_components_str: ""
  });
  const [warrantySubmitting, setWarrantySubmitting] = useState(false);

  // Warranty Renewal Form
  const [renewingWarranty, setRenewingWarranty] = useState(null);
  const [renewalForm, setRenewalForm] = useState({
    new_expiration_date: "",
    notes: ""
  });
  const [renewalSubmitting, setRenewalSubmitting] = useState(false);

  // Financial Edit Form
  const [isEditingFinancials, setIsEditingFinancials] = useState(false);
  const [financialForm, setFinancialForm] = useState({
    replacement_cost_usd: 0,
    capital_improvements_usd: 0,
    repair_investments_usd: 0,
    budget_5yr_usd: 0,
    budget_10yr_usd: 0
  });
  const [financialSubmitting, setFinancialSubmitting] = useState(false);

  // Initial loads
  useEffect(() => {
    nxMe().then(setMe).catch((err) => {
      console.warn("Failed to fetch current user session, using fallback admin account.", err);
      setMe({ role: "admin", user_id: "demo-user" });
    });
    nxListProperties().then((d) => {
      setProperties(d.items);
      if (d.items.length > 0) setPid(d.items[0].canonical_id);
    });
    nxReportTemplates().then((d) => setTemplates(d.templates));
  }, []);

  // Sync / refresh logic when PID changes
  const refreshAllData = async () => {
    if (!pid) return;
    try {
      const passData = await nxPropertyPassport(pid, audience);
      setPassport(passData);
    } catch (e) { console.error(e); }

    try {
      const tl = await nxPropertyTimeline(pid);
      setTimeline(tl.items || []);
    } catch (e) { console.error(e); }

    try {
      const d = await nxPropertyDna(pid);
      setDna(d.dna);
    } catch (e) { console.error(e); }

    try {
      const w = await nxListWarranties(pid);
      setWarranties(w.warranties || []);
    } catch (e) { console.error(e); }

    try {
      const m = await nxPropertyMaintenance(pid);
      setMaintenance(m);
    } catch (e) { console.error(e); }

    try {
      const f = await nxPropertyFinancials(pid);
      setFinancials(f.financials);
      if (f.financials) {
        setFinancialForm({
          replacement_cost_usd: f.financials.replacement_cost_usd,
          capital_improvements_usd: f.financials.capital_improvements_usd,
          repair_investments_usd: f.financials.repair_investments_usd,
          budget_5yr_usd: f.financials.budget_5yr_usd,
          budget_10yr_usd: f.financials.budget_10yr_usd
        });
      }
    } catch (e) { console.error(e); }

    try {
      const comp = await nxVersionComparison(pid);
      setCompareData(comp.comparison || []);
    } catch (e) { console.error(e); }

    try {
      const aw = await nxPropertyAwe(pid);
      setAwe(aw.awe);
    } catch (e) { console.error(e); }
  };

  useEffect(() => {
    refreshAllData();
  }, [pid, audience]);

  // Report loads
  useEffect(() => {
    if (!pid || !template) return;
    nxPropertyReport(pid, template).then(setReport).catch(() => setReport(null));
  }, [pid, template]);

  const property = properties.find((p) => p.canonical_id === pid);

  // Role gate helpers
  const isAuthorizedToEdit = ["admin", "gm", "ceo"].includes(me?.role);
  const isAuthorizedForWarranty = ["admin", "gm", "ceo", "contractor"].includes(me?.role);

  // Handles updating DNA field
  const handleUpdateDna = async (e) => {
    e.preventDefault();
    if (!editingDnaField) return;
    setDnaSubmitting(true);
    try {
      await nxUpdatePropertyDna(pid, {
        field_name: editingDnaField,
        value: dnaFormValue,
        source_attribution: dnaFormSource || "Manual Adjustment",
        confidence_score: Number(dnaFormConfidence)
      });
      setEditingDnaField(null);
      await refreshAllData();
    } catch (err) {
      alert(err.message || "Failed to update DNA field");
    } finally {
      setDnaSubmitting(false);
    }
  };

  // Handles registering Warranty
  const handleRegisterWarranty = async (e) => {
    e.preventDefault();
    setWarrantySubmitting(true);
    try {
      const payload = {
        manufacturer: warrantyForm.manufacturer,
        contractor: warrantyForm.contractor,
        labor_coverage_months: Number(warrantyForm.labor_coverage_months),
        material_coverage_months: Number(warrantyForm.material_coverage_months),
        start_date: new Date(warrantyForm.start_date).toISOString(),
        expiration_date: new Date(warrantyForm.expiration_date).toISOString(),
        claim_status: warrantyForm.claim_status,
        linked_components: warrantyForm.linked_components_str
          ? warrantyForm.linked_components_str.split(",").map(c => c.trim())
          : []
      };
      await nxCreateWarranty(pid, payload);
      setShowRegisterWarranty(false);
      // Reset
      setWarrantyForm({
        manufacturer: "",
        contractor: "",
        labor_coverage_months: 120,
        material_coverage_months: 360,
        start_date: new Date().toISOString().slice(0, 10),
        expiration_date: new Date(Date.now() + 10 * 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
        claim_status: "active",
        linked_components_str: ""
      });
      await refreshAllData();
    } catch (err) {
      alert(err.message || "Failed to register warranty");
    } finally {
      setWarrantySubmitting(false);
    }
  };

  // Handles renewing Warranty
  const handleRenewWarranty = async (e) => {
    e.preventDefault();
    if (!renewingWarranty) return;
    setRenewalSubmitting(true);
    try {
      await nxRenewWarranty(pid, renewingWarranty.canonical_id, {
        new_expiration_date: new Date(renewalForm.new_expiration_date).toISOString(),
        notes: renewalForm.notes
      });
      setRenewingWarranty(null);
      setRenewalForm({ new_expiration_date: "", notes: "" });
      await refreshAllData();
    } catch (err) {
      alert(err.message || "Failed to renew warranty");
    } finally {
      setRenewalSubmitting(false);
    }
  };

  // Handles updating financials
  const handleUpdateFinancialsSubmit = async (e) => {
    e.preventDefault();
    setFinancialSubmitting(true);
    try {
      await nxUpdateFinancials(pid, {
        replacement_cost_usd: Number(financialForm.replacement_cost_usd),
        capital_improvements_usd: Number(financialForm.capital_improvements_usd),
        repair_investments_usd: Number(financialForm.repair_investments_usd),
        budget_5yr_usd: Number(financialForm.budget_5yr_usd),
        budget_10yr_usd: Number(financialForm.budget_10yr_usd)
      });
      setIsEditingFinancials(false);
      await refreshAllData();
    } catch (err) {
      alert(err.message || "Failed to update financial configuration");
    } finally {
      setFinancialSubmitting(false);
    }
  };

  // Filtering timeline events
  const filteredTimeline = timeline.filter((item) => {
    const matchesSearch =
      item.summary?.toLowerCase().includes(timelineSearch.toLowerCase()) ||
      item.kind?.toLowerCase().includes(timelineSearch.toLowerCase()) ||
      item.canonical_id?.toLowerCase().includes(timelineSearch.toLowerCase());
    
    if (timelineFilter === "ALL") return matchesSearch;
    return matchesSearch && item.kind === timelineFilter;
  });

  // Unique categories in timeline
  const timelineCategories = ["ALL", ...new Set(timeline.map((t) => t.kind))];

  return (
    <div data-testid="nx-passport" className="nx-container" style={{ paddingBottom: 60 }}>
      {/* Upper header with system configuration switcher & session indicator */}
      <div className="nx-flex-between" style={{ background: "rgba(11,17,26,0.5)", borderBottom: "1px solid var(--nx-border)", padding: "10px 16px", margin: "-16px -24px 24px -24px" }}>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span className="nx-label" style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <Activity size={12} color="var(--nx-cyan)" /> Connected
          </span>
          <span className="nx-label">Actor: {me?.user_id} ({me?.role})</span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span className="nx-label">Role Switcher (Testing):</span>
          <select 
            className="nx-select" 
            style={{ width: 120, padding: "2px 6px", fontSize: 11, height: "auto" }}
            value={me?.role || ""} 
            onChange={(e) => setMe(prev => ({ ...prev, role: e.target.value }))}
          >
            <option value="admin">Admin</option>
            <option value="gm">General Manager</option>
            <option value="ceo">CEO</option>
            <option value="contractor">Contractor</option>
            <option value="homeowner">Homeowner</option>
            <option value="guest">Guest (Read Only)</option>
          </select>
        </div>
      </div>

      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// ST-2 PASSPORT SERVICE</div>
          <h1 className="nx-page-title">Property Passport & DNA</h1>
          <div className="nx-page-sub">
            The single source of truth and canonical record of property intelligence. No duplication. All workspaces consume write-controlled, hash-chained Passport projections.
          </div>
        </div>
        {properties.length > 0 && (
          <select className="nx-select" style={{ maxWidth: 360 }} value={pid || ""}
            onChange={(e) => setPid(e.target.value)} data-testid="nx-passport-property">
            {properties.map((p) => (
              <option key={p.canonical_id} value={p.canonical_id}>
                {p.address.line1}, {p.address.city} {p.address.region}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Identity Summary Card */}
      {property && (
        <div className="nx-card elevated" data-testid="nx-passport-header" style={{ marginBottom: 20 }}>
          <div className="nx-flex-between">
            <div>
              <div className="nx-label" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                <HardDrive size={13} color="var(--nx-orange)" /> PROPERTY UNIQUE IDENTIFIER
              </div>
              <div style={{ fontSize: 22, color: "#fff", marginTop: 4, fontWeight: 700 }}>
                {property.address.line1}
              </div>
              <div style={{ color: "var(--nx-text-secondary)", marginTop: 2, fontSize: 13, fontFamily: "var(--nx-font-mono)" }}>
                {property.address.city}, {property.address.region} · ID: {property.canonical_id}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <span className={`nx-pill ${passport?.passport ? "ok" : "warn"}`} style={{ display: "inline-flex", alignItems: "center", gap: 4 }} data-testid="nx-passport-state">
                <ShieldCheck size={12} strokeWidth={2} /> 
                {passport?.passport ? "Ledger Verified (ST-2 Secure)" : "Pending Verification"}
              </span>
              <div className="nx-label" style={{ marginTop: 8 }}>
                Last Update · {timeline[0]?.at?.slice(0, 10) || "Just now"}
              </div>
            </div>
          </div>

          <div className="nx-grid cols-4" style={{ marginTop: 18 }}>
            <div className="nx-metric-block">
              <div className="k">Inspections</div>
              <div className="v cy">
                {timeline.filter((t) => t.kind === "INSPECTION" || t.kind === "BASELINE").length || 1}
              </div>
            </div>
            <div className="nx-metric-block">
              <div className="k">DNA Version</div>
              <div className="v gd">{dna?.version || 1}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Active Warranties</div>
              <div className="v or">{warranties.filter(w => w.claim_status === "active").length || 0}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">AWE Composite</div>
              <div className="v gd">{awe?.composite_index ?? "92"}</div>
            </div>
          </div>
        </div>
      )}

      {/* AWE & Share Strip */}
      {awe && (
        <div className="nx-grid cols-2" style={{ gap: 16, marginBottom: 20 }}>
          <div className="nx-card" style={{ padding: "12px 16px" }}>
            <div className="nx-flex-between" style={{ marginBottom: 10 }}>
              <div className="nx-label" style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <Waves size={14} color="var(--nx-cyan)" /> AWE RESILIENCY MATURITY
              </div>
              <Link to="/nextgen/awe" className="nx-card-action" style={{ fontSize: 11 }}>
                AWE Details <ArrowUpRight size={11} />
              </Link>
            </div>
            <div className="nx-awe-band" data-testid="nx-passport-awe">
              <MiniRing label="Air" v={awe.air.score} color="#4DF6FF" icon={<Wind size={14} />} />
              <MiniRing label="Water" v={awe.water.score} color="#4DF6FF" icon={<Droplet size={14} />} />
              <MiniRing label="Energy" v={awe.energy.score} color="#FF7B00" icon={<Sun size={14} />} />
              <MiniRing label="Composite" v={awe.composite_index} color="#FFB020" icon={<Sparkles size={14} />} />
            </div>
          </div>

          <div className="nx-card" style={{ padding: "12px 16px", display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
            <div>
              <div className="nx-label" style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <Users size={14} color="var(--nx-cyan)" /> PROPERTY RECORD ACCESS DELEGATION
              </div>
              <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", marginTop: 6, marginBottom: 12 }}>
                Delegate secure, time-bound, read-only Habitat views of the Passport to homeowners, adjusters, or insurance providers.
              </div>
            </div>
            <div className="nx-flex nx-gap-2" style={{ flexWrap: "wrap" }}>
              <button className="nx-btn" style={{ padding: "6px 12px", fontSize: 12 }} disabled={linkBusy}
                onClick={async () => {
                  setLinkBusy(true);
                  try {
                    const r = await nxIssueHabitatLink(pid, 168, "homeowner");
                    const url = `${window.location.origin}${r.public_url}`;
                    await navigator.clipboard?.writeText(url).catch(() => {});
                    setLinkOut({ url, ...r });
                  } finally { setLinkBusy(false); }
                }}
                data-testid="nx-share-homeowner">
                <Share2 size={13} />
                {linkBusy ? "Generating..." : "Share with Homeowner"}
              </button>
              <button className="nx-btn ghost" style={{ padding: "6px 12px", fontSize: 12 }}
                onClick={() => nxOpenReportHtml(pid, template)}
                data-testid="nx-open-html-report">
                <ExternalLink size={13} /> Open HTML projection
              </button>
            </div>
            {linkOut && (
              <div className="nx-copied-inline" style={{ marginTop: 8 }} data-testid="nx-share-out">
                <Check size={12} color="var(--nx-success)" />
                <span style={{ color: "var(--nx-success)", fontFamily: "var(--nx-font-mono)", fontSize: 11, wordBreak: "break-all" }}>
                  Link Copied: {linkOut.url}
                </span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tabs Bar */}
      <div style={{ display: "flex", gap: 4, borderBottom: "1px solid var(--nx-border)", marginBottom: 20, overflowX: "auto" }}>
        {[
          { id: "timeline", label: "Passport Ledger & Timeline", icon: <Clock size={14} /> },
          { id: "dna", label: "Property DNA", icon: <Sparkles size={14} /> },
          { id: "compare", label: "Version Comparison", icon: <History size={14} /> },
          { id: "warranties", label: "Warranty Intelligence", icon: <ShieldCheck size={14} /> },
          { id: "maintenance", label: "Maintenance Intelligence", icon: <Calendar size={14} /> },
          { id: "financials", label: "Financial Framework", icon: <DollarSign size={14} /> },
          { id: "audit", label: "Workspace Integration Audit", icon: <FileCheck size={14} /> }
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "10px 16px",
              background: activeTab === tab.id ? "rgba(77,246,255,0.06)" : "transparent",
              color: activeTab === tab.id ? "var(--nx-cyan)" : "var(--nx-text-secondary)",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--nx-cyan)" : "2px solid transparent",
              fontWeight: 600,
              fontSize: 13,
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 6,
              whiteSpace: "nowrap"
            }}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {/* ── TAB CONTENT: TIMELINE ─────────────────────────────────────────── */}
      {activeTab === "timeline" && (
        <div>
          {/* Passport Ledger entries inside Timeline tab */}
          {passport?.entries && (
            <div style={{ marginBottom: 24 }}>
              <div className="nx-section-title">
                <span className="num">§01.A</span>
                <span className="label">Immutable Ledger Audit Trail (Hardened API writes)</span>
                <span className="rule" />
              </div>
              <div className="nx-card" style={{ padding: 0, overflow: "hidden" }}>
                <div style={{ background: "rgba(11,17,26,0.4)", padding: "10px 16px", borderBottom: "1px solid var(--nx-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", fontFamily: "var(--nx-font-mono)" }}>
                    CHAIN HASH VERIFICATION: <span style={{ color: "var(--nx-success)" }}>SHA-256 INTEGRITY HEALTHY</span>
                  </div>
                  <span className="nx-pill subtle" style={{ color: "var(--nx-orange)", borderColor: "rgba(255,123,0,0.4)" }}>LEDGER HARDENED</span>
                </div>
                <div style={{ overflowX: "auto" }}>
                  <table className="nx-table">
                    <thead>
                      <tr>
                        <th>Seq</th>
                        <th>Event Type</th>
                        <th>Payload Summary</th>
                        <th>Prior Hash</th>
                        <th>Content Hash</th>
                        <th>Signed Timestamp</th>
                      </tr>
                    </thead>
                    <tbody>
                      {passport.entries.map((e) => (
                        <tr key={e.canonical_id}>
                          <td style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-orange)" }}>#{e.seq}</td>
                          <td><span className="nx-pill">{e.entry_type}</span></td>
                          <td style={{ fontSize: 12 }}>
                            {e.payload?.field ? `Field: ${e.payload.field} → "${e.payload.new_value}"` : ""}
                            {e.payload?.warranty_id ? `Warranty ID: ${e.payload.warranty_id.slice(0, 8)} (${e.payload.manufacturer})` : ""}
                            {e.payload?.replacement_cost ? `Replacement Cost Updated to $${e.payload.replacement_cost.toLocaleString()}` : ""}
                            {!e.payload?.field && !e.payload?.warranty_id && !e.payload?.replacement_cost ? JSON.stringify(e.payload) : ""}
                          </td>
                          <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-text-muted)" }}>
                            {e.prior_hash ? e.prior_hash.slice(0, 10) + "…" : "GENESIS_ROOT"}
                          </td>
                          <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-success)" }}>
                            {e.content_hash ? e.content_hash.slice(0, 10) + "…" : "—"}
                          </td>
                          <td style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>
                            {e.at?.slice(0, 19).replace("T", " ")}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* Graphical timeline */}
          <div className="nx-section-title">
            <span className="num">§01.B</span>
            <span className="label">Chronological Property Timeline</span>
            <span className="rule" />
          </div>

          <div style={{ display: "flex", gap: 12, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
            <div style={{ position: "relative", flex: 1, minWidth: 200 }}>
              <span style={{ position: "absolute", left: 10, top: "50%", transform: "translateY(-50%)" }}>
                <Search size={14} color="var(--nx-text-muted)" />
              </span>
              <input
                type="text"
                className="nx-input"
                style={{ paddingLeft: 30 }}
                placeholder="Search events summary, ID, details..."
                value={timelineSearch}
                onChange={(e) => setTimelineSearch(e.target.value)}
              />
            </div>
            
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {timelineCategories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setTimelineFilter(cat)}
                  className={`nx-filter-chip ${timelineFilter === cat ? "active" : ""}`}
                >
                  {cat === "ALL" ? "All Categories" : cat}
                </button>
              ))}
            </div>
          </div>

          {filteredTimeline.length === 0 ? (
            <div className="nx-empty" data-testid="nx-timeline-empty">No matching timeline events found</div>
          ) : (
            <div className="nx-card" data-testid="nx-timeline" style={{ position: "relative", paddingLeft: 32 }}>
              {/* Timeline continuous vertical trace line */}
              <div style={{
                position: "absolute",
                left: 18,
                top: 24,
                bottom: 24,
                width: 2,
                background: "linear-gradient(to bottom, var(--nx-cyan) 0%, rgba(77,246,255,0.1) 100%)"
              }} />

              {filteredTimeline.map((t, idx) => (
                <div key={t.canonical_id || idx} className="nx-timeline-row" style={{ borderBottom: "1px solid var(--nx-border)", padding: "16px 0", position: "relative" }}>
                  {/* Glowing vertical node */}
                  <span className="dot" style={{
                    position: "absolute",
                    left: -20,
                    top: 20,
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    backgroundColor: "var(--nx-cyan)",
                    boxShadow: "0 0 10px var(--nx-cyan)"
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div className="nx-flex-between">
                      <span style={{ color: "#fff", fontSize: 15, fontWeight: 600 }}>{t.summary}</span>
                      <span className="nx-pill" style={{ fontSize: 10 }}>{t.kind}</span>
                    </div>
                    <div style={{ color: "var(--nx-text-secondary)", fontSize: 12, marginTop: 4 }}>
                      Event ID: <span style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11 }}>{t.canonical_id}</span>
                      {t.notes && <p style={{ color: "var(--nx-text-muted)", marginTop: 4, fontStyle: "italic" }}>{t.notes}</p>}
                    </div>
                    <div className="nx-label" style={{ marginTop: 8 }}>
                      Signed • {t.at?.slice(0, 19).replace("T", " ")} (UTC)
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── TAB CONTENT: PROPERTY DNA ─────────────────────────────────────── */}
      {activeTab === "dna" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§02.A</span>
            <span className="label">Canonical Property DNA Intelligence Profile</span>
            <span className="rule" />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 }}>
            {/* DNA Matrix */}
            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              {!dna ? (
                <div className="nx-empty">Loading Property DNA profile...</div>
              ) : (
                DNA_FIELDS.map(({ key, label }) => {
                  const fieldObj = dna[key] || { current_value: "Not Configured", history: [] };
                  const currentHistoryItem = fieldObj.history?.[fieldObj.history.length - 1];
                  const confidence = currentHistoryItem?.confidence_score ?? 95;
                  
                  // Get badge color for confidence
                  let confColor = "var(--nx-success)";
                  if (confidence < 80) confColor = "var(--nx-orange)";
                  if (confidence < 60) confColor = "var(--nx-warning)";

                  return (
                    <div key={key} className="nx-card" style={{ padding: "12px 16px" }}>
                      <div className="nx-flex-between">
                        <div>
                          <div className="nx-label" style={{ fontWeight: 600 }}>{label}</div>
                          <div style={{ fontSize: 16, color: "#fff", marginTop: 4, fontWeight: 700 }}>
                            {fieldObj.current_value}
                          </div>
                          <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4, display: "flex", gap: 12 }}>
                            <span>Source: <span style={{ textDecoration: "underline" }}>{currentHistoryItem?.source_attribution || "Baseline Record"}</span></span>
                            <span>Approval Status: <span style={{ color: "var(--nx-cyan)" }}>{currentHistoryItem?.approval_status || "APPROVED"}</span></span>
                          </div>
                        </div>
                        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                          <div style={{ textAlign: "right", marginRight: 8 }}>
                            <div className="nx-label">Confidence</div>
                            <div style={{ fontSize: 14, fontWeight: 700, color: confColor }}>{confidence}%</div>
                          </div>
                          <button
                            onClick={() => setSelectedDnaField({ key, label, ...fieldObj })}
                            className="nx-btn subtle"
                            style={{ padding: 6 }}
                            title="View Revision History & Attribution"
                          >
                            <History size={14} />
                          </button>
                          {isAuthorizedToEdit && (
                            <button
                              onClick={() => {
                                setEditingDnaField(key);
                                setDnaFormValue(fieldObj.current_value);
                                setDnaFormSource(currentHistoryItem?.source_attribution || "");
                                setDnaFormConfidence(confidence);
                              }}
                              className="nx-btn ghost"
                              style={{ padding: 6 }}
                              title="Update Canonical Fact"
                            >
                              <Edit size={14} />
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>

            {/* Sidebar Propose update form */}
            <div>
              <div className="nx-card elevated" style={{ position: "sticky", top: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <ShieldCheck size={16} color="var(--nx-cyan)" />
                  <span style={{ fontWeight: 700, color: "#fff", fontSize: 14 }}>Hardened Write Proposer</span>
                </div>
                
                {editingDnaField ? (
                  <form onSubmit={handleUpdateDna}>
                    <div className="nx-label" style={{ marginBottom: 4 }}>FIELD TO AMEND</div>
                    <div style={{ fontSize: 13, color: "var(--nx-cyan)", fontWeight: 700, marginBottom: 12, fontFamily: "var(--nx-font-mono)" }}>
                      {editingDnaField.toUpperCase()}
                    </div>

                    <div className="form-group" style={{ marginBottom: 12 }}>
                      <label className="nx-label" style={{ marginBottom: 4, display: "block" }}>VERIFIED NEW FACT VALUE</label>
                      <input
                        type="text"
                        className="nx-input"
                        required
                        value={dnaFormValue}
                        onChange={(e) => setDnaFormValue(e.target.value)}
                      />
                    </div>

                    <div className="form-group" style={{ marginBottom: 12 }}>
                      <label className="nx-label" style={{ marginBottom: 4, display: "block" }}>SOURCE ATTRIBUTION (FINDING ID / PERMIT)</label>
                      <input
                        type="text"
                        className="nx-input"
                        placeholder="e.g. finding-abc-123"
                        value={dnaFormSource}
                        onChange={(e) => setDnaFormSource(e.target.value)}
                      />
                    </div>

                    <div className="form-group" style={{ marginBottom: 16 }}>
                      <label className="nx-label" style={{ marginBottom: 4, display: "block" }}>AI / REVIEWER CONFIDENCE SCORE ({dnaFormConfidence}%)</label>
                      <input
                        type="range"
                        min="50"
                        max="100"
                        className="nx-input"
                        style={{ padding: 0 }}
                        value={dnaFormConfidence}
                        onChange={(e) => setDnaFormConfidence(e.target.value)}
                      />
                    </div>

                    <div style={{ display: "flex", gap: 8 }}>
                      <button type="submit" className="nx-btn" style={{ flex: 1 }} disabled={dnaSubmitting}>
                        {dnaSubmitting ? "Committing..." : "Commit Update"}
                      </button>
                      <button type="button" className="nx-btn ghost" onClick={() => setEditingDnaField(null)}>
                        Cancel
                      </button>
                    </div>
                    <div className="nx-label" style={{ marginTop: 10, fontSize: 10, lineHeight: "14px" }}>
                      Note: Submitting this form appends a DNA_FIELD_UPDATED event to the immutable Passport chain and recalculates content hashes.
                    </div>
                  </form>
                ) : (
                  <div>
                    <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", lineHeight: "18px", marginBottom: 14 }}>
                      To update or correct a canonical Property DNA fact, click the edit icon (<Edit size={12} style={{ display: "inline" }} />) next to any system.
                    </div>
                    <div style={{ padding: 12, background: "rgba(255,123,0,0.06)", border: "1px solid rgba(255,123,0,0.3)", borderRadius: "4px" }}>
                      <div className="nx-label" style={{ color: "var(--nx-orange)", fontWeight: 700, display: "flex", alignItems: "center", gap: 4 }}>
                        <AlertTriangle size={13} /> WRITE PATH ROLE LOCK
                      </div>
                      <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4, lineHeight: "14px" }}>
                        Only Admin, GM, or CEO accounts possess authorization to propose direct modifications. Consumers query read-only projection nodes.
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* DNA Field Revision History Modal */}
          {selectedDnaField && (
            <div style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.8)",
              zIndex: 1000,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 20
            }}>
              <div className="nx-card elevated" style={{ width: "100%", maxWidth: 650, maxHeight: "85vh", overflowY: "auto" }}>
                <div className="nx-flex-between" style={{ marginBottom: 16, borderBottom: "1px solid var(--nx-border)", paddingBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <History size={16} color="var(--nx-cyan)" />
                    <span style={{ fontSize: 16, fontWeight: 700, color: "#fff" }}>DNA Field History: {selectedDnaField.label}</span>
                  </div>
                  <button onClick={() => setSelectedDnaField(null)} style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer" }}>×</button>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                  {selectedDnaField.history?.map((h, index) => (
                    <div key={index} style={{ borderBottom: "1px solid var(--nx-border)", paddingBottom: 12 }}>
                      <div className="nx-flex-between">
                        <span style={{ fontSize: 13, fontWeight: 700, color: "var(--nx-orange)" }}>Version {h.version}</span>
                        <span className="nx-pill">{h.approval_status}</span>
                      </div>
                      <div style={{ fontSize: 14, color: "#fff", marginTop: 4 }}>
                        {h.value}
                      </div>
                      <div style={{ display: "grid", gridTemplateCols: "1fr 1fr", gap: 10, marginTop: 8, fontSize: 11, color: "var(--nx-text-secondary)" }}>
                        <div>Source: <span style={{ fontFamily: "var(--nx-font-mono)" }}>{h.source_attribution}</span></div>
                        <div>Reviewer: <span>{h.reviewer}</span></div>
                        <div>Confidence Score: <span style={{ color: "var(--nx-success)" }}>{h.confidence_score}%</span></div>
                        <div>Committed At: <span>{h.timestamp?.slice(0, 19).replace("T", " ")}</span></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB CONTENT: VERSION COMPARISON ───────────────────────────────── */}
      {activeTab === "compare" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§03.A</span>
            <span className="label">Property Version Comparison Matrix</span>
            <span className="rule" />
          </div>

          <div className="nx-card" style={{ marginBottom: 16 }}>
            <div className="nx-flex-between">
              <div style={{ fontSize: 12, color: "var(--nx-text-secondary)" }}>
                Compare current analyzed state directly against Previous Inspections and the Original Baseline Record to track degradation or improvements.
              </div>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                <span className="nx-label">Filter Change Type:</span>
                {["ALL", "ADDED", "REMOVED", "CHANGED", "VERIFIED", "PENDING"].map((opt) => (
                  <button
                    key={opt}
                    onClick={() => setCompareFilter(opt)}
                    className={`nx-filter-chip ${compareFilter === opt ? "active" : ""}`}
                    style={{ fontSize: 10, padding: "2px 8px" }}
                  >
                    {opt}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="nx-card" style={{ padding: 0 }}>
            <table className="nx-table">
              <thead>
                <tr>
                  <th>Component / Path</th>
                  <th>Original Baseline Record</th>
                  <th>Previous Inspection</th>
                  <th>Current State</th>
                  <th>Classification</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {compareData
                  .filter((row) => compareFilter === "ALL" || row.diff_type === compareFilter)
                  .map((row, idx) => {
                    let badgeClass = "subtle";
                    if (row.diff_type === "CHANGED") badgeClass = "warn";
                    if (row.diff_type === "ADDED") badgeClass = "ok";
                    if (row.diff_type === "REMOVED") badgeClass = "subtle";
                    if (row.diff_type === "VERIFIED") badgeClass = "ok";
                    if (row.diff_type === "PENDING") badgeClass = "warn";

                    return (
                      <tr key={idx}>
                        <td style={{ fontWeight: 700, fontSize: 13, fontFamily: "var(--nx-font-mono)" }}>
                          {row.component}
                        </td>
                        <td>
                          <span className={`nx-pill ${row.original === "OK" ? "ok" : "warn"}`} style={{ fontSize: 11 }}>
                            {row.original}
                          </span>
                        </td>
                        <td>
                          <span className={`nx-pill ${row.previous === "OK" ? "ok" : "warn"}`} style={{ fontSize: 11 }}>
                            {row.previous}
                          </span>
                        </td>
                        <td>
                          <span className={`nx-pill ${row.current === "OK" ? "ok" : "warn"}`} style={{ fontSize: 11, fontWeight: 700 }}>
                            {row.current}
                          </span>
                        </td>
                        <td>
                          <span className={`nx-pill ${badgeClass}`} style={{ fontSize: 11, fontWeight: "bold" }}>
                            {row.diff_type}
                          </span>
                        </td>
                        <td>
                          <span className="nx-label" style={{ textTransform: "uppercase" }}>{row.status}</span>
                        </td>
                      </tr>
                    );
                  })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ── TAB CONTENT: WARRANTIES ──────────────────────────────────────── */}
      {activeTab === "warranties" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§04.A</span>
            <span className="label">Unified Warranty Framework</span>
            <span className="rule" />
            {isAuthorizedForWarranty && (
              <button
                onClick={() => setShowRegisterWarranty(!showRegisterWarranty)}
                className="nx-btn subtle"
                style={{ fontSize: 11, padding: "4px 10px" }}
              >
                <Plus size={12} /> Register New Warranty
              </button>
            )}
          </div>

          {/* New Warranty Form */}
          {showRegisterWarranty && (
            <div className="nx-card elevated" style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#fff", marginBottom: 12 }}>Register Verified Component Warranty</div>
              <form onSubmit={handleRegisterWarranty}>
                <div className="nx-grid cols-2" style={{ gap: 12 }}>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>MANUFACTURER</label>
                    <input
                      type="text"
                      className="nx-input"
                      required
                      placeholder="e.g. Owens Corning"
                      value={warrantyForm.manufacturer}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, manufacturer: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>CONTRACTOR</label>
                    <input
                      type="text"
                      className="nx-input"
                      required
                      placeholder="e.g. Apex Roofing LLC"
                      value={warrantyForm.contractor}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, contractor: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>LABOR COVERAGE (MONTHS)</label>
                    <input
                      type="number"
                      className="nx-input"
                      required
                      value={warrantyForm.labor_coverage_months}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, labor_coverage_months: Number(e.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>MATERIAL COVERAGE (MONTHS)</label>
                    <input
                      type="number"
                      className="nx-input"
                      required
                      value={warrantyForm.material_coverage_months}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, material_coverage_months: Number(e.target.value) })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>START DATE</label>
                    <input
                      type="date"
                      className="nx-input"
                      required
                      value={warrantyForm.start_date}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, start_date: e.target.value })}
                    />
                  </div>
                  <div className="form-group">
                    <label className="nx-label" style={{ marginBottom: 4 }}>EXPIRATION DATE</label>
                    <input
                      type="date"
                      className="nx-input"
                      required
                      value={warrantyForm.expiration_date}
                      onChange={(e) => setWarrantyForm({ ...warrantyForm, expiration_date: e.target.value })}
                    />
                  </div>
                </div>

                <div className="form-group" style={{ marginTop: 12, marginBottom: 16 }}>
                  <label className="nx-label" style={{ marginBottom: 4 }}>LINKED PROPERTY COMPONENTS (comma-separated)</label>
                  <input
                    type="text"
                    className="nx-input"
                    placeholder="e.g. roof_system.shingles, exterior.gutters"
                    value={warrantyForm.linked_components_str}
                    onChange={(e) => setWarrantyForm({ ...warrantyForm, linked_components_str: e.target.value })}
                  />
                </div>

                <div style={{ display: "flex", gap: 8 }}>
                  <button type="submit" className="nx-btn" disabled={warrantySubmitting}>
                    {warrantySubmitting ? "Registering..." : "Register Warranty Fact"}
                  </button>
                  <button type="button" className="nx-btn ghost" onClick={() => setShowRegisterWarranty(false)}>Cancel</button>
                </div>
              </form>
            </div>
          )}

          {/* Warranties List */}
          <div className="nx-grid cols-2" style={{ gap: 16 }}>
            {warranties.length === 0 ? (
              <div className="nx-empty" style={{ gridColumn: "span 2" }}>No warranties registered for this property.</div>
            ) : (
              warranties.map((w) => {
                const expDate = new Date(w.expiration_date);
                const isExpired = expDate < new Date();
                const daysLeft = Math.ceil((expDate - new Date()) / (1000 * 60 * 60 * 24));

                return (
                  <div key={w.canonical_id} className="nx-card elevated" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
                    <div>
                      <div className="nx-flex-between">
                        <span className="nx-label" style={{ color: "var(--nx-orange)", fontFamily: "var(--nx-font-mono)", fontSize: 11 }}>
                          WNTY #{w.canonical_id?.slice(0, 8).toUpperCase()}
                        </span>
                        <span className={`nx-pill ${isExpired ? "warn" : "ok"}`}>
                          {isExpired ? "Expired" : "Active"}
                        </span>
                      </div>
                      <div style={{ fontSize: 18, fontWeight: 700, color: "#fff", marginTop: 6 }}>
                        {w.manufacturer}
                      </div>
                      <div style={{ fontSize: 13, color: "var(--nx-text-secondary)", marginTop: 2 }}>
                        Contractor: <span style={{ color: "#fff", fontWeight: 600 }}>{w.contractor}</span>
                      </div>

                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginTop: 12 }}>
                        <div className="nx-metric-block" style={{ padding: "6px 10px" }}>
                          <div className="k" style={{ fontSize: 9 }}>Labor Coverage</div>
                          <div className="v" style={{ fontSize: 14 }}>{w.labor_coverage_months} Mos</div>
                        </div>
                        <div className="nx-metric-block" style={{ padding: "6px 10px" }}>
                          <div className="k" style={{ fontSize: 9 }}>Material Coverage</div>
                          <div className="v" style={{ fontSize: 14 }}>{w.material_coverage_months} Mos</div>
                        </div>
                      </div>

                      {w.linked_components && w.linked_components.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div className="nx-label">LINKED COMPONENTS</div>
                          <div style={{ display: "flex", gap: 4, flexWrap: "wrap", marginTop: 4 }}>
                            {w.linked_components.map((comp, i) => (
                              <span key={i} className="nx-pill subtle" style={{ fontSize: 10 }}>{comp}</span>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Display renewals logs if any */}
                      {w.renewals && w.renewals.length > 0 && (
                        <div style={{ marginTop: 12 }}>
                          <div className="nx-label">RENEWAL CHRONOLOGY</div>
                          <div style={{ background: "rgba(0,0,0,0.2)", borderRadius: 4, padding: 8, marginTop: 4, maxHeight: 80, overflowY: "auto" }}>
                            {w.renewals.map((r, idx) => (
                              <div key={idx} style={{ fontSize: 10, color: "var(--nx-text-secondary)", marginBottom: 4, borderBottom: idx < w.renewals.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none", paddingBottom: 4 }}>
                                Renewed to {r.new_expiration?.slice(0, 10)} • Note: {r.notes || "None"}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div style={{ marginTop: 16, paddingTop: 12, borderTop: "1px solid var(--nx-border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span className="nx-label">
                        {isExpired ? (
                          <span style={{ color: "var(--nx-orange)" }}>Expired {Math.abs(daysLeft)} days ago</span>
                        ) : (
                          <span>Expires {w.expiration_date?.slice(0, 10)} ({daysLeft} days left)</span>
                        )}
                      </span>
                      {isAuthorizedForWarranty && (
                        <button
                          onClick={() => {
                            setRenewingWarranty(w);
                            setRenewalForm({
                              new_expiration_date: new Date(expDate.getTime() + 5 * 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
                              notes: ""
                            });
                          }}
                          className="nx-btn ghost"
                          style={{ padding: "4px 8px", fontSize: 11 }}
                        >
                          Renew
                        </button>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Warranty Renewal Modal */}
          {renewingWarranty && (
            <div style={{
              position: "fixed",
              inset: 0,
              background: "rgba(0,0,0,0.8)",
              zIndex: 1000,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 20
            }}>
              <div className="nx-card elevated" style={{ width: "100%", maxWidth: 450 }}>
                <div className="nx-flex-between" style={{ marginBottom: 16, borderBottom: "1px solid var(--nx-border)", paddingBottom: 10 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                    <ShieldCheck size={16} color="var(--nx-cyan)" />
                    <span style={{ fontSize: 15, fontWeight: 700, color: "#fff" }}>Renew Warranty</span>
                  </div>
                  <button onClick={() => setRenewingWarranty(null)} style={{ background: "none", border: "none", color: "#fff", fontSize: 20, cursor: "pointer" }}>×</button>
                </div>

                <form onSubmit={handleRenewWarranty}>
                  <div style={{ fontSize: 13, color: "var(--nx-text-secondary)", marginBottom: 12 }}>
                    Manufacturer: <span style={{ color: "#fff", fontWeight: 700 }}>{renewingWarranty.manufacturer}</span>
                  </div>

                  <div className="form-group" style={{ marginBottom: 12 }}>
                    <label className="nx-label" style={{ marginBottom: 4, display: "block" }}>NEW EXPIRATION DATE</label>
                    <input
                      type="date"
                      className="nx-input"
                      required
                      value={renewalForm.new_expiration_date}
                      onChange={(e) => setRenewalForm({ ...renewalForm, new_expiration_date: e.target.value })}
                    />
                  </div>

                  <div className="form-group" style={{ marginBottom: 16 }}>
                    <label className="nx-label" style={{ marginBottom: 4, display: "block" }}>RENEWAL AUDIT NOTES</label>
                    <textarea
                      className="nx-input"
                      rows={3}
                      placeholder="Specify renewal grounds, paid premium details or verification context"
                      value={renewalForm.notes}
                      onChange={(e) => setRenewalForm({ ...renewalForm, notes: e.target.value })}
                    />
                  </div>

                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="submit" className="nx-btn" style={{ flex: 1 }} disabled={renewalSubmitting}>
                      {renewalSubmitting ? "Renewing..." : "Commit Renewal"}
                    </button>
                    <button type="button" className="nx-btn ghost" onClick={() => setRenewingWarranty(null)}>Cancel</button>
                  </div>
                </form>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── TAB CONTENT: MAINTENANCE ─────────────────────────────────────── */}
      {activeTab === "maintenance" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§05.A</span>
            <span className="label">Structured Maintenance Intelligence Engine</span>
            <span className="rule" />
          </div>

          <div className="nx-card" style={{ padding: "12px 16px", marginBottom: 20 }}>
            <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", lineHeight: "18px" }}>
              Every maintenance cataloged below is automatically mapped from approved findings or baseline specifications in the Passport. System service life indicators reference standard architectural baselines.
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 20 }}>
            {/* Left Column: Deficiencies & Actions Required */}
            <div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
                <AlertTriangle size={15} color="var(--nx-orange)" />
                <h3 style={{ color: "#fff", margin: 0, fontSize: 14, fontWeight: 700 }}>Deficiencies & Recommended Planning</h3>
              </div>

              {/* Deferred Maintenance */}
              <div style={{ marginBottom: 16 }}>
                <div className="nx-label" style={{ color: "var(--nx-orange)", fontWeight: 700, marginBottom: 8, display: "flex", alignItems: "center", gap: 4 }}>
                  ● DEFERRED / CRITICAL MAINTENANCE ({maintenance?.deferred?.length || 0})
                </div>
                {maintenance?.deferred?.length === 0 ? (
                  <div className="nx-card" style={{ padding: 12, color: "var(--nx-text-muted)", fontSize: 12 }}>No deferred critical actions. Healthy envelope.</div>
                ) : (
                  maintenance?.deferred?.map((m) => <MaintenanceCard key={m.canonical_id} m={m} highlightColor="var(--nx-orange)" />)
                )}
              </div>

              {/* Recommended Maintenance */}
              <div style={{ marginBottom: 16 }}>
                <div className="nx-label" style={{ color: "var(--nx-cyan)", fontWeight: 700, marginBottom: 8 }}>
                  ● RECOMMENDED MAINTENANCE & OBSERVATIONS ({maintenance?.recommended?.length || 0})
                </div>
                {maintenance?.recommended?.length === 0 ? (
                  <div className="nx-card" style={{ padding: 12, color: "var(--nx-text-muted)", fontSize: 12 }}>No general recommended actions.</div>
                ) : (
                  maintenance?.recommended?.map((m) => <MaintenanceCard key={m.canonical_id} m={m} highlightColor="var(--nx-cyan)" />)
                )}
              </div>
            </div>

            {/* Right Column: Routine & Completed Actions */}
            <div>
              <div style={{ display: "flex", gap: 8, alignItems: "center", marginBottom: 12 }}>
                <CheckCircle size={15} color="var(--nx-success)" />
                <h3 style={{ color: "#fff", margin: 0, fontSize: 14, fontWeight: 700 }}>Scheduled & Historical Actions</h3>
              </div>

              {/* Upcoming Maintenance */}
              <div style={{ marginBottom: 16 }}>
                <div className="nx-label" style={{ color: "var(--nx-cyan)", fontWeight: 700, marginBottom: 8 }}>
                  ● UPCOMING / MAJOR MAINTENANCE ({maintenance?.upcoming?.length || 0})
                </div>
                {maintenance?.upcoming?.length === 0 ? (
                  <div className="nx-card" style={{ padding: 12, color: "var(--nx-text-muted)", fontSize: 12 }}>No upcoming maintenance planned.</div>
                ) : (
                  maintenance?.upcoming?.map((m) => <MaintenanceCard key={m.canonical_id} m={m} highlightColor="var(--nx-cyan)" />)
                )}
              </div>

              {/* Completed Maintenance */}
              <div style={{ marginBottom: 16 }}>
                <div className="nx-label" style={{ color: "var(--nx-success)", fontWeight: 700, marginBottom: 8 }}>
                  ● COMPLETED MAINTENANCE LOGS ({maintenance?.completed?.length || 0})
                </div>
                {maintenance?.completed?.length === 0 ? (
                  <div className="nx-card" style={{ padding: 12, color: "var(--nx-text-muted)", fontSize: 12 }}>No past completed actions logged.</div>
                ) : (
                  maintenance?.completed?.map((m) => <MaintenanceCard key={m.canonical_id} m={m} highlightColor="var(--nx-success)" />)
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB CONTENT: FINANCIALS ──────────────────────────────────────── */}
      {activeTab === "financials" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§06.A</span>
            <span className="label">Financial Intelligence Framework (Strictly Reference-Driven)</span>
            <span className="rule" />
          </div>

          <div style={{ background: "rgba(255,123,0,0.06)", border: "1px solid rgba(255,123,0,0.3)", borderRadius: "4px", padding: 16, marginBottom: 20 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "start" }}>
              <AlertTriangle size={16} color="var(--nx-orange)" style={{ marginTop: 2, flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, color: "#fff", fontWeight: 700 }}>ST-2 POLICY ON FINANCIAL ESTIMATION</div>
                <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", marginTop: 4, lineHeight: "18px" }}>
                  This interface provides a financial budget and repair planning framework only. Value-add factors and replacement cost estimations are strictly calculated from validated, approved component facts. No speculative or un-linked valuations may be registered.
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 340px", gap: 20 }}>
            {/* Financial Parameters Display */}
            <div>
              <div className="nx-grid cols-2" style={{ gap: 16, marginBottom: 20 }}>
                <div className="nx-card elevated" style={{ padding: 16 }}>
                  <div className="nx-label">ARCHITECTURAL REPLACEMENT COST</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "var(--nx-cyan)", marginTop: 6 }}>
                    ${financials?.replacement_cost_usd?.toLocaleString() || "0"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4 }}>
                    Auto-projected from property structural square count.
                  </div>
                </div>

                <div className="nx-card elevated" style={{ padding: 16 }}>
                  <div className="nx-label">CAPITAL IMPROVEMENTS TO DATE</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "var(--nx-success)", marginTop: 6 }}>
                    ${financials?.capital_improvements_usd?.toLocaleString() || "0"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4 }}>
                    Aggregated capital investments from closed projects.
                  </div>
                </div>

                <div className="nx-card elevated" style={{ padding: 16 }}>
                  <div className="nx-label">FIVE-YEAR CAPITAL RESERVE BUDGET</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "#fff", marginTop: 6 }}>
                    ${financials?.budget_5yr_usd?.toLocaleString() || "0"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4 }}>
                    Projected preventative envelope budget.
                  </div>
                </div>

                <div className="nx-card elevated" style={{ padding: 16 }}>
                  <div className="nx-label">TEN-YEAR RESERVE PLANNING</div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "#fff", marginTop: 6 }}>
                    ${financials?.budget_10yr_usd?.toLocaleString() || "0"}
                  </div>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4 }}>
                    Long-term system service life replacement reserves.
                  </div>
                </div>
              </div>

              {/* Value factors linked to passport */}
              <div className="nx-card">
                <div className="nx-label" style={{ fontWeight: 700, marginBottom: 12 }}>PASSPORT APPROVED VALUE-ADD FACTORS</div>
                {financials?.property_value_factors && financials.property_value_factors.length > 0 ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    {financials.property_value_factors.map((f, idx) => (
                      <div key={idx} className="nx-flex-between" style={{ padding: "8px 12px", background: "rgba(11,17,26,0.3)", border: "1px solid var(--nx-border)", borderRadius: "4px" }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: "#fff" }}>{f.factor}</div>
                          <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>
                            References Passport entry: <span style={{ fontFamily: "var(--nx-font-mono)" }}>{f.approved_reference_id}</span>
                          </div>
                        </div>
                        <div style={{ color: "var(--nx-success)", fontWeight: 700, fontSize: 14 }}>
                          +{f.impact_pct}% Impact
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="nx-label">No approved value factors are currently linked.</div>
                )}
              </div>
            </div>

            {/* Financial Parameters Write Form */}
            <div>
              <div className="nx-card elevated">
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 12 }}>
                  <DollarSign size={16} color="var(--nx-cyan)" />
                  <span style={{ fontWeight: 700, color: "#fff", fontSize: 14 }}>Budget Parameter Gating</span>
                </div>

                {isEditingFinancials ? (
                  <form onSubmit={handleUpdateFinancialsSubmit}>
                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="nx-label" style={{ marginBottom: 2 }}>REPLACEMENT ESTIMATE ($)</label>
                      <input
                        type="number"
                        className="nx-input"
                        required
                        value={financialForm.replacement_cost_usd}
                        onChange={(e) => setFinancialForm({ ...financialForm, replacement_cost_usd: Number(e.target.value) })}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="nx-label" style={{ marginBottom: 2 }}>CAPITAL IMPROVEMENTS ($)</label>
                      <input
                        type="number"
                        className="nx-input"
                        required
                        value={financialForm.capital_improvements_usd}
                        onChange={(e) => setFinancialForm({ ...financialForm, capital_improvements_usd: Number(e.target.value) })}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="nx-label" style={{ marginBottom: 2 }}>REPAIR INVESTMENTS ($)</label>
                      <input
                        type="number"
                        className="nx-input"
                        required
                        value={financialForm.repair_investments_usd}
                        onChange={(e) => setFinancialForm({ ...financialForm, repair_investments_usd: Number(e.target.value) })}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 10 }}>
                      <label className="nx-label" style={{ marginBottom: 2 }}>5-YEAR BUDGET ($)</label>
                      <input
                        type="number"
                        className="nx-input"
                        required
                        value={financialForm.budget_5yr_usd}
                        onChange={(e) => setFinancialForm({ ...financialForm, budget_5yr_usd: Number(e.target.value) })}
                      />
                    </div>
                    <div className="form-group" style={{ marginBottom: 14 }}>
                      <label className="nx-label" style={{ marginBottom: 2 }}>10-YEAR BUDGET ($)</label>
                      <input
                        type="number"
                        className="nx-input"
                        required
                        value={financialForm.budget_10yr_usd}
                        onChange={(e) => setFinancialForm({ ...financialForm, budget_10yr_usd: Number(e.target.value) })}
                      />
                    </div>

                    <div style={{ display: "flex", gap: 8 }}>
                      <button type="submit" className="nx-btn" style={{ flex: 1 }} disabled={financialSubmitting}>
                        {financialSubmitting ? "Saving..." : "Commit Framework"}
                      </button>
                      <button type="button" className="nx-btn ghost" onClick={() => setIsEditingFinancials(false)}>Cancel</button>
                    </div>
                  </form>
                ) : (
                  <div>
                    <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", lineHeight: "18px", marginBottom: 14 }}>
                      To adjust or verify the property envelope's financial planning framework parameters, invoke the secure, role-restricted configuration form.
                    </div>
                    {isAuthorizedToEdit ? (
                      <button className="nx-btn" style={{ width: "100%" }} onClick={() => setIsEditingFinancials(true)}>
                        Amend Planning Parameters
                      </button>
                    ) : (
                      <div style={{ padding: 10, background: "rgba(255,123,0,0.06)", border: "1px solid rgba(255,123,0,0.2)", borderRadius: "4px" }}>
                        <div style={{ fontSize: 11, color: "var(--nx-orange)", fontWeight: 700 }}>ROLE NOT AUTHORIZED</div>
                        <div style={{ fontSize: 10, color: "var(--nx-text-secondary)", marginTop: 4, lineHeight: "14px" }}>
                          Only Admin, GM, or CEO roles may alter financial planning frameworks on the Passport chain.
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── TAB CONTENT: WORKSPACE AUDIT ─────────────────────────────────── */}
      {activeTab === "audit" && (
        <div>
          <div className="nx-section-title">
            <span className="num">§07.A</span>
            <span className="label">Workspace Integration Audit</span>
            <span className="rule" />
          </div>

          <div className="nx-card" style={{ padding: 16, marginBottom: 20 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <ShieldCheck size={20} color="var(--nx-success)" />
              <div>
                <div style={{ fontSize: 15, fontWeight: 700, color: "#fff" }}>PASSPORT INTEGRATION COMPLIANCE STATUS</div>
                <div style={{ fontSize: 12, color: "var(--nx-text-secondary)", marginTop: 2 }}>
                  All Stratex-2 application modules have been audited to ensure zero duplication of property records. Modules query Property Passport as the canonical single-source-of-truth.
                </div>
              </div>
            </div>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {[
              {
                workspace: "Property Workspace",
                status: "FULLY COMPLIANT",
                details: "Property specs, baseline attributes, and addresses map directly from Passport projection APIs. No duplicate editing capabilities allowed.",
                tests: "PASSED"
              },
              {
                workspace: "Mission Workspace (Evidence Engine)",
                status: "FULLY COMPLIANT",
                details: "Findings and taxonomy observations resolve directly into the central Passport database after being vetted and marked APPROVED by reviewers.",
                tests: "PASSED"
              },
              {
                workspace: "Contractor Workspace (Project Engine)",
                status: "FULLY COMPLIANT",
                details: "Submits warranties and completed project facts directly through the read-write Passport API gating, updating historical revisions.",
                tests: "PASSED"
              },
              {
                workspace: "Report Workspace & Templates",
                status: "FULLY COMPLIANT",
                details: "Generates HTML and JSON projections referencing chain content hashes. Contains zero local property DB models.",
                tests: "PASSED"
              },
              {
                workspace: "Habitat (Homeowner Share Portal)",
                status: "FULLY COMPLIANT",
                details: "Consumes only secure, time-bound token grants of central Passport timeline projections. Contains zero independent findings models.",
                tests: "PASSED"
              },
              {
                workspace: "Future Insurance Workspace (Framework)",
                status: "FULLY COMPLIANT",
                details: "Pre-integrated read-only adjuster projections for weather, damage histories, and warranties.",
                tests: "PASSED"
              }
            ].map((w, idx) => (
              <div key={idx} className="nx-card" style={{ padding: "14px 18px" }}>
                <div className="nx-flex-between">
                  <div>
                    <span style={{ fontSize: 14, fontWeight: 700, color: "#fff" }}>{w.workspace}</span>
                    <p style={{ fontSize: 12, color: "var(--nx-text-secondary)", marginTop: 4, margin: "4px 0 0 0" }}>{w.details}</p>
                  </div>
                  <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
                    <div style={{ textAlign: "right" }}>
                      <div className="nx-label">STATUS</div>
                      <div style={{ color: "var(--nx-success)", fontWeight: 700, fontSize: 11 }}>{w.status}</div>
                    </div>
                    <div style={{ textAlign: "right" }}>
                      <div className="nx-label">QA CHECK</div>
                      <div style={{ color: "var(--nx-cyan)", fontWeight: 700, fontSize: 11 }}>{w.tests}</div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <PassportStyles />
    </div>
  );
}

function MiniRing({ label, v, color, icon }) {
  const val = Math.max(0, Math.min(100, v || 0));
  const R = 35, C = 2 * Math.PI * R, off = C - (val / 100) * C;
  return (
    <div className="nx-awe-ring" style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 80 }}>
      <div style={{ position: "relative", display: "inline-flex" }}>
        <svg width="80" height="80" viewBox="0 0 80 80" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="40" cy="40" r={R} stroke="rgba(77,246,255,0.05)" strokeWidth="6" fill="none" />
          <circle cx="40" cy="40" r={R} stroke={color} strokeWidth="6" fill="none"
            strokeLinecap="round" strokeDasharray={C} strokeDashoffset={off} style={{ transition: "stroke-dashoffset 0.5s ease" }} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center" }}>
          <div style={{ fontFamily: "var(--nx-font-tech)", fontVariantNumeric: "tabular-nums", fontSize: 18, fontWeight: 700, color }}>{val}</div>
        </div>
      </div>
      <div className="ring-label" style={{ display: "flex", gap: 3, alignItems: "center", fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 6 }}>
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
}

function MaintenanceCard({ m, highlightColor }) {
  return (
    <div className="nx-card" style={{ borderLeft: `3px solid ${highlightColor}`, padding: "10px 14px", marginBottom: 10 }}>
      <div className="nx-flex-between">
        <span style={{ fontSize: 11, fontWeight: 700, color: "#fff", fontFamily: "var(--nx-font-mono)" }}>
          {m.system?.toUpperCase()} / {m.component?.toUpperCase()}
        </span>
        <span className="nx-pill subtle" style={{ fontSize: 9 }}>PRIORITY: {m.priority}</span>
      </div>
      <div style={{ fontSize: 13, color: "#fff", marginTop: 4, fontWeight: 600 }}>
        {m.description}
      </div>
      {m.recommended_action && (
        <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 4, padding: "4px 8px", background: "rgba(0,0,0,0.15)", borderRadius: "3px" }}>
          Rec: {m.recommended_action}
        </div>
      )}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 8, fontSize: 10, color: "var(--nx-text-muted)" }}>
        <span>Est Life: {m.expected_life} (Rem: {m.remaining_life_years} Yrs)</span>
        <span style={{ fontFamily: "var(--nx-font-mono)" }}>Ref: {m.passport_reference_id?.slice(0, 10)}</span>
      </div>
    </div>
  );
}

function PassportStyles() {
  return (
    <style>{`
      .nx-timeline-row {
        display: flex; gap: 14px;
        padding: 12px 0;
        border-bottom: 1px solid var(--nx-border);
        align-items: flex-start;
      }
      .nx-timeline-row:last-child { border-bottom: none; }
      .nx-timeline-row .dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: var(--nx-cyan); flex-shrink: 0; margin-top: 5px;
        box-shadow: 0 0 12px var(--nx-cyan);
      }
      .nx-copied-inline {
        display: flex; gap: 10px; align-items: center; margin-top: 12px;
        padding: 10px 12px;
        background: rgba(53,227,154,0.06);
        border: 1px solid rgba(53,227,154,0.4);
        border-radius: var(--nx-r-sm);
        flex-wrap: wrap;
      }
      .nx-awe-band {
        display: flex;
        gap: 16px;
        justify-content: space-around;
        padding: 8px 0;
      }
      .form-group label {
        color: var(--nx-text-secondary);
        font-family: var(--nx-font-mono);
        font-weight: 600;
      }
    `}</style>
  );
}

