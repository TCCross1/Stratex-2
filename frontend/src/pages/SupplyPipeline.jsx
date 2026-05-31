/**
 * /ceo/leads · /ceo/orders/build · /ceo/orders/ready · /ceo/orders/shipped
 *
 * Single page that renders ANY of the 4 pipeline statuses based on its `status`
 * prop. Reused so the 4 bottom-dock destinations share zero duplication.
 *
 *   lead      → "NEW CLIENTS · SALES"      (cyan)
 *   to_build  → "ORDERS TO BUILD"           (purple)
 *   ready     → "ORDERS READY"              (cyan)
 *   shipped   → "ORDERS SHIPPED"            (purple)
 *
 * Each row exposes an "Advance →" CTA (POST /api/ceo/orders/{id}/advance) that
 * promotes the order to the next status. Pipeline counts in the top strip
 * stay in sync after every advance.
 */
import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import {
  ArrowLeft, ArrowRight, Users, Package, Truck, Send, Phone, MapPin, Loader2,
} from "lucide-react";

const FN = {
  bgMain: "#080c14", bgCard: "#0f172a", bgInput: "#0b1329",
  cyan: "#06b6d4", purple: "#a855f7", green: "#10b981",
  magenta: "#f43f5e", amber: "#f59e0b",
  text: "#cbd5e1", muted: "#64748b", divider: "#1e293b", ink: "#030712",
};

const STATUS_META = {
  lead:     { label: "New Clients · Sales", color: FN.cyan,    Icon: Users,   blurb: "Inbound leads from the contractor portal · ready to quote." },
  to_build: { label: "Orders to Build",     color: FN.purple,  Icon: Package, blurb: "Materials reserved · production queued at the depot." },
  ready:    { label: "Orders Ready",        color: FN.cyan,    Icon: Truck,   blurb: "Staged at the loading dock · awaiting dispatch." },
  shipped:  { label: "Orders Shipped",      color: FN.purple,  Icon: Send,    blurb: "On-route · last-mile tracking active." },
};

const USD = (n) => Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });

