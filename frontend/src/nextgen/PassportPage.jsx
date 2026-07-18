import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  ShieldCheck, Clock, ArrowUpRight, ExternalLink, Copy, Check,
  Waves, Wind, Droplet, Sun, Sparkles, Share2, FileText,
} from "lucide-react";
import {
  nxListProperties, nxPropertyPassport, nxPropertyTimeline,
  nxPropertyReport, nxReportTemplates, nxPropertyAwe,
  nxIssueHabitatLink, nxOpenReportHtml,
} from "@/nextgen/api";

/* Property Passport (Directive 009 restyle).
   Same APIs, refined presentation. Ledger + Timeline + AWE + Habitat share. */

const AUDIENCES = ["internal", "contractor", "homeowner", "adjuster", "insurer"];

export default function PassportPage() {
  const [properties, setProperties] = useState([]);
  const [pid, setPid] = useState(null);
  const [passport, setPassport] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [audience, setAudience] = useState("internal");
  const [templates, setTemplates] = useState([]);
  const [template, setTemplate] = useState("homeowner_summary");
  const [report, setReport] = useState(null);
  const [awe, setAwe] = useState(null);
  const [linkOut, setLinkOut] = useState(null);
  const [linkBusy, setLinkBusy] = useState(false);

  useEffect(() => {
    nxListProperties().then((d) => {
      setProperties(d.items);
      if (d.items.length > 0) setPid(d.items[0].canonical_id);
    });
    nxReportTemplates().then((d) => setTemplates(d.templates));
  }, []);

  useEffect(() => {
    if (!pid) return;
    nxPropertyPassport(pid, audience).then(setPassport);
    nxPropertyTimeline(pid).then((d) => setTimeline(d.items));
    nxPropertyAwe(pid).then((d) => setAwe(d.awe));
  }, [pid, audience]);

  useEffect(() => {
    if (!pid || !template) return;
    nxPropertyReport(pid, template).then(setReport).catch(() => setReport(null));
  }, [pid, template]);

  const property = properties.find((p) => p.canonical_id === pid);

  return (
    <div data-testid="nx-passport">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// PROPERTY PASSPORT</div>
          <h1 className="nx-page-title">Passport Ledger</h1>
          <div className="nx-page-sub">
            Canonical hash-chained property intelligence record. Only the Passport Service appends.
            Reports and Habitat consume read-only projections.
          </div>
        </div>
        {properties.length > 0 && (
          <select className="nx-select" style={{ maxWidth: 360 }} value={pid || ""}
            onChange={(e) => setPid(e.target.value)} data-testid="nx-passport-property">
            {properties.map((p) => (
              <option key={p.canonical_id} value={p.canonical_id}>
                {p.address.line1}, {p.address.city} {p.address.region}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Identity + status summary */}
      {property && (
        <div className="nx-card elevated" data-testid="nx-passport-header">
          <div className="nx-flex-between">
            <div>
              <div className="nx-label">Property Identity</div>
              <div style={{ fontSize: 20, color: "#fff", marginTop: 4, fontWeight: 700 }}>
                {property.address.line1}
              </div>
              <div style={{ color: "var(--nx-text-secondary)", marginTop: 2, fontSize: 13 }}>
                {property.address.city}, {property.address.region} · {property.canonical_id.slice(0, 10).toUpperCase()}
              </div>
            </div>
            <div style={{ textAlign: "right" }}>
              <span className={`nx-pill ${passport?.passport ? "ok" : "warn"}`} data-testid="nx-passport-state">
                <ShieldCheck size={12} strokeWidth={2} /> {passport?.passport ? "Active" : "Pending"}
              </span>
              <div className="nx-label" style={{ marginTop: 8 }}>
                Last update · {timeline[0]?.at?.slice(0, 10) || "—"}
              </div>
            </div>
          </div>

          <div className="nx-grid cols-4" style={{ marginTop: 18 }}>
            <div className="nx-metric-block">
              <div className="k">Inspections</div>
              <div className="v cy">
                {timeline.filter((t) => t.kind === "INSPECTION").length}
              </div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Findings</div>
              <div className="v">{passport?.entries?.length || 0}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Timeline</div>
              <div className="v or">{timeline.length}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">AWE</div>
              <div className="v gd">{awe?.composite_index ?? "—"}</div>
            </div>
          </div>
        </div>
      )}

      {/* AWE band */}
      {awe && (
        <>
          <div className="nx-section-title">
            <span className="num">§01</span>
            <span className="label">AWE Composite</span>
            <span className="rule" />
            <Link to="/nextgen/awe" className="nx-card-action" data-testid="nx-passport-open-awe">
              Details <ArrowUpRight size={13} strokeWidth={1.8} />
            </Link>
          </div>
          <div className="nx-awe-band" data-testid="nx-passport-awe">
            <MiniRing label="Air" v={awe.air.score} color="#4DF6FF" icon={<Wind size={16} strokeWidth={1.6} />} />
            <MiniRing label="Water" v={awe.water.score} color="#4DF6FF" icon={<Droplet size={16} strokeWidth={1.6} />} />
            <MiniRing label="Energy" v={awe.energy.score} color="#FF7B00" icon={<Sun size={16} strokeWidth={1.6} />} />
            <MiniRing label="Composite" v={awe.composite_index} color="#FFB020" icon={<Sparkles size={16} strokeWidth={1.6} />} />
          </div>
          <div className="nx-flex nx-gap-3" style={{ marginTop: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span className={`nx-pill ${awe.release_state === "CALIBRATED_GENERAL" ? "ok" : "warn"}`}>
              {awe.release_state.replace(/_/g, " ")}
            </span>
            <span className="nx-label">Confidence · {awe.confidence_pct}%</span>
            <span className="nx-label">Evidence · {awe.evidence_completeness_pct}%</span>
          </div>
        </>
      )}

      {/* Share controls */}
      {pid && (
        <>
          <div className="nx-section-title">
            <span className="num">§02</span>
            <span className="label">Homeowner Share</span>
            <span className="rule" />
          </div>
          <div className="nx-card">
            <div className="nx-flex nx-gap-3" style={{ flexWrap: "wrap", alignItems: "center" }}>
              <button className="nx-btn" disabled={linkBusy}
                onClick={async () => {
                  setLinkBusy(true);
                  try {
                    const r = await nxIssueHabitatLink(pid, 168, "homeowner");
                    const url = `${window.location.origin}${r.public_url}`;
                    await navigator.clipboard?.writeText(url).catch(() => {});
                    setLinkOut({ url, ...r });
                  } finally { setLinkBusy(false); }
                }}
                data-testid="nx-share-homeowner">
                <Share2 size={16} strokeWidth={1.8} />
                {linkBusy ? "Issuing…" : "Share with Homeowner"}
              </button>
              <a className="nx-btn ghost" target="_blank" rel="noreferrer"
                href="#"
                onClick={(e) => { e.preventDefault(); nxOpenReportHtml(pid, template); }}
                data-testid="nx-open-html-report">
                <ExternalLink size={14} /> Open HTML Report
              </a>
              <Link to="/nextgen/habitat" className="nx-btn subtle" data-testid="nx-manage-habitat">
                Manage Links
              </Link>
            </div>
            {linkOut && (
              <div className="nx-copied-inline" data-testid="nx-share-out">
                <Check size={14} color="var(--nx-success)" />
                <span style={{ color: "var(--nx-success)", fontFamily: "var(--nx-font-mono)", fontSize: 12, wordBreak: "break-all" }}>
                  {linkOut.url}
                </span>
                <span className="nx-label">Expires {new Date(linkOut.expires_at).toLocaleString()}</span>
              </div>
            )}
          </div>
        </>
      )}

      {/* Ledger */}
      <div className="nx-section-title">
        <span className="num">§03</span>
        <span className="label">Passport Ledger</span>
        <span className="rule" />
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
        {AUDIENCES.map((a) => (
          <button key={a} className={`nx-filter-chip ${audience === a ? "active" : ""}`}
            onClick={() => setAudience(a)} data-testid={`nx-passport-audience-${a}`}>{a}</button>
        ))}
      </div>
      {!passport?.passport ? (
        <div className="nx-empty" data-testid="nx-passport-empty">No passport for this property yet</div>
      ) : (
        <div className="nx-card" style={{ padding: 0 }}>
          <div style={{ overflowX: "auto" }}>
            <table className="nx-table">
              <thead><tr>
                <th>Seq</th><th>Type</th><th>System / Component</th><th>Severity</th>
                <th>Prior Hash</th><th>Content Hash</th><th>Signed</th>
              </tr></thead>
              <tbody>
                {passport.entries.map((e) => (
                  <tr key={e.canonical_id}>
                    <td style={{ fontFamily: "var(--nx-font-mono)", color: "var(--nx-orange)" }}>#{e.seq}</td>
                    <td><span className="nx-pill">{e.entry_type}</span></td>
                    <td style={{ fontSize: 12 }}>
                      {e.payload?.building_system ? `${e.payload.building_system} / ${e.payload.building_component}` : "—"}
                    </td>
                    <td>{e.payload?.severity && <span className="nx-pill gold">{e.payload.severity}</span>}</td>
                    <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-text-muted)" }}>
                      {e.prior_hash ? e.prior_hash.slice(0, 12) + "…" : "GENESIS"}
                    </td>
                    <td style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10, color: "var(--nx-success)" }}>
                      {e.content_hash.slice(0, 12)}…
                    </td>
                    <td style={{ fontSize: 11, color: "var(--nx-text-muted)" }}>
                      {e.at.slice(0, 19).replace("T", " ")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="nx-section-title">
        <span className="num">§04</span>
        <span className="label">Property Timeline</span>
        <span className="rule" />
      </div>
      {timeline.length === 0 ? (
        <div className="nx-empty" data-testid="nx-timeline-empty">No timeline entries yet</div>
      ) : (
        <div className="nx-card" data-testid="nx-timeline">
          {timeline.map((t) => (
            <div key={t.canonical_id} className="nx-timeline-row">
              <span className="dot" />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="nx-flex-between">
                  <span style={{ color: "#fff", fontSize: 14 }}>{t.summary}</span>
                  <span className="nx-pill">{t.kind}</span>
                </div>
                <div className="nx-label" style={{ marginTop: 4 }}>
                  {t.at.slice(0, 19).replace("T", " ")}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Report projections */}
      <div className="nx-section-title">
        <span className="num">§05</span>
        <span className="label">Report Projections</span>
        <span className="rule" />
        <Link to="/nextgen/reports" className="nx-card-action" data-testid="nx-passport-open-reports">
          Full Binder <ArrowUpRight size={13} strokeWidth={1.8} />
        </Link>
      </div>
      <div style={{ display: "flex", gap: 6, marginBottom: 14, flexWrap: "wrap" }}>
        {templates.map((t) => (
          <button key={t} className={`nx-filter-chip ${template === t ? "active" : ""}`}
            onClick={() => setTemplate(t)} data-testid={`nx-report-template-${t}`}>
            {t}
          </button>
        ))}
      </div>
      {report && (
        <div className="nx-card">
          <div className="nx-grid cols-4">
            <div className="nx-metric-block">
              <div className="k">Items</div><div className="v cy">{report.report.counts.total}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">Highest Severity</div>
              <div className="v gd" style={{ fontSize: 22 }}>{report.report.highest_severity || "—"}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">AWE · Water</div>
              <div className="v">{report.report.counts.awe.water}</div>
            </div>
            <div className="nx-metric-block">
              <div className="k">AWE · Energy</div>
              <div className="v">{report.report.counts.awe.energy}</div>
            </div>
          </div>
        </div>
      )}

      <PassportStyles />
    </div>
  );
}

function MiniRing({ label, v, color, icon }) {
  const val = Math.max(0, Math.min(100, v || 0));
  const R = 40, C = 2 * Math.PI * R, off = C - (val / 100) * C;
  return (
    <div className="nx-awe-ring">
      <div style={{ position: "relative", display: "inline-flex" }}>
        <svg width="100" height="100" viewBox="0 0 100 100" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="50" cy="50" r={R} stroke="rgba(77,246,255,0.08)" strokeWidth="8" fill="none" />
          <circle cx="50" cy="50" r={R} stroke={color} strokeWidth="8" fill="none"
            strokeLinecap="round" strokeDasharray={C} strokeDashoffset={off} />
        </svg>
        <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column",
          alignItems: "center", justifyContent: "center" }}>
          <div style={{ fontFamily: "var(--nx-font-tech)", fontVariantNumeric: "tabular-nums", fontSize: 24, fontWeight: 700, color }}>{val}</div>
        </div>
      </div>
      <div className="ring-label">
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
}

function PassportStyles() {
  return (
    <style>{`
      .nx-timeline-row {
        display: flex; gap: 14px;
        padding: 12px 0;
        border-bottom: 1px solid var(--nx-border);
        align-items: flex-start;
      }
      .nx-timeline-row:last-child { border-bottom: none; }
      .nx-timeline-row .dot {
        width: 10px; height: 10px; border-radius: 50%;
        background: var(--nx-cyan); flex-shrink: 0; margin-top: 5px;
        box-shadow: 0 0 12px var(--nx-cyan);
      }
      .nx-copied-inline {
        display: flex; gap: 10px; align-items: center; margin-top: 12px;
        padding: 10px 12px;
        background: rgba(53,227,154,0.06);
        border: 1px solid rgba(53,227,154,0.4);
        border-radius: var(--nx-r-sm);
        flex-wrap: wrap;
      }
    `}</style>
  );
}
