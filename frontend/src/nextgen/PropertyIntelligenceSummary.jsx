import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  Activity, CheckCircle2, Circle, AlertTriangle, Clock, XCircle,
  ShieldCheck, RefreshCw, ArrowUpRight, Info,
} from "lucide-react";
import { nxIntelligenceSummary } from "@/nextgen/api";

/* ─────────────────────────────────────────────────────────────
   PropertyIntelligenceSummary — reusable PIE aggregate panel.

   Used inside the Property Workspace (Overview, Findings, Passport,
   Reports). Never fabricates data. When there are no findings it
   surfaces "NOT YET ANALYZED" per Phase 3 rules. When there are no
   approved findings it makes the user aware that the Passport rule
   prevents publication.
   ───────────────────────────────────────────────────────────── */

const STATUS_META = {
  DRAFT:          { label: "Draft",         color: "var(--nx-text-secondary)", icon: Circle },
  PENDING_REVIEW: { label: "Pending Review",color: "var(--nx-gold)",           icon: Clock },
  APPROVED:       { label: "Approved",      color: "var(--nx-success)",        icon: CheckCircle2 },
  REJECTED:       { label: "Rejected",      color: "var(--nx-critical)",       icon: XCircle },
  RESOLVED:       { label: "Resolved",      color: "var(--nx-cyan)",           icon: ShieldCheck },
  SUPERSEDED:     { label: "Superseded",    color: "var(--nx-text-muted)",     icon: RefreshCw },
};

const SEVERITY_ORDER = ["CRITICAL", "MAJOR", "MODERATE", "MINOR", "INFORMATIONAL"];
const SEVERITY_COLOR = {
  CRITICAL:      "var(--nx-critical)",
  MAJOR:         "var(--nx-orange)",
  MODERATE:      "var(--nx-gold)",
  MINOR:         "var(--nx-cyan)",
  INFORMATIONAL: "var(--nx-text-secondary)",
};

