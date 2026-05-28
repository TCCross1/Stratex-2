import React, { useEffect, useState } from "react";
import { Crosshair, TrendingUp, Phone, ChevronDown, ChevronUp } from "lucide-react";
import { api } from "@/lib/api";

/**
 * /onboard — Section 1.4.5 · Competitive Intel
 *
 * JOINs the prospect's annualized 2-year sales book against the 7 seeded
 * Central-Kentucky targets and renders dynamic outreach hook copy keyed to
 * each target's archetype (specialty slate/copper, commercial membrane,
 * industrial PM-assets, high-volume storm, mixed master applicator, high-end
 * residential). Hooks include real dollar figures and a head-to-head delta.
 *
 * Calls public endpoint POST /api/onboarding/competitive-intel — no auth.
 */
const TEAL = "#00F5D4";
const ORANGE = "#FF5400";

const USD = (n) =>
  Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function CompetitiveIntelSection({ historicalSales2y, leadsPerMonth }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState(null);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    const v = Number(historicalSales2y) || 0;
    if (v < 1) { setData(null); return; }
    let cancelled = false;
    setLoading(true);
    setErr(null);
    const t = setTimeout(async () => {
      try {
        const r = await api.post("/onboarding/competitive-intel", {
          historical_sales_2_years: v,
          leads_per_month: Number(leadsPerMonth) || 0,
        });
        if (!cancelled) setData(r.data);
      } catch (e) {
        if (!cancelled) setErr(e?.response?.data?.detail || e.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 350); // light debounce against rapid input changes
    return () => { cancelled = true; clearTimeout(t); };
  }, [historicalSales2y, leadsPerMonth]);

  if (!data && !loading && !err) return null;

  const beats = data?.targets_user_beats || 0;
  const total = data?.targets_count || 0;
  const userReclaim = data?.user?.stratex_annual_reclaim_usd || 0;

  return (
    <section
      data-testid="competitive-intel-section"
      className="mt-8 border bg-[#0B0F19] p-5"
      style={{ borderColor: "rgba(0,245,212,0.30)" }}
    >
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <div className="font-mono text-[10px] tracking-widest uppercase mb-1" style={{ color: TEAL }}>
            // SECTION 1.4.5 — CENTRAL KENTUCKY COMPETITIVE INTEL
          </div>
          <h3 className="font-display text-base md:text-lg uppercase tracking-[0.06em] text-silver">
            Your annualized book vs. the 7 local targets
          </h3>
          <p className="font-body text-[11.5px] text-muted-hud mt-1 leading-relaxed max-w-2xl">
            STRATEX cross-references your reported book against the seven incumbent Lexington-radius
            contractors. Each row is a calibrated revenue-and-overhead-leak estimate. Hook copy is
            generated live — ready to drop into outreach.
          </p>
        </div>
        <button
          onClick={() => setExpanded((e) => !e)}
          data-testid="competitive-intel-toggle"
          className="font-mono text-[10px] uppercase tracking-widest border px-2 py-1 inline-flex items-center gap-1"
          style={{ borderColor: `${TEAL}55`, color: TEAL }}
        >
          {expanded ? <><ChevronUp size={11}/> Collapse</> : <><ChevronDown size={11}/> Expand</>}
        </button>
      </div>

      {/* Summary strip */}
      {data && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4" data-testid="competitive-intel-summary">
          <SummaryCell
            testid="ci-summary-reclaim"
            label="STRATEX reclaim / yr"
            value={USD(userReclaim)}
            sub={`from a ${USD(data.user.annual_sales_usd)}/yr annualized book`}
            accent={TEAL}
          />
          <SummaryCell
            testid="ci-summary-beat"
            label="Targets you already out-reclaim"
            value={`${beats} / ${total}`}
            sub={beats > 0 ? "drop these into the call list first" : "raise the book or upgrade tier to flip more"}
            accent={beats > 0 ? TEAL : ORANGE}
          />
          <SummaryCell
            testid="ci-summary-leak"
            label="Your est. overhead leak / yr"
            value={USD(data.user.estimated_overhead_leak_usd)}
            sub={`${(data.user.blended_leak_pct * 100).toFixed(0)}% blended 5-overhead leak band`}
            accent={ORANGE}
          />
        </div>
      )}

      {loading && (
        <div className="font-mono text-[10px] uppercase tracking-widest" style={{ color: TEAL }}>
          // CALIBRATING AGAINST 7 TARGETS…
        </div>
      )}
      {err && (
        <div
          className="font-mono text-[10px] uppercase tracking-widest p-3 border"
          style={{ color: ORANGE, borderColor: ORANGE, background: `${ORANGE}10` }}
          data-testid="competitive-intel-error"
        >
          // CI ENGINE ERROR · {String(err).slice(0, 160)}
        </div>
      )}

      {expanded && data?.rows?.length > 0 && (
        <ul className="space-y-2.5" data-testid="competitive-intel-rows">
          {data.rows.map((r) => (
            <li
              key={r.id}
              data-testid={`ci-row-${r.id}`}
              className="border-l-4 bg-[#0B0F19] border-y border-r p-3 md:p-4"
              style={{
                borderLeftColor: r.user_beats_target ? TEAL : ORANGE,
                borderColor: r.user_beats_target ? `${TEAL}44` : `${ORANGE}44`,
                boxShadow: r.user_beats_target ? `0 0 12px ${TEAL}22` : "none",
              }}
            >
              <div className="flex items-start justify-between gap-3 mb-1.5 flex-wrap">
                <div className="flex items-center gap-2 min-w-0">
                  <span
                    className="font-mono text-[9.5px] uppercase tracking-widest px-2 py-0.5 border inline-flex items-center gap-1.5"
                    style={{
                      color: r.user_beats_target ? TEAL : ORANGE,
                      borderColor: r.user_beats_target ? TEAL : ORANGE,
                    }}
                  >
                    {r.user_beats_target ? <><TrendingUp size={10}/> YOU WIN</> : <><Crosshair size={10}/> CLOSE</>}
                  </span>
                  <span className="font-display text-[13px] uppercase tracking-[0.04em] text-silver truncate">
                    {r.name}
                  </span>
                </div>
                <a
                  href={`tel:${r.phone.replace(/[^0-9+]/g, "")}`}
                  data-testid={`ci-call-${r.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="font-mono text-[10px] tracking-widest inline-flex items-center gap-1 px-2 py-0.5 border"
                  style={{ color: TEAL, borderColor: `${TEAL}55` }}
                >
                  <Phone size={10}/> {r.phone}
                </a>
              </div>
              <div className="font-mono text-[11px] uppercase tracking-[0.04em] mb-1" style={{ color: r.user_beats_target ? TEAL : ORANGE }}>
                {r.headline}
              </div>
              <p className="font-body text-[12px] text-silver leading-relaxed">{r.body}</p>
              <div className="font-mono text-[9.5px] text-muted-hud mt-2 flex flex-wrap gap-x-4 gap-y-0.5">
                <span>target_rev · {USD(r.target_annual_revenue_usd)}/yr</span>
                <span>target_leak · {USD(r.target_annual_leak_usd)}/yr</span>
                <span>delta · <span style={{ color: r.user_beats_target ? TEAL : ORANGE }}>{r.delta_usd >= 0 ? "+" : ""}{USD(r.delta_usd)}/yr</span></span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function SummaryCell({ testid, label, value, sub, accent }) {
  return (
    <div
      data-testid={testid}
      className="border p-3"
      style={{ borderColor: `${accent}55`, background: `${accent}0C` }}
    >
      <div className="font-mono text-[9.5px] uppercase tracking-[0.22em]" style={{ color: accent }}>
        {label}
      </div>
      <div className="font-display text-xl mt-1 text-silver">{value}</div>
      <div className="font-mono text-[9.5px] text-muted-hud mt-1">{sub}</div>
    </div>
  );
}
