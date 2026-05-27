import React, { useEffect, useRef, useState } from "react";
import RoofModel3D from "@/components/RoofModel3D";
import { AUDIT_TELEMETRY, AUDIT_RAW_VERTICES } from "@/lib/auditTelemetry";

/**
 * /_roof-audit — Geometric & visual audit harness.
 *
 * Hardcodes a 6-facet compound hip-and-gable roof with KNOWN integer-derived
 * vertex coordinates (see `lib/auditTelemetry.js`) so an external playwright
 * pass can compute the bit-exact delta between raw input vectors and the
 * THREE.js BufferGeometry positions actually rendered to GPU.
 *
 * Public surface (window):
 *   window.__roofAudit = {
 *      raw_vertices:        [{facet_id, vertex_idx, x, y, z}, ...],
 *      telemetry:           <full payload>,
 *      readRenderedVertices(): [{facet_id, points: Float32Array}, ...]
 *   }
 */
export default function RoofAuditHarness() {
  const [activeLayer, setActiveLayer] = useState("shingle");
  const [showGutters, setShowGutters] = useState(true);
  const stateProbe = useRef({});

  // ---- Wire the global audit accessor as soon as the canvas has mounted ----
  useEffect(() => {
    window.__roofAudit = {
      raw_vertices: AUDIT_RAW_VERTICES,
      telemetry: AUDIT_TELEMETRY,
      readRenderedVertices: () => {
        const probe = window.__roofAuditScene;
        if (!probe || !probe.scene) return { error: "scene_not_probed_yet" };
        // Walk every finish layer group + the framing group; dump position
        // buffer contents per mesh tagged with its facet id (stored on the
        // mesh's parent userData.facet when present).
        const out = [];
        const layers = probe.finishLayerGroups || {};
        Object.keys(layers).forEach((layerKey) => {
          layers[layerKey].children.forEach((facetGroup) => {
            const mesh = facetGroup.children[0];
            const facet = facetGroup.userData?.facet;
            if (!mesh?.geometry?.attributes?.position) return;
            const pos = mesh.geometry.attributes.position.array;
            const points = [];
            for (let i = 0; i < pos.length; i += 3) points.push([pos[i], pos[i + 1], pos[i + 2]]);
            out.push({
              layer: layerKey,
              facet_id: facet?.id || "<unknown>",
              point_count: points.length,
              points,
            });
          });
        });
        return { meshes: out };
      },
    };
    return () => {
      delete window.__roofAudit;
      delete window.__roofAuditScene;
    };
  }, []);

  const TOGGLES = [
    { k: "framing", label: "FRAMING", c: "#5FF4FF" },
    { k: "shingle", label: "3-TAB", c: "#4CC3FF" },
    { k: "dimensional", label: "DIMENSIONAL", c: "#4CC3FF" },
    { k: "metal", label: "METAL", c: "#5FF4FF" },
    { k: "slate", label: "SLATE", c: "#D99DFF" },
  ];

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10">
      <div className="max-w-[1500px] mx-auto" data-testid="audit-root">
        <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-2">
          // STRATEX VISION • 3D CAD TWIN AUDIT
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest text-silver mb-2">
          Telemetry → Render Geometric Validation
        </h1>
        <p className="text-sm text-muted-hud font-body mb-6 max-w-3xl">
          6-facet compound hip-and-gable with variable pitches 4:12 → 10:12. Vertex coordinates derived from
          clean integer rises/runs; expected sub-centimeter Float32 buffer delta.
        </p>

        <div className="mb-6 border border-[#00F0FF]/30 bg-[#0B0F19]" data-testid="audit-canvas">
          <div className="flex items-center justify-between px-4 py-3 border-b border-[#00F0FF]/20 flex-wrap gap-3">
            <span className="font-mono text-[11px] tracking-widest uppercase text-teal">
              ACTIVE: {activeLayer.toUpperCase()} {showGutters ? "+ GUTTERS" : ""}
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {TOGGLES.map((t) => {
                const active = activeLayer === t.k;
                return (
                  <button
                    key={t.k}
                    data-testid={`audit-toggle-${t.k}`}
                    aria-pressed={active}
                    onClick={() => setActiveLayer(t.k)}
                    className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                    style={{
                      background: active ? `${t.c}22` : "rgba(11,15,25,0.85)",
                      color: active ? t.c : "#94A3B8",
                      borderColor: active ? t.c : "rgba(0,240,255,0.25)",
                      boxShadow: active ? `0 0 10px ${t.c}66, inset 0 0 6px ${t.c}33` : "none",
                      textShadow: active ? `0 0 6px ${t.c}` : "none",
                    }}
                  >
                    <span className="w-1.5 h-1.5 inline-block mr-1 align-middle" style={{ background: t.c, boxShadow: `0 0 4px ${t.c}` }} />
                    {t.label}
                  </button>
                );
              })}
              <span className="h-4 w-px bg-[#00F0FF]/30 mx-1" />
              <button
                data-testid="audit-toggle-gutters"
                aria-pressed={showGutters}
                onClick={() => setShowGutters((g) => !g)}
                className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                style={{
                  background: showGutters ? "#FF8A1F22" : "rgba(11,15,25,0.85)",
                  color: showGutters ? "#FF8A1F" : "#94A3B8",
                  borderColor: showGutters ? "#FF8A1F" : "rgba(0,240,255,0.25)",
                  boxShadow: showGutters ? "0 0 10px #FF8A1F66, inset 0 0 6px #FF8A1F33" : "none",
                  textShadow: showGutters ? "0 0 6px #FF8A1F" : "none",
                }}
              >
                GUTTERS {showGutters ? "ON" : "OFF"}
              </button>
            </div>
          </div>
          <div className="p-1">
            <RoofModel3D
              telemetry={AUDIT_TELEMETRY}
              anomalies={[]}
              height={620}
              showLabels={false}
              showDimensions={true}
              layers={null}
              primaryLayer={activeLayer}
              showGutters={showGutters}
              autoRotate={true}
              __debugSceneProbe={(probe) => { window.__roofAuditScene = probe; }}
            />
          </div>
        </div>

        <div className="font-mono text-[10px] tracking-widest uppercase text-muted-hud">
          AUDIT VERTEX COUNT • {AUDIT_RAW_VERTICES.length} RAW VECTORS · 6 FACETS · 4:12 / 6:12 / 8:12 / 10:12 PITCHES
        </div>
      </div>
    </div>
  );
}
