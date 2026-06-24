import React, { useMemo } from "react";
import { Thermometer, Crosshair, Activity, Info } from "lucide-react";

/**
 * STRATEX™ Vision — Forensic Overlay PiP
 * Diagnosis / Location / Area / Confidence + thermal raster with -15°C → +25°C scale axis.
 */
function ThermalHeatmap({ anomaly }) {
  const seed = useMemo(() => {
    let s = 0;
    for (let i = 0; i < (anomaly?.id || "").length; i++) s = (s * 31 + anomaly.id.charCodeAt(i)) >>> 0;
    return s;
  }, [anomaly?.id]);

  const canvasRef = React.useRef(null);
  React.useEffect(() => {
    const c = canvasRef.current; if (!c) return;
    const w = c.width = 280, h = c.height = 150;
    const ctx = c.getContext("2d");
    const img = ctx.createImageData(w, h);
    const cx = w / 2 + ((seed % 40) - 20);
    const cy = h / 2 + ((seed >> 4) % 30 - 15);
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        const dx = (x - cx) / (w * 0.45);
        const dy = (y - cy) / (h * 0.55);
        let d = Math.sqrt(dx * dx + dy * dy);
        const n1 = Math.sin((x + seed) * 0.07) * Math.cos((y + seed) * 0.09) * 0.18;
        const n2 = Math.sin((x - seed) * 0.025 + y * 0.04) * 0.1;
        d += n1 + n2;
        d = Math.max(0, Math.min(1, 1 - d));
        let r, g, b;
        if (d < 0.25)      { const t = d / 0.25;        r = 4 + 60 * t;   g = 6 + 6 * t;     b = 38 + 70 * t; }
        else if (d < 0.5)  { const t = (d - 0.25) / 0.25; r = 64 + 130 * t; g = 12 + 20 * t;  b = 108 - 50 * t; }
        else if (d < 0.75) { const t = (d - 0.5) / 0.25;  r = 194 + 50 * t; g = 32 + 130 * t; b = 58 - 40 * t; }
        else               { const t = (d - 0.75) / 0.25; r = 244 + 11 * t; g = 162 + 90 * t; b = 18 + 200 * t; }
        const idx = (y * w + x) * 4;
        img.data[idx] = r; img.data[idx + 1] = g; img.data[idx + 2] = b; img.data[idx + 3] = 255;
      }
    }
    ctx.putImageData(img, 0, 0);
  }, [seed]);

  return (
    <div className="relative flex items-stretch gap-1.5" data-testid="thermal-heatmap">
      {/* Vertical thermal scale */}
      <div className="flex flex-col justify-between font-mono text-[9px] text-silver py-0.5" style={{minWidth: 28}}>
        <span>+25°C</span>
        <span>+5°C</span>
        <span>−15°C</span>
      </div>
      <div className="flex-1 relative border border-[#FF5500]/30">
        <canvas ref={canvasRef} className="block w-full h-auto" style={{ filter: "saturate(1.18) contrast(1.06)" }} />
        <div className="absolute top-1 left-1 font-mono text-[9px] text-silver px-1" style={{ background:"rgba(11,15,25,0.65)" }}>640 × 512 IR · FLIR Iron</div>
      </div>
      {/* Gradient legend bar */}
      <div className="w-2 border border-[#FF5500]/30" style={{
        background: "linear-gradient(to top, #042a, #4c0c6c, #c2203a, #f4a212, #ffffff)",
      }}/>
    </div>
  );
}

