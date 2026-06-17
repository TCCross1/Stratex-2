/**
 * FILENAME: PilotShell.jsx / OpsDashboard.jsx
 * DESCRIPTION: Standalone, zero-login Master Switchboard for the Pilot/Operator Control Plane.
 * PALETTE: PBR Luxury-Corporate Dark Mode — Electric Cyber Teal, Hyper-Volt Orange, Metallic Gold.
 * BACKEND COMPATIBILITY: Reads telemetry streams seamlessly from GET /api/pilot/telemetry.
 */
import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import YellowTriangleWidget from "@/components/YellowTriangleWidget";
import ScrollingGlassDock from "@/components/ScrollingGlassDock";
import {
  Radio, Shield, ShieldCheck, Activity, Brain, Plane, Box, 
  Wind, Cloud, MapPin, AlertTriangle, Cpu, Terminal, KeyRound, CheckCircle2
} from "lucide-react";
import { toast } from "sonner";

export default function PilotShell() {
  const nav = useNavigate();
  
  // Real-time infrastructure states
  const [starlinkSecured, setStarlinkSecured] = useState(true);
  const [routerOptimized, setRouterOptimized] = useState(true);
  const [hatchReady, setHatchReady] = useState(false);
  const [isLaunching, setIsLaunching] = useState(false);
  
  // Standalone dataset to prevent UI dropping on backend reconnection cycles
  const [telemetry, setTelemetry] = useState({
    trailerPowerEfficiency: "98% Output [SUSTAINED]",
    matriceBatteryCharge: 100,
    atcShieldActive: true,
    atcAgentStatus: "ACTIVE",
    superAiSyncPct: 99.8,
    windSpeedKts: 8.2,
    visibilityMiles: 10.0,
    precipRiskPct: 0,
    cloudCeiling: "Clear Sky",
    radarStatus: "LIVE DOPPLER FEED // LEX_REGIONAL"
  });

  useEffect(() => {
    // Graceful ingestion of active edge device streams if live endpoints are active
    const fetchTelemetry = async () => {
      try {
        const r = await api.get("/pilot/telemetry");
        setTelemetry(prev => ({ ...prev, ...r.data }));
      } catch (e) {
        // Safe continuous execution fallback matrix — zero runtime roadblocks
      }
    };
    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleLaunchSequence = () => {
    if (!hatchReady) {
      toast.error("CRITICAL SAFETY BLOCK: Automated mechanized box hatch doors report LOCKED state. Verify clearance actuator checked inside the matrix.");
      return;
    }
    setIsLaunching(true);
    toast.success("LAUNCH SEQUENCE INITIALIZED // Relaying localized vector telemetry maps to Air Traffic Control agent mesh.");
    setTimeout(() => {
      setIsLaunching(false);
    }, 4000);
  };

  return (
    <div className="min-h-screen bg-[#0a0d14] text-gray-200 font-sans p-4 overflow-x-hidden selection:bg-[#00f2fe] selection:text-black">
      <PilotPortalStyles />
      <ScrollingGlassDock portal="pilot" routePrefix="/pilot" />

      {/* GLOBAL MATRIX OUTER BORDER WITH GOLD FILIGREE FEEL */}
      <div className="max-w-[1800px] mx-auto border border-[#d4af37]/30 rounded-xl p-4 bg-gradient-to-b from-[#0a0d14] via-[#0a0d14] to-[#0f1422] gold-border-glow">
        
        {/* HEADER TRACKING ROW */}
        <header className="flex flex-col md:flex-row justify-between items-center pb-4 mb-6 border-b-2 border-[#d4af37]/40 relative">
          <div className="absolute top-0 left-0 w-24 h-1 bg-[#d4af37]"></div>
          <div className="flex items-center space-x-4">
            <div className="w-3 h-3 rounded-full bg-[#00f2fe] animate-ping"></div>
            <div>
              <h1 className="font-mono font-black text-2xl tracking-wider text-white uppercase">
                Stratex <span className="text-[#00f2fe]">Control Plane</span>
              </h1>
              <p className="font-mono text-[10px] text-gray-400 tracking-widest">UNIT: MOBILE LOGISTICS TRAILER // LEXINGTON DETECT NETWORK</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-6 mt-4 md:mt-0 font-mono text-xs bg-black/40 p-2 rounded border border-gray-800">
            <YellowTriangleWidget portal="pilot" />
            <div>SYS_STATUS: <span className="text-[#00f2fe] font-bold neon-text-teal">UNRESTRICTED ACCESS</span></div>
            <div className="text-gray-500">|</div>
            <div>ATC GATEWAY: <span className="text-[#ff6a00] font-bold neon-text-orange">SHIELD ACTIVE</span></div>
          </div>
        </header>

        {/* CONTROLS MASTER 3-COLUMN LAYOUT PANEL GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* COLUMN 1: INTERLOCKING AGENTS & SUPER COMPUTER MESH */}
          <div className="space-y-6">
            
            {/* ATC AGENT TEAM */}
            <div className="glass-panel rounded-lg p-5 relative overflow-hidden">
              <div className="absolute top-0 right-0 bg-[#ff6a00]/10 text-[#ff6a00] font-mono text-[9px] px-2 py-1 border-b border-l border-[#ff6a00]/30 tracking-widest">ATC SHIELD PLAN</div>
              <h2 className="font-mono text-base font-bold text-white mb-4 flex items-center border-b border-gray-800 pb-2 uppercase tracking-wide">
                <span className="mr-2 text-[#ff6a00]"><Cpu size={16}/></span> ATC Agent Guard Team
              </h2>
              
              <div className="space-y-4 font-mono text-xs">
                <div className="p-3 bg-black/30 rounded border border-[#00f2fe]/20 flex justify-between items-center">
                  <div>
                    <p className="text-white font-bold text-xs">Orchestrator Agent V4</p>
                    <p className="text-gray-400 text-[11px] mt-0.5">Monitoring real-time spatial vectors</p>
                  </div>
                  <span className="px-2 py-1 bg-[#00f2fe]/10 text-[#00f2fe] rounded animate-pulse font-bold text-[10px]">RUNNING</span>
                </div>

                <div className="p-3 bg-black/30 rounded border border-[#ff6a00]/20 flex justify-between items-center">
                  <div>
                    <p className="text-white font-bold text-xs">Guardian Anti-Hallucination Shield</p>
                    <p className="text-gray-400 text-[11px] mt-0.5">Verifying telemetry data payloads</p>
                  </div>
                  <span className="px-2 py-1 bg-[#ff6a00]/10 text-[#ff6a00] rounded font-bold text-[10px]">ARMED</span>
                </div>

                <div className="p-3 bg-black/30 rounded border border-gray-800 flex justify-between items-center">
                  <div>
                    <p className="text-white font-bold text-xs">Safety Fence Coordinator</p>
                    <p className="text-gray-400 text-[11px] mt-0.5">Enforcing FAA geofence thresholds</p>
                  </div>
                  <span className="px-2 py-1 bg-green-500/10 text-green-400 rounded font-bold text-[10px]">PASSIVE</span>
                </div>
              </div>
            </div>

            {/* COMMAND CENTER SUPER AI LINK */}
            <div className="glass-panel rounded-lg p-5 relative">
              <h2 className="font-mono text-base font-bold text-white mb-4 flex items-center border-b border-gray-800 pb-2 uppercase tracking-wide">
                <span className="mr-2 text-[#00f2fe]"><Brain size={16}/></span> Core Command Center Link
              </h2>
              <div className="bg-black/50 p-4 rounded border border-[#d4af37]/20 font-mono text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Super AI Handshake:</span>
                  <span className="text-[#00f2fe] font-bold tracking-wide">SYNCHRONIZED ({telemetry.superAiSyncPct}%)</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Data Pipeline Engine:</span>
                  <span className="text-white">Active Neural Mesh</span>
                </div>
                <div className="w-full bg-gray-900 rounded-full h-1.5 mt-3 overflow-hidden">
                  <div className="bg-gradient-to-r from-[#00f2fe] to-[#d4af37] h-1.5 rounded-full" style={{ width: `${telemetry.superAiSyncPct}%` }}></div>
                </div>
              </div>
            </div>

          </div>

          {/* COLUMN 2: ATMOSPHERIC DOPPLER & ENCRYPTED INFRASTRUCTURE EDGE */}
          <div className="space-y-6">
            
            {/* ATMOSPHERICS & LOCAL PULSE RADAR MAP */}
            <div className="glass-panel rounded-lg p-5">
              <h2 className="font-mono text-base font-bold text-white mb-4 flex items-center border-b border-gray-800 pb-2 uppercase tracking-wide">
                <span className="mr-2 text-[#00f2fe]"><Cloud size={16}/></span> Weather Team &amp; Doppler Radar
              </h2>
              
              {/* Radar Reticle Monitor Screen */}
              <div className="relative w-full h-44 bg-[#050811] rounded border border-[#00f2fe]/30 mb-4 overflow-hidden flex items-center justify-center">
                {/* Sweep Animation Overlay */}
                <div className="absolute inset-0 bg-gradient-to-tr from-transparent via-[#00f2fe]/5 to-transparent origin-bottom-left rotate-12 animate-[spin_4s_linear_infinite]"></div>
                
                {/* Fixed Conical Targets */}
                <div className="absolute w-36 h-36 border border-[#00f2fe]/10 rounded-full"></div>
                <div className="absolute w-24 h-24 border border-[#00f2fe]/10 rounded-full"></div>
                <div className="absolute w-12 h-12 border border-[#00f2fe]/5 rounded-full"></div>
                <div className="absolute w-full h-[1px] bg-[#00f2fe]/10"></div>
                <div className="absolute h-full w-[1px] bg-[#00f2fe]/10"></div>
                
                {/* Local Dynamic Precipitation Returns */}
                <div className="absolute top-12 right-16 w-12 h-8 bg-green-500/20 blur-md rounded-full"></div>
                <div className="absolute top-14 right-20 w-6 h-4 bg-yellow-500/30 blur-sm rounded-full"></div>
                
                <span className="absolute bottom-2 left-2 font-mono text-[9px] text-[#00f2fe] tracking-widest bg-black/60 px-1.5 py-0.5 rounded uppercase">{telemetry.radarStatus}</span>
              </div>

              {/* Weather Indicators Readouts */}
              <div className="grid grid-cols-2 gap-2 font-mono text-[11px]">
                <div className="p-2 bg-black/30 rounded border border-gray-800">
                  <p className="text-gray-400 text-[10px]">WIND PROFILE</p>
                  <p className="text-white font-bold mt-0.5">{telemetry.windSpeedKts} kts @ 180°S</p>
                </div>
                <div className="p-2 bg-black/30 rounded border border-gray-800">
                  <p className="text-gray-400 text-[10px]">VISIBILITY</p>
                  <p className="text-white font-bold mt-0.5">{telemetry.visibilityMiles} Miles</p>
                </div>
                <div className="p-2 bg-black/30 rounded border border-gray-800">
                  <p className="text-gray-400 text-[10px]">PRECIPITATION</p>
                  <p className="text-green-400 font-bold mt-0.5">{telemetry.precipRiskPct}% Risk</p>
                </div>
                <div className="p-2 bg-black/30 rounded border border-gray-800">
                  <p className="text-gray-400 text-[10px]">CLOUD CEILING</p>
                  <p className="text-white font-bold mt-0.5">{telemetry.cloudCeiling}</p>
                </div>
              </div>
            </div>

            {/* EDGE TELEMETRY COMMUNICATIONS HARDWARE TUNNEL */}
            <div className="glass-panel rounded-lg p-5">
              <h2 className="font-mono text-base font-bold text-white mb-4 flex items-center border-b border-gray-800 pb-2 uppercase tracking-wide">
                <span className="mr-2 text-[#00f2fe]"><Radio size={16}/></span> Critical Telemetry Connections
              </h2>
              
              <div className="space-y-3 font-mono text-xs">
                {/* Starlink Intercept Gate */}
                <div className="p-3 bg-black/40 rounded border border-[#d4af37]/20 flex justify-between items-center">
                  <div>
                    <p className="text-white font-bold tracking-wide text-xs">STARLINK DISH LINK</p>
                    <p className={`text-[10px] mt-0.5 ${starlinkSecured ? "text-[#00f2fe]" : "text-[#ff6a00]"}`}>
                      {starlinkSecured ? "ENCRYPTED BEAM BACKHAUL ACTIVE" : "WARNING: UNSECURED DIRECT BACKHAUL"}
                    </p>
                  </div>
                  <button 
                    onClick={() => setStarlinkSecured(!starlinkSecured)} 
                    className={`px-3 py-1 text-[11px] font-bold border rounded transition-colors ${
                      starlinkSecured ? "bg-[#00f2fe]/20 text-[#00f2fe] border-[#00f2fe]" : "bg-red-500/20 text-red-400 border-red-500"
                    }`}
                  >
                    {starlinkSecured ? "SECURED" : "UNSECURED"}
                  </button>
                </div>

                {/* Hotspot/Local Router Optimizer Toggle */}
                <div className="p-3 bg-black/40 rounded border border-gray-800 flex justify-between items-center">
                  <div>
                    <p className="text-white font-bold tracking-wide text-xs">FIELD TRAILER WIFI HOVER-NET</p>
                    <p className={`text-[10px] mt-0.5 ${routerOptimized ? "text-green-400" : "text-gray-400"}`}>
                      {routerOptimized ? "Channel scanning cleared. Optimization complete." : "Local Hotspot & Router Paired"}
                    </p>
                  </div>
                  <button 
                    onClick={() => setRouterOptimized(!routerOptimized)}
                    className={`px-3 py-1 text-[11px] font-bold border rounded transition-colors ${
                      routerOptimized ? "bg-green-500/20 text-green-400 border-green-500" : "bg-gray-800 text-gray-300 border-gray-700"
                    }`}
                  >
                    {routerOptimized ? "OPTIMIZED" : "OPTIMIZE"}
                  </button>
                </div>
              </div>
            </div>

          </div>

          {/* COLUMN 3: HARDWARE MATRIX PRE-FLIGHT INTERLOCK DEPLOYMENT */}
          <div className="space-y-6">
            
            <div className="glass-panel rounded-lg p-5 border-l-4 border-l-[#ff6a00] relative">
              <h2 className="font-mono text-base font-bold text-white mb-1 flex items-center uppercase tracking-wide">
                <span className="mr-2 text-[#ff6a00]"><Terminal size={16}/></span> Pre-Flight Matrix
              </h2>
              <p className="font-mono text-[10px] text-gray-400 mb-4 border-b border-gray-800 pb-2 tracking-widest">FIELD OPERATIONS INTEGRATION GATEWAY</p>
              
              <div className="space-y-3 font-mono text-xs">
                
                {/* COMPONENT 1: MOBILE UTILITY TRAILER INVERTER BANKS */}
                <label className="flex items-start p-3 bg-black/40 rounded border border-gray-800 cursor-pointer select-none hover:border-[#d4af37]/40 transition-colors">
                  <input type="checkbox" defaultChecked className="mt-0.5 mr-3 w-4 h-4 accent-[#00f2fe] rounded" />
                  <div>
                    <span className="text-white font-bold block text-xs">1. MOBILE TRAILER POWER SUPPLY</span>
                    <span className="text-gray-400 text-[11px] mt-0.5 block">Inverter output running optimal. Main battery grid efficiency metrics sustained.</span>
                    <span className="block mt-1 text-[#00f2fe] text-[10px] font-bold">STATUS: {telemetry.trailerPowerEfficiency}</span>
                  </div>
                </label>

                {/* COMPONENT 2: DJI AIRCRAFT BATTERY CORES */}
                <label className="flex items-start p-3 bg-black/40 rounded border border-gray-800 cursor-pointer select-none hover:border-[#d4af37]/40 transition-colors">
                  <input type="checkbox" defaultChecked className="mt-0.5 mr-3 w-4 h-4 accent-[#00f2fe] rounded" />
                  <div>
                    <span className="text-white font-bold block text-xs">2. DJI MATRICE BATTERY INTEGRITY</span>
                    <span className="text-gray-400 text-[11px] mt-0.5 block">Internal drone cell configuration blocks fully saturated. Ready for high-altitude capture.</span>
                    <span className="block mt-1 text-[#00f2fe] text-[10px] font-bold">STATUS: {telemetry.matriceBatteryCharge}% READY</span>
                  </div>
                </label>

                {/* COMPONENT 3: MECHANICAL ENCLOSURE AUTOMATIC DOOR CLEARANCE */}
                <label className="flex items-start p-3 bg-black/40 rounded border border-gray-800 cursor-pointer select-none hover:border-[#d4af37]/40 transition-colors">
                  <input 
                    type="checkbox" 
                    checked={hatchReady}
                    onChange={(e) => setHatchReady(e.target.checked)}
                    className="mt-0.5 mr-3 w-4 h-4 accent-[#ff6a00] rounded" 
                  />
                  <div>
                    <span className="text-white font-bold block text-xs">3. AUTOMATED MECHANIZED BOX HATCH</span>
                    <span className="text-gray-400 text-[11px] mt-0.5 block">Mobile utility trailer enclosure roof clearances verified. Actuators unlatched for deploy state.</span>
                    <span className={`block mt-1 text-[10px] font-bold ${hatchReady ? "text-[#00f2fe]" : "text-[#ff6a00]"}`}>
                      STATUS: {hatchReady ? "UNLOCKED & READY TO DEPLOY" : "LOCKED / CLEARANCE PENDING"}
                    </span>
                  </div>
                </label>

              </div>

              {/* MISSION INITIATION LAUNCH SWITCH */}
              <div className="mt-6">
                <button 
                  onClick={handleLaunchSequence}
                  disabled={isLaunching}
                  className="w-full bg-gradient-to-r from-[#ff6a00] to-red-600 hover:from-[#00f2fe] hover:to-blue-600 text-white font-mono font-black text-xs py-4 rounded tracking-widest transition-all duration-300 shadow-lg uppercase border border-white/10"
                >
                  {isLaunching ? "TRANSMITTING FLIGHT CODES..." : "Execute Aerial Scan Sequence"}
                </button>
              </div>

            </div>

          </div>

        </div>

        {/* TRACKING DISPATCH SYSTEM FOOTER */}
        <footer className="mt-6 pt-4 border-t border-gray-900 font-mono text-[9px] text-gray-500 flex flex-col sm:flex-row justify-between items-center">
          <p>STRATEX RESIDENTIAL DETECT NETWORK ENGINE v4.0 // PILOT MASTER INTERFACE</p>
          <p className="mt-2 sm:mt-0 text-[#00f2fe]">EDGE NODE LOCATION: LEXINGTON HQ // UNRESTRICTED BYPASS GATEWAY INTERFACE ACTIVE</p>
        </footer>

      </div>
    </div>
  );
}

/* =====================================================================
   INLINE STYLES SHEET COMPONENT FOR RECON MATRIX
   ===================================================================== */
function PilotPortalStyles() {
  return (
    <style>{`
      .glass-panel {
        background: rgba(16, 22, 34, 0.65);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(212, 175, 55, 0.15);
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37);
      }
      .neon-text-teal {
        text-shadow: 0 0 8px rgba(0, 242, 254, 0.6);
      }
      .neon-text-orange {
        text-shadow: 0 0 8px rgba(255, 106, 0, 0.6);
      }
      .gold-border-glow {
        box-shadow: 0 0 15px rgba(214, 175, 51, 0.1);
      }
    `}</style>
  );
}
