/**
 * /ceo/regional — STRATEX™ Regional Switchboard.
 *
 * National multi-store rollup. Kentucky pinned first (local), then OH/TN/IN.
 * Per-state accordion → per-store cards with ROI saturation + projected MRR.
 *
 * Pure addition (preservation lock).
 */
import React, { useEffect, useMemo, useState } from "react";
import axios from "axios";
import { PilotShell, NeonBadge, FN_TEAL, FN_GREEN, FN_AMBER, FN_DIM, FN_INK } from "@/components/PilotShell";
import {
  Building2, MapPin, TrendingUp, Wallet, Plane,
  ChevronDown, ChevronRight, ShieldCheck, Star,
} from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

const fmtMoney = (n) => "$" + (n ?? 0).toLocaleString("en-US", { maximumFractionDigits: 0 });

export default function RegionalSwitchboard() {
  const [data, setData] = useState(null);
  const [busy, setBusy] = useState(true);
  const [err, setErr] = useState("");
  const [open, setOpen] = useState({});
  const token = typeof window !== "undefined" ? localStorage.getItem("stratex_token") : null;

  useEffect(() => {
    (async () => {
      try {
        const { data } = await axios.get(`${API}/regional/switchboard?local_state=KY`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        setData(data);
        // local state expanded by default
        const initOpen = {};
        (data.states || []).forEach((s, i) => { initOpen[s.state] = i === 0; });
        setOpen(initOpen);
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message || "Failed to load");
      } finally { setBusy(false); }
    })();
  }, [token]);

  const t = data?.totals;

  return (
    <PilotShell
      title="Regional Switchboard"
      subtitle="MULTI-STORE FLEET ROLLUP · LOCAL → NATIONAL"
      back="/ceo/command"
      rightSlot={
        t && <NeonBadge ok={t.roi_saturation_pct >= 50}
                        value={`${t.stores_at_roi}/${t.stores_total} STORES AT ROI · ${t.roi_saturation_pct}%`}/>
      }
    >
      <div style={{ maxWidth: 1300, margin: "0 auto" }}>
        {busy && <Skeleton/>}
        {err && <div style={{ color: FN_AMBER, fontFamily: "monospace", fontSize: 12 }}>⚠ {err}</div>}

        {t && (
          <div data-testid="regional-national-totals" style={{
            display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 10, marginBottom: 20,
          }}>
            <KPI label="ACTIVE UNITS" value={t.units} color={FN_TEAL} icon={<Plane size={11}/>}/>
            <KPI label="ACCUMULATED SCANS" value={t.scans.toLocaleString()} color={FN_TEAL}
                 icon={<ShieldCheck size={11}/>}/>
            <KPI label="GROSS PIPELINE" value={fmtMoney(t.gross_pipeline_sales)} color={FN_GREEN}
                 icon={<TrendingUp size={11}/>}/>
            <KPI label="PROJECTED MRR" value={fmtMoney(t.projected_mrr)} color="#a855f7"
                 icon={<Wallet size={11}/>}/>
            <KPI label="ROI SATURATION"
                 value={`${t.stores_at_roi} / ${t.stores_total}`}
                 color={t.roi_saturation_pct >= 50 ? FN_GREEN : FN_AMBER}
                 icon={<Star size={11}/>}/>
          </div>
        )}

        {/* State accordions */}
        <div data-testid="regional-state-list">
          {(data?.states || []).map((s) => (
            <StateAccordion key={s.state} state={s}
                            isOpen={!!open[s.state]}
                            onToggle={() => setOpen((p) => ({ ...p, [s.state]: !p[s.state] }))}/>
          ))}
        </div>
      </div>
    </PilotShell>
  );
}

function KPI({ label, value, color, icon }) {
  return (
    <div style={{
      padding: "12px 14px", borderRadius: 5,
      border: `1px solid ${color}55`,
      background: `linear-gradient(155deg, ${color}12, rgba(8,18,34,0.6))`,
    }}>
      <div style={{ color: FN_DIM, fontFamily: "monospace", fontSize: 9,
                    letterSpacing: "0.22em", textTransform: "uppercase",
                    display: "flex", alignItems: "center", gap: 5 }}>
        {icon} {label}
      </div>
      <div style={{ color, fontWeight: 800, fontSize: 22, marginTop: 4, letterSpacing: 0.3 }}>
        {value}
      </div>
    </div>
  );
}

