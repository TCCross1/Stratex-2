import React, { useEffect, useState } from "react";
import { Building2, Users, Settings, ShieldCheck, MailCheck } from "lucide-react";
import { nxOrg, nxMe } from "@/nextgen/api";

/* Organization page (Directive 009 · replaces OrgStub).
   Read-only tenant profile view over existing /organizations/current. */

export default function OrganizationPage() {
  const [org, setOrg] = useState(null);
  const [me, setMe] = useState(null);
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([nxOrg().catch(() => null), nxMe().catch(() => null)])
      .then(([o, m]) => { setOrg(o); setMe(m); })
      .catch((e) => setErr(e?.response?.data?.detail || e.message));
  }, []);

  if (err) return <div className="nx-card" style={{ borderColor: "var(--nx-critical)" }}>{err}</div>;

  return (
    <div data-testid="nx-org">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// ORGANIZATION</div>
          <h1 className="nx-page-title">Tenant Profile</h1>
          <div className="nx-page-sub">
            Organization and session details for the current Stratex Core tenant.
            Full onboarding, roles and MFA management arrives in a future directive.
          </div>
        </div>
      </div>

      <div className="nx-grid cols-2">
        <div className="nx-card">
          <div className="nx-flex" style={{ gap: 12, alignItems: "center" }}>
            <Building2 size={20} strokeWidth={1.6} color="var(--nx-cyan)" />
            <div className="nx-card-title">Tenant</div>
          </div>
          <div style={{ fontSize: 22, color: "#fff", fontWeight: 700, marginTop: 10 }}>
            {org?.name || org?.legal_name || me?.tenant?.name || me?.tenant_slug || "—"}
          </div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
            {org?.tenant_slug || me?.tenant_slug || "—"}
          </div>
          <div className="nx-grid cols-2" style={{ marginTop: 18 }}>
            <div className="nx-metric-block">
              <div className="k">Environment</div>
              <div className="v or" style={{ fontSize: 20 }}>Preview</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Region</div>
              <div className="v" style={{ fontSize: 20 }}>{org?.region || "—"}</div>
            </div>
          </div>
        </div>

        <div className="nx-card">
          <div className="nx-flex" style={{ gap: 12, alignItems: "center" }}>
            <Users size={20} strokeWidth={1.6} color="var(--nx-cyan)" />
            <div className="nx-card-title">Current Operator</div>
          </div>
          <div style={{ fontSize: 22, color: "#fff", fontWeight: 700, marginTop: 10 }}>
            {me?.legal_name || me?.email || "—"}
          </div>
          <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
            {me?.email || "—"}
          </div>
          <div className="nx-grid cols-2" style={{ marginTop: 18 }}>
            <div className="nx-metric-block">
              <div className="k">Role</div>
              <div className="v cy" style={{ fontSize: 20 }}>{me?.role || "—"}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Session</div>
              <div className="v" style={{ fontSize: 20 }}>Active</div>
            </div>
          </div>
        </div>
      </div>

      <div className="nx-section-title">
        <span className="num">§01</span>
        <span className="label">Attribution</span>
        <span className="rule" />
      </div>
      <div className="nx-card" data-testid="nx-org-cross-ai">
        <div className="nx-label">Product Ownership</div>
        <div style={{ color: "var(--nx-text-secondary)", fontSize: 14, marginTop: 8, lineHeight: 1.6 }}>
          Stratex Core is a product of <strong style={{ color: "#fff" }}>Cross AI Softwares Inc.</strong>
          Product identity and branding are governed by the Stratex Core visual contract.
          Corporate identity appears in About, footer, and system ownership metadata.
        </div>
      </div>
    </div>
  );
}
