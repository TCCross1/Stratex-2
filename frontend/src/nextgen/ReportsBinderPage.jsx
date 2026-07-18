import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  FileText, ExternalLink, RefreshCw, Home, HardHat, Building2,
  Waves, ShieldCheck, Users, Briefcase, ArrowUpRight, AlertCircle,
} from "lucide-react";
import {
  nxReportTemplates, nxListProperties, nxPropertyReport,
  nxOpenReportHtml,
} from "@/nextgen/api";

/* Reports Binder (Directive 009 · replaces ReportsStub).
   Real backend: /report-templates + /properties/{id}/report/{template}. */

const TEMPLATE_META = {
  homeowner_summary:  { name: "Homeowner Summary",   desc: "Customer-friendly overview",     icon: Home,       tint: "cyan" },
  contractor_full:    { name: "Contractor Report",   desc: "Scope of work & findings",       icon: HardHat,    tint: "orange" },
  property_health:    { name: "Property Health",     desc: "Detailed condition analysis",    icon: ShieldCheck,tint: "cyan" },
  energy_focused:     { name: "AWE Intelligence",    desc: "Air · Water · Energy analysis",  icon: Waves,      tint: "cyan" },
  insurance_claim:    { name: "Insurance Summary",   desc: "Carrier-ready claim summary",    icon: ShieldCheck,tint: "gold" },
  hoa_summary:        { name: "HOA Summary",         desc: "HOA-facing property summary",    icon: Users,      tint: "orange" },
  executive_summary:  { name: "Executive Summary",   desc: "Owner / executive brief",        icon: Briefcase,  tint: "gold" },
};