function StateAccordion({ state, isOpen, onToggle }) {
  const ratio = state.store_count
    ? Math.round((state.stores_at_roi / state.store_count) * 100)
    : 0;
  const stateColor = state.is_local ? FN_GREEN : FN_TEAL;

  return (
    <div data-testid={`regional-state-${state.state}`} style={{
      marginBottom: 12, borderRadius: 6, overflow: "hidden",
      border: `1px solid ${stateColor}55`,
    }}>
      <button onClick={onToggle} style={{
        width: "100%", cursor: "pointer",
        display: "flex", justifyContent: "space-between", alignItems: "center",
        padding: "14px 18px",
        background: `linear-gradient(155deg, ${stateColor}14, rgba(8,18,34,0.85))`,
        border: "none", color: FN_INK, textAlign: "left",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          {isOpen ? <ChevronDown size={14} color={stateColor}/> : <ChevronRight size={14} color={stateColor}/>}
          <span style={{ fontWeight: 800, fontSize: 18, letterSpacing: 0.4 }}>{state.state}</span>
          {state.is_local && (
            <span style={{
              padding: "2px 8px", borderRadius: 2,
              border: `1px solid ${FN_GREEN}88`, background: `${FN_GREEN}18`,
              color: FN_GREEN, fontFamily: "monospace", fontSize: 9,
              letterSpacing: "0.22em", textTransform: "uppercase",
            }}>● LOCAL HQ</span>
          )}
          <span style={{ color: FN_DIM, fontFamily: "monospace", fontSize: 11 }}>
            {state.store_count} stores · {state.units} units · {state.scans} scans
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, fontFamily: "monospace" }}>
          <span style={{ color: FN_DIM, fontSize: 11 }}>
            GROSS <span style={{ color: FN_GREEN }}>{fmtMoney(state.gross_pipeline_sales)}</span>
          </span>
          <span style={{
            padding: "2px 10px", borderRadius: 2,
            border: `1px solid ${ratio >= 50 ? FN_GREEN : FN_AMBER}88`,
            background: `${ratio >= 50 ? FN_GREEN : FN_AMBER}14`,
            color: ratio >= 50 ? FN_GREEN : FN_AMBER,
            fontSize: 10, letterSpacing: "0.2em", fontWeight: 700,
          }}>{state.stores_at_roi}/{state.store_count} ROI</span>
        </div>
      </button>

      {isOpen && (
        <div style={{ padding: "10px 14px", background: "rgba(2,8,16,0.6)" }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 10 }}>
            {state.stores.map((store) => <StoreCard key={`${store.city}_${store.store_id}`} store={store}/>)}
          </div>
        </div>
      )}
    </div>
  );
}

function StoreCard({ store }) {
  const met = store.roi_target_saturation_met;
  const color = met ? FN_GREEN : FN_AMBER;
  return (
    <div data-testid={`regional-store-${store.store_id || store.city}`} style={{
      border: `1px solid ${color}55`,
      background: `linear-gradient(155deg, ${color}08, rgba(8,18,34,0.8))`,
      borderRadius: 5, padding: 12,
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <Building2 size={12} color={color}/>
            <span style={{ fontWeight: 700, fontSize: 13 }}>{store.city}</span>
          </div>
          <div style={{ color: FN_DIM, fontFamily: "monospace", fontSize: 10,
                        letterSpacing: "0.18em", textTransform: "uppercase" }}>
            {store.store_id || "—"}
          </div>
        </div>
        <span style={{
          padding: "3px 8px", borderRadius: 2,
          border: `1px solid ${color}88`, background: `${color}12`, color,
          fontFamily: "monospace", fontSize: 9,
          letterSpacing: "0.2em", textTransform: "uppercase", fontWeight: 700,
        }}>{met ? "● ROI MET" : "○ PENDING"}</span>
      </div>

      <div style={{ marginTop: 10, display: "grid", gridTemplateColumns: "1fr 1fr",
                    gap: 8, fontFamily: "monospace", fontSize: 11 }}>
        <Stat label="UNITS" value={store.combined_units}/>
        <Stat label="SCANS" value={store.accumulated_scans}/>
        <Stat label="GROSS" value={fmtMoney(store.gross_pipeline_sales)} accent={FN_GREEN}/>
        <Stat label="OPEX (MRR)" value={fmtMoney(store.operational_expense_cost)} accent="#a855f7"/>
      </div>

      <div style={{ marginTop: 10, paddingTop: 8, borderTop: "1px dashed #1e293b" }}>
        <div style={{ color: FN_DIM, fontFamily: "monospace", fontSize: 9,
                      letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: 4 }}>
          CALLSIGNS
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
          {store.callsigns.map((c, i) => (
            <span key={c} style={{
              padding: "2px 7px", borderRadius: 2,
              border: `1px solid ${FN_TEAL}55`, background: `${FN_TEAL}10`,
              color: FN_TEAL, fontFamily: "monospace", fontSize: 9,
              letterSpacing: "0.1em",
            }} title={store.pilots[i] || ""}>{c}</span>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div>
      <div style={{ color: "#475569", fontSize: 9, letterSpacing: "0.16em" }}>{label}</div>
      <div style={{ color: accent || FN_INK, marginTop: 1 }}>{value}</div>
    </div>
  );
}

function Skeleton() {
  return (
    <div style={{ color: FN_DIM, fontFamily: "monospace", padding: 30,
                  textAlign: "center", letterSpacing: "0.2em", textTransform: "uppercase" }}>
      LOADING REGIONAL MESH…
    </div>
  );
}
