// STRATEX™ — GM Brand Roster + Pricing Inventory (Phase 3)
//
// Single-page split-view for the General Manager tier:
//   • Left  — Brand Roster (preferred vendors per material category)
//   • Right — Pricing Inventory (SKU-level cost + markup + sell-price)
// Both panels expose full CRUD against MongoDB-backed collections.

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { StratexLogo } from "@/components/StratexBrand";
import {
  ArrowLeft, Plus, Trash2, Pencil, Save, X,
  Boxes, ShieldCheck, Sparkles, Loader2,
} from "lucide-react";

const ACCENTS = {
  cyan: "#00E5FF", amber: "#FFB020", green: "#00FF9C",
  magenta: "#FF2D78", gold: "#D4B86A", volt: "#A6FF00",
};

const CATEGORY_ACCENT = {
  Roofing: ACCENTS.cyan, Gutters: ACCENTS.amber, Siding: ACCENTS.green,
  Windows: ACCENTS.volt, Doors: ACCENTS.magenta, Trim: ACCENTS.gold,
};

const CATEGORIES = ["Roofing", "Gutters", "Siding", "Windows", "Doors", "Trim"];
const TIERS = ["MASTER", "PREMIER", "STANDARD"];

const EMPTY_BRAND = { name: "", category: "Roofing", preferred: true, tier: "STANDARD",
                     rep_name: "", rep_phone: "", rep_email: "", territory: "Central KY", notes: "" };
const EMPTY_SKU   = { brand: "", category: "Roofing", sku: "", description: "",
                      unit: "ea", cost_usd: 0, markup_pct: 25, region: "Central KY", in_stock: true };

// ────────────────────────────────────────────────────────────────────────
function BrandRow({ brand, onEdit, onDelete }) {
  const c = CATEGORY_ACCENT[brand.category] || ACCENTS.cyan;
  const tierColor = brand.tier === "MASTER" ? ACCENTS.gold :
                    brand.tier === "PREMIER" ? ACCENTS.green : ACCENTS.cyan;
  return (
    <div data-testid={`brand-row-${brand.id}`}
         className="rounded-md px-3 py-2.5 flex items-center gap-3"
         style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${c}55` }}>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-display text-[14px] uppercase tracking-[0.08em] text-white truncate">{brand.name}</span>
          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase px-1.5 py-0.5 rounded-full"
                style={{ color: tierColor, border: `1px solid ${tierColor}66`, background: `${tierColor}10` }}>
            {brand.tier}
          </span>
        </div>
        <div className="font-mono text-[9.5px] tracking-[0.14em] uppercase text-slate-400 mt-0.5 truncate">
          {brand.category} · {brand.rep_name} · {brand.rep_phone} · {brand.territory}
        </div>
      </div>
      <button data-testid={`brand-edit-${brand.id}`} onClick={() => onEdit(brand)}
              className="grid place-items-center rounded-md transition hover:brightness-150"
              style={{ width: 26, height: 26, background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
        <Pencil size={11}/>
      </button>
      <button data-testid={`brand-delete-${brand.id}`} onClick={() => onDelete(brand)}
              className="grid place-items-center rounded-md transition hover:brightness-150"
              style={{ width: 26, height: 26, background: `${ACCENTS.magenta}14`, border: `1px solid ${ACCENTS.magenta}66`, color: ACCENTS.magenta }}>
        <Trash2 size={11}/>
      </button>
    </div>
  );
}

function InventoryRow({ item, onEdit, onDelete }) {
  const c = CATEGORY_ACCENT[item.category] || ACCENTS.cyan;
  return (
    <div data-testid={`sku-row-${item.id}`}
         className="grid grid-cols-[1.6fr_1fr_70px_90px_70px_84px] gap-3 items-center px-3 py-2 rounded-md"
         style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${c}44` }}>
      <div className="min-w-0">
        <div className="font-display text-[12px] uppercase tracking-[0.06em] text-white truncate">{item.description}</div>
        <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-slate-500 mt-0.5">
          {item.brand} · {item.category}
        </div>
      </div>
      <span className="font-mono text-[10.5px] tracking-[0.06em] text-cyan-300 truncate">{item.sku}</span>
      <span className="font-mono text-[10px] uppercase text-slate-300 text-center">{item.unit}</span>
      <span className="font-mono text-[10.5px] text-right text-white">${item.cost_usd.toFixed(2)}</span>
      <span className="font-mono text-[10.5px] text-right" style={{ color: ACCENTS.amber }}>{item.markup_pct}%</span>
      <span className="font-mono text-[11px] text-right font-bold" style={{ color: ACCENTS.green }}>${item.sell_price_usd.toFixed(2)}</span>
      <div className="col-span-6 mt-1 -mb-1 flex items-center justify-end gap-2">
        <button data-testid={`sku-edit-${item.id}`} onClick={() => onEdit(item)}
                className="font-mono text-[8.5px] tracking-[0.18em] uppercase px-2 py-0.5 rounded-sm"
                style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
          edit
        </button>
        <button data-testid={`sku-delete-${item.id}`} onClick={() => onDelete(item)}
                className="font-mono text-[8.5px] tracking-[0.18em] uppercase px-2 py-0.5 rounded-sm"
                style={{ background: `${ACCENTS.magenta}14`, border: `1px solid ${ACCENTS.magenta}55`, color: ACCENTS.magenta }}>
          delete
        </button>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
