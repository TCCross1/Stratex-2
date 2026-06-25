// STRATEX™ — REPORTS BINDER
//
// File-folder style viewer for the 17-page forensic deliverable.
// • Top: contractor band + report title
// • Left rail (lg+): grouped folder list (Overview · Geometry · Forensics ·
//   Materials · Labor · Financials · Action · Final) with chevron-style
//   page tiles.  Click a tile → fetches /scan-report/page/<slug>.png and
//   shows it full-bleed in the right canvas.
// • Right canvas: large page preview · download-this-page · open in PDF.
// • Final page (`certification`) gets a gilded gold border + "MASTER FINAL
//   REPORT" eyebrow to differentiate the comprehensive summary.

import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useContractor } from "@/lib/contractor";
import { StratexLogo } from "@/components/StratexBrand";
import {
  Layers, FileText, Camera, Box, Grid3x3, DoorOpen, Flame, Droplets, Zap,
  Boxes, Layers3, HardHat, CalendarRange, TrendingUp, AlertOctagon, Wrench,
  ShieldCheck, Download, FileDown, ExternalLink, ChevronLeft, ChevronRight,
  ArrowLeft, FolderOpen, Loader2,
} from "lucide-react";

const ICONS = {
  Layers, FileText, Camera, Box, Grid3x3, DoorOpen, Flame, Droplets, Zap,
  Boxes, Layers3, HardHat, CalendarRange, TrendingUp, AlertOctagon, Wrench, ShieldCheck,
};

const ACCENTS = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  magenta: "#FF2D78",
  green:   "#00FF9C",
  volt:    "#A6FF00",
  gold:    "#D4B86A",
};

// ─────────────────────────────────────────────────────────────────────────
// Folder tile in the left rail.
// ─────────────────────────────────────────────────────────────────────────
function PageTile({ page, active, onSelect }) {
  const accent = ACCENTS[page.accent] || ACCENTS.cyan;
  const Icon = ICONS[page.icon] || FileText;
  const isFinal = page.is_final;
  return (
    <button
      data-testid={`binder-tile-${page.slug}`}
      onClick={() => onSelect(page)}
      className="group w-full text-left transition-all rounded-md px-3 py-2.5 flex items-center gap-3 relative overflow-hidden"
      style={{
        background: active ? `linear-gradient(90deg, ${accent}22 0%, transparent 80%)` : "transparent",
        borderLeft: `3px solid ${active ? accent : "transparent"}`,
        boxShadow: active ? `inset 0 0 20px ${accent}12` : "none",
      }}
    >
      <span
        className="shrink-0 grid place-items-center rounded-sm"
        style={{
          width: 32, height: 32,
          background: `${accent}14`,
          border: `1px solid ${accent}55`,
          color: accent,
          filter: `drop-shadow(0 0 6px ${accent}66)`,
        }}
      >
        <Icon size={15} strokeWidth={1.7}/>
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-500">
            P{String(page.page).padStart(2,"0")}
          </span>
          {isFinal && (
            <span className="font-mono text-[7.5px] tracking-[0.22em] uppercase px-1.5 py-0.5 rounded-full"
                  style={{ color: ACCENTS.gold, border: `1px solid ${ACCENTS.gold}88`,
                           background: `${ACCENTS.gold}10` }}>
              MASTER
            </span>
          )}
        </div>
        <div className="font-display text-[11.5px] uppercase tracking-[0.08em] text-slate-100 leading-tight truncate mt-0.5">
          {page.title}
        </div>
        <div className="font-mono text-[8.5px] tracking-[0.18em] text-slate-500 truncate mt-0.5">
          {page.eyebrow}
        </div>
      </div>
      <ChevronRight size={12}
                    className="opacity-0 group-hover:opacity-100 transition shrink-0"
                    style={{ color: accent }}/>
    </button>
  );
}

