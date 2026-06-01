import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { HudCard } from "@/components/HudCard";
import { ASSETS } from "@/lib/constants";
import { loginStep1, loginStep2, signup, totpDebug } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Lock, Shield, KeyRound, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";
import QRCode from "qrcode";

function fmtErr(d) {
  if (!d) return "Something went wrong.";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((e) => e?.msg || JSON.stringify(e)).join(" ");
  return d?.msg || String(d);
}

export default function AuthPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [mode, setMode] = useState("login"); // login | signup
  // login
  const [email, setEmail] = useState("anthony@apexroofing.com");
  const [password, setPassword] = useState("Contractor!2026");
  const [totp, setTotp] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [step, setStep] = useState(1); // 1 = creds, 2 = totp
  const [busy, setBusy] = useState(false);

  // signup
  const [sEmail, setSEmail] = useState("");
  const [sPassword, setSPassword] = useState("");
  const [sLegal, setSLegal] = useState("");
  const [sCompany, setSCompany] = useState("");
  const [sRole, setSRole] = useState("contractor");
  const [qrUri, setQrUri] = useState("");
  const [qrDataUrl, setQrDataUrl] = useState("");
  const [tSecret, setTSecret] = useState("");
  // v3.42.0 — Tripwire registration array (contractor only).
  // 6 mandatory fields: Owner/Foreman/Sales Rep × (name + phone).
  const [tripwire, setTripwire] = useState({
    owner:     { name: "", phone: "" },
    foreman:   { name: "", phone: "" },
    sales_rep: { name: "", phone: "" },
  });
  const setTrip = (role, field, val) =>
    setTripwire((t) => ({ ...t, [role]: { ...t[role], [field]: val } }));
  const tripwireComplete =
    !!(tripwire.owner.name.trim() && tripwire.owner.phone.trim() &&
       tripwire.foreman.name.trim() && tripwire.foreman.phone.trim() &&
       tripwire.sales_rep.name.trim() && tripwire.sales_rep.phone.trim());

  const handleLogin = async (e) => {
    e?.preventDefault();
    if (busy) return;
    setBusy(true);
    try {
      if (step === 1) {
        const r = await loginStep1(email.trim().toLowerCase(), password);
        if (r.ceo_redirect) {
          toast.message(r.message || "CEO portal sign-in required.");
          navigate(`/ceo/login?email=${encodeURIComponent(r.email || email.trim().toLowerCase())}`);
          return;
        }
        if (r.mfa_required) {
          setStep(2);
          try {
            // demo helper to auto-fill TOTP in 1 click
            const d = await totpDebug(email.trim().toLowerCase());
            if (d?.current_code) setTotp(d.current_code);
          } catch (_) {}
        } else {
          login(r.access_token, r.user);
          toast.success("Logged in");
          navigate(r.user.role === "operator" ? "/operator" : "/contractor");
        }
      } else {
        const r = await loginStep2(email.trim().toLowerCase(), password, totp);
        login(r.access_token, r.user);
        toast.success("AUTHENTICATED");
        if (r.user.role === "contractor" && !r.user.nda_accepted) navigate("/nda");
        else navigate(r.user.role === "operator" ? "/operator" : "/contractor");
      }
    } catch (e) { toast.error(fmtErr(e.response?.data?.detail) || e.message); }
    finally { setBusy(false); }
  };

  const handleSignup = async (e) => {
    e?.preventDefault();
    if (busy) return;
    if (sRole === "contractor" && !tripwireComplete) {
      toast.error("Tripwire registration incomplete — Owner, Foreman & Sales Rep contact required.");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        email: sEmail.trim().toLowerCase(),
        password: sPassword,
        legal_name: sLegal,
        company_name: sCompany,
        role: sRole,
      };
      if (sRole === "contractor") {
        payload.tripwire_contacts = [
          { role: "owner",     name: tripwire.owner.name.trim(),     phone: tripwire.owner.phone.trim() },
          { role: "foreman",   name: tripwire.foreman.name.trim(),   phone: tripwire.foreman.phone.trim() },
          { role: "sales_rep", name: tripwire.sales_rep.name.trim(), phone: tripwire.sales_rep.phone.trim() },
        ];
      }
      const r = await signup(payload);
      setQrUri(r.totp_setup.uri);
      setTSecret(r.totp_setup.secret);
      const dataUrl = await QRCode.toDataURL(r.totp_setup.uri, { color: { dark: "#00F0FF", light: "#06080B" }, margin: 1, width: 220 });
      setQrDataUrl(dataUrl);
      toast.success("Account created — scan the TOTP QR code");
      setEmail(sEmail);
      setPassword(sPassword);
      setMode("login");
      setStep(1);
    } catch (e) { toast.error(fmtErr(e.response?.data?.detail) || e.message); }
    finally { setBusy(false); }
  };

  return (
    <div data-testid="auth-page" className="min-h-screen flex items-center justify-center px-4 py-10">
      <div className="w-full max-w-md">
        <Link to="/" className="flex items-center justify-center gap-3 mb-6">
          <img src={ASSETS.logo} alt="STRATEX" className="h-12 w-auto"/>
        </Link>
        <HudCard scanline className="p-6">
          <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase mb-2 flex items-center gap-2">
            <Shield size={12}/> SECURE PORTAL
          </div>
          <h1 className="font-display text-2xl uppercase tracking-[0.06em] text-silver mb-1" style={{ overflowWrap: "anywhere" }}>
            {mode === "login" ? (step === 1 ? "Sign In" : "Multi-Factor Verify") : "Create Account"}
          </h1>
          <p className="text-[11px] font-mono text-muted-hud mb-4">
            {mode === "login" ? "Bearer JWT + TOTP MFA" : "Encrypted at rest • TOTP required"}
          </p>

          {mode === "login" && step === 1 && (
            <form onSubmit={handleLogin} className="space-y-3">
              <div>
                <label className="hud-label">Email</label>
                <input data-testid="auth-email" type="email" required className="hud-input" value={email} onChange={(e)=>setEmail(e.target.value)} autoComplete="email"/>
              </div>
              <div>
                <label className="hud-label">Password</label>
                <div className="relative">
                  <input data-testid="auth-password" type={showPw ? "text" : "password"} required className="hud-input pr-12" value={password} onChange={(e)=>setPassword(e.target.value)} autoComplete="current-password"/>
                  <button type="button" onClick={()=>setShowPw(!showPw)} className="absolute right-2 top-1/2 -translate-y-1/2 text-muted-hud" aria-label="Toggle password">{showPw?<EyeOff size={16}/>:<Eye size={16}/>}</button>
                </div>
              </div>
              <button type="submit" disabled={busy} className="btn-hud w-full justify-center" data-testid="auth-submit-login">
                <Lock size={14}/> {busy?"…":"Continue"}
              </button>
            </form>
          )}

          {mode === "login" && step === 2 && (
            <form onSubmit={handleLogin} className="space-y-3">
              <div className="font-mono text-xs text-muted-hud mb-1">Account: <span className="text-teal">{email}</span></div>
              <div>
                <label className="hud-label">6-Digit TOTP Code (Google Authenticator / 1Password / Authy)</label>
                <input data-testid="auth-totp" autoFocus type="text" inputMode="numeric" pattern="\d{6}" maxLength="6" required className="hud-input text-center text-2xl tracking-[0.5em] font-mono" value={totp} onChange={(e)=>setTotp(e.target.value.replace(/\D/g,""))}/>
                <div className="text-[11px] font-mono text-muted-hud mt-1">(Demo: pre-populated from /api/auth/totp-debug)</div>
              </div>
              <div className="flex gap-2">
                <button type="button" onClick={()=>{setStep(1); setTotp("");}} className="btn-hud btn-hud-ghost flex-1 justify-center">Back</button>
                <button type="submit" disabled={busy || totp.length!==6} className="btn-hud flex-1 justify-center" data-testid="auth-submit-totp">
                  <KeyRound size={14}/> {busy?"…":"AUTHENTICATE"}
                </button>
              </div>
            </form>
          )}

          {mode === "signup" && !qrDataUrl && (
            <form onSubmit={handleSignup} className="space-y-3">
              <div className="grid grid-cols-2 gap-2">
                <button type="button" data-testid="role-contractor" onClick={()=>setSRole("contractor")} className={`hud-option ${sRole==="contractor"?"active":""}`}>Contractor</button>
                <button type="button" data-testid="role-operator" onClick={()=>setSRole("operator")} className={`hud-option ${sRole==="operator"?"active":""}`}>Operator</button>
              </div>
              <div><label className="hud-label">Legal Name</label><input data-testid="signup-legal" required className="hud-input" value={sLegal} onChange={(e)=>setSLegal(e.target.value)}/></div>
              {sRole==="contractor" && <div><label className="hud-label">Company</label><input data-testid="signup-company" required className="hud-input" value={sCompany} onChange={(e)=>setSCompany(e.target.value)}/></div>}
              <div><label className="hud-label">Email</label><input data-testid="signup-email" type="email" required className="hud-input" value={sEmail} onChange={(e)=>setSEmail(e.target.value)}/></div>
              <div><label className="hud-label">Password (≥ 10 chars)</label><input data-testid="signup-password" type="password" minLength={10} required className="hud-input" value={sPassword} onChange={(e)=>setSPassword(e.target.value)}/></div>

              {sRole === "contractor" && (
                <div data-testid="tripwire-block" className="mt-2 p-3 border border-volt/30 bg-[#0a1018]/70">
                  <div className="flex items-center gap-2 mb-1">
                    <Shield size={11} className="text-volt"/>
                    <span className="font-mono text-[10px] uppercase tracking-[0.28em] text-volt">
                      Tripwire Registration · Required
                    </span>
                  </div>
                  <p className="text-[10px] font-mono text-muted-hud leading-snug mb-3">
                    All three roles must be present so the geofence breach engine
                    can match phone pings on every active job.
                  </p>

                  {[
                    { key: "owner",     label: "Owner" },
                    { key: "foreman",   label: "Foreman" },
                    { key: "sales_rep", label: "Sales Rep" },
                  ].map((r) => (
                    <div key={r.key} className="grid grid-cols-2 gap-2 mb-2">
                      <div>
                        <label className="hud-label">{r.label} Name</label>
                        <input
                          data-testid={`tripwire-${r.key}-name`}
                          required
                          className="hud-input"
                          value={tripwire[r.key].name}
                          onChange={(e) => setTrip(r.key, "name", e.target.value)}
                          placeholder={`${r.label} legal name`}
                        />
                      </div>
                      <div>
                        <label className="hud-label">{r.label} Phone</label>
                        <input
                          data-testid={`tripwire-${r.key}-phone`}
                          required
                          type="tel"
                          inputMode="tel"
                          className="hud-input"
                          value={tripwire[r.key].phone}
                          onChange={(e) => setTrip(r.key, "phone", e.target.value)}
                          placeholder="+1 555 555 5555"
                        />
                      </div>
                    </div>
                  ))}

                  <div
                    className="font-mono text-[9.5px] uppercase tracking-[0.22em] mt-1"
                    style={{ color: tripwireComplete ? "#10B981" : "#F59E0B" }}
                    data-testid="tripwire-status"
                  >
                    {tripwireComplete
                      ? "✓ Tripwire array sealed — perimeter breach matcher ready"
                      : "⚠ Tripwire incomplete · blocks registration"}
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={busy || (sRole === "contractor" && !tripwireComplete)}
                className="btn-hud w-full justify-center"
                data-testid="signup-submit"
              >
                {busy?"…":"Create Account"}
              </button>
            </form>
          )}

          {mode === "signup" && qrDataUrl && (
            <div className="space-y-3">
              <div className="font-mono text-xs text-volt">Account created. Scan this QR with your authenticator:</div>
              <img src={qrDataUrl} alt="TOTP QR" className="mx-auto"/>
              <div className="font-mono text-[10px] text-muted-hud break-all">Manual key: <span className="text-teal">{tSecret}</span></div>
              <button onClick={()=>{setMode("login"); setQrDataUrl("");}} className="btn-hud w-full justify-center">Continue to Sign In</button>
            </div>
          )}

          <div className="hud-divider my-4"/>
          <button onClick={()=>{setMode(mode==="login"?"signup":"login"); setStep(1); setQrDataUrl("");}} className="text-[11px] font-mono uppercase tracking-widest text-teal hover:text-silver" data-testid="auth-switch-mode">
            {mode==="login" ? "→ Create new contractor / operator account" : "← Back to sign in"}
          </button>

          <div className="mt-2">
            <Link
              to="/ceo/login"
              data-testid="ceo-portal-link"
              className="inline-flex items-center gap-1.5 text-[10px] font-mono uppercase tracking-[0.25em] text-muted-hud hover:text-emerald-400 transition-colors"
            >
              <Lock size={10}/> Executive? → CEO Portal
            </Link>
          </div>

          <div className="my-4 flex items-center gap-3">
            <span className="flex-1 h-px bg-[#00F0FF]/20"/>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">or</span>
            <span className="flex-1 h-px bg-[#00F0FF]/20"/>
          </div>

          <button
            type="button"
            onClick={() => {
              // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
              const redirectUrl = window.location.origin + "/contractor";
              window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
            }}
            data-testid="google-signin"
            className="w-full flex items-center justify-center gap-2 border border-[#00F0FF]/40 bg-[#10141D] hover:bg-[#00F0FF]/10 text-silver py-2.5 transition-all"
          >
            <svg width="16" height="16" viewBox="0 0 48 48">
              <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3c-1.6 4.7-6.1 8-11.3 8-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.5 29.3 4.5 24 4.5 13.2 4.5 4.5 13.2 4.5 24S13.2 43.5 24 43.5c10.4 0 19.4-7.6 19.4-19.5 0-1.3-.1-2.3-.3-3.5z"/>
              <path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.6 16 18.9 13.5 24 13.5c3.1 0 5.9 1.2 8 3.1l5.7-5.7C34 6.5 29.3 4.5 24 4.5 16.2 4.5 9.5 9 6.3 14.7z"/>
              <path fill="#4CAF50" d="M24 43.5c5.2 0 9.9-2 13.4-5.3l-6.2-5.2c-2 1.4-4.6 2.2-7.2 2.2-5.2 0-9.6-3.3-11.2-8l-6.5 5C9.4 38.9 16.1 43.5 24 43.5z"/>
              <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.3-2.3 4.3-4.2 5.7l6.2 5.2c-.4.4 6.6-4.8 6.6-14.9 0-1.3-.1-2.3-.3-3.5z"/>
            </svg>
            <span className="font-mono text-[12px] uppercase tracking-widest">Continue with Google</span>
          </button>

          <div className="mt-6 border-t border-[#00F0FF]/20 pt-3 text-[10px] font-mono text-muted-hud leading-relaxed">
            <Shield size={10} className="inline mr-1 text-volt"/> Material costs, profit margins, overhead multipliers, and client financial data are subject to <span className="text-volt">hardware-isolated AES-256 encryption</span>. STRATEX operators have ZERO visibility into your proprietary business rules.
          </div>
        </HudCard>
      </div>
    </div>
  );
}
