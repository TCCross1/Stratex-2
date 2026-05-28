/**
 * InvestorAssistant — Floating AI tour-guide for the STRATEX™ investor walkthrough.
 *
 * Activates when the logged-in user has `tour_mode: true` (set on John of Crown
 * Roofing). Flow:
 *   1. On first authenticated render, shows a centered greeting card:
 *        "Hi {first_name}, it's so good to meet you. I'm here if you have any questions."
 *   2. After dismiss (or 9s auto-collapse), shrinks to a circular electric-teal
 *      orb in the lower-right corner. Pulses softly.
 *   3. Clicking the orb opens a chat panel; the assistant proactively explains
 *      whichever route the investor is on (one auto-briefing per route per session),
 *      and answers follow-ups via /api/assistant/chat (Claude Haiku 4.5).
 *
 * STRATEX palette: Electric Teal #00F5D4, Neon Orange #FF5400.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Sparkles, X, Send, Loader2, MapPin } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";

// --- Per-route briefings (ground truth fed to Claude + shown to the user) ---
const ROUTE_BRIEFINGS = [
  {
    match: (p) => p === "/" || p === "",
    title: "Landing · Strategic Thermal Reconnaissance",
    intro: "This is the public landing — our positioning, science copy, and the ROI funnel CTA. From here a prospect either books a demo or enters the calculator at /onboard.",
  },
  {
    match: (p) => p === "/onboard",
    title: "Onboarding ROI Calculator",
    intro: "Public funnel. A prospect drops in their leads-per-week / month / year and their 2-year historical sales — we annualize their book, estimate their overhead leak from the 5-leak band, and recommend a STRATEX tier. We also (newer) compare them against the 7 Lexington-area incumbent contractors.",
  },
  {
    match: (p) => p === "/contractor",
    title: "Contractor Pipeline",
    intro: "The roofing-company-owner's home base. Every job they've created, what stage it's at (Pending Capture → In Flight → Analyzed → Reported → Reconciled → Billed), and a 'New Job' button. Click any row to drill in.",
  },
  {
    match: (p) => p === "/contractor/jobs/new",
    title: "New Job Wizard",
    intro: "Geocoded address, square footage, roof complexity, homeowner contact. Submitting it dispatches the job to the operator board, where a STRATEX pilot picks it up for the drone flight.",
  },
  {
    match: (p) => p.startsWith("/contractor/jobs/"),
    title: "Job Detail · Contractor View",
    intro: "Everything tied to one job: the 3D roof mesh, the tri-layer structural forensics (thermal, structural, moisture), the dual-sided report (operator vs contractor), pricing, and the homeowner-facing summary.",
  },
  {
    match: (p) => p === "/contractor/materials",
    title: "Business Brain · Material Configurator",
    intro: "The contractor's confidential profit engine. AES-256-encrypted at rest. They lock in their material costs, labor blends, warranty rules — STRATEX uses this to auto-generate quotes that never violate their margin rules. Competitors can't see it; we can't see it.",
  },
  {
    match: (p) => p === "/operator",
    title: "Operator Job Board",
    intro: "What the STRATEX field pilot sees. Same jobs as the contractor view but every pricing/business field is redacted — the operator gets the address, the roof complexity, and a Launch button.",
  },
  {
    match: (p) => p.startsWith("/operator/jobs/") && !p.startsWith("/operator/launch/"),
    title: "Operator Job Detail",
    intro: "Pre-flight checklist for one job. Mission boundaries, no-fly zones, weather, and a Launch handoff to the Fleet Authorization step.",
  },
  {
    match: (p) => p.startsWith("/operator/launch/"),
    title: "Step 5 · Fleet Launch Authorization",
    intro: "The hardware-bound version of /launch. Same six telemetry checks; if all are green and the operator authorizes, the job transitions to IN_FLIGHT and an audit record lands in db.flight_authorizations.",
  },
  {
    match: (p) => p === "/launch",
    title: "Fleet Launch Demo",
    intro: "Live drone-bay telemetry over WebSocket. Six checks — Hatch, Battery, RTK GPS, Comm Uplink, Weather, Perimeter — must all turn Nominal (about 10 seconds) before the AUTHORIZE button enables. The wire schema matches the on-site hardware gateway exactly.",
  },
  {
    match: (p) => p === "/admin/sales",
    title: "Admin Sales Hub · Central Kentucky",
    intro: "The 7 seeded competitor targets in the Lexington radius. Sortable table on the left, dark-tile Leaflet map with pulsing status pins on the right. Click any row to open the CRM drawer — Outreach Notes, Call Logs, and Communication Templates.",
  },
  {
    match: (p) => p === "/admin/overseer",
    title: "Overseer · Telemetry-Halt Watchdog",
    intro: "If a drone's 3D-mesh renderer drops frames or a structural-forensics agent hits an anomaly, it auto-posts to /api/telemetry/halt and lands here. Filter chips: Open, Reviewed, Dismissed.",
  },
  {
    match: (p) => p === "/admin/flight-audit",
    title: "Flight Authorization Audit",
    intro: "Compliance trail. Every AUTHORIZE_FLEET_LAUNCH command — cloud or on-site — with the telemetry snapshot at the moment of authorization, the operator identity, and the job linkage. Click a row to expand.",
  },
  {
    match: (p) => p === "/admin/cv-ice-shield",
    title: "CV · Sub-Surface Ice & Water Shield",
    intro: "Every parsed valley frame our CV pipeline classifies — Ice & Water Shield confirmed, latent moisture, or low-confidence halt. The pipeline enforces ε=0.92, ΔT∈[0.5°C,1.5°C], a 36\"±2\" valley mask, and a post-sunset capture window. Anything below 0.90 composite confidence auto-routes to the Overseer queue for human review.",
  },
  {
    match: (p) => p === "/fleet",
    title: "Fleet Board",
    intro: "Real-time grid of every STRATEX drone unit — status, last-known location, current job. Shared between admin and the operations team.",
  },
  {
    match: (p) => p === "/billing",
    title: "Billing · Stripe TEST mode",
    intro: "Model A pricing. Stripe checkout for the three tiers (Starter, Growth Pro, Enterprise Elite). Today it's wired to the Stripe test key — flip one env var and it's production-ready.",
  },
];

const DEFAULT_BRIEFING = { title: "STRATEX", intro: "Tap any route in the nav and I'll explain what's on screen as you go." };

function briefingFor(path) {
  return ROUTE_BRIEFINGS.find((b) => b.match(path)) || DEFAULT_BRIEFING;
}

const GREETING_DISMISSED_KEY = "stratex_tour_greeting_dismissed";

export default function InvestorAssistant() {
  const { user } = useAuth();
  const loc = useLocation();

  const [greetOpen, setGreetOpen] = useState(false);
  const [panelOpen, setPanelOpen] = useState(false);
  const [messages, setMessages] = useState([]); // [{role, content}]
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const seenRoutesRef = useRef(new Set());
  const scrollRef = useRef(null);
  const firstName = user?.first_name || "there";

  const active = !!user?.tour_mode;
  const briefing = useMemo(() => briefingFor(loc.pathname), [loc.pathname]);

  // ----- Greeting on first authenticated render (per browser session) -----
  useEffect(() => {
    if (!active) return;
    const already = sessionStorage.getItem(GREETING_DISMISSED_KEY) === "1";
    if (already) return;
    const t = setTimeout(() => setGreetOpen(true), 350);
    return () => clearTimeout(t);
  }, [active]);

  function dismissGreeting() {
    sessionStorage.setItem(GREETING_DISMISSED_KEY, "1");
    setGreetOpen(false);
  }

  // ----- Auto-briefing when the investor lands on a new route -----
  useEffect(() => {
    if (!active) return;
    if (seenRoutesRef.current.has(loc.pathname)) return;
    seenRoutesRef.current.add(loc.pathname);
    if (!greetOpen) {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `**${briefing.title}** — ${briefing.intro}`,
          autoBriefing: true,
          route: loc.pathname,
        },
      ]);
    }
  }, [active, loc.pathname, briefing.title, briefing.intro, greetOpen]);

  // ----- Auto-scroll chat to bottom -----
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, panelOpen]);

  async function sendMessage() {
    const text = draft.trim();
    if (!text || sending) return;
    setDraft("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setSending(true);
    try {
      const r = await api.post("/assistant/chat", {
        session_id: sessionId,
        user_message: text,
        route: loc.pathname,
        route_briefing: `${briefing.title} — ${briefing.intro}`,
        user_first_name: firstName,
      });
      setSessionId(r.data.session_id);
      setMessages((m) => [...m, { role: "assistant", content: r.data.reply }]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        { role: "assistant", content: "I'm having trouble reaching the model right now — try again in a moment.", error: true },
      ]);
    } finally {
      setSending(false);
    }
  }

  if (!active) return null;

  return (
    <>
      {/* keyframes for the orb pulse */}
      <style>{`
        @keyframes tourOrbPulse { 0%,100% { box-shadow: 0 0 0 0 ${TEAL}55, 0 0 26px ${TEAL}66; } 50% { box-shadow: 0 0 0 14px ${TEAL}00, 0 0 28px ${TEAL}88; } }
        @keyframes tourFadeIn { from { opacity: 0; transform: scale(0.96) translateY(8px);} to { opacity: 1; transform: scale(1) translateY(0);} }
      `}</style>

      {/* ---------- Welcome greeting card ---------- */}
      {greetOpen && (
        <div
          data-testid="tour-greeting-card"
          className="fixed inset-0 z-[100] flex items-center justify-center p-6"
          style={{ background: "rgba(8,11,18,0.78)", backdropFilter: "blur(6px)", animation: "tourFadeIn .35s ease both" }}
        >
          <div
            className="max-w-md w-full p-6 md:p-7 relative"
            style={{
              background: "linear-gradient(180deg, #131A25 0%, #0D131C 100%)",
              border: `1px solid ${TEAL}`,
              boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 40px ${TEAL}33`,
            }}
          >
            <button
              onClick={dismissGreeting}
              data-testid="tour-greeting-close"
              className="absolute top-3 right-3 text-muted-hud hover:text-silver"
              aria-label="Close"
            >
              <X size={16}/>
            </button>
            <div className="flex items-center gap-3 mb-3">
              <span
                className="inline-flex items-center justify-center w-10 h-10 rounded-full"
                style={{ background: `${TEAL}22`, color: TEAL, boxShadow: `0 0 20px ${TEAL}55` }}
              >
                <Sparkles size={20}/>
              </span>
              <div>
                <div className="font-mono text-[10px] uppercase tracking-[0.28em]" style={{ color: TEAL }}>
                  STRATEX™ TOUR GUIDE
                </div>
                <div className="text-base font-semibold text-silver">Your private walkthrough</div>
              </div>
            </div>
            <p className="text-silver text-[15px] leading-relaxed">
              Hi <span style={{ color: TEAL }}>{firstName}</span>, it's so good to meet you.
              I'm here if you have any questions.
            </p>
            <p className="text-muted-hud text-[12.5px] leading-relaxed mt-3">
              I'll follow you through each section and explain what it does. Anything you want to know — just ask.
              You have full access to every portal: contractor, operator, admin, fleet — explore wherever you like.
            </p>
            <div className="flex gap-2 mt-5">
              <button
                onClick={() => { dismissGreeting(); setPanelOpen(true); }}
                data-testid="tour-greeting-open-chat"
                className="flex-1 py-2.5 text-sm uppercase tracking-[0.22em] font-bold"
                style={{
                  background: `linear-gradient(135deg, ${TEAL} 0%, #00BFA6 100%)`,
                  color: "#0B0F17",
                  boxShadow: `0 0 18px ${TEAL}55`,
                }}
              >
                Start the Tour
              </button>
              <button
                onClick={dismissGreeting}
                data-testid="tour-greeting-explore"
                className="px-4 py-2.5 text-xs uppercase tracking-[0.22em]"
                style={{ border: `1px solid ${TEAL}55`, color: TEAL, background: `${TEAL}0A` }}
              >
                Explore Alone
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ---------- Floating orb ---------- */}
      {!greetOpen && (
        <button
          onClick={() => setPanelOpen((o) => !o)}
          data-testid="tour-orb"
          aria-label="Open STRATEX tour guide"
          className="fixed z-[90] bottom-5 right-5 md:bottom-6 md:right-6 w-14 h-14 rounded-full inline-flex items-center justify-center"
          style={{
            background: panelOpen
              ? `linear-gradient(135deg, ${ORANGE} 0%, #B83A00 100%)`
              : `linear-gradient(135deg, ${TEAL} 0%, #00BFA6 100%)`,
            color: "#0B0F17",
            border: `1px solid ${panelOpen ? ORANGE : TEAL}`,
            animation: panelOpen ? "none" : "tourOrbPulse 2.2s ease-in-out infinite",
          }}
        >
          {panelOpen ? <X size={22}/> : <Sparkles size={22}/>}
        </button>
      )}

      {/* ---------- Chat panel ---------- */}
      {panelOpen && !greetOpen && (
        <div
          data-testid="tour-panel"
          className="fixed z-[91] bottom-24 right-5 md:right-6 w-[92vw] max-w-[380px] md:max-w-[420px] flex flex-col"
          style={{
            height: "min(560px, 70vh)",
            background: "linear-gradient(180deg, #131A25 0%, #0D131C 100%)",
            border: `1px solid ${TEAL}`,
            boxShadow: `0 30px 80px rgba(0,0,0,0.6), 0 0 30px ${TEAL}33`,
            animation: "tourFadeIn .25s ease both",
          }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: "#212A37" }}>
            <div className="flex items-center gap-2 min-w-0">
              <span
                className="inline-flex items-center justify-center w-7 h-7 rounded-full flex-shrink-0"
                style={{ background: `${TEAL}22`, color: TEAL }}
              >
                <Sparkles size={14}/>
              </span>
              <div className="min-w-0">
                <div className="font-mono text-[9px] uppercase tracking-[0.28em]" style={{ color: TEAL }}>STRATEX Guide</div>
                <div className="text-sm text-silver truncate flex items-center gap-1.5">
                  <MapPin size={11} className="text-muted-hud"/>
                  <span className="truncate">{briefing.title}</span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setPanelOpen(false)}
              data-testid="tour-panel-close"
              className="text-muted-hud hover:text-silver"
              aria-label="Close"
            >
              <X size={16}/>
            </button>
          </div>

          {/* Messages */}
          <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-3 space-y-2.5" data-testid="tour-messages">
            {messages.length === 0 && (
              <div className="text-xs italic text-muted-hud font-body leading-relaxed">
                Move around the app — I'll narrate each screen. Or ask me anything below.
              </div>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                className="text-[13px] leading-relaxed px-3 py-2 rounded-md"
                style={
                  m.role === "user"
                    ? { background: "#212A37", color: "#E2E8F0", marginLeft: "20%" }
                    : m.autoBriefing
                    ? { background: `${TEAL}10`, color: "#E2E8F0", border: `1px solid ${TEAL}33` }
                    : m.error
                    ? { background: `${ORANGE}10`, color: "#E2E8F0", border: `1px solid ${ORANGE}55` }
                    : { background: "#0F1620", color: "#E2E8F0", border: "1px solid #212A37" }
                }
              >
                {m.content.split("\n").map((line, k) => (
                  <div key={k}>
                    {line.split(/(\*\*[^*]+\*\*)/g).map((seg, sx) =>
                      seg.startsWith("**") && seg.endsWith("**") ? (
                        <strong key={sx} style={{ color: TEAL }}>{seg.slice(2, -2)}</strong>
                      ) : (
                        <span key={sx}>{seg}</span>
                      )
                    )}
                  </div>
                ))}
              </div>
            ))}
            {sending && (
              <div className="inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-widest" style={{ color: TEAL }}>
                <Loader2 size={12} className="animate-spin"/> thinking…
              </div>
            )}
          </div>

          {/* Composer */}
          <form
            onSubmit={(e) => { e.preventDefault(); sendMessage(); }}
            className="border-t p-2.5 flex items-center gap-2"
            style={{ borderColor: "#212A37" }}
          >
            <input
              data-testid="tour-input"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask about anything on screen…"
              className="flex-1 bg-[#0B0F17] border px-3 py-2 text-[13px] text-silver placeholder:text-muted-hud focus:outline-none"
              style={{ borderColor: "#212A37" }}
              disabled={sending}
            />
            <button
              type="submit"
              data-testid="tour-send"
              disabled={sending || !draft.trim()}
              className="px-3 py-2 inline-flex items-center justify-center"
              style={{
                background: sending || !draft.trim() ? "#212A37" : `linear-gradient(135deg, ${TEAL} 0%, #00BFA6 100%)`,
                color: sending || !draft.trim() ? "#7A8699" : "#0B0F17",
                border: `1px solid ${sending || !draft.trim() ? "#3A4350" : TEAL}`,
              }}
            >
              <Send size={14}/>
            </button>
          </form>
        </div>
      )}
    </>
  );
}
