import React from "react";

/* Phase 1a stubs — will be wired in Phase 1c per Directive 005 authorization. */

const stub = (title, subtitle, tag) => (
  <div data-testid={`nx-stub-${tag}`}>
    <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// {title.toUpperCase()}</div>
    <h1 className="nx-h1">{title}</h1>
    <div className="nx-sub">{subtitle}</div>

    <div className="nx-panel" style={{ marginTop: 22 }}>
      <div className="corner">// PHASE 1c</div>
      <div style={{ padding: "40px 20px", textAlign: "center" }}>
        <div style={{ fontFamily: "'JetBrains Mono', monospace", color: "#FFB020",
                       letterSpacing: "0.28em", fontSize: 11, textTransform: "uppercase" }}>
          Workspace scaffold pending
        </div>
        <div style={{ color: "#8A9BAE", fontSize: 12, marginTop: 8 }}>
          This surface is authorized under Directive 005 for Phase 1c delivery.
          Data plane and API endpoints are already scaffolded on the backend.
        </div>
      </div>
    </div>
  </div>
);

export const PassportStub = () => stub(
  "Property Passport",
  "Canonical hash-chained property intelligence record (Blueprint §11). Read surface arrives in Phase 1c; ledger writes remain gated to the Passport Service.",
  "passport",
);

export const AweStub = () => stub(
  "AWE™ Intelligence",
  "Air · Water · Energy findings (Blueprint §12.2 · §17.1). Composite Index is release-state gated and never surfaced externally before CALIBRATED_GENERAL.",
  "awe",
);

export const ReportsStub = () => stub(
  "Reports Binder",
  "Approved DayScan · AWE · Elite reports and printable customer deliverables. Every generated PDF is hashed and stored as an evidence derivative (SD-013).",
  "reports",
);

export const HabitatStub = () => stub(
  "Habitat Synchronization",
  "Homeowner projection surface (SD-015). Habitat is a read-only projection consumer; canonical Passport authority remains with the Passport Service.",
  "habitat",
);

export const OrgStub = () => stub(
  "Organization",
  "Tenant profile, users, roles, MFA. Full onboarding flow (SD-001) arrives in Phase 1b.",
  "org",
);
