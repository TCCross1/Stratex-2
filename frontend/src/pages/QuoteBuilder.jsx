/**
 * /contractor/quote-builder — STRATEX™ Quote Builder
 *
 * Contractor-facing surface of the supplier's Material Catalog. Each contractor
 * sees the supplier's SKU list at THEIR assigned tier only. They pick line
 * items + quantities, set a markup %, and save the quote (optionally bound
 * to a job in their pipeline).
 *
 * The supplier wins because every saved quote is a forward indicator of a
 * material order. The contractor wins because the quote takes 60 seconds
 * instead of 30 minutes and the numbers can't be misquoted.
 *
 * Aesthetic locked to PBR Luxury-Corporate (#00F5D4 / #FF5400 / #3A4350).
 */
import React, { useEffect, useMemo, useState } from "react";
import { api } from "@/lib/api";
import { toast } from "sonner";
import {
  Calculator, Plus, Trash2, Save, FileText, Receipt, ShoppingCart,
  Boxes, TrendingUp, Lock, ArrowUpRight, CheckCircle2,
} from "lucide-react";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";

const fmtMoney = (n) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD",
    minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(n || 0));

const Panel = ({ title, right, span = 12, children, testid }) => (
  <div
    data-testid={testid}
    style={{
      gridColumn: `span ${span}`,
      background: "#10141D",
      border: `1px solid ${NICKEL}55`,
      borderRadius: 6,
      padding: "1.75rem",
      position: "relative",
      boxShadow: "0 4px 20px rgba(0,0,0,0.4)",
    }}>
    <div style={{
      position: "absolute", top: 0, left: 0, right: 0, height: 2,
      background: `linear-gradient(90deg, transparent, ${TEAL}, transparent)`, opacity: 0.35,
    }} />
    <div className="flex items-center justify-between mb-5">
      <h3 className="font-heading text-[15px] uppercase tracking-[0.18em] text-silver">{title}</h3>
      {right}
    </div>
    {children}
  </div>
);

const Badge = ({ children, color = NICKEL }) => (
  <span style={{
    display: "inline-flex", padding: "0.2rem 0.55rem", borderRadius: 3,
    fontSize: 10, fontWeight: 700, letterSpacing: "0.15em", textTransform: "uppercase",
    background: `${color}1A`, border: `1px solid ${color}55`, color,
  }}>{children}</span>
);

const Input = (props) => (
  <input {...props}
    className="bg-obsidian/80 border border-[#3A4350]/60 rounded px-3 py-2 text-silver text-sm focus:border-[#00F5D4] focus:shadow-[0_0_10px_rgba(0,245,212,0.2)] outline-none w-full font-mono"
  />
);

const Btn = ({ orange, ghost, disabled, children, ...rest }) => {
  const c = orange ? ORANGE : TEAL;
  return (
    <button {...rest} disabled={disabled}
      style={{
        background: ghost ? "transparent" : `${c}15`,
        border: `1px solid ${c}`, color: c,
        padding: "0.6rem 1rem", borderRadius: 4,
        fontSize: 11, fontWeight: 700, letterSpacing: "0.18em",
        textTransform: "uppercase", cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.4 : 1, transition: "all 0.18s ease",
        display: "inline-flex", alignItems: "center", gap: 8,
      }}
      onMouseEnter={(e) => !disabled && (e.currentTarget.style.boxShadow = `0 0 12px ${c}55`)}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "none")}
    >{children}</button>
  );
};

