/**
 * /ceo/inventory — COMPLETE INVENTORY COST OF MATERIALS.
 *
 * Landed-cost rollup of the supplier ledger. Top: KPI strip (SKU count,
 * units, total landed value, critical reorder count). Middle: stacked
 * category-share bar. Bottom: full SKU table sorted by landed cost desc,
 * critical rows flagged with a magenta pill.
 */
import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, Briefcase, AlertTriangle } from "lucide-react";

const FN = {
  bgMain: "#080c14", bgCard: "#0f172a", bgInput: "#0b1329",
  cyan: "#06b6d4", purple: "#a855f7", green: "#10b981",
  magenta: "#f43f5e", amber: "#f59e0b",
  text: "#cbd5e1", muted: "#64748b", divider: "#1e293b", ink: "#030712",
};

// Deterministic colour pick per category — keeps the bar visually consistent
const CAT_COLORS = [FN.cyan, FN.purple, FN.green, FN.amber, FN.magenta, "#B8865B", "#7C3AED", "#3FA9F5"];

const USD = (n) => Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const USD2 = (n) => Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 2 });

export default function InventoryCost() {
  const nav = useNavigate();
  const [pkt, setPkt] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    api.get("/ceo/inventory/cost-rollup")
      .then((r) => setPkt(r.data))
      .catch((e) => setErr(e?.response?.data?.detail || "Inventory unavailable"));
  }, []);

  if (err) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: FN.bgMain }}>
      <InvCSS/>
      <div className="border max-w-md p-6" style={{ borderColor: FN.magenta, background: "rgba(244,63,94,0.06)" }}>
        <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: FN.magenta }}>// INVENTORY FAILED</div>
        <p className="text-[13px]" style={{ color: FN.text }}>{err}</p>
      </div>
    </div>
  );
  if (!pkt) return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: FN.bgMain }}>
      <InvCSS/>
      <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: FN.green }}>// CALCULATING LANDED COST…</div>
    </div>
  );

  return (
    <div className="inv-root" style={{ background: FN.bgMain, color: FN.text }} data-testid="inv-root">
      <InvCSS/>
      <header className="inv-header">
        <button onClick={() => nav("/ceo/command")} className="inv-back" data-testid="inv-back">
          <ArrowLeft size={12}/> Command Center
        </button>
        <div className="flex items-center gap-3">
          <div className="inv-icon" style={{ background: `${FN.green}14`, border: `1px solid ${FN.green}55` }}>
            <Briefcase size={18} color={FN.green}/>
          </div>
          <div>
            <h1 className="inv-title" style={{ color: FN.green }}>Complete Inventory Cost of Materials</h1>
            <p className="inv-sub">Tier-1 wholesale × stock-on-hand · Lexington Depot rollup</p>
          </div>
        </div>
        <div className="inv-asof">As of {new Date(pkt.generated_at).toLocaleString()}</div>
      </header>

      {/* KPI strip */}
      <section className="inv-kpis" data-testid="inv-kpis">
        <KCard accent={FN.cyan}    title="Distinct SKUs"      value={pkt.totals.sku_count}/>
        <KCard accent={FN.purple}  title="Units on Hand"      value={pkt.totals.total_units.toLocaleString()}/>
        <KCard accent={FN.green}   title="Total Landed Value" value={USD(pkt.totals.total_landed_value_usd)}/>
        <KCard accent={FN.magenta} title="Critical Reorders"  value={pkt.totals.critical_count}/>
      </section>

      {/* Category share bar */}
      <section className="inv-cat-card" data-testid="inv-categories">
        <h3 className="inv-card-title" style={{ color: FN.green }}>Capital Allocation by Category</h3>
        <div className="inv-cat-bar">
          {pkt.by_category.map((c, i) => (
            <div key={c.category} style={{
              width: `${c.share_pct}%`, background: CAT_COLORS[i % CAT_COLORS.length], height: "100%",
            }} title={`${c.category} — ${c.share_pct}%`}/>
          ))}
        </div>
        <div className="inv-cat-legend">
          {pkt.by_category.map((c, i) => (
            <div key={c.category} className="inv-cat-row" data-testid={`inv-cat-${c.category.toLowerCase()}`}>
              <span className="inv-cat-swatch" style={{ background: CAT_COLORS[i % CAT_COLORS.length] }}/>
              <span className="inv-cat-name">{c.category}</span>
              <span className="inv-cat-meta">{c.skus} SKUs · {c.units.toLocaleString()} units</span>
              <span className="inv-cat-val" style={{ color: CAT_COLORS[i % CAT_COLORS.length] }}>{USD(c.landed_cost_usd)}</span>
              <span className="inv-cat-pct">{c.share_pct}%</span>
            </div>
          ))}
        </div>
      </section>

      {/* Full SKU table */}
      <section className="inv-table-card">
        <h3 className="inv-card-title" style={{ color: FN.cyan }}>Per-SKU Landed Cost</h3>
        <div className="inv-table-wrap">
          <table className="inv-table" data-testid="inv-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Item</th>
                <th>Category</th>
                <th className="ceo-r">Unit Cost</th>
                <th className="ceo-r">On Hand</th>
                <th className="ceo-r">Landed</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pkt.rows.map((r) => (
                <tr key={r.sku} data-testid={`inv-row-${r.sku}`}>
                  <td className="inv-mono" style={{ color: FN.muted }}>{r.sku}</td>
                  <td>{r.name}</td>
                  <td><span className="inv-pill" style={{ borderColor: FN.divider, color: FN.muted }}>{r.category}</span></td>
                  <td className="ceo-r inv-mono">{USD2(r.unit_cost_usd)}</td>
                  <td className="ceo-r inv-mono">{r.stock_units.toLocaleString()} <span style={{ color: FN.muted }}>{r.unit_label}</span></td>
                  <td className="ceo-r inv-mono" style={{ color: FN.green, fontWeight: 700 }}>{USD(r.landed_cost_usd)}</td>
                  <td>
                    {r.is_critical && (
                      <span className="inv-pill" style={{ borderColor: FN.magenta, color: FN.magenta }}>
                        <AlertTriangle size={9}/> REORDER
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function KCard({ accent, title, value }) {
  return (
    <div className="inv-kpi" data-testid={`inv-kpi-${title.toLowerCase().replace(/\s+/g, "-")}`}
         style={{ background: FN.bgCard, border: `1px solid ${FN.divider}`, borderLeft: `4px solid ${accent}` }}>
      <div className="inv-kpi-title">{title}</div>
      <div className="inv-kpi-value" style={{ color: accent }}>{value}</div>
    </div>
  );
}

function InvCSS() {
  return (
    <style>{`
      .inv-root { min-height: 100vh; padding-bottom: 40px; }
      .inv-header {
        display: flex; align-items: center; justify-content: space-between; gap: 14px;
        padding: 16px 24px; flex-wrap: wrap;
        background: linear-gradient(135deg, ${FN.ink} 0%, ${FN.bgCard} 100%);
        border-bottom: 1px solid ${FN.divider};
      }
      .inv-back {
        font-family: 'JetBrains Mono', monospace; font-size: 9.5px;
        letter-spacing: 0.25em; text-transform: uppercase; font-weight: 700;
        background: transparent; border: 1px solid ${FN.divider};
        color: ${FN.muted}; padding: 6px 12px; border-radius: 2px;
        display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
      }
      .inv-back:hover { border-color: ${FN.cyan}; color: ${FN.cyan}; }
      .inv-icon { width: 38px; height: 38px; border-radius: 4px;
                  display: flex; align-items: center; justify-content: center; }
      .inv-title { font-family: 'JetBrains Mono', monospace;
                   font-size: 15px; font-weight: 800;
                   text-transform: uppercase; letter-spacing: 0.18em; }
      .inv-sub { font-size: 10px; color: ${FN.muted}; margin-top: 2px; }
      .inv-asof { font-family: 'JetBrains Mono', monospace;
                   font-size: 9.5px; color: ${FN.muted};
                   text-transform: uppercase; letter-spacing: 0.2em; }

      .inv-kpis { display: grid; grid-template-columns: repeat(4, 1fr);
                   gap: 14px; padding: 20px 24px; }
      .inv-kpi { padding: 14px 16px; border-radius: 3px; }
      .inv-kpi-title { font-family: 'JetBrains Mono', monospace;
                       font-size: 9px; color: ${FN.muted};
                       text-transform: uppercase; letter-spacing: 0.3em; }
      .inv-kpi-value { font-family: 'JetBrains Mono', monospace;
                       font-size: 22px; font-weight: 800; margin-top: 6px; }

      .inv-cat-card, .inv-table-card {
        background: ${FN.bgCard}; border: 1px solid ${FN.divider};
        border-radius: 3px; padding: 18px 22px;
        margin: 0 24px 18px 24px;
      }
      .inv-card-title { font-family: 'JetBrains Mono', monospace;
                        font-size: 11px; font-weight: 700;
                        text-transform: uppercase; letter-spacing: 0.2em;
                        margin-bottom: 14px; }
      .inv-cat-bar { display: flex; height: 14px; border-radius: 2px;
                     overflow: hidden; background: ${FN.bgInput};
                     border: 1px solid ${FN.divider}; }
      .inv-cat-legend { display: flex; flex-direction: column; gap: 6px; margin-top: 14px; }
      .inv-cat-row { display: grid;
                      grid-template-columns: 12px 1fr 1.2fr auto auto;
                      gap: 12px; align-items: center;
                      padding: 6px 8px; border-radius: 2px;
                      background: ${FN.bgInput}; border: 1px solid ${FN.divider}; }
      .inv-cat-swatch { width: 12px; height: 12px; border-radius: 2px; }
      .inv-cat-name { font-size: 12px; color: ${FN.text}; font-weight: 700; }
      .inv-cat-meta { font-family: 'JetBrains Mono', monospace;
                       font-size: 10px; color: ${FN.muted}; }
      .inv-cat-val { font-family: 'JetBrains Mono', monospace;
                      font-size: 13px; font-weight: 800; }
      .inv-cat-pct { font-family: 'JetBrains Mono', monospace;
                      font-size: 11px; color: ${FN.muted}; min-width: 50px; text-align: right; }

      .inv-table-wrap { overflow-x: auto; }
      .inv-table { width: 100%; border-collapse: collapse;
                    font-size: 11.5px; min-width: 720px; }
      .inv-table th { font-family: 'JetBrains Mono', monospace;
                      font-size: 9px; color: ${FN.muted};
                      text-transform: uppercase; letter-spacing: 0.22em;
                      text-align: left; padding: 8px;
                      border-bottom: 1px solid ${FN.divider}; }
      .inv-table td { padding: 8px;
                      border-bottom: 1px solid ${FN.divider}; }
      .inv-table .ceo-r { text-align: right; }
      .inv-mono { font-family: 'JetBrains Mono', monospace; }
      .inv-pill {
        display: inline-flex; align-items: center; gap: 4px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 8.5px; padding: 3px 7px;
        border: 1px solid; border-radius: 2px;
        text-transform: uppercase; letter-spacing: 0.2em; font-weight: 700;
      }

      @media (max-width: 768px) {
        .inv-kpis { grid-template-columns: 1fr 1fr; padding: 14px; gap: 10px; }
        .inv-cat-card, .inv-table-card { margin: 0 12px 14px 12px; padding: 14px; }
        .inv-cat-row { grid-template-columns: 12px 1fr auto; }
        .inv-cat-meta, .inv-cat-pct { display: none; }
      }
    `}</style>
  );
}
