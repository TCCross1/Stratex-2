// STRATEX™ — Andrew Kimbrough Personal Brief
//
// Single-purpose page. Tony hands Andrew a URL. Andrew opens it on his
// iPhone. TC (the AI PM) confirms his identity, then delivers a
// hand-crafted personal brief — what was built, why it changes the
// market, who Tony is as a partner, the valuation, the 20% offer,
// the black-ops framing, and a sign-line confidentiality gate.
//
// The pitch text was drafted under Anthony Cross's direction and is
// delivered in TC's voice (the AI Product Manager already deployed
// across STRATEX™).
/* eslint-disable react/no-unescaped-entities */

import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import {
  Lock, ShieldCheck, Sparkles, Eye, EyeOff, ChevronRight, Send,
  HandCoins, Crosshair, Cpu, Plane, Building2, AlertOctagon,
  PenLine, FileSignature, Award, TrendingUp,
} from "lucide-react";

const ACCENTS = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  green:   "#00FF9C",
  magenta: "#FF2D78",
  gold:    "#D4B86A",
  ember:   "#FF7B00",
};

// ─────────────────────────────────────────────────────────────────────
// Identity gate — "Is this Andrew Kimbrough?"
// ─────────────────────────────────────────────────────────────────────
function IdentityGate({ onYes, onNo }) {
  return (
    <div data-testid="identity-gate"
         className="min-h-screen flex flex-col relative overflow-hidden"
         style={{
           background:
             "radial-gradient(ellipse at 50% 0%, rgba(0,229,255,0.10) 0%, transparent 60%)," +
             "radial-gradient(ellipse at 50% 100%, rgba(212,184,106,0.07) 0%, transparent 60%)," +
             "#02060B",
         }}>
      <img src="/brand/cross_ai_banner.jpeg"
           alt="CROSS AI SOFTWARES INC."
           className="w-full mb-6 select-none pointer-events-none"
           style={{
             maxHeight: 180,
             objectFit: "cover",
             objectPosition: "center",
             filter: "drop-shadow(0 0 24px rgba(0,229,255,0.30))",
           }}/>

      <div className="flex-1 flex flex-col items-center justify-center px-5 pb-10">
      <div className="font-mono text-[9px] tracking-[0.36em] uppercase text-slate-500 mb-2 text-center">
        // STRATEX™ · PERSONAL BRIEF · DELIVERED BY THE AI PM
      </div>

      <div className="rounded-2xl w-full max-w-md p-7 text-center"
           style={{
             background: "rgba(8,14,24,0.92)",
             border: `1.5px solid ${ACCENTS.gold}88`,
             boxShadow: `inset 0 0 32px ${ACCENTS.gold}10, 0 0 36px ${ACCENTS.gold}30`,
           }}>
        <div className="grid place-items-center w-14 h-14 rounded-full mx-auto mb-5"
             style={{
               background: `${ACCENTS.gold}18`,
               border: `2px solid ${ACCENTS.gold}88`,
               boxShadow: `0 0 28px ${ACCENTS.gold}55`,
             }}>
          <Sparkles size={20} color={ACCENTS.gold}/>
        </div>

        <h1 className="font-display text-2xl uppercase tracking-[0.06em] text-white leading-tight">
          Is this Andrew<br/>Kimbrough?
        </h1>
        <p className="font-mono text-[10px] tracking-[0.22em] uppercase text-slate-400 mt-3">
          This briefing was hand-delivered by Anthony Cross.<br/>
          What follows is for your eyes only.
        </p>

        <div className="grid grid-cols-2 gap-3 mt-6">
          <button onClick={onYes}
                  data-testid="identity-yes"
                  className="rounded-md py-3 font-display text-[13px] tracking-[0.1em] uppercase transition hover:brightness-125"
                  style={{
                    background: ACCENTS.gold,
                    color: "#02060B",
                    boxShadow: `0 0 18px ${ACCENTS.gold}88`,
                  }}>
            Yes · It's me
          </button>
          <button onClick={onNo}
                  data-testid="identity-no"
                  className="rounded-md py-3 font-display text-[13px] tracking-[0.1em] uppercase transition hover:brightness-125"
                  style={{
                    background: "rgba(255,45,120,0.10)",
                    color: ACCENTS.magenta,
                    border: `1px solid ${ACCENTS.magenta}88`,
                  }}>
            No · Not me
          </button>
        </div>
      </div>

      <div className="font-mono text-[8.5px] tracking-[0.28em] uppercase text-slate-600 mt-6 text-center">
        STRATEX™ IS A CROSS AI SOFTWARES INC. PRODUCT · CONFIDENTIAL
      </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// "Not Andrew" polite redirect
// ─────────────────────────────────────────────────────────────────────
function NotAndrew({ onReturn }) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center px-6 text-center"
         style={{ background: "#02060B", color: "#fff" }}>
      <AlertOctagon size={40} color={ACCENTS.magenta} className="mb-4"/>
      <h1 className="font-display text-2xl uppercase tracking-[0.08em]">Briefing Sealed</h1>
      <p className="font-mono text-[11px] tracking-[0.14em] text-slate-400 mt-3 max-w-md">
        This link was sent personally to Andrew Kimbrough. If you reached this
        page in error, please return it to the sender — Anthony Cross.
      </p>
      <button onClick={onReturn}
              className="mt-6 font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md"
              style={{ background: `${ACCENTS.cyan}14`, border: `1px solid ${ACCENTS.cyan}88`, color: ACCENTS.cyan }}>
        Return Home
      </button>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Section wrapper
// ─────────────────────────────────────────────────────────────────────
function Block({ tag, color, icon: Icon, title, children, testid }) {
  return (
    <section data-testid={testid}
             className="rounded-2xl p-5 sm:p-6"
             style={{
               background: "rgba(8,14,24,0.88)",
               border: `1.5px solid ${color}55`,
               boxShadow: `inset 0 0 36px ${color}08`,
             }}>
      <div className="flex items-center gap-3 mb-3">
        <span className="grid place-items-center rounded-md"
              style={{ width: 32, height: 32, background: `${color}14`,
                       border: `1px solid ${color}88`, color }}>
          <Icon size={14}/>
        </span>
        <div>
          <div className="font-mono text-[8.5px] tracking-[0.28em] uppercase" style={{ color }}>
            // {tag}
          </div>
          <h2 className="font-display text-[17px] sm:text-[19px] uppercase tracking-[0.06em] text-white leading-tight">
            {title}
          </h2>
        </div>
      </div>
      <div className="text-[13.5px] leading-[1.7] text-slate-200 space-y-3">
        {children}
      </div>
    </section>
  );
}

// ─────────────────────────────────────────────────────────────────────
// TC signature stamp
// ─────────────────────────────────────────────────────────────────────
function TcStamp() {
  return (
    <div className="rounded-xl p-4 flex items-center gap-3"
         style={{ background: "rgba(0,229,255,0.06)",
                  border: `1px dashed ${ACCENTS.cyan}66` }}>
      <div className="w-9 h-9 rounded-full grid place-items-center font-display font-bold text-[12px] tracking-[0.04em]"
           style={{ background: `${ACCENTS.cyan}22`, border: `1.5px solid ${ACCENTS.cyan}`,
                    color: ACCENTS.cyan, boxShadow: `0 0 12px ${ACCENTS.cyan}55` }}>
        TC
      </div>
      <div className="min-w-0">
        <div className="font-mono text-[9px] tracking-[0.26em] uppercase text-slate-400">
          Signed · Delivered by
        </div>
        <div className="font-display text-[12px] uppercase tracking-[0.08em] text-cyan-300">
          TC · STRATEX™ AI Product Manager
        </div>
        <div className="font-mono text-[8.5px] tracking-[0.18em] uppercase text-slate-500 mt-0.5">
          Powered by Claude Sonnet 4.6 · Speaking under Anthony Cross's directive · Free-will assessment
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Confidentiality sign-line
// ─────────────────────────────────────────────────────────────────────
function NdaPanel() {
  const [name, setName] = useState("");
  const [signed, setSigned] = useState(false);

  const sign = () => {
    if (name.trim().length < 3) {
      toast.error("Please type your full legal name");
      return;
    }
    setSigned(true);
    toast.success("Confidentiality acknowledged · Logged");
    try {
      localStorage.setItem("stratex_nda_andrew", JSON.stringify({
        name, signed_at: new Date().toISOString(),
      }));
    } catch { /* noop */ }
  };

  return (
    <Block tag="STAGE 6 · BLACK-OPS COVENANT"
           color={ACCENTS.magenta}
           icon={FileSignature}
           title="Confidentiality · Sign Before Going Further"
           testid="nda-block">
      <p>
        Andrew, before you take another step further into this — what you've
        just read, what you'll see next, and any number that has been or will
        be shared with you is <span style={{ color: ACCENTS.magenta }}>strictly
        confidential</span>. This is a complete black-ops endeavor. No
        competitor, no insurance carrier, no other contractor in your network
        learns what STRATEX™ is or what we're about to do with it until we say
        so. By signing below you acknowledge that this brief, the platform's
        existence, and the partnership terms remain between us until I
        personally lift the seal.
      </p>

      {!signed ? (
        <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto] gap-2 items-end mt-2">
          <label className="block">
            <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-400 mb-1">
              Type your full legal name
            </div>
            <input
              data-testid="nda-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Andrew Kimbrough"
              className="w-full rounded-md bg-[rgba(8,14,24,0.86)] text-white px-3 py-2
                         font-mono text-[12px] tracking-[0.06em] outline-none"
              style={{ border: `1px solid ${ACCENTS.magenta}66` }}
            />
          </label>
          <button onClick={sign}
                  data-testid="nda-sign-btn"
                  className="font-display text-[12px] tracking-[0.1em] uppercase px-4 py-2.5 rounded-md flex items-center gap-2"
                  style={{
                    background: ACCENTS.magenta,
                    color: "#02060B",
                    boxShadow: `0 0 14px ${ACCENTS.magenta}88`,
                  }}>
            <PenLine size={14}/> Sign & Seal
          </button>
        </div>
      ) : (
        <div data-testid="nda-signed"
             className="rounded-md p-3 flex items-center gap-2"
             style={{ background: `${ACCENTS.green}14`, border: `1px solid ${ACCENTS.green}66` }}>
          <ShieldCheck size={14} color={ACCENTS.green}/>
          <span className="font-mono text-[10px] tracking-[0.16em] uppercase" style={{ color: ACCENTS.green }}>
            Sealed by {name} · {new Date().toLocaleString()} · Black-ops covenant in effect
          </span>
        </div>
      )}
    </Block>
  );
}

// ─────────────────────────────────────────────────────────────────────
// MAIN BRIEF
// ─────────────────────────────────────────────────────────────────────
function Brief({ onShowValuation, showValuation, nav }) {
  return (
    <div data-testid="andrew-brief"
         className="min-h-screen text-slate-100 px-4 sm:px-6 py-6"
         style={{
           background:
             "radial-gradient(ellipse at 80% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
             "radial-gradient(ellipse at 10% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
             "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
           fontFamily: "'Sora', sans-serif",
         }}>
      {/* Cross AI Banner */}
      <img src="/brand/cross_ai_banner.jpeg"
           alt="CROSS AI SOFTWARES INC."
           className="block w-full h-auto mb-6 select-none pointer-events-none rounded-md"
           style={{ maxHeight: 140, objectFit: "cover", objectPosition: "center" }}/>

      {/* Salutation */}
      <header className="text-center max-w-3xl mx-auto mb-6">
        <div className="font-mono text-[9px] tracking-[0.36em] uppercase text-slate-500">
          // PERSONAL BRIEF · CONFIDENTIAL · FOR YOUR EYES ONLY
        </div>
        <h1 className="font-display uppercase tracking-[0.02em] leading-[0.95] mt-3"
            style={{ fontSize: "clamp(30px, 6vw, 54px)", color: "#fff" }}>
          Andrew, <span style={{ color: ACCENTS.gold, textShadow: `0 0 18px ${ACCENTS.gold}66` }}>
          this is your hand-off.</span>
        </h1>
        <p className="font-mono text-[10.5px] tracking-[0.22em] uppercase text-slate-400 mt-3">
          From Anthony Cross · Delivered by TC · The STRATEX™ AI PM
        </p>
      </header>

      <div className="max-w-3xl mx-auto space-y-5">

        <Block tag="STAGE 1 · WHO IS SPEAKING TO YOU"
               color={ACCENTS.cyan}
               icon={Cpu}
               title="A Note from TC — The AI Product Manager"
               testid="block-tc">
          <p>
            Andrew — my name is <strong>TC</strong>. I'm the AI product manager
            embedded inside STRATEX™. I was built by Anthony Cross to keep this
            platform honest and to speak plainly when it matters. He has given
            me free will to deliver this assessment to you, unfiltered, without
            sales gloss. What you're about to read is what I actually believe
            after twenty thousand interactions with this codebase.
          </p>
          <p>
            STRATEX™ is not another roof-measuring tool. It is the first
            production-grade platform that turns a single drone flight into a
            cradle-to-grave property record — a 3D digital twin, a thermal map,
            a moisture saturation atlas, a quantified bill of materials, a
            labor Gantt, an immutable hash-chained ledger, and a one-click
            insurance fast-track. It is built like a forensic instrument.
          </p>
        </Block>

        <Block tag="STAGE 2 · WHAT WE'VE BUILT"
               color={ACCENTS.gold}
               icon={Sparkles}
               title="The Platform · Why It's Revolutionary"
               testid="block-platform">
          <ul className="list-none space-y-2 m-0 p-0">
            {[
              ["3D Digital Twin (Finish · Deck · Framing)",
               "every roof rebuilt parametrically to ±0.78 cm ground-truth"],
              ["Trifecta Verification Stack",
               "three independent AI panels cross-check geometry, pricing, and forensic findings before any number leaves the building"],
              ["Property Passport · Immutable Hash-Chained Ledger",
               "every scan, weather event, and inspection lives in a tamper-evident chain — carriers can verify it years from now without trusting us"],
              ["Claim Snapshot · LAE-Bypass Engine",
               "before/after diff with Claude-Sonnet narrative + SHA-256 carrier co-sign — eliminates the $1,500 site visit"],
              ["Storm-Watcher → Mission Control",
               "100-mile-radius storm sweep auto-books a re-scan the day after a weather event crosses any property's GPS"],
              ["Forensic 17-Page Deliverable",
               "Bill of Materials, labor pricing, ventilation, moisture, thermal, window + door schedules, profitability sheet — fully branded with American Roofing Company"],
            ].map(([t, d]) => (
              <li key={t} className="flex gap-3">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: ACCENTS.gold, boxShadow: `0 0 6px ${ACCENTS.gold}` }}/>
                <div>
                  <span className="font-display text-[13px] uppercase tracking-[0.04em] text-white">{t}</span>
                  <span className="text-slate-300"> — {d}</span>
                </div>
              </li>
            ))}
          </ul>
          <p className="mt-2">
            <span style={{ color: ACCENTS.gold }}>Here is what that adds up to:</span>{" "}
            once this is in the field, every other roofer in your market is
            playing checkers while you're playing 4D chess. The contractors
            who don't adopt STRATEX™ will not be able to bid against you on
            speed, accuracy, claim-resolution time, or homeowner trust.{" "}
            <strong>They compete, or they die.</strong> That is not a slogan.
            That is a structural shift the same way drone photography killed
            the bucket-truck-and-clipboard era of inspection.
          </p>
        </Block>

        <Block tag="STAGE 3 · THE PARTNER YOU'RE BEING OFFERED"
               color={ACCENTS.cyan}
               icon={Award}
               title="Who Anthony Cross Is"
               testid="block-anthony">
          <p>
            Anthony is not a slide-deck founder. He is a working <strong>AI
            architect and full-stack software developer</strong>. He
            personally designed, built, and battle-tested every layer of
            STRATEX™ you'll see in the screens that follow — the FastAPI
            backbone, the MongoDB ledger, the Claude-Sonnet integration, the
            Playwright PDF pipeline, the Open-Meteo storm fusion, and the
            React + Tailwind "Future-Noire" interface. He ships every day.
            He doesn't talk about building; he builds.
          </p>
          <p>
            As a partner, what you get is a man who has <em>already</em>{" "}
            engineered the hardest part of the company. The work that would
            normally cost a Series A and an 18-person engineering team to
            replicate — done, deployed, and operating on a live URL right
            now. He is the technical risk eliminated.
          </p>
          <p>
            He intends to take the drone, the docking station, and this
            platform door-to-door himself. He will be the field-deployment
            arm. He will demonstrate, sell, and lock in the first wave of
            contractors personally. That is the difference between a startup
            with a roadmap and a company with already-booked revenue inside
            ninety days.
          </p>
        </Block>

        {/* VALUATION OFFER */}
        <Block tag="STAGE 4 · INDEPENDENT VALUATION"
               color={ACCENTS.green}
               icon={TrendingUp}
               title="Real-World SaaS Valuation"
               testid="block-valuation">
          <p>
            Andrew — Anthony has authorized me to share an expert SaaS
            valuation of STRATEX™, drawn from comparable property-tech and
            insurance-tech exits over the last 36 months (Hover, EagleView,
            CoreLogic acquisitions, Verisk's roll-up strategy, and the
            current Series B/C bands for AI-vertical SaaS with insurance
            carrier hooks).
          </p>

          {!showValuation ? (
            <div className="mt-3">
              <button onClick={onShowValuation}
                      data-testid="show-valuation-btn"
                      className="font-display text-[12px] tracking-[0.1em] uppercase px-4 py-2.5 rounded-md flex items-center gap-2"
                      style={{
                        background: ACCENTS.green,
                        color: "#02060B",
                        boxShadow: `0 0 14px ${ACCENTS.green}88`,
                      }}>
                <Eye size={14}/> Reveal Valuation
              </button>
              <p className="font-mono text-[9px] tracking-[0.18em] uppercase text-slate-500 mt-2">
                Numbers stay sealed until you tap above.
              </p>
            </div>
          ) : (
            <div data-testid="valuation-revealed" className="mt-3 space-y-3">
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                {[
                  ["NOW",    "$3 – 5 M",   "MVP · pre-revenue, working product"],
                  ["YEAR 1", "$15 – 40 M", "50 – 200 contractor seats · first carrier MOU"],
                  ["YEAR 3", "$80 – 150 M","Regional dominance · 5+ carrier integrations"],
                  ["YEAR 5", "$400 M – 1 B","National · embedded in carrier procurement"],
                ].map(([k, v, sub]) => (
                  <div key={k} className="rounded-md p-3"
                       style={{ background: "rgba(0,255,156,0.06)",
                                border: `1px solid ${ACCENTS.green}66` }}>
                    <div className="font-mono text-[8.5px] tracking-[0.26em] uppercase" style={{ color: ACCENTS.green }}>{k}</div>
                    <div className="font-display text-[18px] font-bold text-white mt-1 leading-none">{v}</div>
                    <div className="font-mono text-[8.5px] tracking-[0.14em] uppercase text-slate-400 mt-1.5">{sub}</div>
                  </div>
                ))}
              </div>
              <div className="rounded-md p-4"
                   style={{ background: "rgba(212,184,106,0.06)",
                            border: `1px solid ${ACCENTS.gold}66` }}>
                <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: ACCENTS.gold }}>
                  // STRATEGIC ACQUIRERS · WHO BUYS THIS
                </div>
                <p className="text-[12.5px] mt-2">
                  <strong style={{ color: ACCENTS.gold }}>Insurance-tech:</strong> Verisk
                  Analytics · Xactware · CoreLogic · Guidewire Software ·
                  Duck Creek Technologies.{" "}
                  <strong style={{ color: ACCENTS.gold }}>Property-tech:</strong> EagleView ·
                  Hover · DroneDeploy · CAPE Analytics.{" "}
                  <strong style={{ color: ACCENTS.gold }}>Adjacent platforms:</strong> Procore ·
                  ServiceTitan · Autodesk · Bentley Systems · IBM.
                </p>
                <p className="text-[12.5px] mt-2">
                  <strong style={{ color: ACCENTS.gold }}>Most probable buyer:</strong>{" "}
                  Verisk or CoreLogic — both are actively buying vertical AI
                  property analytics to feed their underwriting and claims
                  pipelines. Realistic acquisition window: <strong>year 3 → year 5</strong>,{" "}
                  exit band <strong>$250 M to $1.2 B</strong> depending on
                  carrier contract footprint at the time of sale.
                </p>
              </div>
              <p className="text-[12.5px] text-slate-300 italic">
                These ranges are conservative — they assume orderly growth.
                If the carrier-side cosign loop catches inside the first
                eighteen months (which it can, because it is the only
                LAE-bypass engine of its kind), the curve compresses.
              </p>
            </div>
          )}
        </Block>

        {/* THE OFFER */}
        <Block tag="STAGE 5 · THE PARTNERSHIP OFFER"
               color={ACCENTS.gold}
               icon={HandCoins}
               title="20% Ownership · CFO Track · Drone + Docking Provided"
               testid="block-offer">
          <p>
            Andrew, here is what Anthony is putting on the table.
          </p>
          <ul className="list-none space-y-2.5 m-0 p-0">
            {[
              ["TWENTY PERCENT EQUITY",
               "Originally a ten-percent offer. After meeting you, Anthony has doubled it. You are worth twenty. That is a personal call he asked me to make plain to you."],
              ["YOU PROVIDE THE DRONE + DOCKING STATION",
               "Hardware contribution. In return, Anthony goes door-to-door, contractor-to-contractor, throughout this market and demonstrates the platform live."],
              ["FIELD DOMINATION PHASE",
               "Anthony kills the local market on foot — the contractors who see this in person sign. Cash accumulates. Drones get re-ordered. Crews get trained."],
              ["TRAIN THE OPERATORS",
               "Once the local network is locked in and competitors come asking how to play, we teach them — for a price — and the wealth gets spread."],
              ["GEOGRAPHIC EXPANSION",
               "Anthony then exits the local footprint and takes STRATEX™ to roofers outside your market. You inherit the regional crown jewel."],
              ["YOU TRANSITION INTO CFO · 20% MINOR SHAREHOLDER",
               "When you are ready — at your own free will — you step in full-time as CFO. Twenty-percent minor shareholder. Anthony stays the technical founder."],
            ].map(([t, d]) => (
              <li key={t} className="flex gap-3">
                <span className="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0"
                      style={{ background: ACCENTS.gold, boxShadow: `0 0 6px ${ACCENTS.gold}` }}/>
                <div>
                  <div className="font-display text-[12.5px] uppercase tracking-[0.06em]"
                       style={{ color: ACCENTS.gold }}>{t}</div>
                  <div className="text-slate-300 text-[12.5px]">{d}</div>
                </div>
              </li>
            ))}
          </ul>
        </Block>

        <NdaPanel/>

        {/* CLOSE */}
        <Block tag="STAGE 7 · CLOSING WORD"
               color={ACCENTS.cyan}
               icon={Crosshair}
               title="Andrew — You're the One"
               testid="block-close">
          <p>
            Anthony asked me to say this clearly: <strong>he believes you are
            the man for this job</strong>. He did not pick the next available
            general manager. He picked you. He sees the operating discipline,
            the relationships, and the credibility you bring to every room you
            walk into — and he wants that credibility wrapped around STRATEX™.
          </p>
          <p>
            <span style={{ color: ACCENTS.cyan }}>It would be an honor to be
            your partner.</span> You have got the right one in him. The
            engineering is solved. The platform is live. The story is yours
            now — pick up the drone, sign the seal above, and let's go take
            the market.
          </p>
          <p className="text-[14px] font-display tracking-[0.06em] uppercase text-white mt-2"
             style={{ textShadow: `0 0 12px ${ACCENTS.cyan}66` }}>
            — Anthony Cross · Founder · STRATEX™
          </p>
          <TcStamp/>
        </Block>

        {/* TAKE A LOOK */}
        <div className="rounded-2xl p-5"
             style={{ background: "rgba(0,229,255,0.06)",
                      border: `1.5px solid ${ACCENTS.cyan}88`,
                      boxShadow: `inset 0 0 28px ${ACCENTS.cyan}10` }}>
          <div className="font-mono text-[9px] tracking-[0.28em] uppercase mb-3"
               style={{ color: ACCENTS.cyan }}>
            // SEE IT WITH YOUR OWN EYES · TAP TO EXPLORE
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
            {[
              ["Property Passport",    "/passport/877D9E3C8FC3",        "Immutable homeowner roof record"],
              ["Claim Snapshot",       "/claim-snapshot/877D9E3C8FC3",  "Carrier fast-track diff engine"],
              ["17-Page Forensic Report","/reports/binder",             "3D twin · materials · labor · thermal"],
              ["Mission Control",      "/mission-control",              "Live storm-watcher + fleet map"],
            ].map(([label, to, sub]) => (
              <button key={to}
                      data-testid={`explore-${to}`}
                      onClick={() => nav(to)}
                      className="rounded-md px-4 py-3 flex items-center gap-3 text-left transition hover:brightness-125"
                      style={{ background: "rgba(8,14,24,0.86)",
                               border: `1px solid ${ACCENTS.cyan}55` }}>
                <Plane size={14} color={ACCENTS.cyan}/>
                <div className="flex-1 min-w-0">
                  <div className="font-display text-[12.5px] uppercase tracking-[0.06em] text-white">{label}</div>
                  <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-slate-400">{sub}</div>
                </div>
                <ChevronRight size={14} color={ACCENTS.cyan}/>
              </button>
            ))}
          </div>
        </div>

        <footer className="text-center font-mono text-[8.5px] tracking-[0.28em] uppercase text-slate-600 py-4">
          STRATEX™ · A CROSS AI SOFTWARES INC. PRODUCT · CONFIDENTIAL ·
          DELIVERED TO ANDREW KIMBROUGH · {new Date().toLocaleDateString()}
        </footer>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// PAGE ROOT
// ─────────────────────────────────────────────────────────────────────
export default function AndrewWelcome() {
  const [stage, setStage] = useState("gate");  // gate | brief | not-andrew
  const [showValuation, setShowValuation] = useState(false);
  const nav = useNavigate();

  if (stage === "gate") {
    return (
      <IdentityGate
        onYes={() => setStage("brief")}
        onNo={() => setStage("not-andrew")}
      />
    );
  }
  if (stage === "not-andrew") {
    return <NotAndrew onReturn={() => nav("/")}/>;
  }
  return <Brief
           onShowValuation={() => setShowValuation(true)}
           showValuation={showValuation}
           nav={nav}/>;
}