export default function SupplyPipeline({ status }) {
  const nav = useNavigate();
  const [pkt, setPkt] = useState(null);
  const [err, setErr] = useState("");
  const [busyRow, setBusyRow] = useState(null);

  const refresh = async () => {
    try {
      const r = await api.get(`/ceo/orders?status=${encodeURIComponent(status)}`);
      setPkt(r.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || "Pipeline unavailable");
    }
  };

  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [status]);

  const meta = STATUS_META[status];

  const advance = async (orderId) => {
    setBusyRow(orderId);
    try {
      await api.post(`/ceo/orders/${orderId}/advance`, {});
      await refresh();
    } finally {
      setBusyRow(null);
    }
  };

  if (err) return <FailPanel err={err} onBack={() => nav("/ceo/command")}/>;
  if (!pkt) return <LoadingPanel meta={meta}/>;

  const next = ({ lead: "to_build", to_build: "ready", ready: "shipped" })[status];

  return (
    <div className="sp-root" style={{ background: FN.bgMain, color: FN.text }} data-testid="sp-root">
      <SupplyPipelineCSS/>
      {/* Header bar */}
      <header className="sp-header">
        <button onClick={() => nav("/ceo/command")} className="sp-back" data-testid="sp-back">
          <ArrowLeft size={12}/> Command Center
        </button>
        <div className="flex items-center gap-3">
          <div className="sp-header-icon" style={{ background: `${meta.color}14`, border: `1px solid ${meta.color}55` }}>
            <meta.Icon size={18} color={meta.color}/>
          </div>
          <div>
            <h1 className="sp-title" style={{ color: meta.color }}>{meta.label}</h1>
            <p className="sp-sub">{meta.blurb}</p>
          </div>
        </div>
        <div className="sp-totals" data-testid="sp-totals">
          <span><strong>{pkt.totals.row_count}</strong> rows</span>
          <span><strong>{pkt.totals.total_units}</strong> units</span>
          <span style={{ color: FN.green }}><strong>{USD(pkt.totals.total_value_usd)}</strong> value</span>
        </div>
      </header>

      {/* Pipeline strip */}
      <nav className="sp-strip">
        {[
          { key: "lead",     to: "/ceo/leads",            label: "Leads" },
          { key: "to_build", to: "/ceo/orders/build",     label: "To Build" },
          { key: "ready",    to: "/ceo/orders/ready",     label: "Ready" },
          { key: "shipped",  to: "/ceo/orders/shipped",   label: "Shipped" },
        ].map((s, i, arr) => (
          <React.Fragment key={s.key}>
            <button onClick={() => nav(s.to)}
                    className={`sp-stage ${status === s.key ? "active" : ""}`}
                    data-testid={`sp-stage-${s.key}`}
                    style={{ borderColor: status === s.key ? STATUS_META[s.key].color : FN.divider,
                             color: status === s.key ? STATUS_META[s.key].color : FN.muted }}>
              <span className="sp-stage-count">{pkt.counts_by_status[s.key] ?? 0}</span>
              <span className="sp-stage-label">{s.label}</span>
            </button>
            {i < arr.length - 1 && <ArrowRight size={14} color={FN.muted}/>}
          </React.Fragment>
        ))}
      </nav>

      {/* Order rows */}
      <main className="sp-main">
        {pkt.rows.length === 0 && (
          <div className="sp-empty" data-testid="sp-empty">
            // No orders in this stage right now
          </div>
        )}
        {pkt.rows.map((o) => (
          <article key={o.id} className="sp-card" data-testid={`sp-order-${o.order_code}`}
                   style={{ borderLeft: `4px solid ${meta.color}` }}>
            <div className="sp-card-head">
              <div>
                <div className="sp-code" style={{ color: meta.color }}>{o.order_code}</div>
                <div className="sp-contractor">{o.contractor_company}</div>
                <div className="sp-meta">
                  <span><Phone size={10}/> {o.contractor_contact} · {o.contractor_phone}</span>
                  <span><MapPin size={10}/> {o.site_address}</span>
                </div>
              </div>
              <div className="sp-card-actions">
                <div className="sp-card-total">
                  <div className="sp-card-total-lbl">Order Total</div>
                  <div className="sp-card-total-val" style={{ color: FN.green }}>{USD(o.total_usd)}</div>
                  <div className="sp-card-total-sub">incl. ${o.tax_usd?.toFixed?.(2) ?? "0.00"} tax</div>
                </div>
                {next ? (
                  <button onClick={() => advance(o.id)} disabled={busyRow === o.id}
                          className="sp-advance" data-testid={`sp-advance-${o.order_code}`}
                          style={{ background: meta.color, color: FN.ink }}>
                    {busyRow === o.id ? <Loader2 size={12} className="sp-spin"/> : <ArrowRight size={12}/>}
                    Advance → {STATUS_META[next].label.split(" ")[0]}
                  </button>
                ) : (
                  <span className="sp-terminal">Shipped · terminal</span>
                )}
              </div>
            </div>
            <table className="sp-line-table">
              <thead>
                <tr>
                  <th>SKU</th>
                  <th>Item</th>
                  <th className="ceo-r">Qty</th>
                  <th className="ceo-r">Unit</th>
                  <th className="ceo-r">Line Total</th>
                </tr>
              </thead>
              <tbody>
                {o.line_items.map((li, i) => (
                  <tr key={i}>
                    <td className="sp-mono" style={{ color: FN.muted }}>{li.sku}</td>
                    <td>{li.name}</td>
                    <td className="ceo-r sp-mono">{li.quantity} <span style={{ color: FN.muted }}>{li.unit_label}</span></td>
                    <td className="ceo-r sp-mono" style={{ color: FN.muted }}>{USD(li.unit_price_usd)}</td>
                    <td className="ceo-r sp-mono" style={{ color: FN.text }}>{USD(li.line_total_usd)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
      </main>
    </div>
  );
}

function LoadingPanel({ meta }) {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: FN.bgMain }}>
      <SupplyPipelineCSS/>
      <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: meta?.color || FN.cyan }}>
        // LOADING {meta?.label?.toUpperCase() || "PIPELINE"}…
      </div>
    </div>
  );
}

function FailPanel({ err, onBack }) {
  return (
    <div className="min-h-screen flex items-center justify-center" style={{ background: FN.bgMain }}>
      <SupplyPipelineCSS/>
      <div className="border max-w-md p-6" style={{ borderColor: FN.magenta, background: "rgba(244,63,94,0.06)" }}>
        <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: FN.magenta }}>// PIPELINE FAILED</div>
        <p className="text-[13px]" style={{ color: FN.text }}>{err}</p>
        <button onClick={onBack} className="mt-4 font-mono text-[10px] tracking-widest uppercase px-3 py-1.5"
                style={{ border: `1px solid ${FN.cyan}`, color: FN.cyan }}>
          ← Command Center
        </button>
      </div>
    </div>
  );
}

