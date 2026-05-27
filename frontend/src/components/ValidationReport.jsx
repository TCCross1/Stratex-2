import React from "react";
import { Shield, CheckCircle2, AlertTriangle } from "lucide-react";

/**
 * ValidationReport — pre-render expert-panel quality gate readout.
 *
 * Renders the 6-gate report from the backend's `validate_topology()` so the
 * contractor + adjuster can see proof that every digital twin passed code +
 * craft rules from four expert agents BEFORE the 3D model was drawn.
 *
 * Props:
 *   - validation: the `validation` object from /api/public/demo-topology (or
 *                 any topology endpoint). Shape: { gates[], passed, total,
 *                 all_pass, score_pct }
 *   - compact: if true, render as a 3-line strip instead of a full panel.
 */
export default function ValidationReport({ validation, compact = false }) {
  if (!validation || !validation.gates) return null;
  const { gates, passed, total, all_pass, score_pct } = validation;

  if (compact) {
    return (
      <div
        className="flex items-center gap-3 px-4 py-2 border bg-[#0B0F19] font-mono text-[10px] tracking-widest uppercase"
        style={{ borderColor: all_pass ? "rgba(0,240,255,0.45)" : "rgba(255,170,0,0.5)" }}
        data-testid="validation-report-compact"
      >
        {all_pass ? (
          <Shield size={14} className="text-teal" style={{ filter: "drop-shadow(0 0 4px rgba(0,240,255,0.6))" }} />
        ) : (
          <AlertTriangle size={14} className="text-plasma" />
        )}
        <span className={all_pass ? "text-teal" : "text-plasma"}>
          Expert Panel: {passed}/{total} gates ({score_pct}%)
        </span>
      </div>
    );
  }

  return (
    <div
      className="border bg-[#0B0F19]"
      style={{ borderColor: all_pass ? "rgba(0,240,255,0.45)" : "rgba(255,170,0,0.5)" }}
      data-testid="validation-report"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-[#00F0FF]/20">
        <div className="flex items-center gap-3">
          <Shield
            size={18}
            className={all_pass ? "text-teal" : "text-plasma"}
            style={{ filter: all_pass ? "drop-shadow(0 0 6px rgba(0,240,255,0.6))" : "drop-shadow(0 0 6px rgba(255,85,0,0.6))" }}
          />
          <span className="font-mono text-[11px] tracking-widest uppercase text-silver">
            Multi-Agent Expert Panel
          </span>
        </div>
        <span
          className={`font-mono text-[11px] tracking-widest uppercase ${all_pass ? "text-teal" : "text-plasma"}`}
          data-testid="validation-score"
        >
          {passed}/{total} • {score_pct}%
        </span>
      </div>
      <ul className="divide-y divide-[#00F0FF]/10">
        {gates.map((g) => (
          <li key={g.id} className="px-4 py-2.5 flex items-start gap-3" data-testid={`validation-gate-${g.id}`}>
            {g.pass ? (
              <CheckCircle2 size={14} className="text-teal mt-[2px] shrink-0" />
            ) : (
              <AlertTriangle size={14} className="text-plasma mt-[2px] shrink-0" />
            )}
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <span className="font-mono text-[10px] tracking-widest uppercase text-silver">{g.label}</span>
                <span className="font-mono text-[9px] tracking-widest uppercase text-muted-hud whitespace-nowrap">
                  {g.agent} · {g.rule_ref}
                </span>
              </div>
              <p className="text-[11px] text-muted-hud font-body mt-0.5 leading-snug">{g.message}</p>
            </div>
          </li>
        ))}
      </ul>
      <div className="px-4 py-2 border-t border-[#00F0FF]/20 font-mono text-[9px] tracking-widest uppercase text-muted-hud">
        Pre-render quality gate · per /memory/expert_panel_review.md
      </div>
    </div>
  );
}
