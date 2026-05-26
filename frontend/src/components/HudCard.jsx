import React from "react";

export const HudCard = ({ children, className = "", alert = false, scanline = false, ...rest }) => (
  <div
    className={`hud-card ${alert ? "hud-card-alert" : ""} ${className}`}
    {...rest}
  >
    <span className="corner-bl" />
    <span className="corner-br" />
    {scanline && <div className="scanline" />}
    {children}
  </div>
);

export const DataReadout = ({ label, value, accent = "teal", testid }) => {
  const color = accent === "orange" ? "text-plasma glow-orange" : accent === "volt" ? "text-volt glow-volt" : "text-teal glow-teal";
  return (
    <div data-testid={testid} className="flex flex-col gap-1">
      <span className="hud-label">{label}</span>
      <span className={`font-mono font-bold text-xl ${color}`}>{value}</span>
    </div>
  );
};

export const SectionTitle = ({ eyebrow, title, accent = "teal" }) => (
  <div className="mb-6 min-w-0">
    {eyebrow && (
      <div className={`font-mono text-[11px] tracking-[0.32em] uppercase mb-2 ${accent === "orange" ? "text-plasma" : "text-teal"}`}>
        {eyebrow}
      </div>
    )}
    <h2
      className="font-display text-[1.5rem] sm:text-3xl md:text-4xl uppercase tracking-[0.04em] sm:tracking-[0.12em] md:tracking-[0.16em] text-silver"
      style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}
    >
      {title}
    </h2>
    <div className="hud-divider mt-3" />
  </div>
);
