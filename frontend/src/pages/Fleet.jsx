import React from "react";
import { HudCard, DataReadout, SectionTitle } from "@/components/HudCard";
import { ASSETS } from "@/lib/constants";
import { Truck, Sun, Battery, Satellite, Radio, Cpu } from "lucide-react";

const Specs = [
  { label: "Trailer", value: "5×8 Carry-On Enclosed", icon: Truck },
  { label: "Drone", value: "DJI Dock 2 + Matrice 3TD", icon: Cpu },
  { label: "Solar", value: "400W Monocrystalline Array", icon: Sun },
  { label: "Battery", value: "12V 200Ah LiFePO4", icon: Battery },
  { label: "Comms", value: "Starlink Mini High-Gain", icon: Satellite },
  { label: "Relay", value: "Raspberry Pi 4 + IoT Cellular", icon: Radio },
];

export default function Fleet() {
  return (
    <div data-testid="fleet-page" className="px-6 md:px-12 py-10 max-w-[1500px] mx-auto">
      <SectionTitle eyebrow="// COMMAND RIG SPECIFICATIONS" title="Autonomous Trailer Fleet"/>
      <div className="grid lg:grid-cols-[1.05fr_1fr] gap-8">
        <HudCard scanline className="p-3"><img src={ASSETS.trailer_engineering} alt="Trailer" className="w-full"/></HudCard>
        <div className="space-y-4">
          {Specs.map((s, i)=>(
            <div key={i} data-testid={`fleet-spec-${i}`} className="hud-card p-4 flex items-center gap-4">
              <span className="corner-bl"/><span className="corner-br"/>
              <div className="w-10 h-10 border border-[#00F0FF]/40 flex items-center justify-center text-teal"><s.icon size={18} strokeWidth={1.5}/></div>
              <div>
                <div className="font-mono text-[10px] uppercase tracking-widest text-muted-hud">{s.label}</div>
                <div className="font-heading text-lg text-silver tracking-wide">{s.value}</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-10 grid md:grid-cols-4 gap-4">
        <DataReadout label="CapEx per rig" value="$26,500.50" accent="orange" testid="fleet-capex"/>
        <DataReadout label="Standby Power" value="48 HRS" accent="volt" testid="fleet-standby"/>
        <DataReadout label="Actuator Stroke" value="12 IN" testid="fleet-stroke"/>
        <DataReadout label="Hatch Cycle" value="< 7 SEC" testid="fleet-cycle"/>
      </div>
    </div>
  );
}
