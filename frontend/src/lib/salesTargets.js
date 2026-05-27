/**
 * STRATEX™ Admin Sales Hub — Pre-Cached Sales Targets
 * ====================================================
 * Central Kentucky footprint, per Executive Spec Section 4.
 * Coordinates are best-public-record approximations sourced for the Leaflet
 * pin layer (Lexington metro 38.04°N, -84.50°W ± ~0.15°). Status defaults to
 * "uncontacted" so the CRM pipeline starts cleanly.
 */
export const KY_SALES_TARGETS = [
  {
    id: "ale-roofing",
    name: "ALE Roofing LLC",
    aka: "Formerly Atlas Contracting / Elleman Contracting",
    base: "Lexington, KY",
    phone: "859-402-5211",
    focus: "Historic Preservation, Slate, Copper, Custom Internal Box Gutters, Residential/Commercial Replacements",
    lat: 38.0406, lng: -84.5037,
    status: "uncontacted",
  },
  {
    id: "burnett-roofing",
    name: "Burnett Roofing",
    base: "656 Bizzell Drive, Lexington, KY 40510",
    phone: "859-253-0116",
    focus: "Tier 1 Commercial Manufacturing, Single-Ply Membranes (EPDM/TPO/PVC), Modified Bitumen, Architectural Sheet Metal",
    lat: 38.0739, lng: -84.5494,
    status: "uncontacted",
  },
  {
    id: "centimark",
    name: "CentiMark Corporation",
    base: "260 Crossfield Dr, Unit 4, Versailles, KY 40383",
    phone: "502-716-5777",
    focus: "Large-Scale Industrial, Thermal Shock Inspections, Commercial Property Maintenance Assets",
    lat: 38.0530, lng: -84.7286,
    status: "uncontacted",
  },
  {
    id: "big-league",
    name: "Big League Roofers",
    base: "3022 Lexington Road, Nicholasville, KY 40356 · 2901 Richmond Road, Lexington, KY 40509",
    phone: "859-693-7663",
    focus: "High-Volume GAF Master Elite Residential, Hail/Storm Insurance Adjuster Coordination",
    lat: 37.8806, lng: -84.5728,
    status: "uncontacted",
  },
  {
    id: "godsend",
    name: "A Godsend Roofing LLC",
    base: "380 E Main St, Lexington, KY 40507",
    phone: "859-432-7663",
    focus: "Commercial/Residential Master Applicators, Complex Custom Step Flashing, Storm Repair Logistics",
    lat: 38.0457, lng: -84.4906,
    status: "uncontacted",
  },
  {
    id: "odessa",
    name: "Odessa Roofing, Inc.",
    base: "232 Gold Rush Road, Suite 110, Lexington, KY 40503",
    phone: "859-271-0524",
    focus: "KRCA/NRCA Members, Custom Copper Flashing, Synthetic Slate, High-End Residential Architecture",
    lat: 38.0019, lng: -84.5310,
    status: "uncontacted",
  },
  {
    id: "barrier",
    name: "Barrier Roofs",
    base: "Lexington, KY",
    phone: "859-251-5119",
    focus: "High-Volume Owens Corning Platinum Dealer, Insurance Claims Supplementing",
    lat: 38.0406, lng: -84.5037,
    status: "uncontacted",
  },
];

export const SALES_STATUS_OPTIONS = ["uncontacted", "contacted", "demoed", "negotiating", "closed-won", "closed-lost"];
export const SALES_STATUS_COLORS = {
  "uncontacted":   "#94A3B8",
  "contacted":     "#4CC3FF",
  "demoed":        "#00F5D4",
  "negotiating":   "#FFB400",
  "closed-won":    "#22D3EE",
  "closed-lost":   "#FF5400",
};
