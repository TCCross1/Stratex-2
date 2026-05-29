/**
 * /admin/weather — STRATEX™ Weather Intelligence
 *
 * - Doppler radar (RainViewer free tiles, animated)
 * - 7-day forecast (Open-Meteo free)
 * - AI storm-watch agent (Claude Haiku 4.5) — admin-tailored verdict
 * - 3-year on-this-day historical analysis (Claude Haiku 4.5)
 *
 * All upstream services are public/free. The two LLM calls are cached
 * server-side (15min / 1h) so this page is cheap to load repeatedly.
 */
import React, { useEffect, useMemo, useRef, useState } from "react";
import { MapContainer, TileLayer, GeoJSON, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";
import {
  CloudRain, Wind, Sun, Snowflake, CloudFog, CloudLightning, Cloud,
  AlertOctagon, ShieldCheck, RotateCw, Activity, History, Radar as RadarIcon,
} from "lucide-react";
import { api } from "@/lib/api";
import countiesGeo from "@/data/centralKyCounties.json";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";

const RISK_STYLE = {
  calm:    { color: TEAL,                  bg: "rgba(0,245,212,0.10)",  Icon: ShieldCheck,    label: "Calm"    },
  watch:   { color: "#FFC857",             bg: "rgba(255,200,87,0.10)", Icon: Activity,       label: "Watch"   },
  warning: { color: ORANGE,                bg: "rgba(255,84,0,0.10)",   Icon: AlertOctagon,   label: "Warning" },
  severe:  { color: "#FF3D6E",             bg: "rgba(255,61,110,0.12)", Icon: CloudLightning, label: "Severe"  },
};

// WMO weather codes → icon
const wmoIcon = (code) => {
  if (code == null) return Cloud;
  if (code === 0) return Sun;
  if (code <= 3) return Cloud;
  if (code <= 48) return CloudFog;
  if (code <= 67) return CloudRain;
  if (code <= 77) return Snowflake;
  if (code <= 82) return CloudRain;
  if (code <= 99) return CloudLightning;
  return Cloud;
};
const wmoLabel = (code) => {
  if (code == null) return "—";
  if (code === 0) return "Clear";
  if (code <= 3) return ["Mainly Clear","Partly Cloudy","Overcast"][code-1] || "Cloudy";
  if (code <= 48) return "Fog";
  if (code <= 57) return "Drizzle";
  if (code <= 67) return "Rain";
  if (code <= 77) return "Snow";
  if (code <= 82) return "Rain Showers";
  if (code <= 86) return "Snow Showers";
  if (code <= 99) return "Thunderstorm";
  return "—";
};

const COUNTY_STYLE = (f) => ({
  color: f?.properties?.is_primary ? TEAL : "#5ff4ff",
  weight: f?.properties?.is_primary ? 2.2 : 1.4,
  opacity: f?.properties?.is_primary ? 0.95 : 0.6,
  fillColor: f?.properties?.is_primary ? TEAL : "#5ff4ff",
  fillOpacity: f?.properties?.is_primary ? 0.05 : 0.02,
  dashArray: f?.properties?.is_primary ? null : "3,3",
});

const LEX = { lat: 38.0406, lon: -84.5037 };

export default function AdminWeather() {
  const [forecast, setForecast] = useState(null);
  const [radar, setRadar] = useState(null);
  const [storm, setStorm] = useState(null);
  const [hist, setHist] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);
  const [err, setErr] = useState(null);

  // Radar frame animation
  const [frameIdx, setFrameIdx] = useState(0);
  const radarLayerRef = useRef(null);

  useEffect(() => {
    (async () => {
      try {
        const [f, r] = await Promise.all([
          api.get("/weather/forecast"),
          api.get("/weather/radar"),
        ]);
        setForecast(f.data);
        setRadar(r.data);
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message);
      }
    })();
  }, []);

  // Animate radar frames at 1.2 FPS
  useEffect(() => {
    if (!radar?.frames?.length) return;
    const t = setInterval(() => setFrameIdx((i) => (i + 1) % radar.frames.length), 800);
    return () => clearInterval(t);
  }, [radar]);

  const radarTileUrl = useMemo(() => {
    if (!radar?.frames?.length) return null;
    const f = radar.frames[frameIdx];
    return `${radar.host}${f.path}/256/{z}/{x}/{y}/2/1_1.png`;
  }, [radar, frameIdx]);

  // Lazy AI agent calls (only when admin asks)
  async function runAIAgents() {
    setLoadingAI(true);
    try {
      const [s, h] = await Promise.all([
        api.post("/weather/storm-watch", { audience: "admin" }),
        api.post("/weather/historical-analysis", { audience: "admin", years_back: 3 }),
      ]);
      setStorm(s.data); setHist(h.data);
    } catch (e) {
      setErr(e?.response?.data?.detail || e.message);
    } finally { setLoadingAI(false); }
  }

  // Auto-trigger AI agents on first load
  useEffect(() => { if (forecast && !storm && !loadingAI) runAIAgents(); }, [forecast]); // eslint-disable-line

  const days = useMemo(() => {
    if (!forecast?.daily) return [];
    const d = forecast.daily;
    return (d.time || []).slice(0, 7).map((date, i) => ({
      date,
      code: d.weather_code?.[i],
      tmax: d.temperature_2m_max?.[i],
      tmin: d.temperature_2m_min?.[i],
      precip: d.precipitation_sum?.[i],
      precip_prob: d.precipitation_probability_max?.[i],
      wind: d.wind_speed_10m_max?.[i],
      gust: d.wind_gusts_10m_max?.[i],
    }));
  }, [forecast]);

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="admin-weather-root">
      <div className="max-w-[1400px] mx-auto">
        <div className="flex items-center gap-3 mb-2">
          <span className="led led-teal"/>
          <div className="font-mono text-[11px] tracking-[0.36em] uppercase" style={{ color: TEAL }}>
            // STRATEX VISION • WEATHER INTELLIGENCE • CENTRAL KY
          </div>
        </div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">Doppler · Forecast · Storm Watch</h1>
        <p className="font-body text-sm text-muted-hud mb-6 max-w-3xl">
          Live Doppler radar (RainViewer), 7-day forecast (Open-Meteo), and two AI agents — a storm-watch agent
          tracking developing systems and a historical analyst comparing today's date across the last three years.
        </p>

        {err && (
          <div className="mb-5 font-mono text-[10px] uppercase tracking-widest p-3 border"
               style={{ color: ORANGE, borderColor: ORANGE, background: "rgba(255,84,0,0.08)" }}
               data-testid="admin-weather-error">
            // ERROR · {String(err).slice(0, 200)}
          </div>
        )}

        {/* Storm-watch verdict banner */}
        {storm && <StormWatchBanner verdict={storm.verdict} generatedAt={storm.generated_at}/>}
        {loadingAI && !storm && (
          <div className="mb-5 font-mono text-[10px] uppercase tracking-widest" style={{ color: TEAL }}>
            // STORM-WATCH AGENT ANALYZING FORECAST…
          </div>
        )}

        {/* Doppler radar + forecast */}
        <div className="grid lg:grid-cols-[1.6fr_1fr] gap-4 mb-5">
          <div className="border bg-[#0B0F19]" style={{ borderColor: `${TEAL}33` }} data-testid="admin-weather-radar">
            <div className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest flex items-center gap-2" style={{ color: TEAL }}>
              <RadarIcon size={11}/> Doppler Radar · RainViewer · Frame {radar ? `${frameIdx + 1}/${radar.frames.length}` : "—"}
            </div>
            <div className="relative" style={{ height: 460 }}>
              <MapContainer center={[LEX.lat, LEX.lon]} zoom={7} style={{ height: "100%", width: "100%", background: "#06080B" }} scrollWheelZoom>
                <TileLayer
                  attribution='Imagery &copy; Esri'
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  maxZoom={19}
                />
                {radarTileUrl && (
                  <TileLayer
                    key={radarTileUrl}
                    ref={radarLayerRef}
                    url={radarTileUrl}
                    opacity={0.7}
                    maxNativeZoom={8}
                    attribution='Radar &copy; RainViewer'
                  />
                )}
                <GeoJSON data={countiesGeo} style={COUNTY_STYLE}
                  onEachFeature={(feature, layer) => {
                    const p = feature.properties || {};
                    layer.bindTooltip(
                      `<div style="font-family:monospace;font-size:10px;color:#0B0F19;background:#00F5D4;padding:2px 6px;letter-spacing:1px">${(p.city || "").toUpperCase()} · ${p.name || ""}</div>`,
                      { permanent: false, direction: "center" }
                    );
                  }}
                />
                <Marker position={[LEX.lat, LEX.lon]} icon={L.divIcon({
                  className: "stratex-wx-pin",
                  html: `<div style="filter:drop-shadow(0 0 8px ${TEAL});transform:translate(-9px,-9px);">
                    <svg width="18" height="18" viewBox="0 0 18 18"><circle cx="9" cy="9" r="4" fill="${TEAL}"/><circle cx="9" cy="9" r="7" fill="none" stroke="${TEAL}" stroke-width="1.2"/></svg></div>`,
                  iconSize: [18, 18], iconAnchor: [9, 9],
                })}>
                  <Popup><div style={{fontFamily:"monospace",fontSize:11,color:"#06080B"}}>STRATEX OPS · Lexington</div></Popup>
                </Marker>
              </MapContainer>
            </div>
          </div>

          {/* 7-day forecast cards */}
          <div className="border" style={{ borderColor: NICKEL }} data-testid="admin-weather-forecast">
            <div className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest" style={{ color: TEAL }}>
              7-DAY FORECAST · OPEN-METEO
            </div>
            <ul className="divide-y" style={{ borderColor: NICKEL }}>
              {days.map((d, i) => {
                const Icon = wmoIcon(d.code);
                return (
                  <li key={d.date} className="flex items-center gap-3 px-3 py-2.5" style={{ borderColor: NICKEL }}>
                    <div className="w-12 text-[10px] font-mono uppercase tracking-widest text-muted-hud">
                      {i === 0 ? "Today" : new Date(d.date + "T12:00:00").toLocaleDateString(undefined, { weekday: "short" })}
                    </div>
                    <Icon size={20} style={{ color: TEAL }}/>
                    <div className="flex-1 min-w-0">
                      <div className="font-mono text-[11px] uppercase tracking-widest text-silver">{wmoLabel(d.code)}</div>
                      <div className="font-mono text-[9.5px] text-muted-hud">
                        gust {d.gust ?? "—"}mph · precip {d.precip ?? 0}" · {d.precip_prob ?? 0}%
                      </div>
                    </div>
                    <div className="font-mono text-[12px] text-silver tabular-nums">
                      <span style={{ color: TEAL }}>{Math.round(d.tmax)}°</span>
                      <span className="text-muted-hud"> / {Math.round(d.tmin)}°</span>
                    </div>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>

        {/* AI re-run + 3-year historical */}
        <div className="flex items-center gap-3 mb-3">
          <button
            onClick={runAIAgents}
            disabled={loadingAI}
            data-testid="admin-weather-refresh-ai"
            className="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 inline-flex items-center gap-2"
            style={{ borderColor: `${TEAL}55`, color: TEAL, opacity: loadingAI ? 0.5 : 1 }}
          >
            <RotateCw size={11} className={loadingAI ? "animate-spin" : ""}/> {loadingAI ? "Agents working…" : "Re-run AI agents"}
          </button>
          <div className="ml-auto font-mono text-[10px] text-muted-hud">
            {storm?.generated_at && <>storm-watch {new Date(storm.generated_at).toLocaleTimeString()} · </>}
            {hist?.generated_at && <>historical {new Date(hist.generated_at).toLocaleTimeString()}</>}
          </div>
        </div>

        {hist && <HistoricalAnalysisCard hist={hist}/>}
      </div>
    </div>
  );
}

function StormWatchBanner({ verdict, generatedAt }) {
  if (!verdict) return null;
  const s = RISK_STYLE[verdict.risk_level] || RISK_STYLE.calm;
  const Icon = s.Icon;
  return (
    <div className="border-l-4 mb-5 p-4" style={{ borderLeftColor: s.color, background: s.bg, borderColor: NICKEL }}
         data-testid="admin-weather-storm-watch">
      <div className="flex items-start gap-3">
        <Icon size={22} style={{ color: s.color }} className="flex-shrink-0 mt-0.5"/>
        <div className="min-w-0">
          <div className="font-mono text-[10px] uppercase tracking-[0.28em] mb-1" style={{ color: s.color }}>
            // STORM-WATCH AGENT · CLAUDE HAIKU 4.5 · {s.label}
          </div>
          <div className="font-display text-base md:text-lg uppercase tracking-widest text-silver mb-1">
            {verdict.headline || "—"}
          </div>
          <p className="font-body text-[12.5px] leading-relaxed text-silver">{verdict.narrative}</p>
          {Array.isArray(verdict.developing_systems) && verdict.developing_systems.length > 0 && (
            <div className="mt-3 space-y-1.5">
              <div className="font-mono text-[9.5px] uppercase tracking-[0.22em]" style={{ color: s.color }}>
                Developing systems detected
              </div>
              {verdict.developing_systems.map((sys, i) => (
                <div key={i} className="font-mono text-[11px] flex flex-wrap items-center gap-x-3 gap-y-0.5">
                  <span className="text-muted-hud">{sys.date}</span>
                  <span style={{ color: s.color }}>{sys.kind}</span>
                  <span className="text-muted-hud">conf {sys.confidence_pct}%</span>
                  <span className="text-silver">{sys.note}</span>
                </div>
              ))}
            </div>
          )}
          {generatedAt && (
            <div className="font-mono text-[9.5px] text-muted-hud mt-2">
              generated · {new Date(generatedAt).toLocaleString()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function HistoricalAnalysisCard({ hist }) {
  const v = hist.verdict || {};
  return (
    <div className="border p-4" style={{ borderColor: `${TEAL}33` }} data-testid="admin-weather-historical">
      <div className="flex items-center gap-2 mb-2">
        <History size={16} style={{ color: TEAL }}/>
        <div className="font-mono text-[10px] uppercase tracking-[0.28em]" style={{ color: TEAL }}>
          // 3-YEAR ON-THIS-DAY ANALYSIS · {hist.today}
        </div>
      </div>
      <div className="font-display text-base uppercase tracking-widest text-silver mb-1">
        {v.summary_headline || "—"}
      </div>
      <p className="font-body text-[12.5px] leading-relaxed text-silver mb-3">{v.narrative}</p>

      {Array.isArray(v.key_signals) && v.key_signals.length > 0 && (
        <ul className="mb-3 space-y-1">
          {v.key_signals.map((s, i) => (
            <li key={i} className="font-mono text-[11px] text-silver flex gap-2">
              <span style={{ color: TEAL }}>›</span>
              <span>{s}</span>
            </li>
          ))}
        </ul>
      )}

      <div className="grid md:grid-cols-3 gap-3">
        {(v.year_by_year || []).map((y, i) => (
          <div key={y.year} className="border p-3" style={{ borderColor: NICKEL, background: "#0B0F19" }}>
            <div className="font-mono text-[9.5px] uppercase tracking-[0.22em] mb-1" style={{ color: TEAL }}>
              {y.year}
            </div>
            <div className="font-mono text-[10.5px] text-silver leading-snug mb-2">
              {y.one_line_note}
            </div>
            {hist.rows[i] && !hist.rows[i].error && (
              <div className="font-mono text-[9.5px] text-muted-hud space-y-0.5">
                <div>hi {Math.round(hist.rows[i].tmax_f)}° · lo {Math.round(hist.rows[i].tmin_f)}°</div>
                <div>precip {hist.rows[i].precip_in ?? 0}" · gust {hist.rows[i].gust_max_mph ?? "—"}mph</div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
