import React, { useState, useMemo } from "react";
import { Thermometer, Crosshair, Activity, Info } from "lucide-react";

/**
 * Forensic Overlay floating card — matches the reference image.
 * Shows: Diagnosis / Location (Facet ID) / Area Affected / Confidence + thermal heatmap.
 */

function ThermalHeatmap({ anomaly }) {
  // Procedurally render a faux thermal heatmap canvas based on anomaly seed.
  const seed = useMemo(() => {
    let s = 0;
    for (let i = 0; i < (anomaly?.id || "").length; i++) s = (s * 31 + anomaly.id.charCodeAt(i)) >>> 0;
    return s;
  }, [anomaly?.id]);

  const canvasRef = React.useRef(null);
  React.useEffect(() => {
    const c = canvasRef.current;
    if (!c) return;
    const w = c.width = 260;
    const h = c.height = 130;
    const ctx = c.getContext("2d");
    const img = ctx.createImageData(w, h);
    const cx = w / 2 + ((seed % 40) - 20);
    const cy = h / 2 + ((seed >> 4) % 30 - 15);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const dx = (x - cx) / (w * 0.45);
        const dy = (y - cy) / (h * 0.55);
        let d = Math.sqrt(dx * dx + dy * dy);
        // add multi-octave noise for cluster shape
        const n1 = Math.sin((x + seed) * 0.07) * Math.cos((y + seed) * 0.09) * 0.18;
        const n2 = Math.sin((x - seed) * 0.025 + y * 0.04) * 0.1;
        d += n1 + n2;
        d = Math.max(0, Math.min(1, 1 - d));
        // ramp: navy -> magenta -> orange -> yellow -> white (FLIR Iron palette feel)
        let r, g, b;
        if (d < 0.25) {       // deep cold (navy)
          const t = d / 0.25;
          r = 4 + 60 * t; g = 6 + 6 * t; b = 38 + 70 * t;
        } else if (d < 0.5) { // magenta/purple
          const t = (d - 0.25) / 0.25;
          r = 64 + 130 * t; g = 12 + 20 * t; b = 108 - 50 * t;
        } else if (d < 0.75) {// orange
          const t = (d - 0.5) / 0.25;
          r = 194 + 50 * t; g = 32 + 130 * t; b = 58 - 40 * t;
        } else {              // yellow→white core
          const t = (d - 0.75) / 0.25;
          r = 244 + 11 * t; g = 162 + 90 * t; b = 18 + 200 * t;
        }
        const idx = (y * w + x) * 4;
        img.data[idx] = r; img.data[idx + 1] = g; img.data[idx + 2] = b; img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [seed]);

  return (
    <div className="relative" data-testid="thermal-heatmap">
      <canvas ref={canvasRef} className="w-full h-auto" style={{ filter: "saturate(1.15) contrast(1.05)" }} />
      <div className="absolute left-1 top-1 font-mono text-[9px] text-silver" style={{ textShadow: "0 0 4px rgba(0,0,0,0.8)" }}>0°C</div>
      <div className="absolute right-1 top-1 font-mono text-[9px] text-silver" style={{ textShadow: "0 0 4px rgba(0,0,0,0.8)" }}>+25°C</div>
      <div className="absolute right-1 bottom-1 font-mono text-[9px] text-silver" style={{ textShadow: "0 0 4px rgba(0,0,0,0.8)" }}>-15°C</div>
    </div>
  );
}

export default function ForensicOverlay({ anomaly, projectId, accentClass = "" }) {
  if (!anomaly) return null;
  return (
    <div data-testid="forensic-overlay" className={`hud-card hud-card-alert p-4 ${accentClass}`}>
      <span className="corner-bl" /><span className="corner-br" />
      <div className="flex items-center gap-2 mb-3">
        <div className="w-7 h-7 border border-[#FF5500] flex items-center justify-center text-plasma"><Thermometer size={14} strokeWidth={1.5}/></div>
        <div className="font-display text-base uppercase tracking-widest text-plasma glow-orange">Forensic Overlay</div>
      </div>
      <div className="space-y-2 text-sm">
        <Row label="Diagnosis" value={anomaly.diagnosis || anomaly.type} mono icon={Crosshair}/>
        <Row label="Location" value={`Facet ${anomaly.facet_id} (${anomaly.severity})`} icon={Info}/>
        <Row label="Area Affected" value={`${anomaly.area_affected_sf} sq. ft.`} icon={Activity}/>
        <Row label="Confidence" value={`${(anomaly.confidence * 100).toFixed(1)}%`} accent="volt"/>
        <Row label="Thermal Δ" value={anomaly.thermal_delta} accent="orange"/>
      </div>
      <div className="hud-divider my-3"/>
      <ThermalHeatmap anomaly={anomaly} />
      <div className="font-mono text-[10px] text-muted-hud mt-2">
        ID: <span className="text-silver">{anomaly.id}</span> • {anomaly.lat?.toFixed(4)}, {anomaly.lon?.toFixed(4)}
      </div>
    </div>
  );
}

function Row({ label, value, mono, accent, icon: Icon }) {
  const color = accent === "orange" ? "text-plasma" : accent === "volt" ? "text-volt" : "text-silver";
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="font-mono text-[10px] uppercase tracking-widest text-muted-hud flex items-center gap-1">
        {Icon && <Icon size={11} strokeWidth={1.5}/>} {label}
      </span>
      <span className={`${mono ? "font-mono" : "font-heading"} text-sm ${color}`}>{value}</span>
    </div>
  );
}

export function AnomalySelector({ anomalies, selectedId, onSelect }) {
  return (
    <div className="space-y-1.5" data-testid="anomaly-selector">
      {anomalies.map((a) => (
        <button
          key={a.id}
          onClick={() => onSelect(a)}
          data-testid={`anomaly-pick-${a.id}`}
          className={`w-full text-left p-2.5 border transition-all flex items-center gap-2 ${a.id === selectedId ? "border-[#FF5500] bg-[#FF5500]/10" : "border-[#00F0FF]/25 bg-[#10141D]/50 hover:border-[#00F0FF]"}`}
        >
          <span className={`led ${a.severity === "CRITICAL" || a.severity === "HIGH" ? "led-alert" : a.severity === "MED" ? "led-teal" : "led-ok"}`}/>
          <div className="flex-1">
            <div className="font-mono text-[11px] text-silver">{a.id}</div>
            <div className="font-heading text-[12px] uppercase tracking-widest text-muted-hud">{a.diagnosis || a.type} • Facet {a.facet_id}</div>
          </div>
          <div className="text-right">
            <div className="font-mono text-[11px] text-teal">{a.area_affected_sf} SF</div>
            <div className="font-mono text-[9px] text-plasma">{a.thermal_delta}</div>
          </div>
        </button>
      ))}
    </div>
  );
}
