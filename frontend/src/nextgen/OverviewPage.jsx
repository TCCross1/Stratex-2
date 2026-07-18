import React, { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight, Zap, ClipboardList, ShieldCheck, Waves,
  Activity, Radio, Wind, Droplet, Sun, CheckCircle2,
  AlertCircle, Circle, Sparkles,
} from "lucide-react";
import {
  nxOverview, nxHealth, nxMe, nxListProperties, nxListMissions,
  nxPropertyAwe, nxPropertyTimeline,
} from "@/nextgen/api";
import BrandLogo from "@/nextgen/BrandLogo";

/* STRATEX CORE — Home / Operational Overview (Directive 009).
   Mobile-first premium command surface. Reuses all existing NextGen APIs. */

const STAGE_LABELS_SHORT = [
  "Book", "Assign", "Preflt", "Fly", "Ingest", "QA", "Cert",
  "Report", "Deliver", "Passport", "Habitat", "Follow", "Warranty", "Archive", "Retire",
];

export default function OverviewPage() {
  const [ov, setOv] = useState(null);
  const [health, setHealth] = useState(null);
  const [me, setMe] = useState(null);
  const [properties, setProperties] = useState([]);
  const [missions, setMissions] = useState([]);
  const [awe, setAwe] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [err, setErr] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const [o, h, m, props, miss] = await Promise.all([
          nxOverview(), nxHealth(), nxMe(),
          nxListProperties(), nxListMissions(),
        ]);
        setOv(o); setHealth(h); setMe(m);
        setProperties(props.items || []);
        setMissions((miss.items || []).sort((a, b) =>
          new Date(b.created_at) - new Date(a.created_at)));
        // Pull AWE + timeline for the first property for the hero band
        if ((props.items || []).length > 0) {
          const pid = props.items[0].canonical_id;
          nxPropertyAwe(pid).then((r) => setAwe(r.awe)).catch(() => {});
          nxPropertyTimeline(pid).then((r) => setTimeline(r.items || [])).catch(() => {});
        }
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message);
      }
    })();
  }, []);

  const activeMission = useMemo(() => {
    return missions.find((m) => m.stage > 0 && m.stage < 15 && m.state !== "COMPLETED");
  }, [missions]);

  const primaryAction = useMemo(() => {
    if (activeMission) {
      return {
        label: "Continue Active Mission",
        to: `/nextgen/missions/${activeMission.canonical_id}`,
        subtitle: `Mission ${activeMission.canonical_id.slice(0, 8)} · Stage ${activeMission.stage}/15`,
        testid: "nx-primary-continue",
      };
    }
    if (missions.length === 0) {
      return {
        label: "Create First Mission",
        to: "/nextgen/missions/new",
        subtitle: "Launch your first drone inspection",
        testid: "nx-primary-create-first",
      };
    }
    return {
      label: "Create New Mission",
      to: "/nextgen/missions/new",
      subtitle: `${missions.length} missions in ledger`,
      testid: "nx-primary-new",
    };
  }, [activeMission, missions]);

  if (err) return <ErrorState msg={err} />;
  if (!ov) return <LoadingState />;

  const propertyForAwe = properties[0] || null;

  return (
    <div data-testid="nx-overview">
      {/* ── COMPACT BRAND HERO ────────────────────────────── */}
      <section className="nx-hero" data-testid="nx-hero">
        <div className="nx-hero-inner">
          <BrandLogo variant="full" className="nx-hero-logo" ariaLabel="Stratex Core" />
        </div>
        <div className="nx-hero-caption">
          <span>Property Intelligence Platform</span>
          <span className="dot" />
          <span>Preview Build</span>
        </div>
      </section>

      {/* ── OPERATIONAL STATUS STRIP ───────────────────────── */}
      <div className="nx-status-strip" data-testid="nx-status-strip">
        <StatusChip
          k="System"
          v={"Operational"}
          state="ok"
          testid="status-system"
          icon={<Activity size={14} strokeWidth={1.8} />}
        />
        <StatusChip
          k="Tenant"
          v={me?.tenant?.name || me?.tenant_slug || "—"}
          state="cyan"
          testid="status-tenant"
        />
        <StatusChip
          k="Env"
          v="Preview"
          state="orange"
          testid="status-env"
        />
        <StatusChip
          k="Phase"
          v={health?.phase || "—"}
          state="cyan"
          testid="status-phase"
        />
        <StatusChip
          k="Last Sync"
          v={new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
          state="dim"
          testid="status-sync"
        />
      </div>

      {/* ── PRIMARY ACTION ─────────────────────────────────── */}
      <Link
        to={primaryAction.to}
        className="nx-primary-cta"
        data-testid={primaryAction.testid}
      >
        <div className="nx-primary-cta-body">
          <div className="nx-primary-cta-eyebrow">Next Action</div>
          <div className="nx-primary-cta-title">{primaryAction.label}</div>
          <div className="nx-primary-cta-sub">{primaryAction.subtitle}</div>
        </div>
        <div className="nx-primary-cta-arrow">
          <ArrowUpRight size={22} strokeWidth={1.8} />
        </div>
      </Link>

      {/* ── ACTIVE MISSION SUMMARY (when present) ─────────── */}
      {activeMission && (
        <section className="nx-mt-4" data-testid="nx-active-mission">
          <SectionTitle num="§01" label="Active Mission" />
          <ActiveMissionCard mission={activeMission} property={properties.find((p) => p.canonical_id === activeMission.property_id)} />
        </section>
      )}

      {/* ── AWE COMPOSITE ─────────────────────────────────── */}
      {awe && propertyForAwe && (
        <section className="nx-mt-5" data-testid="nx-awe-hero">
          <SectionTitle num="§02" label="AWE Composite · Health Overview" action={{ to: "/nextgen/passport", label: "View details" }} />
          <div className="nx-awe-band">
            <AweRing label="Air" value={awe.air.score} icon={<Wind size={18} strokeWidth={1.6} />} accent="cyan" testid="awe-air" />
            <AweRing label="Water" value={awe.water.score} icon={<Droplet size={18} strokeWidth={1.6} />} accent="cyan" testid="awe-water" />
            <AweRing label="Energy" value={awe.energy.score} icon={<Sun size={18} strokeWidth={1.6} />} accent="orange" testid="awe-energy" />
            <AweRing label="Composite" value={awe.composite_index} icon={<Sparkles size={18} strokeWidth={1.6} />} accent="composite" testid="awe-composite" />
          </div>
          <div className="nx-awe-meta" data-testid="nx-awe-release">
            <span className={`nx-pill ${awe.release_state === "CALIBRATED_GENERAL" ? "ok" : "warn"}`}>
              {awe.release_state.replace(/_/g, " ")}
            </span>
            <span className="nx-label">Confidence · {awe.confidence_pct}%</span>
            <span className="nx-label">Evidence · {awe.evidence_completeness_pct}%</span>
          </div>
        </section>
      )}

      {/* ── KPI STRIP ─────────────────────────────────────── */}
      <section className="nx-mt-5">
        <SectionTitle num="§03" label="System Metrics" />
        <div className="nx-grid cols-4 metrics-2" data-testid="nx-kpis">
          <Metric k="Properties" v={ov.counts.properties_active} tint="cy" sub="Canonical identities" />
          <Metric k="Missions" v={ov.counts.missions_total} tint="or" sub="Across all products" />
          <Metric k="Stages Live" v={`${ov.missions_by_stage.filter((s) => s.count > 0).length}/15`} tint="gd" sub="Operational chain" />
          <Metric k="Passports" v={properties.length} sub="Property records" />
        </div>
      </section>

      {/* ── STAGE STRIP ───────────────────────────────────── */}
      <section className="nx-mt-5">
        <SectionTitle num="§04" label="Operational Chain — 15 Stages" />
        <div className="nx-card">
          <div className="nx-stage-strip">
            {ov.missions_by_stage.map((s) => (
              <div key={s.stage}
                className={`cell ${s.count > 0 ? "active" : ""}`}
                data-testid={`nx-stage-${s.stage}`}
                title={s.label}
              >
                <span className="n">{String(s.stage).padStart(2, "0")}</span>
                {STAGE_LABELS_SHORT[s.stage - 1] || s.label}
                {s.count > 0 && <span className="c">{s.count}</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── RECENT ACTIVITY ────────────────────────────────── */}
      <section className="nx-mt-5">
        <SectionTitle num="§05" label="Recent Activity" action={missions.length > 0 ? { to: "/nextgen/missions", label: "See all" } : null} />
        {missions.length === 0 && timeline.length === 0 ? (
          <div className="nx-empty" data-testid="nx-recent-empty">No activity yet · create your first mission to begin</div>
        ) : (
          <div className="nx-card" style={{ padding: 0 }}>
            <ul className="nx-activity-list" data-testid="nx-recent-list">
              {timeline.slice(0, 3).map((t) => (
                <li key={t.canonical_id}>
                  <div className="ico ok"><CheckCircle2 size={18} strokeWidth={1.6} /></div>
                  <div className="body">
                    <div className="row">
                      <span className="title">{t.summary}</span>
                      <span className="time">{relTime(t.at)}</span>
                    </div>
                    <div className="meta">{t.kind}</div>
                  </div>
                </li>
              ))}
              {missions.slice(0, 4).map((m) => (
                <li key={m.canonical_id}>
                  <div className="ico"><Radio size={18} strokeWidth={1.6} /></div>
                  <div className="body">
                    <div className="row">
                      <span className="title">Mission {m.canonical_id.slice(0, 8)}</span>
                      <span className="time">{relTime(m.created_at)}</span>
                    </div>
                    <div className="meta">
                      <span className="nx-pill orange" style={{ marginRight: 6 }}>{m.product}</span>
                      <span className="nx-pill">STAGE {m.stage}/15</span>
                    </div>
                  </div>
                  <Link className="nx-card-action" to={`/nextgen/missions/${m.canonical_id}`} data-testid={`nx-recent-open-${m.canonical_id}`}>
                    Open <ArrowUpRight size={13} strokeWidth={1.8} />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </section>

      <StyleBlock />
    </div>
  );
}

/* ── Sub-components ───────────────────────────────────────── */

function ActiveMissionCard({ mission, property }) {
  const nextAction = mission.stage < 4 ? "Preflight & Capture" :
                     mission.stage < 6 ? "Upload Remaining Evidence" :
                     mission.stage < 8 ? "Complete QA Review" :
                     mission.stage < 10 ? "Deliver Report" :
                     mission.stage < 12 ? "Share with Homeowner" : "Archive";
  const pct = Math.round((mission.stage / 15) * 100);

  return (
    <Link
      to={`/nextgen/missions/${mission.canonical_id}`}
      className="nx-card elevated"
      style={{ display: "block", textDecoration: "none", color: "inherit" }}
      data-testid="nx-active-mission-card"
    >
      <div className="nx-flex-between">
        <div>
          <div className="nx-label">Mission · {mission.canonical_id.slice(0, 8)}</div>
          <div style={{ fontSize: 20, fontWeight: 700, color: "#fff", marginTop: 4 }}>
            {mission.product.replace(/_/g, " ")}
          </div>
          {property && (
            <div style={{ color: "var(--nx-text-secondary)", fontSize: 13, marginTop: 4 }}>
              {property.address.line1}, {property.address.city} {property.address.region}
            </div>
          )}
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontFamily: "var(--nx-font-tech)", fontVariantNumeric: "tabular-nums", fontSize: 34, color: "var(--nx-cyan)", fontWeight: 700, lineHeight: 1 }}>{pct}%</div>
          <div className="nx-label" style={{ marginTop: 4 }}>Complete</div>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <div className="nx-progress" data-testid="nx-mission-progress">
          <div className="fill" style={{ width: `${pct}%` }} />
        </div>
        <div className="nx-flex-between" style={{ marginTop: 10 }}>
          <span className="nx-pill cyan">STAGE {mission.stage}/15</span>
          <span className="nx-pill dim">{mission.state}</span>
          <span className="nx-pill gold">${(mission.price?.amount_cents / 100 || 0).toFixed(0)}</span>
        </div>
      </div>

      <div style={{ marginTop: 18, paddingTop: 14, borderTop: "1px solid var(--nx-border)" }}>
        <div className="nx-flex-between">
          <div>
            <div className="nx-label">Next Action</div>
            <div style={{ color: "#fff", marginTop: 4, fontWeight: 600 }}>{nextAction}</div>
          </div>
          <ArrowUpRight size={20} strokeWidth={1.8} color="var(--nx-cyan)" />
        </div>
      </div>
    </Link>
  );
}

function AweRing({ label, value, icon, accent = "cyan", testid }) {
  const stroke = accent === "orange" ? "#FF7B00" :
                 accent === "composite" ? "#FFB020" : "#4DF6FF";
  const v = Math.max(0, Math.min(100, value || 0));
  const R = 44, C = 2 * Math.PI * R, off = C - (v / 100) * C;
  return (
    <div className="nx-awe-ring" data-testid={testid}>
      <div className="nx-ring" style={{ ["--size"]: "108px", ["--thickness"]: "9px" }}>
        <svg width="108" height="108" viewBox="0 0 108 108" aria-hidden="true">
          <circle cx="54" cy="54" r={R} stroke="rgba(77,246,255,0.08)" strokeWidth="9" fill="none" />
          <circle cx="54" cy="54" r={R} stroke={stroke} strokeWidth="9" fill="none"
            strokeLinecap="round" strokeDasharray={C} strokeDashoffset={off}
            style={{ transition: "stroke-dashoffset 0.6s ease" }} />
        </svg>
        <div className="ring-value" style={{ color: stroke }}>{v}</div>
      </div>
      <div className="ring-label">
        {icon}
        <span>{label}</span>
      </div>
    </div>
  );
}

function StatusChip({ k, v, state = "dim", testid, icon }) {
  return (
    <div className={`nx-status-chip ${state}`} data-testid={testid}>
      {icon}
      <div>
        <div className="k">{k}</div>
        <div className="v">{v}</div>
      </div>
    </div>
  );
}

function Metric({ k, v, tint, sub }) {
  return (
    <div className="nx-metric-block">
      <div className="k">{k}</div>
      <div className={`v ${tint || ""}`}>{v}</div>
      {sub && <div className="s">{sub}</div>}
    </div>
  );
}

function SectionTitle({ num, label, action }) {
  return (
    <div className="nx-section-title">
      <span className="num">{num}</span>
      <span className="label">{label}</span>
      <span className="rule" />
      {action && (
        <Link className="nx-card-action" to={action.to} data-testid={`nx-section-action-${label.toLowerCase().replace(/\s+/g, "-")}`}>
          {action.label} <ArrowUpRight size={13} strokeWidth={1.8} />
        </Link>
      )}
    </div>
  );
}

function LoadingState() {
  return (
    <div style={{ padding: 60, textAlign: "center" }} data-testid="nx-loading">
      <div className="nx-label" style={{ letterSpacing: "0.32em" }}>// Loading operational overview…</div>
    </div>
  );
}

function ErrorState({ msg }) {
  return (
    <div className="nx-card" style={{ borderColor: "var(--nx-critical)", color: "var(--nx-critical)" }} data-testid="nx-error">
      <div className="nx-label" style={{ color: "var(--nx-critical)" }}>// System error</div>
      <div style={{ marginTop: 6 }}>{String(msg)}</div>
    </div>
  );
}

function relTime(iso) {
  if (!iso) return "—";
  const t = new Date(iso).getTime();
  const s = Math.round((Date.now() - t) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.round(s / 60)}m ago`;
  if (s < 86400) return `${Math.round(s / 3600)}h ago`;
  return `${Math.round(s / 86400)}d ago`;
}

/* Home-specific styles co-located to avoid coupling to global CSS churn. */
function StyleBlock() {
  return (
    <style>{`
      .nx-hero {
        border: 1px solid var(--nx-border);
        background:
          radial-gradient(700px 260px at 50% -20%, rgba(77,246,255,0.10), transparent 60%),
          radial-gradient(500px 240px at 90% 110%, rgba(255,123,0,0.07), transparent 60%),
          linear-gradient(180deg, var(--nx-panel), var(--nx-panel-2));
        border-radius: var(--nx-r-lg);
        padding: 20px 20px 14px 20px;
        margin-bottom: 14px;
        position: relative;
        overflow: hidden;
      }
      .nx-hero::before, .nx-hero::after {
        content: ""; position: absolute; width: 18px; height: 18px; border: 1px solid var(--nx-cyan);
      }
      .nx-hero::before { top: 8px; left: 8px; border-right: none; border-bottom: none; }
      .nx-hero::after { bottom: 8px; right: 8px; border-left: none; border-top: none; }
      .nx-hero-inner { display: flex; justify-content: center; align-items: center; }
      .nx-hero-logo {
        width: 100%; max-width: 460px;
        aspect-ratio: 800 / 620;
        height: auto;
      }
      .nx-hero-caption {
        display: flex; justify-content: center; align-items: center; gap: 10px;
        color: var(--nx-text-muted); font-family: var(--nx-font-tech);
        font-size: 10px; letter-spacing: 0.32em; text-transform: uppercase;
        margin-top: 6px;
      }
      .nx-hero-caption .dot { width: 4px; height: 4px; border-radius: 50%; background: var(--nx-cyan); }

      .nx-status-strip {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 10px;
        margin-bottom: 16px;
      }
      @media (max-width: 820px) {
        .nx-status-strip {
          display: flex; overflow-x: auto; gap: 8px;
          scrollbar-width: none; -ms-overflow-style: none;
          padding-bottom: 2px;
        }
        .nx-status-strip::-webkit-scrollbar { display: none; }
        .nx-hero-logo { max-width: 320px; }
      }
      .nx-status-chip {
        display: flex; align-items: center; gap: 10px;
        padding: 10px 14px;
        border: 1px solid var(--nx-border);
        border-radius: var(--nx-r-sm);
        background: linear-gradient(180deg, var(--nx-panel), var(--nx-panel-2));
        min-width: 120px;
      }
      .nx-status-chip .k {
        font-family: var(--nx-font-tech); font-size: 9px;
        color: var(--nx-text-muted); letter-spacing: 0.28em; text-transform: uppercase;
      }
      .nx-status-chip .v {
        color: #fff; font-family: var(--nx-font-tech);
        letter-spacing: 0.06em; font-size: 12.5px; margin-top: 2px;
      }
      .nx-status-chip.ok { border-color: rgba(53,227,154,0.4); color: var(--nx-success); }
      .nx-status-chip.ok .v { color: var(--nx-success); }
      .nx-status-chip.orange { border-color: rgba(255,123,0,0.4); }
      .nx-status-chip.orange .v { color: var(--nx-orange); }
      .nx-status-chip.cyan { border-color: rgba(77,246,255,0.4); }
      .nx-status-chip.cyan .v { color: var(--nx-cyan); }

      .nx-primary-cta {
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
        padding: 18px 22px;
        background: linear-gradient(180deg, #0F1826, #0A1220);
        border: 1px solid var(--nx-border-strong);
        border-radius: var(--nx-r-md);
        text-decoration: none;
        color: inherit;
        position: relative;
        transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.2s ease;
      }
      .nx-primary-cta::before {
        content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
        border-top-left-radius: var(--nx-r-md); border-bottom-left-radius: var(--nx-r-md);
        background: linear-gradient(180deg, var(--nx-cyan), var(--nx-orange));
      }
      .nx-primary-cta:hover { border-color: var(--nx-cyan); box-shadow: var(--nx-ring-active); transform: translateY(-1px); }
      .nx-primary-cta-eyebrow {
        font-family: var(--nx-font-tech); font-size: 10px;
        color: var(--nx-cyan); letter-spacing: 0.32em; text-transform: uppercase;
      }
      .nx-primary-cta-title {
        font-size: 20px; font-weight: 700; color: #fff; margin: 4px 0 4px 0;
      }
      .nx-primary-cta-sub {
        color: var(--nx-text-secondary); font-size: 13px;
      }
      .nx-primary-cta-arrow {
        width: 44px; height: 44px; border-radius: 50%;
        border: 1px solid var(--nx-cyan);
        display: inline-flex; align-items: center; justify-content: center;
        color: var(--nx-cyan);
        flex-shrink: 0;
      }

      .nx-awe-band {
        display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px;
        padding: 20px; border: 1px solid var(--nx-border);
        border-radius: var(--nx-r-md);
        background: linear-gradient(180deg, var(--nx-panel), var(--nx-panel-2));
      }
      .nx-awe-ring { display: flex; flex-direction: column; align-items: center; gap: 10px; }
      .nx-awe-ring .ring-label {
        display: flex; align-items: center; gap: 6px;
        font-family: var(--nx-font-tech);
        font-size: 10px; letter-spacing: 0.28em; text-transform: uppercase;
        color: var(--nx-text-secondary);
      }
      @media (max-width: 820px) {
        .nx-awe-band { grid-template-columns: repeat(2, 1fr); padding: 16px; }
      }
      .nx-awe-meta {
        display: flex; gap: 12px; align-items: center; flex-wrap: wrap;
        margin-top: 10px;
      }

      .nx-activity-list {
        list-style: none; padding: 0; margin: 0;
      }
      .nx-activity-list li {
        display: flex; align-items: center; gap: 14px;
        padding: 14px 18px;
        border-bottom: 1px solid var(--nx-border);
      }
      .nx-activity-list li:last-child { border-bottom: none; }
      .nx-activity-list .ico {
        width: 36px; height: 36px; border-radius: var(--nx-r-sm);
        display: inline-flex; align-items: center; justify-content: center;
        background: rgba(77,246,255,0.06);
        color: var(--nx-cyan);
        flex-shrink: 0;
      }
      .nx-activity-list .ico.ok { background: rgba(53,227,154,0.08); color: var(--nx-success); }
      .nx-activity-list .body { flex: 1; min-width: 0; }
      .nx-activity-list .row { display: flex; justify-content: space-between; align-items: baseline; gap: 8px; }
      .nx-activity-list .title { color: #fff; font-weight: 500; font-size: 14px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .nx-activity-list .time { color: var(--nx-text-muted); font-family: var(--nx-font-tech); font-size: 10px; letter-spacing: 0.16em; text-transform: uppercase; flex-shrink: 0; }
      .nx-activity-list .meta { color: var(--nx-text-secondary); font-size: 12px; margin-top: 3px; }
    `}</style>
  );
}
