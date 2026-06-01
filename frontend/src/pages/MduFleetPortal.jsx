/**
 * MduFleetPortal — v4.0-PROD Mobile Drone Unit Capital Allocation Portal.
 *
 * Reads the immutable seal at /app/frontend/src/config/mdu_fleet_ledger.json,
 * renders per-unit line items, computes subtotals, grand total, and a
 * personnel + cloud overlay column. Frosted glass cards, brand palette.
 */
import React, { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, ShieldCheck, Truck, Cloud, HardDrive } from "lucide-react";
import ledger from "@/config/mdu_fleet_ledger.json";

const C = { cyan: "#00F0FF", amber: "#FF9900", green: "#00FF66",
            text: "#E2E8F0", muted: "#64748B", ink: "#06080B" };

const USD = (n) => Number(n || 0).toLocaleString("en-US",
  { style: "currency", currency: "USD", maximumFractionDigits: 2 });

const prettify = (k) =>
  k.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

function LedgerColumn({ title, icon: Icon, accent, entries, testid }) {
  const total = useMemo(
    () => Object.values(entries).reduce((s, v) => s + (Number(v) || 0), 0),
    [entries],
  );
  return (
    <section data-testid={testid}
      style={{
        background: "rgba(11, 16, 28, 0.55)",
        backdropFilter: "blur(20px) saturate(150%)",
        border: `1px solid ${accent}55`,
        borderRadius: 12, padding: "18px 20px",
        boxShadow: `0 28px 60px -28px ${accent}88`,
      }}>
      <header className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon size={16} color={accent}/>
          <h2 style={{ color: accent, fontFamily: "'JetBrains Mono', monospace",
                       fontSize: 11, letterSpacing: "0.22em", textTransform: "uppercase",
                       margin: 0 }}>
            {title}
          </h2>
        </div>
        <span style={{ color: accent, fontFamily: "'JetBrains Mono', monospace",
                       fontSize: 10, letterSpacing: "0.18em" }}>
          {Object.keys(entries).length} LINES
        </span>
      </header>

      <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
        {Object.entries(entries).map(([k, v]) => (
          <li key={k}
              data-testid={`ledger-line-${k}`}
              style={{
                display: "flex", justifyContent: "space-between", alignItems: "baseline",
                padding: "8px 0",
                borderBottom: "1px dashed rgba(100,116,139,0.18)",
                fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                color: C.text,
              }}>
            <span style={{ flex: 1, paddingRight: 12 }}>{prettify(k)}</span>
            <strong style={{ color: accent }}>{USD(v)}</strong>
          </li>
        ))}
      </ol>

      <div style={{
        marginTop: 12, paddingTop: 10,
        borderTop: `1px solid ${accent}55`,
        display: "flex", justifyContent: "space-between",
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 12, letterSpacing: "0.16em", textTransform: "uppercase",
      }}>
        <span style={{ color: C.muted }}>Subtotal</span>
        <strong style={{ color: accent, fontSize: 14 }}>{USD(total)}</strong>
      </div>
    </section>
  );
}

export default function MduFleetPortal() {
  const nav = useNavigate();
  const grand = useMemo(() => {
    const total =
      Object.values(ledger.personnel_and_cloud_infrastructure || {}).reduce((s, v) => s + Number(v || 0), 0) +
      Object.values(ledger.mobile_drone_unit_1_master_command   || {}).reduce((s, v) => s + Number(v || 0), 0) +
      Object.values(ledger.mobile_drone_unit_2_satellite_extension || {}).reduce((s, v) => s + Number(v || 0), 0);
    return total;
  }, []);

  return (
    <div data-testid="mdu-fleet-portal-root"
         style={{ minHeight: "100vh", background: C.ink, color: C.text,
                  padding: "32px 24px 140px", position: "relative" }}>
      <style>{`
        @keyframes mfp-stream {
          0%   { transform: translateX(-100%); opacity: 0; }
          100% { transform: translateX(0%);   opacity: 0.45; }
        }
      `}</style>

      <div style={{ maxWidth: 1500, margin: "0 auto" }}>
        <button onClick={() => nav(-1)}
                data-testid="mfp-back"
                style={{
                  display: "inline-flex", alignItems: "center", gap: 6,
                  background: "transparent", border: `1px solid ${C.cyan}55`,
                  color: C.cyan, padding: "5px 11px", borderRadius: 5,
                  fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                  letterSpacing: "0.2em", textTransform: "uppercase",
                  cursor: "pointer",
                }}>
          <ArrowLeft size={12}/> Return
        </button>

        <header style={{ marginTop: 18, marginBottom: 22 }}>
          <div style={{ color: C.cyan, fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, letterSpacing: "0.32em", textTransform: "uppercase" }}>
            // STRATEX VISION · MDU FLEET MANAGEMENT PORTAL · {ledger.version}
          </div>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif",
                       fontSize: 36, lineHeight: 1.05,
                       letterSpacing: "0.08em", textTransform: "uppercase",
                       margin: "6px 0 4px" }}>
            Capital Allocation Ledger
          </h1>
          <p style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, letterSpacing: "0.12em" }}>
            <ShieldCheck size={11} style={{ display: "inline", verticalAlign: -1, marginRight: 4 }}/>
            Sealed {ledger.sealed_at_iso} · IMMUTABLE · Mobile Drone Unit deployment economics
          </p>
        </header>

        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(360px, 1fr))",
          gap: 18,
        }}>
          <LedgerColumn title="Personnel & Cloud Infra" icon={Cloud} accent={C.amber}
                        entries={ledger.personnel_and_cloud_infrastructure}
                        testid="ledger-col-personnel"/>
          <LedgerColumn title="MDU-1 · Master Command"  icon={Truck} accent={C.cyan}
                        entries={ledger.mobile_drone_unit_1_master_command}
                        testid="ledger-col-mdu1"/>
          <LedgerColumn title="MDU-2 · Satellite Ext."  icon={HardDrive} accent={C.green}
                        entries={ledger.mobile_drone_unit_2_satellite_extension}
                        testid="ledger-col-mdu2"/>
        </div>

        <section data-testid="ledger-grand-total"
          style={{
            marginTop: 22,
            background: "rgba(11, 16, 28, 0.65)",
            backdropFilter: "blur(22px) saturate(150%)",
            border: `1px solid ${C.cyan}88`,
            borderRadius: 14, padding: "22px 26px",
            boxShadow: `0 34px 90px -30px ${C.cyan}cc`,
            display: "flex", flexWrap: "wrap", alignItems: "center",
            justifyContent: "space-between", gap: 14,
          }}>
          <div>
            <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 10, letterSpacing: "0.28em", textTransform: "uppercase" }}>
              Grand Total · Sealed Capital Allocation
            </div>
            <div style={{ color: C.cyan, fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 36, fontWeight: 800, letterSpacing: "0.04em",
                          textShadow: `0 0 18px ${C.cyan}66`, marginTop: 4 }}
                 data-testid="ledger-grand-amount">
              {USD(grand)}
            </div>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ color: C.green, fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 11, letterSpacing: "0.22em", textTransform: "uppercase" }}>
              ◉ Ledger Channel · Fernet/AES-256
            </div>
            <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                          fontSize: 9, letterSpacing: "0.18em", marginTop: 4 }}>
              MDU-1 + MDU-2 + Personnel/Cloud
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
