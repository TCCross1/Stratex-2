// STRATEX™ — TC, the in-app AI Project Manager.
//
// Renders:
//   • A floating "TC" launcher pill (bottom-right) on every route
//   • A glass cockpit chat panel that streams Claude tokens via SSE
//   • Page-aware briefing as the first message (auto-fetched from /api/tc/page-guide)
//   • Three suggested quick-questions per page, contextually tuned

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { MessageCircle, X, Send, Loader2, Sparkles } from "lucide-react";

const ACCENTS = {
  cyan: "#00E5FF", gold: "#D4B86A", green: "#00FF9C", magenta: "#FF2D78",
};

// Static fallback briefings — only used until SSE responds.
const QUICK_QUESTIONS = {
  default: [
    "What is STRATEX™ in one sentence?",
    "Where do I start?",
    "Walk me through the demo.",
  ],
  "/deck": [
    "What does the Command Deck show?",
    "Where is the Property Passport?",
    "How do I open the Reports Binder?",
  ],
  "/reports/binder": [
    "What's on each page of this report?",
    "Where's the final pricing?",
    "How do I download just one page?",
  ],
  "/passport/": [
    "What is the Property Passport?",
    "What does the seal mean?",
    "Why does the carrier link matter?",
  ],
  "/contractor/verify": [
    "Why do I need 3 references?",
    "What unlocks the dashboard?",
    "How long does verification take?",
  ],
  "/gm/roster": [
    "How is sell-price calculated?",
    "What's the MASTER/PREMIER/STANDARD tier?",
    "How do I add a brand?",
  ],
  "/": [
    "What's on the left rail?",
    "How do I close an app window?",
    "Where is the Property Passport demo?",
  ],
};

function pickQuestions(route) {
  for (const k of Object.keys(QUICK_QUESTIONS)) {
    if (k !== "default" && route.startsWith(k)) return QUICK_QUESTIONS[k];
  }
  return QUICK_QUESTIONS.default;
}