function SupplyPipelineCSS() {
  return (
    <style>{`
      .sp-root { min-height: 100vh; padding-bottom: 40px; }
      .sp-header {
        display: flex; align-items: center; justify-content: space-between;
        gap: 14px;
        padding: 16px 24px;
        background: linear-gradient(135deg, ${FN.ink} 0%, ${FN.bgCard} 100%);
        border-bottom: 1px solid ${FN.divider};
        flex-wrap: wrap;
      }
      .sp-back {
        font-family: 'JetBrains Mono', monospace; font-size: 9.5px;
        letter-spacing: 0.25em; text-transform: uppercase; font-weight: 700;
        background: transparent; border: 1px solid ${FN.divider};
        color: ${FN.muted}; padding: 6px 12px; border-radius: 2px;
        display: inline-flex; align-items: center; gap: 6px; cursor: pointer;
        transition: all 0.2s;
      }
      .sp-back:hover { border-color: ${FN.cyan}; color: ${FN.cyan}; }
      .sp-header-icon {
        width: 38px; height: 38px; border-radius: 4px;
        display: flex; align-items: center; justify-content: center;
      }
      .sp-title {
        font-family: 'JetBrains Mono', monospace;
        font-size: 15px; font-weight: 800;
        text-transform: uppercase; letter-spacing: 0.18em;
      }
      .sp-sub { font-size: 10px; color: ${FN.muted}; margin-top: 2px; max-width: 480px; }
      .sp-totals {
        display: flex; gap: 16px;
        font-family: 'JetBrains Mono', monospace;
        font-size: 11px; color: ${FN.text};
        text-transform: uppercase; letter-spacing: 0.15em;
      }
      .sp-totals strong { font-weight: 800; color: #fff; }

      .sp-strip {
        display: flex; align-items: center; gap: 8px;
        padding: 14px 24px; overflow-x: auto;
        border-bottom: 1px solid ${FN.divider};
        background: ${FN.bgCard};
      }
      .sp-stage {
        background: transparent; border: 1px solid; padding: 8px 14px;
        font-family: 'JetBrains Mono', monospace; font-size: 9.5px;
        letter-spacing: 0.2em; text-transform: uppercase; font-weight: 700;
        cursor: pointer; border-radius: 2px;
        display: inline-flex; flex-direction: column; align-items: center; gap: 2px;
        min-width: 100px; flex-shrink: 0;
      }
      .sp-stage.active { box-shadow: 0 0 12px currentColor; }
      .sp-stage-count { font-size: 16px; font-weight: 800; }
      .sp-stage-label { font-size: 9px; opacity: 0.85; }

      .sp-main { padding: 20px 24px; display: flex; flex-direction: column; gap: 14px; }
      .sp-empty {
        text-align: center; padding: 60px 24px;
        font-family: 'JetBrains Mono', monospace;
        color: ${FN.muted}; font-size: 11px;
        letter-spacing: 0.25em; text-transform: uppercase;
      }
      .sp-card {
        background: ${FN.bgCard}; border: 1px solid ${FN.divider};
        padding: 16px 20px; border-radius: 3px;
      }
      .sp-card-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
      .sp-code {
        font-family: 'JetBrains Mono', monospace; font-size: 14px;
        font-weight: 800; letter-spacing: 0.15em;
      }
      .sp-contractor { font-size: 13px; font-weight: 700; color: ${FN.text}; margin-top: 2px; }
      .sp-meta { display: flex; gap: 16px; flex-wrap: wrap; margin-top: 4px;
                 font-size: 10px; color: ${FN.muted}; }
      .sp-meta span { display: inline-flex; align-items: center; gap: 4px; }
      .sp-card-actions { display: flex; align-items: center; gap: 16px; flex-shrink: 0; }
      .sp-card-total { text-align: right; }
      .sp-card-total-lbl { font-size: 8.5px; color: ${FN.muted};
                            font-family: 'JetBrains Mono', monospace;
                            text-transform: uppercase; letter-spacing: 0.3em; }
      .sp-card-total-val { font-family: 'JetBrains Mono', monospace;
                            font-size: 20px; font-weight: 800; margin-top: 2px; }
      .sp-card-total-sub { font-size: 9px; color: ${FN.muted};
                            font-family: 'JetBrains Mono', monospace; }
      .sp-advance {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9.5px; letter-spacing: 0.25em; text-transform: uppercase;
        font-weight: 700; border: 0; padding: 10px 14px; border-radius: 2px;
        cursor: pointer; display: inline-flex; align-items: center; gap: 6px;
      }
      .sp-advance:disabled { opacity: 0.6; cursor: wait; }
      .sp-spin { animation: spin 1s linear infinite; }
      @keyframes spin { to { transform: rotate(360deg); } }
      .sp-terminal {
        font-family: 'JetBrains Mono', monospace;
        font-size: 9px; color: ${FN.muted};
        text-transform: uppercase; letter-spacing: 0.25em;
      }

      .sp-line-table { width: 100%; margin-top: 14px;
                        border-top: 1px solid ${FN.divider};
                        border-collapse: collapse; }
      .sp-line-table th, .sp-line-table td { padding: 6px 8px; font-size: 11px;
                                              border-bottom: 1px solid ${FN.divider}; }
      .sp-line-table th { font-family: 'JetBrains Mono', monospace;
                          font-size: 8.5px; color: ${FN.muted};
                          text-transform: uppercase; letter-spacing: 0.2em;
                          text-align: left; }
      .sp-line-table .ceo-r { text-align: right; }
      .sp-mono { font-family: 'JetBrains Mono', monospace; }

      @media (max-width: 768px) {
        .sp-header { flex-direction: column; align-items: flex-start; }
        .sp-totals { flex-wrap: wrap; gap: 10px; font-size: 10px; }
        .sp-card-head { flex-direction: column; }
        .sp-card-actions { width: 100%; justify-content: space-between; }
        .sp-line-table { font-size: 10px; }
      }
    `}</style>
  );
}