export default function QuoteBuilder() {
  const [catalog, setCatalog] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [eligibleJobs, setEligibleJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState("");
  const [promoteForQuoteId, setPromoteForQuoteId] = useState(null);
  const [promoteJobId, setPromoteJobId] = useState("");
  const [promoting, setPromoting] = useState(false);

  // Quote draft state
  const [title, setTitle] = useState("");
  const [homeowner, setHomeowner] = useState("");
  const [siteAddr, setSiteAddr] = useState("");
  const [markupPct, setMarkupPct] = useState(30);
  const [notes, setNotes] = useState("");
  const [lines, setLines] = useState([]); // [{ material_id, quantity }]
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const [c, q, j] = await Promise.all([
        api.get("/contractor/quote-builder/catalog"),
        api.get("/contractor/quote-builder/quotes"),
        api.get("/contractor/quote-builder/eligible-jobs"),
      ]);
      setCatalog(c.data);
      setQuotes(q.data.quotes || []);
      setEligibleJobs(j.data.jobs || []);
      setErr("");
    } catch (e) {
      setErr(e.response?.data?.detail || e.message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => { load(); }, []);

  async function promote(quoteId) {
    if (!promoteJobId) {
      toast.error("Pick a job to promote into");
      return;
    }
    setPromoting(true);
    try {
      const r = await api.post(`/contractor/quote-builder/quotes/${quoteId}/promote`, { job_id: promoteJobId });
      toast.success(`Promoted to job · ${fmtMoney(r.data.total_usd)} → ${promoteJobId}`);
      setPromoteForQuoteId(null);
      setPromoteJobId("");
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Promote failed");
    } finally {
      setPromoting(false);
    }
  }

  const materialById = useMemo(() => {
    const m = {};
    (catalog?.materials || []).forEach((x) => { m[x.id] = x; });
    return m;
  }, [catalog]);

  const lineDetails = useMemo(() => {
    return lines.map((ln) => {
      const m = materialById[ln.material_id] || {};
      const qty = parseFloat(ln.quantity) || 0;
      const unit = parseFloat(m.unit_price_usd) || 0;
      return {
        ...ln,
        name: m.name || "—",
        sku: m.sku || "—",
        unit_label: m.unit_label || "Each",
        unit_price_usd: unit,
        line_total_usd: +(qty * unit).toFixed(2),
      };
    });
  }, [lines, materialById]);

  const subtotal = useMemo(
    () => +(lineDetails.reduce((s, l) => s + l.line_total_usd, 0)).toFixed(2),
    [lineDetails],
  );
  const markupUsd = +(subtotal * (parseFloat(markupPct) || 0) / 100).toFixed(2);
  const total = +(subtotal + markupUsd).toFixed(2);

  function addLine(materialId) {
    if (lines.some((l) => l.material_id === materialId)) {
      toast.info("Already on the quote — adjust its quantity.");
      return;
    }
    setLines([...lines, { material_id: materialId, quantity: 1 }]);
  }
  function updateLineQty(materialId, qty) {
    setLines(lines.map((l) => l.material_id === materialId ? { ...l, quantity: qty } : l));
  }
  function removeLine(materialId) {
    setLines(lines.filter((l) => l.material_id !== materialId));
  }

  async function saveQuote() {
    if (lineDetails.length === 0) {
      toast.error("Add at least one line item.");
      return;
    }
    setSaving(true);
    try {
      await api.post("/contractor/quote-builder/quotes", {
        title: title || "Untitled Quote",
        homeowner_name: homeowner,
        site_address: siteAddr,
        markup_pct: (parseFloat(markupPct) || 0) / 100,
        lines: lineDetails.map((l) => ({ material_id: l.material_id, quantity: parseFloat(l.quantity) || 0 })),
        notes,
      });
      toast.success(`Quote saved · ${fmtMoney(total)} ready to send`);
      // Reset draft
      setTitle(""); setHomeowner(""); setSiteAddr(""); setMarkupPct(30);
      setNotes(""); setLines([]);
      await load();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <div className="p-12 text-center text-slate-400 font-mono text-sm">// Loading Quote Builder…</div>;
  if (err) return <div className="p-12 text-center text-[#FF5400] font-mono text-sm">// Error: {err}</div>;

  const tierLabel = catalog?.tier_label || "—";

  return (
    <div className="min-h-screen bg-obsidian">
      <div className="max-w-[1600px] mx-auto px-6 py-8">
        {/* Header */}
        <div className="border-b border-white/5 pb-6 mb-8 flex items-end justify-between">
          <div>
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.3em] text-[#00F5D4] font-heading font-semibold">
              <Lock size={12}/> Stratex Engine · Contractor Quote Builder
            </div>
            <h1 className="text-4xl md:text-5xl font-heading font-bold tracking-tight text-silver mt-2"
              style={{ background: "linear-gradient(135deg, #FFFFFF 0%, #94a3b8 100%)", WebkitBackgroundClip: "text", WebkitTextFillColor: "transparent" }}>
              Quote Builder
            </h1>
            <p className="text-sm text-slate-400 mt-2 max-w-3xl leading-relaxed">
              Build homeowner quotes from your supplier's tier-priced catalog in under a minute.
              Pick line items, set your markup, save the quote. Your supplier sees the SKU forecast;
              your homeowner sees a clean total.
            </p>
          </div>
          <Badge color={TEAL}>{tierLabel}</Badge>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* LEFT — Catalog (pick line items) */}
          <Panel title="Material Catalog · Your Tier Pricing"
            right={<Badge color={NICKEL}><Boxes size={11} className="inline mr-1"/>{catalog?.materials?.length ?? 0} SKUs</Badge>}
            span={7} testid="qb-catalog-panel">
            <div style={{ overflowX: "auto" }}>
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b-2 border-white/5">
                    {["SKU · Material", "Stock", "Unit Price", ""].map((h, i) => (
                      <th key={i} className={`px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading ${i === 3 ? "text-right" : ""}`}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {(catalog?.materials || []).map((m) => {
                    const onQuote = lines.some((l) => l.material_id === m.id);
                    return (
                      <tr key={m.id} className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`qb-catalog-row-${m.id}`}>
                        <td className="px-3 py-3">
                          <div className="text-silver text-sm font-semibold">{m.name}</div>
                          <div className="text-[10px] text-slate-500 font-mono mt-0.5">{m.sku} · {m.category}</div>
                        </td>
                        <td className="px-3 py-3"><Badge color={NICKEL}>{m.stock_units}</Badge></td>
                        <td className="px-3 py-3 font-mono text-[#00F5D4] text-sm">{fmtMoney(m.unit_price_usd)} <span className="text-slate-500 text-[10px]">/ {m.unit_label}</span></td>
                        <td className="px-3 py-3 text-right">
                          <Btn ghost disabled={onQuote} onClick={() => addLine(m.id)} data-testid={`qb-add-${m.id}`}>
                            <Plus size={12}/>{onQuote ? "Added" : "Add"}
                          </Btn>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Panel>

          {/* RIGHT — Live Quote Draft */}
          <Panel title="Quote Draft" span={5} testid="qb-draft-panel"
            right={<Badge color={ORANGE}><Calculator size={11} className="inline mr-1"/>Live</Badge>}>
            <div className="space-y-3">
              <div>
                <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">Quote Title</label>
                <Input value={title} onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Whitaker · 1247 Bluegrass Pkwy"
                  data-testid="qb-title-input"/>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">Homeowner</label>
                  <Input value={homeowner} onChange={(e) => setHomeowner(e.target.value)} placeholder="Name" data-testid="qb-homeowner-input"/>
                </div>
                <div>
                  <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">Site Address</label>
                  <Input value={siteAddr} onChange={(e) => setSiteAddr(e.target.value)} placeholder="123 Main St" data-testid="qb-address-input"/>
                </div>
              </div>

              <div className="border-t border-white/5 pt-3">
                <div className="text-[10px] font-heading uppercase tracking-[0.18em] text-slate-500 mb-2">Line Items ({lineDetails.length})</div>
                {lineDetails.length === 0 ? (
                  <div className="py-6 text-center text-xs text-slate-500">
                    Add items from the catalog →
                  </div>
                ) : (
                  <div className="space-y-2 max-h-[280px] overflow-y-auto pr-1" data-testid="qb-lines">
                    {lineDetails.map((l) => (
                      <div key={l.material_id} className="flex items-center gap-2 p-2 rounded border border-white/5 bg-white/[0.02]"
                        data-testid={`qb-line-${l.material_id}`}>
                        <div className="flex-1 min-w-0">
                          <div className="text-xs text-silver truncate">{l.name}</div>
                          <div className="text-[10px] text-slate-500 font-mono">{fmtMoney(l.unit_price_usd)} / {l.unit_label}</div>
                        </div>
                        <Input type="number" min="0" step="0.5"
                          value={l.quantity}
                          onChange={(e) => updateLineQty(l.material_id, e.target.value)}
                          className="!w-20 !py-1 !px-2 !text-xs"
                          style={{ width: 72 }}
                          data-testid={`qb-qty-${l.material_id}`}/>
                        <div className="text-xs font-mono text-[#00F5D4] w-20 text-right">{fmtMoney(l.line_total_usd)}</div>
                        <button onClick={() => removeLine(l.material_id)}
                          className="text-red-500 hover:opacity-70 p-1"
                          data-testid={`qb-remove-${l.material_id}`}><Trash2 size={12}/></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Totals */}
              <div className="border-t border-white/5 pt-3 space-y-1.5 font-mono text-sm">
                <div className="flex justify-between"><span className="text-slate-500">Subtotal</span><span className="text-silver">{fmtMoney(subtotal)}</span></div>
                <div className="flex justify-between items-center">
                  <span className="text-slate-500 flex items-center gap-2">
                    <TrendingUp size={12}/> Markup
                    <input type="number" min="0" max="200" value={markupPct}
                      onChange={(e) => setMarkupPct(e.target.value)}
                      className="bg-obsidian/60 border border-[#3A4350]/60 rounded px-2 py-0.5 text-silver text-xs w-14 focus:border-[#FF5400] outline-none"
                      data-testid="qb-markup-input"/>%
                  </span>
                  <span className="text-[#FF5400]">{fmtMoney(markupUsd)}</span>
                </div>
                <div className="flex justify-between border-t border-white/5 pt-2 mt-2">
                  <span className="text-silver font-heading uppercase tracking-[0.18em] text-xs">Total</span>
                  <span className="text-[#00F5D4] text-xl font-bold" data-testid="qb-total">{fmtMoney(total)}</span>
                </div>
              </div>

              <div>
                <label className="block text-[10px] font-heading uppercase tracking-[0.18em] text-[#00F5D4] mb-1.5">Notes (internal)</label>
                <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="bg-obsidian/80 border border-[#3A4350]/60 rounded px-3 py-2 text-silver text-xs focus:border-[#00F5D4] outline-none w-full font-mono resize-none"
                  placeholder="Optional"
                  data-testid="qb-notes-input"/>
              </div>

              <Btn onClick={saveQuote} disabled={saving || lineDetails.length === 0}
                data-testid="qb-save-btn">
                <Save size={14}/>{saving ? "Saving…" : "Save Quote"}
              </Btn>
            </div>
          </Panel>

          {/* BOTTOM — Saved quotes */}
          <Panel title="Saved Quotes" span={12} testid="qb-saved-panel"
            right={<Badge color={TEAL}>
              <Receipt size={11} className="inline mr-1"/>{quotes.length} · {fmtMoney(quotes.reduce((s, q) => s + (q.total_usd || 0), 0))} total
            </Badge>}>
            {quotes.length === 0 ? (
              <div className="py-8 text-center text-slate-500 text-sm">No saved quotes yet.</div>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table className="w-full text-left">
                  <thead>
                    <tr className="border-b-2 border-white/5">
                      {["Title", "Homeowner", "Lines", "Subtotal", "Markup", "Total", "Status", "Action"].map((h) => (
                        <th key={h} className="px-3 py-2 text-[10px] uppercase tracking-[0.18em] text-slate-500 font-heading">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {quotes.map((q) => {
                      const promoted = q.status === "promoted";
                      const showPromoter = promoteForQuoteId === q.id;
                      return (
                        <React.Fragment key={q.id}>
                          <tr className="border-b border-white/5 hover:bg-white/[0.02]" data-testid={`qb-saved-row-${q.id}`}>
                            <td className="px-3 py-3">
                              <div className="text-silver text-sm font-semibold">{q.title}</div>
                              <div className="text-[10px] text-slate-500 font-mono mt-0.5">{q.id}</div>
                            </td>
                            <td className="px-3 py-3 text-silver text-sm">
                              {q.homeowner_name || "—"}
                              {q.site_address && <div className="text-[10px] text-slate-500">{q.site_address}</div>}
                            </td>
                            <td className="px-3 py-3"><Badge color={NICKEL}>{(q.lines || []).length}</Badge></td>
                            <td className="px-3 py-3 font-mono text-slate-400 text-sm">{fmtMoney(q.subtotal_usd)}</td>
                            <td className="px-3 py-3 font-mono text-[#FF5400] text-sm">{(q.markup_pct * 100).toFixed(0)}% · {fmtMoney(q.markup_usd)}</td>
                            <td className="px-3 py-3 font-mono text-[#00F5D4] text-sm font-bold">{fmtMoney(q.total_usd)}</td>
                            <td className="px-3 py-3">
                              {promoted
                                ? <Badge color={TEAL} testid={`qb-status-promoted-${q.id}`}><CheckCircle2 size={10} className="inline mr-1"/>Promoted</Badge>
                                : <Badge color={NICKEL}>Draft</Badge>}
                            </td>
                            <td className="px-3 py-3">
                              {promoted
                                ? <a href={`/contractor/deliverable/${q.job_id}`}
                                    className="text-[#00F5D4] text-[10px] uppercase tracking-[0.18em] font-heading font-bold hover:opacity-80"
                                    data-testid={`qb-view-deliverable-${q.id}`}>
                                    View Deliverable →
                                  </a>
                                : showPromoter
                                  ? <Btn ghost orange onClick={() => { setPromoteForQuoteId(null); setPromoteJobId(""); }}>
                                      <X size={11}/>Cancel
                                    </Btn>
                                  : <Btn ghost onClick={() => { setPromoteForQuoteId(q.id); setPromoteJobId(""); }}
                                      data-testid={`qb-promote-toggle-${q.id}`}>
                                      <ArrowUpRight size={11}/>Promote
                                    </Btn>}
                            </td>
                          </tr>
                          {showPromoter && (
                            <tr className="bg-[#00F5D4]/[0.03] border-b border-[#00F5D4]/30" data-testid={`qb-promote-row-${q.id}`}>
                              <td colSpan={8} className="px-3 py-4">
                                <div className="flex items-center gap-3">
                                  <span className="text-[10px] uppercase tracking-[0.18em] text-[#00F5D4] font-heading font-bold whitespace-nowrap">
                                    Promote to job →
                                  </span>
                                  <select value={promoteJobId}
                                    onChange={(e) => setPromoteJobId(e.target.value)}
                                    className="bg-obsidian/80 border border-[#3A4350]/60 rounded px-3 py-2 text-silver text-sm focus:border-[#00F5D4] outline-none flex-1 font-mono"
                                    data-testid={`qb-promote-job-select-${q.id}`}>
                                    <option value="">Select job…</option>
                                    {eligibleJobs.map((j) => (
                                      <option key={j.job_id} value={j.job_id}>
                                        {j.project_code} · {j.site_address} {j.has_pricing ? "(⚠ overwrites existing pricing)" : ""}
                                      </option>
                                    ))}
                                  </select>
                                  <Btn onClick={() => promote(q.id)} disabled={promoting || !promoteJobId}
                                    data-testid={`qb-promote-submit-${q.id}`}>
                                    <CheckCircle2 size={12}/>{promoting ? "Promoting…" : "Promote"}
                                  </Btn>
                                </div>
                                {eligibleJobs.length === 0 && (
                                  <div className="text-xs text-slate-400 mt-2">
                                    You have no jobs yet. Create one from <a href="/contractor/jobs/new" className="text-[#00F5D4]">New Job</a>, then promote this quote.
                                  </div>
                                )}
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </Panel>
        </div>
      </div>
    </div>
  );
}
