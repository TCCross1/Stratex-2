import React, { useEffect, useState, useMemo } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  ArrowUpRight, CheckCircle2, Camera, Cpu, ShieldCheck, Share2,
  FileText, Waves, AlertCircle, Calculator, Layers, Ruler, DoorOpen,
  Package, Folder, Box, History as HistoryIcon, ScrollText,
} from "lucide-react";
import {
  nxPropertyPassport, nxPropertyTimeline, nxPropertyAwe,
  nxListHabitatGrants, nxReportTemplates, nxPropertyReport, nxOpenReportHtml,
} from "@/nextgen/api";
import { StatusPill, WorkflowStatusRow, ProvenanceChip, STATUS } from "@/nextgen/PropertyWorkspaceShell";
import Placeholder, { DemoDataBadge } from "@/nextgen/Placeholder";

/* Property Workspace destinations (Phase 2).
   Fully connected: Overview, Jobs, Mission&Capture, Evidence, AWE,
   Reports, Passport, Habitat, History, Audit.
   Workspace-native status pages (real data + gaps + provenance) for:
     Digital Twin, CAD/BIM, Measurements, Openings, Materials,
     Findings, Estimate, Documents. */

/* ── Overview ──────────────────────────────────────────────── */
export function OverviewPage() {
  const { property, propertyId, missions, activeMission } = useOutletContext();
  const [awe, setAwe] = useState(null);
  const [passport, setPassport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [grants, setGrants] = useState([]);

  useEffect(() => {
    if (!propertyId) return;
    nxPropertyAwe(propertyId).then((r) => setAwe(r.awe)).catch(() => {});
    nxPropertyPassport(propertyId, "internal").then(setPassport).catch(() => {});
    nxPropertyTimeline(propertyId).then((r) => setTimeline(r.items || [])).catch(() => {});
    nxListHabitatGrants(propertyId).then((r) => setGrants(r.items || r.grants || [])).catch(() => {});
  }, [propertyId]);

  const stage = activeMission?.stage ?? 0;
  const rows = useMemo(() => ([
    { label: "Property Identity", status: property ? "COMPLETE" : "MISSING",
      hint: property?.canonical_id?.slice(0, 12) },
    { label: "Active Job",        status: activeMission ? "IN_PROGRESS" : missions.length ? "COMPLETE" : "NOT_ORDERED",
      hint: activeMission ? `Stage ${stage}/15 · ${activeMission.product}` : missions.length ? `${missions.length} archived` : "No jobs yet",
      cta: activeMission ? { to: `/nextgen/missions/${activeMission.canonical_id}`, label: "Open" } : null },
    { label: "Mission Progress",  status: !activeMission ? "NOT_APPLICABLE" : stage >= 14 ? "COMPLETE" : "IN_PROGRESS",
      hint: activeMission ? `Stage ${stage}/15` : "n/a" },
    { label: "Capture & Evidence",status: !activeMission ? "NOT_APPLICABLE" : stage >= 5 ? "COMPLETE" : stage >= 3 ? "IN_PROGRESS" : "REQUIRED",
      cta: activeMission ? { to: `/nextgen/missions/${activeMission.canonical_id}/evidence`, label: "Evidence" } : null },
    { label: "Findings Summary",  status: "NOT_YET_IMPLEMENTED",
      hint: "Findings engine ships in a later phase" },
    { label: "AWE Composite",     status: awe ? "COMPLETE" : "NOT_ORDERED",
      hint: awe ? `${awe.composite_index} · ${awe.release_state.replace(/_/g, " ")}` : "no AWE yet",
      cta: awe ? { to: `/nextgen/properties/${propertyId}/awe`, label: "Details" } : null },
    { label: "Estimate Readiness",status: "NOT_YET_IMPLEMENTED",
      hint: "Estimating engine ships in a later phase" },
    { label: "Report Readiness",  status: awe ? "COMPLETE" : "NOT_ORDERED",
      cta: { to: `/nextgen/properties/${propertyId}/reports`, label: "Reports" } },
    { label: "Passport Update",   status: passport?.passport ? "COMPLETE" : "NOT_ORDERED",
      hint: passport?.entries?.length ? `${passport.entries.length} entries` : "no passport yet",
      cta: passport?.passport ? { to: `/nextgen/properties/${propertyId}/passport`, label: "Ledger" } : null },
    { label: "Habitat Sync",      status: grants.some((g) => !g.revoked_at) ? "COMPLETE" : "NOT_ORDERED",
      hint: grants.length ? `${grants.length} link(s) issued` : "no share yet",
      cta: grants.length ? { to: `/nextgen/properties/${propertyId}/habitat`, label: "Manage" } : null },
  ]), [property, activeMission, missions, awe, passport, grants, propertyId, stage]);

  const nextAction = deriveNextAction({ activeMission, missions, awe, passport });

  return (
    <div data-testid="nx-ws-overview">
      {/* Next Action */}
      <section className="nx-card elevated" data-testid="nx-ws-next-action">
        <div className="nx-flex-between">
          <div>
            <div className="nx-label">Next Action</div>
            <div style={{ fontSize: 20, color: "#fff", fontWeight: 700, marginTop: 4 }}>
              {nextAction.title}
            </div>
            <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
              {nextAction.subtitle}
            </div>
          </div>
          {nextAction.to && (
            <Link to={nextAction.to} className="nx-btn" data-testid="nx-ws-next-action-cta">
              {nextAction.cta} <ArrowUpRight size={14} strokeWidth={1.8} />
            </Link>
          )}
        </div>
      </section>

      {/* Workflow status */}
      <div className="nx-section-title">
        <span className="num">§01</span>
        <span className="label">Workflow Status</span>
        <span className="rule" />
      </div>
      <div className="nx-card" style={{ padding: 0 }} data-testid="nx-ws-workflow">
        {rows.map((r, i) => (
          <WorkflowStatusRow
            key={i}
            label={r.label}
            status={r.status}
            hint={r.hint}
            cta={r.cta}
            testId={`nx-ws-flow-${r.label.toLowerCase().replace(/\W+/g, "-")}`}
          />
        ))}
      </div>

      {/* AWE quick */}
      {awe && (
        <>
          <div className="nx-section-title">
            <span className="num">§02</span>
            <span className="label">AWE Composite</span>
            <span className="rule" />
            <Link className="nx-card-action" to={`/nextgen/properties/${propertyId}/awe`}>
              Details <ArrowUpRight size={13} strokeWidth={1.8} />
            </Link>
          </div>
          <div className="nx-grid cols-4" data-testid="nx-ws-awe-metrics">
            <MiniMetric k="Air" v={awe.air.score} tint="cy"/>
            <MiniMetric k="Water" v={awe.water.score} tint="cy"/>
            <MiniMetric k="Energy" v={awe.energy.score} tint="or"/>
            <MiniMetric k="Composite" v={awe.composite_index} tint="gd"/>
          </div>
        </>
      )}

      {/* Recent activity */}
      <div className="nx-section-title">
        <span className="num">§03</span>
        <span className="label">Recent Activity</span>
        <span className="rule" />
      </div>
      {timeline.length === 0 ? (
        <div className="nx-empty" data-testid="nx-ws-timeline-empty">No activity yet</div>
      ) : (
        <div className="nx-card" style={{ padding: 0 }} data-testid="nx-ws-timeline">
          {timeline.slice(0, 6).map((t) => (
            <div key={t.canonical_id} className="nx-timeline-row">
              <span className="dot" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="nx-flex-between">
                  <span style={{ color: "#fff", fontSize: 14 }}>{t.summary}</span>
                  <span className="nx-pill">{t.kind}</span>
                </div>
                <div className="nx-label" style={{ marginTop: 4 }}>{t.at?.slice(0, 19).replace("T", " ")}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MiniMetric({ k, v, tint }) {
  return (
    <div className="nx-metric-block">
      <div className="k">{k}</div>
      <div className={`v ${tint || ""}`} style={{ fontSize: 28 }}>{v ?? "—"}</div>
    </div>
  );
}

function deriveNextAction({ activeMission, missions, awe, passport }) {
  if (!missions?.length) return {
    title: "Create the first job for this property",
    subtitle: "Bind a Stratex product to this property to start the 15-stage operational chain.",
    cta: "New Mission",
    to: "/nextgen/missions/new",
  };
  if (activeMission && activeMission.stage < 5) return {
    title: "Capture required evidence",
    subtitle: `Mission is at stage ${activeMission.stage}/15 · needs field capture.`,
    cta: "Open Evidence",
    to: `/nextgen/missions/${activeMission.canonical_id}/evidence`,
  };
  if (activeMission && activeMission.stage < 8) return {
    title: "Complete QA review",
    subtitle: `Mission is at stage ${activeMission.stage}/15 · awaiting QA sign-off.`,
    cta: "Open Mission",
    to: `/nextgen/missions/${activeMission.canonical_id}`,
  };
  if (!awe) return {
    title: "Order an AWE scan",
    subtitle: "This property has no AWE composite yet.",
    cta: "New Mission",
    to: "/nextgen/missions/new",
  };
  if (!passport?.passport) return {
    title: "Approve intelligence to enrich the Passport",
    subtitle: "The persistent property record has no approved entries yet.",
    cta: "Open Missions",
    to: "/nextgen/missions",
  };
  return {
    title: "All caught up",
    subtitle: "Every current workflow step for this property is complete.",
    cta: null,
    to: null,
  };
}

/* ── Jobs ──────────────────────────────────────────────────── */
export function JobsPage() {
  const { propertyId, missions } = useOutletContext();
  return (
    <div data-testid="nx-ws-jobs">
      <div className="nx-flex-between" style={{ marginBottom: 12 }}>
        <div>
          <div className="nx-label">All Jobs for this Property</div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
            Every job is bound to this canonical property. Legacy contractor tools remain
            reachable at their existing paths — this workspace is the canonical index.
          </div>
        </div>
        <Link to={`/nextgen/missions/new?property=${propertyId}`} className="nx-btn" data-testid="nx-ws-jobs-new">
          New Job
        </Link>
      </div>
      {missions.length === 0 ? (
        <div className="nx-empty" data-testid="nx-ws-jobs-empty">No jobs yet — create one</div>
      ) : (
        <div className="nx-card" style={{ padding: 0 }}>
          <table className="nx-table">
            <thead>
              <tr><th>Mission</th><th>Product</th><th>Stage</th><th>State</th><th>Created</th><th></th></tr>
            </thead>
            <tbody>
              {missions.map((m) => (
                <tr key={m.canonical_id}>
                  <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-orange)" }}>
                    {m.canonical_id.slice(0, 12)}
                  </td>
                  <td>{m.product?.replace(/_/g, " ")}</td>
                  <td><span className="nx-pill cyan">{m.stage}/15</span></td>
                  <td><StatusPill status={
                    m.state === "COMPLETED" || m.stage >= 14 ? "COMPLETE"
                    : m.stage < 5 ? "IN_PROGRESS"
                    : "IN_PROGRESS"
                  }/></td>
                  <td style={{ fontSize: 12, color: "var(--nx-text-muted)" }}>
                    {m.created_at?.slice(0, 10)}
                  </td>
                  <td>
                    <Link to={`/nextgen/missions/${m.canonical_id}`} className="nx-card-action"
                      data-testid={`nx-ws-job-${m.canonical_id}`}>
                      Open <ArrowUpRight size={13} strokeWidth={1.8} />
                    </Link>
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

/* ── Mission & Capture — links straight into the mission command ── */
export function MissionCapturePage() {
  const { activeMission, propertyId } = useOutletContext();
  if (!activeMission) {
    return (
      <div data-testid="nx-ws-mission-capture-empty">
        <div className="nx-empty">No active mission — open Jobs to start one.</div>
        <div style={{ marginTop: 14 }}>
          <Link to={`/nextgen/properties/${propertyId}/jobs`} className="nx-btn ghost">
            Open Jobs <ArrowUpRight size={14} strokeWidth={1.8} />
          </Link>
        </div>
      </div>
    );
  }
  return (
    <div data-testid="nx-ws-mission-capture">
      <div className="nx-card elevated">
        <div className="nx-flex-between">
          <div>
            <div className="nx-label">Active Mission</div>
            <div style={{ fontSize: 20, color: "#fff", fontWeight: 700, marginTop: 4 }}>
              {activeMission.product.replace(/_/g, " ")} · Stage {activeMission.stage}/15
            </div>
          </div>
          <StatusPill status={
            activeMission.stage >= 14 ? "COMPLETE"
            : activeMission.stage < 5 ? "IN_PROGRESS"
            : "IN_PROGRESS"
          }/>
        </div>
        <div className="nx-flex nx-gap-3" style={{ marginTop: 20, flexWrap: "wrap" }}>
          <Link to={`/nextgen/missions/${activeMission.canonical_id}`} className="nx-btn">
            <Camera size={15} /> Open Mission Command
          </Link>
          <Link to={`/nextgen/missions/${activeMission.canonical_id}/evidence`} className="nx-btn ghost">
            Evidence Workspace
          </Link>
          <Link to={`/nextgen/missions/${activeMission.canonical_id}/intelligence`} className="nx-btn ghost">
            Intelligence
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ── Evidence — provenance-first summary of every mission's evidence ── */
export function EvidencePage() {
  const { missions, propertyId } = useOutletContext();
  return (
    <div data-testid="nx-ws-evidence">
      <div className="nx-label">Evidence Across All Jobs</div>
      <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4, marginBottom: 14 }}>
        Content-addressed evidence bytes are immutable. Every item carries SHA-256 + mission provenance.
      </div>
      {missions.length === 0 ? (
        <div className="nx-empty">No jobs / no evidence yet.</div>
      ) : (
        <div className="nx-grid cols-2" data-testid="nx-ws-evidence-grid">
          {missions.map((m) => (
            <div key={m.canonical_id} className="nx-card">
              <div className="nx-flex-between">
                <div>
                  <div className="nx-label">Mission</div>
                  <div style={{ color: "#fff", fontWeight: 600, marginTop: 4 }}>
                    {m.product.replace(/_/g, " ")}
                  </div>
                </div>
                <StatusPill status={m.stage >= 5 ? "COMPLETE" : m.stage >= 3 ? "IN_PROGRESS" : "REQUIRED"} />
              </div>
              <ProvenanceChip mission={m.canonical_id} at={m.created_at}/>
              <div style={{ marginTop: 12 }}>
                <Link to={`/nextgen/missions/${m.canonical_id}/evidence`} className="nx-btn ghost small"
                      data-testid={`nx-ws-ev-${m.canonical_id}`}>
                  Open Evidence <ArrowUpRight size={13} strokeWidth={1.8} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── AWE — property-scoped composite score ─────────────────── */
export function AwePage() {
  const { propertyId } = useOutletContext();
  const [awe, setAwe] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    nxPropertyAwe(propertyId).then((r) => setAwe(r.awe)).finally(() => setLoading(false));
  }, [propertyId]);

  if (loading) return <div className="nx-empty">Loading AWE…</div>;
  if (!awe) return (
    <div data-testid="nx-ws-awe-empty">
      <div className="nx-empty">No AWE composite yet for this property.</div>
      <div style={{ marginTop: 14 }}>
        <Link to="/nextgen/awe" className="nx-btn ghost">Open AWE workspace <ArrowUpRight size={14}/></Link>
      </div>
    </div>
  );
  return (
    <div data-testid="nx-ws-awe">
      <div className="nx-flex nx-gap-3" style={{ alignItems: "center", marginBottom: 14, flexWrap: "wrap" }}>
        <StatusPill status={awe.release_state === "CALIBRATED_GENERAL" ? "COMPLETE" : "AWAITING_APPROVAL"}
          label={awe.release_state.replace(/_/g, " ")}/>
        <span className="nx-label">Confidence · {awe.confidence_pct}%</span>
        <span className="nx-label">Evidence · {awe.evidence_completeness_pct}%</span>
      </div>
      <div className="nx-grid cols-4" data-testid="nx-ws-awe-grid">
        <MiniMetric k="Air" v={awe.air.score} tint="cy"/>
        <MiniMetric k="Water" v={awe.water.score} tint="cy"/>
        <MiniMetric k="Energy" v={awe.energy.score} tint="or"/>
        <MiniMetric k="Composite" v={awe.composite_index} tint="gd"/>
      </div>
      <div style={{ marginTop: 16 }}>
        <Link to="/nextgen/awe" className="nx-btn ghost">
          Full AWE workspace <ArrowUpRight size={14} strokeWidth={1.8}/>
        </Link>
      </div>
    </div>
  );
}

/* ── Reports — property-scoped ─────────────────────────────── */
export function ReportsPage() {
  const { propertyId } = useOutletContext();
  const [templates, setTemplates] = useState([]);
  useEffect(() => { nxReportTemplates().then((d) => setTemplates(d.templates || [])); }, []);
  return (
    <div data-testid="nx-ws-reports">
      <div className="nx-label">Report Projections for this Property</div>
      <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4, marginBottom: 14 }}>
        Reports are read-only projections of approved intelligence.
      </div>
      <div className="nx-grid cols-3">
        {templates.map((t) => (
          <button
            key={t}
            className="nx-report-tile-mini"
            onClick={() => nxOpenReportHtml(propertyId, t)}
            data-testid={`nx-ws-report-${t}`}
          >
            <FileText size={18} strokeWidth={1.6} color="var(--nx-cyan)"/>
            <div style={{ flex: 1, textAlign: "left" }}>
              <div style={{ color: "#fff", fontSize: 14, fontWeight: 600 }}>
                {t.replace(/_/g, " ")}
              </div>
              <div style={{ color: "var(--nx-text-muted)", fontSize: 11 }}>Open HTML preview</div>
            </div>
            <ArrowUpRight size={16} strokeWidth={1.8} color="var(--nx-cyan)"/>
          </button>
        ))}
      </div>
      <div className="nx-notice" style={{ marginTop: 18 }}>
        <AlertCircle size={16} strokeWidth={1.6}/>
        <span>PDF renderer pending — reports open as HTML previews.</span>
      </div>
    </div>
  );
}

/* ── Passport — property-scoped ledger ─────────────────────── */
export function PassportPage() {
  const { propertyId } = useOutletContext();
  const [passport, setPassport] = useState(null);
  useEffect(() => {
    nxPropertyPassport(propertyId, "internal").then(setPassport).catch(() => setPassport(null));
  }, [propertyId]);
  if (!passport?.passport) {
    return (
      <div data-testid="nx-ws-passport-empty">
        <div className="nx-empty">No passport ledger for this property yet.</div>
        <div className="nx-label" style={{ marginTop: 20 }}>
          The Passport is the canonical persistent record. It updates when intelligence is approved.
        </div>
      </div>
    );
  }
  return (
    <div data-testid="nx-ws-passport">
      <div className="nx-flex nx-gap-3" style={{ marginBottom: 14 }}>
        <StatusPill status="COMPLETE" label="Passport Active"/>
        <span className="nx-label">{passport.entries.length} entries</span>
      </div>
      <div className="nx-card" style={{ padding: 0 }}>
        <table className="nx-table">
          <thead><tr>
            <th>Seq</th><th>Type</th><th>Content Hash</th><th>Signed</th>
          </tr></thead>
          <tbody>
            {passport.entries.map((e) => (
              <tr key={e.canonical_id}>
                <td style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-orange)" }}>#{e.seq}</td>
                <td><span className="nx-pill">{e.entry_type}</span></td>
                <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-success)" }}>
                  {e.content_hash.slice(0, 16)}…
                </td>
                <td style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>
                  {e.at.slice(0, 19).replace("T", " ")}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div style={{ marginTop: 14 }}>
        <Link to="/nextgen/passport" className="nx-btn ghost">
          Full Passport Workspace <ArrowUpRight size={14} strokeWidth={1.8}/>
        </Link>
      </div>
    </div>
  );
}

/* ── Habitat — property-scoped sync status ─────────────────── */
export function HabitatSyncPage() {
  const { propertyId } = useOutletContext();
  const [grants, setGrants] = useState([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    nxListHabitatGrants(propertyId)
      .then((r) => setGrants(r.items || r.grants || []))
      .finally(() => setLoading(false));
  }, [propertyId]);
  const active = grants.filter((g) => !g.revoked_at &&
    (!g.expires_at || new Date(g.expires_at) > new Date()));
  const status = grants.length === 0 ? "NOT_ORDERED"
              : active.length ? "COMPLETE"
              : "AWAITING_APPROVAL";
  return (
    <div data-testid="nx-ws-habitat">
      <div className="nx-flex nx-gap-3" style={{ marginBottom: 14, alignItems: "center" }}>
        <StatusPill status={status} testId="nx-ws-habitat-status"/>
        {loading && <span className="nx-label">Loading…</span>}
        {!loading && <span className="nx-label">{active.length} active / {grants.length} total</span>}
      </div>
      <div className="nx-card">
        <div className="nx-flex" style={{ alignItems: "center", gap: 10 }}>
          <Share2 size={18} strokeWidth={1.6} color="var(--nx-cyan)"/>
          <div>
            <div style={{ color: "#fff", fontWeight: 600 }}>Homeowner-Safe Projection</div>
            <div style={{ color: "var(--nx-text-secondary)", fontSize: 12, marginTop: 4 }}>
              Habitat reads only approved intelligence — internal reviewer identity, tier
              assignments, and confidence numbers are stripped by the projection layer.
            </div>
          </div>
        </div>
        <div style={{ marginTop: 16 }}>
          <Link to="/nextgen/habitat" className="nx-btn">
            Manage Habitat Links <ArrowUpRight size={14} strokeWidth={1.8}/>
          </Link>
        </div>
      </div>
    </div>
  );
}

/* ── History — property timeline ───────────────────────────── */
export function HistoryPage() {
  const { propertyId } = useOutletContext();
  const [timeline, setTimeline] = useState([]);
  useEffect(() => { nxPropertyTimeline(propertyId).then((r) => setTimeline(r.items || [])); }, [propertyId]);
  if (timeline.length === 0) return <div className="nx-empty" data-testid="nx-ws-history-empty">No timeline entries yet</div>;
  return (
    <div data-testid="nx-ws-history">
      <div className="nx-card">
        {timeline.map((t) => (
          <div key={t.canonical_id} className="nx-timeline-row">
            <span className="dot"/>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div className="nx-flex-between">
                <span style={{ color: "#fff", fontSize: 14 }}>{t.summary}</span>
                <span className="nx-pill">{t.kind}</span>
              </div>
              <div className="nx-label" style={{ marginTop: 4 }}>{t.at?.slice(0, 19).replace("T", " ")}</div>
              <ProvenanceChip at={t.at} mission={t.mission_id} testId="nx-ws-history-provenance"/>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Audit — property-scoped audit note ─────────────────────── */
export function AuditPage() {
  const { propertyId } = useOutletContext();
  return (
    <Placeholder
      eyebrow="// AUDIT"
      title="Property Audit"
      description="Property-scoped audit view is planned for Phase 2b. In the meantime, the tenant-wide audit trail is available in the shell nav."
      icon={ScrollText}
      testId="nx-ws-audit"
      relatedLinks={[
        { to: "/nextgen/audit", label: "Full Audit Trail" },
        { to: `/nextgen/properties/${propertyId}/history`, label: "Property History" },
      ]}
    />
  );
}

/* ── Workspace-native gap pages for incomplete integrations ── */
function makeGapPage({ title, icon, description, source }) {
  return function GapPage() {
    return (
      <div data-testid={`nx-ws-gap-${title.toLowerCase().replace(/\W+/g, "-")}`}>
        <div className="nx-flex-between" style={{ marginBottom: 14 }}>
          <div>
            <div className="nx-label">Workspace destination · integration pending</div>
            <div style={{ fontSize: 20, color: "#fff", fontWeight: 700, marginTop: 4 }}>{title}</div>
          </div>
          <DemoDataBadge kind="placeholder" />
        </div>
        <div className="nx-card">
          <div className="nx-flex" style={{ gap: 14, alignItems: "flex-start" }}>
            {React.createElement(icon, { size: 22, strokeWidth: 1.6, color: "var(--nx-cyan)" })}
            <div>
              <div style={{ color: "#fff", fontWeight: 600 }}>Not yet operational for this property</div>
              <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 6, lineHeight: 1.6 }}>
                {description}
              </div>
              <div style={{ marginTop: 12 }}>
                <div className="nx-label">Currently Available Source</div>
                <div style={{ color: "var(--nx-cyan)", fontFamily: "var(--nx-font-mono)", fontSize: 12, marginTop: 4 }}>
                  {source || "None — awaiting integration"}
                </div>
              </div>
              <div style={{ marginTop: 12 }}>
                <StatusPill status="NOT_YET_IMPLEMENTED"/>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  };
}

export const DigitalTwinPage   = makeGapPage({ title: "3D Digital Twin",  icon: Box,
  description: "Photogrammetry-driven twin generation from approved mission imagery. No processor is wired for this property yet.",
  source: "Requires: mission imagery + 3D processor · Phase 2b" });
export const CadBimPage        = makeGapPage({ title: "CAD / BIM Export", icon: Layers,
  description: "IFC / DXF export from the property twin. No exporter is wired yet.",
  source: "Requires: Digital Twin · Phase 2b" });
export const MeasurementsPage  = makeGapPage({ title: "Measurements",     icon: Ruler,
  description: "Automatic elevation, roof-plane, and dimension measurements from the twin. No measurement service is wired yet.",
  source: "Requires: Digital Twin · Phase 2b" });
export const OpeningsPage      = makeGapPage({ title: "Windows & Doors",  icon: DoorOpen,
  description: "Automated openings schedule detection from mission imagery. No detector is wired yet.",
  source: "Requires: mission imagery + vision engine · Phase 2b" });
export const MaterialsPage     = makeGapPage({ title: "Materials",        icon: Package,
  description: "Materials catalog and take-off for this property. No supplier integration is connected yet.",
  source: "Requires: Estimating engine · Phase 3" });
export const FindingsPage      = makeGapPage({ title: "Findings",         icon: AlertCircle,
  description: "Approved property intelligence items (roof damage, water intrusion, thermal anomalies). No findings engine is wired yet for property-scoped display.",
  source: "Requires: Intelligence engine approvals · Phase 2b" });
export const EstimatePage      = makeGapPage({ title: "Estimate",         icon: Calculator,
  description: "Repair / replacement estimate synthesized from findings + materials + labor. No estimating engine is wired yet.",
  source: "Requires: Findings + Materials · Phase 3" });
export const DocumentsPage     = makeGapPage({ title: "Documents",        icon: Folder,
  description: "Property document vault (contracts, permits, warranty, insurance). No document store is wired for this property yet.",
  source: "Requires: Document store integration · Phase 2b" });
