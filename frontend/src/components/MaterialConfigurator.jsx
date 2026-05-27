import React, { useMemo, useState } from "react";
import {
  MATERIALS_DATABASE,
  takeoffBundlesFromArea,
  takeoffRollsFromArea,
  takeoffEdgePiecesFromLinear,
} from "@/lib/materialsDatabase";

/**
 * <MaterialConfigurator /> — Interactive Multi-Tier Material Picker
 *
 * Per Executive Spec 3.1: a fully conditional dropdown structure where the
 * parent system (asphalt / metal / slate / custom) dynamically swaps the
 * child manufacturer / line / underlayment / flashing / fastener panels.
 *
 * Selection state is reported upward via the `onChange(selection)` callback
 * so the parent screen (ContractorPortal Business Brain or onboard preview)
 * can persist it through the encrypted /api/contractor/materials-config endpoint.
 *
 * Optional `takeoff_inputs` (total_sq_ft, total_linear_ft) renders a live
 * quantity-takeoff panel using the bundles/rolls/edge math from materialsDatabase.
 */
export default function MaterialConfigurator({
  initialSelection = null,
  onChange = () => {},
  takeoff_inputs = null,
}) {
  const [system, setSystem]    = useState(initialSelection?.system || "asphalt_shingle_system");
  const [picks, setPicks]      = useState(initialSelection?.picks || {});
  const [customText, setText]  = useState(initialSelection?.custom_text || "");

  function setPick(key, val) {
    const next = { ...picks, [key]: val };
    setPicks(next);
    onChange({ system, picks: next, custom_text: customText });
  }

  React.useEffect(() => {
    onChange({ system, picks, custom_text: customText });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [system, customText]);

  const SYSTEMS = [
    { id: "asphalt_shingle_system",   label: "Asphalt Shingle System", color: "#4CC3FF" },
    { id: "metal_standing_seam_system", label: "Metal Standing-Seam",   color: "#5FF4FF" },
    { id: "slate_premium_system",     label: "Slate Premium",          color: "#D99DFF" },
    { id: "custom_fallback_infrastructure", label: "Other / Custom",   color: "#FF8A1F" },
  ];

  const ActiveSystem = MATERIALS_DATABASE[system];

  return (
    <div className="border border-[#00F0FF]/30 bg-[#0B0F19] p-5" data-testid="material-configurator">
      <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-4">// MATERIAL EXPERT CONFIGURATOR</div>

      {/* ============== PARENT SYSTEM SELECTOR ============== */}
      <div className="flex flex-wrap gap-2 mb-5" data-testid="system-selector">
        {SYSTEMS.map((s) => {
          const active = s.id === system;
          return (
            <button
              key={s.id}
              data-testid={`system-${s.id}`}
              aria-pressed={active}
              onClick={() => { setSystem(s.id); setPicks({}); }}
              className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
              style={{
                background: active ? `${s.color}22` : "rgba(11,15,25,0.85)",
                color: active ? s.color : "#94A3B8",
                borderColor: active ? s.color : "rgba(0,240,255,0.25)",
                boxShadow: active ? `0 0 10px ${s.color}66` : "none",
              }}
            >
              {s.label}
            </button>
          );
        })}
      </div>

      {/* ============== ASPHALT BRANCH ============== */}
      {system === "asphalt_shingle_system" && (
        <AsphaltBranch sys={ActiveSystem} picks={picks} setPick={setPick} takeoff_inputs={takeoff_inputs} />
      )}

      {/* ============== METAL BRANCH ============== */}
      {system === "metal_standing_seam_system" && (
        <MetalBranch sys={ActiveSystem} picks={picks} setPick={setPick} />
      )}

      {/* ============== SLATE BRANCH ============== */}
      {system === "slate_premium_system" && (
        <SlateBranch sys={ActiveSystem} picks={picks} setPick={setPick} />
      )}

      {/* ============== CUSTOM BRANCH ============== */}
      {system === "custom_fallback_infrastructure" && (
        <div data-testid="custom-branch">
          <label className="block">
            <span className="font-mono text-[10px] tracking-widest uppercase text-muted-hud block mb-1">
              Custom Specification
            </span>
            <textarea
              data-testid="custom-spec-input"
              value={customText}
              onChange={(e) => setText(e.target.value)}
              placeholder={ActiveSystem.comment_line_placeholder}
              rows={6}
              className="w-full bg-[#0B0F19] border border-[#00F0FF]/25 px-3 py-2 font-mono text-xs text-silver outline-none focus:border-teal"
            />
          </label>
        </div>
      )}
    </div>
  );
}

// ===========================================================================
// ASPHALT BRANCH — manufacturer → line → color → starter → ridge → underlayment
// → drip edge → flashing → fasteners + LIVE QUANTITY TAKEOFF
// ===========================================================================
function AsphaltBranch({ sys, picks, setPick, takeoff_inputs }) {
  const manufacturer = sys.manufacturers.find((m) => m.name === picks.manufacturer) || null;
  const line         = manufacturer?.lines.find((l) => l.name === picks.line) || null;

  // Live takeoff math (only when inputs + line are present)
  const takeoff = useMemo(() => {
    if (!takeoff_inputs || !line) return null;
    const total_sq_ft     = Number(takeoff_inputs.total_sq_ft || 0);
    const total_linear_ft = Number(takeoff_inputs.total_linear_ft || 0);

    const bundles = takeoffBundlesFromArea({
      total_sq_ft,
      bundle_coverage_sq_ft: line.bundle_coverage_sq_ft,
    });

    const underlayment = sys.underlayment_options.synthetic_felt.find((u) => u.style === picks.underlayment) ||
                         sys.underlayment_options.traditional_felt.find((u) => u.style === picks.underlayment) ||
                         sys.underlayment_options.ice_and_water_shield.find((u) => u.style === picks.underlayment);
    const underlayment_rolls = underlayment
      ? takeoffRollsFromArea({ total_sq_ft, roll_coverage_sq_ft: underlayment.roll_coverage_sq_ft })
      : 0;

    const dripEdge = sys.edge_metal_and_drip_options.styles.find((s) => s.type === picks.drip_edge_style);
    const drip_pieces = dripEdge
      ? takeoffEdgePiecesFromLinear({ total_linear_ft, length_per_piece_ft: dripEdge.length_per_piece_ft })
      : 0;

    return { bundles, underlayment_rolls, drip_pieces };
  }, [takeoff_inputs, line, picks, sys]);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="asphalt-branch">
      <Select label="Manufacturer" testid="asphalt-manufacturer" value={picks.manufacturer || ""} onChange={(v) => { setPick("manufacturer", v); setPick("line", ""); setPick("color", ""); }}>
        <option value="">Select…</option>
        {sys.manufacturers.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
      </Select>

      <Select label="Product Line" testid="asphalt-line" value={picks.line || ""} disabled={!manufacturer} onChange={(v) => setPick("line", v)}>
        <option value="">{manufacturer ? "Select line…" : "Pick a manufacturer first"}</option>
        {manufacturer?.lines.map((l) => <option key={l.name} value={l.name}>{l.name}</option>)}
      </Select>

      <Select label="Color" testid="asphalt-color" value={picks.color || ""} disabled={!manufacturer} onChange={(v) => setPick("color", v)}>
        <option value="">{manufacturer ? "Select color…" : "—"}</option>
        {manufacturer?.color_catalog.map((c) => <option key={c} value={c}>{c}</option>)}
      </Select>

      <Select label="Starter Strip" testid="asphalt-starter" value={picks.starter_strip || ""} onChange={(v) => setPick("starter_strip", v)}>
        <option value="">Select…</option>
        {sys.starter_strip_options.map((s) => <option key={s.name} value={s.name}>{s.name} ({s.linear_ft_per_bundle} lf/bundle)</option>)}
      </Select>

      <Select label="Hip & Ridge Cap" testid="asphalt-ridge" value={picks.hip_ridge_cap || ""} onChange={(v) => setPick("hip_ridge_cap", v)}>
        <option value="">Select…</option>
        {sys.hip_and_ridge_caps.map((c) => <option key={c.name} value={c.name}>{c.name} ({c.linear_ft_per_box} lf/box)</option>)}
      </Select>

      <Select label="Underlayment" testid="asphalt-underlayment" value={picks.underlayment || ""} onChange={(v) => setPick("underlayment", v)}>
        <option value="">Select…</option>
        <optgroup label="Traditional Felt">
          {sys.underlayment_options.traditional_felt.map((u) => <option key={u.style} value={u.style}>{u.style}</option>)}
        </optgroup>
        <optgroup label="Synthetic Felt">
          {sys.underlayment_options.synthetic_felt.map((u) => <option key={u.style} value={u.style}>{u.style}</option>)}
        </optgroup>
        <optgroup label="Ice & Water Shield">
          {sys.underlayment_options.ice_and_water_shield.map((u) => <option key={u.style} value={u.style}>{u.style} ({u.mil_thickness} mil)</option>)}
        </optgroup>
      </Select>

      <Select label="Drip Edge Style" testid="asphalt-drip-style" value={picks.drip_edge_style || ""} onChange={(v) => setPick("drip_edge_style", v)}>
        <option value="">Select…</option>
        {sys.edge_metal_and_drip_options.styles.map((s) => <option key={s.type} value={s.type}>{s.type}</option>)}
      </Select>

      <Select label="Drip Edge Material" testid="asphalt-drip-material" value={picks.drip_edge_material || ""} onChange={(v) => setPick("drip_edge_material", v)}>
        <option value="">Select…</option>
        {sys.edge_metal_and_drip_options.materials.map((m) => <option key={m} value={m}>{m}</option>)}
      </Select>

      <Select label="Drip Edge Color" testid="asphalt-drip-color" value={picks.drip_edge_color || ""} onChange={(v) => setPick("drip_edge_color", v)}>
        <option value="">Select…</option>
        {sys.edge_metal_and_drip_options.color_catalog.map((c) => <option key={c} value={c}>{c}</option>)}
      </Select>

      <Select label="Step Flashing" testid="asphalt-step-flashing" value={picks.step_flashing || ""} onChange={(v) => setPick("step_flashing", v)}>
        <option value="">Select…</option>
        {sys.flashing_infrastructure.step_flashing.map((s) => <option key={s.size} value={s.size}>{s.size} (pack {s.pack_count})</option>)}
      </Select>

      <Select label="Wall / Counter Flashing" testid="asphalt-counter-flashing" value={picks.counter_flashing || ""} onChange={(v) => setPick("counter_flashing", v)}>
        <option value="">Select…</option>
        {sys.flashing_infrastructure.wall_and_counter_flashing.map((s) => <option key={s.type} value={s.type}>{s.type} ({s.dimensions})</option>)}
      </Select>

      <Select label="Pipe Boot Penetration" testid="asphalt-pipe-boot" value={picks.pipe_boot || ""} onChange={(v) => setPick("pipe_boot", v)}>
        <option value="">Select…</option>
        {sys.flashing_infrastructure.penetration_boots.map((p) => <option key={`${p.type}-${p.pipe_size_range}`} value={`${p.type} • ${p.pipe_size_range}`}>{p.type} ({p.pipe_size_range})</option>)}
      </Select>

      <Select label="Fastener Matrix" testid="asphalt-fasteners" value={picks.fastener || ""} onChange={(v) => setPick("fastener", v)}>
        <option value="">Select…</option>
        {sys.fastener_matrix.map((f) => <option key={f.type} value={f.type}>{f.type} — {f.delivery_method}</option>)}
      </Select>

      {/* LIVE TAKEOFF PREVIEW */}
      {takeoff && (
        <div className="md:col-span-2 mt-2 p-3 border border-[#00F5D4]/40 bg-[#00F5D4]/[0.04]" data-testid="asphalt-takeoff-preview">
          <div className="font-mono text-[10px] tracking-widest uppercase text-teal mb-2">// LIVE QUANTITY TAKEOFF (12% waste · 10% underlayment waste · 8% edge waste)</div>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Shingle Bundles" value={`${takeoff.bundles}`} />
            <Stat label="Underlayment Rolls" value={`${takeoff.underlayment_rolls}`} />
            <Stat label="Drip Edge Pieces" value={`${takeoff.drip_pieces}`} />
          </div>
        </div>
      )}
    </div>
  );
}

// ===========================================================================
// METAL BRANCH
// ===========================================================================
function MetalBranch({ sys, picks, setPick }) {
  const manufacturer = sys.manufacturers.find((m) => m.name === picks.manufacturer);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="metal-branch">
      <Select label="Manufacturer" testid="metal-manufacturer" value={picks.manufacturer || ""} onChange={(v) => { setPick("manufacturer", v); setPick("series", ""); }}>
        <option value="">Select…</option>
        {sys.manufacturers.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
      </Select>

      <Select label="Panel Series" testid="metal-series" value={picks.series || ""} disabled={!manufacturer} onChange={(v) => setPick("series", v)}>
        <option value="">{manufacturer ? "Select…" : "Pick manufacturer first"}</option>
        {manufacturer?.series.map((s) => <option key={s} value={s}>{s}</option>)}
      </Select>

      <Select label="Seam Profile" testid="metal-seam" value={picks.seam_profile || ""} onChange={(v) => setPick("seam_profile", v)}>
        <option value="">Select…</option>
        {sys.seam_profiles.map((s) => <option key={s.name} value={s.name}>{s.name} (min {s.minimum_slope})</option>)}
      </Select>

      <Select label="Substrate" testid="metal-substrate" value={picks.substrate || ""} onChange={(v) => setPick("substrate", v)}>
        <option value="">Select…</option>
        {sys.metal_substrates.map((s) => <option key={s.type} value={s.type}>{s.type}</option>)}
      </Select>

      <Select label="Fasteners / Anchors" testid="metal-fasteners" value={picks.fastener || ""} onChange={(v) => setPick("fastener", v)}>
        <option value="">Select…</option>
        {sys.fasteners_and_anchors.map((f) => <option key={f.type} value={f.type}>{f.type}</option>)}
      </Select>

      <Select label="Sealants / Closures" testid="metal-sealants" value={picks.sealant || ""} onChange={(v) => setPick("sealant", v)}>
        <option value="">Select…</option>
        {sys.sealants_and_closures.map((s) => <option key={s.type} value={s.type}>{s.type}</option>)}
      </Select>

      <Select label="Panel Color" testid="metal-color" value={picks.color || ""} onChange={(v) => setPick("color", v)}>
        <option value="">Select…</option>
        {sys.color_catalog.map((c) => <option key={c} value={c}>{c}</option>)}
      </Select>
    </div>
  );
}

// ===========================================================================
// SLATE BRANCH
// ===========================================================================
function SlateBranch({ sys, picks, setPick }) {
  const manufacturer = sys.manufacturers.find((m) => m.name === picks.manufacturer);

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="slate-branch">
      <Select label="Manufacturer / Quarry" testid="slate-manufacturer" value={picks.manufacturer || ""} onChange={(v) => { setPick("manufacturer", v); setPick("quarry_origin", ""); }}>
        <option value="">Select…</option>
        {sys.manufacturers.map((m) => <option key={m.name} value={m.name}>{m.name}</option>)}
      </Select>

      <Select label="Quarry Origin" testid="slate-quarry" value={picks.quarry_origin || ""} disabled={!manufacturer} onChange={(v) => setPick("quarry_origin", v)}>
        <option value="">{manufacturer ? "Select…" : "Pick quarry first"}</option>
        {manufacturer?.quarry_origins.map((q) => <option key={q} value={q}>{q}</option>)}
      </Select>

      <Select label="Thickness Grade" testid="slate-thickness" value={picks.thickness || ""} onChange={(v) => setPick("thickness", v)}>
        <option value="">Select…</option>
        {sys.thickness_grading.map((t) => <option key={t.grade} value={t.grade}>{t.grade} ({t.average_weight_per_square_lbs} lbs/sq)</option>)}
      </Select>

      <Select label="Fastener" testid="slate-fastener" value={picks.fastener || ""} onChange={(v) => setPick("fastener", v)}>
        <option value="">Select…</option>
        {sys.fasteners.map((f) => <option key={f.type} value={f.type}>{f.type}</option>)}
      </Select>
    </div>
  );
}

// ============ Reusable form widgets ============
function Select({ label, value, onChange, children, disabled = false, testid }) {
  return (
    <label className="block" data-testid={`${testid}-label`}>
      <span className="font-mono text-[10px] tracking-widest uppercase text-muted-hud block mb-1">{label}</span>
      <select
        data-testid={testid}
        disabled={disabled}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full bg-[#0B0F19] border border-[#00F0FF]/25 px-3 py-2 font-mono text-xs text-silver outline-none focus:border-teal disabled:opacity-40"
      >
        {children}
      </select>
    </label>
  );
}

function Stat({ label, value }) {
  return (
    <div className="border border-[#00F0FF]/20 p-2">
      <div className="font-mono text-[9px] tracking-widest uppercase text-muted-hud">{label}</div>
      <div className="font-display text-base text-teal">{value}</div>
    </div>
  );
}
