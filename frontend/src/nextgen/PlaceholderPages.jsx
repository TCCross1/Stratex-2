import React from "react";
import { Bell, Calendar, Handshake, Plane, Home as HomeIcon,
  Map, ScrollText, Info } from "lucide-react";
import Placeholder from "@/nextgen/Placeholder";

/* Phase 1 placeholder destinations. All new NextGen sub-routes render
   through Placeholder — no fabricated live data. */

export function AlertsPage() {
  return (
    <Placeholder
      eyebrow="// COMMAND"
      title="Alerts"
      description="Consolidated inbox of operational alerts across all missions — MFA challenges, QA blockers, weather alerts, evidence gaps, calibration drift. Ships in Phase 2."
      icon={Bell}
      testId="nx-page-alerts"
      relatedLinks={[
        { to: "/nextgen/missions", label: "Open Mission Control" },
        { to: "/nextgen/audit", label: "Audit Trail" },
      ]}
    />
  );
}

export function SchedulePage() {
  return (
    <Placeholder
      eyebrow="// OPERATIONS"
      title="Schedule"
      description="Unified crew, drone, and property scheduling with weather window awareness. Ships in Phase 2."
      icon={Calendar}
      testId="nx-page-schedule"
      relatedLinks={[
        { to: "/nextgen/missions", label: "Open Mission Control" },
        { to: "/nextgen/properties", label: "Jobs & Properties" },
      ]}
    />
  );
}

export function NetworkContractorsPage() {
  return (
    <Placeholder
      eyebrow="// NETWORK"
      title="Contractors & Insurance"
      description="Directory of vetted contractors, insurance adjusters, and their compliance posture. Includes materials configuration, quote-builder, and brand kits (currently reachable via legacy /contractor/* routes). Ships in Phase 2."
      icon={Handshake}
      testId="nx-page-network-contractors"
      relatedLinks={[
        { to: "/contractor", label: "Legacy Contractor Portal" },
      ]}
    />
  );
}

export function NetworkOperatorsPage() {
  return (
    <Placeholder
      eyebrow="// NETWORK"
      title="Operators & Pilots"
      description="Operator roster, pilot certifications, fleet assignments, and live crew status. Currently reachable via legacy /operator, /pilot, /fleet routes. Ships in Phase 2."
      icon={Plane}
      testId="nx-page-network-operators"
      relatedLinks={[
        { to: "/pilot", label: "Pilot Dashboard (tablet)" },
        { to: "/operator", label: "Operator Board" },
        { to: "/fleet", label: "Fleet Board" },
      ]}
    />
  );
}

export function NetworkHomeownersPage() {
  return (
    <Placeholder
      eyebrow="// NETWORK"
      title="Homeowners"
      description="Homeowner directory with active Habitat share status, communication logs, and warranty tracking. Ships in Phase 2."
      icon={HomeIcon}
      testId="nx-page-network-homeowners"
      relatedLinks={[
        { to: "/nextgen/habitat", label: "Stratex Habitat" },
        { to: "/nextgen/passport", label: "Property Passport" },
      ]}
    />
  );
}

export function GeographicIntelligencePage() {
  return (
    <Placeholder
      eyebrow="// PROPERTY INTELLIGENCE"
      title="Geographic Intelligence"
      description="Map-driven view of every property, mission, drone flight, and AWE score across the region. Includes weather overlays, satellite time-series, and fleet live positions. Ships in Phase 2."
      icon={Map}
      testId="nx-page-geo"
      relatedLinks={[
        { to: "/fleet/live-map", label: "Legacy Fleet Live Map" },
      ]}
    />
  );
}

export function PlansCompliancePage() {
  return (
    <Placeholder
      eyebrow="// MANAGEMENT"
      title="Plans, Licenses & Compliance"
      description="Subscription plans, tenant billing, FAA / state operator licenses, insurance certificates, and compliance calendar. Ships in Phase 2."
      icon={ScrollText}
      testId="nx-page-plans"
      relatedLinks={[
        { to: "/billing", label: "Legacy Billing" },
      ]}
    />
  );
}

export function CompanyResourcesPage() {
  return (
    <Placeholder
      eyebrow="// COMPANY"
      title="Company & Resources"
      description="Company overview, mission, investor briefing, executive deck, demos, sample outputs, and press resources — one canonical index. Ships in Phase 2."
      icon={Info}
      testId="nx-page-company"
      relatedLinks={[
        { to: "/deck", label: "Executive Deck" },
        { to: "/demo/scan", label: "Sample Scan Walkthrough" },
        { to: "/onboard", label: "ROI Onboarding" },
        { to: "/contractor/verify", label: "Contractor Verification" },
      ]}
    />
  );
}
