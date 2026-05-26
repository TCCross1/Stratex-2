import React, { useEffect, useRef, useState } from "react";
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { Crosshair, Search } from "lucide-react";

// Custom STRATEX cyber-teal pin marker (no asset shim needed)
const STRATEX_ICON = L.divIcon({
  className: "stratex-leaflet-pin",
  html: `
    <div style="position:relative;width:28px;height:36px;transform:translate(-14px,-32px);">
      <div style="position:absolute;inset:0;filter:drop-shadow(0 0 6px #00F0FF);">
        <svg viewBox="0 0 28 36" width="28" height="36" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 0 C5.5 0 0 6.7 0 14.5 C0 25 14 36 14 36 C14 36 28 25 28 14.5 C28 6.7 22.5 0 14 0 Z" fill="#06080B" stroke="#00F0FF" stroke-width="1.5"/>
          <circle cx="14" cy="14" r="4.5" fill="#00F0FF"/>
        </svg>
      </div>
    </div>`,
  iconSize: [28, 36],
  iconAnchor: [14, 32],
});

function ClickHandler({ onPick }) {
  useMapEvents({ click: (e) => onPick(e.latlng.lat, e.latlng.lng) });
  return null;
}

function Recenter({ lat, lng }) {
  const map = useMap();
  useEffect(() => {
    if (Number.isFinite(lat) && Number.isFinite(lng)) {
      map.setView([lat, lng], Math.max(map.getZoom(), 17));
    }
  }, [lat, lng, map]);
  return null;
}

/**
 * MapPicker — interactive Leaflet (OpenStreetMap) map for contractor job dispatch.
 * - Click anywhere on the map → drops a pin and emits (lat, lon, address?)
 * - Search box uses Nominatim (OSM) public geocoder; no key required.
 */
export default function MapPicker({ lat, lon, address, onChange }) {
  const [q, setQ] = useState(address || "");
  const [busy, setBusy] = useState(false);
  const debounceRef = useRef(null);

  useEffect(() => { setQ(address || ""); }, [address]);

  const geocode = async (text) => {
    if (!text || text.trim().length < 3) return;
    setBusy(true);
    try {
      const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&q=${encodeURIComponent(text)}`;
      const r = await fetch(url, { headers: { "Accept": "application/json" } });
      const arr = await r.json();
      if (arr && arr[0]) {
        const { lat: la, lon: lo, display_name } = arr[0];
        onChange({ lat: parseFloat(la), lon: parseFloat(lo), address: display_name });
      }
    } catch (e) { /* ignore network errors */ }
    finally { setBusy(false); }
  };

  const reverse = async (la, lo) => {
    try {
      const url = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${la}&lon=${lo}`;
      const r = await fetch(url, { headers: { "Accept": "application/json" } });
      const d = await r.json();
      const addr = d?.display_name || `${la.toFixed(5)}, ${lo.toFixed(5)}`;
      onChange({ lat: la, lon: lo, address: addr });
    } catch {
      onChange({ lat: la, lon: lo, address: `${la.toFixed(5)}, ${lo.toFixed(5)}` });
    }
  };

  const onSearchChange = (val) => {
    setQ(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => geocode(val), 700);
  };

  const center = [Number.isFinite(lat) ? lat : 38.0406, Number.isFinite(lon) ? lon : -84.5037];

  return (
    <div data-testid="map-picker" className="space-y-2">
      <div className="relative">
        <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-teal pointer-events-none"/>
        <input
          data-testid="map-search"
          className="hud-input pl-9"
          placeholder="Search property address (OSM Nominatim)…"
          value={q}
          onChange={(e)=>onSearchChange(e.target.value)}
          onKeyDown={(e)=>{ if (e.key === "Enter") { e.preventDefault(); geocode(q); } }}
        />
        {busy && <span className="absolute right-3 top-1/2 -translate-y-1/2 font-mono text-[10px] text-teal uppercase tracking-widest">…locating</span>}
      </div>
      <div className="relative border border-[#00F0FF]/35 overflow-hidden" style={{ height: 360 }}>
        <span className="corner-bl"/><span className="corner-br"/>
        <MapContainer
          center={center}
          zoom={17}
          style={{ height: "100%", width: "100%", background: "#06080B" }}
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          {Number.isFinite(lat) && Number.isFinite(lon) && (
            <Marker position={[lat, lon]} icon={STRATEX_ICON}/>
          )}
          <ClickHandler onPick={reverse}/>
          <Recenter lat={lat} lng={lon}/>
        </MapContainer>
        <div className="absolute bottom-2 left-2 z-[400] bg-[#06080B]/85 border border-[#00F0FF]/40 px-2 py-1 font-mono text-[10px] uppercase tracking-widest text-teal flex items-center gap-1 pointer-events-none">
          <Crosshair size={10}/> CLICK MAP TO DROP DISPATCH PIN
        </div>
      </div>
      <div className="grid grid-cols-2 gap-3 font-mono text-[11px]">
        <div className="text-muted-hud">LAT: <span className="text-teal" data-testid="map-lat-readout">{Number.isFinite(lat) ? lat.toFixed(5) : "—"}</span></div>
        <div className="text-muted-hud">LON: <span className="text-teal" data-testid="map-lon-readout">{Number.isFinite(lon) ? lon.toFixed(5) : "—"}</span></div>
      </div>
    </div>
  );
}