function EditorModal({ open, title, fields, value, onChange, onSave, onClose, accent = ACCENTS.cyan }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 grid place-items-center px-4"
         style={{ background: "rgba(2,6,11,0.85)", backdropFilter: "blur(6px)" }}>
      <div className="w-full max-w-lg rounded-xl p-5"
           style={{ background: "rgba(8,14,24,0.96)", border: `1.5px solid ${accent}99`,
                    boxShadow: `0 0 36px ${accent}22, inset 0 0 28px ${accent}10` }}>
        <div className="flex items-center justify-between mb-4">
          <div className="font-display text-base uppercase tracking-[0.12em] text-white">{title}</div>
          <button data-testid="modal-close" onClick={onClose}
                  className="grid place-items-center rounded-md"
                  style={{ width: 26, height: 26, background: "rgba(255,255,255,0.04)", color: "#fff" }}>
            <X size={12}/>
          </button>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {fields.map((f) => (
            <label key={f.k} className={f.full ? "col-span-2 block" : "block"}>
              <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">{f.l}</span>
              {f.type === "select" ? (
                <select
                  data-testid={`field-${f.k}`}
                  value={value[f.k] ?? ""}
                  onChange={(e) => onChange({ [f.k]: e.target.value })}
                  className="w-full mt-0.5 px-3 py-1.5 rounded-sm font-mono text-[11.5px] text-white outline-none"
                  style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${accent}55` }}>
                  {(f.options || []).map((o) => <option key={o} value={o}>{o}</option>)}
                </select>
              ) : (
                <input
                  data-testid={`field-${f.k}`}
                  type={f.type || "text"}
                  value={value[f.k] ?? ""}
                  onChange={(e) => onChange({
                    [f.k]: f.type === "number" ? parseFloat(e.target.value || 0) : e.target.value
                  })}
                  className="w-full mt-0.5 px-3 py-1.5 bg-transparent outline-none font-mono text-[11.5px] tracking-[0.04em] text-white rounded-sm"
                  style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${accent}55` }}
                />
              )}
            </label>
          ))}
        </div>
        <div className="mt-5 flex justify-end gap-2">
          <button data-testid="modal-cancel" onClick={onClose}
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md"
                  style={{ background: "rgba(255,255,255,0.04)", color: "#fff" }}>
            Cancel
          </button>
          <button data-testid="modal-save" onClick={onSave}
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md flex items-center gap-2"
                  style={{ background: accent, color: "#02060B", boxShadow: `0 0 16px ${accent}66` }}>
            <Save size={12}/> Save
          </button>
        </div>
      </div>
    </div>
  );
}

