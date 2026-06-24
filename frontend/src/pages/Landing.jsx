import React, { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { HudCard, DataReadout, SectionTitle } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import ValidationReport from "@/components/ValidationReport";
import useIsMobile from "@/hooks/use-is-mobile";
import { api } from "@/lib/api";
import { Crosshair, Cpu, Activity, Radar, ArrowRight, Shield, Zap, Cloud, Satellite, Sun, Box } from "lucide-react";

const PORTAL_TILES = [
  { id: "scan",   label: "New Drone Scan",            sub: "Upload imagery → CAD/BIM report", to: "/demo/scan",          accent: "teal",   primary: true, icon: Radar },
  { id: "twin",   label: "Diagnostic Twin Command",   sub: "3D wireframe · framing · thermal",  to: "/demo/twin",          accent: "orange", icon: Box },
  { id: "maint",  label: "AI Maintenance Priority",   sub: "Urgency-ranked task queue",         to: "/demo/maintenance",   accent: "teal",   icon: Activity },
  { id: "quant",  label: "STRATEX Quant™ Estimator",  sub: "Take-off analytics · valuation",    to: "/demo/quant",         accent: "volt",   icon: Cpu },
  { id: "supply", label: "Supply Chain Security",     sub: "Geofence · pipeline · encryption",  to: "/demo/supply-chain",  accent: "orange", icon: Shield },
];

function PortalTile({ tile }) {
  const accentClass = tile.accent === "orange" ? "text-plasma" : tile.accent === "volt" ? "text-volt" : "text-teal";
  const accentColor = tile.accent === "orange" ? "#FF5400" : tile.accent === "volt" ? "#A6FF00" : "#00F5D4";
  const Icon = tile.icon;
  return (
    <Link to={tile.to} data-testid={`portal-tile-${tile.id}`} className="block group">
      <HudCard scanline className={`p-5 md:p-6 h-full transition-all hover:brightness-110 hover:scale-[1.01] ${tile.primary ? "ring-1 ring-teal/40" : ""}`}>
        <div className={`flex items-center gap-3 mb-4 ${accentClass}`}>
          <Icon size={20} strokeWidth={1.5}/>
          <span className="font-mono text-[10px] tracking-[0.28em] uppercase">{tile.primary ? "PRIMARY OPERATION" : `MODULE · ${tile.id.toUpperCase()}`}</span>
        </div>
        <h3 className="font-display text-base md:text-lg uppercase tracking-[0.12em] text-silver">{tile.label}</h3>
        <p className="font-body text-xs text-muted-hud leading-relaxed mt-2">{tile.sub}</p>
        <div className="mt-4 font-mono text-[10px] tracking-[0.22em] uppercase" style={{ color: accentColor }}>
          Launch →
        </div>
      </HudCard>
    </Link>
  );
}

const Pillar = ({ tag, title, blurb, icon: Icon, accent, testid }) => (
  <HudCard scanline className="p-6 md:p-8" data-testid={testid}>
    <div className={`flex items-center gap-3 mb-6 ${accent === "orange" ? "text-plasma" : accent === "volt" ? "text-volt" : "text-teal"}`}>
      <Icon size={22} strokeWidth={1.5} />
      <span className="font-mono text-[11px] tracking-[0.3em] uppercase">{tag}</span>
    </div>
    <h3 className="font-display text-2xl uppercase tracking-[0.14em] text-silver mb-3">{title}</h3>
    <p className="text-sm text-muted-hud leading-relaxed font-body">{blurb}</p>
  </HudCard>
);

export default function Landing() {
  const isMobile = useIsMobile(900);
  const [demo, setDemo] = useState(null);
  useEffect(() => {
    api.get("/public/demo-topology").then((r) => setDemo(r.data)).catch(() => setDemo(null));
  }, []);
  return (
    <div data-testid="landing-page">
      {/* HERO */}
      <section className="relative px-4 md:px-12 pt-10 md:pt-16 pb-16 md:pb-24 overflow-hidden">
        <div className="absolute inset-0 grid-floor opacity-30 pointer-events-none" />
        <div className="max-w-[1500px] mx-auto grid lg:grid-cols-[1.05fr_1fr] gap-8 md:gap-12 items-center relative">
          <div className="min-w-0">
            <div className="flex items-center gap-3 mb-4 md:mb-6">
              <span className="led led-teal" />
              <span className="font-mono text-[10px] md:text-[11px] tracking-[0.32em] text-teal uppercase">STRATEX™ • STRATEGIC THERMAL RECONNAISSANCE • v1.2.0</span>
            </div>
            <h1 className="font-display text-[1.75rem] leading-[1.04] sm:text-5xl md:text-6xl lg:text-7xl uppercase tracking-[0.02em] sm:tracking-[0.06em] sm:leading-[0.95] text-silver" style={{ overflowWrap: "anywhere", wordBreak: "break-word" }}>
              <span className="block">STRATEGIC</span>
              <span className="block">THERMAL</span>
              <span className="block text-teal glow-teal">RECONNAISSANCE</span>
            </h1>
            <p className="mt-5 md:mt-6 max-w-xl text-sm md:text-lg text-muted-hud font-body leading-relaxed">
              STRATEX™ does not display surface anomalies — it <span className="text-teal">quantifies them</span>.
              Radiometric drone telemetry is cross-referenced with localized weather data and a proprietary thermal
              capacitance model to calculate the <span className="text-silver">true moisture volume and depth beneath the roof membrane</span> —
              not what reflects off the surface, but the actual sub-surface mass entrapment, measured to the cubic inch.
            </p>
            <div className="mt-8 md:mt-10">
              <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase mb-3">// MASTER PORTAL SWITCHBOARD</div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl">
                {PORTAL_TILES.slice(0, 1).map((t) => <PortalTile key={t.id} tile={t}/>)}
                {PORTAL_TILES.slice(1, 3).map((t) => <PortalTile key={t.id} tile={t}/>)}
              </div>
            </div>
            <div className="mt-10 md:mt-12 grid grid-cols-2 sm:grid-cols-4 gap-4 md:gap-6 max-w-2xl">
              <DataReadout label="Trailer Rigs" value="24/7" testid="stat-trailers" />
              <DataReadout label="Uplink" value="STARLINK" accent="volt" testid="stat-uplink" />
              <DataReadout label="O&P Lock" value="20 / 25" accent="orange" testid="stat-op" />
              <DataReadout label="MVP Sprint" value="14 DAYS" testid="stat-sprint" />
            </div>
          </div>

          <div className="relative">
            <HudCard scanline className="p-3">
              <img src={ASSETS.logo} alt="STRATEX Neon Nexus" className="w-full h-auto" data-testid="hero-logo" />
            </HudCard>
            <div className="absolute -bottom-6 -left-6 hidden md:block">
              <HudCard className="px-4 py-3">
                <span className="font-mono text-[11px] text-muted-hud tracking-widest uppercase">Luxury-Corporate Palette</span>
                <div className="flex gap-2 mt-2" data-testid="palette-swatches">
                  <span className="w-6 h-6" style={{background:"#00F5D4", boxShadow:"0 0 8px #00F5D4"}} title="Electric Teal" data-testid="swatch-electric-teal" />
                  <span className="w-6 h-6" style={{background:"#FF5400", boxShadow:"0 0 8px #FF5400"}} title="Neon Orange" data-testid="swatch-neon-orange" />
                  <span className="w-6 h-6" style={{background:"#3A4350", border:"1px solid rgba(0,245,212,0.35)"}} title="Metallic Nickel" data-testid="swatch-metallic-nickel" />
                </div>
              </HudCard>
            </div>
          </div>
        </div>
      </section>

      {/* PILLARS */}
      <section className="px-6 md:px-12 py-16 relative">
        <div className="max-w-[1500px] mx-auto">
          <SectionTitle eyebrow="// THREE OPERATIONAL MODULES" title="The STRATEX™ Recon Stack" />
          <div className="grid md:grid-cols-3 gap-6">
            <Pillar tag="MODULE 01" accent="teal" icon={Crosshair} title="STRATEX Vision™"
              blurb="3D spatial photogrammetry & live mesh engine. Drone-captured orthomosaics stitched into millimeter-accurate roof topology."
              testid="pillar-vision" />
            <Pillar tag="MODULE 02" accent="orange" icon={Activity} title="STRATEX Thermal™"
              blurb="Sub-surface radiometric mass quantization. Cross-references diurnal temperature shift cycles with thermal capacitance modeling to isolate true moisture entrapment from surface reflectivity — eliminating false positives at the substrate."
              testid="pillar-thermal" />
            <Pillar tag="MODULE 03" accent="teal" icon={Cpu} title="STRATEX Quant™"
              blurb="Multi-agent actuarial estimating engine. Auto-maps every line-item to Xactimate tags under a locked 20/25 O&P envelope."
              testid="pillar-quant" />
          </div>
        </div>
      </section>

      {/* SCIENTIFIC RIGOR — Sub-Surface Quantization · Mathematical Accuracy · Precision Edge-Mapping */}
      <section className="px-6 md:px-12 py-16 relative" data-testid="scientific-rigor-section">
        <div className="max-w-[1500px] mx-auto">
          <SectionTitle eyebrow="// ABSOLUTE SCIENTIFIC RIGOR" title="Quantitative Sub-Surface Analytics" />
          <p className="text-sm md:text-base text-muted-hud font-body leading-relaxed max-w-3xl mb-10">
            Every STRATEX™ scan is a mathematical instrument. Radiometric drone telemetry is fused with localized
            diurnal weather data and a proprietary thermal-capacitance model to compute the actual moisture volume
            and depth beneath the membrane — never a generic heat-map approximation.
          </p>
          <div className="grid md:grid-cols-3 gap-6" data-testid="rigor-tiles">
            <HudCard scanline className="p-6 md:p-7" data-testid="rigor-quantization">
              <div className="flex items-center gap-3 mb-4 text-teal">
                <Activity size={18} strokeWidth={1.5} />
                <span className="font-mono text-[10.5px] tracking-[0.3em] uppercase">// SUB-SURFACE QUANTIZATION</span>
              </div>
              <h3 className="font-display text-lg md:text-xl uppercase tracking-[0.14em] text-silver mb-3">
                Sub-Surface Moisture Quantization
              </h3>
              <p className="text-sm text-muted-hud leading-relaxed font-body">
                Calculates true thermodynamic mass anomalies beneath the roof substrate, isolating actual
                moisture entrapment from simple surface reflectivity.
              </p>
            </HudCard>

            <HudCard scanline className="p-6 md:p-7" data-testid="rigor-accuracy">
              <div className="flex items-center gap-3 mb-4" style={{ color: "#FF5400" }}>
                <Crosshair size={18} strokeWidth={1.5} />
                <span className="font-mono text-[10.5px] tracking-[0.3em] uppercase">// MATHEMATICAL ACCURACY</span>
              </div>
              <h3 className="font-display text-lg md:text-xl uppercase tracking-[0.14em] text-silver mb-3">
                Absolute Mathematical Accuracy
              </h3>
              <p className="text-sm text-muted-hud leading-relaxed font-body">
                Cross-references radiometric drone telemetry with localized diurnal temperature shift cycles
                to eliminate false positives.
              </p>
            </HudCard>

            <HudCard scanline className="p-6 md:p-7" data-testid="rigor-edge-mapping">
              <div className="flex items-center gap-3 mb-4 text-teal">
                <Box size={18} strokeWidth={1.5} />
                <span className="font-mono text-[10.5px] tracking-[0.3em] uppercase">// EDGE PRECISION</span>
              </div>
              <h3 className="font-display text-lg md:text-xl uppercase tracking-[0.14em] text-silver mb-3">
                Precision Edge-Mapping
              </h3>
              <p className="text-sm text-muted-hud leading-relaxed font-body">
                High-contrast vector detailing ensures that moisture boundaries are calculated down to the
                exact square inch, giving field crews flawless repair lines.
              </p>
            </HudCard>
          </div>
        </div>
      </section>

      {/* FLEET COMMAND */}
      <section className="px-6 md:px-12 py-16">
        <div className="max-w-[1500px] mx-auto grid lg:grid-cols-2 gap-10 items-center">
          <div>
            <SectionTitle eyebrow="// AUTONOMOUS FIELD RIG" title="Fleet Command Trailer" />
            <p className="text-base text-muted-hud font-body leading-relaxed mb-6">
              A custom 5×8 enclosed cargo trailer outfitted with a motorized roof hatch, DJI Dock 2, solar power core, and Starlink Mini. STRATEX™ deploys autonomously — no pilots, no ladders, no climbing.
            </p>
            <div className="grid grid-cols-2 gap-4">
              <HudCard className="p-4"><div className="flex items-center gap-2 text-teal mb-2"><Sun size={16}/><span className="font-mono text-[11px] tracking-widest uppercase">Power Core</span></div><p className="text-silver font-heading text-lg">400W Solar • 200Ah LiFePO4</p></HudCard>
              <HudCard className="p-4"><div className="flex items-center gap-2 text-teal mb-2"><Satellite size={16}/><span className="font-mono text-[11px] tracking-widest uppercase">Comms</span></div><p className="text-silver font-heading text-lg">Starlink Mini • Unlimited</p></HudCard>
              <HudCard className="p-4"><div className="flex items-center gap-2 text-teal mb-2"><Zap size={16}/><span className="font-mono text-[11px] tracking-widest uppercase">Actuators</span></div><p className="text-silver font-heading text-lg">2× VEVOR 12V • 220 lb</p></HudCard>
              <HudCard className="p-4"><div className="flex items-center gap-2 text-teal mb-2"><Shield size={16}/><span className="font-mono text-[11px] tracking-widest uppercase">Drone</span></div><p className="text-silver font-heading text-lg">DJI Dock 2 + M3TD</p></HudCard>
            </div>
          </div>
          <HudCard scanline className="p-2">
            <img src={ASSETS.trailer_engineering} alt="STRATEX Trailer Engineering" className="w-full h-auto" data-testid="fleet-trailer-image" />
          </HudCard>
        </div>
      </section>

      {/* DASHBOARD MONTAGE */}
      <section className="px-6 md:px-12 py-16">
        <div className="max-w-[1500px] mx-auto">
          <SectionTitle eyebrow="// VOLUMETRIC LAYERING ENGINE" title="STRATEX Vision™ — Sub-Surface Mesh"/>
          <HudCard scanline className="p-2">
            <RoofModel3D
              telemetry={demo || {
                style: "stratex_demo", scale: 1.0,
                facets: [], edges: [], framing: { rafters: [], sub_fascia: [] }, gutters: { polylines: [], downspouts: [] },
              }}
              anomalies={demo?.anomalies || []}
              height={isMobile ? 360 : 560}
              showLabels={!isMobile}
              layers={null}
              primaryLayer="shingle"
              showGutters={true}
            />
          </HudCard>
          <p className="text-sm text-muted-hud max-w-2xl mt-4 font-body">
            Razor-sharp point clouds + high-contrast volumetric mesh overlays. Moisture boundaries pulse Neon
            Orange against a Metallic Nickel substrate, with Electric Teal vector edges mathematically locked to
            the exact square inch — the same geometry the Quant™ engine uses to lock every Xactimate line-item.
          </p>
          {demo?.validation && (
            <div className="mt-6 max-w-2xl">
              <ValidationReport validation={demo.validation} />
            </div>
          )}
          <div className="grid md:grid-cols-4 gap-4 mt-8">
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Cloud size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Cloud Rendering</span></div><p className="text-silver font-heading">Real-time photogrammetry stitch</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Activity size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Thermal Map</span></div><p className="text-silver font-heading">Radiometric anomaly overlay</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Cpu size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Multi-Agent Core</span></div><p className="text-silver font-heading">4 narrow AI specialists</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Box size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Xactimate Bridge</span></div><p className="text-silver font-heading">Supplement-ready billing tags</p></HudCard>
          </div>
        </div>
      </section>

      {/* SWITCHBOARD — full grid */}
      <section className="px-6 md:px-12 py-16 md:py-24" id="switchboard">
        <div className="max-w-[1500px] mx-auto">
          <div className="text-center mb-10">
            <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-4">// MASTER PORTAL SWITCHBOARD · ALL OPERATIONAL PLANES</div>
            <h2 className="font-display text-[1.5rem] sm:text-3xl md:text-5xl uppercase tracking-[0.04em] sm:tracking-[0.1em] text-silver leading-tight">
              Choose Your <span className="text-teal glow-teal">Command Plane</span>
            </h2>
            <p className="mt-4 max-w-2xl mx-auto text-muted-hud font-body">
              Five operational modules. Zero friction. Upload any drone payload to receive a forensic
              CAD/BIM report — squares, valleys, gables, layered digital twin, BOM, labor — under 90 seconds.
            </p>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
            {PORTAL_TILES.map((t) => <PortalTile key={t.id} tile={t}/>)}
          </div>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#00F0FF]/15 px-6 py-6 mt-8">
        <div className="max-w-[1500px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] font-mono uppercase tracking-widest text-muted-hud">
          <span>STRATEX™ 2026 • Strategic Thermal Reconnaissance</span>
          <span className="text-teal">v3.7.0 • LUXURY-CORPORATE BUILD</span>
        </div>
      </footer>
    </div>
  );
}
