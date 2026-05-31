/**
 * /ceo/login — Future-Noire CEO sign-in. Distinct from the main /auth flow.
 *
 * This is the ONLY way into the CEO Command Center. On success the JWT is
 * stored in the same `stratex_token` localStorage key as every other portal,
 * so `useAuth()` immediately recognises the user as `role: "ceo"`.
 */
import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth } from "@/lib/auth";
import { Lock, AlertTriangle, ArrowRight } from "lucide-react";

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export default function CeoLogin() {
  const nav = useNavigate();
  const { setUser } = useAuth();
  const [email, setEmail] = useState("Tony@Stratexdrone.com");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const { data } = await axios.post(`${API}/auth/ceo/login`, { email, password });
      localStorage.setItem("stratex_token", data.access_token);
      localStorage.setItem("stratex_refresh", data.refresh_token);
      setUser(data.user);
      nav("/ceo/command", { replace: true });
    } catch (e2) {
      const detail = e2?.response?.data?.detail;
      setErr(typeof detail === "string" ? detail : "Authentication failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4" style={{
      background: "radial-gradient(ellipse at top, #0f172a 0%, #080c14 70%, #030712 100%)",
    }} data-testid="ceo-login-root">
      <FutureNoireCSS/>
      <form onSubmit={submit} className="w-full max-w-md relative" data-testid="ceo-login-form">
        {/* Diagonal neon corner glow */}
        <div className="absolute -top-12 -left-12 w-44 h-44 pointer-events-none"
             style={{ background: "radial-gradient(circle, rgba(6,182,212,0.25), transparent 70%)" }}/>
        <div className="absolute -bottom-10 -right-10 w-44 h-44 pointer-events-none"
             style={{ background: "radial-gradient(circle, rgba(168,85,247,0.18), transparent 70%)" }}/>

        <div className="relative" style={{
          background: "linear-gradient(160deg, #0f172a 0%, #0b1329 100%)",
          border: "1px solid #1e293b",
          padding: "36px 32px",
          borderRadius: 4,
          boxShadow: "0 30px 80px rgba(0,0,0,0.55), inset 0 0 0 1px rgba(16,185,129,0.05)",
        }}>
          <div className="flex items-center gap-3 mb-7">
            <div className="flex items-center justify-center" style={{
              width: 46, height: 46, borderRadius: 4,
              background: "rgba(16,185,129,0.08)",
              border: "1px solid rgba(16,185,129,0.55)",
              boxShadow: "0 0 12px rgba(16,185,129,0.25)",
            }}>
              <Lock size={20} color="#10b981"/>
            </div>
            <div>
              <div className="font-mono text-[10px] tracking-[0.4em] uppercase" style={{ color: "#10b981" }}>
                // STRATEX // CEO PORTAL
              </div>
              <h1 className="font-bold text-[22px] tracking-wide" style={{ color: "#e2e8f0" }}>
                Command Clearance
              </h1>
            </div>
          </div>

          <p className="text-[12px] mb-6 leading-relaxed" style={{ color: "#64748b" }}>
            This is the ONLY entry point to the BUILD-SUPPLY GM Command Center.
            Sessions are isolated from the contractor & operator portals.
          </p>

          <label className="block text-[9.5px] font-mono tracking-[0.3em] uppercase mb-1.5" style={{ color: "#64748b" }}>
            CEO Email
          </label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            autoComplete="username"
            data-testid="ceo-email"
            className="w-full px-3 py-2.5 mb-4 font-mono text-[13px] outline-none transition-colors"
            style={{
              background: "#0b1329",
              border: "1px solid #1e293b",
              color: "#e2e8f0",
              borderRadius: 2,
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = "#10b981"}
            onBlur={(e) => e.currentTarget.style.borderColor = "#1e293b"}
          />

          <label className="block text-[9.5px] font-mono tracking-[0.3em] uppercase mb-1.5" style={{ color: "#64748b" }}>
            Passphrase
          </label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            autoComplete="current-password"
            data-testid="ceo-password"
            className="w-full px-3 py-2.5 mb-6 font-mono text-[14px] tracking-[0.3em] outline-none transition-colors"
            style={{
              background: "#0b1329",
              border: "1px solid #1e293b",
              color: "#e2e8f0",
              borderRadius: 2,
            }}
            onFocus={(e) => e.currentTarget.style.borderColor = "#10b981"}
            onBlur={(e) => e.currentTarget.style.borderColor = "#1e293b"}
          />

          {err && (
            <div className="flex items-center gap-2 mb-5 px-3 py-2"
              style={{ background: "rgba(244,63,94,0.08)", border: "1px solid #f43f5e", borderRadius: 2 }}
              data-testid="ceo-error">
              <AlertTriangle size={13} color="#f43f5e"/>
              <span className="text-[11.5px] font-mono" style={{ color: "#f43f5e" }}>{err}</span>
            </div>
          )}

          <button
            type="submit"
            disabled={busy}
            data-testid="ceo-submit"
            className="w-full py-3 font-mono text-[11px] tracking-[0.35em] uppercase font-bold inline-flex items-center justify-center gap-2 transition-all disabled:opacity-50"
            style={{
              background: "linear-gradient(90deg, #10b981, #06b6d4)",
              color: "#030712",
              border: 0,
              borderRadius: 2,
              boxShadow: "0 8px 20px rgba(16,185,129,0.25)",
            }}>
            {busy ? "// AUTHENTICATING…" : <>Enter Command Center <ArrowRight size={14}/></>}
          </button>

          <div className="mt-6 pt-4 text-center font-mono text-[9px] tracking-[0.3em] uppercase"
               style={{ color: "#64748b", borderTop: "1px solid #1e293b" }}>
            STX LINK SECURE · Single-tenant ceo session
          </div>
        </div>
      </form>
    </div>
  );
}

function FutureNoireCSS() {
  return (
    <style>{`
      :root {
        --fn-bg: #080c14;
        --fn-card: #0f172a;
        --fn-input: #0b1329;
        --fn-cyan: #06b6d4;
        --fn-purple: #a855f7;
        --fn-green: #10b981;
        --fn-magenta: #f43f5e;
        --fn-amber: #f59e0b;
        --fn-text: #cbd5e1;
        --fn-muted: #64748b;
      }
    `}</style>
  );
}
