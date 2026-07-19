// STRATEX™ — APP LAUNCHER (home shell)
//
// Replaces the long-scroll marketing landing with a desktop-OS-style
// launcher: persistent app rail on the left (vertical, scrollable),
// large display screen on the right that defaults to the official
// STRATEX™ logo and is replaced by the active app window when an icon
// is clicked.  Every window carries a red [X] cancel pill in its top
// corner that pops back to the logo splash.
//
// Mobile: the rail collapses to a thin scrollable column on the left
// (44px wide) so the launcher fits in a phone viewport without ever
// triggering a long vertical scroll.
//
// IMPORTANT: nothing from the previous landing is removed — every
// section (Recon Stack, Scientific Rigor, Fleet Command, Mesh Engine,
// Switchboard) lives inside one of the app windows below.

import React, { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { HudCard, DataReadout, SectionTitle } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ValidationReport from "@/components/ValidationReport";
import useIsMobile from "@/hooks/use-is-mobile";
import { api } from "@/lib/api";
import { useContractor } from "@/lib/contractor";
import {
  Crosshair, Cpu, Activity, Radar, Shield, Zap, Cloud, Satellite, Sun, Box,
  Info, X, Truck, LayoutDashboard, FileText, ShieldCheck, FolderOpen, Boxes,
  ChevronRight, Layers, Sparkles, Hexagon, Plane,
} from "lucide-react";

const ACCENTS = {
  teal: "#00F5D4", orange: "#FF5400", volt: "#A6FF00",
  cyan: "#00E5FF", gold: "#D4B86A", magenta: "#FF2D78", green: "#00FF9C",
};

// ─────────────────────────────────────────────────────────────────────
// App registry — every icon on the rail, in display order.
// `kind: "window"` apps open inline (red X returns to logo splash)
// `kind: "route"`  apps navigate to a separate full-page experience
// ─────────────────────────────────────────────────────────────────────
const APPS = [
  // ── PRIMARY PRODUCT — STRATEX CORE (Directive 009)
  { id: "core",        kind: "route",  label: "Stratex Core",     icon: Sparkles,        accent: "cyan",   desc: "Property Intelligence Platform · Mission command · Passport · AWE", to: "/nextgen", primary: true },

  // ── INFO cluster: marketing content lifted out of the old landing scroll
  { id: "info",        kind: "window", label: "Info Hub",         icon: Info,            accent: "teal",   desc: "Recon stack · scientific rigor · everything that was on the landing page" },
  { id: "fleet",       kind: "window", label: "Fleet Trailer",    icon: Truck,           accent: "orange", desc: "Autonomous DJI Dock 2 trailer · Starlink · Solar core" },
  { id: "mesh",        kind: "window", label: "Vision Mesh",      icon: Hexagon,         accent: "teal",   desc: "Volumetric layering · 3D photogrammetry · radiometric overlay" },
  { id: "switchboard", kind: "window", label: "Switchboard",      icon: LayoutDashboard, accent: "volt",   desc: "Every operational dashboard surface" },

  // ── OPERATIONAL APPS — open the full pages
  { id: "mission",     kind: "route",  label: "Mission Control",  icon: Plane,       accent: "green",   desc: "Pre-Flight ATC · Doppler · Calendar · Fleet Map", to: "/mission-control" },
  { id: "deck",        kind: "route",  label: "Command Deck",     icon: ShieldCheck, accent: "gold",    desc: "Contractor command portal",                  to: "/deck" },
  { id: "binder",      kind: "route",  label: "Reports Binder",   icon: FolderOpen,  accent: "cyan",    desc: "Open every report page individually",       to: "/reports/binder" },
  { id: "passport",    kind: "route",  label: "Property Passport", icon: Sparkles,    accent: "gold",   desc: "Public homeowner certificate",              to: "/passport/877D9E3C8FC3" },
  { id: "claim",       kind: "route",  label: "Claim Snapshot",   icon: ShieldCheck, accent: "magenta", desc: "Before/after diff · adjuster fast-track",   to: "/claim-snapshot/877D9E3C8FC3" },
  { id: "scan",        kind: "route",  label: "New Drone Scan",   icon: Radar,       accent: "teal",    desc: "5-Agent scan-to-report engine",             to: "/demo/scan" },
  { id: "twin",        kind: "route",  label: "Diagnostic Twin",  icon: Box,         accent: "orange",  desc: "3-D wireframe · framing · thermal",         to: "/demo/twin" },
  { id: "quant",       kind: "route",  label: "Quant™ Estimator", icon: Cpu,         accent: "magenta", desc: "Take-off analytics · valuation",            to: "/demo/quant" },
  { id: "verify",      kind: "route",  label: "Verify Wall",      icon: Shield,      accent: "amber",   desc: "3-contact contractor verification",         to: "/contractor/verify" },
  { id: "gm",          kind: "route",  label: "GM Roster",        icon: Boxes,       accent: "amber",   desc: "Brand roster · pricing inventory",          to: "/gm/roster" },
  { id: "supply",      kind: "route",  label: "Supply Security",  icon: Shield,      accent: "orange",  desc: "Geofence · pipeline · encryption",          to: "/demo/supply-chain" },
];

// ─────────────────────────────────────────────────────────────────────
// Vertical rail — one icon per app · accent-colored · active highlight
// ─────────────────────────────────────────────────────────────────────
function AppRail({ activeId, onPick }) {
  return (
    <aside
      data-testid="app-rail"
      className="shrink-0 sticky top-0 self-start overflow-y-auto deck-rail-scroll
                 w-[68px] sm:w-[80px] lg:w-[96px] py-3
                 border-r"
      style={{
        height: "calc(100vh - 80px)",
        borderColor: "rgba(0,229,255,0.18)",
        background: "linear-gradient(180deg, rgba(8,14,24,0.92) 0%, rgba(2,6,11,0.96) 100%)",
        backdropFilter: "blur(14px)",
      }}
    >
      {/* STRATEX CORE brand mark — click returns to splash */}
      <button
        data-testid="rail-home"
        onClick={() => onPick(null)}
        className="block w-full px-2 mb-3"
        title="Home — STRATEX CORE"
      >
        <img
          src={ASSETS.stratex_core_logo}
          alt="STRATEX CORE"
          className="w-full h-auto rounded-md object-contain"
          style={{
            background: "#000",
            boxShadow: "0 0 14px rgba(77,246,255,0.35), inset 0 0 0 1px rgba(77,246,255,0.28)",
            padding: 2,
          }}
        />
      </button>

      <div className="border-t mx-2 mb-3" style={{ borderColor: "rgba(0,229,255,0.18)" }}/>

      <div className="space-y-2 px-2">
        {APPS.map((a) => {
          const c = ACCENTS[a.accent] || ACCENTS.cyan;
          const isActive = activeId === a.id;
          const Icon = a.icon;
          return (
            <button
              key={a.id}
              data-testid={`app-icon-${a.id}`}
              onClick={() => onPick(a)}
              title={a.label}
              className="group relative w-full aspect-square rounded-xl transition-all hover:scale-105"
              style={{
                background: isActive
                  ? `linear-gradient(135deg, ${c}28 0%, ${c}10 100%)`
                  : "rgba(8,14,24,0.85)",
                border: `1.5px solid ${isActive ? c : `${c}44`}`,
                boxShadow: isActive
                  ? `0 0 18px ${c}66, inset 0 0 18px ${c}18`
                  : `inset 0 0 10px ${c}08`,
              }}
            >
              {/* corner brackets — futuristic touch */}
              <span className="absolute top-1 left-1 w-2 h-2 border-t border-l" style={{ borderColor: c }}/>
              <span className="absolute bottom-1 right-1 w-2 h-2 border-b border-r" style={{ borderColor: c }}/>
              <Icon size={20} strokeWidth={1.7} color={c}
                    style={{ filter: `drop-shadow(0 0 6px ${c}aa)` }}
                    className="mx-auto"/>
              <div className="font-mono text-[7.5px] tracking-[0.16em] uppercase mt-1 px-1 leading-tight"
                   style={{ color: c }}>
                {a.label.split(" ")[0]}
              </div>
              {isActive && (
                <span className="absolute -left-2 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r"
                      style={{ background: c, boxShadow: `0 0 8px ${c}` }}/>
              )}
            </button>
          );
        })}
      </div>

      <div className="mt-4 px-3 font-mono text-[8px] tracking-[0.22em] uppercase text-slate-600 text-center">
        STRATEX™ · v4.0
      </div>
    </aside>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Generic window chrome — every in-place app uses this so they share
// the same red [X] cancel pill and visual frame.
// ─────────────────────────────────────────────────────────────────────
function WindowFrame({ app, onClose, children }) {
  const c = ACCENTS[app.accent] || ACCENTS.cyan;
  const Icon = app.icon;
  return (
    <div
      data-testid={`window-${app.id}`}
      className="rounded-xl relative overflow-hidden"
      style={{
        background: "linear-gradient(180deg, rgba(8,14,24,0.94) 0%, rgba(4,8,14,0.96) 100%)",
        border: `1.5px solid ${c}88`,
        boxShadow:
          `inset 0 0 40px ${c}10, ` +
          `0 0 0 1px ${c}22, ` +
          `0 16px 48px rgba(0,0,0,0.5)`,
      }}
    >
      {/* TITLE BAR */}
      <div className="sticky top-0 z-10 px-4 sm:px-5 py-3 flex items-center justify-between gap-3 border-b backdrop-blur"
           style={{ borderColor: `${c}44`, background: "rgba(2,6,11,0.85)" }}>
        <div className="flex items-center gap-3 min-w-0">
          <span className="grid place-items-center rounded-sm shrink-0"
                style={{ width: 32, height: 32, background: `${c}14`,
                         border: `1px solid ${c}88`, color: c }}>
            <Icon size={16} strokeWidth={1.7}/>
          </span>
          <div className="min-w-0">
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: c }}>
              // APP · {app.id.toUpperCase()}
            </div>
            <div className="font-display text-[14px] uppercase tracking-[0.1em] text-white truncate">
              {app.label}
            </div>
          </div>
        </div>
        <button
          data-testid={`window-close-${app.id}`}
          onClick={onClose}
          title="Close — back to STRATEX™ logo"
          className="grid place-items-center rounded-full transition hover:brightness-125 shrink-0"
          style={{
            width: 32, height: 32,
            background: "#FF2D2D",
            color: "#fff",
            boxShadow: "0 0 14px rgba(255,45,45,0.65)",
            border: "1px solid #FF5555",
          }}>
          <X size={14} strokeWidth={3}/>
        </button>
      </div>

      {/* WINDOW BODY */}
      <div className="p-4 sm:p-6 md:p-8 max-h-[calc(100vh-180px)] overflow-y-auto deck-rail-scroll">
        {children}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Window content — INFO HUB (Recon Stack + Scientific Rigor)
// ─────────────────────────────────────────────────────────────────────
function InfoWindow() {
  return (
    <div className="space-y-10">
      <div>
        <SectionTitle eyebrow="// THREE OPERATIONAL MODULES" title="The STRATEX™ Recon Stack" />
        <div className="grid md:grid-cols-3 gap-4 mt-6">
          <Pillar tag="MODULE 01" accent="teal"   icon={Crosshair} title="STRATEX Vision™"
                  blurb="3-D spatial photogrammetry & live mesh engine. Drone-captured orthomosaics stitched into millimeter-accurate roof topology." />
          <Pillar tag="MODULE 02" accent="orange" icon={Activity}  title="STRATEX Thermal™"
                  blurb="Sub-surface radiometric mass quantization. Cross-references diurnal temperature shift cycles with thermal capacitance modeling to isolate true moisture entrapment from surface reflectivity." />
          <Pillar tag="MODULE 03" accent="teal"   icon={Cpu}       title="STRATEX Quant™"
                  blurb="Multi-agent actuarial estimating engine. Auto-maps every line-item to Xactimate tags under a locked 20/25 O&P envelope." />
        </div>
      </div>

      <div>
        <SectionTitle eyebrow="// ABSOLUTE SCIENTIFIC RIGOR" title="Quantitative Sub-Surface Analytics" />
        <p className="text-sm text-muted-hud font-body leading-relaxed max-w-3xl mt-4 mb-6">
          Every STRATEX™ scan is a mathematical instrument. Radiometric drone telemetry is fused with localised
          diurnal weather data and a proprietary thermal-capacitance model to compute the actual moisture volume
          and depth beneath the membrane — never a generic heat-map approximation.
        </p>
        <div className="grid md:grid-cols-3 gap-4">
          {[
            { eyebrow: "// SUB-SURFACE QUANTIZATION", title: "Sub-Surface Moisture Quantization",
              icon: Activity,  accent: "teal",
              body: "Calculates true thermodynamic mass anomalies beneath the roof substrate, isolating actual moisture entrapment from simple surface reflectivity." },
            { eyebrow: "// MATHEMATICAL ACCURACY", title: "Absolute Mathematical Accuracy",
              icon: Crosshair, accent: "orange",
              body: "Cross-references radiometric drone telemetry with localised diurnal temperature shift cycles to eliminate false positives." },
            { eyebrow: "// EDGE PRECISION", title: "Precision Edge-Mapping",
              icon: Box, accent: "teal",
              body: "High-contrast vector detailing ensures that moisture boundaries are calculated down to the exact square inch, giving field crews flawless repair lines." },
          ].map((r, i) => {
            const c = ACCENTS[r.accent];
            const Icon = r.icon;
            return (
              <HudCard key={i} scanline className="p-5">
                <div className="flex items-center gap-3 mb-3" style={{ color: c }}>
                  <Icon size={16} strokeWidth={1.5}/>
                  <span className="font-mono text-[9.5px] tracking-[0.3em] uppercase">{r.eyebrow}</span>
                </div>
                <h3 className="font-display text-base uppercase tracking-[0.12em] text-silver mb-2">{r.title}</h3>
                <p className="text-[12px] text-muted-hud leading-relaxed font-body">{r.body}</p>
              </HudCard>
            );
          })}
        </div>
      </div>

      <div>
        <SectionTitle eyebrow="// PROOF AT A GLANCE" title="The Numbers That Run the Engine" />
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
          <DataReadout label="Ground Truth" value="±0.78 CM"/>
          <DataReadout label="Drone Payload" value="DJI MATRICE 4TD"/>
          <DataReadout label="Code Stack" value="REACT · FASTAPI · MONGO"/>
          <DataReadout label="MVP Sprint" value="14 DAYS"/>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Window content — FLEET TRAILER
// ─────────────────────────────────────────────────────────────────────
function FleetWindow() {
  return (
    <div>
      <SectionTitle eyebrow="// AUTONOMOUS FIELD RIG" title="Fleet Command Trailer" />
      <p className="text-sm text-muted-hud font-body leading-relaxed mt-3 mb-6">
        A custom 5×8 enclosed cargo trailer outfitted with a motorised roof hatch, DJI Dock 2,
        solar power core and Starlink Mini. STRATEX™ deploys autonomously — no pilots, no ladders,
        no climbing.
      </p>
      <div className="grid grid-cols-1 lg:grid-cols-[1fr_1fr] gap-5 items-start">
        <div className="grid grid-cols-2 gap-3">
          {[
            { l: "Power Core", v: "400W Solar · 200Ah LiFePO4", icon: Sun },
            { l: "Comms",      v: "Starlink Mini · Unlimited",  icon: Satellite },
            { l: "Actuators",  v: "2× VEVOR 12V · 220 lb",      icon: Zap },
            { l: "Drone",      v: "DJI Dock 2 + M3TD",          icon: Shield },
          ].map((s) => (
            <HudCard key={s.l} className="p-4">
              <div className="flex items-center gap-2 text-teal mb-2">
                <s.icon size={14}/>
                <span className="font-mono text-[10px] tracking-widest uppercase">{s.l}</span>
              </div>
              <p className="text-silver font-heading text-sm">{s.v}</p>
            </HudCard>
          ))}
        </div>
        <HudCard scanline className="p-2 flex items-center justify-center">
          <img src={ASSETS.trailer_engineering} alt="STRATEX Trailer Engineering"
               className="w-full h-auto rounded-sm"
               style={{ maxHeight: 320, objectFit: "contain", imageRendering: "high-quality" }}/>
        </HudCard>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Window content — VISION MESH (3D + feature grid)
// ─────────────────────────────────────────────────────────────────────
function MeshWindow({ demo, isMobile }) {
  return (
    <div>
      <SectionTitle eyebrow="// VOLUMETRIC LAYERING ENGINE" title="STRATEX Vision™ — Sub-Surface Mesh" />
      <div className="mt-4 max-w-3xl mx-auto">
        <HudCard scanline className="p-2">
          <RoofModel3D
            telemetry={demo || {
              style: "stratex_demo", scale: 1.0,
              facets: [], edges: [], framing: { rafters: [], sub_fascia: [] }, gutters: { polylines: [], downspouts: [] },
            }}
            anomalies={demo?.anomalies || []}
            height={isMobile ? 240 : 340}
            showLabels={!isMobile}
            layers={null}
            primaryLayer="shingle"
            showGutters={true}
          />
        </HudCard>
      </div>
      <p className="text-sm text-muted-hud max-w-2xl mt-4 font-body leading-relaxed">
        Razor-sharp point clouds + high-contrast volumetric mesh overlays. Moisture boundaries pulse Neon
        Orange against a Metallic Nickel substrate, with Electric Teal vector edges locked to the exact
        square inch.
      </p>
      {demo?.validation && (
        <div className="mt-5 max-w-2xl"><ValidationReport validation={demo.validation}/></div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-6">
        {[
          { icon: Cloud,    label: "Cloud Rendering",   v: "Real-time photogrammetry stitch" },
          { icon: Activity, label: "Thermal Map",       v: "Radiometric anomaly overlay" },
          { icon: Cpu,      label: "Multi-Agent Core",  v: "4 narrow AI specialists" },
          { icon: Box,      label: "Xactimate Bridge",  v: "Supplement-ready billing tags" },
        ].map((it) => (
          <HudCard key={it.label} className="p-3">
            <div className="flex items-center gap-2 mb-1.5 text-muted-hud">
              <it.icon size={13}/>
              <span className="font-mono text-[9.5px] tracking-widest uppercase">{it.label}</span>
            </div>
            <p className="text-silver font-heading text-[13px]">{it.v}</p>
          </HudCard>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Window content — SWITCHBOARD (every dashboard, compact bento)
// ─────────────────────────────────────────────────────────────────────
function SwitchboardWindow() {
  const groups = [
    { title: "Demo Modules",        accent: "teal",   items: [
        { id: "demo-scan",   label: "New Drone Scan",          to: "/demo/scan",          icon: Radar },
        { id: "demo-twin",   label: "Diagnostic Twin",         to: "/demo/twin",          icon: Box },
        { id: "demo-maint",  label: "Maintenance Priority",    to: "/demo/maintenance",   icon: Activity },
        { id: "demo-quant",  label: "Quant™ Estimator",        to: "/demo/quant",         icon: Cpu },
        { id: "demo-supply", label: "Supply Security",         to: "/demo/supply-chain",  icon: Shield },
    ]},
    { title: "Executive Cockpits",  accent: "volt",   items: [
        { id: "ceo-ops",       label: "CEO Cockpit",       to: "/ceo/ops",       icon: Satellite },
        { id: "ceo-suppliers", label: "Supplier Registry", to: "/ceo/suppliers", icon: Cloud },
        { id: "ceo-login",     label: "CEO Secure Portal", to: "/ceo/login",     icon: Shield },
    ]},
    { title: "Operations",          accent: "orange", items: [
        { id: "gm-roster", label: "GM Roster · Pricing",  to: "/gm/roster",   icon: Boxes },
        { id: "admin-ops", label: "Admin Operations",     to: "/admin/ops",   icon: Cpu },
        { id: "pricing",   label: "Pricing & Plans",      to: "/pricing",     icon: Zap },
    ]},
    { title: "Field & Contractor",  accent: "teal",   items: [
        { id: "contractor", label: "Contractor Portal",  to: "/auth",                icon: Crosshair },
        { id: "verify",     label: "Verify Wall",        to: "/contractor/verify",   icon: Shield },
        { id: "pilot",      label: "Pilot Terminal",     to: "/pilot",               icon: Sun },
        { id: "operator",   label: "Operator Console",   to: "/operator",            icon: Radar },
    ]},
    { title: "Reports & Passport",  accent: "gold",   items: [
        { id: "deck",     label: "Command Deck",      to: "/deck",            icon: ShieldCheck },
        { id: "binder",   label: "Reports Binder",    to: "/reports/binder",  icon: FolderOpen },
        { id: "passport", label: "Property Passport", to: "/passport/877D9E3C8FC3", icon: Sparkles },
    ]},
  ];
  return (
    <div className="space-y-6">
      <SectionTitle eyebrow="// MASTER PORTAL · ALL DASHBOARDS" title="Every Command Surface, One Switchboard"/>
      <div className="space-y-6 mt-2">
        {groups.map((g) => {
          const dot = ACCENTS[g.accent];
          return (
            <div key={g.title}>
              <div className="flex items-center gap-3 mb-3">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: dot, boxShadow: `0 0 6px ${dot}` }}/>
                <h3 className="font-display text-[13px] uppercase tracking-[0.2em] text-silver">{g.title}</h3>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2.5">
                {g.items.map((it) => {
                  const Icon = it.icon;
                  return (
                    <Link key={it.id} to={it.to}
                          data-testid={`switchboard-${it.id}`}
                          className="group block rounded-md p-3 transition-all hover:scale-[1.015] hover:brightness-110"
                          style={{ background: "rgba(15,22,34,0.55)",
                                   border: `1px solid ${dot}55`,
                                   boxShadow: `inset 0 0 14px ${dot}10` }}>
                      <Icon size={14} color={dot} style={{ filter: `drop-shadow(0 0 4px ${dot}99)` }}/>
                      <div className="mt-2 font-display text-[11px] uppercase tracking-[0.08em] text-silver leading-tight">{it.label}</div>
                      <div className="mt-0.5 font-mono text-[8px] tracking-[0.16em] uppercase" style={{ color: dot }}>{it.to}</div>
                    </Link>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Default state — STRATEX CORE hero (Directive 009) with primary entry CTA.
// Cross AI is the parent company but Stratex Core is the dominant product.
// ─────────────────────────────────────────────────────────────────────
function LogoSplash({ onPickInfo }) {
  const nav = useNavigate();
  return (
    <div data-testid="logo-splash"
         className="relative rounded-xl overflow-hidden flex flex-col items-center justify-center text-center p-6 sm:p-10 min-h-[62vh]"
         style={{
           background:
             "radial-gradient(700px 320px at 50% 0%, rgba(77,246,255,0.10), transparent 60%)," +
             "radial-gradient(500px 260px at 90% 110%, rgba(255,123,0,0.07), transparent 60%)," +
             "linear-gradient(180deg, rgba(8,14,24,0.7) 0%, rgba(4,8,14,0.9) 100%)",
           border: "1.5px solid rgba(77,246,255,0.32)",
           boxShadow: "inset 0 0 80px rgba(77,246,255,0.10)",
         }}>
      {/* corner brackets */}
      {[
        "top-3 left-3 border-t-2 border-l-2",
        "top-3 right-3 border-t-2 border-r-2",
        "bottom-3 left-3 border-b-2 border-l-2",
        "bottom-3 right-3 border-b-2 border-r-2",
      ].map((cls, i) => (
        <span key={i} className={`absolute ${cls} w-5 h-5`} style={{ borderColor: "#4DF6FF" }}/>
      ))}

      {/* STRATEX CORE hero — approved brand asset */}
      <img
        src="/brand/stratex-core-logo.png"
        alt="STRATEX CORE — Property Intelligence Platform"
        className="w-full max-w-xs sm:max-w-md md:max-w-xl h-auto rounded-lg"
        style={{
          boxShadow: "0 0 60px rgba(77,246,255,0.25), inset 0 0 0 1px rgba(77,246,255,0.18)",
        }}
        data-testid="splash-stratex-core-logo"
      />

      {/* Primary CTA — Enter Stratex Core */}
      <button
        data-testid="splash-enter-core-cta"
        onClick={() => nav("/nextgen")}
        className="mt-8 font-mono uppercase tracking-[0.24em] text-[13px] px-8 py-4 rounded-lg flex items-center gap-3 transition hover:brightness-110 active:translate-y-[1px]"
        style={{
          background: "linear-gradient(180deg, #FF9A3D 0%, #FF7B00 100%)",
          color: "#0B0F14",
          fontWeight: 700,
          boxShadow: "0 12px 32px rgba(255,123,0,0.30), inset 0 1px 0 rgba(255,255,255,0.2)",
          border: "none",
          minHeight: 56,
        }}>
        Enter Stratex Core <ChevronRight size={16} strokeWidth={2.4}/>
      </button>

      <div className="font-mono text-[10px] tracking-[0.32em] uppercase mt-5" style={{ color: "#4DF6FF" }}>
        Property Intelligence Platform · Preview Build
      </div>

      {/* Secondary — legacy explore */}
      <div className="mt-8 pt-6 border-t max-w-md w-full" style={{ borderColor: "rgba(77,246,255,0.15)" }}>
        <div className="font-mono text-[9px] tracking-[0.28em] uppercase mb-3" style={{ color: "#6D7B8F" }}>
          // Explore Legacy Modules
        </div>
        <button
          data-testid="splash-info-cta"
          onClick={onPickInfo}
          className="font-mono text-[10px] tracking-[0.22em] uppercase px-4 py-2 rounded-md inline-flex items-center gap-2 transition hover:brightness-125"
          style={{ background: "rgba(0,229,255,0.08)", border: `1px solid ${ACCENTS.cyan}66`, color: ACCENTS.cyan }}>
          Open Info Hub <ChevronRight size={12}/>
        </button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Marketing Pillar tile (same look as before, kept inside Info Hub)
// ─────────────────────────────────────────────────────────────────────
function Pillar({ tag, accent, icon: Icon, title, blurb }) {
  const c = ACCENTS[accent] || ACCENTS.teal;
  return (
    <HudCard scanline className="p-5">
      <div className="flex items-center gap-3 mb-3" style={{ color: c }}>
        <Icon size={18} strokeWidth={1.5}/>
        <span className="font-mono text-[10px] tracking-[0.28em] uppercase">{tag}</span>
      </div>
      <h3 className="font-display text-base md:text-lg uppercase tracking-[0.12em] text-silver mb-2">{title}</h3>
      <p className="text-[12.5px] text-muted-hud leading-relaxed font-body">{blurb}</p>
    </HudCard>
  );
}

// ─────────────────────────────────────────────────────────────────────
// Main shell
// ─────────────────────────────────────────────────────────────────────
export default function Landing() {
  const isMobile = useIsMobile();
  const nav = useNavigate();
  const contractor = useContractor();
  const [demo, setDemo] = useState(null);
  const [activeApp, setActiveApp] = useState(null);

  // Existing demo telemetry fetch — preserved.
  useEffect(() => {
    let dead = false;
    api.get("/demo/sample-roof")
       .then((r) => { if (!dead && r.data) setDemo(r.data); })
       .catch(() => {});
    return () => { dead = true; };
  }, []);

  const pickApp = (app) => {
    if (!app) { setActiveApp(null); return; }
    if (app.kind === "route") { nav(app.to); return; }
    setActiveApp(app);
  };

  return (
    <div className="min-h-screen text-silver flex flex-col"
         style={{
           background:
             "radial-gradient(ellipse at 75% 8%, rgba(0,229,255,0.10) 0%, transparent 55%)," +
             "radial-gradient(ellipse at 8% 92%, rgba(255,84,0,0.07) 0%, transparent 55%)," +
             "#02060B",
           fontFamily: "'Sora', sans-serif",
         }}>
      {/* faint grid */}
      <div aria-hidden className="pointer-events-none fixed inset-0 opacity-[0.05]"
           style={{ backgroundImage:
             "linear-gradient(rgba(0,229,255,0.6) 1px, transparent 1px),linear-gradient(90deg, rgba(0,229,255,0.6) 1px, transparent 1px)",
             backgroundSize: "60px 60px",
             maskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)",
             WebkitMaskImage: "radial-gradient(ellipse at center, black 30%, transparent 80%)" }}/>

      {/* ─── Parent-company attribution — subordinate to Stratex Core (Directive 009 §6) ─── */}
      <header data-testid="cross-ai-banner"
              className="relative w-full border-b overflow-hidden"
              style={{
                background: "#000",
                borderColor: "rgba(0,229,255,0.15)",
                height: "72px",
              }}>
        <img
          src="/brand/cross_ai_banner.png"
          alt="A Cross AI Softwares Inc. product"
          data-testid="cross-ai-logo"
          className="block select-none pointer-events-none"
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            objectPosition: "center",
          }}
        />
      </header>

      <div className="flex flex-1 min-h-0">
      <AppRail activeId={activeApp?.id} onPick={pickApp}/>

      {/* Display screen — flex-1 */}
      <main className="flex-1 min-w-0 px-3 sm:px-6 lg:px-8 py-4 sm:py-6">
        {/* tiny top status strip */}
        <div className="flex items-center justify-between mb-4 px-1 flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"
                  style={{ boxShadow: "0 0 6px #00FF9C" }}/>
            <span className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-500">
              SYS · OPERATIONAL · TENANT {contractor.business_name.toUpperCase()}
            </span>
          </div>
          <div className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-500">
            APP LAUNCHER · v4.1
          </div>
        </div>

        {activeApp ? (
          <WindowFrame app={activeApp} onClose={() => setActiveApp(null)}>
            {activeApp.id === "info"        && <InfoWindow/>}
            {activeApp.id === "fleet"       && <FleetWindow/>}
            {activeApp.id === "mesh"        && <MeshWindow demo={demo} isMobile={isMobile}/>}
            {activeApp.id === "switchboard" && <SwitchboardWindow/>}
          </WindowFrame>
        ) : (
          <LogoSplash onPickInfo={() => setActiveApp(APPS.find((a) => a.id === "info"))}/>
        )}

        <footer className="mt-6 px-1 font-mono text-[8.5px] tracking-[0.22em] uppercase text-slate-600 flex flex-col sm:flex-row justify-between gap-1">
          <span>STRATEX™ 2026 · Strategic Thermal Reconnaissance · A CROSS AI SOFTWARES INC. PRODUCT</span>
          <span style={{ color: ACCENTS.teal }}>v4.1 · APP LAUNCHER BUILD</span>
        </footer>
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
