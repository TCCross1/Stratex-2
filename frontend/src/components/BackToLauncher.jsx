// STRATEX™ — Universal "Back to Launcher" pill.
//
// Floats bottom-left on every page that isn't the launcher itself.
// One tap returns the Commander to `/` (the App Launcher splash).

import React from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { ArrowLeft, Home } from "lucide-react";

export default function BackToLauncher() {
  const loc = useLocation();
  const nav = useNavigate();

  // Don't show on the launcher itself.
  if (loc.pathname === "/") return null;

  return (
    <button
      data-testid="back-to-launcher"
      onClick={() => nav("/")}
      title="Back to App Launcher"
      className="fixed bottom-5 left-5 z-50 rounded-full pl-3 pr-4 py-2.5 flex items-center gap-2 transition hover:scale-105"
      style={{
        background: "linear-gradient(135deg, rgba(255,45,45,0.18) 0%, rgba(15,22,34,0.92) 100%)",
        border: "1.5px solid #FF5555",
        boxShadow:
          "0 0 0 1px rgba(255,45,45,0.35), " +
          "0 0 22px rgba(255,45,45,0.40), " +
          "inset 0 0 14px rgba(255,45,45,0.12)",
        backdropFilter: "blur(8px)",
        fontFamily: "'Sora', sans-serif",
      }}>
      <span className="grid place-items-center rounded-full shrink-0"
            style={{ width: 28, height: 28, background: "#FF2D2D",
                     color: "#fff", boxShadow: "0 0 8px rgba(255,45,45,0.55)" }}>
        <ArrowLeft size={13} strokeWidth={3}/>
      </span>
      <span className="text-left">
        <span className="block font-mono text-[8px] tracking-[0.28em] uppercase text-rose-300">// GO BACK</span>
        <span className="block font-display text-[11px] uppercase tracking-[0.06em] text-white flex items-center gap-1">
          <Home size={11}/> App Launcher
        </span>
      </span>
    </button>
  );
}