// ─────────────────────────────────────────────────────────────────────
// Streaming SSE client.
// ─────────────────────────────────────────────────────────────────────
async function streamTc({ API, body, onToken, onDone, onError }) {
  try {
    const r = await fetch(`${API}/api/tc/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!r.ok || !r.body) throw new Error(`http ${r.status}`);
    const reader = r.body.getReader();
    const decoder = new TextDecoder();
    let buf = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += decoder.decode(value, { stream: true });
      let idx;
      while ((idx = buf.indexOf("\n\n")) !== -1) {
        const event = buf.slice(0, idx);
        buf = buf.slice(idx + 2);
        if (event.startsWith("event: error")) {
          const m = event.match(/data:\s*(.*)/);
          throw new Error(m ? m[1] : "stream error");
        }
        if (event.startsWith("event: done")) { onDone(); return; }
        if (event.startsWith("data: ")) {
          onToken(event.slice(6));
        }
      }
    }
    onDone();
  } catch (e) {
    onError(e);
  }
}

// ─────────────────────────────────────────────────────────────────────
// Main component
// ─────────────────────────────────────────────────────────────────────
export default function TcAssistant() {
  const API = process.env.REACT_APP_BACKEND_URL;
  const loc = useLocation();
  const [open, setOpen] = useState(false);
  const [briefing, setBriefing] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [streaming, setStreaming] = useState(false);
  const sessionIdRef = useRef(`tc-${Math.random().toString(36).slice(2, 10)}`);
  const scrollRef = useRef(null);

  // Pull the route briefing whenever the route changes (and we're open).
  useEffect(() => {
    if (!open) return;
    (async () => {
      try {
        const r = await fetch(`${API}/api/tc/page-guide?route=${encodeURIComponent(loc.pathname)}`);
        const j = await r.json();
        setBriefing(j.briefing || "");
      } catch { /* ignore */ }
    })();
  }, [API, loc.pathname, open]);

  // Auto-scroll on new message tokens
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, streaming]);

  const suggested = useMemo(() => pickQuestions(loc.pathname), [loc.pathname]);

  const send = async (text) => {
    const userText = (text ?? input).trim();
    if (!userText || streaming) return;
    const history = messages.map((m) => ({ role: m.role, content: m.content }));
    setMessages((m) => [...m, { role: "user", content: userText }, { role: "assistant", content: "" }]);
    setInput("");
    setStreaming(true);

    await streamTc({
      API,
      body: {
        message: userText,
        route: loc.pathname,
        history,
        session_id: sessionIdRef.current,
      },
      onToken: (tok) => {
        setMessages((m) => {
          const copy = [...m];
          const last = copy[copy.length - 1];
          if (last && last.role === "assistant") {
            copy[copy.length - 1] = { ...last, content: last.content + tok };
          }
          return copy;
        });
      },
      onDone: () => setStreaming(false),
      onError: (e) => {
        setMessages((m) => {
          const copy = [...m];
          copy[copy.length - 1] = {
            role: "assistant",
            content: `TC offline — ${e?.message || "stream interrupted"}. Try again, Commander.`,
            err: true,
          };
          return copy;
        });
        setStreaming(false);
      },
    });
  };

  // ╔═════════════════ FLOATING LAUNCHER PILL ════════════════════╗
  if (!open) {
    return (
      <button
        data-testid="tc-launcher"
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-50 rounded-full px-4 py-3 flex items-center gap-2 transition hover:scale-105 group"
        style={{
          background: "linear-gradient(135deg, rgba(0,229,255,0.20) 0%, rgba(212,184,106,0.15) 100%)",
          border: `1.5px solid ${ACCENTS.cyan}`,
          boxShadow:
            `0 0 0 1px ${ACCENTS.cyan}22, ` +
            `0 0 24px ${ACCENTS.cyan}55, ` +
            `inset 0 0 18px ${ACCENTS.cyan}15`,
          backdropFilter: "blur(8px)",
          fontFamily: "'Sora', sans-serif",
        }}
      >
        {/* "TC" avatar bubble */}
        <span className="grid place-items-center rounded-full"
              style={{ width: 32, height: 32,
                       background: "linear-gradient(135deg, #00E5FF 0%, #D4B86A 100%)",
                       color: "#02060B",
                       fontWeight: 900, fontSize: 13, letterSpacing: 1,
                       boxShadow: "inset 0 0 6px rgba(0,0,0,0.35)" }}>
          TC
        </span>
        <span className="text-left">
          <span className="block font-mono text-[8.5px] tracking-[0.28em] uppercase text-cyan-300">// AI PM · ASK ME ANYTHING</span>
          <span className="block font-display text-[12px] uppercase tracking-[0.06em] text-white">Talk to TC</span>
        </span>
        <Sparkles size={12} className="text-cyan-200 ml-1"/>
      </button>
    );
  }

  // ╔═════════════════ CHAT COCKPIT ══════════════════════════════╗
  return (
    <div data-testid="tc-panel"
         className="fixed bottom-5 right-5 z-50 w-[min(420px,calc(100vw-24px))] max-h-[80vh] flex flex-col rounded-xl overflow-hidden"
         style={{
           background: "linear-gradient(180deg, rgba(8,14,24,0.96) 0%, rgba(4,8,14,0.98) 100%)",
           border: `1.5px solid ${ACCENTS.cyan}88`,
           boxShadow:
             `0 0 0 1px ${ACCENTS.cyan}22, ` +
             `0 24px 48px rgba(0,0,0,0.5), ` +
             `inset 0 0 36px ${ACCENTS.cyan}10`,
           backdropFilter: "blur(14px)",
           fontFamily: "'Sora', sans-serif",
         }}>

      {/* HEADER */}
      <div className="px-3 py-2.5 flex items-center justify-between border-b"
           style={{ borderColor: `${ACCENTS.cyan}33`, background: "rgba(2,6,11,0.7)" }}>
        <div className="flex items-center gap-2 min-w-0">
          <span className="grid place-items-center rounded-full shrink-0"
                style={{ width: 30, height: 30,
                         background: "linear-gradient(135deg, #00E5FF 0%, #D4B86A 100%)",
                         color: "#02060B", fontWeight: 900, fontSize: 12, letterSpacing: 1 }}>
            TC
          </span>
          <div className="min-w-0">
            <div className="font-display text-[13px] uppercase tracking-[0.12em] text-white truncate">Tactical Commander</div>
            <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-slate-500 truncate">
              // STRATEX AI · PM · ONLINE
            </div>
          </div>
        </div>
        <button
          data-testid="tc-close"
          onClick={() => setOpen(false)}
          className="grid place-items-center rounded-full transition hover:brightness-125"
          style={{ width: 28, height: 28, background: "#FF2D2D", color: "#fff",
                   boxShadow: "0 0 10px rgba(255,45,45,0.65)" }}>
          <X size={12} strokeWidth={3}/>
        </button>
      </div>

      {/* BRIEFING + MESSAGES */}
      <div ref={scrollRef}
           className="flex-1 overflow-y-auto px-3 py-3 space-y-2"
           style={{ minHeight: 200 }}>
        {briefing && messages.length === 0 && (
          <div className="rounded-md p-3"
               style={{ background: `${ACCENTS.cyan}10`, border: `1px solid ${ACCENTS.cyan}33` }}>
            <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase text-cyan-300 mb-1">
              // BRIEFING · THIS PAGE
            </div>
            <div className="text-[12px] leading-relaxed text-slate-200">{briefing}</div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i}
               data-testid={`tc-msg-${m.role}-${i}`}
               className={`rounded-md p-2.5 max-w-[92%] ${m.role === "user" ? "ml-auto" : ""}`}
               style={{
                 background: m.role === "user" ? `${ACCENTS.cyan}18` :
                             m.err ? `${ACCENTS.magenta}10` : "rgba(255,255,255,0.04)",
                 border: `1px solid ${m.role === "user" ? `${ACCENTS.cyan}44` :
                                       m.err ? `${ACCENTS.magenta}66` : "rgba(255,255,255,0.10)"}`,
               }}>
            <div className="font-mono text-[8px] tracking-[0.26em] uppercase mb-1"
                 style={{ color: m.role === "user" ? ACCENTS.cyan : ACCENTS.gold }}>
              {m.role === "user" ? "COMMANDER" : "TC"}
            </div>
            <div className="text-[12.5px] leading-relaxed text-slate-100 whitespace-pre-wrap">
              {m.content || (streaming && m.role === "assistant" && i === messages.length - 1
                ? <span className="inline-flex items-center gap-1.5"><Loader2 size={11} className="animate-spin text-cyan-400"/> thinking…</span>
                : "")}
            </div>
          </div>
        ))}
      </div>

      {/* SUGGESTED QUICK-QS */}
      {messages.length === 0 && (
        <div className="px-3 pb-2 flex flex-wrap gap-1.5">
          {suggested.map((q) => (
            <button
              key={q}
              data-testid="tc-suggested"
              onClick={() => send(q)}
              className="font-mono text-[9px] tracking-[0.12em] px-2.5 py-1 rounded-full transition hover:brightness-125"
              style={{ background: `${ACCENTS.cyan}10`, border: `1px solid ${ACCENTS.cyan}44`, color: ACCENTS.cyan }}>
              {q}
            </button>
          ))}
        </div>
      )}

      {/* INPUT */}
      <div className="px-3 pb-3 pt-1 border-t flex items-center gap-2"
           style={{ borderColor: `${ACCENTS.cyan}22`, background: "rgba(2,6,11,0.6)" }}>
        <input
          data-testid="tc-input"
          type="text"
          value={input}
          disabled={streaming}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask TC anything…"
          className="flex-1 bg-transparent outline-none font-mono text-[12px] text-white px-3 py-2 rounded-md disabled:opacity-60"
          style={{ background: "rgba(0,229,255,0.05)", border: `1px solid ${ACCENTS.cyan}44` }}
        />
        <button
          data-testid="tc-send"
          onClick={() => send()}
          disabled={streaming || !input.trim()}
          className="grid place-items-center rounded-md transition hover:brightness-125 disabled:opacity-50 disabled:cursor-not-allowed"
          style={{ width: 36, height: 36, background: ACCENTS.cyan, color: "#02060B",
                   boxShadow: `0 0 12px ${ACCENTS.cyan}66` }}>
          {streaming ? <Loader2 size={14} className="animate-spin"/> : <Send size={14}/>}
        </button>
      </div>
    </div>
  );
}
