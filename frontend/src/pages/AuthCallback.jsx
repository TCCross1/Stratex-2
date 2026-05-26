import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { googleSessionExchange } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Shield, Loader2 } from "lucide-react";
import { toast } from "sonner";

// REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
export default function AuthCallback() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const processed = useRef(false);

  useEffect(() => {
    if (processed.current) return;
    processed.current = true;
    const hash = window.location.hash || "";
    const m = hash.match(/session_id=([^&]+)/);
    if (!m) { navigate("/auth", { replace: true }); return; }
    const session_id = decodeURIComponent(m[1]);
    (async () => {
      try {
        const r = await googleSessionExchange(session_id);
        login(r.access_token, r.user);
        toast.success(`Welcome, ${r.user.legal_name || r.user.email}`);
        // Strip hash & route to portal (NDA gate handled by Protected wrapper)
        window.history.replaceState({}, "", window.location.pathname);
        navigate(r.user.role === "operator" ? "/operator" : "/contractor", { replace: true });
      } catch (e) {
        toast.error(e.response?.data?.detail || "Google sign-in failed");
        navigate("/auth", { replace: true });
      }
    })();
  }, [login, navigate]);

  return (
    <div data-testid="auth-callback" className="min-h-screen flex items-center justify-center px-4">
      <div className="text-center">
        <Shield size={28} className="text-teal mx-auto"/>
        <Loader2 size={20} className="text-teal mx-auto animate-spin mt-3"/>
        <div className="mt-4 font-mono text-[11px] tracking-widest uppercase text-muted-hud">Verifying Google identity…</div>
      </div>
    </div>
  );
}