export default function ForensicOverlay({ anomaly, projectId, accentClass = "" }) {
  if (!anomaly) return null;
  return (
    <div data-testid="forensic-overlay" className={`hud-card hud-card-alert p-4 ${accentClass}`} style={{
      backdropFilter: "blur(18px)",
      WebkitBackdropFilter: "blur(18px)",
      background: "linear-gradient(180deg, rgba(11,15,25,0.92) 0%, rgba(11,15,25,0.78) 100%)",
    }}>
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
          <div className="flex-1 min-w-0">
            <div className="font-mono text-[11px] text-silver truncate">{a.id}</div>
            <div className="font-heading text-[12px] uppercase tracking-widest text-muted-hud truncate">{a.diagnosis || a.type} • Facet {a.facet_id}</div>
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

/**
 * Project Identity card — top-left of the Vision canvas.
 * Mirrors the reference image: shield logo + Project ID + CEO + Property.
 */
export function ProjectIdentityCard({ project }) {
  return (
    <div
      data-testid="project-identity-card"
      className="inline-flex items-center gap-3 px-3 py-2 border border-[#00F0FF]/55"
      style={{
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        background: "linear-gradient(135deg, rgba(11,15,25,0.92), rgba(16,20,29,0.78))",
        boxShadow: "0 0 24px rgba(0,240,255,0.18), inset 0 0 12px rgba(0,240,255,0.08)",
      }}
    >
      <div className="w-9 h-9 rounded-full border border-[#00F0FF]/70 flex items-center justify-center" style={{ boxShadow:"0 0 12px rgba(0,240,255,0.55)" }}>
        <svg viewBox="0 0 28 28" width="20" height="20" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2 L25 9 L23 22 L14 26 L5 22 L3 9 Z" fill="none" stroke="#00F0FF" strokeWidth="1.4"/>
          <path d="M9 16 L14 9 L19 16 Z" fill="#FF5500" opacity="0.85"/>
          <path d="M9 16 L14 9 L19 16 Z" fill="none" stroke="#00F0FF" strokeWidth="1"/>
        </svg>
      </div>
      <div className="leading-tight">
        <div className="font-mono text-[10px] uppercase tracking-widest text-teal" style={{ textShadow:"0 0 6px rgba(0,240,255,0.55)" }}>Project: {project.id_short}</div>
        <div className="font-mono text-[10px] text-silver">{project.principal}</div>
        <div className="font-mono text-[10px] text-muted-hud">Property: {project.property}</div>
      </div>
    </div>
  );
}

/**
 * STRATEX Quant™ Estimation card — bottom-left summary.
 */
export function QuantEstimationCard({ telemetry }) {
  const t = telemetry?.totals || {};
  return (
    <div
      data-testid="quant-estimation-card"
      className="px-4 py-3 border border-[#00F0FF]/55 min-w-[230px]"
      style={{
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        background: "linear-gradient(135deg, rgba(11,15,25,0.92), rgba(16,20,29,0.78))",
        boxShadow: "0 0 28px rgba(0,240,255,0.18), inset 0 0 12px rgba(0,240,255,0.08)",
      }}
    >
      <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-2" style={{ textShadow:"0 0 6px rgba(0,240,255,0.5)" }}>
        STRATEX Quant™ Estimation
      </div>
      <div className="space-y-1 font-mono text-[12px] text-silver">
        <div className="flex justify-between gap-6"><span>Total Squares</span><span className="text-teal">{t.squares ?? "—"}</span></div>
        <div className="flex justify-between gap-6"><span>Valleys (LF)</span><span className="text-plasma">{t.valleys_lf ?? "—"}</span></div>
        <div className="flex justify-between gap-6"><span>Gables / Hips (LF)</span><span className="text-teal">{t.hips_lf ?? "—"}</span></div>
        <div className="flex justify-between gap-6"><span>Ridges (LF)</span><span className="text-teal">{t.ridges_lf ?? "—"}</span></div>
        <div className="flex justify-between gap-6"><span>Total Roof SF</span><span className="text-silver">{t.total_sf ?? "—"}</span></div>
      </div>
    </div>
  );
}

/**
 * Anomaly Monetization Engine card — bottom-right, shows the dollar value
 * dynamically resolved from the contractor's encrypted Business Brain.
 */
export function AnomalyMonetizationCard({ anomaly, lineItem }) {
  if (!anomaly) {
    return (
      <div className="px-4 py-3 border border-[#00F0FF]/40 text-muted-hud font-mono text-[11px] uppercase tracking-widest"
           style={{ background: "rgba(11,15,25,0.85)" }}>
        Select an anomaly to compute repair value
      </div>
    );
  }
  const idx  = (anomaly.id || "").slice(-2);
  const dx   = lineItem?.total ?? anomaly.estimated_cost ?? 0;
  return (
    <div
      data-testid="anomaly-monetization-card"
      className="px-5 py-3 border border-[#00F0FF]/55 min-w-[280px]"
      style={{
        backdropFilter: "blur(16px)",
        WebkitBackdropFilter: "blur(16px)",
        background: "linear-gradient(135deg, rgba(11,15,25,0.92), rgba(16,20,29,0.78))",
        boxShadow: "0 0 28px rgba(0,240,255,0.22), inset 0 0 12px rgba(0,240,255,0.1)",
      }}
    >
      <div className="font-mono text-[10px] uppercase tracking-widest text-teal mb-0.5" style={{ textShadow:"0 0 6px rgba(0,240,255,0.5)" }}>
        Anomaly #{idx}:
      </div>
      <div className="font-mono text-[11px] text-silver mb-2">
        {(anomaly.diagnosis || anomaly.type)} ({anomaly.area_affected_sf} sq. ft.)
      </div>
      <div className="flex items-center justify-between gap-2 border-t border-[#00F0FF]/30 pt-2">
        <div className="font-display text-[26px] text-silver" style={{ textShadow: "0 0 14px rgba(0,240,255,0.45)" }}>
          {dx > 0 ? `$${dx.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : "Compute Proposal"}
        </div>
        <svg viewBox="0 0 16 16" width="18" height="18">
          <path d="M8 1 L11 5 L15 8 L11 11 L8 15 L5 11 L1 8 L5 5 Z" fill="#00F0FF" opacity="0.95" />
        </svg>
      </div>
    </div>
  );
}
