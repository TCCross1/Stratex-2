import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Wind, Droplet, Sun, Sparkles, ArrowUpRight, TrendingUp, Info } from "lucide-react";
import { nxListProperties, nxPropertyAwe } from "@/nextgen/api";

/* AWE Intelligence page (Directive 009 · replaces AweStub).
   Presentation surface over the existing deterministic AWE calculation. */

export default function AwePage() {
  const [properties, setProperties] = useState([]);
  const [pid, setPid] = useState(null);
  const [awe, setAwe] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    nxListProperties().then((d) => {
      setProperties(d.items || []);
      if (d.items?.length) setPid(d.items[0].canonical_id);
      else setLoading(false);
    });
  }, []);

  useEffect(() => {
    if (!pid) return;
    setLoading(true);
    nxPropertyAwe(pid).then((r) => setAwe(r.awe)).finally(() => setLoading(false));
  }, [pid]);

  return (
    <div data-testid="nx-awe">
      <div className="nx-page-header">
        <div>
          <div className="nx-page-eyebrow">// AWE INTELLIGENCE</div>
          <h1 className="nx-page-title">AWE · Air · Water · Energy</h1>
          <div className="nx-page-sub">
            Deterministic composite score derived from approved property intelligence. Never published
            externally before <span style={{ color: "var(--nx-success)" }}>CALIBRATED_GENERAL</span> release state.
          </div>
        </div>
        {properties.length > 0 && (
          <select
            className="nx-select"
            style={{ maxWidth: 360 }}
            value={pid || ""}
            onChange={(e) => setPid(e.target.value)}
            data-testid="nx-awe-property"
          >
            {properties.map((p) => (
              <option key={p.canonical_id} value={p.canonical_id}>
                {p.address.line1}, {p.address.city} {p.address.region}
              </option>
            ))}
          </select>
        )}
      </div>

      {loading ? (
        <div className="nx-empty">Loading AWE intelligence…</div>
      ) : !awe ? (
        <div className="nx-empty" data-testid="nx-awe-empty">
          No AWE data for this property yet — collect evidence and approve intelligence to populate scores.
        </div>
      ) : (
        <>
          {/* Release state banner */}
          <div
            className={`nx-awe-release-banner ${awe.release_state === "CALIBRATED_GENERAL" ? "ok" : "draft"}`}
            data-testid="nx-awe-release-banner"
          >
            <Info size={16} strokeWidth={1.8} />
            <div>
              <div className="nx-label" style={{ color: "inherit" }}>Release State</div>
              <div style={{ fontFamily: "var(--nx-font-tech)", letterSpacing: "0.24em", marginTop: 2 }}>
                {awe.release_state.replace(/_/g, " ")}
              </div>
            </div>
            <div className="rule" />
            <div className="stat">
              <div className="nx-label">Confidence</div>
              <div style={{ color: "#fff", fontFamily: "var(--nx-font-tech)", fontSize: 18 }}>{awe.confidence_pct}%</div>
            </div>
            <div className="stat">
              <div className="nx-label">Evidence</div>
              <div style={{ color: "#fff", fontFamily: "var(--nx-font-tech)", fontSize: 18 }}>{awe.evidence_completeness_pct}%</div>
            </div>
          </div>

          {/* Ring band */}
          <div className="nx-awe-band" style={{ marginTop: 16 }} data-testid="nx-awe-rings">
            <BigRing label="Air" score={awe.air.score} contrib={awe.air.contributing_pios} icon={<Wind size={20} strokeWidth={1.6} />} color="#4DF6FF" testid="ring-air" />
            <BigRing label="Water" score={awe.water.score} contrib={awe.water.contributing_pios} icon={<Droplet size={20} strokeWidth={1.6} />} color="#4DF6FF" testid="ring-water" />
            <BigRing label="Energy" score={awe.energy.score} contrib={awe.energy.contributing_pios} icon={<Sun size={20} strokeWidth={1.6} />} color="#FF7B00" testid="ring-energy" />
            <BigRing label="Composite" score={awe.composite_index} contrib={awe.air.contributing_pios + awe.water.contributing_pios + awe.energy.contributing_pios} icon={<Sparkles size={20} strokeWidth={1.6} />} color="#FFB020" testid="ring-composite" />
          </div>

          {/* Category detail */}
          <div className="nx-section-title">
            <span className="num">§01</span>
            <span className="label">Category Detail</span>
            <span className="rule" />
          </div>
          <div className="nx-grid cols-3">
            <CategoryCard label="Air"    data={awe.air}    icon={<Wind size={18} strokeWidth={1.6} />} color="#4DF6FF" />
            <CategoryCard label="Water"  data={awe.water}  icon={<Droplet size={18} strokeWidth={1.6} />} color="#4DF6FF" />
            <CategoryCard label="Energy" data={awe.energy} icon={<Sun size={18} strokeWidth={1.6} />} color="#FF7B00" />
          </div>

          <div className="nx-section-title">
            <span className="num">§02</span>
            <span className="label">Related</span>
            <span className="rule" />
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            <Link to="/nextgen/passport" className="nx-btn ghost" data-testid="nx-awe-open-passport">
              Property Passport <ArrowUpRight size={14} />
            </Link>
            <Link to="/nextgen/reports" className="nx-btn ghost" data-testid="nx-awe-open-reports">
              Reports Binder <ArrowUpRight size={14} />
            </Link>
          </div>
        </>
      )}

      <AweStyles />
    </div>
  );
}

