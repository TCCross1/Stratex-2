/**
 * STRATEX™ Pilot App — shared Future-Noire shell.
 *
 * Provides the dark, neon-grid background + STRATEX header used across every
 * pilot tablet screen. Pure addition (preservation lock).
 */
import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { Plane, ChevronLeft, LogOut } from "lucide-react";

export const FN_BG = "radial-gradient(ellipse at top, #0a1626 0%, #050810 70%, #02050a 100%)";
export const FN_TEAL = "#00E5FF";
export const FN_GREEN = "#00FF9C";
export const FN_AMBER = "#FFB020";
export const FN_RED = "#FF2D78";
export const FN_INK = "#E2E8F0";
export const FN_DIM = "#7C8A9E";

export function PilotShell({ children, title, subtitle, back, rightSlot }) {
  const nav = useNavigate();
  const { logout } = useAuth();
  return (
    <div data-testid="pilot-shell" style={{
      minHeight: "100vh",
      background: FN_BG,
      color: FN_INK,
      position: "relative",
      overflow: "hidden",
    }}>
      {/* neon grid texture */}
      <div aria-hidden style={{
        position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.16,
        backgroundImage:
          "linear-gradient(rgba(34,211,238,0.18) 1px, transparent 1px)," +
          "linear-gradient(90deg, rgba(34,211,238,0.18) 1px, transparent 1px)",
        backgroundSize: "48px 48px",
        maskImage: "radial-gradient(ellipse at center, rgba(0,0,0,1) 30%, rgba(0,0,0,0) 80%)",
      }}/>
      {/* corner glow */}
      <div aria-hidden style={{
        position: "absolute", top: -180, right: -200, width: 520, height: 520,
        borderRadius: "50%",
        background: "radial-gradient(circle, rgba(34,211,238,0.18) 0%, rgba(0,0,0,0) 60%)",
        pointerEvents: "none",
      }}/>

      <header style={{
        position: "relative", zIndex: 5, padding: "18px 26px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        borderBottom: `1px solid ${FN_TEAL}22`,
        background: "linear-gradient(180deg, rgba(8,15,30,0.92), rgba(8,15,30,0.55))",
        backdropFilter: "blur(12px)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {back && (
            <button onClick={() => nav(back)} data-testid="pilot-back-btn"
                    style={{ background: "transparent", border: `1px solid ${FN_TEAL}55`,
                             color: FN_TEAL, borderRadius: 4, padding: "4px 8px",
                             cursor: "pointer", fontFamily: "monospace", fontSize: 11 }}>
              <ChevronLeft size={12} style={{ verticalAlign: "middle", marginRight: 4 }}/>BACK
            </button>
          )}
          <Plane size={20} color={FN_TEAL}/>
          <div>
            <div style={{ fontFamily: "monospace", fontSize: 10, letterSpacing: "0.32em",
                          color: FN_TEAL, textTransform: "uppercase" }}>
              // STRATEX // PILOT TABLET
            </div>
            <div style={{ fontWeight: 700, fontSize: 18, letterSpacing: 0.4, marginTop: 2 }}>
              {title}
            </div>
            {subtitle && (
              <div style={{ color: FN_DIM, fontSize: 11, fontFamily: "monospace",
                            letterSpacing: "0.16em", textTransform: "uppercase", marginTop: 2 }}>
                {subtitle}
              </div>
            )}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {rightSlot}
          <button onClick={() => { logout(); nav("/auth"); }} data-testid="pilot-logout"
                  style={{ background: "transparent", border: "1px solid #334155",
                           color: FN_DIM, borderRadius: 4, padding: "5px 12px",
                           cursor: "pointer", fontFamily: "monospace", fontSize: 10,
                           letterSpacing: "0.18em", textTransform: "uppercase" }}>
            <LogOut size={10} style={{ verticalAlign: "middle", marginRight: 4 }}/>End shift
          </button>
        </div>
      </header>

      <main style={{ position: "relative", zIndex: 4, padding: "24px 26px 60px" }}>
        {children}
      </main>
    </div>
  );
}

export function NeonBadge({ ok, label, value }) {
  const color = ok ? FN_GREEN : FN_AMBER;
  return (
    <span data-testid={`neon-badge-${label}`} style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "3px 10px", borderRadius: 999,
      border: `1px solid ${color}55`,
      background: `${color}10`, color,
      fontFamily: "monospace", fontSize: 10,
      letterSpacing: "0.2em", textTransform: "uppercase",
    }}>
      <span style={{
        width: 7, height: 7, borderRadius: "50%", background: color,
        boxShadow: `0 0 8px ${color}`,
      }}/>
      {value || label}
    </span>
  );
}
