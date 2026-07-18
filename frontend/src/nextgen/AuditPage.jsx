import React, { useEffect, useState } from "react";
import { nxAudit } from "@/nextgen/api";

/* Audit trail read view — Domain 10 §12. Every state change writes an audit_events row. */

export default function AuditPage() {
  const [items, setItems] = useState([]);
  useEffect(() => { nxAudit().then((d) => setItems(d.items || [])); }, []);
  return (
    <div data-testid="nx-audit">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>// AUDIT TRAIL · DOMAIN 10</div>
      <h1 className="nx-h1">Audit Events</h1>
      <div className="nx-sub">
        Immutable audit surface consumed by security, compliance, and Human QA replay
        (Data Model v1.0 §12). Retention class · auth_log · 2 yr hot / 7 yr cold.
      </div>

      {items.length === 0 ? (
        <div className="nx-empty">No audit events yet</div>
      ) : (
        <div className="nx-panel" style={{ padding: 0, marginTop: 18 }}>
          <table className="nx-table" data-testid="nx-audit-table">
            <thead><tr>
              <th>// At</th><th>Event</th><th>Resource</th><th>Actor</th>
            </tr></thead>
            <tbody>
              {items.map((e) => (
                <tr key={e.canonical_id}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, color: "#8A9BAE" }}>
                    {e.at.replace("T", " ").slice(0, 19)}
                  </td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, color: "#4DF6FF" }}>
                    {e.event_type}
                  </td>
                  <td style={{ fontSize: 11 }}>
                    {e.resource_kind} · <span style={{ color: "#FFB020" }}>{String(e.resource_id).slice(0, 12)}…</span>
                  </td>
                  <td style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}>
                    {String(e.actor_id).slice(0, 12)}…
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
