import React, { useEffect, useState } from "react";
import { Rocket, Clock } from "lucide-react";

/**
 * LaunchCountdownBadge — pulses next to a homeowner's name in the pipeline once they've
 * confirmed a reschedule window via SMS reply. Green when launch is days away, orange
 * when within 24h, red when within 1h or in the past ("READY TO LAUNCH").
 *
 * Props:
 *   scheduledAt: ISO-ish string from job.scheduled_launch_at (e.g. "2026-05-27T21:00")
 *   compact?: boolean — when true, renders inline without the leading icon (table cells)
 */
export default function LaunchCountdownBadge({ scheduledAt, compact = false }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!scheduledAt) return;
    const id = setInterval(() => setNow(Date.now()), 30000); // tick every 30s
    return () => clearInterval(id);
  }, [scheduledAt]);

  if (!scheduledAt) return null;

  // The ISO from open-meteo is local-zone naïve (e.g. "2026-05-27T21:00"). Treating it as
  // local-time-without-offset is the closest semantic — Date.parse will assume local.
  const target = new Date(scheduledAt).getTime();
  if (Number.isNaN(target)) return null;
  const deltaMs = target - now;
  const past = deltaMs <= 0;
  const minutes = Math.floor(Math.abs(deltaMs) / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  let tier;            // "ready" | "imminent" | "soon" | "future"
  let label;
  if (past || hours < 1) {
    tier = "ready";
    label = past ? "READY TO LAUNCH" : `LAUNCHES IN ${minutes}M`;
  } else if (hours < 24) {
    tier = "imminent";
    label = `LAUNCHES IN ${hours}H ${minutes % 60}M`;
  } else if (days < 7) {
    tier = "soon";
    label = `LAUNCHES IN ${days}D ${hours % 24}H`;
  } else {
    tier = "future";
    label = `LAUNCHES IN ${days}D`;
  }

  const style = {
    ready:    { color: "#FF3939", border: "rgba(255,57,57,0.6)",  glow: "rgba(255,57,57,0.55)", bg: "rgba(255,57,57,0.10)" },
    imminent: { color: "#FF8A1F", border: "rgba(255,138,31,0.6)", glow: "rgba(255,138,31,0.45)", bg: "rgba(255,138,31,0.10)" },
    soon:     { color: "#39FF14", border: "rgba(57,255,20,0.55)", glow: "rgba(57,255,20,0.35)", bg: "rgba(57,255,20,0.08)" },
    future:   { color: "#00F0FF", border: "rgba(0,240,255,0.45)", glow: "rgba(0,240,255,0.30)", bg: "rgba(0,240,255,0.06)" },
  }[tier];

  const pulse = tier === "ready" || tier === "imminent";
  const Icon = tier === "ready" ? Rocket : Clock;

  return (
    <span
      data-testid="launch-countdown-badge"
      data-tier={tier}
      className={`inline-flex items-center gap-1 font-mono text-[9px] uppercase tracking-widest px-1.5 py-0.5 ml-2 ${pulse ? "pulse-alert" : ""}`}
      style={{
        color: style.color,
        background: style.bg,
        border: `1px solid ${style.border}`,
        boxShadow: `0 0 8px ${style.glow}, inset 0 0 4px ${style.glow}`,
        textShadow: `0 0 5px ${style.glow}`,
        whiteSpace: "nowrap",
        verticalAlign: compact ? "middle" : "baseline",
      }}
      title={`Locked in via homeowner reply · target ${scheduledAt}`}
    >
      <Icon size={9}/>
      {label}
    </span>
  );
}
