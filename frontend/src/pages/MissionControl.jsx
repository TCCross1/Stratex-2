// STRATEX™ — Mission Control
//
// Single-screen cockpit that unifies the three operational systems:
//   1. Pre-Flight ATC  — live Open-Meteo verdict + Doppler radar tile
//   2. Connected Calendar — shared events feed (read + write)
//   3. Fleet & Jobs Map — real Leaflet map with MDU rigs + job pins
//
// All three panels poll real backend endpoints. No mocked data.

import React, { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { StratexLogo } from "@/components/StratexBrand";
import {
  ArrowLeft, Plane, ShieldCheck, ShieldAlert, ShieldQuestion, Wind, Droplets,
  Eye, CloudSun, Thermometer, Plus, X, Calendar as CalIcon, Loader2,
  Truck, Crosshair, MapPin, RefreshCw,
} from "lucide-react";

const ACCENTS = {
  cyan: "#00E5FF", amber: "#FFB020", green: "#00FF9C",
  magenta: "#FF2D78", gold: "#D4B86A", volt: "#A6FF00",
};

const LEXINGTON = { lat: 38.0406, lon: -84.5037 };

// ─────────────────────────────────────────────────────────────────
// Leaflet (loaded from CDN to avoid yarn install during demo)
// ─────────────────────────────────────────────────────────────────
function useLeaflet() {
  const [ready, setReady] = useState(typeof window !== "undefined" && !!window.L);
  useEffect(() => {
    if (typeof window === "undefined" || window.L) { setReady(true); return; }
    // CSS
    if (!document.getElementById("leaflet-css")) {
      const link = document.createElement("link");
      link.id = "leaflet-css";
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }
    // JS
    if (!document.getElementById("leaflet-js")) {
      const s = document.createElement("script");
      s.id = "leaflet-js";
      s.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      s.async = true;
      s.onload = () => setReady(true);
      document.body.appendChild(s);
    } else {
      setReady(true);
    }
  }, []);
  return ready;
}

// ─────────────────────────────────────────────────────────────────
// Pre-Flight ATC panel
// ─────────────────────────────────────────────────────────────────
function PreflightAtcPanel({ coords, refreshKey }) {
  const API = process.env.REACT_APP_BACKEND_URL;
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let dead = false;
    setLoading(true);
    fetch(`${API}/api/atc/preflight?lat=${coords.lat}&lon=${coords.lon}`)
      .then((r) => r.json())
      .then((j) => { if (!dead) { setData(j); setLoading(false); } })
      .catch(() => { if (!dead) setLoading(false); });
    return () => { dead = true; };
  }, [API, coords.lat, coords.lon, refreshKey]);

  if (loading || !data) {
    return (
      <div className="rounded-xl p-6 grid place-items-center min-h-[260px]"
           style={{ background: "rgba(8,14,24,0.86)", border: `1px solid ${ACCENTS.cyan}55` }}>
        <Loader2 size={26} className="animate-spin text-cyan-400"/>
      </div>
    );
  }

  const v = data.verdict;
  const t = data.telemetry;
  const isGo = v.decision === "GO";
  const isHold = v.decision === "HOLD";
  const accent = isGo ? ACCENTS.green : isHold ? ACCENTS.amber : ACCENTS.magenta;
  const Icon = isGo ? ShieldCheck : isHold ? ShieldQuestion : ShieldAlert;

  return (
    <div
      data-testid="preflight-panel"
      className="rounded-xl overflow-hidden"
      style={{
        background: "linear-gradient(180deg, rgba(8,14,24,0.94) 0%, rgba(4,8,14,0.96) 100%)",
        border: `1.5px solid ${accent}88`,
        boxShadow: `inset 0 0 36px ${accent}10, 0 0 24px ${accent}22`,
      }}
    >
      {/* HEADER */}
      <div className="px-5 py-3 flex items-center justify-between border-b"
           style={{ borderColor: `${accent}33` }}>
        <div className="flex items-center gap-3">
          <Plane size={16} style={{ color: accent }}/>
          <div>
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: accent }}>
              // PRE-FLIGHT ATC · LIVE
            </div>
            <div className="font-display text-[14px] uppercase tracking-[0.12em] text-white">
              {coords.lat.toFixed(3)}, {coords.lon.toFixed(3)}
            </div>
          </div>
        </div>
        <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
          OPEN-METEO · {new Date(data.polled_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>

      {/* VERDICT BLOCK */}
      <div className="p-5 grid grid-cols-1 md:grid-cols-[200px_1fr] gap-5 items-center">
        <div className="text-center">
          <div className="relative w-[160px] h-[160px] mx-auto grid place-items-center">
            <svg viewBox="0 0 160 160" className="absolute inset-0">
              <defs>
                <radialGradient id="atcSeal" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stopColor={accent} stopOpacity="0.45"/>
                  <stop offset="100%" stopColor={accent} stopOpacity="0"/>
                </radialGradient>
              </defs>
              <circle cx="80" cy="80" r="74" fill="url(#atcSeal)"/>
              <circle cx="80" cy="80" r="70" fill="none" stroke={accent} strokeWidth="2"/>
              {Array.from({length: 24}).map((_, i) => (
                <line key={i} x1="80" y1="6" x2="80" y2="14"
                      transform={`rotate(${i * 15} 80 80)`}
                      stroke={accent} strokeWidth="1.4"/>
              ))}
            </svg>
            <div className="relative text-center" style={{ filter: `drop-shadow(0 0 12px ${accent})` }}>
              <Icon size={30} color={accent} strokeWidth={1.6} className="mx-auto"/>
              <div className="font-display font-bold text-3xl tracking-[0.04em] text-white mt-1 leading-none">
                {v.decision}
              </div>
              <div className="font-mono text-[9px] tracking-[0.22em] mt-1" style={{ color: accent }}>
                {v.confidence_pct}% CONFIDENCE
              </div>
            </div>
          </div>
        </div>

        <div>
          <div className="font-mono text-[10px] tracking-[0.24em] uppercase mb-2" style={{ color: accent }}>
            // OPERATOR BRIEF
          </div>
          <p className="text-[12.5px] text-slate-200 leading-relaxed mb-3">{v.operator_brief}</p>
          <ul className="space-y-1">
            {v.reasons.map((r, i) => (
              <li key={i} className="flex items-start gap-2 font-mono text-[10.5px] text-slate-300 tracking-wide">
                <span className="mt-1.5 w-1 h-1 rounded-full shrink-0" style={{ background: accent }}/>
                <span>{r}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>

      {/* TELEMETRY GRID */}
      <div className="px-5 pb-5 grid grid-cols-3 md:grid-cols-6 gap-2">
        {[
          { l: "WIND",   v: `${t.wind_mph}`, u: "mph", icon: Wind,       c: ACCENTS.cyan },
          { l: "GUST",   v: `${t.gust_mph}`, u: "mph", icon: Wind,       c: ACCENTS.amber },
          { l: "PRECIP", v: `${t.precip_mm}`,u: "mm",  icon: Droplets,   c: ACCENTS.cyan },
          { l: "VIS",    v: `${(t.visibility_m / 1000).toFixed(1)}`, u: "km", icon: Eye,    c: ACCENTS.green },
          { l: "CLOUD",  v: `${t.cloud_pct}`,u: "%",   icon: CloudSun,   c: ACCENTS.cyan },
          { l: "TEMP",   v: `${t.temp_f}`,   u: "°F",  icon: Thermometer,c: ACCENTS.amber },
        ].map((cell) => (
          <div key={cell.l} className="rounded-md p-2.5 text-center"
               style={{ background: "rgba(15,22,34,0.55)", border: `1px solid ${cell.c}44` }}>
            <cell.icon size={11} color={cell.c} className="mx-auto"/>
            <div className="font-display text-[15px] leading-none mt-1 text-white">{cell.v}</div>
            <div className="font-mono text-[8px] tracking-[0.22em] uppercase mt-0.5" style={{ color: cell.c }}>
              {cell.l} · {cell.u}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Doppler radar (RainViewer)
// ─────────────────────────────────────────────────────────────────
function DopplerRadarPanel({ coords }) {
  const ready = useLeaflet();
  const mapRef = useRef(null);
  const containerRef = useRef(null);
  const [tsList, setTsList] = useState([]);
  const radarLayerRef = useRef(null);

  // Init map once
  useEffect(() => {
    if (!ready || mapRef.current || !containerRef.current) return;
    const L = window.L;
    mapRef.current = L.map(containerRef.current, { zoomControl: false, attributionControl: false })
                      .setView([coords.lat, coords.lon], 6);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      maxZoom: 10, subdomains: "abcd",
    }).addTo(mapRef.current);
    L.circleMarker([coords.lat, coords.lon], {
      radius: 8, color: ACCENTS.cyan, fillColor: ACCENTS.cyan, fillOpacity: 1, weight: 2,
    }).addTo(mapRef.current).bindTooltip("Target · " + coords.lat.toFixed(3) + ", " + coords.lon.toFixed(3));
  }, [ready, coords.lat, coords.lon]);

  // Fetch latest radar frame index
  useEffect(() => {
    fetch("https://api.rainviewer.com/public/weather-maps.json")
      .then((r) => r.json())
      .then((j) => {
        const list = (j.radar?.past || []).slice(-6).map((p) => p.path);
        setTsList(list);
      }).catch(() => {});
  }, []);

  // Apply latest frame
  useEffect(() => {
    if (!ready || !mapRef.current || tsList.length === 0) return;
    const L = window.L;
    const latest = tsList[tsList.length - 1];
    if (radarLayerRef.current) {
      mapRef.current.removeLayer(radarLayerRef.current);
    }
    radarLayerRef.current = L.tileLayer(
      `https://tilecache.rainviewer.com${latest}/256/{z}/{x}/{y}/2/1_1.png`,
      { opacity: 0.7, maxZoom: 8, minZoom: 2 }
    ).addTo(mapRef.current);
  }, [ready, tsList]);

  return (
    <div
      data-testid="doppler-panel"
      className="rounded-xl overflow-hidden relative"
      style={{
        background: "rgba(8,14,24,0.86)",
        border: `1.5px solid ${ACCENTS.cyan}88`,
        boxShadow: `inset 0 0 36px ${ACCENTS.cyan}10`,
      }}
    >
      <div className="px-5 py-3 border-b flex items-center justify-between"
           style={{ borderColor: `${ACCENTS.cyan}33` }}>
        <div className="flex items-center gap-3">
          <Wind size={16} className="text-cyan-400"/>
          <div>
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase text-cyan-400">
              // DOPPLER RADAR · LIVE
            </div>
            <div className="font-display text-[14px] uppercase tracking-[0.12em] text-white">
              RainViewer · 60-min loop
            </div>
          </div>
        </div>
        <span className="font-mono text-[9px] tracking-[0.22em] uppercase text-slate-500">
          {tsList.length} FRAMES
        </span>
      </div>
      <div ref={containerRef}
           data-testid="doppler-map"
           style={{ height: 320, background: "#02060B" }}/>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Connected Calendar
// ─────────────────────────────────────────────────────────────────
function CalendarPanel({ refreshKey, onRefresh }) {
  const API = process.env.REACT_APP_BACKEND_URL;
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState({
    title: "", kind: "SCAN", start: "", location: "", crew: "",
  });

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/calendar/events`);
      const j = await r.json();
      setEvents(j.items || []);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, [refreshKey]);

  const add = async () => {
    if (!draft.title || !draft.start) {
      toast.error("Title and start time required.");
      return;
    }
    const body = {
      ...draft,
      crew: draft.crew ? draft.crew.split(",").map((s) => s.trim()) : null,
      end: null, notes: null, job_id: null, color: null,
    };
    const r = await fetch(`${API}/api/calendar/events`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      toast.success("Event added");
      setAdding(false);
      setDraft({ title: "", kind: "SCAN", start: "", location: "", crew: "" });
      load();
      onRefresh?.();
    } else {
      toast.error("Save failed");
    }
  };

  const del = async (id) => {
    if (!window.confirm("Remove this event?")) return;
    const r = await fetch(`${API}/api/calendar/events/${id}`, { method: "DELETE" });
    if (r.ok) { toast.success("Removed"); load(); onRefresh?.(); }
  };

  const grouped = useMemo(() => {
    const g = {};
    for (const e of events) {
      const day = e.start?.slice(0, 10) || "unscheduled";
      (g[day] ||= []).push(e);
    }
    return g;
  }, [events]);

  const kindColor = (k) => ({
    SCAN: ACCENTS.cyan, CREW: ACCENTS.volt, DISPATCH: ACCENTS.amber,
    BILLING: ACCENTS.magenta, CHECKUP: ACCENTS.gold, MAINT: ACCENTS.magenta,
  })[k] || ACCENTS.cyan;

  return (
    <div data-testid="calendar-panel" className="rounded-xl"
         style={{ background: "rgba(8,14,24,0.86)", border: `1.5px solid ${ACCENTS.gold}66`,
                  boxShadow: `inset 0 0 28px ${ACCENTS.gold}08` }}>
      <div className="px-5 py-3 border-b flex items-center justify-between flex-wrap gap-2"
           style={{ borderColor: `${ACCENTS.gold}33` }}>
        <div className="flex items-center gap-3">
          <CalIcon size={16} style={{ color: ACCENTS.gold }}/>
          <div>
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: ACCENTS.gold }}>
              // CONNECTED CALENDAR · LIVE
            </div>
            <div className="font-display text-[14px] uppercase tracking-[0.12em] text-white">
              Shared schedule · {events.length} events
            </div>
          </div>
        </div>
        <button
          data-testid="cal-add-btn"
          onClick={() => setAdding((v) => !v)}
          className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1"
          style={{ background: `${ACCENTS.gold}14`, border: `1px solid ${ACCENTS.gold}88`, color: ACCENTS.gold }}>
          <Plus size={11}/> Add Event
        </button>
      </div>

      {adding && (
        <div className="px-5 py-3 border-b grid grid-cols-2 lg:grid-cols-4 gap-2"
             style={{ borderColor: `${ACCENTS.gold}22` }}>
          <input data-testid="cal-title" placeholder="Title" value={draft.title}
                 onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                 className="lg:col-span-2 px-2.5 py-1.5 rounded-sm bg-transparent outline-none font-mono text-[11px] text-white"
                 style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}44` }}/>
          <select data-testid="cal-kind" value={draft.kind}
                  onChange={(e) => setDraft({ ...draft, kind: e.target.value })}
                  className="px-2.5 py-1.5 rounded-sm font-mono text-[11px] text-white outline-none"
                  style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}44` }}>
            {["SCAN","CREW","DISPATCH","BILLING","CHECKUP","MAINT","OTHER"].map((k) =>
              <option key={k} value={k}>{k}</option>)}
          </select>
          <input data-testid="cal-start" type="datetime-local" value={draft.start}
                 onChange={(e) => setDraft({ ...draft, start: e.target.value ? new Date(e.target.value).toISOString() : "" })}
                 className="px-2.5 py-1.5 rounded-sm bg-transparent outline-none font-mono text-[11px] text-white"
                 style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}44`, colorScheme: "dark" }}/>
          <input data-testid="cal-location" placeholder="Location (e.g. 2440 Regency Rd · Lexington KY)"
                 value={draft.location} onChange={(e) => setDraft({ ...draft, location: e.target.value })}
                 className="lg:col-span-2 px-2.5 py-1.5 rounded-sm bg-transparent outline-none font-mono text-[11px] text-white"
                 style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}44` }}/>
          <input data-testid="cal-crew" placeholder="Crew (comma-separated)"
                 value={draft.crew} onChange={(e) => setDraft({ ...draft, crew: e.target.value })}
                 className="px-2.5 py-1.5 rounded-sm bg-transparent outline-none font-mono text-[11px] text-white"
                 style={{ background: "rgba(0,229,255,0.04)", border: `1px solid ${ACCENTS.cyan}44` }}/>
          <button data-testid="cal-save" onClick={add}
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md"
                  style={{ background: ACCENTS.cyan, color: "#02060B", boxShadow: `0 0 12px ${ACCENTS.cyan}55` }}>
            Save Event
          </button>
        </div>
      )}

      <div className="px-5 py-3 max-h-[420px] overflow-y-auto deck-rail-scroll">
        {loading ? (
          <div className="py-6 text-center"><Loader2 size={20} className="mx-auto animate-spin text-cyan-400"/></div>
        ) : Object.keys(grouped).length === 0 ? (
          <div className="py-10 text-center font-mono text-[10px] tracking-[0.22em] uppercase text-slate-500">
            No events on the calendar.
            <div className="mt-2 text-[9px] text-slate-600">Add one with the button above ↑</div>
          </div>
        ) : (
          Object.entries(grouped).sort().map(([day, list]) => (
            <div key={day} className="mb-3">
              <div className="font-mono text-[9px] tracking-[0.28em] uppercase text-slate-500 mb-2">
                {new Date(day + "T00:00:00").toLocaleDateString(undefined, { weekday: "short", month: "short", day: "numeric" })}
              </div>
              <div className="space-y-1.5">
                {list.map((e) => {
                  const c = e.color || kindColor(e.kind);
                  const t = e.start ? new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "";
                  return (
                    <div key={e.id} className="rounded-md px-3 py-2 flex items-center gap-3"
                         style={{ background: "rgba(15,22,34,0.55)", border: `1px solid ${c}44` }}>
                      <span className="w-1 h-8 rounded-full shrink-0" style={{ background: c, boxShadow: `0 0 6px ${c}` }}/>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-[8.5px] tracking-[0.22em] uppercase px-1.5 py-0.5 rounded-full"
                                style={{ color: c, border: `1px solid ${c}66`, background: `${c}10` }}>{e.kind}</span>
                          <span className="font-mono text-[10px] text-cyan-300">{t}</span>
                        </div>
                        <div className="font-display text-[12px] uppercase tracking-[0.06em] text-white truncate">{e.title}</div>
                        <div className="font-mono text-[9px] tracking-[0.16em] uppercase text-slate-500 truncate">
                          {e.location || "—"} {e.crew ? `· ${e.crew.join(", ")}` : ""}
                        </div>
                      </div>
                      <button onClick={() => del(e.id)} data-testid={`cal-del-${e.id}`}
                              className="grid place-items-center rounded-md transition hover:brightness-150"
                              style={{ width: 24, height: 24, background: `${ACCENTS.magenta}14`,
                                       border: `1px solid ${ACCENTS.magenta}66`, color: ACCENTS.magenta }}>
                        <X size={11}/>
                      </button>
                    </div>
                  );
                })}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Fleet & Jobs Map
// ─────────────────────────────────────────────────────────────────
function FleetMapPanel({ refreshKey }) {
  const API = process.env.REACT_APP_BACKEND_URL;
  const ready = useLeaflet();
  const containerRef = useRef(null);
  const mapRef = useRef(null);
  const layerRef = useRef(null);
  const [snap, setSnap] = useState({ units: [], jobs: [] });
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/fleet/snapshot`);
      setSnap(await r.json());
    } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [refreshKey]);

  // Init map
  useEffect(() => {
    if (!ready || mapRef.current || !containerRef.current) return;
    const L = window.L;
    mapRef.current = L.map(containerRef.current, { zoomControl: true, attributionControl: false })
                      .setView([LEXINGTON.lat, LEXINGTON.lon], 11);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
      { maxZoom: 18, subdomains: "abcd" }).addTo(mapRef.current);
  }, [ready]);

  // Update pins
  useEffect(() => {
    if (!ready || !mapRef.current) return;
    const L = window.L;
    if (layerRef.current) mapRef.current.removeLayer(layerRef.current);
    const group = L.layerGroup();

    (snap.units || []).forEach((u) => {
      const c = u.status === "ACTIVE" ? ACCENTS.green :
                u.status === "EN_ROUTE" ? ACCENTS.cyan :
                u.status === "MAINT" ? ACCENTS.magenta : ACCENTS.amber;
      const dotHtml = `<div style="width:18px;height:18px;border-radius:50%;
        background:${c};box-shadow:0 0 10px ${c};
        border:2px solid #02060B;display:grid;place-items:center;
        font-family:'JetBrains Mono';font-size:8px;color:#02060B;font-weight:700;">
        ${u.kind === "MDU" ? "M" : u.kind === "DRONE" ? "D" : u.kind === "TRUCK" ? "T" : "C"}
      </div>`;
      L.marker([u.lat, u.lon], {
        icon: L.divIcon({ html: dotHtml, className: "", iconSize: [18, 18] })
      }).bindTooltip(`<b>${u.callsign}</b><br/>${u.kind} · ${u.status}<br/>${u.label || ""}`).addTo(group);
    });

    (snap.jobs || []).forEach((j) => {
      const c = ACCENTS.amber;
      const html = `<div style="width:14px;height:14px;border-radius:3px;
        background:transparent;border:2px solid ${c};box-shadow:0 0 8px ${c};
        transform:rotate(45deg);"></div>`;
      L.marker([j.lat, j.lon], {
        icon: L.divIcon({ html, className: "", iconSize: [14, 14] })
      }).bindTooltip(`<b>${j.title}</b><br/>${j.kind} · ${new Date(j.start).toLocaleString()}`).addTo(group);
    });

    layerRef.current = group.addTo(mapRef.current);
  }, [ready, snap]);

  return (
    <div data-testid="fleet-map-panel" className="rounded-xl overflow-hidden"
         style={{ background: "rgba(8,14,24,0.86)", border: `1.5px solid ${ACCENTS.volt}66`,
                  boxShadow: `inset 0 0 28px ${ACCENTS.volt}08` }}>
      <div className="px-5 py-3 border-b flex items-center justify-between"
           style={{ borderColor: `${ACCENTS.volt}33` }}>
        <div className="flex items-center gap-3">
          <MapPin size={16} style={{ color: ACCENTS.volt }}/>
          <div>
            <div className="font-mono text-[9px] tracking-[0.28em] uppercase" style={{ color: ACCENTS.volt }}>
              // FLEET & JOBS MAP · LIVE
            </div>
            <div className="font-display text-[14px] uppercase tracking-[0.12em] text-white">
              {snap.units.length} units · {snap.jobs.length} jobs
            </div>
          </div>
        </div>
        <button onClick={load} data-testid="fleet-refresh"
                className="font-mono text-[9px] tracking-[0.22em] uppercase px-2.5 py-1 rounded-md flex items-center gap-1"
                style={{ background: `${ACCENTS.volt}14`, border: `1px solid ${ACCENTS.volt}66`, color: ACCENTS.volt }}>
          <RefreshCw size={10}/> Sync
        </button>
      </div>
      <div ref={containerRef} style={{ height: 360, background: "#02060B" }}/>
      <div className="px-4 py-2 border-t flex items-center justify-between text-[9px] font-mono tracking-[0.18em] uppercase"
           style={{ borderColor: `${ACCENTS.volt}22` }}>
        <span className="text-slate-500 flex items-center gap-3">
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: ACCENTS.green, boxShadow: `0 0 4px ${ACCENTS.green}` }}/>ACTIVE</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: ACCENTS.cyan, boxShadow: `0 0 4px ${ACCENTS.cyan}` }}/>EN-ROUTE</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full" style={{ background: ACCENTS.amber, boxShadow: `0 0 4px ${ACCENTS.amber}` }}/>STANDBY</span>
          <span className="flex items-center gap-1"><span className="w-2 h-2 rotate-45 border" style={{ borderColor: ACCENTS.amber }}/>JOB</span>
        </span>
        {loading && <Loader2 size={11} className="animate-spin text-cyan-400"/>}
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Main page
// ─────────────────────────────────────────────────────────────────
export default function MissionControl() {
  const nav = useNavigate();
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div
      data-testid="mission-control"
      className="min-h-screen text-slate-100"
      style={{
        background:
          "radial-gradient(ellipse at 75% 0%, rgba(0,229,255,0.10) 0%, transparent 50%)," +
          "radial-gradient(ellipse at 5% 100%, rgba(212,184,106,0.08) 0%, transparent 55%)," +
          "linear-gradient(180deg, #050912 0%, #02060B 60%, #050912 100%)",
        fontFamily: "'Sora', sans-serif",
      }}
    >
      <header className="max-w-[1500px] mx-auto px-4 sm:px-6 py-6 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <button onClick={() => nav("/deck")}
                  data-testid="back-deck"
                  className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                  style={{ background: "rgba(0,229,255,0.10)", border: `1px solid ${ACCENTS.cyan}55`, color: ACCENTS.cyan }}>
            <ArrowLeft size={12}/> Command Deck
          </button>
          <StratexLogo height={28}/>
        </div>
        <div className="font-mono text-[10px] tracking-[0.32em] uppercase text-cyan-400">// MISSION CONTROL · LIVE OPS</div>
        <button onClick={() => setRefreshKey((k) => k + 1)}
                data-testid="refresh-all"
                className="font-mono text-[10px] tracking-[0.22em] uppercase px-3 py-1.5 rounded-md flex items-center gap-1.5"
                style={{ background: "rgba(0,255,156,0.10)", border: `1px solid ${ACCENTS.green}66`, color: ACCENTS.green }}>
          <RefreshCw size={12}/> Sync All
        </button>
      </header>

      <main className="max-w-[1500px] mx-auto px-4 sm:px-6 pb-12 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PreflightAtcPanel coords={LEXINGTON} refreshKey={refreshKey}/>
        <DopplerRadarPanel  coords={LEXINGTON}/>
        <CalendarPanel       refreshKey={refreshKey} onRefresh={() => setRefreshKey((k) => k + 1)}/>
        <FleetMapPanel       refreshKey={refreshKey}/>
      </main>

      <style>{`
        .deck-rail-scroll::-webkit-scrollbar { width: 6px; }
        .deck-rail-scroll::-webkit-scrollbar-track { background: transparent; }
        .deck-rail-scroll::-webkit-scrollbar-thumb { background: rgba(0,229,255,0.28); border-radius: 4px; }
        .leaflet-tooltip { background: rgba(8,14,24,0.92) !important; border: 1px solid #00E5FF66 !important; color: #fff !important; font-family: 'JetBrains Mono', monospace !important; font-size: 10px !important; padding: 4px 8px !important; }
        .leaflet-tooltip:before { display: none; }
      `}</style>
    </div>
  );
}
