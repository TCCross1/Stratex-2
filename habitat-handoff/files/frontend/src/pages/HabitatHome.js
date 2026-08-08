/**
 * Habitat home dashboard — aligned to approved desktop/mobile mockups.
 * Data: GET /api/habitat/dashboard/projection + /api/habitat/openings
 * Uses REACT_APP_BACKEND_URL so the browser receives JSON (not SPA HTML).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Brand } from "@/components/Brand";
import { useAppData } from "@/context/AppDataContext";
import { CENTRAL_KENTUCKY_DEMO_HOME } from "@/propertyVisualization/centralKentuckyDemoHome";
import { API } from "@/lib/api";

async function fetchJson(path) {
  const r = await fetch(`${API}${path}`, { credentials: "include" });
  const ctype = r.headers.get("content-type") || "";
  if (!r.ok) {
    throw new Error(`HTTP ${r.status} for ${path}`);
  }
  if (!ctype.includes("application/json")) {
    throw new Error(
      `Expected JSON from ${path}, got ${ctype || "unknown"} (check REACT_APP_BACKEND_URL)`
    );
  }
  return r.json();
}

export default function HabitatHome() {
  const navigate = useNavigate();
  const { property } = useAppData();
  const twinImg =
    property?.twin_image ||
    property?.thumbnail ||
    CENTRAL_KENTUCKY_DEMO_HOME?.heroAsset ||
    CENTRAL_KENTUCKY_DEMO_HOME?.thumbAsset ||
    null;
  const [data, setData] = useState(null);
  const [openings, setOpenings] = useState([]);
  const [selected, setSelected] = useState(null);
  const [layers, setLayers] = useState([]);
  const [activeLayers, setActiveLayers] = useState({ finish: true });
  const [err, setErr] = useState(null);

  useEffect(() => {
    Promise.all([
      fetchJson("/habitat/dashboard/projection"),
      fetchJson("/habitat/openings"),
      fetchJson("/habitat/twin/layers"),
    ])
      .then(([dash, opens, lyr]) => {
        setData(dash);
        setOpenings(opens.openings || []);
        if (opens.openings?.[0]) setSelected(opens.openings[0]);
        setLayers(lyr.layers || []);
        const init = {};
        (lyr.layers || []).forEach((l) => {
          init[l.id] = !!l.default;
        });
        setActiveLayers(init);
      })
      .catch((e) => setErr(String(e)));
  }, []);

  if (err) {
    return (
      <div className="p-8 text-red-400" data-testid="habitat-home-error">
        Failed to load projection: {err}
      </div>
    );
  }
  if (!data) {
    return (
      <div className="p-8 text-[#71717a] animate-pulse" data-testid="habitat-home-loading">
        Loading Property Passport…
      </div>
    );
  }

  const p = data.property || {};
  const hh = data.home_health || { systems: {} };
  const pm = data.predictive_maintenance || {};
  const fin = data.financial || {};
  const awe = data.awe || {};

  const toggleLayer = (id) =>
    setActiveLayers((prev) => ({ ...prev, [id]: !prev[id] }));

  return (
    <div className="min-h-full bg-[#0b0e14] text-[#f3f6fa]" data-testid="habitat-home">
      {/* Hero passport */}
      <section className="m-4 p-5 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d] shadow-[0_0_24px_rgba(0,229,255,0.12)]">
        <div className="flex flex-col lg:flex-row gap-6">
          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1">
              <div className="text-[11px] tracking-widest text-teal-300/90">PROPERTY PASSPORT</div>
              <span
                data-testid="projection-authority-badge"
                className={
                  data.authoritative
                    ? "text-[10px] px-2 py-0.5 rounded border border-[rgba(0,229,255,0.45)] text-[#00e5ff]"
                    : "text-[10px] px-2 py-0.5 rounded border border-[rgba(245,158,11,0.45)] text-[#f59e0b]"
                }
              >
                {data.authoritative ? "Official" : "Preview"}
              </span>
            </div>
            <h1 className="text-2xl font-semibold text-white">{p.address_line}</h1>
            <p className="text-sm text-[#8b9bb0]">{p.city_state_zip}</p>
            <div className="flex items-end gap-4 mt-4">
              <div>
                <div className="text-5xl font-bold text-[#00e5ff]">{p.certified_score}</div>
                <div className="text-xs text-[#8b9bb0]">/{p.score_scale ?? 1000}</div>
              </div>
              <div className="text-sm text-[#a1a1aa] pb-1">{p.rank_label}</div>
            </div>
            <div className="flex flex-wrap gap-2 mt-4">
              <button
                type="button"
                onClick={() => navigate("/reports")}
                className="px-4 py-2 rounded-lg bg-[#00e5ff] text-[#0b0e14] text-sm font-semibold"
              >
                View Property Report
              </button>
              <button
                type="button"
                onClick={() => navigate("/twin")}
                className="px-4 py-2 rounded-lg border border-[rgba(0,229,255,0.45)] text-[#00e5ff] text-sm"
              >
                Explore 3D Twin
              </button>
              <button
                type="button"
                className="px-4 py-2 rounded-lg border border-[#27272a] text-[#a1a1aa] text-sm"
              >
                Quick Scan
              </button>
              <button
                type="button"
                onClick={() => navigate("/exterior-studio")}
                className="px-4 py-2 rounded-lg border border-[rgba(0,229,255,0.35)] text-[#00e5ff] text-sm"
              >
                Exterior Studio
              </button>
              <button
                type="button"
                onClick={() => navigate("/interior-studio")}
                className="px-4 py-2 rounded-lg border border-[rgba(0,229,255,0.35)] text-[#00e5ff] text-sm"
              >
                Interior Studio
              </button>
            </div>
          </div>
          <div className="flex-1 min-h-[220px] rounded-lg border border-[rgba(0,229,255,0.35)] bg-[#12181f] flex flex-col items-center justify-center gap-3 overflow-hidden relative">
            {twinImg ? (
              <img src={twinImg} alt="Property digital twin" className="absolute inset-0 w-full h-full object-cover opacity-80" />
            ) : (
              <Brand />
            )}
            <div className="relative z-10 flex flex-col items-center gap-2 bg-black/40 px-3 py-2 rounded-lg">
            <p className="text-xs text-[#e4e4e7]">Twin viewport · layers below</p>
            <div className="flex flex-wrap gap-2 justify-center px-3">
              {layers.map((l) => (
                <button
                  key={l.id}
                  type="button"
                  onClick={() => toggleLayer(l.id)}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    activeLayers[l.id]
                      ? "border-[#00e5ff] text-[#00e5ff] shadow-[0_0_12px_rgba(0,229,255,0.25)]"
                      : "border-[#27272a] text-[#71717a]"
                  }`}
                >
                  {l.label}
                </button>
              ))}
            </div>
            {activeLayers.openings && (
              <p className="text-[11px] text-[#00e5ff]">Openings layer on · select a unit →</p>
            )}
            {activeLayers.awe && (
              <p className="text-[11px] text-orange-400">AWE hotspots active</p>
            )}
            </div>
          </div>
        </div>
      </section>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4 px-4 pb-4">
        {/* Home health */}
        <section className="p-4 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d]">
          <h2 className="text-sm font-medium text-white mb-2">Home Health Forecast</h2>
          <div className="text-4xl font-bold text-[#00e5ff]">{hh.overall}%</div>
          <div className="text-sm text-green-400 mb-3">{hh.label}</div>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(hh.systems || {}).map(([k, v]) => (
              <div key={k} className="rounded-lg bg-[#12181f] p-2">
                <div className="text-[10px] uppercase text-[#71717a]">{k}</div>
                <div className="text-sm font-semibold">{v}%</div>
              </div>
            ))}
          </div>
        </section>

        {/* Predictive + AWE */}
        <section className="p-4 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d] space-y-4">
          <div>
            <h2 className="text-sm font-medium text-white">Predictive Maintenance</h2>
            <div className="text-3xl font-bold mt-1">
              ${Number(pm.next_12_months_usd || 0).toLocaleString()}
            </div>
            <div className="text-sm text-[#8b9bb0]">
              {pm.recommended_actions ?? 0} Recommended Actions
            </div>
          </div>
          <div>
            <h2 className="text-sm font-medium text-white">AWE™ Index</h2>
            <div className="text-4xl font-bold text-[#00e5ff]">{awe.awe_index}</div>
            <div className="text-sm text-green-400">{awe.label}</div>
          </div>
        </section>

        {/* Financial */}
        <section className="p-4 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d]">
          <h2 className="text-sm font-medium text-white mb-3">Financial Dashboard</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-[#8b9bb0]">Current value</dt>
              <dd>${Number(fin.current_home_value || 0).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#8b9bb0]">Equity</dt>
              <dd>${Number(fin.equity || 0).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#8b9bb0]">Investment in home</dt>
              <dd>${Number(fin.investment_in_home || 0).toLocaleString()}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-[#8b9bb0]">Projected (5yr)</dt>
              <dd>${Number(fin.projected_value_5yr || 0).toLocaleString()}</dd>
            </div>
          </dl>
        </section>
      </div>

      {/* Openings */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 px-4 pb-8">
        <section className="lg:col-span-2 p-4 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d]">
          <h2 className="text-sm font-medium text-white mb-3">Exterior Openings</h2>
          <ul className="divide-y divide-[rgba(0,229,255,0.12)]">
            {openings.map((o) => (
              <li key={o.id}>
                <button
                  type="button"
                  onClick={() => setSelected(o)}
                  className={`w-full text-left py-3 text-sm hover:text-[#00e5ff] ${
                    selected?.id === o.id ? "text-[#00e5ff]" : "text-[#f3f6fa]"
                  }`}
                >
                  <span className="font-medium">{o.label}</span>
                  <span className="text-[#8b9bb0]"> · {o.unit_display} · RO {o.rough_opening_display}</span>
                </button>
              </li>
            ))}
          </ul>
        </section>
        {selected && (
          <aside className="p-4 rounded-xl border border-[rgba(0,229,255,0.18)] bg-[#1a222d]">
            <h3 className="font-medium text-white mb-3">{selected.label}</h3>
            <dl className="space-y-2 text-sm">
              <div>
                <dt className="text-[11px] text-teal-300/80">Type</dt>
                <dd>{selected.kind}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-teal-300/80">Elevation</dt>
                <dd>{selected.elevation}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-teal-300/80">Unit size</dt>
                <dd>{selected.unit_display}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-teal-300/80">Rough opening</dt>
                <dd className="text-[#00e5ff] font-semibold">{selected.rough_opening_display}</dd>
              </div>
              <div>
                <dt className="text-[11px] text-teal-300/80">Material / condition</dt>
                <dd>
                  {selected.material} · {selected.condition}
                </dd>
              </div>
              <div>
                <dt className="text-[11px] text-teal-300/80">Truth</dt>
                <dd>{selected.truth}</dd>
              </div>
            </dl>
            <p className="mt-3 text-[11px] text-[#71717a]">{selected.disclaimer}</p>
          </aside>
        )}
      </div>

      <footer className="text-center text-[10px] tracking-[0.15em] text-[#71717a] py-4 border-t border-[rgba(0,229,255,0.12)]">
        {data.tagline}
      </footer>
      <div
        className="text-center text-[10px] text-[#52525b] pb-4"
        data-testid="projection-authority-footer"
      >
        Passport: {data.passport_status || (data.authoritative ? "OK" : "PROJECTED")}
        {data.authoritative
          ? " · official Passport projection"
          : " · non-authoritative / preview overlay"}
        {data.source === "HABITAT_PROJECTION_PATH" ? " · file handoff" : ""}
      </div>
    </div>
  );
}
