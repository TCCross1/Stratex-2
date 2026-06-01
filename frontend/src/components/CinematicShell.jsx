/**
 * CinematicShell — STRATEX™ universal "Investor Mode" wrapper.
 *
 * Recreates the IMG_2555 reference vibe in pure CSS/SVG so every screen
 * can be wrapped in a world-class scene without changing its content.
 *
 * Eight cinematic layers, z-stacked behind children:
 *   1. Deep room ambient (radial gradient base, blue→ink)
 *   2. Animated SVG PCB circuit traces (stroke-dasharray flow)
 *   3. Ceiling light strips (top edge, mix-blend screen)
 *   4. Volumetric cyan haze (3 stacked radial gradients)
 *   5. Holographic spillover (outer glow ring around content frame)
 *   6. Floating data crystals (animated diamond particles)
 *   7. Floor reflection plate (subtle gradient + scaleY mirror)
 *   8. Vignette + warm rim-light (left edge magenta wash)
 *
 * Usage:
 *   <CinematicShell title="Pilot Tablet" kiosk={kiosk}>
 *     <YourDashboardContent/>
 *   </CinematicShell>
 *
 * Or auto-toggle from URL: <CinematicShell autoKiosk>
 */
import React, { useEffect, useMemo, useState } from "react";

export default function CinematicShell({
  children,
  kiosk = false,
  autoKiosk = false,
  intensity = "high",     // "low" | "medium" | "high"
  framed = true,          // wrap content in a tablet-bezel frame
  testid = "cinematic-shell",
}) {
  const [active, setActive] = useState(kiosk);

  useEffect(() => {
    if (autoKiosk) {
      const url = new URL(window.location.href);
      const kioskFlag = url.searchParams.get("kiosk");
      setActive(kioskFlag === "1" || kioskFlag === "true");
    } else {
      setActive(kiosk);
    }
  }, [kiosk, autoKiosk]);

  // Pre-compute 24 random crystal positions so they don't reshuffle on re-render.
  const crystals = useMemo(() => (
    Array.from({ length: 24 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: 3 + Math.random() * 4,
      delay: Math.random() * 6,
      duration: 6 + Math.random() * 6,
      opacity: 0.3 + Math.random() * 0.5,
    }))
  ), []);

  const intensityScale = intensity === "low" ? 0.4 : intensity === "medium" ? 0.7 : 1;

  if (!active) {
    // Pass-through when kiosk disabled — operator daily mode stays clean.
    return <div data-testid={`${testid}-passthrough`}>{children}</div>;
  }

  return (
    <div data-testid={testid} className="stx-cine-root">
      {/* Layer 1: deep room ambient */}
      <div className="stx-cine-ambient"/>

      {/* Layer 2: animated PCB circuit traces */}
      <svg className="stx-cine-pcb" viewBox="0 0 1920 1080" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
        <defs>
          <linearGradient id="stx-trace-grad" x1="0" x2="1" y1="0" y2="0">
            <stop offset="0%"   stopColor="#00E5FF" stopOpacity="0"/>
            <stop offset="50%"  stopColor="#00E5FF" stopOpacity="0.95"/>
            <stop offset="100%" stopColor="#00E5FF" stopOpacity="0"/>
          </linearGradient>
          <filter id="stx-trace-glow"><feGaussianBlur stdDeviation="3"/></filter>
        </defs>
        {[
          "M0,200 L300,200 L320,180 L520,180 L540,200 L900,200",
          "M0,420 L240,420 L260,440 L580,440 L600,420 L1020,420 L1040,400 L1380,400",
          "M0,640 L160,640 L180,620 L460,620 L480,640 L820,640",
          "M0,860 L320,860 L340,840 L720,840 L740,860 L1240,860",
          "M1920,260 L1640,260 L1620,280 L1300,280 L1280,260 L900,260",
          "M1920,500 L1700,500 L1680,480 L1320,480",
          "M1920,720 L1580,720 L1560,740 L1180,740 L1160,720 L820,720",
          "M1920,960 L1620,960 L1600,940 L1240,940",
        ].map((d, i) => (
          <g key={i}>
            <path d={d} stroke="#00E5FF22" strokeWidth="1.2" fill="none"/>
            <path d={d} stroke="url(#stx-trace-grad)" strokeWidth="2"
                  fill="none" filter="url(#stx-trace-glow)"
                  strokeDasharray="120 800"
                  style={{
                    animation: `stxFlow ${10 + (i % 4) * 2}s linear infinite`,
                    animationDelay: `${i * 0.6}s`,
                  }}/>
            {/* Node dots */}
            {[300, 540, 900, 1300].map((x, j) => (
              <circle key={j} cx={x} cy={i % 2 ? 200 + i * 110 : 200 + i * 110}
                      r="2" fill="#00E5FF" opacity="0.6"/>
            ))}
          </g>
        ))}
      </svg>

      {/* Layer 3: ceiling light strips */}
      <div className="stx-cine-ceiling"/>

      {/* Layer 4: volumetric cyan haze (3 stacked) */}
      <div className="stx-cine-haze stx-cine-haze-1" style={{ opacity: 0.45 * intensityScale }}/>
      <div className="stx-cine-haze stx-cine-haze-2" style={{ opacity: 0.30 * intensityScale }}/>
      <div className="stx-cine-haze stx-cine-haze-3" style={{ opacity: 0.20 * intensityScale }}/>

      {/* Layer 8: rim-light + vignette */}
      <div className="stx-cine-rim"/>
      <div className="stx-cine-vignette"/>

      {/* Layer 6: floating data crystals */}
      <div className="stx-cine-crystals" aria-hidden="true">
        {crystals.map(c => (
          <span key={c.id}
            className="stx-crystal"
            style={{
              left: `${c.left}%`, top: `${c.top}%`,
              width: `${c.size}px`, height: `${c.size}px`,
              opacity: c.opacity * intensityScale,
              animationDelay: `${c.delay}s`,
              animationDuration: `${c.duration}s`,
            }}/>
        ))}
      </div>

      {/* Content frame (Layer 5 holographic spillover lives on this border) */}
      <div className={`stx-cine-stage ${framed ? "stx-cine-framed" : ""}`}>
        {framed && (
          <>
            <div className="stx-cine-bezel-status">
              <span className="stx-bezel-dot"/>
              <span className="stx-bezel-time">STRATEX™ · LIVE</span>
              <span className="stx-bezel-meta">{new Date().toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" })}</span>
            </div>
            {/* Layer 7: floor reflection */}
            <div className="stx-cine-reflection" aria-hidden="true"/>
          </>
        )}
        <div className="stx-cine-content">
          {children}
        </div>
      </div>

      <style>{`
        @keyframes stxFlow {
          0%   { stroke-dashoffset: 920; }
          100% { stroke-dashoffset: 0; }
        }
        @keyframes stxDrift {
          0%   { transform: translateY(0) rotate(45deg) scale(1); opacity: 0; }
          15%  { opacity: var(--stx-c-op, 0.6); }
          50%  { transform: translateY(-24px) rotate(45deg) scale(1.15); }
          85%  { opacity: var(--stx-c-op, 0.6); }
          100% { transform: translateY(-48px) rotate(45deg) scale(0.9); opacity: 0; }
        }
        @keyframes stxPulseBezel {
          0%, 100% { box-shadow: 0 0 60px #00E5FF44, 0 0 140px #00E5FF22, inset 0 0 60px #00E5FF11; }
          50%      { box-shadow: 0 0 90px #00E5FF66, 0 0 200px #00E5FF33, inset 0 0 70px #00E5FF1A; }
        }

        .stx-cine-root {
          position: relative; min-height: 100vh;
          background: #02060B;
          color: var(--stx-text);
          overflow: hidden;
          isolation: isolate;
        }
        .stx-cine-ambient {
          position: absolute; inset: 0; pointer-events: none; z-index: 1;
          background:
            radial-gradient(ellipse at 50% 0%,   rgba(0,90,140,0.40) 0%, transparent 55%),
            radial-gradient(ellipse at 50% 100%, rgba(0,30,60,0.55)  0%, transparent 60%),
            #02060B;
        }
        .stx-cine-pcb {
          position: absolute; inset: 0; width: 100%; height: 100%;
          pointer-events: none; z-index: 2; opacity: 0.55;
        }
        .stx-cine-ceiling {
          position: absolute; top: 0; left: 10%; right: 10%; height: 4px;
          background: linear-gradient(90deg, transparent, #00E5FF, #00E5FF, transparent);
          box-shadow: 0 0 24px #00E5FF, 0 0 60px #00E5FF88, 0 0 120px #00E5FF44;
          mix-blend-mode: screen;
          pointer-events: none; z-index: 3;
        }
        .stx-cine-haze {
          position: absolute; inset: 0; pointer-events: none; z-index: 4;
          mix-blend-mode: screen;
        }
        .stx-cine-haze-1 {
          background: radial-gradient(circle at 50% 65%, #00E5FF 0%, transparent 38%);
          filter: blur(60px);
        }
        .stx-cine-haze-2 {
          background: radial-gradient(circle at 20% 30%, #4A6FFF 0%, transparent 30%);
          filter: blur(70px);
        }
        .stx-cine-haze-3 {
          background: radial-gradient(circle at 85% 75%, #FFB020 0%, transparent 28%);
          filter: blur(80px);
        }
        .stx-cine-rim {
          position: absolute; top: 0; left: 0; bottom: 0; width: 8%;
          background: linear-gradient(90deg, #FFB02055 0%, transparent 100%);
          mix-blend-mode: screen; pointer-events: none; z-index: 5;
        }
        .stx-cine-vignette {
          position: absolute; inset: 0; pointer-events: none; z-index: 6;
          background: radial-gradient(ellipse at center, transparent 55%, rgba(0,0,0,0.7) 100%);
        }

        .stx-cine-crystals {
          position: absolute; inset: 0; pointer-events: none; z-index: 7;
        }
        .stx-crystal {
          position: absolute;
          background: linear-gradient(135deg, #00E5FF, #ffffff);
          box-shadow: 0 0 10px #00E5FF, 0 0 24px #00E5FF66;
          animation: stxDrift linear infinite;
          --stx-c-op: 0.6;
          will-change: transform, opacity;
        }

        .stx-cine-stage {
          position: relative; z-index: 10;
          padding: 22px 24px 80px;
          max-width: 1840px; margin: 0 auto;
        }
        .stx-cine-framed {
          margin: 24px auto 80px;
          padding: 0;
          background: linear-gradient(180deg, rgba(8,12,20,0.85) 0%, rgba(3,7,18,0.92) 100%);
          border: 1px solid rgba(0, 229, 255, 0.32);
          border-radius: 22px;
          animation: stxPulseBezel 4.5s ease-in-out infinite;
          overflow: hidden;
        }
        .stx-cine-bezel-status {
          display: flex; align-items: center; gap: 10px;
          padding: 9px 16px;
          background: rgba(2, 6, 11, 0.65);
          border-bottom: 1px solid rgba(0, 229, 255, 0.18);
          font-family: 'JetBrains Mono', monospace;
          font-size: 9px; letter-spacing: 0.28em; text-transform: uppercase;
          color: var(--stx-cyan);
          text-shadow: var(--stx-glow-cyan-tight);
        }
        .stx-bezel-dot {
          width: 6px; height: 6px; border-radius: 50%;
          background: var(--stx-green);
          box-shadow: 0 0 8px var(--stx-green), 0 0 18px var(--stx-green);
          animation: stxPulseBezel 2s ease-in-out infinite;
        }
        .stx-bezel-meta { margin-left: auto; color: var(--stx-text); opacity: 0.78; }
        .stx-cine-content {
          position: relative;
          padding: 8px 6px 18px;
        }
        .stx-cine-reflection {
          position: absolute; left: 6%; right: 6%; bottom: -42px; height: 64px;
          background: radial-gradient(ellipse at center, #00E5FF55 0%, transparent 70%);
          filter: blur(18px);
          pointer-events: none;
        }
      `}</style>
    </div>
  );
}
