import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  nxListProperties, nxPropertyPassport, nxPropertyTimeline,
  nxPropertyReport, nxReportTemplates, nxPropertyAwe,
  nxIssueHabitatLink, nxHabitatReportHtmlUrl,
} from "@/nextgen/api";

/* Property Passport + Timeline + Report projections — Directive 007.
   The permanent property intelligence record and its consumers. */

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

  return (
    <div data-testid="nx-passport">
      <div className="nx-topbar-title" style={{ color: "#4DF6FF" }}>
        // PROPERTY PASSPORT · DIRECTIVE 007
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 20 }}>
        <div>
          <h1 className="nx-h1">Property Passport</h1>
          <div className="nx-sub">
            Canonical hash-chained property intelligence ledger. Only the Passport Service
            appends. Reports and Habitat consume read-only projections.
          </div>
        </div>
        <select className="nx-select" style={{ width: 320 }} value={pid || ""}
          onChange={(e) => setPid(e.target.value)} data-testid="nx-passport-property">
          {properties.map((p) => (
            <option key={p.canonical_id} value={p.canonical_id}>
              {p.address.line1}, {p.address.city} {p.address.region}
            </option>
          ))}
        </select>
      </div>

      {/* AWE Composite + Share */}
      {awe && (
        <>
          <h2 className="nx-h2"><span className="num">§00</span>AWE Composite · Deterministic (Directive 008)</h2>
          <div className="nx-grid cols-4" data-testid="nx-awe-panel">
            {["air", "water", "energy"].map((k) => {
              const score = awe[k].score;
              const color = score >= 80 ? "#00FF9C" : score >= 60 ? "#FFB020" : "#FF5A5F";
              return (
                <div key={k} className="nx-stat">
                  <div className="k">// {k}</div>
                  <div className="v" style={{ color, fontSize: 34 }}>{score}</div>
                  <div className="s">{awe[k].contributing_pios} contributing PIOs</div>
                </div>
              );
            })}
            <div className="nx-stat" style={{ borderColor: "#FFB020" }}>
              <div className="k">// Composite Index</div>
              <div className="v" style={{ color: "#FFB020", fontSize: 40 }}>{awe.composite_index}</div>
              <div className="s">Release · <b style={{ color: "#FFB020" }}>{awe.release_state}</b> · Conf {awe.confidence_pct}% · Evidence {awe.evidence_completeness_pct}%</div>
            </div>
          </div>

          <div className="nx-panel" style={{ marginTop: 14 }}>
            <div className="corner">// DIRECTIVE 008 · HOMEOWNER DELIVERY</div>
            <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
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
                {linkBusy ? "Issuing…" : "Share with Homeowner (copy link)"}
              </button>
              <a className="nx-btn ghost" target="_blank" rel="noreferrer"
                href={nxHabitatReportHtmlUrl(pid, template)}
                data-testid="nx-open-html-report">Open HTML Report</a>
              {linkOut && (
                <div style={{ fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
                  color: "#00FF9C", marginLeft: 8, wordBreak: "break-all", flex: 1 }}>
                  {linkOut.url}
                  <div style={{ color: "#8A9BAE", fontSize: 10, marginTop: 4 }}>
                    Expires {new Date(linkOut.expires_at).toLocaleString()} · copied to clipboard
                  </div>
                </div>
              )}
            </div>
          </div>
        </>
      )}

      {/* Passport ledger */}
      <h2 className="nx-h2"><span className="num">§01</span>Passport Ledger</h2>
      <div style={{ display: "flex", gap: 10, marginBottom: 12 }}>
        {["internal", "contractor", "homeowner", "adjuster", "insurer"].map((a) => (
          <button key={a} className={`nx-btn ${audience === a ? "" : "ghost"} small`}
            onClick={() => setAudience(a)} data-testid={`nx-passport-audience-${a}`}>{a}</button>
        ))}
      </div>
      {!passport?.passport ? (
        <div className="nx-empty">No passport for this property yet</div>
      ) : (
        <div className="nx-panel" style={{ padding: 0 }}>
          <table className="nx-table">
            <thead><tr>
              <th>Seq</th><th>Type</th><th>System / Component</th><th>Severity</th>
              <th>Prior Hash</th><th>Content Hash</th><th>Signed At</th>
            </tr></thead>
            <tbody>
              {passport.entries.map((e) => (
                <tr key={e.canonical_id}>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", color: "#FFB020" }}>#{e.seq}</td>
                  <td><span className="nx-pill">{e.entry_type}</span></td>
                  <td style={{ fontSize: 11 }}>
                    {e.payload?.building_system ? `${e.payload.building_system} / ${e.payload.building_component}` : "—"}
                  </td>
                  <td>{e.payload?.severity && <span className="nx-pill gold">{e.payload.severity}</span>}</td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#8A9BAE" }}>
                    {e.prior_hash ? e.prior_hash.slice(0, 12) + "…" : "GENESIS"}
                  </td>
                  <td style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 9, color: "#00FF9C" }}>
                    {e.content_hash.slice(0, 12)}…
                  </td>
                  <td style={{ fontSize: 10, color: "#8A9BAE" }}>{e.at.slice(0, 19).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Timeline */}
      <h2 className="nx-h2"><span className="num">§02</span>Property Timeline</h2>
      {timeline.length === 0 ? (
        <div className="nx-empty">No timeline entries yet</div>
      ) : (
        <div className="nx-panel">
          <div className="corner">// PERMANENT PROPERTY HISTORY</div>
          {timeline.map((t) => (
            <div key={t.canonical_id} style={{
              display: "grid", gridTemplateColumns: "160px 200px 1fr",
              gap: 12,
              padding: "10px 0", borderBottom: "1px solid #1D2836", fontSize: 12,
              alignItems: "center",
            }}>
              <span style={{ fontFamily: "'JetBrains Mono', monospace", color: "#8A9BAE", fontSize: 10 }}>
                {t.at.slice(0, 19).replace("T", " ")}
              </span>
              <span className="nx-pill" style={{ width: "fit-content", whiteSpace: "nowrap" }}>{t.kind}</span>
              <span style={{ color: "#E6EEF6", minWidth: 0 }}>{t.summary}</span>
            </div>
          ))}
        </div>
      )}

      {/* Report projections */}
      <h2 className="nx-h2"><span className="num">§03</span>Report Projections</h2>
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {templates.map((t) => (
          <button key={t} className={`nx-btn ${template === t ? "" : "ghost"} small`}
            onClick={() => setTemplate(t)} data-testid={`nx-report-template-${t}`}>
            {t}
          </button>
        ))}
      </div>
      {report && (
        <div className="nx-panel">
          <div className="corner">// PROJECTION · READ-ONLY · SOURCED FROM INTELLIGENCE ENGINE</div>
          <div className="nx-grid cols-4" style={{ marginBottom: 12 }}>
            <div className="nx-stat">
              <div className="k">// Items</div><div className="v">{report.report.counts.total}</div>
            </div>
            <div className="nx-stat">
              <div className="k">// Highest Severity</div>
              <div className="v gd" style={{ fontSize: 22 }}>{report.report.highest_severity}</div>
            </div>
            <div className="nx-stat">
              <div className="k">// AWE · Water</div>
              <div className="v cy">{report.report.counts.awe.water}</div>
            </div>
            <div className="nx-stat">
              <div className="k">// AWE · Energy</div>
              <div className="v cy">{report.report.counts.awe.energy}</div>
            </div>
          </div>

          {report.report.items.length === 0 ? (
            <div className="nx-empty">No approved intelligence visible to this template</div>
          ) : (
            <table className="nx-table">
              <thead><tr>
                {Object.keys(report.report.items[0]).map((k) => (
                  <th key={k}>{k}</th>
                ))}
              </tr></thead>
              <tbody>
                {report.report.items.map((row, i) => (
                  <tr key={i}>
                    {Object.entries(row).map(([k, v]) => (
                      <td key={k} style={{ fontSize: 11 }}>
                        {typeof v === "object" ? (
                          <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>
                            {JSON.stringify(v)}
                          </span>
                        ) : String(v)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
