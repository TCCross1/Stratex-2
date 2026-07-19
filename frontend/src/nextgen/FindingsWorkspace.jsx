import React, { useEffect, useMemo, useState } from "react";
import { useOutletContext } from "react-router-dom";
import {
  Plus, X, AlertTriangle, CheckCircle2, Clock, Circle,
  RefreshCw, XCircle, ShieldCheck, User, ArrowUpRight, Info,
} from "lucide-react";
import { useAuth } from "@/lib/auth";
import {
  nxCreateFinding, nxUpdateFinding, nxSubmitFinding, nxApproveFinding,
  nxRejectFinding, nxResolveFinding, nxListFindings, nxGetFinding,
  nxTaxonomy,
} from "@/nextgen/api";
import PropertyIntelligenceSummary from "@/nextgen/PropertyIntelligenceSummary";

const APPROVER_ROLES = new Set(["ceo", "admin", "gm"]);
const CREATOR_ROLES = new Set(["ceo", "admin", "gm", "contractor", "operator", "pilot", "inspector"]);
const SEVERITY = ["INFORMATIONAL", "MINOR", "MODERATE", "MAJOR", "CRITICAL"];
const PRIORITY = ["MONITOR", "SCHEDULE", "IMPORTANT", "URGENT", "IMMEDIATE"];
const STATUS_META = {
  DRAFT:          { label: "Draft",          color: "var(--nx-text-secondary)", icon: Circle },
  PENDING_REVIEW: { label: "Pending Review", color: "var(--nx-gold)",           icon: Clock },
  APPROVED:       { label: "Approved",       color: "var(--nx-success)",        icon: CheckCircle2 },
  REJECTED:       { label: "Rejected",       color: "var(--nx-critical)",       icon: XCircle },
  RESOLVED:       { label: "Resolved",       color: "var(--nx-cyan)",           icon: ShieldCheck },
  SUPERSEDED:     { label: "Superseded",     color: "var(--nx-text-muted)",     icon: RefreshCw },
};

