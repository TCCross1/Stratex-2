import React, { useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import {
  ROI_PRICING_TIERS,
  CK_COST_BASIS,
  computeROI,
  recommendTier,
} from "@/lib/roiPricing";
import CompetitiveIntelSection from "@/components/CompetitiveIntelSection";
import { StratexLogo } from "@/components/StratexBrand";

/**
 * /onboard — STRATEX™ ROI Onboarding & Pricing Funnel
 *
 * Captures 4 data metrics (Section 1.1), renders the elite Central Kentucky
 * Cost-Basis Matrix leakage breakdown live (Section 1.2 + 1.3), surfaces a
 * 3-tier pricing chart with an AI auto-circle ring on the recommended tier
 * (Section 1.4), enforces the Data Promise discretion clause (Section 2.1),
 * and offers two sign-up pathways (Stripe TEST checkout vs. standard access).
 */

const USD = (n) =>
  Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function OnboardingROI() {
  const navigate = useNavigate();

  // ---- Step 1.1 — 4 data metrics ----
  const [leadsWeek,    setLeadsWeek]    = useState(8);
  const [leadsMonth,   setLeadsMonth]   = useState(35);
  const [leadsYear,    setLeadsYear]    = useState(420);
  const [historical2y, setHistorical2y] = useState(1_400_000);

  // ---- Step 1.2 — Account placeholders for sign-up step ----
  const [email,    setEmail]    = useState("");
  const [password, setPassword] = useState("");
  const [company,  setCompany]  = useState("");
  const [busy,     setBusy]     = useState(false);
  const [error,    setError]    = useState(null);

  const recommended_id = recommendTier(Number(leadsMonth));
  const [selectedTier, setSelectedTier] = useState(recommended_id);
  // Keep selectedTier in sync if user revises leads_per_month and they were on the auto-circle
  React.useEffect(() => { setSelectedTier(recommended_id); }, [recommended_id]);

  const roi = useMemo(
    () => computeROI({
      leads_per_year: leadsYear,
      historical_sales_2_years: historical2y,
    }),
    [leadsYear, historical2y],
  );

  // ---- Sign-up handlers ----
  async function handleStandardAccess(e) {
    e?.preventDefault?.();
    setBusy(true); setError(null);
    try {
      const payload = {
        email, password, company,
        role: "contractor",
        onboarding_metrics: {
          leads_per_week: Number(leadsWeek),
          leads_per_month: Number(leadsMonth),
          leads_per_year: Number(leadsYear),
          historical_sales_2_years: Number(historical2y),
        },
        selected_tier: selectedTier,
        capex_upgrade: false,
      };
      const r = await api.post("/onboarding/signup", payload);
      // Persist token + bounce to contractor portal
      localStorage.setItem("stratex_token", r.data.access_token);
      navigate("/contractor");
    } catch (err) {
      setError(err?.response?.data?.detail || "Signup failed. Please review your inputs.");
    } finally { setBusy(false); }
  }

  async function handleCapExActivation(e) {
    e?.preventDefault?.();
    setBusy(true); setError(null);
    try {
      // Create the account first (capex_upgrade=true marks intent)
      const r = await api.post("/onboarding/signup", {
        email, password, company,
        role: "contractor",
        onboarding_metrics: {
          leads_per_week: Number(leadsWeek),
          leads_per_month: Number(leadsMonth),
          leads_per_year: Number(leadsYear),
          historical_sales_2_years: Number(historical2y),
        },
        selected_tier: selectedTier,
        capex_upgrade: true,
      });
      localStorage.setItem("stratex_token", r.data.access_token);
      // Kick a Stripe TEST checkout session for the selected ROI tier
      const co = await api.post("/onboarding/stripe-checkout", {
        tier: selectedTier,
        origin_url: window.location.origin,
      });
      if (co.data?.url) {
        window.location.href = co.data.url;
      } else {
        navigate("/contractor");
      }
    } catch (err) {
      setError(err?.response?.data?.detail || "Upgrade flow failed. Please try again.");
    } finally { setBusy(false); }
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="onboard-root">
      <div className="max-w-[1400px] mx-auto">
        {/* ============== HEADER ============== */}
        <StratexLogo height={40} className="mb-5"/>
        <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-2">
          // VISION • CONTRACTOR ONBOARDING • ROI MATRIX
        </div>
        <h1 className="font-display text-3xl md:text-5xl uppercase tracking-widest text-silver mb-3">
          Quantify Your Ladder-Free ROI
        </h1>
        <p className="text-sm md:text-base text-muted-hud font-body mb-10 max-w-3xl">
          The elite Central Kentucky cost framework computes your roof-inspection overhead leakage live. Adjust the
          four metrics below — STRATEX™ instantly maps the savings, gates the right tier, and gets you to drone
          deployment in under 60 seconds.
        </p>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* ============== LEFT: 4 DATA METRICS ============== */}
          <div className="border border-[#00F0FF]/30 bg-[#0B0F19] p-5">
            <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-4">// SECTION 1.1 — DATA CAPTURE</div>
            <Field label="Leads per Week"            value={leadsWeek}    onChange={setLeadsWeek}    testid="onb-leads-week"  unit="leads/wk" />
            <Field label="Leads per Month"           value={leadsMonth}   onChange={setLeadsMonth}   testid="onb-leads-month" unit="leads/mo" />
            <Field label="Leads per Year"            value={leadsYear}    onChange={setLeadsYear}    testid="onb-leads-year"  unit="leads/yr" />
            <Field label="Historical Sales — 2 yr"   value={historical2y} onChange={setHistorical2y} testid="onb-sales-2y"    unit="USD" step={50000} />

            {/* Discretion Clause — Section 2.1 */}
            <div className="mt-6 p-4 border border-[#00F5D4]/40 bg-[#00F5D4]/[0.04]" data-testid="discretion-clause">
              <div className="flex items-start gap-2">
                <span className="text-teal font-mono text-base leading-none">🛡️</span>
                <div>
                  <div className="font-mono text-[10px] tracking-widest uppercase text-teal mb-1">STRATEX DATA PROMISE</div>
                  <p className="font-body text-[11.5px] leading-snug text-silver">
                    Your pricing structures, labor rates, overhead settings, material costs, and final client estimations are
                    <strong className="text-teal"> exclusively yours</strong>. Once the drone passes imagery to the BEES pipeline,
                    estimations are processed locally and securely encrypted. No STRATEX corporate representative, admin user,
                    or outside third-party can access your financials or your final client quotes.
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* ============== MIDDLE: ROI LEAKAGE MATRIX ============== */}
          <div className="border border-[#00F0FF]/30 bg-[#0B0F19] p-5" data-testid="roi-matrix">
            <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-4">// SECTION 1.2 — LEAKAGE MATRIX (CK GC FRAMEWORK)</div>

            <LeakageRow label="Outside Sales Rep Commissions"    detail="10% of gross contract value" value={`${(CK_COST_BASIS.outside_sales_rep_commission_pct*100).toFixed(0)}%`} />
            <LeakageRow label="W2/1099 Blended Labor"            detail="Per-hour field cost"         value={`$${CK_COST_BASIS.w2_1099_blended_hourly_usd.toFixed(2)}/hr`} />
            <LeakageRow label="Field Rep Insurance / Liability"  detail="Per active field estimator"  value={`$${CK_COST_BASIS.field_rep_insurance_monthly_usd.toFixed(0)}/mo`} />
            <LeakageRow label="Vehicle Wear + Fuel"               detail={`${CK_COST_BASIS.avg_miles_per_inspection} mi avg · IRS rate`} value={`$${CK_COST_BASIS.vehicle_per_mile_usd}/mi`} />
            <LeakageRow label="Ladder Safety Premium Uplift"     detail="Of GL package"               value={`${(CK_COST_BASIS.ladder_safety_premium_multiplier_pct*100).toFixed(1)}%`} />

            <div className="h-px bg-[#00F0FF]/20 my-4"/>

            <div className="grid grid-cols-2 gap-3 text-[11px] font-mono">
              <Stat label="Manual Est. / Roof"   value={USD(CK_COST_BASIS.manual_estimate_unit_cost_usd)} />
              <Stat label="STRATEX Est. / Roof"  value={USD(CK_COST_BASIS.stratex_unit_cost_usd)} color="#00F5D4" />
              <Stat label="Manual Annual Cost"   value={USD(roi.manual_cost)} />
              <Stat label="STRATEX Annual Cost"  value={USD(roi.stratex_cost)} color="#00F5D4" />
            </div>

            <div className="h-px bg-[#00F0FF]/20 my-4"/>

            <div className="p-3 border border-[#00F5D4]/40 bg-[#00F5D4]/[0.06]" data-testid="net-savings-card">
              <div className="font-mono text-[9px] tracking-widest uppercase text-muted-hud">// NET ANNUAL SAVINGS</div>
              <div className="font-display text-3xl md:text-4xl text-teal tracking-wider mt-1" style={{textShadow:"0 0 14px #00F5D4"}}>
                {USD(roi.audited_net_savings)}
              </div>
              <div className="font-mono text-[10px] text-muted-hud mt-1">
                Gross savings <span className="text-silver">{USD(roi.gross_savings)}</span> + Sales-rep time reclaim{" "}
                <span className="text-silver">{USD(roi.sales_time_reclaim)}</span>
              </div>
            </div>
          </div>

          {/* ============== RIGHT: PRICING TIERS ============== */}
          <div className="border border-[#00F0FF]/30 bg-[#0B0F19] p-5" data-testid="tier-picker">
            <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-1">// SECTION 1.4 — TIER MATRIX</div>
            <div className="font-mono text-[10px] text-muted-hud uppercase tracking-wider mb-4">
              AI Auto-Circle ⟶ <span className="text-teal" data-testid="recommended-tier">{recommended_id.replace("_"," ").toUpperCase()}</span>
            </div>

            <div className="space-y-3">
              {ROI_PRICING_TIERS.map((t) => {
                const isRecommended = t.id === recommended_id;
                const isSelected    = t.id === selectedTier;
                return (
                  <button
                    key={t.id}
                    data-testid={`tier-${t.id}`}
                    aria-pressed={isSelected}
                    onClick={() => setSelectedTier(t.id)}
                    className="w-full text-left p-4 border transition-all relative"
                    style={{
                      borderColor: isSelected ? "#00F5D4" : "rgba(0,240,255,0.25)",
                      background: isSelected ? "rgba(0,245,212,0.06)" : "rgba(11,15,25,0.6)",
                      boxShadow: isSelected ? "0 0 20px rgba(0,245,212,0.25), inset 0 0 8px rgba(0,245,212,0.18)" : "none",
                    }}
                  >
                    {isRecommended && (
                      <div
                        className="absolute -top-2 -right-2 px-2 py-0.5 font-mono text-[9px] tracking-widest uppercase"
                        style={{
                          background:"#00F5D4", color:"#0B0F19",
                          boxShadow:"0 0 14px #00F5D4", borderRadius:"2px",
                        }}
                        data-testid="auto-circle-ring"
                      >
                        AI RECOMMENDED
                      </div>
                    )}
                    <div className="font-display text-base uppercase tracking-wider text-silver">{t.name}</div>
                    <div className="font-mono text-[10px] text-muted-hud uppercase tracking-wider mt-0.5">{t.leads_band}</div>
                    <div className="font-display text-2xl mt-2 text-teal">
                      ${t.monthly_usd}<span className="text-[11px] text-muted-hud">/mo</span>
                    </div>
                    <div className="text-[11px] text-silver mt-1">{t.blurb}</div>
                    <ul className="mt-2 space-y-0.5 text-[10.5px] text-muted-hud font-mono">
                      {t.features.map((f, i) => <li key={i}>• {f}</li>)}
                    </ul>
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* ============== ACCOUNT + SIGN-UP UX INTERCEPT ============== */}
        <div className="mt-10 border border-[#00F0FF]/30 bg-[#0B0F19] p-6" data-testid="signup-intercept">
          <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-4">// SECTION 1.5 — ACTIVATION GATEWAY</div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-5">
            <Field plain label="Work Email"  value={email}    onChange={setEmail}    testid="onb-email"    type="email"    />
            <Field plain label="Password"    value={password} onChange={setPassword} testid="onb-password" type="password" />
            <Field plain label="Company"     value={company}  onChange={setCompany}  testid="onb-company"  type="text"     />
          </div>

          {error && (
            <div className="mb-4 p-3 border border-[#FF5400] bg-[#FF5400]/10 text-[#FF5400] font-mono text-[11px]" data-testid="signup-error">
              ⚠️ {error}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              data-testid="capex-activation-btn"
              disabled={busy || !email || !password}
              onClick={handleCapExActivation}
              className="px-5 py-4 font-display uppercase tracking-widest text-base border transition-all disabled:opacity-50"
              style={{
                background:"linear-gradient(135deg, rgba(0,245,212,0.18), rgba(0,245,212,0.04))",
                borderColor:"#00F5D4", color:"#00F5D4",
                boxShadow:"0 0 22px rgba(0,245,212,0.35), inset 0 0 10px rgba(0,245,212,0.18)",
                textShadow:"0 0 8px #00F5D4",
              }}
            >
              ⚡ Upgraded CapEx Activation — ${ROI_PRICING_TIERS.find((t) => t.id === selectedTier)?.monthly_usd}/mo
            </button>

            <button
              data-testid="standard-access-btn"
              disabled={busy || !email || !password}
              onClick={handleStandardAccess}
              className="px-5 py-4 font-mono uppercase tracking-widest text-xs border transition-all disabled:opacity-50"
              style={{
                background:"rgba(11,15,25,0.85)",
                borderColor:"rgba(0,240,255,0.4)",
                color:"#94A3B8",
              }}
            >
              Commit Later · Standard Access
              <div className="font-body normal-case tracking-normal text-[10px] text-muted-hud mt-1">
                Profile only · 3D viewports locked · Asset Locked: Membership Upgrade Required
              </div>
            </button>
          </div>

          <p className="mt-4 font-mono text-[10px] tracking-wider text-muted-hud uppercase">
            • Stripe TEST mode active — no real charges in this environment
            • All financials AES-256 isolated · admin profiles return {"{}"} on financial reads
          </p>
        </div>

        <CompetitiveIntelSection historicalSales2y={historical2y} leadsPerMonth={leadsMonth}/>
      </div>
    </div>
  );
}

// ============= helper sub-components =============
function Field({ label, value, onChange, testid, unit, type = "number", step = 1, plain = false }) {
  return (
    <label className={plain ? "block" : "block mb-3"} data-testid={`${testid}-label`}>
      <span className="font-mono text-[10px] tracking-widest uppercase text-muted-hud block mb-1">{label}</span>
      <div className="flex items-center border border-[#00F0FF]/25 bg-[#0B0F19]">
        <input
          type={type}
          step={step}
          value={value}
          onChange={(e) => onChange(type === "number" ? Number(e.target.value) : e.target.value)}
          className="flex-1 bg-transparent px-3 py-2 font-mono text-sm text-silver outline-none focus:border-teal"
          data-testid={testid}
        />
        {unit && <span className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-teal border-l border-[#00F0FF]/25">{unit}</span>}
      </div>
    </label>
  );
}

function LeakageRow({ label, detail, value }) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b border-[#00F0FF]/10">
      <div>
        <div className="font-body text-[12px] text-silver">{label}</div>
        <div className="font-mono text-[9.5px] text-muted-hud uppercase tracking-wider">{detail}</div>
      </div>
      <div className="font-mono text-[12px] text-teal">{value}</div>
    </div>
  );
}

function Stat({ label, value, color = "#E2E8F0" }) {
  return (
    <div className="border border-[#00F0FF]/20 p-2">
      <div className="font-mono text-[9px] tracking-widest uppercase text-muted-hud">{label}</div>
      <div className="font-display text-base" style={{ color }}>{value}</div>
    </div>
  );
}
