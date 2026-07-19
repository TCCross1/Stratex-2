import React, { useEffect, useState, useMemo, useCallback } from "react";
import { NavLink, Outlet, useParams, Link, useLocation } from "react-router-dom";
import {
  Home, Briefcase, Camera, Layers, Ruler, DoorOpen, Package,
  Waves, AlertCircle, Calculator, FileText, ShieldCheck, Share2,
  Folder, History, ScrollText, ArrowUpRight, Building2,
  ChevronRight, Box, MapPin,
} from "lucide-react";
import { nxGetProperty, nxListMissions, nxPropertyPassport,
  nxPropertyTimeline, nxPropertyAwe, nxListHabitatGrants } from "@/nextgen/api";
import { DemoDataBadge } from "@/nextgen/Placeholder";

/* Property Workspace Shell (Phase 2 · canonical property & job workspace).
   ONE shared shell wraps every /nextgen/properties/:propertyId/* route. */

const WORKSPACE_NAV = [
  { seg: "overview",        label: "Overview",          icon: Home,          impl: true },
  { seg: "jobs",            label: "Jobs",              icon: Briefcase,     impl: true },
  { seg: "mission-capture", label: "Mission & Capture", icon: Camera,        impl: true },
  { seg: "evidence",        label: "Evidence",          icon: Camera,        impl: true },
  { seg: "digital-twin",    label: "Digital Twin",      icon: Box,           impl: false },
  { seg: "cad-bim",         label: "CAD / BIM",         icon: Layers,        impl: false },
  { seg: "measurements",    label: "Measurements",      icon: Ruler,         impl: false },
  { seg: "openings",        label: "Windows & Doors",   icon: DoorOpen,      impl: false },
  { seg: "materials",       label: "Materials",         icon: Package,       impl: false },
  { seg: "awe",             label: "AWE",               icon: Waves,         impl: true },
  { seg: "findings",        label: "Findings",          icon: AlertCircle,   impl: false },
  { seg: "estimate",        label: "Estimate",          icon: Calculator,    impl: false },
  { seg: "reports",         label: "Reports",           icon: FileText,      impl: true },
  { seg: "passport",        label: "Property Passport", icon: ShieldCheck,   impl: true },
  { seg: "habitat",         label: "Habitat",           icon: Share2,        impl: true },
  { seg: "documents",       label: "Documents",         icon: Folder,        impl: false },
  { seg: "history",         label: "History",           icon: History,       impl: true },
  { seg: "audit",           label: "Audit",             icon: ScrollText,    impl: true },
];

/* Workflow status vocabulary (Phase 2 §C). Import this vocabulary
   everywhere status is displayed so the workspace speaks one language. */
export const STATUS = {
  COMPLETE:            { label: "Complete",           pill: "ok" },
  IN_PROGRESS:         { label: "In Progress",        pill: "cyan" },
  REQUIRED:            { label: "Required",           pill: "orange" },
  MISSING:             { label: "Missing",            pill: "warn" },
  NOT_ORDERED:         { label: "Not Ordered",        pill: "dim" },
  NOT_APPLICABLE:      { label: "Not Applicable",     pill: "dim" },
  AWAITING_APPROVAL:   { label: "Awaiting Approval",  pill: "gold" },
  BLOCKED:             { label: "Blocked",            pill: "danger" },
  NOT_YET_IMPLEMENTED: { label: "Not Yet Implemented",pill: "dim" },
};

/** Reusable status pill (used across the whole workspace). */
export function StatusPill({ status = "NOT_ORDERED", label, testId }) {
  const s = STATUS[status] || STATUS.NOT_ORDERED;
  return (
    <span
      className={`nx-pill ${s.pill}`}
      data-testid={testId || `status-${status}`}
      style={{ whiteSpace: "nowrap" }}
    >
      {label || s.label}
    </span>
  );
}

