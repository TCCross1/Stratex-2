// STRATEX™ — Multi-Angle Twin Gallery (Presentation Asset Only)
//
// IMPORTANT — PRIMARY ROLE NOTE:
// Stratex is an ANALYSIS ENGINE for already-created scan data. It does NOT
// create raw measurements. These visuals are presentation assets only.
// All calculations and estimations are tied to real scan inputs upstream.
//
// This component shows the approved Stratex digital-twin renders as a
// stepped 4-angle rotation gallery:
//   1) Front-Right · 2) Rear-Right · 3) Rear-Left · 4) Front-Left
// Sourced from /twin/quad.jpeg (a 2x2 grid of pre-rendered isometric views).
//
// We never misrepresent these as measurement-grade 3D geometry.

import { useEffect, useState } from "react";

const ANGLES = [
  { id: 0, label: "FRONT · RIGHT", clip: "inset(0 50% 50% 0)", origin: "0% 0%" },
  { id: 1, label: "REAR · RIGHT",  clip: "inset(0 0 50% 50%)", origin: "100% 0%" },
  { id: 2, label: "REAR · LEFT",   clip: "inset(50% 0 0 50%)", origin: "100% 100%" },
  { id: 3, label: "FRONT · LEFT",  clip: "inset(50% 50% 0 0)", origin: "0% 100%" },
];

export default function StratexTwinGallery({ height = 360, autoRotate = true }) {
  const [angle, setAngle] = useState(0);

  useEffect(() => {
    if (!autoRotate) return;
    const t = setInterval(() => setAngle((a) => (a + 1) % 4), 3800);
    return () => clearInterval(t);
  }, [autoRotate]);

  const a = ANGLES[angle];
  return (
    <div data-testid="stratex-twin-gallery" style={{
      position: "relative", width: "100%", height,
      borderRadius: 6, overflow: "hidden",
      border: "1px solid rgba(77,246,255,0.25)",
      boxShadow: "inset 0 0 60px rgba(77,246,255,0.06)",
      background: "#02060B",
    }}>
      {/* Image — single source, clipped to one of 4 quadrants, scaled 2x */}
      <div style={{
        position: "absolute", inset: 0,
        backgroundImage: "url(/twin/quad.jpeg)",
        backgroundSize: "200% 200%",
        backgroundPosition: a.origin,
        transition: "background-position 1.6s cubic-bezier(0.4,0,0.2,1)",
      }}/>

      {/* Top-left: angle label */}
      <div style={{
        position: "absolute", top: 10, left: 12,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
        color: "#4DF6FF", letterSpacing: "0.22em",
        background: "rgba(2,6,11,0.7)", border: "1px solid rgba(77,246,255,0.35)",
        padding: "5px 10px", borderRadius: 3,
      }}>
        VIEW · {a.label}
      </div>

      {/* Top-right: presentation-asset disclaimer */}
      <div style={{
        position: "absolute", top: 10, right: 12,
        fontFamily: "'JetBrains Mono', monospace", fontSize: 8,
        color: "#7C8A9E", letterSpacing: "0.18em",
        background: "rgba(2,6,11,0.65)",
        padding: "5px 10px", borderRadius: 3,
        border: "1px solid rgba(124,138,158,0.25)",
      }}>
        ANALYSIS ENGINE · PRESENTATION RENDER
      </div>

      {/* Bottom: angle stepper */}
      <div style={{
        position: "absolute", bottom: 10, left: "50%", transform: "translateX(-50%)",
        display: "flex", gap: 6, alignItems: "center",
        background: "rgba(2,6,11,0.75)", border: "1px solid rgba(77,246,255,0.25)",
        padding: "6px 10px", borderRadius: 100,
      }}>
        {ANGLES.map((x) => (
          <button
            key={x.id}
            data-testid={`twin-angle-${x.id}`}
            onClick={() => setAngle(x.id)}
            style={{
              width: angle === x.id ? 22 : 8, height: 8, borderRadius: 100,
              background: angle === x.id ? "#4DF6FF" : "#3a4a5c",
              boxShadow: angle === x.id ? "0 0 8px rgba(77,246,255,0.7)" : "none",
              border: "none", cursor: "pointer", padding: 0,
              transition: "all 0.25s ease",
            }}
            aria-label={x.label}
          />
        ))}
      </div>
    </div>
  );
}
