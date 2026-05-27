/**
 * STRATEX™ Materials Expert Database
 * ===================================
 * Master roofing GC taxonomy per Executive Spec 3.1 (expanded).
 * Frozen — UI consumers MUST NOT mutate; the configurator only stores
 * SELECTED references by id back to the user's encrypted profile.
 */
export const MATERIALS_DATABASE = Object.freeze({
  asphalt_shingle_system: {
    label: "Asphalt Shingle System",
    manufacturers: [
      {
        name: "GAF",
        lines: [
          { name: "Timberline HDZ (Architectural)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Timberline UHDZ (Premium Laminated)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Royal Sovereign (Traditional 3-Tab)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Camelot II (Luxury/Designer)", bundle_coverage_sq_ft: 25.0, bundles_per_square: 4 },
        ],
        color_catalog: ["Charcoal","Pewter Gray","Barkwood","Weathered Wood","Hunter Green","Mission Brown","Slate","Oyster Shell"],
      },
      {
        name: "Owens Corning",
        lines: [
          { name: "Duration (Architectural w/ SureNail)", bundle_coverage_sq_ft: 32.8, bundles_per_square: 3 },
          { name: "Duration Designer", bundle_coverage_sq_ft: 32.8, bundles_per_square: 3 },
          { name: "Supreme (3-Tab)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Berkshire (Luxury)", bundle_coverage_sq_ft: 25.0, bundles_per_square: 4 },
        ],
        color_catalog: ["Onyx Black","Estate Gray","Driftwood","Teak","Brownwood","Chateau Green","Desert Tan","Sand Dune"],
      },
      {
        name: "CertainTeed",
        lines: [
          { name: "Landmark (Dual-Layer Architectural)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Landmark Pro", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Grand Manor (Luxury Slate-Mimic)", bundle_coverage_sq_ft: 20.0, bundles_per_square: 5 },
          { name: "XT 25 (Heavy-Duty 3-Tab)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
        ],
        color_catalog: ["Moire Black","Colonial Slate","Weathered Wood","Burnt Sienna","Resawn Shake","Cobblestone Gray","Atlantic Blue"],
      },
      {
        name: "Tamko",
        lines: [
          { name: "Heritage (Architectural)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Titan XT (Premium High-Wind)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
          { name: "Elite Glass-Seal (3-Tab)", bundle_coverage_sq_ft: 33.3, bundles_per_square: 3 },
        ],
        color_catalog: ["Thunderstorm Grey","Rustic Black","Virginia Slate","Weathered Wood","Harvest Gold","Desert Pale"],
      },
    ],
    starter_strip_options: [
      { name: "GAF Pro-Start Starter Strip Shingles", linear_ft_per_bundle: 120.3 },
      { name: "Owens Corning Starter Shingle Roll", linear_ft_per_bundle: 105.0 },
      { name: "CertainTeed Swiftstart Starter Shingles", linear_ft_per_bundle: 116.0 },
      { name: "Universal Field-Cut 3-Tab Starter Method", linear_ft_per_bundle: 100.0 },
    ],
    hip_and_ridge_caps: [
      { name: "GAF Seal-A-Ridge Standard Caps", linear_ft_per_box: 25.0 },
      { name: "GAF Timbertex Premium Distinctive Ridge Caps", linear_ft_per_box: 20.0 },
      { name: "Owens Corning DecoRidge High-Profile Caps", linear_ft_per_box: 30.0 },
      { name: "CertainTeed Shadow Ridge Cedar-Shake Look", linear_ft_per_box: 30.0 },
      { name: "Field-Cut Shingle Tab Cap Method", linear_ft_per_box: 35.0 },
    ],
    underlayment_options: {
      traditional_felt: [
        { style: "15-Pound Asphalt Saturated Felt Paper", roll_coverage_sq_ft: 432.0, weight_lbs: 60 },
        { style: "30-Pound Heavy-Duty Saturated Felt Paper", roll_coverage_sq_ft: 216.0, weight_lbs: 60 },
      ],
      synthetic_felt: [
        { style: "GAF FeltBuster Synthetic Polypropylene", roll_coverage_sq_ft: 1000.0 },
        { style: "Owens Corning ProArmor Synthetic Premium", roll_coverage_sq_ft: 1000.0 },
        { style: "CertainTeed DiamondDeck High-Performance Synthetic", roll_coverage_sq_ft: 1000.0 },
        { style: "Tiger Paw Breathable Woven Synthetic Underlayment", roll_coverage_sq_ft: 1000.0 },
      ],
      ice_and_water_shield: [
        { style: "Grace Ice & Water Shield (Original Rubberized Asphalt)", roll_coverage_sq_ft: 225.0, mil_thickness: 40 },
        { style: "GAF WeatherWatch Granular-Surfaced Leak Barrier", roll_coverage_sq_ft: 200.0, mil_thickness: 45 },
        { style: "Owens Corning WeatherLock G Granular", roll_coverage_sq_ft: 200.0, mil_thickness: 50 },
        { style: "CertainTeed WinterGuard Sand-Surfaced Leak Barrier", roll_coverage_sq_ft: 200.0, mil_thickness: 60 },
      ],
    },
    edge_metal_and_drip_options: {
      styles: [
        { type: "F4.5 Overhanging Drip Edge", length_per_piece_ft: 10.0 },
        { type: "F5 Premium Extended Drip Edge", length_per_piece_ft: 10.0 },
        { type: "D-Style Deluxe Gutter-Direct Edge Metal", length_per_piece_ft: 10.0 },
        { type: "Standard L-Type Rake Metal Edge", length_per_piece_ft: 10.0 },
      ],
      materials: ["Aluminum (0.024 gauge)","Aluminum (0.032 heavy gauge)","Galvanized Steel (26 gauge)","Galvanized Steel (24 heavy gauge)","Solid Copper (16 oz)"],
      color_catalog: ["White","Black","Royal Brown","Commercial Bronze","Clay","Sandstone","Charcoal Gray","Mill Finish (Unpainted)"],
    },
    flashing_infrastructure: {
      step_flashing: [
        { size: "5x7 Pre-Bent Aluminum", gauge: "0.019", pack_count: 100 },
        { size: "5x7 Pre-Bent Galvanized Steel", gauge: "26", pack_count: 100 },
        { size: "5x7 Pre-Bent Heavy Copper", weight: "16 oz", pack_count: 50 },
        { size: "4x4x8 Custom-Bent Step Profiles", gauge: "24", pack_count: 100 },
      ],
      wall_and_counter_flashing: [
        { type: "Tern Metal Flashing Roll", dimensions: "10 inch x 50 ft" },
        { type: "Galvanized Steel Pre-Cut Apron Flashing Roll", dimensions: "14 inch x 50 ft" },
        { type: "Aluminum Coil Stock For Custom Brake Profiles", dimensions: "24 inch x 50 ft" },
      ],
      penetration_boots: [
        { type: "Oatey Master Flash Neoprene Pipe Boot Flange", pipe_size_range: "1.25 to 3.0 inches" },
        { type: "Oatey Master Flash Neoprene Pipe Boot Flange", pipe_size_range: "3.0 to 4.0 inches" },
        { type: "Heavy-Duty Ultimate Lead Pipe Boot Shield", pipe_size_range: "3.0 inches" },
        { type: "Heavy-Duty Ultimate Lead Pipe Boot Shield", pipe_size_range: "4.0 inches" },
      ],
    },
    fastener_matrix: [
      { type: "Coil Roofing Nails - 1 1/4 inch", delivery_method: "Pneumatic Gun", finish: "Electro-Galvanized Smooth Shank", box_quantity: 7200 },
      { type: "Coil Roofing Nails - 1 1/2 inch", delivery_method: "Pneumatic Gun", finish: "Electro-Galvanized Smooth Shank", box_quantity: 7200 },
      { type: "Coil Roofing Nails - 1 3/4 inch", delivery_method: "Pneumatic Gun", finish: "Electro-Galvanized Ring Shank", box_quantity: 7200 },
      { type: "Hand Drive Nails - 1 1/4 inch", delivery_method: "Manual Hammer", finish: "Hot-Dipped Galvanized Smooth Shank", box_quantity: 2500 },
      { type: "Hand Drive Nails - 1 1/2 inch", delivery_method: "Manual Hammer", finish: "Hot-Dipped Galvanized Ring Shank", box_quantity: 2500 },
    ],
  },

  metal_standing_seam_system: {
    label: "Metal Standing-Seam System",
    manufacturers: [
      { name: "McElroy Metal", series: ["Maxima Structural Seam","Medallion-Lok Architectural","Meridian Snap-Lock"] },
      { name: "Pac-Clad (Petersen Aluminum)", series: ["Snap-Clad Panel","Tite-Lok Mechanical Seam","PAC-150"] },
      { name: "Sheffield Metals", series: ["SMI 1.5-inch Mechanical","SMI 1.75-inch Snap-Lock","SMI 1.0-inch Integral Fastener Strip"] },
    ],
    seam_profiles: [
      { name: "1.5-inch Mechanical Lock (Single or Double Fold)", minimum_slope: "0.5:12" },
      { name: "1.75-inch Architectural Snap-Lock", minimum_slope: "2:12" },
      { name: "1.0-inch Fastener Strip / Nail Strip Profile", minimum_slope: "3:12" },
    ],
    metal_substrates: [
      { type: "Galvalume Steel (24 gauge AZ50)", finish: "70% Kynar 500 / PVDF Coating" },
      { type: "Galvalume Steel (22 gauge heavy-duty)", finish: "70% Kynar 500 / PVDF Coating" },
      { type: "Architectural Aluminum (0.032 gauge)", finish: "70% Kynar 500 Coating" },
      { type: "Architectural Aluminum (0.040 ultra-heavy)", finish: "70% Kynar 500 Coating" },
      { type: "Solid Structural Copper (16 oz cold-rolled)", finish: "Natural Bright (Mill Patina)" },
      { type: "Solid Structural Copper (20 oz heavy-rolled)", finish: "Natural Bright (Mill Patina)" },
    ],
    fasteners_and_anchors: [
      { type: "Concealed Fixed Clip Floating Anchor Screws #10-12 x 1-inch", finish: "Pancake Head Carbon Steel RyShield" },
      { type: "Concealed Slider Clip Expansion Anchor Screws #10 x 1.25-inch", finish: "Pancake Head Stainless Steel 304" },
      { type: "Exposed EPDM Neo-Washer Wood Screws #9 x 1.5-inch (Eaves/Valleys)", finish: "PVDF Color-Matched Powder Coat", box_quantity: 250 },
      { type: "Exposed EPDM Neo-Washer Stitch Screws #14 x 7/8-inch (Metal-to-Metal)", finish: "PVDF Color-Matched Powder Coat", box_quantity: 250 },
    ],
    sealants_and_closures: [
      { type: "Continuous Butyl Flange Sealant Tape", dimensions: "3/8 inch x 3/32 inch x 45 ft" },
      { type: "NovaFlex Metal Roof Ultra-Polymer Liquid Sealant Tube", colors: ["Clear","Gray","Black","Bronze","White"] },
      { type: "Eave/Ridge Inside and Outside Formed Foam Closure Strips", profile_match: "Vendor-Specific Panel Geometry" },
    ],
    color_catalog: ["Slate Gray","Matte Black","Charcoal","Dark Bronze","Medium Bronze","Classic Green","Colonial Red","Copper Penny (Metallic)"],
  },

  slate_premium_system: {
    label: "Slate Premium System",
    manufacturers: [
      { name: "Vermont Structural Slate Company", quarry_origins: ["Vermont Unfading Green","Vermont Unfading Mottled Purple","Vermont Unfading Black"] },
      { name: "Glendyne Quarry", quarry_origins: ["Glendyne Canadian Unfading Dark Grey Metallic Splendour"] },
    ],
    thickness_grading: [
      { grade: "3/16 inch Standard Architectural Slate", average_weight_per_square_lbs: 800 },
      { grade: "1/4 inch Medium Structural Slate", average_weight_per_square_lbs: 1000 },
      { grade: "3/8 inch Heavy-Duty Estate Slate", average_weight_per_square_lbs: 1400 },
      { grade: "1/2 inch Ultra-Heavy Graduated Monumental Slate", average_weight_per_square_lbs: 1800 },
    ],
    fasteners: [
      { type: "Solid Copper Slate Roof Nails - 1 1/2 inch", wire_gauge: "10 gauge smooth shank", box_weight_lbs: 50 },
      { type: "Solid Copper Slate Roof Nails - 1 3/4 inch", wire_gauge: "10 gauge smooth shank", box_weight_lbs: 50 },
      { type: "Solid Copper Slate Roof Nails - 2.00 inch", wire_gauge: "11 gauge ring shank heavy structural", box_weight_lbs: 50 },
      { type: "Stainless Steel Type 316 Heavy Slate Hooks - 3-inch length", wire_gauge: "12 gauge structural spring wire" },
    ],
  },

  custom_fallback_infrastructure: {
    label: "Other / Proprietary Specialty Specification",
    type: "Other / Proprietary Specialty Specification",
    display_input_field: true,
    comment_line_placeholder: "Specify custom material classifications, unique gauges, structural profiles, proprietary fastener patterns, and specialized underlayments here...",
  },
});

/** Lightweight quantity-takeoff math used by the configurator preview pane. */
export function takeoffBundlesFromArea({ total_sq_ft, bundle_coverage_sq_ft, waste_factor_pct = 12 }) {
  if (!total_sq_ft || !bundle_coverage_sq_ft) return 0;
  const w = 1 + (waste_factor_pct / 100);
  return Math.ceil((total_sq_ft * w) / bundle_coverage_sq_ft);
}

export function takeoffRollsFromArea({ total_sq_ft, roll_coverage_sq_ft, waste_factor_pct = 10 }) {
  if (!total_sq_ft || !roll_coverage_sq_ft) return 0;
  const w = 1 + (waste_factor_pct / 100);
  return Math.ceil((total_sq_ft * w) / roll_coverage_sq_ft);
}

export function takeoffEdgePiecesFromLinear({ total_linear_ft, length_per_piece_ft, waste_factor_pct = 8 }) {
  if (!total_linear_ft || !length_per_piece_ft) return 0;
  const w = 1 + (waste_factor_pct / 100);
  return Math.ceil((total_linear_ft * w) / length_per_piece_ft);
}