/** Reusable workflow-status row: label + status + optional hint / cta. */
export function WorkflowStatusRow({ label, status, hint, cta, testId }) {
  return (
    <div className="nx-workflow-row" data-testid={testId}>
      <div className="nx-workflow-row-label">{label}</div>
      <StatusPill status={status} />
      {hint && <div className="nx-workflow-row-hint">{hint}</div>}
      {cta && (
        <Link to={cta.to} className="nx-card-action" data-testid={`${testId}-cta`}>
          {cta.label} <ArrowUpRight size={13} strokeWidth={1.8} />
        </Link>
      )}
    </div>
  );
}

/* Provenance chip. Never fabricated — if source data is absent, we
   surface "PROVENANCE NOT YET AVAILABLE" per Phase 2 §G. */
export function ProvenanceChip({ mission, evidence, approvedBy, confidence, at, testId }) {
  const parts = [];
  if (mission)    parts.push(`mission·${String(mission).slice(0, 8)}`);
  if (evidence)   parts.push(`ev·${String(evidence).slice(0, 8)}`);
  if (approvedBy) parts.push(`by·${approvedBy}`);
  if (confidence != null) parts.push(`conf·${confidence}%`);
  if (at)         parts.push(new Date(at).toISOString().slice(0, 10));
  if (parts.length === 0) {
    return (
      <span className="nx-pill dim" data-testid={testId || "provenance-missing"}>
        PROVENANCE NOT YET AVAILABLE
      </span>
    );
  }
  return (
    <span className="nx-pill cyan" data-testid={testId || "provenance"} style={{ fontFamily: "var(--nx-font-mono)" }}>
      {parts.join(" · ")}
    </span>
  );
}

/* ── Property Workspace Shell ──────────────────────────────── */
export default function PropertyWorkspaceShell() {
  const { propertyId } = useParams();
  const loc = useLocation();
  const [prop, setProp] = useState(null);
  const [missions, setMissions] = useState([]);
  const [err, setErr] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    if (!propertyId) return;
    setLoading(true);
    Promise.all([
      nxGetProperty(propertyId).catch((e) => { throw e; }),
      nxListMissions(propertyId).catch(() => ({ items: [] })),
    ])
      .then(([p, m]) => {
        setProp(p);
        setMissions((m.items || []).filter((mm) => mm.property_id === propertyId));
        setErr(null);
      })
      .catch((e) => {
        const detail = e?.response?.data?.detail || e.message;
        setErr({ status: e?.response?.status, detail });
      })
      .finally(() => setLoading(false));
  }, [propertyId]);

  useEffect(() => { load(); }, [load]);

  if (loading && !prop) return <WorkspaceLoading />;
  if (err) return <WorkspaceError err={err} propertyId={propertyId} />;

  const activeMission = missions.find(
    (m) => m.stage > 0 && m.stage < 15 && m.state !== "COMPLETED",
  );

  const ctx = {
    propertyId,
    property: prop?.property || prop,
    missions,
    activeMission,
    reload: load,
  };

  return (
    <div className="nx-workspace" data-testid="nx-property-workspace">
      <Breadcrumbs propertyId={propertyId} loc={loc} />
      <PropertyHeader ctx={ctx} />
      <WorkspaceNav propertyId={propertyId} />
      <div className="nx-workspace-body">
        <Outlet context={ctx} />
      </div>
    </div>
  );
}

function Breadcrumbs({ propertyId, loc }) {
  const parts = loc.pathname.split("/").filter(Boolean);
  const segIdx = parts.indexOf("properties");
  const current = parts[segIdx + 2] || "overview";
  const currentLabel = WORKSPACE_NAV.find((w) => w.seg === current)?.label || current;
  return (
    <nav className="nx-breadcrumbs" data-testid="nx-workspace-breadcrumbs" aria-label="Breadcrumb">
      <Link to="/nextgen">Home</Link>
      <ChevronRight size={13} strokeWidth={1.8} />
      <Link to="/nextgen/properties">Jobs & Properties</Link>
      <ChevronRight size={13} strokeWidth={1.8} />
      <Link to={`/nextgen/properties/${propertyId}/overview`}>
        {propertyId.slice(0, 8).toUpperCase()}
      </Link>
      <ChevronRight size={13} strokeWidth={1.8} />
      <span aria-current="page">{currentLabel}</span>
    </nav>
  );
}

