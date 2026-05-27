import React, { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { HudCard } from "@/components/HudCard";
import { getBillingPlans, getBillingMe, createCheckout, getCheckoutStatus, getBillingMeter } from "@/lib/api";
import { Check, Lock, CreditCard, Crown, Rocket, Loader2, Receipt, TrendingUp, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const TIER_ICONS = { on_demand: Rocket, volume_builder: Crown };
const TIER_ACCENT = { on_demand: "teal", volume_builder: "orange" };

export default function Pricing() {
  const [plans, setPlans] = useState(null);
  const [me, setMe] = useState(null);
  const [meter, setMeter] = useState(null);
  const [busy, setBusy] = useState(null);

  useEffect(() => {
    getBillingPlans().then(setPlans).catch(()=>{});
    getBillingMe().then(setMe).catch(()=>{});
    getBillingMeter().then(setMeter).catch(()=>{});
  }, []);

  const subscribe = async (tier) => {
    setBusy(tier);
    try {
      const r = await createCheckout(tier, window.location.origin);
      window.location.href = r.url;
    } catch (e) {
      toast.error(e.response?.data?.detail || e.message);
      setBusy(null);
    }
  };

  if (!plans) return <div className="p-10 text-muted-hud font-mono">Loading plans…</div>;
  const order = ["on_demand", "volume_builder"];

  return (
    <div data-testid="pricing-page" className="px-4 md:px-10 py-10 max-w-[1400px] mx-auto">
      <div className="text-center mb-10">
        <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase mb-2">// MODEL A · PREMIUM FLEET DEPLOYMENT ENGINE</div>
        <h1 className="font-display text-[1.75rem] sm:text-4xl md:text-5xl uppercase tracking-[0.04em] sm:tracking-[0.08em] text-silver" style={{overflowWrap:"anywhere",wordBreak:"break-word"}}>
          Activate Your <span className="text-teal glow-teal">Recon Fleet</span>
        </h1>
        <p className="mt-3 text-muted-hud max-w-2xl mx-auto font-body text-sm md:text-base">
          Every drop runs through a mandatory 3-phase Risk Engine before the trailer hatch opens. Locked under AES-256 — STRATEX™ never touches your business multipliers.
        </p>
        {me?.subscription_tier && (
          <div className="mt-4 inline-flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest text-volt border border-[#39FF14]/40 px-3 py-1">
            <Check size={11}/> ACTIVE: {plans.tiers[me.subscription_tier]?.name || me.subscription_tier} — {me.subscription_status}
          </div>
        )}
      </div>

      <div className="grid md:grid-cols-2 gap-5 max-w-4xl mx-auto">
        {order.map((k) => {
          const t = plans.tiers[k];
          if (!t) return null;
          const Icon = TIER_ICONS[k];
          const accent = TIER_ACCENT[k];
          const accentColor = accent === "orange" ? "#FF5500" : "#00F0FF";
          const isCurrent = me?.subscription_tier === k && me?.subscription_status === "active";
          const isPro = t.popular;
          return (
            <HudCard key={k} scanline={isPro} alert={isPro} className="p-6 relative transition-transform hover:-translate-y-1" data-testid={`tier-${k}`}>
              {isPro && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-plasma text-obsidian font-mono text-[10px] tracking-widest uppercase px-3 py-0.5">CORE TARGET</div>
              )}
              <div className="flex items-center gap-2 mb-3" style={{ color: accentColor }}>
                <Icon size={18} strokeWidth={1.5}/>
                <span className="font-mono text-[11px] uppercase tracking-widest">{t.name}</span>
              </div>
              <div className="font-display text-4xl text-silver mb-1">
                ${t.price.toFixed(0)}
                <span className="text-[12px] font-mono text-muted-hud uppercase tracking-widest ml-2">/ mo retainer</span>
              </div>
              <div className="font-mono text-[11px] text-muted-hud uppercase tracking-widest mb-1">
                {t.included_drops > 0 ? <><span className="text-volt">{t.included_drops} drops included</span> · then ${t.extra_drop_price.toFixed(0)} / drop</> : <><span className="text-plasma">0 included drops</span> · ${t.extra_drop_price.toFixed(0)} per drop</>}
              </div>
              <p className="text-muted-hud font-body text-sm mb-4 mt-2">{t.blurb}</p>

              <ul className="space-y-2 mb-6">
                {t.features.map((f, i) => (
                  <li key={i} className="flex items-start gap-2 text-silver text-sm">
                    <Check size={14} className="mt-0.5 shrink-0" style={{ color: accentColor }}/>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>

              <button onClick={()=>subscribe(k)} disabled={busy===k || isCurrent} data-testid={`subscribe-${k}`} className={`btn-hud w-full justify-center ${isPro ? "btn-hud-alert" : ""}`}>
                {isCurrent ? <><Check size={14}/> Current Plan</> : busy===k ? <><Loader2 size={14} className="animate-spin"/> Redirecting…</> : <><CreditCard size={14}/> Subscribe</>}
              </button>
            </HudCard>
          );
        })}
      </div>

      {/* Risk Engine ROI panel */}
      <div className="mt-10 grid md:grid-cols-3 gap-3 max-w-4xl mx-auto">
        <HudCard className="p-4">
          <div className="font-mono text-[10px] tracking-widest text-teal uppercase mb-1 flex items-center gap-1.5"><AlertTriangle size={11}/> DRY-RUN PROTECTION</div>
          <div className="font-display text-2xl text-silver">$150</div>
          <p className="text-[11px] text-muted-hud mt-1">Auto-billed when access blocked by locked gates / unnotified homeowners / aggressive animals. Your fleet never loses money on disorganized contractors.</p>
        </HudCard>
        <HudCard className="p-4">
          <div className="font-mono text-[10px] tracking-widest text-volt uppercase mb-1 flex items-center gap-1.5"><Lock size={11}/> AUDIT TRAIL</div>
          <div className="font-display text-2xl text-silver">IMMUTABLE</div>
          <p className="text-[11px] text-muted-hud mt-1">Every Phase 1/2/3 check is sealed to an append-only log. Bulletproof against property-damage disputes and lowers your commercial hull premiums.</p>
        </HudCard>
        <HudCard className="p-4">
          <div className="font-mono text-[10px] tracking-widest text-plasma uppercase mb-1 flex items-center gap-1.5"><TrendingUp size={11}/> NET MARGIN</div>
          <div className="font-display text-2xl text-silver">80%</div>
          <p className="text-[11px] text-muted-hud mt-1">Per Volume Builder account at 8 jobs/mo: $1,790 revenue − $360 variable cost = $1,430 net.</p>
        </HudCard>
      </div>

      {/* Current month meter */}
      {meter && (
        <HudCard scanline className="mt-6 p-5 max-w-4xl mx-auto" data-testid="invoice-meter">
          <div className="flex items-center gap-2 mb-3 font-mono text-[11px] uppercase tracking-widest text-teal"><Receipt size={12}/> Current Month — {meter.bucket} · Upcoming Invoice</div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-3">
            <Meter label="Retainer" value={`$${meter.monthly_retainer.toFixed(2)}`}/>
            <Meter label="Drops Used" value={`${meter.drops_used} / ${meter.drops_included || "∞"}`} accent={meter.overage_drops>0?"orange":"volt"}/>
            <Meter label={`Overage @ $${meter.overage_drop_price.toFixed(0)}`} value={`$${meter.overage_charges_usd.toFixed(2)}`} accent={meter.overage_charges_usd>0?"orange":"muted"}/>
            <Meter label="Dry-Run Penalties" value={`$${meter.dry_run_charges_usd.toFixed(2)} (${meter.dry_run_count})`} accent={meter.dry_run_charges_usd>0?"orange":"muted"}/>
            <Meter label="Estimated Total" value={`$${meter.estimated_invoice_total.toFixed(2)}`} accent="orange" big/>
          </div>
          <div className="text-[10px] font-mono text-muted-hud uppercase tracking-widest">Penalties + overage roll into next billing cycle.</div>
        </HudCard>
      )}

      <div className="text-center mt-10 font-mono text-[10px] uppercase tracking-widest text-muted-hud flex items-center justify-center gap-2">
        <Lock size={11} className="text-volt"/> Stripe TEST mode · Card 4242 4242 4242 4242 will succeed
      </div>
    </div>
  );
}

function Meter({ label, value, accent, big }) {
  const c = accent==="orange"?"text-plasma":accent==="volt"?"text-volt":accent==="muted"?"text-muted-hud":"text-teal";
  return (
    <div className="border-l border-[#00F0FF]/30 pl-2">
      <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">{label}</div>
      <div className={`${big?"font-display text-2xl":"font-mono text-base"} ${c}`}>{value}</div>
    </div>
  );
}

export function BillingSuccess() {
  const loc = useLocation();
  const navigate = useNavigate();
  const [state, setState] = useState({ phase: "polling", attempts: 0, data: null });

  useEffect(() => {
    const sp = new URLSearchParams(loc.search);
    const session_id = sp.get("session_id");
    if (!session_id) { setState({ phase: "missing" }); return; }
    let attempts = 0;
    let cancelled = false;
    const poll = async () => {
      if (cancelled) return;
      attempts += 1;
      try {
        const d = await getCheckoutStatus(session_id);
        if (d.payment_status === "paid") { setState({ phase: "paid", data: d }); return; }
        if (d.status === "expired") { setState({ phase: "expired", data: d }); return; }
      } catch (e) { /* ignore */ }
      if (attempts >= 8) { setState({ phase: "timeout" }); return; }
      setState((s)=>({ ...s, attempts }));
      setTimeout(poll, 2000);
    };
    poll();
    return () => { cancelled = true; };
  }, [loc.search]);

  return (
    <div data-testid="billing-success" className="min-h-[70vh] flex items-center justify-center px-4">
      <HudCard scanline className="p-10 text-center max-w-md w-full">
        {state.phase === "polling" && (
          <>
            <Loader2 size={32} className="text-teal mx-auto animate-spin"/>
            <h2 className="font-display text-2xl uppercase tracking-widest text-silver mt-4">Confirming Payment</h2>
            <p className="text-muted-hud text-sm mt-2 font-mono">Polling Stripe… attempt {state.attempts}/8</p>
          </>
        )}
        {state.phase === "paid" && (
          <>
            <Check size={36} className="text-volt mx-auto"/>
            <h2 className="font-display text-2xl uppercase tracking-widest text-volt mt-4">Subscription Active</h2>
            <p className="text-muted-hud text-sm mt-2">Tier upgraded to <span className="text-teal uppercase">{state.data?.metadata?.tier}</span>. Recon fleet unlocked.</p>
            <button onClick={()=>navigate("/contractor")} data-testid="billing-success-continue" className="btn-hud mt-6">Open Contractor Portal</button>
          </>
        )}
        {state.phase === "expired" && (<><h2 className="font-display text-xl uppercase tracking-widest text-plasma">Session Expired</h2><button onClick={()=>navigate("/billing")} className="btn-hud btn-hud-ghost mt-4">Try Again</button></>)}
        {state.phase === "timeout" && (<><h2 className="font-display text-xl uppercase tracking-widest text-muted-hud">Still Processing</h2><p className="text-muted-hud text-sm mt-2">Confirmation taking longer than expected. You'll receive an email shortly.</p><button onClick={()=>navigate("/contractor")} className="btn-hud mt-4">Back to Portal</button></>)}
        {state.phase === "missing" && (<><h2 className="font-display text-xl uppercase tracking-widest text-muted-hud">No Session</h2><button onClick={()=>navigate("/billing")} className="btn-hud btn-hud-ghost mt-4">Choose a Plan</button></>)}
      </HudCard>
    </div>
  );
}
