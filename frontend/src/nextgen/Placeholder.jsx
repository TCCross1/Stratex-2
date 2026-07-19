import React from "react";
import { Link } from "react-router-dom";
import { Construction, ArrowUpRight } from "lucide-react";

/* NextGen placeholder destination (Phase 1 consolidation).
   Renders a clearly-labeled "not yet implemented" surface WITHOUT fabricating live data.
   Every placeholder shows a Demo Data indicator per user directive. */

export default function Placeholder({
  title,
  eyebrow = "// PHASE 2",
  description,
  relatedLinks = [],
  status = "planned",
  icon: Icon = Construction,
  testId,
}) {
  return (
    <div data-testid={testId || "nx-placeholder"}>
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">{eyebrow}</div>
          <h1 className="nx-page-title">{title}</h1>
          {description && <div className="nx-page-sub">{description}</div>}
        </div>
        <DemoDataBadge kind="placeholder" />
      </div>

      <div
        className="nx-card elevated"
        style={{ padding: 40, textAlign: "center" }}
        data-testid="nx-placeholder-panel"
      >
        <Icon size={44} strokeWidth={1.4} color="var(--nx-cyan)" style={{ opacity: 0.7 }} />
        <div style={{ fontSize: 18, color: "#fff", marginTop: 14, fontWeight: 600 }}>
          {title} · Not Yet Implemented
        </div>
        <div
          style={{
            color: "var(--nx-text-secondary)",
            fontSize: 13,
            marginTop: 8,
            maxWidth: 520,
            marginInline: "auto",
            lineHeight: 1.6,
          }}
        >
          This surface is a Phase 1 placeholder inside the canonical NextGen shell. No live data
          is shown here yet. When the backend and workflow ship, this route will host the real
          {" "}<strong style={{ color: "#fff" }}>{title}</strong> workspace — with the same
          navigation, layout, and design system you see elsewhere in Stratex Core.
        </div>

        <div className="nx-flex nx-gap-3" style={{ marginTop: 20, justifyContent: "center", flexWrap: "wrap" }}>
          <span className="nx-pill orange" data-testid="nx-placeholder-status">
            STATUS · {status.toUpperCase()}
          </span>
          <span className="nx-pill dim">NO LIVE DATA</span>
        </div>

        {relatedLinks.length > 0 && (
          <div style={{ marginTop: 26, paddingTop: 20, borderTop: "1px solid var(--nx-border)" }}>
            <div className="nx-label" style={{ marginBottom: 10 }}>Related · Available Now</div>
            <div className="nx-flex nx-gap-3" style={{ justifyContent: "center", flexWrap: "wrap" }}>
              {relatedLinks.map((r) => (
                <Link
                  key={r.to}
                  to={r.to}
                  className="nx-btn ghost small"
                  data-testid={`nx-placeholder-link-${r.to.replace(/\W+/g, "-")}`}
                >
                  {r.label} <ArrowUpRight size={13} strokeWidth={1.8} />
                </Link>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* Reusable Demo-Data indicator — visible whenever seed / mock / placeholder data is shown. */
export function DemoDataBadge({ kind = "seed", label, testId = "nx-demo-data-badge" }) {
  const labels = {
    seed: "SEED DATA",
    mock: "MOCKED",
    placeholder: "PLACEHOLDER · NO LIVE DATA",
    partial: "PARTIAL DATA",
  };
  return (
    <span
      className="nx-pill orange"
      data-testid={testId}
      title="This surface displays non-production data (seeded, mocked, or placeholder)."
      style={{
        borderColor: "var(--nx-orange)",
        color: "var(--nx-orange)",
        background: "rgba(255,123,0,0.06)",
      }}
    >
      {label || labels[kind] || "DEMO DATA"}
    </span>
  );
}