export default function FindingsWorkspace() {
  const { propertyId, missions } = useOutletContext();
  const { user } = useAuth();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [openId, setOpenId] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [errBanner, setErrBanner] = useState(null);

  const canCreate = CREATOR_ROLES.has(user?.role);
  const canApprove = APPROVER_ROLES.has(user?.role);

  const reload = () => {
    setLoading(true);
    nxListFindings(propertyId, statusFilter ? { status: statusFilter } : {})
      .then((r) => setItems(r.items || []))
      .catch((e) => setErrBanner(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (!propertyId) return;
    reload();
  }, [propertyId, statusFilter, reloadKey]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div data-testid="nx-ws-findings">
      <PropertyIntelligenceSummary
        propertyId={propertyId}
        audience="internal"
        reloadKey={reloadKey}
      />

      <div className="nx-flex-between" style={{ marginTop: 20, marginBottom: 14, flexWrap: "wrap", gap: 12 }}>
        <div>
          <div className="nx-label">Findings Ledger</div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
            Manual observations only. AI-drafted findings are deferred to Vision Grounding.
          </div>
        </div>
        <div className="nx-flex nx-gap-3" style={{ flexWrap: "wrap" }}>
          <FilterSelect value={statusFilter} onChange={setStatusFilter} />
          {canCreate && (
            <button
              className="nx-btn"
              onClick={() => setShowForm(true)}
              data-testid="finding-new-btn"
            >
              <Plus size={14} strokeWidth={1.8} /> New Finding
            </button>
          )}
        </div>
      </div>

      {errBanner && (
        <div className="nx-notice" data-testid="finding-error-banner" style={{ marginBottom: 12 }}>
          <AlertTriangle size={14} /> {String(errBanner)}
        </div>
      )}

      {loading ? (
        <div className="nx-empty">Loading findings…</div>
      ) : items.length === 0 ? (
        <div className="nx-empty" data-testid="findings-empty">
          NOT YET ANALYZED · no findings match the current filter.
        </div>
      ) : (
        <div className="nx-card" style={{ padding: 0 }} data-testid="findings-list">
          <table className="nx-table">
            <thead>
              <tr>
                <th>Ref</th>
                <th>Taxonomy</th>
                <th>Severity</th>
                <th>Status</th>
                <th>Author</th>
                <th>Evidence</th>
                <th>Created</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {items.map((f) => (
                <FindingRow
                  key={f.canonical_id}
                  finding={f}
                  onOpen={() => setOpenId(f.canonical_id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showForm && (
        <FindingForm
          propertyId={propertyId}
          missions={missions}
          onClose={() => setShowForm(false)}
          onCreated={() => {
            setShowForm(false);
            setReloadKey((k) => k + 1);
          }}
        />
      )}

      {openId && (
        <FindingDrawer
          findingId={openId}
          user={user}
          canApprove={canApprove}
          onClose={() => setOpenId(null)}
          onChanged={() => {
            setOpenId(null);
            setReloadKey((k) => k + 1);
          }}
        />
      )}
    </div>
  );
}

function FilterSelect({ value, onChange }) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="nx-input"
      data-testid="finding-filter-status"
      style={{ padding: "8px 10px", minWidth: 180 }}
    >
      <option value="">All Statuses</option>
      {Object.keys(STATUS_META).map((s) => (
        <option key={s} value={s}>{STATUS_META[s].label}</option>
      ))}
    </select>
  );
}

function FindingRow({ finding, onOpen }) {
  const meta = STATUS_META[finding.status] || STATUS_META.DRAFT;
  const Icon = meta.icon;
  return (
    <tr data-testid={`finding-row-${finding.canonical_id}`}>
      <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-orange)" }}>
        {finding.canonical_id.slice(0, 10)}
      </td>
      <td>
        <div style={{ color: "#fff", fontSize: 13 }}>
          {finding.taxonomy_category}
          {finding.taxonomy_component ? ` / ${finding.taxonomy_component}` : ""}
        </div>
        <div style={{ color: "var(--nx-text-muted)", fontSize: 11, marginTop: 2, maxWidth: 320,
          overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {finding.description}
        </div>
      </td>
      <td>
        <span className="nx-pill">{finding.severity}</span>
      </td>
      <td>
        <span
          className="nx-pill"
          style={{ color: meta.color, borderColor: meta.color }}
          data-testid={`finding-status-pill-${finding.canonical_id}`}
        >
          <Icon size={11} strokeWidth={1.8} /> {meta.label}
        </span>
      </td>
      <td style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>
        {finding.author_role} · {String(finding.author_id).slice(0, 8)}
      </td>
      <td style={{ fontSize: 11 }}>
        {finding.manual_observation ? (
          <span
            className="nx-pill"
            style={{ color: "var(--nx-gold)", borderColor: "var(--nx-gold)" }}
            data-testid={`finding-manual-badge-${finding.canonical_id}`}
          >
            MANUAL · NOT LINKED
          </span>
        ) : (
          <span className="nx-pill cyan">
            {finding.evidence_ids?.length || 0} evidence
          </span>
        )}
      </td>
      <td style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>
        {finding.created_at?.slice(0, 10)}
      </td>
      <td>
        <button
          className="nx-card-action"
          onClick={onOpen}
          data-testid={`finding-open-${finding.canonical_id}`}
        >
          Open <ArrowUpRight size={13} strokeWidth={1.8} />
        </button>
      </td>
    </tr>
  );
}

/* ── Create form ─────────────────────────────────────────────────────── */
function FindingForm({ propertyId, missions, onClose, onCreated }) {
  const [taxonomy, setTaxonomy] = useState(null);
  const [category, setCategory] = useState("");
  const [component, setComponent] = useState("");
  const [severity, setSeverity] = useState("MINOR");
  const [priority, setPriority] = useState("SCHEDULE");
  const [description, setDescription] = useState("");
  const [missionId, setMissionId] = useState("");
  const [evidenceIds, setEvidenceIds] = useState("");
  const [notes, setNotes] = useState("");
  const [confidencePct, setConfidencePct] = useState("");
  const [confidenceSource, setConfidenceSource] = useState("");
  const [habitatVisible, setHabitatVisible] = useState(false);
  const [insuranceRelevant, setInsuranceRelevant] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    nxTaxonomy().then(setTaxonomy).catch(() => {});
  }, []);

  const components = useMemo(() => {
    if (!taxonomy || !category) return [];
    return taxonomy.systems?.[category] || [];
  }, [taxonomy, category]);

  const evidenceList = useMemo(
    () => evidenceIds.split(",").map((s) => s.trim()).filter(Boolean),
    [evidenceIds],
  );
  const manualObservation = evidenceList.length === 0;

  const submit = async () => {
    if (!category) { setErr("Taxonomy category is required"); return; }
    if (!description.trim()) { setErr("Description is required"); return; }
    if (confidencePct && !confidenceSource) {
      setErr("Confidence % requires a confidence source (e.g. 'human_field_observation')");
      return;
    }
    setSubmitting(true);
    setErr(null);
    try {
      const body = {
        property_id: propertyId,
        mission_id: missionId || null,
        evidence_ids: evidenceList,
        taxonomy_category: category,
        taxonomy_component: component || null,
        severity,
        priority,
        description: description.trim(),
        notes: notes || null,
        habitat_visible: habitatVisible,
        insurance_relevant: insuranceRelevant,
      };
      if (confidencePct) {
        body.confidence_pct = Number(confidencePct);
        body.confidence_source = confidenceSource || null;
      }
      await nxCreateFinding(body);
      onCreated();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Drawer title="New Manual Finding" onClose={onClose} testId="finding-form">
      {manualObservation && (
        <div className="nx-notice" data-testid="finding-form-manual-warning" style={{ marginBottom: 12 }}>
          <AlertTriangle size={14} strokeWidth={1.8} />
          <span>
            This finding is not linked to captured evidence and requires reviewer attention.
            It will be labeled <strong>MANUAL OBSERVATION — EVIDENCE NOT LINKED</strong>.
          </span>
        </div>
      )}

      <FormRow label="Taxonomy Category">
        <select
          value={category}
          onChange={(e) => { setCategory(e.target.value); setComponent(""); }}
          className="nx-input"
          data-testid="finding-form-category"
        >
          <option value="">—</option>
          {taxonomy?.systems && Object.keys(taxonomy.systems).map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </FormRow>
      <FormRow label="Component">
        <select
          value={component}
          onChange={(e) => setComponent(e.target.value)}
          className="nx-input"
          disabled={!components.length}
          data-testid="finding-form-component"
        >
          <option value="">—</option>
          {components.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </FormRow>
      <FormRow label="Severity">
        <select value={severity} onChange={(e) => setSeverity(e.target.value)}
          className="nx-input" data-testid="finding-form-severity">
          {SEVERITY.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
      </FormRow>
      <FormRow label="Priority">
        <select value={priority} onChange={(e) => setPriority(e.target.value)}
          className="nx-input" data-testid="finding-form-priority">
          {PRIORITY.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
      </FormRow>
      <FormRow label="Description *">
        <textarea
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          className="nx-input"
          rows={3}
          data-testid="finding-form-description"
          placeholder="Describe the observation clearly. Do not invent details."
        />
      </FormRow>
      <FormRow label="Mission (optional)">
        <select
          value={missionId}
          onChange={(e) => setMissionId(e.target.value)}
          className="nx-input"
          data-testid="finding-form-mission"
        >
          <option value="">—</option>
          {(missions || []).map((m) => (
            <option key={m.canonical_id} value={m.canonical_id}>
              {m.product?.replace(/_/g, " ")} · {m.canonical_id.slice(0, 8)}
            </option>
          ))}
        </select>
      </FormRow>
      <FormRow label="Evidence IDs (comma-separated · optional)">
        <input
          type="text"
          value={evidenceIds}
          onChange={(e) => setEvidenceIds(e.target.value)}
          className="nx-input"
          data-testid="finding-form-evidence"
          placeholder="canonical_id_1, canonical_id_2"
        />
      </FormRow>
      <FormRow label="Confidence % (optional)">
        <input
          type="number"
          min="0"
          max="100"
          value={confidencePct}
          onChange={(e) => setConfidencePct(e.target.value)}
          className="nx-input"
          data-testid="finding-form-confidence"
          placeholder="Only if a valid source exists"
        />
      </FormRow>
      {confidencePct && (
        <FormRow label="Confidence Source *">
          <input
            type="text"
            value={confidenceSource}
            onChange={(e) => setConfidenceSource(e.target.value)}
            className="nx-input"
            data-testid="finding-form-confidence-source"
            placeholder="e.g. human_field_observation"
          />
        </FormRow>
      )}
      <FormRow label="Notes (internal)">
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="nx-input"
          rows={2}
          data-testid="finding-form-notes"
        />
      </FormRow>
      <FormRow label="Homeowner-Visible (Habitat)">
        <label className="nx-flex nx-gap-3" style={{ alignItems: "center" }}>
          <input
            type="checkbox"
            checked={habitatVisible}
            onChange={(e) => setHabitatVisible(e.target.checked)}
            data-testid="finding-form-habitat"
          />
          <span style={{ color: "var(--nx-text-secondary)", fontSize: 12 }}>
            If checked, appears in the homeowner Habitat projection (only after approval).
          </span>
        </label>
      </FormRow>
      <FormRow label="Insurance Relevant">
        <label className="nx-flex nx-gap-3" style={{ alignItems: "center" }}>
          <input
            type="checkbox"
            checked={insuranceRelevant}
            onChange={(e) => setInsuranceRelevant(e.target.checked)}
            data-testid="finding-form-insurance"
          />
          <span style={{ color: "var(--nx-text-secondary)", fontSize: 12 }}>
            Marks the finding as insurance-relevant. Insurance projections may include it after approval.
          </span>
        </label>
      </FormRow>

      {err && (
        <div className="nx-notice" data-testid="finding-form-error" style={{ marginTop: 8 }}>
          <AlertTriangle size={14} /> {String(err)}
        </div>
      )}

      <div className="nx-flex nx-gap-3" style={{ marginTop: 16 }}>
        <button
          className="nx-btn"
          onClick={submit}
          disabled={submitting}
          data-testid="finding-form-submit"
        >
          {submitting ? "Saving…" : "Save as Draft"}
        </button>
        <button className="nx-btn ghost" onClick={onClose} data-testid="finding-form-cancel">
          Cancel
        </button>
      </div>
    </Drawer>
  );
}

/* ── Detail drawer + approval controls ────────────────────────────────── */
function FindingDrawer({ findingId, user, canApprove, onClose, onChanged }) {
  const [finding, setFinding] = useState(null);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);

  const reload = () => {
    nxGetFinding(findingId).then((r) => setFinding(r.finding)).catch(() => {});
  };
  useEffect(() => { reload(); }, [findingId]);

  const isAuthor = finding && user && finding.author_id === user.id;
  const status = finding?.status;

  const act = async (fn, ok = "OK") => {
    setBusy(true);
    setErr(null);
    try {
      await fn();
      onChanged();
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
      setBusy(false);
    }
  };

  if (!finding) {
    return (
      <Drawer title="Loading finding…" onClose={onClose} testId="finding-drawer">
        <div className="nx-empty">Loading…</div>
      </Drawer>
    );
  }

  const meta = STATUS_META[status] || STATUS_META.DRAFT;
  const Icon = meta.icon;

  return (
    <Drawer
      title={`Finding · ${finding.canonical_id.slice(0, 10)}`}
      onClose={onClose}
      testId="finding-drawer"
    >
      <div className="nx-flex nx-gap-3" style={{ marginBottom: 12, flexWrap: "wrap" }}>
        <span
          className="nx-pill"
          style={{ color: meta.color, borderColor: meta.color }}
          data-testid="finding-drawer-status"
        >
          <Icon size={12} strokeWidth={1.8} /> {meta.label}
        </span>
        <span className="nx-pill">{finding.severity}</span>
        <span className="nx-pill">{finding.priority}</span>
        {finding.manual_observation && (
          <span
            className="nx-pill"
            style={{ color: "var(--nx-gold)", borderColor: "var(--nx-gold)" }}
            data-testid="finding-drawer-manual"
          >
            MANUAL OBSERVATION — EVIDENCE NOT LINKED
          </span>
        )}
      </div>

      <DetailField label="Taxonomy">
        {finding.taxonomy_category}{finding.taxonomy_component ? ` / ${finding.taxonomy_component}` : ""}
      </DetailField>
      <DetailField label="Description">{finding.description}</DetailField>
      <DetailField label="Author">
        <span className="nx-flex nx-gap-3" style={{ alignItems: "center" }}>
          <User size={12} /> {finding.author_role} · {String(finding.author_id).slice(0, 12)}
        </span>
      </DetailField>
      <DetailField label="Created">
        {finding.created_at?.slice(0, 19).replace("T", " ")}
      </DetailField>
      {finding.confidence_pct != null && (
        <DetailField label="Confidence">
          {finding.confidence_pct}% · source: {finding.confidence_source || "—"}
        </DetailField>
      )}
      {finding.evidence_ids?.length > 0 && (
        <DetailField label="Evidence">
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            {finding.evidence_ids.map((eid) => (
              <span key={eid} className="nx-pill cyan" style={{ fontFamily: "var(--nx-font-mono)" }}>
                {eid.slice(0, 10)}
              </span>
            ))}
          </div>
        </DetailField>
      )}
      {finding.mission_id && (
        <DetailField label="Mission">
          {finding.mission_id.slice(0, 12)}
        </DetailField>
      )}

      {finding.approval && (
        <div className="nx-card" data-testid="finding-drawer-approval" style={{ marginTop: 12 }}>
          <div className="nx-label">Approval Receipt</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "var(--nx-text-secondary)" }}>
            Approved by <strong>{finding.approval.reviewer_role}</strong> ·{" "}
            {String(finding.approval.reviewer_id).slice(0, 10)}
            {" · "}{finding.approval.at?.slice(0, 19).replace("T", " ")}
          </div>
          <div style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-success)", marginTop: 6 }}>
            sig · {finding.approval.signature?.slice(0, 24)}…
          </div>
        </div>
      )}

      {finding.passport_entry_id && (
        <div className="nx-card" data-testid="finding-drawer-passport" style={{ marginTop: 12 }}>
          <div className="nx-label">Passport Update</div>
          <div style={{ marginTop: 6, fontSize: 12, color: "var(--nx-text-secondary)" }}>
            Passport seq #{finding.passport_seq}
          </div>
          <div style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-cyan)", marginTop: 6 }}>
            content_hash · {finding.passport_content_hash?.slice(0, 32)}…
          </div>
        </div>
      )}

      <ReviewHistory history={finding.review_history || []} />

      {err && (
        <div className="nx-notice" data-testid="finding-drawer-error" style={{ marginTop: 12 }}>
          <AlertTriangle size={14} /> {String(err)}
        </div>
      )}

      {isAuthor && status === "PENDING_REVIEW" && (
        <div className="nx-notice" data-testid="finding-drawer-sod-warning" style={{ marginTop: 12 }}>
          <Info size={14} />
          Separation of duties: as the author, you cannot approve or reject your own finding.
        </div>
      )}

      <div className="nx-flex nx-gap-3" style={{ marginTop: 16, flexWrap: "wrap" }}>
        <textarea
          className="nx-input"
          rows={2}
          placeholder="Reviewer notes (optional)"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          data-testid="finding-drawer-notes"
          style={{ flex: 1, minWidth: 220 }}
        />
      </div>

      <div className="nx-flex nx-gap-3" style={{ marginTop: 12, flexWrap: "wrap" }}>
        {status === "DRAFT" && (
          <button
            className="nx-btn"
            disabled={busy}
            onClick={() => act(() => nxSubmitFinding(findingId, notes))}
            data-testid="finding-drawer-submit"
          >
            Submit for Review
          </button>
        )}
        {status === "PENDING_REVIEW" && canApprove && !isAuthor && (
          <>
            <button
              className="nx-btn"
              disabled={busy}
              onClick={() => act(() => nxApproveFinding(findingId, notes))}
              data-testid="finding-drawer-approve"
            >
              <CheckCircle2 size={14} /> Approve → Passport
            </button>
            <button
              className="nx-btn ghost"
              disabled={busy}
              onClick={() => act(() => nxRejectFinding(findingId, notes))}
              data-testid="finding-drawer-reject"
            >
              <XCircle size={14} /> Reject
            </button>
          </>
        )}
        {status === "APPROVED" && canApprove && (
          <button
            className="nx-btn ghost"
            disabled={busy}
            onClick={() => act(() => nxResolveFinding(findingId, notes))}
            data-testid="finding-drawer-resolve"
          >
            <ShieldCheck size={14} /> Mark Resolved
          </button>
        )}
        <button className="nx-btn ghost" onClick={onClose} data-testid="finding-drawer-close">
          Close
        </button>
      </div>
    </Drawer>
  );
}

function ReviewHistory({ history }) {
  if (!history?.length) return null;
  return (
    <div className="nx-card" style={{ marginTop: 12 }} data-testid="finding-drawer-history">
      <div className="nx-label">Review History</div>
      <ul style={{ marginTop: 8, paddingLeft: 0, listStyle: "none" }}>
        {history.map((h, i) => (
          <li key={i} style={{
            padding: "6px 0", borderTop: i ? "1px solid var(--nx-line)" : "none",
            fontSize: 12, color: "var(--nx-text-secondary)",
          }}>
            <span style={{ color: "var(--nx-cyan)", fontFamily: "var(--nx-font-mono)" }}>
              {h.action}
            </span>{" · "}
            {h.role} · {String(h.by).slice(0, 8)}
            {" · "}{h.at?.slice(0, 19).replace("T", " ")}
            {h.notes && <div style={{ marginTop: 2, color: "var(--nx-text-muted)" }}>“{h.notes}”</div>}
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── Layout primitives ────────────────────────────────────────────────── */
function Drawer({ title, onClose, children, testId }) {
  return (
    <div
      style={{
        position: "fixed", inset: 0, background: "rgba(0,0,0,0.55)",
        zIndex: 800, display: "flex", justifyContent: "flex-end",
      }}
      onClick={onClose}
      data-testid={`${testId}-backdrop`}
    >
      <div
        style={{
          width: "min(560px, 100%)",
          height: "100%",
          overflowY: "auto",
          background: "var(--nx-bg-panel, #0b0f14)",
          borderLeft: "1px solid var(--nx-line, #1a2530)",
          padding: 24,
        }}
        onClick={(e) => e.stopPropagation()}
        data-testid={testId}
      >
        <div className="nx-flex-between" style={{ marginBottom: 16 }}>
          <div style={{ fontSize: 18, color: "#fff", fontWeight: 700 }}>{title}</div>
          <button
            className="nx-btn ghost small"
            onClick={onClose}
            aria-label="Close"
            data-testid={`${testId}-close-x`}
          >
            <X size={14} />
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

function FormRow({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <div className="nx-label" style={{ marginBottom: 4 }}>{label}</div>
      {children}
    </div>
  );
}

function DetailField({ label, children }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div className="nx-label">{label}</div>
      <div style={{ color: "#fff", fontSize: 13, marginTop: 4, wordBreak: "break-word" }}>
        {children}
      </div>
    </div>
  );
}