// ────────────────────────────────────────────────────────────────────────
export default function GmRoster() {
  const API = process.env.REACT_APP_BACKEND_URL;
  const nav = useNavigate();
  const [brands, setBrands] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterCat, setFilterCat] = useState("ALL");
  const [editBrand, setEditBrand] = useState(null);
  const [editSku, setEditSku] = useState(null);

  const reload = async () => {
    setLoading(true);
    try {
      const [r1, r2] = await Promise.all([
        fetch(`${API}/api/gm/roster`).then((r) => r.json()),
        fetch(`${API}/api/gm/inventory`).then((r) => r.json()),
      ]);
      setBrands(r1.items || []);
      setInventory(r2.items || []);
      if ((r1.count ?? 0) === 0 && (r2.count ?? 0) === 0) {
        // Auto-seed on first visit for demo continuity
        await Promise.all([
          fetch(`${API}/api/gm/roster/seed-demo`, { method: "POST" }),
          fetch(`${API}/api/gm/inventory/seed-demo`, { method: "POST" }),
        ]);
        const [r1b, r2b] = await Promise.all([
          fetch(`${API}/api/gm/roster`).then((r) => r.json()),
          fetch(`${API}/api/gm/inventory`).then((r) => r.json()),
        ]);
        setBrands(r1b.items || []);
        setInventory(r2b.items || []);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); }, []);

  const filteredBrands = useMemo(() =>
    filterCat === "ALL" ? brands : brands.filter((b) => b.category === filterCat),
    [brands, filterCat]);

  const filteredInv = useMemo(() =>
    filterCat === "ALL" ? inventory : inventory.filter((i) => i.category === filterCat),
    [inventory, filterCat]);

  const saveBrand = async () => {
    if (!editBrand) return;
    const isNew = !editBrand.id;
    const url = isNew ? `${API}/api/gm/roster` : `${API}/api/gm/roster/${editBrand.id}`;
    const method = isNew ? "POST" : "PATCH";
    const r = await fetch(url, { method, headers: { "Content-Type": "application/json" },
                                 body: JSON.stringify(editBrand) });
    if (r.ok) {
      toast.success(isNew ? "Brand added" : "Brand updated");
      setEditBrand(null);
      reload();
    } else {
      toast.error("Save failed");
    }
  };
  const removeBrand = async (b) => {
    if (!window.confirm(`Delete ${b.name}?`)) return;
    const r = await fetch(`${API}/api/gm/roster/${b.id}`, { method: "DELETE" });
    if (r.ok) { toast.success("Brand deleted"); reload(); }
  };

  const saveSku = async () => {
    if (!editSku) return;
    const isNew = !editSku.id;
    const url = isNew ? `${API}/api/gm/inventory` : `${API}/api/gm/inventory/${editSku.id}`;
    const method = isNew ? "POST" : "PATCH";
    const r = await fetch(url, { method, headers: { "Content-Type": "application/json" },
                                 body: JSON.stringify(editSku) });
    if (r.ok) {
      toast.success(isNew ? "SKU added" : "SKU updated");
      setEditSku(null);
      reload();
    } else {
      toast.error("Save failed");
    }
  };
  const removeSku = async (it) => {
    if (!window.confirm(`Delete ${it.sku}?`)) return;
    const r = await fetch(`${API}/api/gm/inventory/${it.id}`, { method: "DELETE" });
    if (r.ok) { toast.success("SKU deleted"); reload(); }
  };

  return (
    <div data-testid="gm-roster-page" className="min-h-screen text-slate-100"
         style={{ background:
           "radial-gradient(ellipse at 80% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
           "radial-gradient(ellipse at 5% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
           "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
           fontFamily: "'Sora', sans-serif" }}>
      <div aria-hidden className="pointer-events-none fixed inset-0 opacity-[0.04]"
           style={{ backgroundImage:
             "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px),linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
             backgroundSize: "60px 60px" }}/>

      <header className="max-w-[1500px] mx-auto px-4 sm:px-6 py-6 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => nav("/deck")}
                  data-testid="back-deck"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                  style={{ background: "rgba(0,229,255,0.10)", border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
            <ArrowLeft size={12}/> Command Deck
          </button>
          <StratexLogo height={28}/>
          <span className="font-mono text-[9px] tracking-[0.32em] uppercase text-slate-500 hidden md:inline">
            // GM · ROSTER & INVENTORY
          </span>
        </div>
        <div className="inline-flex p-1 rounded-full"
             style={{ background: "rgba(8,14,24,0.85)", border: `1px solid ${ACCENTS.cyan}33` }}>
          {["ALL", ...CATEGORIES].map((cat) => (
            <button
              key={cat}
              data-testid={`cat-filter-${cat.toLowerCase()}`}
              onClick={() => setFilterCat(cat)}
              className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-full transition"
              style={{
                background: filterCat === cat ? (CATEGORY_ACCENT[cat] || ACCENTS.cyan) : "transparent",
                color: filterCat === cat ? "#02060B" : (CATEGORY_ACCENT[cat] || ACCENTS.cyan),
                fontWeight: filterCat === cat ? 700 : 400,
              }}>
              {cat}
            </button>
          ))}
        </div>
      </header>

      <h1 className="max-w-[1500px] mx-auto px-4 sm:px-6 font-display uppercase tracking-[0.04em] text-3xl sm:text-5xl leading-[1.05]">
        GM Brand <span style={{ color: ACCENTS.gold, textShadow: `0 0 18px ${ACCENTS.gold}55` }}>Roster</span> &amp; Pricing
      </h1>
      <p className="max-w-[1500px] mx-auto px-4 sm:px-6 font-mono text-[11px] tracking-[0.14em] uppercase text-slate-400 mt-3">
        Preferred vendors per material category + SKU-level cost &amp; sell-price control. Tied to the contractor pricing engine.
      </p>

      {loading ? (
        <div className="text-center py-16"><Loader2 size={28} className="mx-auto animate-spin text-cyan-400"/></div>
      ) : (
      <main className="max-w-[1500px] mx-auto px-4 sm:px-6 py-8 grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-5">

        {/* LEFT — Brand Roster */}
        <section className="rounded-xl p-4"
                 style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.cyan}55`,
                          boxShadow: `inset 0 0 28px ${ACCENTS.cyan}08` }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck size={14} className="text-cyan-400"/>
              <span className="font-display text-base uppercase tracking-[0.12em] text-white">Brand Roster</span>
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                {filteredBrands.length}
              </span>
            </div>
            <button data-testid="add-brand-btn" onClick={() => setEditBrand({ ...EMPTY_BRAND })}
                    className="font-mono text-[10px] tracking-[0.22em] uppercase px-2.5 py-1 rounded-md flex items-center gap-1"
                    style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
              <Plus size={11}/> Add
            </button>
          </div>
          <div className="space-y-2 max-h-[64vh] overflow-y-auto pr-1 deck-rail-scroll">
            {filteredBrands.map((b) => (
              <BrandRow key={b.id} brand={b} onEdit={setEditBrand} onDelete={removeBrand}/>
            ))}
          </div>
        </section>

        {/* RIGHT — Inventory */}
        <section className="rounded-xl p-4"
                 style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.amber}55`,
                          boxShadow: `inset 0 0 28px ${ACCENTS.amber}08` }}>
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <Boxes size={14} className="text-amber-400"/>
              <span className="font-display text-base uppercase tracking-[0.12em] text-white">Pricing Inventory</span>
              <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                {filteredInv.length} SKUs
              </span>
            </div>
            <button data-testid="add-sku-btn" onClick={() => setEditSku({ ...EMPTY_SKU })}
                    className="font-mono text-[10px] tracking-[0.22em] uppercase px-2.5 py-1 rounded-md flex items-center gap-1"
                    style={{ background: `${ACCENTS.amber}14`, border: `1px solid ${ACCENTS.amber}66`, color: ACCENTS.amber }}>
              <Plus size={11}/> Add SKU
            </button>
          </div>
          <div className="grid grid-cols-[1.6fr_1fr_70px_90px_70px_84px] gap-3 px-3 pb-2 font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
            <span>Description / Brand</span><span>SKU</span><span className="text-center">Unit</span>
            <span className="text-right">Cost</span><span className="text-right">M-up</span><span className="text-right">Sell</span>
          </div>
          <div className="space-y-2 max-h-[64vh] overflow-y-auto pr-1 deck-rail-scroll">
            {filteredInv.map((it) => (
              <InventoryRow key={it.id} item={it} onEdit={setEditSku} onDelete={removeSku}/>
            ))}
          </div>
        </section>
      </main>
      )}

      {/* Brand Editor */}
      <EditorModal
        open={!!editBrand}
        title={editBrand?.id ? "Edit Brand" : "Add Brand"}
        accent={ACCENTS.cyan}
        value={editBrand || EMPTY_BRAND}
        onChange={(patch) => setEditBrand((b) => ({ ...b, ...patch }))}
        onSave={saveBrand}
        onClose={() => setEditBrand(null)}
        fields={[
          { k: "name", l: "Brand Name" },
          { k: "category", l: "Category", type: "select", options: CATEGORIES },
          { k: "tier", l: "Tier", type: "select", options: TIERS },
          { k: "territory", l: "Territory" },
          { k: "rep_name", l: "Rep Name" },
          { k: "rep_phone", l: "Rep Phone" },
          { k: "rep_email", l: "Rep Email", full: true },
          { k: "notes", l: "Notes", full: true },
        ]}
      />

      {/* SKU Editor */}
      <EditorModal
        open={!!editSku}
        title={editSku?.id ? "Edit SKU" : "Add SKU"}
        accent={ACCENTS.amber}
        value={editSku || EMPTY_SKU}
        onChange={(patch) => setEditSku((s) => ({ ...s, ...patch }))}
        onSave={saveSku}
        onClose={() => setEditSku(null)}
        fields={[
          { k: "brand", l: "Brand" },
          { k: "category", l: "Category", type: "select", options: CATEGORIES },
          { k: "sku", l: "SKU code" },
          { k: "description", l: "Description", full: true },
          { k: "unit", l: "Unit (ea/sq/lf)" },
          { k: "region", l: "Region" },
          { k: "cost_usd", l: "Cost (USD)", type: "number" },
          { k: "markup_pct", l: "Markup (%)", type: "number" },
        ]}
      />

      <style>{`
        .deck-rail-scroll::-webkit-scrollbar { width: 6px; }
        .deck-rail-scroll::-webkit-scrollbar-track { background: transparent; }
        .deck-rail-scroll::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.28); border-radius: 4px; }
      `}</style>
    </div>
  );
}
