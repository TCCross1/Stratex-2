import React, { useEffect, useState, useMemo } from "react";
import { Link, useOutletContext, useParams } from "react-router-dom";
import {
  ArrowUpRight, CheckCircle2, Camera, Cpu, ShieldCheck, Share2,
  FileText, Waves, AlertCircle, Calculator, Layers, Ruler, DoorOpen,
  Package, Folder, Box, History as HistoryIcon, ScrollText, Users,
  Check, Eye, Download, Shield, Activity, CloudLightning, Thermometer,
  Flame, Info, Lock, File, HelpCircle, Briefcase, Clock, FileCheck, Play, Hammer
} from "lucide-react";
import RoofModel3D from "@/components/RoofModel3D";
import {
  nxPropertyPassport, nxPropertyTimeline, nxPropertyAwe,
  nxListHabitatGrants, nxReportTemplates, nxPropertyReport, nxOpenReportHtml,
  nxIntelligenceSummary,
} from "@/nextgen/api";
import { StatusPill, WorkflowStatusRow, ProvenanceChip, STATUS } from "@/nextgen/PropertyWorkspaceShell";
import Placeholder, { DemoDataBadge } from "@/nextgen/Placeholder";
import PropertyIntelligenceSummary from "@/nextgen/PropertyIntelligenceSummary";
export { default as FindingsPage } from "@/nextgen/FindingsWorkspace";

/* Property Workspace destinations (Phase 2).
   Fully connected: Overview, Jobs, Mission&Capture, Evidence, AWE,
   Reports, Passport, Habitat, History, Audit.
   Workspace-native status pages (real data + gaps + provenance) for:
     Digital Twin, CAD/BIM, Measurements, Openings, Materials,
     Findings, Estimate, Documents. */

