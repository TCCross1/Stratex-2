import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { HudCard } from "@/components/HudCard";
import { previewNDA, acceptNDA } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Shield, FileText } from "lucide-react";
import { toast } from "sonner";
import { StratexLogo } from "@/components/StratexBrand";

export default function NDAPage() {
  const navigate = useNavigate();
  const { user, refresh } = useAuth();
  const [text, setText] = useState("Loading NDA…");
  const [typed, setTyped] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => { previewNDA().then(d=>setText(d.rendered_text)).catch(()=>{}); }, []);

  const submit = async () => {
    if (typed.trim().toLowerCase() !== (user?.legal_name || "").trim().toLowerCase()) {
      toast.error(`Signature must match your registered legal name (${user?.legal_name}) exactly`);
      return;
    }
    setBusy(true);
    try {
      await acceptNDA(typed.trim());
      await refresh();
      toast.success("NDA signed — portal unlocked");
      navigate("/contractor");
    } catch (e) { toast.error(e.response?.data?.detail || e.message); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="nda-page" className="min-h-screen px-4 py-8 max-w-3xl mx-auto">
      <StratexLogo height={40} className="mb-6"/>
      <div className="flex items-center gap-2 text-teal font-mono text-[11px] tracking-widest uppercase mb-3"><Shield size={14}/> SECURE ONBOARDING • STEP 02</div>
      <h1 className="font-display text-2xl md:text-3xl uppercase tracking-[0.08em] text-silver mb-2" style={{ overflowWrap: "anywhere" }}>Mutual Non-Disclosure Agreement</h1>
      <p className="text-sm text-muted-hud font-body mb-5">Review the binding mutual NDA below, then affix your typed legal name to unlock the contractor portal. Your IP address and a UTC timestamp will be captured as part of the digital signature audit trail.</p>

      <HudCard className="p-4 mb-4">
        <pre data-testid="nda-text" className="font-mono text-[11px] text-silver whitespace-pre-wrap leading-relaxed max-h-[420px] overflow-auto"><FileText size={12} className="inline mr-1 text-teal"/>{text}</pre>
      </HudCard>

      <HudCard className="p-4">
        <label className="hud-label">Type your legal name exactly: <span className="text-teal">{user?.legal_name}</span></label>
        <input data-testid="nda-typed-name" className="hud-input" value={typed} onChange={(e)=>setTyped(e.target.value)} placeholder={user?.legal_name}/>
        <button onClick={submit} disabled={busy} className="btn-hud mt-3 w-full sm:w-auto" data-testid="nda-accept-btn">
          {busy ? "Signing…" : "I Agree & Sign"}
        </button>
      </HudCard>
    </div>
  );
}
