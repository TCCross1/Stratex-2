import React from "react";

/* STRATEX CORE brand assets (Directive 009).
   One master SVG per variant lives at /brand/*.svg. Do not redraw the logo.
   Emblem-only + horizontal + full — respect proportions, no cropping. */

export const BRAND = {
  emblem: "/brand/stratex-emblem.svg",       // compact hexagon (nav/tab bars, favicons)
  horizontal: "/brand/stratex-core-logo.png", // full brand for header/rail/hero
  full: "/brand/stratex-core-logo.png",     // approved master image
  icon: "/brand/stratex-icon.svg",
};

/**
 * Approved brand mark.
 * variant: "emblem" | "horizontal" | "full" | "icon"
 * ariaHidden: true when adjacent visible text repeats the brand name.
 */
export default function BrandLogo({
  variant = "horizontal",
  height,
  width,
  className = "",
  ariaLabel,
  style,
  onClick,
  loading = "eager",
  "data-testid": testId,
}) {
  const src = BRAND[variant] || BRAND.horizontal;
  const label = ariaLabel ?? (variant === "emblem" ? "Stratex Core" : "Stratex Core");
  return (
    <img
      src={src}
      alt={label}
      className={className}
      loading={loading}
      onClick={onClick}
      data-testid={testId || `brand-logo-${variant}`}
      style={{ display: "block", height, width, userSelect: "none", ...style }}
      draggable={false}
    />
  );
}
