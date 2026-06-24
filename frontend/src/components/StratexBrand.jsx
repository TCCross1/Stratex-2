// STRATEX™ — Official brand lock-up components
// Use these wherever the brand appears. NEVER hardcode "STRATEX" or
// the typo "STRATE Quant" — always use <StratexWordmark/> + the
// product names exported below.
//
// Color tokens (locked):
//   --brand-cyan:    #4DF6FF  (neon cyan-teal — outline + glow)
//   --brand-amber:   #FF7B00  (warm low-poly facet)
//   --brand-silver:  linear-gradient #FFFFFF → #8A95A3
//   --brand-bg:      #02060B  (matte black)

import React from "react";

export const BRAND_CYAN = "#4DF6FF";
export const BRAND_AMBER = "#FF7B00";

// Canonical product names
export const PRODUCT = {
  master: "STRATEX™",
  quant: "STRATEX Quant™",
  vision: "STRATEX Vision™",
  twin: "STRATEX Twin™",
  recon: "STRATEX Recon™",
};

// Official logo PNG — same one used on the landing page.
// USE THIS in every header across the app for brand consistency.
export function StratexLogo({ height = 32, className = "" }) {
  return (
    <img
      src="/stratex_logo.png"
      alt="STRATEX"
      className={className}
      style={{ height, width: "auto", display: "block" }}
      data-testid="stratex-logo"
    />
  );
}

export function StratexWordmark({ size = "md", trademark = true }) {
  const fz = { xs: 12, sm: 16, md: 22, lg: 36, xl: 64, hero: 84 }[size] || 22;
  return (
    <span
      className="font-bold"
      style={{
        fontFamily: "'Space Grotesk', sans-serif",
        fontSize: `${fz}px`,
        letterSpacing: "0.04em",
        lineHeight: 1,
        display: "inline-flex",
        alignItems: "baseline",
        whiteSpace: "nowrap",
      }}
    >
      <span
        style={{
          background: "linear-gradient(180deg, #FFFFFF 0%, #B6BFCB 70%, #8A95A3 100%)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          backgroundClip: "text",
        }}
      >
        STRAT
      </span>
      <span
        style={{
          color: "transparent",
          WebkitTextStroke: `${Math.max(1, fz / 28)}px ${BRAND_CYAN}`,
          textShadow: `0 0 ${fz / 10}px rgba(77,246,255,0.85), 0 0 ${fz / 4}px rgba(77,246,255,0.55), 0 0 ${fz / 2}px rgba(77,246,255,0.35)`,
          fontStyle: "italic",
          marginLeft: "0.04em",
        }}
      >
        EX
      </span>
      {trademark && (
        <span
          style={{
            fontSize: `${Math.round(fz * 0.32)}px`,
            color: BRAND_CYAN,
            marginLeft: "0.18em",
            opacity: 0.9,
          }}
        >
          ™
        </span>
      )}
    </span>
  );
}

export function StratexGlyph({ size = 38 }) {
  return (
    <svg viewBox="0 0 80 64" width={size} height={size * 0.8}
      style={{ filter: `drop-shadow(0 0 ${size / 6}px rgba(77,246,255,0.55))` }}>
      {/* roof outline */}
      <path d="M8 50 L40 12 L72 50" fill="none" stroke={BRAND_CYAN} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M16 50 L16 56 L64 56 L64 50" fill="none" stroke={BRAND_CYAN} strokeWidth="2.5" strokeLinejoin="round"/>
      {/* swoosh tail */}
      <path d="M8 50 Q4 56 12 60" fill="none" stroke={BRAND_CYAN} strokeWidth="2.5" strokeLinecap="round"/>
      {/* inner facet */}
      <path d="M30 30 L52 22 L60 36 L52 50 L34 50 Z"
        fill="rgba(255,123,0,0.18)" stroke={BRAND_AMBER} strokeWidth="1.8" strokeLinejoin="round"
        style={{ filter: `drop-shadow(0 0 ${size / 8}px rgba(255,123,0,0.7))` }}/>
      <line x1="42" y1="30" x2="46" y2="50" stroke={BRAND_AMBER} strokeWidth="1" opacity="0.7"/>
      <line x1="30" y1="40" x2="60" y2="36" stroke={BRAND_AMBER} strokeWidth="1" opacity="0.5"/>
    </svg>
  );
}

// Convenience: horizontal lock-up (glyph + wordmark side-by-side)
export function StratexLockup({ size = "md" }) {
  const glyphSize = { sm: 24, md: 36, lg: 56, xl: 84 }[size] || 36;
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: glyphSize / 5 }}>
      <StratexGlyph size={glyphSize}/>
      <StratexWordmark size={size}/>
    </span>
  );
}
