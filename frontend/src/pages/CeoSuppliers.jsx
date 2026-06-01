/**
 * CeoSuppliers — STRATEX Phase 1 supplier-registry surface.
 *
 * CEO-only screen to create, list, and theme building-material suppliers
 * (QXO, ABC Supply, future). Every supplier here becomes a scoped GM
 * Dashboard downstream.
 *
 * Brand bible v4.0 compliant — cyan/amber/green palette + glow tokens.
 */
import React, { useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { ArrowLeft, Building2, Plus, Edit3, Archive, ShieldCheck } from "lucide-react";
import { toast } from "sonner";

const C = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  green:   "#00FF9C",
  magenta: "#FF2D78",
  text:    "#E2E8F0",
  muted:   "#7C8A9E",
  ink:     "#080C14",
  card:    "#0F172A",
  divider: "#1E293B",
};

const empty = {
  name: "", short_code: "", brand_color: C.cyan, secondary_color: C.amber,
  logo_text: "", headquarters_city: "",
};

export default function CeoSuppliers() {
  const nav = useNavigate();
  const [items, setItems] = useState([]);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState(empty);
  const [showGmModal, setShowGmModal] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get("/admin/suppliers");
      setItems(data?.items || []);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Failed to load suppliers");
    }
  }, []);
  useEffect(() => { load(); }, [load]);

  const createSupplier = async (e) => {
    e?.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await api.post("/admin/suppliers", form);
      toast.success(`${form.short_code.toUpperCase()} registered`);
      setForm(empty);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Create failed");
    } finally { setBusy(false); }
  };

  const archive = async (id) => {
    if (!window.confirm("Archive this supplier? GM accounts under it will be frozen.")) return;
    try {
      await api.delete(`/admin/suppliers/${id}`);
      toast.success("Archived"); load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Archive failed");
    }
  };

  return (
    <div data-testid="ceo-suppliers-root"
         style={{ minHeight: "100vh", background: C.ink, color: C.text,
                  padding: "32px 24px 140px" }}>
      <div style={{ maxWidth: 1500, margin: "0 auto" }}>
        <button onClick={() => nav(-1)} data-testid="suppliers-back"
          style={{
            display: "inline-flex", alignItems: "center", gap: 6,
            background: "transparent", border: `1px solid ${C.cyan}66`,
            color: C.cyan, padding: "5px 11px", borderRadius: 5,
            fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
            letterSpacing: "0.2em", textTransform: "uppercase", cursor: "pointer",
            textShadow: `0 0 8px ${C.cyan}`,
          }}>
          <ArrowLeft size={12}/> Return
        </button>

        <header style={{ marginTop: 18, marginBottom: 22 }}>
          <div style={{ color: C.cyan, fontFamily: "'JetBrains Mono', monospace",
                        fontSize: 10, letterSpacing: "0.32em", textTransform: "uppercase",
                        textShadow: `0 0 10px ${C.cyan}` }}>
            // STRATEX VISION · CEO · SUPPLIER REGISTRY · PHASE 1
          </div>
          <h1 style={{ fontFamily: "'Space Grotesk', sans-serif",
                       fontSize: 36, lineHeight: 1.05, letterSpacing: "0.08em",
                       textTransform: "uppercase", margin: "6px 0 4px",
                       textShadow: `0 0 14px ${C.cyan}55` }}>
            Building Supplier Roster
          </h1>
          <p style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                      fontSize: 11, letterSpacing: "0.12em" }}>
            <ShieldCheck size={11} style={{ display: "inline", verticalAlign: -1, marginRight: 4 }}/>
            Only the CEO portal can register a supplier brand. Each supplier becomes a scoped GM dashboard.
          </p>
        </header>

        <div style={{ display: "grid", gap: 18,
                      gridTemplateColumns: "minmax(0, 1.5fr) minmax(0, 1fr)" }}>
          {/* LIST */}
          <section data-testid="suppliers-list"
            style={{ background: C.card, border: `1px solid ${C.divider}`,
                     borderLeft: `4px solid ${C.cyan}`, borderRadius: 6,
                     padding: "16px 18px",
                     boxShadow: `0 22px 60px -22px ${C.cyan}33` }}>
            <div style={{ display: "flex", justifyContent: "space-between",
                          alignItems: "center", marginBottom: 12 }}>
              <h2 style={{ color: C.cyan, fontFamily: "'JetBrains Mono', monospace",
                           fontSize: 11, letterSpacing: "0.24em", margin: 0,
                           textTransform: "uppercase",
                           textShadow: `0 0 10px ${C.cyan}` }}>
                Active Suppliers
              </h2>
              <span data-testid="suppliers-count"
                    style={{ color: C.cyan, fontFamily: "'JetBrains Mono', monospace",
                             fontSize: 10, letterSpacing: "0.18em" }}>
                {items.length} ACTIVE
              </span>
            </div>
            {items.length === 0 ? (
              <div style={{ color: C.muted, padding: "26px 0", textAlign: "center",
                            fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>
                // No suppliers yet — register QXO + ABC Supply to begin.
              </div>
            ) : (
              <ol style={{ listStyle: "none", padding: 0, margin: 0 }}>
                {items.map((s) => (
                  <li key={s.id} data-testid={`supplier-row-${s.short_code}`}
                      style={{
                        padding: "12px 0",
                        borderBottom: `1px dashed ${C.divider}`,
                        display: "grid",
                        gridTemplateColumns: "44px minmax(0, 1fr) auto",
                        gap: 12, alignItems: "center",
                      }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 6,
                      background: `linear-gradient(135deg, ${s.brand_color}22, ${s.secondary_color}22)`,
                      border: `1px solid ${s.brand_color}88`,
                      display: "grid", placeItems: "center",
                      color: s.brand_color, fontWeight: 800,
                      fontFamily: "'JetBrains Mono', monospace",
                      textShadow: `0 0 8px ${s.brand_color}`,
                      boxShadow: `0 0 14px ${s.brand_color}33`,
                    }}>
                      {s.short_code}
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ color: C.text, fontWeight: 700, fontSize: 14 }}>
                        {s.name}
                      </div>
                      <div style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                                    fontSize: 10, letterSpacing: "0.12em", marginTop: 2 }}>
                        {s.headquarters_city || "—"}
                        <span style={{ margin: "0 6px", opacity: 0.4 }}>·</span>
                        GMs <strong style={{ color: C.cyan }}>{s.gm_count}</strong>
                        <span style={{ margin: "0 6px", opacity: 0.4 }}>·</span>
                        Contractors <strong style={{ color: C.green }}>{s.contractor_count}</strong>
                      </div>
                    </div>
                    <div style={{ display: "flex", gap: 6 }}>
                      <button onClick={() => setShowGmModal(s)}
                              data-testid={`supplier-create-gm-${s.short_code}`}
                              style={btnStyle(C.green)}>
                        <Plus size={11}/> GM
                      </button>
                      <button onClick={() => archive(s.id)}
                              data-testid={`supplier-archive-${s.short_code}`}
                              style={btnStyle(C.magenta)}>
                        <Archive size={11}/> Archive
                      </button>
                    </div>
                  </li>
                ))}
              </ol>
            )}
          </section>

          {/* CREATE FORM */}
          <section data-testid="suppliers-create-form"
            style={{ background: C.card, border: `1px solid ${C.divider}`,
                     borderLeft: `4px solid ${C.amber}`, borderRadius: 6,
                     padding: "16px 18px",
                     boxShadow: `0 22px 60px -22px ${C.amber}33` }}>
            <h2 style={{ color: C.amber, fontFamily: "'JetBrains Mono', monospace",
                         fontSize: 11, letterSpacing: "0.24em", margin: "0 0 12px",
                         textTransform: "uppercase",
                         textShadow: `0 0 10px ${C.amber}` }}>
              Register New Supplier
            </h2>
            <form onSubmit={createSupplier} style={{ display: "grid", gap: 10 }}>
              <Field label="Legal Name"      val={form.name}        onChange={(v)=>setForm({...form, name: v})}        testid="sup-name"/>
              <Field label="Short Code (≤12)" val={form.short_code} onChange={(v)=>setForm({...form, short_code: v.toUpperCase()})} testid="sup-short"/>
              <Field label="Logo Text"       val={form.logo_text}   onChange={(v)=>setForm({...form, logo_text: v})}   testid="sup-logo"/>
              <Field label="HQ City, State"  val={form.headquarters_city} onChange={(v)=>setForm({...form, headquarters_city: v})} testid="sup-hq"/>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <Field label="Brand Color"     val={form.brand_color}     onChange={(v)=>setForm({...form, brand_color: v})} testid="sup-color1" type="color"/>
                <Field label="Secondary Color" val={form.secondary_color} onChange={(v)=>setForm({...form, secondary_color: v})} testid="sup-color2" type="color"/>
              </div>
              <button type="submit" disabled={busy}
                      data-testid="sup-create-btn"
                      style={{
                        marginTop: 6,
                        background: `linear-gradient(135deg, ${C.cyan}, #0891b2)`,
                        border: "none", color: C.ink, fontWeight: 800,
                        padding: "9px 0", borderRadius: 4, cursor: "pointer",
                        fontFamily: "'JetBrains Mono', monospace",
                        letterSpacing: "0.22em", fontSize: 11, textTransform: "uppercase",
                        boxShadow: `0 0 18px ${C.cyan}88, 0 0 36px ${C.cyan}44`,
                      }}>
                {busy ? "…" : "+ Register Supplier"}
              </button>
            </form>
          </section>
        </div>
      </div>

      {showGmModal && (
        <GmCreateModal supplier={showGmModal}
                       onClose={() => { setShowGmModal(null); load(); }}/>
      )}
    </div>
  );
}