// ─────────────────────────────────────────────────────────────────────────
// Main
// ─────────────────────────────────────────────────────────────────────────
export default function ReportsBinder() {
  const nav = useNavigate();
  const contractor = useContractor();
  const API = process.env.REACT_APP_BACKEND_URL;

  const [pages, setPages] = useState([]);
  const [active, setActive] = useState(null);
  const [imgLoading, setImgLoading] = useState(true);
  const [audience, setAudience] = useState("adjuster");

  // 1. Load page manifest
  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API}/api/demo/scan-report/pages`);
        const j = await r.json();
        setPages(j.pages || []);
        setActive((j.pages || [])[0] || null);
      } catch {
        setPages([]);
      }
    })();
  }, [API]);

  // 2. Group pages by section for the rail.
  const grouped = useMemo(() => {
    const g = {};
    for (const p of pages) (g[p.section] ||= []).push(p);
    return g;
  }, [pages]);

  const sectionOrder = ["Overview","Geometry","Forensics","Materials","Labor","Financials","Action","Final"];

  const onPick = (p) => { setActive(p); setImgLoading(true); };
  const goPrev = () => {
    const i = pages.findIndex(p => p.slug === active?.slug);
    if (i > 0) onPick(pages[i-1]);
  };
  const goNext = () => {
    const i = pages.findIndex(p => p.slug === active?.slug);
    if (i >= 0 && i < pages.length - 1) onPick(pages[i+1]);
  };

  const accent = active ? (ACCENTS[active.accent] || ACCENTS.cyan) : ACCENTS.cyan;
  const isFinal = active?.is_final;
  const ActiveIcon = active ? (ICONS[active.icon] || FileText) : FileText;

  const pageImg = active ? `${API}/api/demo/scan-report/page/${active.slug}.png?audience=${audience}` : "";
  const pagePdf = active ? `${API}/api/demo/scan-report/page/${active.slug}.pdf?audience=${audience}` : "";
  const fullPdf = `${API}/api/demo/scan-report.pdf?audience=${audience}`;

  return (
    <div
      data-testid="reports-binder"
      className="min-h-screen text-slate-100"
      style={{
        background:
          "radial-gradient(ellipse at 75% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
          "radial-gradient(ellipse at 10% 100%, rgba(212,184,106,0.07) 0%, transparent 55%)," +
          "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
        fontFamily: "'Sora', sans-serif",
      }}
    >
      {/* faint grid */}
      <div aria-hidden className="pointer-events-none fixed inset-0 opacity-[0.04]"
           style={{
             backgroundImage:
               "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px)," +
               "linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
             backgroundSize: "56px 56px",
           }}/>

      {/* ────────────── HEADER BAND ────────────── */}
      <header className="relative max-w-[1500px] mx-auto px-4 sm:px-6 pt-6 pb-4">
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4">
            <button
              data-testid="binder-back"
              onClick={() => nav("/deck")}
              className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
              style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF66", color: "#00E5FF" }}
            >
              <ArrowLeft size={12}/> Command Deck
            </button>
            <StratexLogo height={28}/>
          </div>
          <div className="flex items-center gap-3">
            <img src={contractor.logo_url} alt={contractor.business_name}
                 className="rounded-sm"
                 style={{ height: 44, width: "auto", maxWidth: 200,
                          border: "1px solid rgba(215,40,47,0.5)",
                          background: "rgba(255,255,255,0.04)", padding: 4 }}/>
            <div className="text-right hidden md:block">
              <div className="font-display text-[13px] uppercase tracking-[0.1em] text-white">{contractor.business_name}</div>
              <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                {contractor.address} · {contractor.city_state}
              </div>
            </div>
          </div>
        </div>

        <div className="mt-6">
          <div className="font-mono text-[10px] tracking-[0.32em] uppercase text-cyan-400">// REPORTS BINDER · FORENSIC DELIVERABLE</div>
          <h1 className="font-display uppercase tracking-[0.04em] text-3xl sm:text-5xl text-white leading-[1.05] mt-2">
            Open Each Section <span style={{ color: ACCENTS.cyan, textShadow: `0 0 18px ${ACCENTS.cyan}66` }}>Like a File.</span>
          </h1>
          <p className="font-mono text-[11px] tracking-[0.14em] uppercase text-slate-400 mt-2 max-w-2xl">
            Click any folder tile to open that page individually. The last page is the master pricing &amp; 3-D CAD certification.
          </p>
        </div>

        {/* audience toggle + full download */}
        <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex p-1 rounded-full"
               style={{ background: "rgba(8,14,24,0.85)", border: "1px solid rgba(0,229,255,0.25)" }}>
            {[
              { k: "adjuster",  l: "Adjuster · 17pp" },
              { k: "homeowner", l: "Homeowner · 6pp" },
            ].map((a) => (
              <button
                key={a.k}
                data-testid={`binder-audience-${a.k}`}
                onClick={() => setAudience(a.k)}
                className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-1.5 rounded-full transition"
                style={{
                  background: audience === a.k ? "#00E5FF" : "transparent",
                  color: audience === a.k ? "#02060B" : "#00E5FF",
                  fontWeight: audience === a.k ? 700 : 400,
                }}
              >
                {a.l}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2">
            <a
              data-testid="binder-download-passport"
              href={`${API}/api/demo/property-passport.pdf`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md flex items-center gap-2 transition hover:brightness-125"
              style={{
                background: "linear-gradient(120deg, rgba(212,184,106,0.16) 0%, rgba(8,14,24,0.85) 100%)",
                border: "1.5px solid #D4B86A",
                color: "#F5E0A3",
                boxShadow: "0 0 14px rgba(212,184,106,0.30)",
              }}
            >
              <ShieldCheck size={12}/> Issue Property Passport
            </a>
            <a
              data-testid="binder-download-full"
              href={fullPdf}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md flex items-center gap-2 transition hover:brightness-125"
              style={{ background: "rgba(0,229,255,0.10)", border: "1px solid #00E5FF88", color: "#00E5FF" }}
            >
              <FileDown size={12}/> Download Full Report
            </a>
          </div>
        </div>
      </header>

      {/* ────────────── BODY ────────────── */}
      <div className="max-w-[1500px] mx-auto px-4 sm:px-6 pb-12 grid grid-cols-1 lg:grid-cols-[320px_1fr] gap-4">

        {/* ── LEFT RAIL — folder list ── */}
        <aside
          data-testid="binder-rail"
          className="rounded-xl p-3 self-start lg:sticky lg:top-4 max-h-none lg:max-h-[calc(100vh-32px)] lg:overflow-y-auto deck-rail-scroll"
          style={{ background: "rgba(8,14,24,0.86)", border: "1px solid rgba(0,229,255,0.30)",
                   boxShadow: "0 0 36px rgba(0,229,255,0.10) inset" }}
        >
          <div className="px-2 py-1 flex items-center gap-2 mb-2">
            <FolderOpen size={14} className="text-cyan-400"/>
            <span className="font-mono text-[10px] tracking-[0.28em] uppercase text-cyan-400">// PAGE INDEX</span>
            <span className="ml-auto font-mono text-[9px] text-slate-500">{pages.length}</span>
          </div>

          {sectionOrder.map((sec) => {
            const list = grouped[sec] || [];
            if (!list.length) return null;
            const sectionAccent = ACCENTS[list[0].accent] || ACCENTS.cyan;
            return (
              <div key={sec} className="mb-3" data-testid={`binder-section-${sec.toLowerCase()}`}>
                <div className="px-2 mb-1.5 flex items-center gap-2">
                  <span className="w-1 h-1 rounded-full"
                        style={{ background: sectionAccent, boxShadow: `0 0 6px ${sectionAccent}` }}/>
                  <span className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-400">
                    {sec}
                  </span>
                </div>
                <div className="space-y-0.5">
                  {list.map((p) => (
                    <PageTile
                      key={p.slug}
                      page={p}
                      active={active?.slug === p.slug}
                      onSelect={onPick}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </aside>

        {/* ── RIGHT — page viewer ── */}
        <main className="min-w-0">
          {!active ? (
            <div className="rounded-xl p-12 text-center"
                 style={{ background: "rgba(8,14,24,0.86)", border: "1px dashed rgba(0,229,255,0.35)" }}>
              <Loader2 size={28} className="mx-auto animate-spin text-cyan-400"/>
              <div className="mt-4 font-mono text-[10px] tracking-[0.22em] uppercase text-slate-400">
                Loading binder…
              </div>
            </div>
          ) : (
            <div
              data-testid="binder-viewer"
              className="rounded-xl overflow-hidden"
              style={{
                background: "linear-gradient(180deg, rgba(8,14,24,0.92) 0%, rgba(4,8,14,0.95) 100%)",
                border: `1.5px solid ${isFinal ? ACCENTS.gold : accent}aa`,
                boxShadow:
                  `0 0 0 1px ${(isFinal ? ACCENTS.gold : accent)}22, ` +
                  `inset 0 0 36px ${(isFinal ? ACCENTS.gold : accent)}10, ` +
                  `0 12px 40px rgba(0,0,0,0.5)`,
              }}
            >
              {/* viewer header */}
              <div className="px-4 sm:px-6 py-4 flex items-center justify-between gap-3 border-b"
                   style={{ borderColor: `${isFinal ? ACCENTS.gold : accent}33` }}>
                <div className="flex items-center gap-3 min-w-0">
                  <span className="grid place-items-center rounded-sm shrink-0"
                        style={{ width: 36, height: 36,
                                 background: `${(isFinal ? ACCENTS.gold : accent)}14`,
                                 border: `1px solid ${(isFinal ? ACCENTS.gold : accent)}88`,
                                 color: isFinal ? ACCENTS.gold : accent }}>
                    <ActiveIcon size={18} strokeWidth={1.7}/>
                  </span>
                  <div className="min-w-0">
                    <div className="font-mono text-[9px] tracking-[0.26em] uppercase"
                         style={{ color: isFinal ? ACCENTS.gold : accent }}>
                      {isFinal ? "MASTER · FINAL · " : ""}P{String(active.page).padStart(2,"0")} · {active.eyebrow}
                    </div>
                    <div className="font-display text-base sm:text-lg uppercase tracking-[0.1em] text-white truncate">
                      {active.title}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <button
                    data-testid="binder-prev"
                    onClick={goPrev}
                    className="grid place-items-center rounded-md transition hover:brightness-150"
                    style={{ width: 32, height: 32, background: "rgba(0,229,255,0.10)",
                             border: "1px solid #00E5FF66", color: "#00E5FF" }}
                  >
                    <ChevronLeft size={14}/>
                  </button>
                  <button
                    data-testid="binder-next"
                    onClick={goNext}
                    className="grid place-items-center rounded-md transition hover:brightness-150"
                    style={{ width: 32, height: 32, background: "rgba(0,229,255,0.10)",
                             border: "1px solid #00E5FF66", color: "#00E5FF" }}
                  >
                    <ChevronRight size={14}/>
                  </button>
                </div>
              </div>

              {/* canvas */}
              <div className="relative bg-[#02060B]">
                {imgLoading && (
                  <div className="absolute inset-0 grid place-items-center" style={{ minHeight: 480 }}>
                    <div className="text-center">
                      <Loader2 size={24} className="mx-auto animate-spin" style={{ color: accent }}/>
                      <div className="mt-3 font-mono text-[10px] tracking-[0.22em] uppercase text-slate-500">
                        Rendering page · this may take a moment
                      </div>
                    </div>
                  </div>
                )}
                <img
                  key={pageImg /* force reload when slug changes */}
                  src={pageImg}
                  alt={active.title}
                  data-testid="binder-page-img"
                  onLoad={() => setImgLoading(false)}
                  onError={() => setImgLoading(false)}
                  className="w-full block"
                  style={{ minHeight: imgLoading ? 480 : "auto" }}
                />
              </div>

              {/* viewer footer */}
              <div className="px-4 sm:px-6 py-3 border-t flex flex-wrap items-center justify-between gap-3"
                   style={{ borderColor: `${isFinal ? ACCENTS.gold : accent}33` }}>
                <div className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
                  Section · {active.section} &nbsp;·&nbsp; Audience · {audience.toUpperCase()}
                </div>
                <div className="flex items-center gap-2">
                  <a
                    data-testid="binder-page-pdf"
                    href={pagePdf}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5 transition hover:brightness-125"
                    style={{ background: `${accent}14`, border: `1px solid ${accent}66`, color: accent }}
                  >
                    <Download size={11}/> This page · PDF
                  </a>
                  <a
                    data-testid="binder-page-png"
                    href={pageImg}
                    download={`STRATEX_${active.slug}.png`}
                    className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5 transition hover:brightness-125"
                    style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.18)", color: "#fff" }}
                  >
                    <Download size={11}/> This page · PNG
                  </a>
                  <a
                    data-testid="binder-full-pdf"
                    href={fullPdf}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[9.5px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5 transition hover:brightness-125"
                    style={{ background: "rgba(212,184,106,0.10)", border: "1px solid #D4B86A88", color: "#D4B86A" }}
                  >
                    <ExternalLink size={11}/> Full Report
                  </a>
                </div>
              </div>
            </div>
          )}

          {/* MASTER FINAL PROMO TILE */}
          {active && !isFinal && pages.length > 0 && (
            <button
              data-testid="binder-jump-final"
              onClick={() => onPick(pages[pages.length - 1])}
              className="mt-4 w-full text-left rounded-xl p-4 flex items-center gap-4 transition hover:scale-[1.005] hover:brightness-110"
              style={{
                background: "linear-gradient(120deg, rgba(212,184,106,0.10) 0%, rgba(8,14,24,0.85) 60%)",
                border: `1.5px solid ${ACCENTS.gold}88`,
                boxShadow: `0 0 24px ${ACCENTS.gold}25, inset 0 0 28px ${ACCENTS.gold}10`,
              }}
            >
              <span className="grid place-items-center rounded-md shrink-0"
                    style={{ width: 44, height: 44, background: `${ACCENTS.gold}18`,
                             border: `1px solid ${ACCENTS.gold}88`, color: ACCENTS.gold }}>
                <ShieldCheck size={22} strokeWidth={1.6}/>
              </span>
              <div className="flex-1 min-w-0">
                <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: ACCENTS.gold }}>
                  // MASTER · FINAL · COMPREHENSIVE
                </div>
                <div className="font-display text-base uppercase tracking-[0.1em] text-white mt-0.5">
                  Open the Final Pricing & 3-D CAD Certification
                </div>
                <div className="font-mono text-[10px] tracking-[0.18em] uppercase text-slate-400 mt-0.5">
                  Comprehensive report · grand-total range · stamped sign-off
                </div>
              </div>
              <ChevronRight size={18} style={{ color: ACCENTS.gold }}/>
            </button>
          )}
        </main>
      </div>

      <style>{`
        .deck-rail-scroll::-webkit-scrollbar { width: 6px; }
        .deck-rail-scroll::-webkit-scrollbar-track { background: transparent; }
        .deck-rail-scroll::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.28); border-radius: 4px; }
      `}</style>
    </div>
  );
}