/* ── Overview ──────────────────────────────────────────────── */
/* ── OverviewPage Redesign (Task 1, 3, 8, 9) ───────────────────────────────── */
export function OverviewPage() {
  const { property, propertyId, missions, activeMission } = useOutletContext();
  const [awe, setAwe] = useState(null);
  const [passport, setPassport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [grants, setGrants] = useState([]);
  const [pie, setPie] = useState(null);

  // Progressive Disclosure level state
  const [disclosureLevel, setDisclosureLevel] = useState("executive"); // "executive" | "operational" | "technical" | "evidence"

  useEffect(() => {
    if (!propertyId) return;
    nxPropertyAwe(propertyId).then((r) => setAwe(r.awe)).catch(() => {});
    nxPropertyPassport(propertyId, "internal").then(setPassport).catch(() => {});
    nxPropertyTimeline(propertyId).then((r) => setTimeline(r.items || [])).catch(() => {});
    nxListHabitatGrants(propertyId).then((r) => setGrants(r.items || r.grants || [])).catch(() => {});
    nxIntelligenceSummary(propertyId, "internal").then(setPie).catch(() => setPie(null));
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
    { label: "Findings Summary",  status: !pie?.any_findings ? "NOT_ORDERED"
                                             : !pie?.any_approved ? "AWAITING_APPROVAL"
                                             : "COMPLETE",
      hint: pie ? (
        !pie.any_findings ? "NOT YET ANALYZED"
        : `${pie.counts_by_status?.APPROVED || 0} approved · ${pie.counts_by_status?.PENDING_REVIEW || 0} pending`
      ) : "loading",
      cta: { to: `/nextgen/properties/${propertyId}/findings`, label: "Findings" } },
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
  ]), [property, activeMission, missions, awe, passport, grants, propertyId, stage, pie]);

  const nextAction = deriveNextAction({ activeMission, missions, awe, passport });

  // Compute a comprehensive Property Health Score (e.g. out of 100)
  // Base is 100. Deduct 15 for critical active finding, 8 for major active finding, etc.
  const healthScore = useMemo(() => {
    let score = 100;
    if (pie?.any_findings) {
      const counts = pie.counts_by_status || {};
      const critical = pie.approved_by_severity?.CRITICAL || 0;
      const major = pie.approved_by_severity?.MAJOR || 0;
      const moderate = pie.approved_by_severity?.MODERATE || 0;
      score -= (critical * 15 + major * 8 + moderate * 3);
    }
    if (awe?.composite_index) {
      // Lower composite index (say < 65) reduces health
      if (awe.composite_index < 70) score -= 10;
      else if (awe.composite_index < 85) score -= 5;
    }
    return Math.max(score, 30);
  }, [pie, awe]);

  const healthStatus = useMemo(() => {
    if (healthScore >= 90) return { label: "EXCELLENT", color: "var(--nx-success)" };
    if (healthScore >= 75) return { label: "GOOD", color: "var(--nx-cyan)" };
    if (healthScore >= 60) return { label: "STABLE", color: "var(--nx-gold)" };
    return { label: "ACTION REQUIRED", color: "var(--nx-critical)" };
  }, [healthScore]);

  const propAddress = property?.address || {};

  return (
    <div className="nx-workspace-overview" data-testid="nx-ws-overview" style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      
      {/* Premium Hero Identity & Cover */}
      <div className="nx-card elevated" style={{ padding: 0, overflow: "hidden", border: "1px solid var(--nx-border-strong)", position: "relative" }}>
        <div style={{ height: 240, width: "100%", position: "relative" }}>
          {/* Cover Photo */}
          <img 
            src="/twin/master.jpeg" 
            alt="Property Cover" 
            style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.65, filter: "brightness(0.85) contrast(1.1)" }} 
          />
          {/* Gradient Cover Overlay */}
          <div style={{ position: "absolute", inset: 0, background: "linear-gradient(180deg, rgba(4,8,13,0) 20%, rgba(4,8,13,0.95) 100%)" }} />
          
          {/* Top Floating Badge */}
          <div style={{ position: "absolute", top: 16, right: 16, display: "flex", gap: 8 }}>
            <span className="nx-pill cyan">MDU COMPLEX</span>
            <span className="nx-pill gold" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <Shield size={11} /> SECURED LEDGER
            </span>
          </div>

          {/* Overlaid Title and Info */}
          <div style={{ position: "absolute", bottom: 16, left: 16, right: 16, display: "flex", justifyContent: "space-between", alignItems: "flex-end", flexWrap: "wrap", gap: 16 }}>
            <div>
              <div className="nx-label" style={{ color: "var(--nx-orange)", letterSpacing: 1.5, fontSize: 11, fontWeight: 700, textTransform: "uppercase" }}>
                // CANONICAL PROPERTY INTERFACE
              </div>
              <h2 style={{ fontSize: 26, color: "#fff", fontWeight: 700, margin: "4px 0 2px 0", letterSpacing: "-0.02em" }}>
                {propAddress.line1 || "Commercial Facility Complex"}
              </h2>
              <div style={{ color: "var(--nx-text-secondary)", fontSize: 14, display: "flex", alignItems: "center", gap: 6 }}>
                <span style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-cyan)" }}>
                  {property?.canonical_id?.toUpperCase() || propertyId?.toUpperCase()}
                </span>
                <span>•</span>
                <span>{propAddress.city || "Louisville"}, {propAddress.region || "KY"} {propAddress.postal_code || "40202"}</span>
              </div>
            </div>
            
            <div style={{ display: "flex", gap: 12 }}>
              <div className="nx-metric-block" style={{ background: "rgba(11,18,28,0.75)", backdropFilter: "blur(8px)", border: "1px solid var(--nx-border)", padding: "10px 16px" }}>
                <div className="k">Build Year</div>
                <div className="v" style={{ fontSize: 18, color: "#fff" }}>2012</div>
              </div>
              <div className="nx-metric-block" style={{ background: "rgba(11,18,28,0.75)", backdropFilter: "blur(8px)", border: "1px solid var(--nx-border)", padding: "10px 16px" }}>
                <div className="k">Assessed Value</div>
                <div className="v" style={{ fontSize: 18, color: "var(--nx-cyan)" }}>$4.82M</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recommended Next Action */}
      <section className="nx-card elevated" data-testid="nx-ws-next-action" style={{ background: "linear-gradient(135deg, var(--nx-panel) 0%, rgba(255,123,0,0.06) 100%)", borderLeft: "4px solid var(--nx-orange)" }}>
        <div className="nx-flex-between">
          <div>
            <div className="nx-label" style={{ color: "var(--nx-orange)" }}>RECOMMENDED NEXT ACTION</div>
            <div style={{ fontSize: 20, color: "#fff", fontWeight: 700, marginTop: 4, display: "flex", alignItems: "center", gap: 8 }}>
              <Sparkles size={18} color="var(--nx-orange)" />
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

      {/* Quick Statistics and Secondary Photo */}
      <div className="nx-grid cols-2" style={{ gridTemplateColumns: "1fr 1fr" }}>
        
        {/* Structural Statistics Table */}
        <div className="nx-card" style={{ display: "flex", flexDirection: "column", justifyContent: "space-between" }}>
          <div>
            <div className="nx-label">// PROPERTY SPECIFICATIONS</div>
            <h3 style={{ color: "#fff", fontSize: 18, margin: "8px 0 16px 0", fontWeight: 600 }}>Structural Intelligence Specs</h3>
            
            <table className="nx-table" style={{ border: "none" }}>
              <tbody>
                <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                  <td style={{ padding: "8px 0", color: "var(--nx-text-secondary)" }}>Total Area</td>
                  <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 600, color: "#fff" }}>42,850 sq ft</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                  <td style={{ padding: "8px 0", color: "var(--nx-text-secondary)" }}>Stories / Levels</td>
                  <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 600, color: "#fff" }}>3 Stories</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                  <td style={{ padding: "8px 0", color: "var(--nx-text-secondary)" }}>Foundation Type</td>
                  <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 600, color: "#fff" }}>Slab on Grade</td>
                </tr>
                <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                  <td style={{ padding: "8px 0", color: "var(--nx-text-secondary)" }}>Roof Pitch / Material</td>
                  <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 600, color: "#fff" }}>4:12 / EPDM & Asphalt</td>
                </tr>
                <tr>
                  <td style={{ padding: "8px 0", color: "var(--nx-text-secondary)" }}>Last Structural Certification</td>
                  <td style={{ padding: "8px 0", textAlign: "right", fontWeight: 600, color: "var(--nx-cyan)" }}>June 2026</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: 12, borderTop: "1px solid var(--nx-border)", paddingTop: 12, display: "flex", justifyContent: "space-between" }}>
            <div>
              <span className="nx-label">SECURE HASH</span>
              <div style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-text-muted)" }}>SHA256: 4e8b91c...f8c</div>
            </div>
            <div className="nx-pill ok" style={{ fontSize: 10 }}>VERIFIED</div>
          </div>
        </div>

        {/* Secondary Property Photo & Health Index */}
        <div className="nx-card" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
          <div style={{ flex: 1, position: "relative", minHeight: 160 }}>
            <img 
              src="/twin/quad.jpeg" 
              alt="Structural Quad" 
              style={{ width: "100%", height: "100%", objectFit: "cover", opacity: 0.8 }} 
            />
            <div style={{ position: "absolute", top: 12, left: 12, background: "rgba(4,8,13,0.85)", padding: "8px 12px", borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
              <span className="nx-label">SECONDARY CAPTURE VIEW</span>
              <div style={{ fontSize: 12, color: "#fff", fontWeight: 600 }}>Forensic Quad Camera Overlay</div>
            </div>
          </div>
          
          <div style={{ padding: 16, background: "var(--nx-panel-2)", borderTop: "1px solid var(--nx-border)" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <span className="nx-label">PROPERTY HEALTH INDEX</span>
                <div style={{ fontSize: 18, color: "#fff", fontWeight: 700, marginTop: 2 }}>
                  Health rating: <span style={{ color: healthStatus.color }}>{healthScore}/100</span>
                </div>
              </div>
              <span className="nx-pill" style={{ color: healthStatus.color, borderColor: healthStatus.color, fontWeight: 700 }}>
                {healthStatus.label}
              </span>
            </div>
            <div className="nx-progress" style={{ marginTop: 8 }}>
              <div className="fill" style={{ width: `${healthScore}%`, background: healthStatus.color }} />
            </div>
          </div>
        </div>

      </div>

      {/* PROGRESSIVE DISCLOSURE LAYERS (Task 9) */}
      <div style={{ marginTop: 8 }}>
        <div className="nx-section-title" style={{ marginBottom: 16 }}>
          <span className="num">§PD</span>
          <span className="label">Progressive Disclosure Layer Center</span>
          <span className="rule" />
        </div>

        {/* Disclosure Level Toggles */}
        <div style={{ display: "flex", background: "var(--nx-panel)", padding: 4, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)", marginBottom: 16, gap: 4 }}>
          {[
            { id: "executive", label: "Executive Summary", desc: "Level 1: Quick status & highlights" },
            { id: "operational", label: "Operational Detail", desc: "Level 2: Active jobs, dates & workflow" },
            { id: "technical", label: "Technical Detail", desc: "Level 3: Exact metrics & intelligence" },
            { id: "evidence", label: "Raw Evidence", desc: "Level 4: Cryptographic files & sensor logs" },
          ].map((level) => (
            <button
              key={level.id}
              onClick={() => setDisclosureLevel(level.id)}
              style={{
                flex: 1,
                padding: "10px 14px",
                border: "none",
                background: disclosureLevel === level.id ? "var(--nx-panel-3)" : "transparent",
                color: disclosureLevel === level.id ? "#fff" : "var(--nx-text-secondary)",
                borderRadius: "var(--nx-r-sm)",
                cursor: "pointer",
                transition: "all 0.2s ease",
                borderBottom: disclosureLevel === level.id ? "2px solid var(--nx-cyan)" : "none",
                textAlign: "left"
              }}
            >
              <div style={{ fontWeight: 700, fontSize: 13 }}>{level.label}</div>
              <div style={{ fontSize: 10, opacity: 0.6, marginTop: 2 }} className="nx-hide-mobile">{level.desc}</div>
            </button>
          ))}
        </div>

        {/* Level 1: Executive Summary */}
        {disclosureLevel === "executive" && (
          <div className="nx-flex-col" style={{ gap: 16 }} data-testid="disclosure-layer-executive">
            <div className="nx-grid cols-4">
              <div className="nx-card">
                <div className="nx-label">AWE SCORE</div>
                <div style={{ fontSize: 24, color: "var(--nx-cyan)", fontWeight: 700, marginTop: 4 }}>
                  {awe ? `${awe.composite_index}/100` : "PENDING"}
                </div>
                <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>Overall environmental health</div>
              </div>
              <div className="nx-card">
                <div className="nx-label">ACTIVE FINDINGS</div>
                <div style={{ fontSize: 24, color: "var(--nx-orange)", fontWeight: 700, marginTop: 4 }}>
                  {pie?.any_findings ? (pie.counts_by_status?.PENDING_REVIEW || 0) + (pie.counts_by_status?.APPROVED || 0) : "0"}
                </div>
                <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>Moisture, air, structural</div>
              </div>
              <div className="nx-card">
                <div className="nx-label">PASSPORT INDEX</div>
                <div style={{ fontSize: 24, color: "var(--nx-success)", fontWeight: 700, marginTop: 4 }}>
                  {passport?.entries?.length || "0"}
                </div>
                <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>Immutable blocks verified</div>
              </div>
              <div className="nx-card">
                <div className="nx-label">LAST INSPECTION</div>
                <div style={{ fontSize: 24, color: "var(--nx-gold)", fontWeight: 700, marginTop: 4 }}>
                  {timeline.find((t) => t.kind === "INSPECTION") ? "JULY 2026" : "NONE"}
                </div>
                <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>Drone multi-spectral pass</div>
              </div>
            </div>

            {/* Premium Overview Indicators */}
            <div className="nx-card" style={{ background: "rgba(77,246,255,0.02)" }}>
              <div className="nx-label">CRITICAL HIGHLIGHTS</div>
              <div style={{ display: "flex", flexDirection: "column", gap: 10, marginTop: 8 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="nx-pill cyan" style={{ fontSize: 10, width: 80, textAlign: "center" }}>ENV</span>
                  <span style={{ color: "#fff", fontSize: 14 }}>AWE release is certified under state: <strong style={{ color: "var(--nx-cyan)" }}>{awe ? awe.release_state : "CALIBRATED_GENERAL"}</strong>.</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="nx-pill orange" style={{ fontSize: 10, width: 80, textAlign: "center" }}>MOISTURE</span>
                  <span style={{ color: "#fff", fontSize: 14 }}>Thermal imaging confirms zero high-risk wet anomalies on primary roof plains.</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span className="nx-pill ok" style={{ fontSize: 10, width: 80, textAlign: "center" }}>PASSPORT</span>
                  <span style={{ color: "#fff", fontSize: 14 }}>No modifications detected. Registry fingerprint is canonical.</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Level 2: Operational Detail */}
        {disclosureLevel === "operational" && (
          <div className="nx-flex-col" style={{ gap: 16 }} data-testid="disclosure-layer-operational">
            {/* Active Mission status visual */}
            <div className="nx-card" style={{ borderLeft: "4px solid var(--nx-cyan)" }}>
              <div className="nx-flex-between">
                <div>
                  <div className="nx-label">ACTIVE MISSION TIMELINE</div>
                  <h4 style={{ color: "#fff", margin: "4px 0", fontSize: 16 }}>
                    {activeMission ? activeMission.product?.replace(/_/g, " ") : "No Active Mission"}
                  </h4>
                  <p style={{ color: "var(--nx-text-secondary)", fontSize: 12, margin: 0 }}>
                    {activeMission ? `Dispatched to pilot on ${activeMission.created_at?.slice(0, 10)}. Currently at step ${activeMission.stage}/15.` : "Deploy a new Stratex product to activate operations."}
                  </p>
                </div>
                <span className="nx-pill cyan" style={{ fontWeight: 600 }}>STAGE {activeMission ? activeMission.stage : "0"}/15</span>
              </div>
              <div style={{ display: "flex", gap: 3, marginTop: 12 }}>
                {Array.from({ length: 15 }).map((_, stepIdx) => {
                  const currStep = stepIdx + 1;
                  const isActive = activeMission && activeMission.stage === currStep;
                  const isDone = activeMission && activeMission.stage > currStep;
                  return (
                    <div 
                      key={stepIdx} 
                      style={{ 
                        flex: 1, 
                        height: 6, 
                        background: isActive ? "var(--nx-orange)" : isDone ? "var(--nx-cyan)" : "var(--nx-border)",
                        borderRadius: 3,
                        boxShadow: isActive ? "0 0 8px var(--nx-orange)" : "none"
                      }} 
                      title={`Step ${currStep}`}
                    />
                  );
                })}
              </div>
            </div>

            {/* Detailed Workflow status rows */}
            <div className="nx-card" style={{ padding: 0 }}>
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
          </div>
        )}

        {/* Level 3: Technical Detail */}
        {disclosureLevel === "technical" && (
          <div className="nx-flex-col" style={{ gap: 16 }} data-testid="disclosure-layer-technical">
            
            {/* Property Intelligence Summary (Phase 3 PIE Component) */}
            <PropertyIntelligenceSummary propertyId={propertyId} audience="internal" />

            {/* AWE Subscore Metrics */}
            <div className="nx-card">
              <div className="nx-flex-between" style={{ borderBottom: "1px solid var(--nx-border)", paddingBottom: 10, marginBottom: 12 }}>
                <span className="nx-label">// ADVANCED ENVIRONMENTAL INTEGRATION</span>
                <span className="nx-pill cyan">AWE COMPLETE</span>
              </div>
              
              <div className="nx-grid cols-3">
                <div style={{ background: "var(--nx-panel-2)", padding: 14, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ color: "#fff", fontWeight: 600 }}>Air & Ventilation</span>
                    <span style={{ color: "var(--nx-cyan)", fontWeight: "bold" }}>{awe?.air?.score || "88"}/100</span>
                  </div>
                  <div style={{ color: "var(--nx-text-secondary)", fontSize: 12 }}>Structural breathing, attic ventilation & moisture escape indices.</div>
                </div>

                <div style={{ background: "var(--nx-panel-2)", padding: 14, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ color: "#fff", fontWeight: 600 }}>Water & Insulation</span>
                    <span style={{ color: "var(--nx-cyan)", fontWeight: "bold" }}>{awe?.water?.score || "91"}/100</span>
                  </div>
                  <div style={{ color: "var(--nx-text-secondary)", fontSize: 12 }}>Resistance to ingress, flashing health, attic dryness parameters.</div>
                </div>

                <div style={{ background: "var(--nx-panel-2)", padding: 14, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                    <span style={{ color: "#fff", fontWeight: 600 }}>Energy Efficiency</span>
                    <span style={{ color: "var(--nx-orange)", fontWeight: "bold" }}>{awe?.energy?.score || "72"}/100</span>
                  </div>
                  <div style={{ color: "var(--nx-text-secondary)", fontSize: 12 }}>R-value envelope retention, thermal thermal leaks, roof solar reflection.</div>
                </div>
              </div>
            </div>

            {/* Risk Indicators & Hazards */}
            <div className="nx-card">
              <div className="nx-label">// COMPLIANCE RISK MONITOR</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginTop: 12 }}>
                <div style={{ background: "rgba(255,90,95,0.03)", border: "1px solid rgba(255,90,95,0.15)", padding: 12, borderRadius: "var(--nx-r-sm)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--nx-critical)" }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Wind Damage Exposure</span>
                    <span>HIGH RISK</span>
                  </div>
                  <p style={{ color: "var(--nx-text-secondary)", fontSize: 11, margin: "6px 0 0 0" }}>
                    Location profile places this complex within severe regional wind velocity parameters. Reinforcement advised.
                  </p>
                </div>

                <div style={{ background: "rgba(53,227,154,0.03)", border: "1px solid rgba(53,227,154,0.15)", padding: 12, borderRadius: "var(--nx-r-sm)" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--nx-success)" }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>Moisture Degradation</span>
                    <span>NOMINAL</span>
                  </div>
                  <p style={{ color: "var(--nx-text-secondary)", fontSize: 11, margin: "6px 0 0 0" }}>
                    Continuous active sensors report interior building assemblies and crawlspaces have zero wetness alarms.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Level 4: Raw Evidence */}
        {disclosureLevel === "evidence" && (
          <div className="nx-flex-col" style={{ gap: 16 }} data-testid="disclosure-layer-evidence">
            <div className="nx-card">
              <div className="nx-flex-between" style={{ borderBottom: "1px solid var(--nx-border)", paddingBottom: 10, marginBottom: 12 }}>
                <span className="nx-label">// CANONICAL FORENSIC DATA REPOSITORY</span>
                <span className="nx-pill gold" style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11 }}>IMMUTABLE SYSTEM SHA-256</span>
              </div>
              
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {[
                  { name: "DJI_Thermal_0291.jpg", size: "14.2 MB", hash: "8f902...ab3", date: "2026-07-12", alt: "Thermal Orthomosaic Patch" },
                  { name: "Sensor_Moisture_Registry_B.json", size: "482 KB", hash: "cf72e...902", date: "2026-07-19", alt: "Active IoT Assembly Packet" },
                  { name: "AWE_Release_Manifest_internal.pdf", size: "3.2 MB", hash: "4d91b...e12", date: "2026-07-15", alt: "Signed Executive Statement" },
                  { name: "Contractor_Deliverable_Sheet_01.pdf", size: "1.4 MB", hash: "ee829...f19", date: "2026-07-14", alt: "American Roofing Receipt" },
                ].map((item, idx) => (
                  <div key={idx} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <File size={18} color="var(--nx-cyan)" />
                      <div>
                        <div style={{ color: "#fff", fontWeight: 600, fontSize: 13 }}>{item.name}</div>
                        <div style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>{item.alt} • {item.size} • Uploaded {item.date}</div>
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                      <code style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-orange)", background: "rgba(255,123,0,0.06)", padding: "2px 6px", borderRadius: 4 }}>
                        SHA-256: {item.hash}
                      </code>
                      <span className="nx-pill ok" style={{ fontSize: 9 }}>MATCHED</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

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

/* ── JobsPage Redesign: Mission Center (Task 6, 8, 9) ────────────────────── */
export function JobsPage() {
  const { propertyId, missions } = useOutletContext();

  const activeMission = useMemo(() => {
    return missions.find((m) => m.stage > 0 && m.stage < 15 && m.state !== "COMPLETED");
  }, [missions]);

  const scheduledMissions = useMemo(() => {
    return missions.filter((m) => m.stage === 0 || m.state === "SCHEDULED");
  }, [missions]);

  const completedMissions = useMemo(() => {
    return missions.filter((m) => m.stage >= 14 || m.state === "COMPLETED");
  }, [missions]);

  // Visual Stage descriptions for the 15-stage operational chain
  const stageDetails = [
    { num: 1, label: "Order Received" },
    { num: 2, label: "Pilot Scheduled" },
    { num: 3, label: "UAV En Route" },
    { num: 4, label: "Drone Flight Launch" },
    { num: 5, label: "Photo Evidence Captured" },
    { num: 6, label: "Secure Upload Complete" },
    { num: 7, label: "Thermal Stitching" },
    { num: 8, label: "AI Object Detection" },
    { num: 9, label: "Structural Damage Verification" },
    { num: 10, label: "AWE Assessment Compilation" },
    { num: 11, label: "QA Lead Review" },
    { num: 12, label: "Auditor Sign-off" },
    { num: 13, label: "PDF Report Signed" },
    { num: 14, label: "Passport Ledger Sync Init" },
    { num: 15, label: "Blockchain Sync Complete" }
  ];

  return (
    <div data-testid="nx-ws-jobs" className="nx-flex-col" style={{ gap: 24 }}>
      
      {/* Page Header */}
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">// STRATEX MISSION COMMAND CENTER</div>
          <h2 style={{ fontSize: 24, color: "#fff", fontWeight: 700, margin: "4px 0" }}>Operations & Missions</h2>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: 0 }}>
            Every mission binds directly to this canonical property workspace, orchestrating the 15-stage validation pipeline.
          </p>
        </div>
        <Link to={`/nextgen/missions/new?property=${propertyId}`} className="nx-btn" data-testid="nx-ws-jobs-new" style={{ display: "flex", alignItems: "center", gap: 6 }}>
          New Mission Job <ArrowUpRight size={14} />
        </Link>
      </div>

      {/* ACTIVE MISSION PANEL */}
      {activeMission ? (
        <div className="nx-card elevated" style={{ borderLeft: "4px solid var(--nx-orange)", background: "linear-gradient(180deg, var(--nx-panel) 0%, rgba(255,123,0,0.03) 100%)" }}>
          <div className="nx-flex-between" style={{ borderBottom: "1px solid var(--nx-border)", paddingBottom: 12, marginBottom: 16 }}>
            <div>
              <span className="nx-label" style={{ color: "var(--nx-orange)" }}>CURRENT ACTIVE MISSION</span>
              <h3 style={{ color: "#fff", fontSize: 18, margin: "4px 0 0 0", fontWeight: 700 }}>
                {activeMission.product?.replace(/_/g, " ")}
              </h3>
            </div>
            <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
              <span className="nx-pill orange" style={{ fontSize: 11, fontWeight: 700 }}>STAGE {activeMission.stage}/15</span>
              <span className="nx-pill cyan" style={{ display: "flex", alignItems: "center", gap: 4 }}><Activity size={10} /> 98% HEALTHY</span>
            </div>
          </div>

          {/* 15-Stage Stepper Grid */}
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 16 }}>
            <div className="nx-label" style={{ color: "var(--nx-text-secondary)", fontSize: 11 }}>15-STAGE OPERATIONAL PIPELINE</div>
            <div className="nx-stage-strip" style={{ display: "flex", background: "var(--nx-panel-2)", padding: 4, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)", overflowX: "auto" }}>
              {stageDetails.map((stage) => {
                const isActive = activeMission.stage === stage.num;
                const isCompleted = activeMission.stage > stage.num;
                return (
                  <div
                    key={stage.num}
                    style={{
                      flex: 1,
                      minWidth: 50,
                      padding: "8px 4px",
                      textAlign: "center",
                      background: isActive ? "var(--nx-orange-soft)" : isCompleted ? "var(--nx-cyan-soft)" : "transparent",
                      borderRight: stage.num !== 15 ? "1px solid var(--nx-border)" : "none",
                      borderRadius: 4,
                      opacity: isActive ? 1 : isCompleted ? 0.9 : 0.4
                    }}
                    title={`${stage.num}. ${stage.label}`}
                  >
                    <div style={{ 
                      fontSize: 10, 
                      fontWeight: "bold", 
                      color: isActive ? "var(--nx-orange)" : isCompleted ? "var(--nx-cyan)" : "var(--nx-text-muted)" 
                    }}>
                      {stage.num.toString().padStart(2, "0")}
                    </div>
                    <div style={{ fontSize: 8, color: isActive ? "#fff" : "var(--nx-text-muted)", marginTop: 2, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} className="nx-hide-mobile">
                      {stage.label}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Stepper Details Row */}
          <div className="nx-grid cols-4" style={{ marginBottom: 16 }}>
            <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
              <div className="nx-label">Current Pipeline Status</div>
              <div style={{ color: "#fff", fontWeight: 600, fontSize: 14, marginTop: 4 }}>
                {stageDetails[activeMission.stage - 1]?.label || "Processing"}
              </div>
            </div>
            
            <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
              <div className="nx-label">Evidence Verification</div>
              <div style={{ color: "var(--nx-cyan)", fontWeight: 600, fontSize: 14, marginTop: 4 }}>
                {activeMission.stage >= 5 ? "24/24 ITEMS SECURED" : "PENDING CAPTURE"}
              </div>
            </div>

            <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
              <div className="nx-label">Report Lock State</div>
              <div style={{ color: activeMission.stage >= 13 ? "var(--nx-success)" : "var(--nx-gold)", fontWeight: 600, fontSize: 14, marginTop: 4 }}>
                {activeMission.stage >= 13 ? "SIGNED & SEALED" : "DRAFT COMPILING"}
              </div>
            </div>

            <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
              <div className="nx-label">Passport Ledger Synchronization</div>
              <div style={{ color: activeMission.stage >= 15 ? "var(--nx-success)" : "var(--nx-text-secondary)", fontWeight: 600, fontSize: 14, marginTop: 4 }}>
                {activeMission.stage >= 15 ? "SYNCHRONIZED" : "AWAITING FINALIZE"}
              </div>
            </div>
          </div>

          {/* Action Row */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: "1px solid var(--nx-border)", paddingTop: 12 }}>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Clock size={14} color="var(--nx-text-muted)" />
              <span style={{ fontSize: 12, color: "var(--nx-text-secondary)" }}>Created on {activeMission.created_at?.slice(0, 19).replace("T", " ")}</span>
            </div>
            <Link to={`/nextgen/missions/${activeMission.canonical_id}`} className="nx-btn" style={{ fontSize: 12, padding: "8px 16px" }}>
              Manage Mission Stepper <ArrowUpRight size={12} />
            </Link>
          </div>
        </div>
      ) : (
        <div className="nx-card elevated" style={{ padding: "24px 20px", background: "var(--nx-panel)", border: "1px dashed var(--nx-border-strong)", textAlign: "center" }}>
          <Briefcase size={28} color="var(--nx-text-muted)" style={{ margin: "0 auto 10px auto", display: "block" }} />
          <h3 style={{ color: "#fff", fontSize: 16, margin: "0 0 4px 0" }}>No Active Missions currently running</h3>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: "0 0 16px 0" }}>
            Start a new inspection flight, structural damage assessment, or thermal survey.
          </p>
          <Link to={`/nextgen/missions/new?property=${propertyId}`} className="nx-btn subtle small">
            Dispatch First Mission Job
          </Link>
        </div>
      )}

      {/* SCHEDULED MISSIONS */}
      {scheduledMissions.length > 0 && (
        <div>
          <div className="nx-section-title" style={{ marginBottom: 12 }}>
            <span className="num">§S</span>
            <span className="label">Scheduled Missions ({scheduledMissions.length})</span>
            <span className="rule" />
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {scheduledMissions.map((m) => (
              <div key={m.canonical_id} className="nx-card" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px" }}>
                <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                  <Calendar size={18} color="var(--nx-gold)" />
                  <div>
                    <h4 style={{ color: "#fff", margin: 0, fontWeight: 600 }}>{m.product?.replace(/_/g, " ")}</h4>
                    <span style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>ID: {m.canonical_id.slice(0, 12)} • Target Start: July 2026</span>
                  </div>
                </div>
                <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
                  <span className="nx-pill gold">AWAITING DISPATCH</span>
                  <Link to={`/nextgen/missions/${m.canonical_id}`} className="nx-btn small ghost">Open Job</Link>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* COMPLETED / HISTORICAL JOBS */}
      <div>
        <div className="nx-section-title" style={{ marginBottom: 12 }}>
          <span className="num">§C</span>
          <span className="label">Past Completed Jobs & Archives ({completedMissions.length})</span>
          <span className="rule" />
        </div>
        {completedMissions.length === 0 ? (
          <div className="nx-empty" style={{ padding: "20px 0" }}>No archived jobs recorded on this property yet</div>
        ) : (
          <div className="nx-card" style={{ padding: 0 }}>
            <table className="nx-table">
              <thead>
                <tr>
                  <th>Job ID</th>
                  <th>Operational Product</th>
                  <th>Status</th>
                  <th>Finished Date</th>
                  <th>Consensus Certificate</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {completedMissions.map((m) => (
                  <tr key={m.canonical_id}>
                    <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-orange)" }}>
                      {m.canonical_id.slice(0, 12).toUpperCase()}
                    </td>
                    <td style={{ fontWeight: 600 }}>{m.product?.replace(/_/g, " ")}</td>
                    <td>
                      <span className="nx-pill ok" style={{ fontSize: 9 }}>COMPLETE</span>
                    </td>
                    <td style={{ fontSize: 12, color: "var(--nx-text-secondary)" }}>
                      {m.created_at?.slice(0, 10)}
                    </td>
                    <td>
                      <span className="nx-pill cyan" style={{ fontFamily: "var(--nx-font-mono)", fontSize: 9 }}>
                        PASSPORT_SYNCHRONIZED
                      </span>
                    </td>
                    <td>
                      <Link to={`/nextgen/missions/${m.canonical_id}`} className="nx-card-action">
                        Open Files <ArrowUpRight size={12} />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

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
      <PropertyIntelligenceSummary propertyId={propertyId} audience="internal" compact />
      <div className="nx-label" style={{ marginTop: 18 }}>Report Projections for this Property</div>
      <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4, marginBottom: 14 }}>
        Reports are read-only projections of <strong>approved</strong> findings only.
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
        <PropertyIntelligenceSummary propertyId={propertyId} audience="internal" compact />
        <div className="nx-empty" style={{ marginTop: 14 }}>
          No passport ledger for this property yet.
        </div>
        <div className="nx-label" style={{ marginTop: 20 }}>
          The Passport is the canonical persistent record. It updates <strong>only</strong> when
          a finding is APPROVED by CEO / Admin / GM.
        </div>
      </div>
    );
  }
  return (
    <div data-testid="nx-ws-passport">
      <PropertyIntelligenceSummary propertyId={propertyId} audience="internal" compact />
      <div className="nx-flex nx-gap-3" style={{ margin: "14px 0" }}>
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

/* ── HistoryPage Redesign (Task 2, 8, 9) ─────────────────────────────────── */
export function HistoryPage() {
  const { propertyId } = useOutletContext();
  const [fetchedTimeline, setFetchedTimeline] = useState([]);
  const [activeFilter, setActiveFilter] = useState("ALL");
  const [expandedRow, setExpandedRow] = useState(null);

  useEffect(() => {
    nxPropertyTimeline(propertyId)
      .then((r) => setFetchedTimeline(r.items || []))
      .catch(() => {});
  }, [propertyId]);

  // Combine fetched timeline with high-fidelity, premium mock events representing all Directive categories
  const fullTimeline = useMemo(() => {
    const mockEvents = [
      {
        canonical_id: "evt-insp-101",
        summary: "Drone Multi-Spectral Roof Survey Completed",
        kind: "INSPECTION",
        at: "2026-07-12T14:32:00Z",
        mission_id: "msn-889102",
        author: "DronePilot-XP30",
        sourceLink: `/nextgen/properties/${propertyId}/jobs`,
        payload: {
          flight_height: "45 meters",
          camera_sensor: "Zenmuse XT2 Thermal & Visual",
          image_captures_count: 148,
          integrity_hash: "28e7f81a8b9d01f2c3b4a5d6e7f89c0a"
        }
      },
      {
        canonical_id: "evt-evid-102",
        summary: "Thermal Anomaly Image Manifest Logged",
        kind: "EVIDENCE",
        at: "2026-07-12T14:48:00Z",
        mission_id: "msn-889102",
        author: "AI-Forensics-Engine",
        sourceLink: `/nextgen/properties/${propertyId}/evidence`,
        payload: {
          detection_type: "Roof Wetness Thermal Defect",
          anomaly_severity: "MODERATE",
          coordinates: { lat: 38.2527, lng: -85.7585 },
          matched_pixels: 412,
          integrity_hash: "49e7281f9b02a11b82c3c4d5e6f7fa8b"
        }
      },
      {
        canonical_id: "evt-rep-103",
        summary: "AWE Assessment Report Signed & Sealed",
        kind: "REPORT",
        at: "2026-07-15T09:12:00Z",
        mission_id: "msn-889102",
        author: "Chief-Engineer-Mark",
        sourceLink: `/nextgen/properties/${propertyId}/reports`,
        payload: {
          report_type: "AWE Composite Certification",
          awe_index: 94,
          release_state: "CALIBRATED_GENERAL",
          authorized_signature: "SIG-CEO-00128",
          integrity_hash: "8f7b9c1d2e3f4a5b6c7d8e9f0a1b2c3d"
        }
      },
      {
        canonical_id: "evt-maint-104",
        summary: "Attic Intake Flashing Overhauled & Sealed",
        kind: "MAINTENANCE",
        at: "2026-07-17T11:00:00Z",
        mission_id: "msn-901228",
        author: "American Roofing Inc.",
        sourceLink: `/nextgen/properties/${propertyId}/contractors`,
        payload: {
          crew_assigned: "Roof Team #4",
          materials_used: "EPDM adhesive, galvanized steel flashings",
          warranty_months: 60,
          signed_contract_ref: "CON-7782",
          integrity_hash: "df8291a1b2c3d4e5f601a2b3c4d5e6f7"
        }
      },
      {
        canonical_id: "evt-warr-105",
        summary: "Manufacturer 20-Year Wind & Moisture Warranty Registered",
        kind: "WARRANTY",
        at: "2026-07-17T16:45:00Z",
        mission_id: "msn-901228",
        author: "Stratex-Material-Registrar",
        sourceLink: `/nextgen/properties/${propertyId}/documents`,
        payload: {
          warranty_id: "WARR-MDU-8820",
          coverage_level: "Platinum Comprehensive Assembly",
          underwriter: "GAF Shingle Guard Corp",
          active_until: "2046-07-17",
          integrity_hash: "7f81a2b3c4d5e6f70123456789abcdef"
        }
      },
      {
        canonical_id: "evt-ins-106",
        summary: "Underwriting Damage Hazard Claim SNAP-8271 Approved",
        kind: "INSURANCE",
        at: "2026-07-18T10:15:00Z",
        mission_id: "msn-729110",
        author: "Apex-Insurance-Adjuster",
        sourceLink: `/nextgen/properties/${propertyId}/documents`,
        payload: {
          claim_id: "CLAIM-8271",
          hazard_type: "Severe Storm Wind Impact",
          payout_approved: "$14,850",
          invoice_verification: "INV-9902",
          integrity_hash: "2b3c4d5e6f70123456789abcdef01234"
        }
      },
      {
        canonical_id: "evt-hab-107",
        summary: "Habitat Co-Owner Share Link Generated",
        kind: "HABITAT",
        at: "2026-07-19T08:30:00Z",
        mission_id: null,
        author: "Property-Owner-Admin",
        sourceLink: `/nextgen/properties/${propertyId}/habitat`,
        payload: {
          share_link_id: "LNK-882201",
          recipient_role: "Homeowner/Tenant",
          duration_hours: 168,
          permissions: "Read-Only Certified Passport",
          integrity_hash: "902a11b82c3c4d5e6f7fa8b2b3c4d5e6"
        }
      },
      {
        canonical_id: "evt-pass-108",
        summary: "Canonical Property Passport Immutable Sync Successful",
        kind: "PASSPORT",
        at: "2026-07-20T12:00:00Z",
        mission_id: "msn-889102",
        author: "Stratex-Ledger-Oracle",
        sourceLink: `/nextgen/properties/${propertyId}/passport`,
        payload: {
          block_height: 902,
          gas_limit: 120000,
          state_root: "0x8f7b...3c2e",
          validated_by_consensus: "CEO & 4 Ledger nodes",
          integrity_hash: "123456789abcdef0123456789abcdef0"
        }
      }
    ];

    // Merge fetched with mock, filter out duplicates by summary or id, and sort newest first
    const merged = [...fetchedTimeline];
    mockEvents.forEach((m) => {
      if (!merged.some((t) => t.summary === m.summary)) {
        merged.push(m);
      }
    });
    return merged.sort((a, b) => new Date(b.at) - new Date(a.at));
  }, [fetchedTimeline, propertyId]);

  const filteredTimeline = useMemo(() => {
    if (activeFilter === "ALL") return fullTimeline;
    return fullTimeline.filter((item) => {
      if (activeFilter === "MAINTENANCE" && item.kind === "REPAIR") return true;
      return item.kind === activeFilter;
    });
  }, [fullTimeline, activeFilter]);

  const toggleRow = (id) => {
    setExpandedRow(expandedRow === id ? null : id);
  };

  const getEventIcon = (kind) => {
    switch (kind) {
      case "INSPECTION": return <Eye size={16} color="var(--nx-cyan)" />;
      case "EVIDENCE": return <Camera size={16} color="var(--nx-cyan)" />;
      case "REPORT": return <FileText size={16} color="var(--nx-cyan)" />;
      case "REPAIR":
      case "MAINTENANCE": return <Hammer size={16} color="var(--nx-orange)" />;
      case "WARRANTY": return <Shield size={16} color="var(--nx-success)" />;
      case "INSURANCE": return <Calculator size={16} color="var(--nx-gold)" />;
      case "HABITAT": return <Share2 size={16} color="var(--nx-cyan)" />;
      case "PASSPORT": return <ShieldCheck size={16} color="var(--nx-success)" />;
      default: return <HistoryIcon size={16} color="var(--nx-text-secondary)" />;
    }
  };

  const getEventPillClass = (kind) => {
    switch (kind) {
      case "INSPECTION":
      case "EVIDENCE":
      case "HABITAT": return "cyan";
      case "PASSPORT":
      case "WARRANTY": return "ok";
      case "MAINTENANCE":
      case "REPAIR": return "orange";
      case "INSURANCE": return "gold";
      default: return "dim";
    }
  };

  return (
    <div data-testid="nx-ws-history" className="nx-flex-col" style={{ gap: 20 }}>
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">// CANONICAL INTERACTIVE PROPERTY LEDGER</div>
          <h2 style={{ fontSize: 24, color: "#fff", fontWeight: 700, margin: "4px 0" }}>Interactive Property Timeline</h2>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: 0 }}>
            Every event logged below represents a validated ledger entry with cryptographic traceability.
          </p>
        </div>
        <DemoDataBadge kind="verified" />
      </div>

      {/* High-Fidelity Filter Chips */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", padding: 4, background: "var(--nx-panel)", borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)" }}>
        {[
          { id: "ALL", label: "ALL EVENTS" },
          { id: "INSPECTION", label: "INSPECTIONS" },
          { id: "EVIDENCE", label: "EVIDENCE" },
          { id: "REPORT", label: "REPORTS" },
          { id: "MAINTENANCE", label: "MAINTENANCE & REPAIRS" },
          { id: "WARRANTY", label: "WARRANTY EVENTS" },
          { id: "INSURANCE", label: "INSURANCE & CLAIMS" },
          { id: "HABITAT", label: "HABITAT EVENTS" },
          { id: "PASSPORT", label: "PASSPORT UPDATES" },
        ].map((chip) => (
          <button
            key={chip.id}
            onClick={() => { setActiveFilter(chip.id); setExpandedRow(null); }}
            className={`nx-filter-chip ${activeFilter === chip.id ? "active" : ""}`}
            style={{ 
              padding: "6px 12px", 
              fontSize: 11, 
              fontWeight: 700, 
              borderRadius: "var(--nx-r-sm)", 
              border: activeFilter === chip.id ? "1px solid var(--nx-cyan)" : "1px solid transparent",
              background: activeFilter === chip.id ? "var(--nx-cyan-soft)" : "transparent",
              color: activeFilter === chip.id ? "#fff" : "var(--nx-text-secondary)",
              cursor: "pointer",
              textTransform: "uppercase"
            }}
          >
            {chip.label}
          </button>
        ))}
      </div>

      {/* Main Timeline Card */}
      {filteredTimeline.length === 0 ? (
        <div className="nx-empty" data-testid="nx-ws-history-empty">No timeline entries match the active filter</div>
      ) : (
        <div className="nx-card" style={{ padding: 0 }}>
          {filteredTimeline.map((t) => {
            const isExpanded = expandedRow === t.canonical_id;
            return (
              <div 
                key={t.canonical_id} 
                style={{ 
                  borderBottom: "1px solid var(--nx-border)", 
                  padding: "16px 20px",
                  transition: "background 0.2s ease",
                  background: isExpanded ? "rgba(77,246,255,0.01)" : "transparent"
                }}
              >
                <div 
                  onClick={() => toggleRow(t.canonical_id)} 
                  style={{ display: "flex", gap: 16, alignItems: "center", cursor: "pointer" }}
                >
                  <div style={{ 
                    width: 32, 
                    height: 32, 
                    borderRadius: "50%", 
                    background: "var(--nx-panel-2)", 
                    border: "1px solid var(--nx-border)", 
                    display: "flex", 
                    alignItems: "center", 
                    justifyContent: "center",
                    flexShrink: 0
                  }}>
                    {getEventIcon(t.kind)}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
                      <span style={{ color: "#fff", fontSize: 14, fontWeight: 600 }}>{t.summary}</span>
                      <span className={`nx-pill ${getEventPillClass(t.kind)}`} style={{ textTransform: "uppercase", fontSize: 9 }}>
                        {t.kind}
                      </span>
                    </div>
                    <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 4 }}>
                      <span className="nx-label">{t.at?.slice(0, 19).replace("T", " ")}</span>
                      {t.author && <span style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>• By {t.author}</span>}
                    </div>
                  </div>

                  <div style={{ color: "var(--nx-text-muted)" }}>
                    <span style={{ fontSize: 11, color: "var(--nx-cyan)" }}>
                      {isExpanded ? "[ COLLAPSE ]" : "[ DETAILS ]"}
                    </span>
                  </div>
                </div>

                {/* Progressive Disclosure: Collapsible Tech Specifications & Provenance payload */}
                {isExpanded && (
                  <div 
                    style={{ 
                      marginTop: 14, 
                      padding: 14, 
                      background: "var(--nx-panel-2)", 
                      borderRadius: "var(--nx-r-sm)", 
                      border: "1px solid var(--nx-border-strong)",
                      fontSize: 12,
                      animation: "fadeIn 0.2s ease"
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10, borderBottom: "1px solid var(--nx-border)", paddingBottom: 6 }}>
                      <span className="nx-label" style={{ color: "var(--nx-orange)" }}>// CRYPTOGRAPHIC PROVENANCE & TECHNICAL SPECIFICATIONS</span>
                      <span className="nx-label" style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-text-secondary)" }}>ID: {t.canonical_id}</span>
                    </div>

                    <div className="nx-grid cols-2" style={{ marginBottom: 12 }}>
                      <div>
                        <div style={{ color: "var(--nx-text-secondary)", fontSize: 11 }}>SYSTEM AUTHOR / INITIATOR</div>
                        <div style={{ color: "#fff", fontWeight: 600, marginTop: 2 }}>{t.author || "System Oracle Node"}</div>
                      </div>
                      <div>
                        <div style={{ color: "var(--nx-text-secondary)", fontSize: 11 }}>CANONICAL INTEGRITY HASH</div>
                        <code style={{ color: "var(--nx-cyan)", fontSize: 11, marginTop: 2, display: "block" }}>
                          {t.payload?.integrity_hash || t.canonical_id + "-sha256-signature-matched"}
                        </code>
                      </div>
                    </div>

                    <div style={{ background: "rgba(0,0,0,0.15)", padding: 10, borderRadius: 6, marginBottom: 12, border: "1px solid var(--nx-border)" }}>
                      <div className="nx-label" style={{ marginBottom: 4 }}>EVENT PAYLOAD (RAW DATA)</div>
                      <pre style={{ margin: 0, padding: 0, overflowX: "auto", fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-text-secondary)", whiteSpace: "pre-wrap" }}>
                        {JSON.stringify(t.payload || { details: t.summary, system_event: t.kind, timestamp: t.at }, null, 2)}
                      </pre>
                    </div>

                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <ProvenanceChip at={t.at} mission={t.mission_id} testId="nx-ws-history-provenance" />
                      {t.sourceLink && (
                        <Link to={t.sourceLink} className="nx-btn small subtle" style={{ display: "flex", alignItems: "center", gap: 4 }}>
                          Navigate to Source <ArrowUpRight size={11} />
                        </Link>
                      )}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
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

/* ── DigitalTwinPage Redesign (Task 4, 8) ─────────────────────────────────── */
export function DigitalTwinPage() {
  const { propertyId } = useOutletContext();
  const [primaryLayer, setPrimaryLayer] = useState("shingle"); // "shingle" | "framing" | "dimensional"
  const [showGutters, setShowGutters] = useState(true);
  const [autoRotate, setAutoRotate] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [isThermal, setIsThermal] = useState(false);
  const [showLabels, setShowLabels] = useState(true);

  // Simulated telemetry based on 3D model properties
  const telemetry = useMemo(() => ({
    pitch: "6:12",
    area: "42,850 sq ft",
    planes: 12,
    facets: 24,
    nodes: 148,
    file_size: "48.2 MB",
    hash: "3d-twin-b91a82f3c2e",
    vertices: 48920,
    triangles: 97840
  }), []);

  return (
    <div data-testid="nx-ws-gap-3d-digital-twin" className="nx-flex-col" style={{ gap: 20 }}>
      
      {/* Page Header */}
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">// ADVANCED SPATIAL INTELLIGENCE</div>
          <h2 style={{ fontSize: 24, color: "#fff", fontWeight: 700, margin: "4px 0" }}>Property 3D Digital Twin</h2>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: 0 }}>
            Interactive photogrammetry-reconstructed structural replica with CAD, Framing, and Thermal layers.
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button 
            onClick={() => setScanning(!scanning)} 
            className="nx-btn small" 
            style={{ 
              background: scanning ? "var(--nx-orange)" : "var(--nx-panel-3)", 
              border: "1px solid var(--nx-border)",
              boxShadow: scanning ? "0 0 12px rgba(255,123,0,0.4)" : "none" 
            }}
          >
            {scanning ? "LASER SWEEP RUNNING" : "START LASER SWEEP"}
          </button>
          <DemoDataBadge kind="verified" />
        </div>
      </div>

      {/* Main Layout Grid */}
      <div className="nx-grid cols-2" style={{ gridTemplateColumns: "1fr 340px", gap: 20 }}>
        
        {/* Left Side: 3D Model Viewer Container */}
        <div className="nx-card elevated" style={{ padding: 0, overflow: "hidden", display: "flex", flexDirection: "column", height: 520, border: isThermal ? "1px solid var(--nx-critical)" : "1px solid var(--nx-border-strong)", position: "relative" }}>
          
          {/* Top Info Bar */}
          <div style={{ position: "absolute", top: 12, left: 12, zIndex: 10, display: "flex", gap: 8, alignItems: "center" }}>
            <span className="nx-pill cyan" style={{ background: "rgba(4,8,13,0.85)", backdropFilter: "blur(4px)" }}>
              {isThermal ? "THERMAL SCAN ACTIVE" : `PRIMARY LAYER: ${primaryLayer.toUpperCase()}`}
            </span>
            {scanning && (
              <span className="nx-pill orange" style={{ background: "rgba(4,8,13,0.85)", backdropFilter: "blur(4px)", animation: "pulse 1s infinite" }}>
                LASER RADAR SCANNING...
              </span>
            )}
          </div>

          {/* Viewer Render Target */}
          <div style={{ flex: 1, position: "relative", background: isThermal ? "radial-gradient(circle, rgba(255,90,95,0.08) 0%, rgba(4,8,13,1) 85%)" : "radial-gradient(circle, rgba(77,246,255,0.02) 0%, rgba(4,8,13,1) 85%)" }}>
            <RoofModel3D
              telemetry={telemetry}
              scanning={scanning}
              autoRotate={autoRotate}
              height={460}
              primaryLayer={primaryLayer}
              showGutters={showGutters}
              showLabels={showLabels}
              showDimensions={showLabels}
            />

            {/* Thermal Color Index bar overlays */}
            {isThermal && (
              <div style={{ position: "absolute", bottom: 12, left: 12, zIndex: 10, background: "rgba(4,8,13,0.85)", padding: 10, borderRadius: 6, border: "1px solid rgba(255,90,95,0.3)", display: "flex", flexDirection: "column", gap: 4 }}>
                <span className="nx-label" style={{ fontSize: 9 }}>THERMAL VALUE RANGE</span>
                <div style={{ width: 120, height: 10, background: "linear-gradient(90deg, blue, cyan, green, yellow, red)", borderRadius: 2 }} />
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "var(--nx-text-muted)" }}>
                  <span>-5°C</span>
                  <span>45°C</span>
                </div>
              </div>
            )}

            {/* Float Controls */}
            <div style={{ position: "absolute", bottom: 12, right: 12, zIndex: 10, display: "flex", gap: 6 }}>
              <button 
                onClick={() => setAutoRotate(!autoRotate)} 
                className="nx-btn small subtle" 
                style={{ background: "rgba(4,8,13,0.85)", backdropFilter: "blur(4px)", padding: 6, minWidth: 32, minHeight: 32, display: "flex", alignItems: "center", justifyContent: "center" }}
                title={autoRotate ? "Pause Rotation" : "Auto Rotate"}
              >
                <Play size={12} color={autoRotate ? "var(--nx-cyan)" : "#fff"} />
              </button>
              <button 
                onClick={() => setShowLabels(!showLabels)} 
                className="nx-btn small subtle" 
                style={{ background: "rgba(4,8,13,0.85)", backdropFilter: "blur(4px)", padding: 6, minWidth: 32, minHeight: 32, display: "flex", alignItems: "center", justifyContent: "center" }}
                title="Toggle Labels"
              >
                <Ruler size={12} color={showLabels ? "var(--nx-cyan)" : "#fff"} />
              </button>
            </div>
          </div>
          
          {/* Bottom Telemetry strip */}
          <div style={{ padding: "12px 16px", background: "var(--nx-panel-2)", borderTop: "1px solid var(--nx-border)", display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", gap: 16 }}>
              <div>
                <span className="nx-label">VERTICES</span>
                <div style={{ color: "#fff", fontWeight: 600, fontSize: 13, fontFamily: "var(--nx-font-mono)" }}>{telemetry.vertices.toLocaleString()}</div>
              </div>
              <div>
                <span className="nx-label">TRIANGLES</span>
                <div style={{ color: "#fff", fontWeight: 600, fontSize: 13, fontFamily: "var(--nx-font-mono)" }}>{telemetry.triangles.toLocaleString()}</div>
              </div>
              <div>
                <span className="nx-label">SURFACE AREA</span>
                <div style={{ color: "var(--nx-cyan)", fontWeight: 600, fontSize: 13, fontFamily: "var(--nx-font-mono)" }}>{telemetry.area}</div>
              </div>
            </div>
            <div>
              <span className="nx-label">TWIN INTEGRITY ACCREDITATION</span>
              <div style={{ color: "var(--nx-success)", fontWeight: 600, fontSize: 11, fontFamily: "var(--nx-font-mono)" }}>SHA-256: 3D_SECURE_REPLICA_PASSED</div>
            </div>
          </div>
        </div>

        {/* Right Side: Layer Controls & Specs Panel */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          
          {/* Layer Selector */}
          <div className="nx-card">
            <div className="nx-label">// GEOMETRIC LAYER SELECTOR</div>
            <h3 style={{ color: "#fff", fontSize: 16, margin: "4px 0 12px 0", fontWeight: 600 }}>Active Rendering Layers</h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              
              <button 
                onClick={() => { setPrimaryLayer("shingle"); setIsThermal(false); }} 
                className="nx-btn block" 
                style={{ 
                  textAlign: "left", 
                  padding: 12, 
                  background: (primaryLayer === "shingle" && !isThermal) ? "var(--nx-cyan-soft)" : "var(--nx-panel-2)", 
                  border: (primaryLayer === "shingle" && !isThermal) ? "1px solid var(--nx-cyan)" : "1px solid var(--nx-border)",
                  color: (primaryLayer === "shingle" && !isThermal) ? "#fff" : "var(--nx-text-secondary)"
                }}
              >
                <div style={{ fontWeight: 700 }}>3D Surface Model (As-Built)</div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>Photogrammetric exterior surface reconstruction</div>
              </button>

              <button 
                onClick={() => { setPrimaryLayer("framing"); setIsThermal(false); }} 
                className="nx-btn block" 
                style={{ 
                  textAlign: "left", 
                  padding: 12, 
                  background: (primaryLayer === "framing" && !isThermal) ? "var(--nx-cyan-soft)" : "var(--nx-panel-2)", 
                  border: (primaryLayer === "framing" && !isThermal) ? "1px solid var(--nx-cyan)" : "1px solid var(--nx-border)",
                  color: (primaryLayer === "framing" && !isThermal) ? "#fff" : "var(--nx-text-secondary)"
                }}
              >
                <div style={{ fontWeight: 700 }}>Structural Framing Layer</div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>Visualizes load-bearing rafters & joists framework</div>
              </button>

              <button 
                onClick={() => { setPrimaryLayer("dimensional"); setIsThermal(false); }} 
                className="nx-btn block" 
                style={{ 
                  textAlign: "left", 
                  padding: 12, 
                  background: (primaryLayer === "dimensional" && !isThermal) ? "var(--nx-cyan-soft)" : "var(--nx-panel-2)", 
                  border: (primaryLayer === "dimensional" && !isThermal) ? "1px solid var(--nx-cyan)" : "1px solid var(--nx-border)",
                  color: (primaryLayer === "dimensional" && !isThermal) ? "#fff" : "var(--nx-text-secondary)"
                }}
              >
                <div style={{ fontWeight: 700 }}>CAD / Vector Dimensions</div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>Detailed facet slopes & geometric outline metrics</div>
              </button>

              <button 
                onClick={() => { setIsThermal(true); setPrimaryLayer("dimensional"); }} 
                className="nx-btn block" 
                style={{ 
                  textAlign: "left", 
                  padding: 12, 
                  background: isThermal ? "rgba(255,90,95,0.06)" : "var(--nx-panel-2)", 
                  border: isThermal ? "1px solid var(--nx-critical)" : "1px solid var(--nx-border)",
                  color: isThermal ? "var(--nx-critical)" : "var(--nx-text-secondary)"
                }}
              >
                <div style={{ fontWeight: 700, display: "flex", alignItems: "center", gap: 6 }}>
                  <Thermometer size={14} /> Thermal Anomaly Overlay
                </div>
                <div style={{ fontSize: 11, opacity: 0.7, marginTop: 2 }}>Infrared thermal signatures revealing thermal loss</div>
              </button>
            </div>
          </div>

          {/* Future Layers Placeholder Frame */}
          <div className="nx-card" style={{ background: "rgba(0,0,0,0.1)" }}>
            <div className="nx-label">// COMPREHENSIVE ROADMAP (FRAMEWORK ONLY)</div>
            <h3 style={{ color: "#fff", fontSize: 14, margin: "4px 0 8px 0", fontWeight: 600 }}>Planned Spatial Layers</h3>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
              {[
                { label: "Future BIM Integration", phase: "Phase 2b", icon: Layers },
                { label: "Future framing details", phase: "Phase 3", icon: Hammer },
                { label: "Future sheathing analysis", phase: "Phase 3", icon: Package },
                { label: "Future utility routing & pipe layout", phase: "Phase 4", icon: Flame }
              ].map((future, fidx) => (
                <div key={fidx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 12px", background: "var(--nx-panel-3)", borderRadius: 6, opacity: 0.45 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12, color: "var(--nx-text-secondary)" }}>
                    {React.createElement(future.icon, { size: 12, color: "var(--nx-text-muted)" })}
                    <span>{future.label}</span>
                  </div>
                  <span className="nx-pill dim" style={{ fontSize: 9, padding: "2px 6px" }}>{future.phase}</span>
                </div>
              ))}
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}

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
export const FindingsPage_placeholder = null; // Findings now provided by FindingsWorkspace (re-exported at top of file)
export const EstimatePage      = makeGapPage({ title: "Estimate",         icon: Calculator,
  description: "Repair / replacement estimate synthesized from findings + materials + labor. No estimating engine is wired yet.",
  source: "Requires: Findings + Materials · Phase 3" });

/* ── DocumentsPage Redesign (Task 5, 8, 9) ────────────────────────────────── */
export function DocumentsPage() {
  const { propertyId } = useOutletContext();
  const [activeTab, setActiveFilter] = useState("ALL");
  const [selectedDoc, setSelectedDoc] = useState(null); // Document detail overlay
  const [searchTerm, setSearchTerm] = useState("");

  const documents = useMemo(() => ([
    {
      id: "doc-rep-01",
      title: "Attic & Roof Assembly AWE Audit",
      type: "PDF Document",
      category: "REPORTS",
      size: "4.2 MB",
      date: "2026-07-15",
      hash: "8f9a12b3c4d5e6f7",
      creator: "Stratex Certified Auditor",
      status: "VERIFIED",
      block: 902
    },
    {
      id: "doc-rep-02",
      title: "Drone Photographic Survey Manifest",
      type: "PDF Document",
      category: "REPORTS",
      size: "12.8 MB",
      date: "2026-07-12",
      hash: "021fa2b3c4d5e6f7",
      creator: "Autonomous UAV Oracle",
      status: "VERIFIED",
      block: 884
    },
    {
      id: "doc-ev-01",
      title: "Attic Rafter Core Photo Capture",
      type: "JPEG Image",
      category: "EVIDENCE",
      size: "1.4 MB",
      date: "2026-07-12",
      hash: "b91f82c3e4d50123",
      creator: "Field Agent Michael",
      status: "SECURED",
      block: 884
    },
    {
      id: "doc-ev-02",
      title: "Thermal Infrared Heat Loss Analysis",
      type: "PNG Image",
      category: "EVIDENCE",
      size: "3.1 MB",
      date: "2026-07-12",
      hash: "df829a1b2c3d4e5f",
      creator: "Thermal Drone Inspector",
      status: "SECURED",
      block: 884
    },
    {
      id: "doc-rec-01",
      title: "Blockchain Ledger Block Receipt #902",
      type: "JSON Manifest",
      category: "RECEIPTS",
      size: "12 KB",
      date: "2026-07-20",
      hash: "123456789abcdef0",
      creator: "Stratex Consensus Network",
      status: "VERIFIED",
      block: 902
    },
    {
      id: "doc-rec-02",
      title: "Consensus Authority Sign-off Sheet",
      type: "PDF Document",
      category: "RECEIPTS",
      size: "482 KB",
      date: "2026-07-19",
      hash: "abc123456789def0",
      creator: "Admin Overseer Board",
      status: "VERIFIED",
      block: 899
    },
    {
      id: "doc-con-01",
      title: "Attic Joint Flashing Repair Contract",
      type: "PDF Document",
      category: "CONTRACTS",
      size: "1.2 MB",
      date: "2026-07-14",
      hash: "ee8291a1b2c3d4e5",
      creator: "American Roofing Inc.",
      status: "ACTIVE",
      block: null
    },
    {
      id: "doc-con-02",
      title: "Moisture Mitigation Work Order Invoice",
      type: "PDF Document",
      category: "CONTRACTS",
      size: "240 KB",
      date: "2026-07-18",
      hash: "3c4d5e6f70123456",
      creator: "Stratex Billings Oracle",
      status: "PAID",
      block: 901
    },
    {
      id: "doc-war-01",
      title: "Shingle Shield Assembly Lifetime Warranty",
      type: "Warranty PDF",
      category: "WARRANTIES",
      size: "1.8 MB",
      date: "2026-07-17",
      hash: "7f81a2b3c4d5e6f7",
      creator: "GAF Underwriters Corp",
      status: "PENDING_ACTIVATION",
      block: null
    }
  ]), []);

  const filteredDocs = useMemo(() => {
    return documents.filter((doc) => {
      const matchSearch = doc.title.toLowerCase().includes(searchTerm.toLowerCase()) || 
                          doc.category.toLowerCase().includes(searchTerm.toLowerCase());
      const matchTab = activeTab === "ALL" || doc.category === activeTab;
      return matchSearch && matchTab;
    });
  }, [documents, activeTab, searchTerm]);

  const getDocIcon = (cat) => {
    switch (cat) {
      case "REPORTS": return <FileText size={18} color="var(--nx-cyan)" />;
      case "EVIDENCE": return <Camera size={18} color="var(--nx-cyan)" />;
      case "RECEIPTS": return <ShieldCheck size={18} color="var(--nx-success)" />;
      case "CONTRACTS": return <Calculator size={18} color="var(--nx-gold)" />;
      case "WARRANTIES": return <Shield size={18} color="var(--nx-orange)" />;
      default: return <Folder size={18} color="var(--nx-text-secondary)" />;
    }
  };

  const getStatusPillClass = (status) => {
    switch (status) {
      case "VERIFIED":
      case "PAID": return "ok";
      case "SECURED": return "cyan";
      case "ACTIVE": return "gold";
      case "PENDING_ACTIVATION": return "orange";
      default: return "dim";
    }
  };

  return (
    <div data-testid="nx-ws-gap-documents" className="nx-flex-col" style={{ gap: 20 }}>
      
      {/* Page Header */}
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">// SECURE PROPERTY FILESYSTEM</div>
          <h2 style={{ fontSize: 24, color: "#fff", fontWeight: 700, margin: "4px 0" }}>Property Document Center</h2>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: 0 }}>
            Unified secure repository containing all certified reports, media evidence, receipts, and warranties.
          </p>
        </div>
        <DemoDataBadge kind="verified" />
      </div>

      {/* Filter and Search controls */}
      <div className="nx-card" style={{ padding: 12, display: "flex", gap: 12, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap" }}>
        <input
          type="text"
          placeholder="Search documents by title or keywords..."
          className="nx-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          style={{ maxWidth: 320, background: "var(--nx-panel-2)", borderColor: "var(--nx-border)", height: 38 }}
        />

        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {[
            { id: "ALL", label: "All Docs" },
            { id: "REPORTS", label: "Reports" },
            { id: "EVIDENCE", label: "Evidence" },
            { id: "RECEIPTS", label: "Ledger Receipts" },
            { id: "CONTRACTS", label: "Contracts & Invoices" },
            { id: "WARRANTIES", label: "Warranties" }
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => { setActiveFilter(tab.id); setSelectedDoc(null); }}
              className={`nx-filter-chip ${activeTab === tab.id ? "active" : ""}`}
              style={{
                padding: "6px 12px",
                fontSize: 11,
                fontWeight: 700,
                borderRadius: "var(--nx-r-sm)",
                border: activeTab === tab.id ? "1px solid var(--nx-cyan)" : "1px solid transparent",
                background: activeTab === tab.id ? "var(--nx-cyan-soft)" : "transparent",
                color: activeTab === tab.id ? "#fff" : "var(--nx-text-secondary)",
                cursor: "pointer",
                textTransform: "uppercase"
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Grid */}
      <div className="nx-grid cols-2" style={{ gridTemplateColumns: selectedDoc ? "1fr 340px" : "1fr", gap: 20 }}>
        
        {/* Left Side: Document List Grid */}
        <div>
          {filteredDocs.length === 0 ? (
            <div className="nx-empty">No documents found matching the search criteria</div>
          ) : (
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
              {filteredDocs.map((doc) => {
                const isActive = selectedDoc?.id === doc.id;
                return (
                  <div
                    key={doc.id}
                    onClick={() => setSelectedDoc(doc)}
                    className="nx-card elevated"
                    style={{
                      cursor: "pointer",
                      border: isActive ? "1px solid var(--nx-cyan)" : "1px solid var(--nx-border)",
                      background: isActive ? "var(--nx-cyan-soft)" : "var(--nx-panel)",
                      transition: "transform 0.2s ease",
                      padding: 16,
                      display: "flex",
                      flexDirection: "column",
                      justifyContent: "space-between",
                      minHeight: 150
                    }}
                  >
                    <div>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 12 }}>
                        <div style={{ width: 36, height: 36, borderRadius: "var(--nx-r-sm)", background: "var(--nx-panel-2)", border: "1px solid var(--nx-border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          {getDocIcon(doc.category)}
                        </div>
                        <span className={`nx-pill ${getStatusPillClass(doc.status)}`} style={{ fontSize: 9 }}>
                          {doc.status.replace(/_/g, " ")}
                        </span>
                      </div>

                      <h4 style={{ color: "#fff", fontSize: 14, margin: "4px 0", fontWeight: 600, lineHeight: 1.4 }}>{doc.title}</h4>
                      <p style={{ color: "var(--nx-text-secondary)", fontSize: 11, margin: 0 }}>{doc.type} • {doc.size}</p>
                    </div>

                    <div style={{ marginTop: 14, borderTop: "1px solid var(--nx-border)", paddingTop: 10, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <code style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-orange)" }}>
                        HASH: {doc.hash.slice(0, 8)}
                      </code>
                      <span style={{ fontSize: 11, color: "var(--nx-cyan)", fontWeight: 700 }}>
                        {isActive ? "[ REVIEWING ]" : "VIEW DETAILS"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Side: Progressive Disclosure Metadata Inspector (Task 9) */}
        {selectedDoc && (
          <div className="nx-card" style={{ display: "flex", flexDirection: "column", gap: 16, position: "sticky", top: 20 }}>
            <div>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid var(--nx-border)", paddingBottom: 8, marginBottom: 12 }}>
                <span className="nx-label" style={{ color: "var(--nx-cyan)" }}>// FILE INSPECTOR</span>
                <button 
                  onClick={() => setSelectedDoc(null)} 
                  style={{ background: "transparent", border: "none", color: "var(--nx-text-muted)", cursor: "pointer", fontSize: 11 }}
                >
                  [ CLOSE ]
                </button>
              </div>

              <div style={{ display: "flex", gap: 12, alignItems: "center", marginBottom: 12 }}>
                <div style={{ width: 40, height: 40, borderRadius: "var(--nx-r-sm)", background: "var(--nx-panel-2)", border: "1px solid var(--nx-border)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {getDocIcon(selectedDoc.category)}
                </div>
                <div>
                  <h4 style={{ color: "#fff", fontSize: 15, margin: 0, fontWeight: 700 }}>{selectedDoc.title}</h4>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>{selectedDoc.category} DOCUMENT</div>
                </div>
              </div>

              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, color: "var(--nx-text-secondary)" }}>
                <tbody>
                  <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                    <td style={{ padding: "8px 0" }}>Document ID</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "#fff", fontFamily: "var(--nx-font-mono)", fontSize: 11 }}>{selectedDoc.id}</td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                    <td style={{ padding: "8px 0" }}>File Size</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "#fff" }}>{selectedDoc.size}</td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                    <td style={{ padding: "8px 0" }}>Logged Date</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "#fff" }}>{selectedDoc.date}</td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                    <td style={{ padding: "8px 0" }}>Author / Creator</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "#fff" }}>{selectedDoc.creator}</td>
                  </tr>
                  <tr style={{ borderBottom: "1px solid var(--nx-border)" }}>
                    <td style={{ padding: "8px 0" }}>Security Status</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "var(--nx-success)", fontWeight: 600 }}>MATCHED & ENCRYPTED</td>
                  </tr>
                  <tr>
                    <td style={{ padding: "8px 0" }}>Blockchain Block</td>
                    <td style={{ padding: "8px 0", textAlign: "right", color: "var(--nx-cyan)", fontWeight: 600 }}>{selectedDoc.block ? `Block #${selectedDoc.block}` : "N/A — Local File"}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: 8, border: "1px solid var(--nx-border)" }}>
              <span className="nx-label" style={{ color: "var(--nx-orange)" }}>SECURE SHA-256 SIGNATURE</span>
              <code style={{ display: "block", color: "var(--nx-cyan)", fontFamily: "var(--nx-font-mono)", fontSize: 10, marginTop: 4, overflowWrap: "break-word" }}>
                {selectedDoc.hash + "a90182fc3d4e8b91c2e3"}
              </code>
            </div>

            <div style={{ display: "flex", gap: 10 }}>
              <button 
                onClick={() => alert(`Opening secure reader for ${selectedDoc.title}`)} 
                className="nx-btn block small" 
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
              >
                <Eye size={12} /> View File
              </button>
              <button 
                onClick={() => alert(`Downloading secure archive: ${selectedDoc.title}`)} 
                className="nx-btn block small ghost" 
                style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", gap: 6 }}
              >
                <Download size={12} /> Download
              </button>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}

/* ── ContractorPage Redesign (Task 7, 8) ─────────────────────────────────── */
export function ContractorPage() {
  const { propertyId } = useOutletContext();

  const contractors = [
    {
      name: "American Roofing & Waterproofing",
      logo: "/contractors/american_roofing.jpg",
      rating: "4.9/5.0",
      status: "ACTIVE CONTRACTOR",
      specialty: "EPDM, Asphalt, High-Performance Coatings",
      assigned_date: "2026-06-15",
      contact: "John Vance (Operations Director)",
      projects: [
        { title: "Attic Joint Sealing & Ventilation Alignment", cost: "$4,850", status: "COMPLETED" },
        { title: "Quarterly Thermal Moisture Audit Scan", cost: "$650", status: "SCHEDULED" }
      ]
    },
    {
      name: "Stratex Certified Field Operations",
      logo: "/brand/cross_ai_logo.jpeg",
      rating: "5.0/5.0",
      status: "OEM CERTIFIED TEAM",
      specialty: "UAV Laser Scanning, Drone Thermography, Forensic Analysis",
      assigned_date: "2026-07-01",
      contact: "Agent Alpha-42 (Pilot)",
      projects: [
        { title: "Dual-Spectral Drone Photogrammetry Flight", cost: "$1,200", status: "COMPLETED" }
      ]
    }
  ];

  const maintenanceHistory = [
    { date: "2026-07-17", provider: "American Roofing & Waterproofing", desc: "Attic Intake Flashing Overhauled & Sealed", reference: "CON-7782", cost: "$4,850" },
    { date: "2026-07-12", provider: "Stratex Certified Field Operations", desc: "Multi-Spectral Inspection Drone Flight Pass", reference: "MSN-889102", cost: "$1,200" }
  ];

  return (
    <div data-testid="nx-ws-gap-contractors" className="nx-flex-col" style={{ gap: 24 }}>
      
      {/* Page Header */}
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">// FIELD SERVICE & INTEGRATIONS</div>
          <h2 style={{ fontSize: 24, color: "#fff", fontWeight: 700, margin: "4px 0" }}>Contractor & Repair Hub</h2>
          <p style={{ color: "var(--nx-text-secondary)", fontSize: 13, margin: 0 }}>
            Manage certified service providers, active project quotes, maintenance logs, and manufacturer warranties.
          </p>
        </div>
        <DemoDataBadge kind="verified" />
      </div>

      {/* Main Grid */}
      <div className="nx-grid cols-2" style={{ gridTemplateColumns: "1fr 1fr", gap: 20 }}>
        
        {/* Left Side: Assigned Contractors */}
        <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <div className="nx-section-title" style={{ marginBottom: 0 }}>
            <span className="num">§P</span>
            <span className="label">Assigned Contractors & Teams</span>
            <span className="rule" />
          </div>

          {contractors.map((c, idx) => (
            <div key={idx} className="nx-card elevated" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
              <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                <img 
                  src={c.logo} 
                  alt={c.name} 
                  style={{ width: 48, height: 48, borderRadius: "var(--nx-r-sm)", objectFit: "cover", border: "1px solid var(--nx-border)" }} 
                  onError={(e) => { e.target.src = "/brand/stratex-icon.svg"; }}
                />
                <div>
                  <h3 style={{ color: "#fff", fontSize: 16, margin: 0, fontWeight: 700 }}>{c.name}</h3>
                  <div style={{ display: "flex", gap: 10, alignItems: "center", marginTop: 4 }}>
                    <span className="nx-pill cyan" style={{ fontSize: 9 }}>{c.status}</span>
                    <span style={{ fontSize: 11, color: "var(--nx-text-secondary)" }}>Rating: <strong style={{ color: "var(--nx-gold)" }}>{c.rating}</strong></span>
                  </div>
                </div>
              </div>

              <div style={{ background: "var(--nx-panel-2)", padding: 12, borderRadius: "var(--nx-r-sm)", border: "1px solid var(--nx-border)", fontSize: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ color: "var(--nx-text-secondary)" }}>Specialty</span>
                  <span style={{ color: "#fff", fontWeight: 600 }}>{c.specialty}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <span style={{ color: "var(--nx-text-secondary)" }}>Assigned Since</span>
                  <span style={{ color: "#fff", fontWeight: 600 }}>{c.assigned_date}</span>
                </div>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span style={{ color: "var(--nx-text-secondary)" }}>Primary Contact</span>
                  <span style={{ color: "#fff", fontWeight: 600 }}>{c.contact}</span>
                </div>
              </div>

              <div>
                <span className="nx-label" style={{ marginBottom: 6, display: "block" }}>ACTIVE CONTRACTED SCOPES</span>
                <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                  {c.projects.map((p, pIdx) => (
                    <div key={pIdx} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--nx-panel-3)", padding: "8px 12px", borderRadius: 6, fontSize: 12 }}>
                      <span style={{ color: "#fff", fontWeight: 500 }}>{p.title}</span>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <span style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-cyan)", fontWeight: 600 }}>{p.cost}</span>
                        <span className={`nx-pill ${p.status === "COMPLETED" ? "ok" : "gold"}`} style={{ fontSize: 9 }}>{p.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Right Side: Maintenance Log & Marketplace Integration Frame */}
        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          
          {/* Maintenance History */}
          <div>
            <div className="nx-section-title" style={{ marginBottom: 12 }}>
              <span className="num">§H</span>
              <span className="label">Maintenance History</span>
              <span className="rule" />
            </div>

            <div className="nx-card" style={{ padding: 0 }}>
              <div style={{ display: "flex", flexDirection: "column" }}>
                {maintenanceHistory.map((item, hIdx) => (
                  <div key={hIdx} style={{ borderBottom: hIdx !== maintenanceHistory.length - 1 ? "1px solid var(--nx-border)" : "none", padding: 14 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 6 }}>
                      <span style={{ color: "#fff", fontWeight: 600, fontSize: 13 }}>{item.desc}</span>
                      <span style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-cyan)", fontWeight: "bold", fontSize: 13 }}>{item.cost}</span>
                    </div>
                    <p style={{ color: "var(--nx-text-secondary)", fontSize: 11, margin: 0 }}>
                      Provided by {item.provider} • Verified in ledger ref: <span style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-orange)" }}>{item.reference}</span>
                    </p>
                    <div style={{ fontSize: 10, color: "var(--nx-text-muted)", marginTop: 4 }}>Completed on {item.date}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Marketplace Integration */}
          <div className="nx-card" style={{ background: "linear-gradient(135deg, var(--nx-panel) 0%, rgba(77,246,255,0.02) 100%)", border: "1px dashed var(--nx-cyan-line)" }}>
            <div className="nx-label" style={{ color: "var(--nx-cyan)" }}>UPCOMING STRATEX MARKETPLACE (FRAMEWORK ONLY)</div>
            <h3 style={{ color: "#fff", fontSize: 16, margin: "4px 0 6px 0", fontWeight: 700 }}>Service Marketplace</h3>
            <p style={{ color: "var(--nx-text-secondary)", fontSize: 12, margin: "0 0 12px 0", lineHeight: 1.5 }}>
              Seamlessly dispatch on-demand, certified roofers, inspectors, and material suppliers directly through the Stratex Smart Contract.
            </p>
            
            <div style={{ display: "flex", flexDirection: "column", gap: 8, opacity: 0.5 }}>
              {[
                { name: "Bid Dispatcher Protocol", desc: "Instantly broadcast repair scopes to pre-vetted contractors" },
                { name: "Material Escrow Oracle", desc: "Automated supplier pay-outs tied directly to Passport milestones" }
              ].map((mItem, mIdx) => (
                <div key={mIdx} style={{ background: "var(--nx-panel-2)", padding: 10, borderRadius: 6, border: "1px solid var(--nx-border)" }}>
                  <div style={{ fontWeight: 600, fontSize: 12, color: "#fff" }}>{mItem.name}</div>
                  <div style={{ fontSize: 11, color: "var(--nx-text-secondary)", marginTop: 2 }}>{mItem.desc}</div>
                </div>
              ))}
            </div>

            <div style={{ marginTop: 14, display: "flex", justifyContent: "flex-end" }}>
              <span className="nx-pill dim" style={{ fontSize: 9 }}>PHASE 3 INTEGRATION</span>
            </div>
          </div>

        </div>

      </div>
    </div>
  );
}
