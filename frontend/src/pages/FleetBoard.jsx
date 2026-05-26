import React, { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { HudCard, DataReadout } from "@/components/HudCard";
import { fleetStatus } from "@/lib/api";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Truck, Battery, Satellite, Wrench, Radio, MapPin, Activity, Zap } from "lucide-react";

const STATUS_META = {
  STANDBY:     { color: "#39FF14", label: "Standby",     dot: "led-ok" },
  CHARGING:    { color: "#00F0FF", label: "Charging",    dot: "led-teal pulse-glow" },
  DEPLOYED:    { color: "#FF5500", label: "Deployed",    dot: "led-alert pulse-alert" },
  IN_FLIGHT:   { color: "#FF5500", label: "In Flight",   dot: "led-alert pulse-alert" },
  MAINTENANCE: { color: "#94A3B8", label: "Maintenance", dot: "" },
};

function rigIcon(status) {
  const c = STATUS_META[status]?.color || "#00F0FF";
  return L.divIcon({
    className: "stratex-rig-pin",
    html: `<div style="filter:drop-shadow(0 0 8px ${c});transform:translate(-12px,-12px);">
      <svg width="24" height="24" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <rect x="2" y="2" width="20" height="20" fill="#06080B" stroke="${c}" stroke-width="1.5"/>
        <circle cx="12" cy="12" r="4" fill="${c}"/>
      </svg></div>`,
    iconSize: [24, 24], iconAnchor: [12, 12],
  });
}

export default function FleetBoard() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const load = () => fleetStatus().then(setData).catch(()=>{});
    load();
    const id = setInterval(() => { load(); setTick((t)=>t+1); }, 6000);
    return () => clearInterval(id);
  }, []);

  if (!data) return <div className="p-10 text-muted-hud font-mono">Acquiring fleet uplink…</div>;
  const { rigs, totals, as_of } = data;
  const center = [38.5, -86.5];

  return (
    <div data-testid="fleet-board" className="px-4 md:px-10 py-6 max-w-[1700px] mx-auto">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div>
          <div className="font-mono text-[10px] tracking-[0.32em] text-teal uppercase">// LIVE FLEET TELEMETRY</div>
          <h1 className="font-display text-2xl md:text-4xl uppercase tracking-[0.06em] md:tracking-[0.14em] text-silver">Fleet Command</h1>
        </div>
        <div className="flex items-center gap-3 font-mono text-[10px] uppercase tracking-widest">
          <span className="led led-ok pulse-glow"/>
          <span className="text-volt">{user?.role === "operator" ? "OPERATOR VIEW" : "CONTRACTOR VIEW"}</span>
          <span className="text-muted-hud">• polled every 6s • tick {tick}</span>
        </div>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3 mb-4">
        <DataReadout label="Total Rigs"  value={totals.total_rigs}  testid="fleet-total"/>
        <DataReadout label="Deployed"    value={totals.deployed}    accent="orange" testid="fleet-deployed"/>
        <DataReadout label="Standby"     value={totals.standby}     accent="volt"/>
        <DataReadout label="Charging"    value={totals.charging}/>
        <DataReadout label="Maintenance" value={totals.maintenance}/>
        <DataReadout label="Avg Battery" value={`${totals.avg_battery_pct}%`} accent={totals.avg_battery_pct>70?"volt":"orange"}/>
      </div>

      <div className="grid lg:grid-cols-[1.5fr_1fr] gap-4">
        {/* MAP */}
        <HudCard scanline className="p-2 overflow-hidden">
          <div className="font-mono text-[10px] uppercase tracking-widest text-teal px-2 py-1 flex items-center gap-2"><Satellite size={11}/> CONTINENTAL DISPATCH GRID</div>
          <div className="relative border border-[#00F0FF]/30 overflow-hidden" style={{ height: 540 }}>
            <span className="corner-bl"/><span className="corner-br"/>
            <MapContainer center={center} zoom={5} style={{ height: "100%", width: "100%", background: "#06080B" }} scrollWheelZoom>
              <TileLayer attribution='Imagery &copy; Esri' url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}" maxZoom={19}/>
              {rigs.map((r) => (
                <Marker key={r.id} position={[r.lat, r.lon]} icon={rigIcon(r.status)}>
                  <Popup>
                    <div style={{fontFamily:"monospace",fontSize:11,color:"#06080B"}}>
                      <strong>{r.id} • {r.callsign}</strong><br/>
                      Status: {STATUS_META[r.status]?.label || r.status}<br/>
                      Battery: {r.battery_pct}%<br/>
                      Uplink: {r.uplink}<br/>
                      {r.active_job_address && <>Job: {r.active_job_address}<br/></>}
                    </div>
                  </Popup>
                </Marker>
              ))}
            </MapContainer>
            <div className="absolute top-2 left-2 z-[400] flex flex-wrap gap-1 text-[10px] font-mono uppercase tracking-widest">
              {Object.entries(STATUS_META).map(([k, m]) => (
                <span key={k} className="bg-[#06080B]/85 border border-[#00F0FF]/25 px-2 py-1 flex items-center gap-1" style={{color: m.color}}>
                  <span className="w-2 h-2 inline-block" style={{background: m.color, boxShadow: `0 0 6px ${m.color}`}}/> {m.label}
                </span>
              ))}
            </div>
          </div>
        </HudCard>

        {/* RIG ROSTER */}
        <div className="space-y-2 max-h-[600px] overflow-auto pr-1">
          {rigs.map((r) => {
            const meta = STATUS_META[r.status] || {};
            return (
              <div key={r.id} className="hud-card p-3" data-testid={`rig-${r.id}`}>
                <span className="corner-bl"/><span className="corner-br"/>
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <div className="font-mono text-[10px] text-muted-hud">{r.id}</div>
                    <div className="font-display text-silver text-sm tracking-widest uppercase">{r.callsign}</div>
                  </div>
                  <div className="flex items-center gap-2 font-mono text-[10px] uppercase tracking-widest">
                    <span className={`led ${meta.dot}`} style={{background: meta.color, boxShadow:`0 0 8px ${meta.color}`}}/>
                    <span style={{color: meta.color}}>{meta.label}</span>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-1 font-mono text-[11px]">
                  <Stat icon={<MapPin size={11}/>} label="Base" value={r.base}/>
                  <Stat icon={<Battery size={11}/>} label="Battery" value={`${r.battery_pct}%`} accent={r.battery_pct>70?"volt":r.battery_pct>40?"teal":"orange"}/>
                  <Stat icon={<Radio size={11}/>} label="Uplink" value={r.uplink}/>
                  <Stat icon={<Activity size={11}/>} label="RTK" value={`${r.rtk_signal_cm}cm`}/>
                  <Stat icon={<Zap size={11}/>} label="Today" value={r.missions_today}/>
                  <Stat icon={<Wrench size={11}/>} label="Heartbeat" value="LIVE" accent="volt"/>
                </div>
                {r.active_job_address && (
                  <div className="mt-2 font-mono text-[10px] text-plasma uppercase tracking-widest border-t border-[#FF5500]/30 pt-1">
                    ACTIVE → {r.active_job_address}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <div className="text-right text-[10px] font-mono text-muted-hud uppercase tracking-widest mt-3">as of {as_of}</div>
    </div>
  );
}

function Stat({ icon, label, value, accent }) {
  const c = accent==="orange"?"text-plasma":accent==="volt"?"text-volt":"text-teal";
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <span className="text-muted-hud">{icon}</span>
      <span className="text-muted-hud uppercase tracking-widest text-[9px]">{label}:</span>
      <span className={`${c} truncate`}>{value}</span>
    </div>
  );
}
