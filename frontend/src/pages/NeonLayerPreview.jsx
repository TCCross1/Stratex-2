import React, { useEffect, useState } from "react";
import RoofModel3D from "@/components/RoofModel3D";
import { api } from "@/lib/api";

/**
 * /_neon-preview — internal visual gallery rendering each XOR layer of the
 * STRATEX Vision 3D canvas so designers/PMs can compare the neon palette
 * side-by-side. Public, no auth, not linked from the main nav.
 */
const LAYERS = [
  { key: "shingle", label: "Shingle", swatch: "#1ea7ff", desc: "Neon Blue" },
  { key: "metal",   label: "Metal",   swatch: "#ff2d4a", desc: "Neon Red" },
  { key: "slate",   label: "Slate",   swatch: "#c77dff", desc: "Neon Violet" },
  { key: "framing", label: "Framing", swatch: "#ffea00", desc: "Neon Yellow" },
];

export default function NeonLayerPreview() {
  const [demo, setDemo] = useState(null);

  useEffect(() => {
    api.get("/public/demo-topology").then((r) => setDemo(r.data)).catch(() => setDemo(null));
  }, []);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10">
      <div className="max-w-[1500px] mx-auto">
        <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-2">
          // STRATEX VISION • NEON LAYER PALETTE
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest text-silver mb-2">
          Layer Visibility Constraints — Side-by-Side
        </h1>
        <p className="text-sm text-muted-hud font-body mb-8 max-w-3xl">
          Four mutually-exclusive primary layers. Each panel below renders the same compound demo roof with a different
          neon finish active, plus one final panel showing Framing-only and one with gutters toggled OFF for contrast.
        </p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {LAYERS.map((l) => (
            <div key={l.key} className="border border-[#00F0FF]/25 bg-[#0B0F19]" data-testid={`neon-preview-${l.key}`}>
              <div className="flex items-center justify-between px-4 py-3 border-b border-[#00F0FF]/20">
                <div className="flex items-center gap-3">
                  <span
                    className="w-4 h-4 rounded-full"
                    style={{ background: l.swatch, boxShadow: `0 0 12px ${l.swatch}` }}
                  />
                  <span className="font-mono text-[11px] tracking-widest uppercase text-teal">{l.label}</span>
                </div>
                <span className="font-mono text-[10px] tracking-widest uppercase text-muted-hud">{l.desc} • {l.swatch}</span>
              </div>
              <div className="p-1">
                <RoofModel3D
                  telemetry={demo || { style: "stratex_demo", scale: 1.0, facets: [], edges: [], framing: { rafters: [], sub_fascia: [] }, gutters: { polylines: [], downspouts: [] } }}
                  anomalies={[]}
                  height={360}
                  showLabels={false}
                  showDimensions={false}
                  layers={null}
                  primaryLayer={l.key}
                  showGutters={true}
                  autoRotate={true}
                />
              </div>
            </div>
          ))}

          {/* Bonus: gutters OFF reference */}
          <div className="border border-[#00F0FF]/25 bg-[#0B0F19] md:col-span-2" data-testid="neon-preview-shingle-no-gutters">
            <div className="flex items-center justify-between px-4 py-3 border-b border-[#00F0FF]/20">
              <div className="flex items-center gap-3">
                <span className="w-4 h-4 rounded-full" style={{ background: "#1ea7ff", boxShadow: "0 0 12px #1ea7ff" }} />
                <span className="font-mono text-[11px] tracking-widest uppercase text-teal">Shingle • Gutters OFF</span>
              </div>
              <span className="font-mono text-[10px] tracking-widest uppercase text-muted-hud">Reference: same roof, no orange eave</span>
            </div>
            <div className="p-1">
              <RoofModel3D
                telemetry={demo || { style: "stratex_demo", scale: 1.0, facets: [], edges: [], framing: { rafters: [], sub_fascia: [] }, gutters: { polylines: [], downspouts: [] } }}
                anomalies={[]}
                height={420}
                showLabels={false}
                showDimensions={false}
                layers={null}
                primaryLayer="shingle"
                showGutters={false}
                autoRotate={true}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
