import React, { useEffect, useState } from "react";
import RoofModel3D from "@/components/RoofModel3D";
import ValidationReport from "@/components/ValidationReport";
import { api } from "@/lib/api";

/**
 * /_neon-preview — internal interactive 3D layer-switcher demo.
 * Single RoofModel3D instance + BEES layer toggles with the cinematic
 * electric-teal wipe transition. Public, no auth, not linked from main nav.
 *
 * NOTE: This page hosts ONLY ONE RoofModel3D instance by design — multiple
 * WebGL contexts on the same page would throttle each other's rAF down to
 * 2-3 fps and make the wipe imperceptible. Designers comparing finishes
 * should cycle the layer toggles to see each variant.
 */
export default function NeonLayerPreview() {
  const [demo, setDemo] = useState(null);
  const [activeLayer, setActiveLayer] = useState("shingle");
  const [demoGutters, setDemoGutters] = useState(true);

  useEffect(() => {
    api.get("/public/demo-topology").then((r) => setDemo(r.data)).catch(() => setDemo(null));
  }, []);

  const TOGGLE_KEYS = [
    { k: "framing",     label: "FRAMING",     c: "#5FF4FF", desc: "Cyan Rafters + Orange Sub-Fascia" },
    { k: "shingle",     label: "3-TAB",       c: "#4CC3FF", desc: "Matte Nickel · Flat Tab Grid" },
    { k: "dimensional", label: "DIMENSIONAL", c: "#4CC3FF", desc: "Matte Nickel · High-Relief Lamination" },
    { k: "metal",       label: "METAL",       c: "#5FF4FF", desc: "High Specular · Standing Seam" },
    { k: "slate",       label: "SLATE",       c: "#D99DFF", desc: "Stone-Fracture · Razor Edges" },
  ];
  const activeDesc = TOGGLE_KEYS.find((t) => t.k === activeLayer)?.desc || "";
  const activeColor = TOGGLE_KEYS.find((t) => t.k === activeLayer)?.c || "#00F5D4";

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10">
      <div className="max-w-[1500px] mx-auto">
        <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-2">
          // STRATEX VISION • BEES LAYER SWITCHER
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest text-silver mb-2">
          Layer Visibility Constraints — Live Switcher
        </h1>
        <p className="text-sm text-muted-hud font-body mb-8 max-w-3xl">
          Five mutually-exclusive primary layers. Each toggle triggers a cinematic electric-teal wipe transition.
          The gutter overlay is an independent secondary layer that anchors to whichever primary is currently active.
        </p>

        {/* ===== INTERACTIVE WIPE-TRANSITION DEMO ===== */}
        <div className="mb-10 border border-[#00F0FF]/30 bg-[#0B0F19]" data-testid="wipe-demo-panel">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#00F0FF]/20 flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span
                className="w-4 h-4 rounded-full"
                style={{ background: activeColor, boxShadow: `0 0 16px ${activeColor}` }}
              />
              <span className="font-mono text-[11px] tracking-widest uppercase text-teal">
                {activeDesc}
              </span>
            </div>
            <div className="flex items-center gap-1.5 flex-wrap">
              {TOGGLE_KEYS.map((t) => {
                const active = activeLayer === t.k;
                return (
                  <button
                    key={t.k}
                    data-testid={`wipe-demo-${t.k}`}
                    aria-pressed={active}
                    onClick={() => setActiveLayer(t.k)}
                    className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                    style={{
                      background: active ? `${t.c}22` : "rgba(11,15,25,0.85)",
                      color: active ? t.c : "#94A3B8",
                      borderColor: active ? t.c : "rgba(0,240,255,0.25)",
                      boxShadow: active ? `0 0 10px ${t.c}66, inset 0 0 6px ${t.c}33` : "none",
                      textShadow: active ? `0 0 6px ${t.c}` : "none",
                      backdropFilter: "blur(8px)",
                    }}
                  >
                    <span className="w-1.5 h-1.5 inline-block mr-1 align-middle" style={{ background: t.c, boxShadow: `0 0 4px ${t.c}` }} />
                    {t.label}
                  </button>
                );
              })}
              <span className="h-4 w-px bg-[#00F0FF]/30 mx-1" />
              <button
                data-testid="wipe-demo-gutters"
                aria-pressed={demoGutters}
                onClick={() => setDemoGutters((g) => !g)}
                className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                style={{
                  background: demoGutters ? "#FF8A1F22" : "rgba(11,15,25,0.85)",
                  color: demoGutters ? "#FF8A1F" : "#94A3B8",
                  borderColor: demoGutters ? "#FF8A1F" : "rgba(0,240,255,0.25)",
                  boxShadow: demoGutters ? "0 0 10px #FF8A1F66, inset 0 0 6px #FF8A1F33" : "none",
                  textShadow: demoGutters ? "0 0 6px #FF8A1F" : "none",
                }}
              >
                <span className="w-1.5 h-1.5 inline-block mr-1 align-middle" style={{ background: "#FF8A1F", boxShadow: "0 0 4px #FF8A1F" }} />
                GUTTERS {demoGutters ? "ON" : "OFF"}
              </button>
            </div>
          </div>
          <div className="p-1">
            <RoofModel3D
              telemetry={demo || { style: "stratex_demo", scale: 1.0, facets: [], edges: [], framing: { rafters: [], sub_fascia: [] }, gutters: { polylines: [], downspouts: [] } }}
              anomalies={[]}
              height={620}
              showLabels={false}
              showDimensions={false}
              layers={null}
              primaryLayer={activeLayer}
              showGutters={demoGutters}
              autoRotate={true}
            />
          </div>
        </div>

        {demo?.validation && (
          <div className="max-w-2xl">
            <ValidationReport validation={demo.validation} />
          </div>
        )}
      </div>
    </div>
  );
}