export default function PropertyIntelligenceSummary({
  propertyId,
  audience = "internal",
  compact = false,
  showLink = true,
  reloadKey = 0,
}) {
  const [summary, setSummary] = useState(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState(null);

  useEffect(() => {
    if (!propertyId) return;
    setLoading(true);
    setErr(null);
    nxIntelligenceSummary(propertyId, audience)
      .then(setSummary)
      .catch((e) => setErr(e?.response?.data?.detail || e.message))
      .finally(() => setLoading(false));
  }, [propertyId, audience, reloadKey]);

  if (loading) {
    return (
      <div className="nx-card" data-testid="pie-summary-loading">
        <div className="nx-label">Property Intelligence Summary</div>
        <div style={{ color: "var(--nx-text-muted)", marginTop: 6 }}>Loading…</div>
      </div>
    );
  }
  if (err) {
    return (
      <div className="nx-card" data-testid="pie-summary-error">
        <div className="nx-label" style={{ color: "var(--nx-critical)" }}>PIE Summary Error</div>
        <div style={{ color: "var(--nx-text-secondary)", marginTop: 6, fontSize: 12 }}>{String(err)}</div>
      </div>
    );
  }
  if (!summary) return null;

  // Homeowner / public — restricted subset (only approved counts).
  if (audience === "homeowner" || audience === "public") {
    return <HomeownerSummary summary={summary} compact={compact} />;
  }

  const {
    any_findings, any_approved, counts_by_status,
    approved_by_severity, completeness_pct,
    approved_manual_observation_count, habitat_visible_approved_count,
    latest_approved_at,
  } = summary;

  if (!any_findings) {
    return (
      <div className="nx-card" data-testid="pie-summary-not-analyzed">
        <div className="nx-flex-between">
          <div>
            <div className="nx-label">Property Intelligence Summary</div>
            <div style={{ fontSize: 18, color: "#fff", fontWeight: 700, marginTop: 4 }}>
              NOT YET ANALYZED
            </div>
            <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
              No findings have been authored on this property. Create the first draft to begin.
            </div>
          </div>
          {showLink && (
            <Link
              to={`/nextgen/properties/${propertyId}/findings`}
              className="nx-btn"
              data-testid="pie-summary-open-findings"
            >
              Author First Finding <ArrowUpRight size={14} strokeWidth={1.8} />
            </Link>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="nx-card" data-testid="pie-summary">
      <div className="nx-flex-between" style={{ marginBottom: 12 }}>
        <div>
          <div className="nx-label">Property Intelligence Summary</div>
          <div style={{ fontSize: 18, color: "#fff", fontWeight: 700, marginTop: 4 }}>
            {any_approved ? "PIE OPERATIONAL" : "AWAITING APPROVAL"}
          </div>
        </div>
        {showLink && (
          <Link
            to={`/nextgen/properties/${propertyId}/findings`}
            className="nx-btn ghost"
            data-testid="pie-summary-open-findings"
          >
            Open Findings <ArrowUpRight size={14} strokeWidth={1.8} />
          </Link>
        )}
      </div>

      {!any_approved && (
        <div className="nx-notice" data-testid="pie-summary-passport-warning" style={{ marginBottom: 12 }}>
          <Info size={14} strokeWidth={1.8} />
          <span>
            No approved findings yet — the Passport ledger cannot be updated until a
            reviewer with CEO / Admin / GM authority approves at least one finding.
          </span>
        </div>
      )}

      <div className="nx-grid cols-3" data-testid="pie-summary-status-counts">
        {Object.keys(counts_by_status).map((s) => {
          const meta = STATUS_META[s] || STATUS_META.DRAFT;
          const Icon = meta.icon;
          return (
            <div
              key={s}
              className="nx-metric-block"
              data-testid={`pie-status-${s.toLowerCase()}`}
            >
              <div className="k" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <Icon size={12} strokeWidth={1.8} color={meta.color} /> {meta.label}
              </div>
              <div className="v" style={{ fontSize: 24, color: meta.color }}>
                {counts_by_status[s] || 0}
              </div>
            </div>
          );
        })}
      </div>

      {any_approved && !compact && (
        <>
          <div style={{ marginTop: 16 }} className="nx-label">
            Approved · Severity Breakdown
          </div>
          <div className="nx-flex nx-gap-3" data-testid="pie-summary-severity" style={{ flexWrap: "wrap" }}>
            {SEVERITY_ORDER.map((sev) => (
              <span
                key={sev}
                className="nx-pill"
                style={{ color: SEVERITY_COLOR[sev], borderColor: SEVERITY_COLOR[sev] }}
                data-testid={`pie-severity-${sev.toLowerCase()}`}
              >
                {sev} · {approved_by_severity?.[sev] || 0}
              </span>
            ))}
          </div>
        </>
      )}

      {!compact && (
        <div style={{ marginTop: 16 }} className="nx-flex nx-gap-3" data-testid="pie-summary-meta">
          <span className="nx-pill cyan">
            Completeness · {completeness_pct == null ? "—" : `${completeness_pct}%`}
          </span>
          {approved_manual_observation_count > 0 && (
            <span
              className="nx-pill"
              style={{ color: "var(--nx-gold)", borderColor: "var(--nx-gold)" }}
              data-testid="pie-summary-manual-observations"
            >
              MANUAL OBSERVATIONS · {approved_manual_observation_count}
            </span>
          )}
          {habitat_visible_approved_count > 0 && (
            <span className="nx-pill">
              Homeowner-visible · {habitat_visible_approved_count}
            </span>
          )}
          {latest_approved_at && (
            <span className="nx-label">
              Latest approval · {latest_approved_at.slice(0, 19).replace("T", " ")}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

function HomeownerSummary({ summary, compact }) {
  const total = summary.approved_count || 0;
  return (
    <div className="nx-card" data-testid="pie-summary-homeowner">
      <div className="nx-label">Property Intelligence</div>
      <div style={{ fontSize: 18, color: "#fff", fontWeight: 700, marginTop: 4 }}>
        {total === 0 ? "NOT YET ANALYZED" : `${total} findings on record`}
      </div>
      {total > 0 && !compact && (
        <div className="nx-flex nx-gap-3" style={{ flexWrap: "wrap", marginTop: 10 }}>
          {SEVERITY_ORDER.map((sev) => (
            <span
              key={sev}
              className="nx-pill"
              style={{ color: SEVERITY_COLOR[sev], borderColor: SEVERITY_COLOR[sev] }}
            >
              {sev} · {summary.approved_by_severity?.[sev] || 0}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