export default function ReportsBinderPage() {
  const [templates, setTemplates] = useState([]);
  const [properties, setProperties] = useState([]);
  const [pid, setPid] = useState(null);
  const [selected, setSelected] = useState(null);
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    nxReportTemplates().then((d) => setTemplates(d.templates || []));
    nxListProperties().then((d) => {
      setProperties(d.items || []);
      if (d.items?.length) setPid(d.items[0].canonical_id);
    });
  }, []);

  const generate = async (templateKey) => {
    if (!pid) return;
    setSelected(templateKey);
    setBusy(true);
    try {
      const r = await nxPropertyReport(pid, templateKey);
      setReport(r);
    } catch {
      setReport(null);
    } finally { setBusy(false); }
  };

  return (
    <div data-testid="nx-reports">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// REPORTS BINDER</div>
          <h1 className="nx-page-title">Reports</h1>
          <div className="nx-page-sub">
            Approved DayScan · AWE · Elite report projections. Every report is a read-only projection of
            approved intelligence — not a source of truth.
          </div>
        </div>
        {properties.length > 0 && (
          <select
            className="nx-select"
            style={{ maxWidth: 360 }}
            value={pid || ""}
            onChange={(e) => { setPid(e.target.value); setReport(null); setSelected(null); }}
            data-testid="nx-reports-property"
          >
            {properties.map((p) => (
              <option key={p.canonical_id} value={p.canonical_id}>
                {p.address.line1}, {p.address.city} {p.address.region}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* Templates */}
      <div className="nx-section-title">
        <span className="num">§01</span>
        <span className="label">Templates</span>
        <span className="rule" />
      </div>

      {templates.length === 0 ? (
        <div className="nx-empty">Loading templates…</div>
      ) : (
        <div className="nx-report-grid" data-testid="nx-report-grid">
          {templates.map((key) => {
            const meta = TEMPLATE_META[key] || { name: key, desc: "Report projection", icon: FileText, tint: "cyan" };
            const Icon = meta.icon;
            return (
              <button
                key={key}
                className={`nx-report-tile ${selected === key ? "selected" : ""}`}
                onClick={() => generate(key)}
                disabled={!pid}
                data-testid={`nx-report-template-${key}`}
              >
                <div className={`icon-wrap ${meta.tint}`}>
                  <Icon size={20} strokeWidth={1.6} />
                </div>
                <div className="body">
                  <div className="name">{meta.name}</div>
                  <div className="desc">{meta.desc}</div>
                </div>
                <ArrowUpRight size={18} strokeWidth={1.6} color="var(--nx-cyan)" />
              </button>
            );
          })}
        </div>
      )}

      {!pid && (
        <div className="nx-empty" style={{ marginTop: 20 }} data-testid="nx-reports-no-property">
          Select a property to generate report projections.
        </div>
      )}

      {/* PDF availability notice */}
      <div className="nx-notice" data-testid="nx-reports-pdf-notice">
        <AlertCircle size={16} strokeWidth={1.6} />
        <span>PDF renderer pending — reports are delivered as JSON projections + HTML previews.</span>
      </div>

      {/* Report preview */}
      {selected && (
        <div style={{ marginTop: 22 }}>
          <div className="nx-section-title">
            <span className="num">§02</span>
            <span className="label">Preview · {TEMPLATE_META[selected]?.name || selected}</span>
            <span className="rule" />
            <a
              className="nx-card-action"
              href="#"
              onClick={(e) => { e.preventDefault(); nxOpenReportHtml(pid, selected); }}
              data-testid={`nx-report-html-${selected}`}
            >
              Open HTML <ExternalLink size={13} strokeWidth={1.8} />
            </a>
            <button
              className="nx-card-action"
              onClick={() => generate(selected)}
              style={{ background: "transparent", border: "none", cursor: "pointer" }}
              data-testid={`nx-report-refresh-${selected}`}
            >
              Refresh <RefreshCw size={13} strokeWidth={1.8} />
            </button>
          </div>

          {busy ? (
            <div className="nx-empty">Generating projection…</div>
          ) : !report ? (
            <div className="nx-empty">Projection unavailable — property may lack approved intelligence.</div>
          ) : (
            <div className="nx-card elevated" data-testid="nx-report-preview">
              <div className="nx-grid cols-4">
                <div className="nx-metric-block">
                  <div className="k">Items</div>
                  <div className="v cy">{report.report.counts.total}</div>
                </div>
                <div className="nx-metric-block">
                  <div className="k">Highest Severity</div>
                  <div className="v or" style={{ fontSize: 22 }}>{report.report.highest_severity || "—"}</div>
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

              <div className="nx-label" style={{ marginTop: 18, marginBottom: 6 }}>Report Items</div>
              {report.report.items.length === 0 ? (
                <div className="nx-empty" style={{ marginTop: 6 }}>No items visible to this template.</div>
              ) : (
                <div style={{ overflowX: "auto" }}>
                  <table className="nx-table">
                    <thead>
                      <tr>{Object.keys(report.report.items[0]).map((k) => (<th key={k}>{k}</th>))}</tr>
                    </thead>
                    <tbody>
                      {report.report.items.map((row, i) => (
                        <tr key={i}>
                          {Object.entries(row).map(([k, v]) => (
                            <td key={k} style={{ fontSize: 11 }}>
                              {typeof v === "object" ? (
                                <span style={{ fontFamily: "var(--nx-font-mono)", fontSize: 10 }}>
                                  {JSON.stringify(v)}
                                </span>
                              ) : String(v)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <ReportsStyles />
    </div>
  );
}

function ReportsStyles() {
  return (
    <style>{`
      .nx-report-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
      }
      .nx-report-tile {
        display: flex; align-items: center; gap: 14px;
        padding: 16px 18px;
        background: linear-gradient(180deg, var(--nx-panel), var(--nx-panel-2));
        border: 1px solid var(--nx-border);
        border-radius: var(--nx-r-md);
        text-align: left; cursor: pointer;
        color: inherit; font-family: inherit;
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
        min-height: 76px;
      }
      .nx-report-tile:disabled { opacity: 0.45; cursor: not-allowed; }
      .nx-report-tile:not(:disabled):hover {
        border-color: var(--nx-cyan-line); transform: translateY(-2px);
        box-shadow: 0 10px 26px rgba(0,0,0,0.4);
      }
      .nx-report-tile.selected {
        border-color: var(--nx-cyan);
        box-shadow: inset 0 0 0 1px var(--nx-cyan), 0 0 24px rgba(77,246,255,0.12);
      }
      .nx-report-tile .icon-wrap {
        width: 40px; height: 40px; border-radius: var(--nx-r-sm);
        display: inline-flex; align-items: center; justify-content: center;
        background: rgba(77,246,255,0.08); color: var(--nx-cyan); flex-shrink: 0;
      }
      .nx-report-tile .icon-wrap.orange { background: rgba(255,123,0,0.08); color: var(--nx-orange); }
      .nx-report-tile .icon-wrap.gold { background: rgba(255,176,32,0.08); color: var(--nx-gold); }
      .nx-report-tile .body { flex: 1; min-width: 0; }
      .nx-report-tile .name { color: #fff; font-weight: 600; font-size: 14px; }
      .nx-report-tile .desc { color: var(--nx-text-secondary); font-size: 12px; margin-top: 2px; }

      .nx-notice {
        display: flex; align-items: center; gap: 10px;
        margin-top: 16px;
        padding: 12px 14px;
        border: 1px solid rgba(255,176,32,0.35);
        background: rgba(255,176,32,0.05);
        color: var(--nx-warning);
        border-radius: var(--nx-r-sm);
        font-family: var(--nx-font-tech);
        font-size: 11px; letter-spacing: 0.16em; text-transform: uppercase;
      }
    `}</style>
  );
}