function BigRing({ label, score, contrib, icon, color, testid }) {
  const v = Math.max(0, Math.min(100, score || 0));
  const R = 60, C = 2 * Math.PI * R, off = C - (v / 100) * C;
  return (
    <div className="nx-awe-ring" data-testid={testid}>
      <div style={{ position: "relative", display: "inline-flex", alignItems: "center", justifyContent: "center" }}>
        <svg width="144" height="144" viewBox="0 0 144 144" style={{ transform: "rotate(-90deg)" }}>
          <circle cx="72" cy="72" r={R} stroke="rgba(77,246,255,0.08)" strokeWidth="10" fill="none" />
          <circle cx="72" cy="72" r={R} stroke={color} strokeWidth="10" fill="none"
            strokeLinecap="round" strokeDasharray={C} strokeDashoffset={off}
            style={{ transition: "stroke-dashoffset 0.6s ease" }} />
        </svg>
        <div style={{ position: "absolute", textAlign: "center" }}>
          <div style={{ fontFamily: "var(--nx-font-tech)", fontVariantNumeric: "tabular-nums", fontSize: 34, fontWeight: 700, color, lineHeight: 1 }}>{v}</div>
          <div className="nx-label" style={{ marginTop: 4 }}>{contrib} PIOs</div>
        </div>
      </div>
      <div className="ring-label">
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
}

function CategoryCard({ label, data, icon, color }) {
  const v = Math.max(0, Math.min(100, data.score || 0));
  return (
    <div className="nx-card">
      <div className="nx-flex-between">
        <div className="nx-flex" style={{ alignItems: "center", gap: 10 }}>
          <span style={{ color, display: "inline-flex" }}>{icon}</span>
          <span className="nx-tech" style={{ color: "#fff", fontSize: 14, letterSpacing: "0.2em" }}>{label}</span>
        </div>
        <span className="nx-pill" style={{ color, borderColor: color }}>{v}/100</span>
      </div>
      <div className="nx-progress" style={{ marginTop: 14 }}>
        <div className="fill" style={{ width: `${v}%`, background: color }} />
      </div>
      <div style={{ marginTop: 14, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
        <div className="nx-metric-block">
          <div className="k">Contributing PIOs</div>
          <div className="v" style={{ fontSize: 22 }}>{data.contributing_pios}</div>
        </div>
        <div className="nx-metric-block">
          <div className="k">Trend</div>
          <div className="v" style={{ fontSize: 22, display: "inline-flex", alignItems: "center", gap: 6 }}>
            <TrendingUp size={18} strokeWidth={1.8} color={color} />
            <span style={{ color }}>–</span>
          </div>
          <div className="s">Historical data pending</div>
        </div>
      </div>
    </div>
  );
}

function AweStyles() {
  return (
    <style>{`
      .nx-awe-release-banner {
        display: flex; align-items: center; gap: 14px;
        padding: 14px 18px; border-radius: var(--nx-r-md);
        border: 1px solid var(--nx-border-strong);
      }
      .nx-awe-release-banner.ok { border-color: rgba(53,227,154,0.4); background: rgba(53,227,154,0.06); color: var(--nx-success); }
      .nx-awe-release-banner.draft { border-color: rgba(255,176,32,0.4); background: rgba(255,176,32,0.05); color: var(--nx-warning); }
      .nx-awe-release-banner .rule { flex: 1; height: 1px; background: currentColor; opacity: 0.2; }
      .nx-awe-release-banner .stat { text-align: right; }
      @media (max-width: 820px) {
        .nx-awe-release-banner { flex-wrap: wrap; }
        .nx-awe-release-banner .rule { display: none; }
      }
    `}</style>
  );
}
