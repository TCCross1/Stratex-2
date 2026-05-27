/**
 * STRATEX™ ROI Pricing Tiers — single source of truth
 * ===================================================
 * Used by:
 *   - /onboard ROI calculator + tier picker UI
 *   - Backend /api/onboarding/stripe-checkout to create matching Stripe sessions
 *
 * AI auto-circle rule (per Executive Spec 1.4):
 *   leads_per_month <= 15   → starter
 *   16 <= leads_per_month <= 50  → growth_pro
 *   51 <= leads_per_month         → enterprise_elite
 */
export const ROI_PRICING_TIERS = [
  {
    id: "starter",
    name: "Starter",
    monthly_usd: 199,
    leads_band: "0-15 leads/mo",
    leads_min: 0,
    leads_max: 15,
    blurb: "Solo estimators + low-volume residential",
    features: [
      "1 active field estimator",
      "Up to 15 drone scans / month",
      "Standard PDF supplement reports",
      "Email delivery, 9-5 support",
    ],
  },
  {
    id: "growth_pro",
    name: "Growth Pro",
    monthly_usd: 499,
    leads_band: "16-50 leads/mo",
    leads_min: 16,
    leads_max: 50,
    blurb: "Mid-sized residential operators scaling beyond ladders",
    features: [
      "Up to 50 drone scans / month",
      "AES-256 Business Brain isolation",
      "Multi-trailer dispatch + RTK fleet",
      "Priority operator allocation",
      "Compliance audit log",
    ],
    recommended_marker: true,
  },
  {
    id: "enterprise_elite",
    name: "Enterprise Elite",
    monthly_usd: 1299,
    leads_band: "51+ leads/mo",
    leads_min: 51,
    leads_max: 100000,
    blurb: "High-volume hail/storm GAF Master Elite shops",
    features: [
      "Unlimited drone scans",
      "Dedicated success engineer",
      "Insurance adjuster coordination API",
      "SOC2 audit export",
      "24/7 critical support line",
    ],
  },
];

/** Map a monthly lead volume to the recommended tier id. */
export function recommendTier(leads_per_month) {
  if (!leads_per_month || leads_per_month < 0) return "starter";
  if (leads_per_month <= 15) return "starter";
  if (leads_per_month <= 50) return "growth_pro";
  return "enterprise_elite";
}

/**
 * Central Kentucky General Contractor Cost-Basis Matrix
 * (Per Executive Spec section 1.2 — elite Lexington-radius GC framework)
 *
 * These are the locked overhead leakage constants used by the ROI engine.
 * Treat as a frozen contract — UI labels reference them by exact name.
 */
export const CK_COST_BASIS = Object.freeze({
  outside_sales_rep_commission_pct: 0.10,
  w2_1099_blended_hourly_usd: 28.50,
  field_rep_insurance_monthly_usd: 350.0,
  vehicle_per_mile_usd: 0.655,
  avg_miles_per_inspection: 45,
  ladder_safety_premium_multiplier_pct: 0.035,
  manual_estimate_unit_cost_usd: 185.0,   // 3 man-hours + fuel + risk
  stratex_unit_cost_usd: 25.0,            // per drone deployment
  sales_rep_time_recovery_pct: 0.08,      // 8% gross margin reclaim
});

/**
 * Pure ROI calculator. Returns the full breakdown so the UI can render the
 * leakage table line-by-line. All amounts in USD.
 *
 *   Savings = (leads_per_year * 185) - (leads_per_year * 25)
 *             - (historical_sales_2_years / 2 * 0.08)   ← annualized 8% reclaim
 */
export function computeROI(input) {
  const leads_year = Math.max(0, Number(input.leads_per_year) || 0);
  const sales_2y   = Math.max(0, Number(input.historical_sales_2_years) || 0);
  const annualized_sales = sales_2y / 2;

  const manual_cost   = leads_year * CK_COST_BASIS.manual_estimate_unit_cost_usd;
  const stratex_cost  = leads_year * CK_COST_BASIS.stratex_unit_cost_usd;
  const gross_savings = manual_cost - stratex_cost;
  const sales_time_reclaim = annualized_sales * CK_COST_BASIS.sales_rep_time_recovery_pct;

  // Spec formula: Savings = (leads*185) - (leads*25) - (8% gross margin reclaim)
  // The minus sign in the formula is interpreted as "additional reclaim added back"
  // since reclaiming sales-rep time can only INCREASE savings. We surface BOTH
  // strict-formula and audited-net so the contractor sees what's happening.
  const strict_formula_savings = gross_savings - sales_time_reclaim;
  const audited_net_savings    = gross_savings + sales_time_reclaim;

  return {
    leads_year,
    annualized_sales,
    manual_cost,
    stratex_cost,
    gross_savings,
    sales_time_reclaim,
    strict_formula_savings,
    audited_net_savings,
    // Per-inspection leakage breakdown for the line-item table
    leakages_per_inspection: {
      sales_rep_commission_usd: annualized_sales > 0
        ? (annualized_sales * CK_COST_BASIS.outside_sales_rep_commission_pct) / Math.max(1, leads_year)
        : 0,
      labor_3hr_blended_usd: 3 * CK_COST_BASIS.w2_1099_blended_hourly_usd,
      vehicle_fuel_usd: CK_COST_BASIS.avg_miles_per_inspection * CK_COST_BASIS.vehicle_per_mile_usd,
      ladder_safety_uplift_usd: CK_COST_BASIS.ladder_safety_premium_multiplier_pct * 100,
    },
  };
}