function PropertyHeader({ ctx }) {
  const p = ctx.property;
  if (!p) return null;
  const a = p.address || {};
  const activeCount = ctx.missions.filter(
    (m) => m.stage > 0 && m.stage < 15 && m.state !== "COMPLETED",
  ).length;
  const completedCount = ctx.missions.filter(
    (m) => m.stage >= 14 || m.state === "COMPLETED",
  ).length;

  return (
    <header className="nx-property-header" data-testid="nx-workspace-header">
      <div className="nx-flex" style={{ gap: 14, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div className="nx-property-header-icon">
          <Building2 size={22} strokeWidth={1.6} />
        </div>
        <div style={{ flex: 1, minWidth: 240 }}>
          <div className="nx-label">Property · {p.canonical_id?.slice(0, 12) || "—"}</div>
          <h1 className="nx-property-header-title">
            {a.line1 || "(no address)"}
          </h1>
          <div className="nx-property-header-sub">
            <MapPin size={13} strokeWidth={1.8} />
            <span>{a.city || "—"}, {a.region || "—"} {a.postal_code || ""}</span>
          </div>
        </div>
        <div className="nx-property-header-stats">
          <div className="nx-metric-block">
            <div className="k">Active Jobs</div>
            <div className="v cy" style={{ fontSize: 26 }}>{activeCount}</div>
          </div>
          <div className="nx-metric-block">
            <div className="k">Completed</div>
            <div className="v" style={{ fontSize: 26 }}>{completedCount}</div>
          </div>
        </div>
      </div>
    </header>
  );
}

function WorkspaceNav({ propertyId }) {
  return (
    <nav className="nx-workspace-nav" aria-label="Property workspace">
      <div className="nx-workspace-nav-scroll" data-testid="nx-workspace-nav">
        {WORKSPACE_NAV.map((w) => (
          <NavLink
            key={w.seg}
            to={`/nextgen/properties/${propertyId}/${w.seg}`}
            className={({ isActive }) => `nx-workspace-nav-item ${isActive ? "active" : ""}`}
            data-testid={`nx-ws-nav-${w.seg}`}
          >
            <w.icon size={14} strokeWidth={1.7} />
            <span>{w.label}</span>
            {!w.impl && <span className="nx-workspace-nav-dot" title="Not yet implemented" />}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}

function WorkspaceLoading() {
  return <div className="nx-empty" data-testid="nx-workspace-loading">Loading property workspace…</div>;
}

function WorkspaceError({ err, propertyId }) {
  const status = err?.status;
  const isNotFound = status === 404;
  const isUnauthorized = status === 401 || status === 403;
  return (
    <div data-testid={isNotFound ? "nx-workspace-not-found" : isUnauthorized ? "nx-workspace-unauthorized" : "nx-workspace-error"}>
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow" style={{ color: "var(--nx-critical)" }}>
            // {isNotFound ? "NOT FOUND" : isUnauthorized ? "ACCESS DENIED" : "ERROR"}
          </div>
          <h1 className="nx-page-title">
            {isNotFound ? "Property not found" : isUnauthorized ? "Not authorized" : "Could not load property"}
          </h1>
          <div className="nx-page-sub">
            {isNotFound && (<>The property <code style={{ color: "var(--nx-cyan)" }}>{propertyId}</code> does not exist or is not visible to your tenant.</>)}
            {isUnauthorized && (<>Your role does not include access to this property.</>)}
            {!isNotFound && !isUnauthorized && <>Details: {String(err?.detail)}</>}
          </div>
        </div>
      </div>
      <Link to="/nextgen/properties" className="nx-btn ghost">Back to Jobs & Properties</Link>
    </div>
  );
}
