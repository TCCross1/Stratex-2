import React from "react";
import { Link } from "react-router-dom";
import { ASSETS } from "@/lib/constants";
import { HudCard, DataReadout, SectionTitle } from "@/components/HudCard";
import RoofModel3D from "@/components/RoofModel3D";
import { Crosshair, Cpu, Activity, Radar, ArrowRight, Shield, Zap, Cloud, Satellite, Sun, Box } from "lucide-react";

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
  return (
    <div data-testid="landing-page">
      {/* HERO */}
      <section className="relative px-6 md:px-12 pt-16 pb-24 overflow-hidden">
        <div className="absolute inset-0 grid-floor opacity-30 pointer-events-none" />
        <div className="max-w-[1500px] mx-auto grid lg:grid-cols-[1.05fr_1fr] gap-12 items-center relative">
          <div>
            <div className="flex items-center gap-3 mb-6">
              <span className="led led-teal" />
              <span className="font-mono text-[11px] tracking-[0.32em] text-teal uppercase">SYSTEM ONLINE • RECON GRID v1.0.0</span>
            </div>
            <h1 className="font-display text-5xl md:text-6xl lg:text-7xl uppercase tracking-[0.06em] leading-[0.95] text-silver">
              <span className="block">STRATEGIC</span>
              <span className="block">THERMAL</span>
              <span className="block text-teal glow-teal">RECONNAISSANCE</span>
            </h1>
            <p className="mt-6 max-w-xl text-base md:text-lg text-muted-hud font-body leading-relaxed">
              STRATEX™ is the world's first autonomous, solar-powered roofing recon platform — pairing radiometric thermal mapping with a multi-agent actuarial engine to deliver insurance-grade estimates without a human ever climbing a ladder.
            </p>
            <div className="mt-10 flex flex-wrap gap-4">
              <Link to="/mission/new" data-testid="hero-launch-cta" className="btn-hud pulse-glow">
                <Radar size={16} /> Launch Fleet Command
              </Link>
              <Link to="/projects" data-testid="hero-projects-cta" className="btn-hud btn-hud-ghost">
                <Box size={16} /> Project Ledger
              </Link>
            </div>
            <div className="mt-12 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-2xl">
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
                <span className="font-mono text-[11px] text-muted-hud tracking-widest uppercase">Cyber-Shield Theme</span>
                <div className="flex gap-2 mt-2">
                  <span className="w-6 h-6 bg-[#00F0FF]" />
                  <span className="w-6 h-6 bg-[#39FF14]" />
                  <span className="w-6 h-6 bg-[#FF5500]" />
                  <span className="w-6 h-6 bg-[#10141D] border border-[#00F0FF]/30" />
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
              blurb="Subsurface radiometric moisture mapping. Detects wet decking, hidden rot, and adhesion failures invisible to RGB capture."
              testid="pillar-thermal" />
            <Pillar tag="MODULE 03" accent="teal" icon={Cpu} title="STRATEX Quant™"
              blurb="Multi-agent actuarial estimating engine. Auto-maps every line-item to Xactimate tags under a locked 20/25 O&P envelope."
              testid="pillar-quant" />
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
          <SectionTitle eyebrow="// SPATIAL MODEL LIVE" title="STRATEX Vision™ — Photogrammetry Mesh"/>
          <HudCard scanline className="p-2">
            <RoofModel3D
              telemetry={{
                style: "cross_hip",
                scale: 1.0,
                facets: [
                  {id:"A1", vertices:[[-23,0,-13],[23,0,-13],[12,7.5,0],[-12,7.5,0]], normal:[0,0.83,-0.55], area_planar_sf:600, area_true_sf:660, pitch:8, color_tag:"#FF8A60"},
                  {id:"A2", vertices:[[23,0,-13],[23,0,13],[12,7.5,0]], normal:[0.83,0.55,0], area_planar_sf:170, area_true_sf:200, pitch:8, color_tag:"#FFB87A"},
                  {id:"A3", vertices:[[23,0,13],[-23,0,13],[-12,7.5,0],[12,7.5,0]], normal:[0,0.83,0.55], area_planar_sf:600, area_true_sf:660, pitch:8, color_tag:"#7BB7C6"},
                  {id:"A4", vertices:[[-23,0,13],[-23,0,-13],[-12,7.5,0]], normal:[-0.83,0.55,0], area_planar_sf:170, area_true_sf:200, pitch:8, color_tag:"#6FA3B5"},
                ],
                edges: [
                  {a:[-23,0,-13],b:[23,0,-13],length_ft:46,classification:"eave"},
                  {a:[23,0,-13],b:[23,0,13],length_ft:26,classification:"eave"},
                  {a:[23,0,13],b:[-23,0,13],length_ft:46,classification:"eave"},
                  {a:[-23,0,13],b:[-23,0,-13],length_ft:26,classification:"eave"},
                  {a:[-23,0,-13],b:[-12,7.5,0],length_ft:18,classification:"hip"},
                  {a:[23,0,-13],b:[12,7.5,0],length_ft:18,classification:"hip"},
                  {a:[23,0,13],b:[12,7.5,0],length_ft:18,classification:"hip"},
                  {a:[-23,0,13],b:[-12,7.5,0],length_ft:18,classification:"hip"},
                  {a:[-12,7.5,0],b:[12,7.5,0],length_ft:24,classification:"ridge"},
                ],
              }}
              anomalies={[
                {id:"AD-KY041-001", diagnosis:"Trapped Moisture", facet_id:"A1", severity:"CRITICAL", thermal_delta:"+7.2°F", confidence:0.92, area_affected_sf:96, lat:38.0406, lon:-84.5037},
                {id:"AD-KY041-002", diagnosis:"CDX Deck Rot", facet_id:"A3", severity:"HIGH", thermal_delta:"+9.6°F", confidence:0.94, area_affected_sf:140, lat:38.0406, lon:-84.5037},
              ]}
              height={560}
              showLabels
            />
          </HudCard>
          <p className="text-sm text-muted-hud max-w-2xl mt-4 font-body">
            Every Quant™ calculation is locked to the geometry of this mesh. Drag to orbit, scroll to zoom — anomalies pulse plasma orange on the exact roof facet where the drone detected them.
          </p>
          <div className="grid md:grid-cols-4 gap-4 mt-8">
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Cloud size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Cloud Rendering</span></div><p className="text-silver font-heading">Real-time photogrammetry stitch</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Activity size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Thermal Map</span></div><p className="text-silver font-heading">Radiometric anomaly overlay</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Cpu size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Multi-Agent Core</span></div><p className="text-silver font-heading">4 narrow AI specialists</p></HudCard>
            <HudCard className="p-4"><div className="flex items-center gap-2 mb-2 text-muted-hud"><Box size={14}/><span className="font-mono text-[10px] tracking-widest uppercase">Xactimate Bridge</span></div><p className="text-silver font-heading">Supplement-ready billing tags</p></HudCard>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="px-6 md:px-12 py-24">
        <div className="max-w-[1500px] mx-auto">
          <HudCard scanline className="p-10 md:p-16 text-center">
            <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-4">// AUTHORIZE AERIAL RECONNAISSANCE</div>
            <h2 className="font-display text-3xl md:text-5xl uppercase tracking-[0.1em] text-silver leading-tight">
              Deploy your first <span className="text-teal glow-teal">autonomous</span> mission
            </h2>
            <p className="mt-4 max-w-2xl mx-auto text-muted-hud font-body">
              Configure intake, run a caliper analysis, lock your pricing under 20/25 O&P, and authorize launch — all in under 5 minutes.
            </p>
            <div className="mt-8 flex justify-center">
              <Link to="/mission/new" data-testid="cta-new-mission" className="btn-hud pulse-glow">
                <ArrowRight size={16}/> Initiate Mission
              </Link>
            </div>
          </HudCard>
        </div>
      </section>

      {/* FOOTER */}
      <footer className="border-t border-[#00F0FF]/15 px-6 py-6 mt-8">
        <div className="max-w-[1500px] mx-auto flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] font-mono uppercase tracking-widest text-muted-hud">
          <span>STRATEX™ 2026 • All Telemetry Locked</span>
          <span className="text-teal">v1.0.0 • CYBER-SHIELD BUILD</span>
        </div>
      </footer>
    </div>
  );
}