const btnStyle = (color) => ({
  display: "inline-flex", alignItems: "center", gap: 4,
  background: "transparent", border: `1px solid ${color}77`,
  color, padding: "5px 9px", borderRadius: 4, cursor: "pointer",
  fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
  letterSpacing: "0.18em", textTransform: "uppercase",
  textShadow: `0 0 6px ${color}`,
});

function Field({ label, val, onChange, testid, type = "text" }) {
  return (
    <label style={{ display: "block" }}>
      <span style={{ display: "block", color: C.muted,
                     fontFamily: "'JetBrains Mono', monospace", fontSize: 9,
                     letterSpacing: "0.22em", textTransform: "uppercase",
                     marginBottom: 4 }}>
        {label}
      </span>
      <input data-testid={testid}
             type={type} value={val} onChange={(e) => onChange(e.target.value)}
             required style={{
               width: "100%", background: "#0b1329",
               border: `1px solid ${C.divider}`, color: C.text,
               padding: "8px 10px", borderRadius: 4,
               fontFamily: type === "color" ? "inherit" : "'JetBrains Mono', monospace",
               fontSize: 12, outline: "none",
             }}/>
    </label>
  );
}

// ---------------------------------------------------------------------------
// GM creation modal (Phase 1 — CEO creates GM scoped to selected supplier)
// ---------------------------------------------------------------------------
function GmCreateModal({ supplier, onClose }) {
  const [f, setF] = useState({ email: "", legal_name: "", phone: "",
                               initial_password: "" });
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e?.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      await api.post("/admin/users/create", {
        ...f,
        role: "gm",
        supplier_id: supplier.id,
      });
      toast.success(`GM created for ${supplier.short_code}`);
      onClose();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Create failed");
    } finally { setBusy(false); }
  };

  return (
    <div onClick={onClose}
         style={{ position: "fixed", inset: 0, background: "rgba(2,6,11,0.78)",
                  display: "grid", placeItems: "center", zIndex: 100,
                  backdropFilter: "blur(8px)" }}>
      <form onClick={(e)=>e.stopPropagation()} onSubmit={submit}
            data-testid="gm-create-modal"
            style={{
              background: C.card, border: `1px solid ${supplier.brand_color}66`,
              borderRadius: 8, padding: "22px 24px", minWidth: 420, maxWidth: 520,
              boxShadow: `0 30px 80px -10px ${supplier.brand_color}66, 0 0 60px ${supplier.brand_color}33`,
            }}>
        <h3 style={{ color: supplier.brand_color,
                     fontFamily: "'JetBrains Mono', monospace", fontSize: 11,
                     letterSpacing: "0.24em", textTransform: "uppercase",
                     margin: "0 0 4px",
                     textShadow: `0 0 10px ${supplier.brand_color}` }}>
          Create GM · {supplier.short_code}
        </h3>
        <p style={{ color: C.muted, fontFamily: "'JetBrains Mono', monospace",
                    fontSize: 10, letterSpacing: "0.12em", marginBottom: 16 }}>
          Branch Manager scoped to <strong style={{ color: C.text }}>{supplier.name}</strong>.
          Account ships with forced password reset on first login.
        </p>
        <div style={{ display: "grid", gap: 10 }}>
          <Field label="Legal Name"   val={f.legal_name} onChange={(v)=>setF({...f, legal_name:v})} testid="gm-name"/>
          <Field label="Email"        val={f.email}      onChange={(v)=>setF({...f, email:v})} testid="gm-email"/>
          <Field label="Phone (E.164)" val={f.phone}     onChange={(v)=>setF({...f, phone:v})} testid="gm-phone"/>
          <Field label="Initial Password (≥8)" val={f.initial_password}
                 onChange={(v)=>setF({...f, initial_password:v})}
                 testid="gm-pw" type="password"/>
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 14, justifyContent: "flex-end" }}>
          <button type="button" onClick={onClose} style={btnStyle(C.muted)}>Cancel</button>
          <button type="submit" disabled={busy} data-testid="gm-submit"
                  style={{
                    background: `linear-gradient(135deg, ${supplier.brand_color}, ${supplier.secondary_color})`,
                    border: "none", color: C.ink, fontWeight: 800,
                    padding: "8px 16px", borderRadius: 4, cursor: "pointer",
                    fontFamily: "'JetBrains Mono', monospace", fontSize: 10,
                    letterSpacing: "0.22em", textTransform: "uppercase",
                    boxShadow: `0 0 18px ${supplier.brand_color}88`,
                  }}>
            {busy ? "…" : "Create GM"}
          </button>
        </div>
      </form>
    </div>
  );
}
