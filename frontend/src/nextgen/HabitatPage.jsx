import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Share2, Copy, RotateCcw, ExternalLink, Clock, Eye, Shield,
  Check, X, ArrowUpRight,
} from "lucide-react";
import {
  nxListProperties, nxIssueHabitatLink, nxListHabitatGrants,
  nxRevokeGrant, nxHabitatReportHtmlUrl,
} from "@/nextgen/api";

/* Habitat Sync — internal control surface (Directive 009 · replaces HabitatStub).
   Uses existing habitat-link + habitat-grants APIs. Homeowner view remains public route. */

const TTL_OPTIONS = [
  { hours: 24,  label: "24 hours" },
  { hours: 72,  label: "3 days" },
  { hours: 168, label: "7 days" },
  { hours: 336, label: "14 days" },
];

export default function HabitatPage() {
  const [properties, setProperties] = useState([]);
  const [pid, setPid] = useState(null);
  const [grants, setGrants] = useState([]);
  const [ttl, setTtl] = useState(168);
  const [audience, setAudience] = useState("homeowner");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(null);

  useEffect(() => {
    nxListProperties().then((d) => {
      setProperties(d.items || []);
      if (d.items?.length) setPid(d.items[0].canonical_id);
    });
  }, []);

  useEffect(() => {
    if (!pid) return;
    loadGrants();
  }, [pid]);

  const loadGrants = async () => {
    if (!pid) return;
    try {
      const r = await nxListHabitatGrants(pid);
      setGrants(r.items || r.grants || []);
    } catch { setGrants([]); }
  };

  const issue = async () => {
    if (!pid) return;
    setBusy(true);
    try {
      const r = await nxIssueHabitatLink(pid, ttl, audience);
      const url = `${window.location.origin}${r.public_url}`;
      await navigator.clipboard?.writeText(url).catch(() => {});
      setCopied(url);
      loadGrants();
      setTimeout(() => setCopied(null), 4000);
    } finally { setBusy(false); }
  };

  const revoke = async (grantId) => {
    await nxRevokeGrant(grantId);
    loadGrants();
  };

  return (
    <div data-testid="nx-habitat">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// HABITAT SYNC</div>
          <h1 className="nx-page-title">Habitat Sharing</h1>
          <div className="nx-page-sub">
            Issue safe homeowner-facing projections of the property record. Habitat is a read-only projection —
            never exposes internal QA notes, AI confidence, or unapproved intelligence.
          </div>
        </div>
        {properties.length > 0 && (
          <select
            className="nx-select"
            style={{ maxWidth: 360 }}
            value={pid || ""}
            onChange={(e) => setPid(e.target.value)}
            data-testid="nx-habitat-property"
          >
            {properties.map((p) => (
              <option key={p.canonical_id} value={p.canonical_id}>
                {p.address.line1}, {p.address.city} {p.address.region}
              </option>
            ))}
          </select>
        )}
      </div>

      {!pid ? (
        <div className="nx-empty">Select a property to manage sharing links.</div>
      ) : (
        <>
          {/* Issue new link */}
          <div className="nx-card elevated" data-testid="nx-habitat-issue">
            <div className="nx-card-title">Issue Homeowner Link</div>
            <div className="nx-grid cols-3" style={{ marginTop: 16 }}>
              <div>
                <label className="nx-field-label">Audience</label>
                <select className="nx-select" value={audience} onChange={(e) => setAudience(e.target.value)}
                  data-testid="nx-habitat-audience">
                  <option value="homeowner">Homeowner</option>
                  <option value="adjuster">Insurance Adjuster</option>
                </select>
              </div>
              <div>
                <label className="nx-field-label">Expiration</label>
                <select className="nx-select" value={ttl} onChange={(e) => setTtl(Number(e.target.value))}
                  data-testid="nx-habitat-ttl">
                  {TTL_OPTIONS.map((o) => (
                    <option key={o.hours} value={o.hours}>{o.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="nx-field-label">&nbsp;</label>
                <button
                  className="nx-btn block"
                  onClick={issue}
                  disabled={busy}
                  data-testid="nx-habitat-issue-btn"
                >
                  <Share2 size={16} strokeWidth={1.8} />
                  {busy ? "Issuing…" : "Create & Copy Link"}
                </button>
              </div>
            </div>
            {copied && (
              <div className="nx-copied-box" data-testid="nx-habitat-copied">
                <Check size={16} color="var(--nx-success)" />
                <span>Copied to clipboard —</span>
                <code style={{ color: "var(--nx-cyan)", wordBreak: "break-all" }}>{copied}</code>
              </div>
            )}
          </div>

          {/* Preview */}
          <div className="nx-section-title">
            <span className="num">§01</span>
            <span className="label">Homeowner Preview</span>
            <span className="rule" />
            <a
              className="nx-card-action"
              href={nxHabitatReportHtmlUrl(pid, "homeowner_summary")}
              target="_blank" rel="noreferrer"
              data-testid="nx-habitat-preview-link"
            >
              Open HTML Preview <ExternalLink size={13} strokeWidth={1.8} />
            </a>
          </div>
          <div className="nx-card">
            <div className="nx-flex" style={{ gap: 12, alignItems: "flex-start" }}>
              <Shield size={22} strokeWidth={1.6} color="var(--nx-cyan)" />
              <div>
                <div style={{ color: "#fff", fontWeight: 600 }}>Safe Homeowner Projection</div>
                <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4, lineHeight: 1.6 }}>
                  The homeowner view shows only approved intelligence, AWE composite (when calibrated), and
                  homeowner-safe action recommendations. Internal reviewer identities, tier assignments,
                  and confidence numbers are stripped by the projection layer.
                </div>
              </div>
            </div>
          </div>

          {/* Active grants */}
          <div className="nx-section-title">
            <span className="num">§02</span>
            <span className="label">Active Share Links</span>
            <span className="rule" />
          </div>
          {grants.length === 0 ? (
            <div className="nx-empty" data-testid="nx-habitat-grants-empty">No active share links for this property.</div>
          ) : (
            <div className="nx-card" style={{ padding: 0 }} data-testid="nx-habitat-grants">
              <div style={{ overflowX: "auto" }}>
                <table className="nx-table">
                  <thead>
                    <tr>
                      <th>Audience</th>
                      <th>Created</th>
                      <th>Expires</th>
                      <th>Access</th>
                      <th>Last Access</th>
                      <th>State</th>
                      <th style={{ textAlign: "right" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {grants.map((g) => {
                      const revoked = g.revoked_at || g.state === "REVOKED";
                      const expired = g.expires_at && new Date(g.expires_at) < new Date();
                      const state = revoked ? { label: "Revoked", pill: "danger" }
                                  : expired ? { label: "Expired", pill: "warn" }
                                            : { label: "Active", pill: "ok" };
                      return (
                        <tr key={g.canonical_id || g.id || g.token}>
                          <td><span className="nx-pill cyan">{g.audience || "homeowner"}</span></td>
                          <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-text-secondary)" }}>
                            {g.issued_at?.slice(0, 16).replace("T", " ") || "—"}
                          </td>
                          <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-text-secondary)" }}>
                            {g.expires_at?.slice(0, 16).replace("T", " ") || "—"}
                          </td>
                          <td>{g.access_count ?? 0}</td>
                          <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 11, color: "var(--nx-text-secondary)" }}>
                            {g.last_accessed_at ? g.last_accessed_at.slice(0, 16).replace("T", " ") : "—"}
                          </td>
                          <td><span className={`nx-pill ${state.pill}`}>{state.label}</span></td>
                          <td style={{ textAlign: "right" }}>
                            {!revoked && !expired && (
                              <button
                                className="nx-btn ghost small"
                                onClick={() => revoke(g.canonical_id || g.id)}
                                data-testid={`nx-habitat-revoke-${g.canonical_id || g.id}`}
                              >
                                <X size={13} /> Revoke
                              </button>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </>
      )}

      <HabitatStyles />
    </div>
  );
}

function HabitatStyles() {
  return (
    <style>{`
      .nx-copied-box {
        margin-top: 14px; padding: 12px 14px;
        border: 1px solid rgba(53,227,154,0.4);
        background: rgba(53,227,154,0.06);
        border-radius: var(--nx-r-sm);
        display: flex; align-items: center; gap: 10px;
        font-family: var(--nx-font-mono);
        font-size: 12px;
        color: var(--nx-success);
        flex-wrap: wrap;
      }
    `}</style>
  );
}
