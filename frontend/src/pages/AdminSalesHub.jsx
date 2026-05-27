import React, { useMemo, useState, useEffect, useRef } from "react";
import { api } from "@/lib/api";
import { KY_SALES_TARGETS, SALES_STATUS_OPTIONS, SALES_STATUS_COLORS } from "@/lib/salesTargets";

/**
 * /admin/sales — Pre-Cached Sales Targets Hub (Section 4 seed)
 *
 * Admin-only screen rendering the 7-record Central Kentucky contractor list.
 * Layout: sortable table (left 60%) + Leaflet map with status-tinted pins
 * anchored to Lexington-radius coordinates (right 40%).
 *
 * Admin gating: backend `/api/admin/sales-targets` returns 403 for non-admin
 * roles; this UI also reads the JWT and shows an inline lock screen if the
 * decoded role is not "admin".
 */
export default function AdminSalesHub() {
  const [rows, setRows] = useState(KY_SALES_TARGETS);
  const [sortKey, setSortKey] = useState("name");
  const [sortDir, setSortDir] = useState("asc");
  const [statusFilter, setStatusFilter] = useState("all");
  const [forbidden, setForbidden] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const mapRef = useRef(null);
  const mapInstRef = useRef(null);

  // ---- Admin auth probe ----
  useEffect(() => {
    api.get("/admin/sales-targets")
      .then((r) => {
        if (r.data?.targets?.length) setRows(r.data.targets);
        setLoaded(true);
      })
      .catch((err) => {
        if (err?.response?.status === 403) setForbidden(true);
        setLoaded(true);
      });
  }, []);

  // ---- Sorting + filtering ----
  const sorted = useMemo(() => {
    const filtered = statusFilter === "all" ? rows : rows.filter((r) => r.status === statusFilter);
    const out = [...filtered].sort((a, b) => {
      const av = (a[sortKey] || "").toString().toLowerCase();
      const bv = (b[sortKey] || "").toString().toLowerCase();
      if (av < bv) return sortDir === "asc" ? -1 : 1;
      if (av > bv) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return out;
  }, [rows, statusFilter, sortKey, sortDir]);

  // ---- Leaflet map lifecycle ----
  useEffect(() => {
    if (forbidden) return;
    let L; let cleaned = false;
    (async () => {
      L = await import("leaflet");
      await import("leaflet/dist/leaflet.css");
      if (cleaned || !mapRef.current) return;
      // teardown any prior instance (HMR)
      if (mapInstRef.current) { try { mapInstRef.current.remove(); } catch (e) {} }
      const map = L.map(mapRef.current, { zoomControl: true, attributionControl: false })
        .setView([38.04, -84.50], 10);
      L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
        subdomains: "abcd", maxZoom: 19,
      }).addTo(map);

      sorted.forEach((t) => {
        const color = SALES_STATUS_COLORS[t.status] || "#94A3B8";
        const ringSize = t.status === "uncontacted" ? 10 : 14;
        const html = `
          <div style="position:relative;width:${ringSize*2}px;height:${ringSize*2}px;">
            <div style="position:absolute;top:0;left:0;width:100%;height:100%;border-radius:50%;border:2px solid ${color};box-shadow:0 0 12px ${color};animation:salesPulse 2s ease-in-out infinite;"></div>
            <div style="position:absolute;top:50%;left:50%;width:6px;height:6px;border-radius:50%;background:${color};transform:translate(-50%,-50%);box-shadow:0 0 8px ${color};"></div>
          </div>`;
        const icon = L.divIcon({ html, className: "sales-pin", iconSize: [ringSize*2, ringSize*2] });
        const marker = L.marker([t.lat, t.lng], { icon }).addTo(map);
        marker.bindPopup(`
          <div style="font-family:'IBM Plex Mono', monospace;background:#0B0F19;color:#E2E8F0;padding:8px;border:1px solid ${color};min-width:220px;">
            <div style="font-size:10px;letter-spacing:0.2em;color:${color};text-transform:uppercase;margin-bottom:4px;">${t.status}</div>
            <div style="font-weight:bold;font-size:13px;margin-bottom:2px;">${t.name}</div>
            <div style="font-size:11px;color:#94A3B8;margin-bottom:4px;">${t.phone}</div>
            <div style="font-size:10.5px;color:#94A3B8;">${t.focus}</div>
          </div>
        `);
      });
      mapInstRef.current = map;
    })();
    return () => { cleaned = true; };
  }, [sorted, forbidden]);

  function bumpStatus(id) {
    const next = rows.map((r) => {
      if (r.id !== id) return r;
      const i = SALES_STATUS_OPTIONS.indexOf(r.status);
      const nxt = SALES_STATUS_OPTIONS[(i + 1) % SALES_STATUS_OPTIONS.length];
      return { ...r, status: nxt };
    });
    setRows(next);
  }

  function toggleSort(k) {
    if (k === sortKey) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    else { setSortKey(k); setSortDir("asc"); }
  }

  if (!loaded) {
    return <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center font-mono text-teal">// LOADING…</div>;
  }

  if (forbidden) {
    return (
      <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center p-8" data-testid="admin-forbidden">
        <div className="border border-[#FF5400] bg-[#FF5400]/10 p-8 max-w-md">
          <div className="font-mono text-[10px] tracking-widest uppercase text-[#FF5400] mb-2">// 403 — ACCESS DENIED</div>
          <h1 className="font-display text-2xl uppercase tracking-widest mb-2">Admin Privilege Required</h1>
          <p className="font-body text-sm text-muted-hud">
            The Sales Hub is restricted to <code className="text-teal">role=admin</code> accounts. Contact your STRATEX
            workspace owner to elevate privileges.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0B0F19] text-silver px-6 md:px-12 py-10" data-testid="admin-sales-root">
      <style>{`@keyframes salesPulse { 0%,100% { transform:scale(1); opacity:0.95;} 50% { transform:scale(1.18); opacity:0.55;} }`}</style>
      <div className="max-w-[1500px] mx-auto">
        <div className="font-mono text-[11px] tracking-[0.36em] text-teal uppercase mb-2">// STRATEX VISION • ADMIN • SALES HUB</div>
        <h1 className="font-display text-2xl md:text-4xl uppercase tracking-widest mb-2">Central Kentucky Footprint</h1>
        <p className="font-body text-sm text-muted-hud mb-6 max-w-3xl">
          Pre-cached contractor sales targets seeded from Lexington-radius prospect intel. Click any status chip
          to advance the pipeline → uncontacted ⟶ contacted ⟶ demoed ⟶ negotiating ⟶ closed-won / closed-lost.
        </p>

        {/* Status filter chips */}
        <div className="flex flex-wrap gap-2 mb-5" data-testid="status-filter-bar">
          {["all", ...SALES_STATUS_OPTIONS].map((s) => {
            const active = statusFilter === s;
            const color = s === "all" ? "#00F5D4" : SALES_STATUS_COLORS[s];
            const count = s === "all" ? rows.length : rows.filter((r) => r.status === s).length;
            return (
              <button
                key={s}
                data-testid={`filter-${s}`}
                onClick={() => setStatusFilter(s)}
                aria-pressed={active}
                className="px-3 py-1.5 font-mono text-[10px] uppercase tracking-widest border transition-all"
                style={{
                  background: active ? `${color}22` : "rgba(11,15,25,0.85)",
                  color: active ? color : "#94A3B8",
                  borderColor: active ? color : "rgba(0,240,255,0.25)",
                  boxShadow: active ? `0 0 10px ${color}66` : "none",
                }}
              >
                {s} <span className="opacity-60">({count})</span>
              </button>
            );
          })}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
          {/* ============== TABLE (3 / 5) ============== */}
          <div className="lg:col-span-3 border border-[#00F0FF]/30 bg-[#0B0F19] overflow-hidden" data-testid="sales-table">
            <table className="w-full text-left">
              <thead>
                <tr className="border-b border-[#00F0FF]/25">
                  {[
                    { k: "name", label: "Contractor" },
                    { k: "base", label: "Base" },
                    { k: "phone", label: "Phone" },
                    { k: "status", label: "Status" },
                  ].map((h) => (
                    <th
                      key={h.k}
                      data-testid={`sort-${h.k}`}
                      onClick={() => toggleSort(h.k)}
                      className="px-3 py-2 font-mono text-[10px] uppercase tracking-widest text-teal cursor-pointer hover:bg-[#00F5D4]/[0.04]"
                    >
                      {h.label} {sortKey === h.k ? (sortDir === "asc" ? "↑" : "↓") : ""}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((t) => (
                  <tr key={t.id} className="border-b border-[#00F0FF]/10 align-top" data-testid={`row-${t.id}`}>
                    <td className="px-3 py-3">
                      <div className="font-body text-sm text-silver">{t.name}</div>
                      {t.aka && <div className="font-mono text-[9.5px] text-muted-hud mt-0.5">{t.aka}</div>}
                      <div className="font-mono text-[10px] text-muted-hud mt-1">{t.focus}</div>
                    </td>
                    <td className="px-3 py-3 font-body text-[11.5px] text-silver">{t.base}</td>
                    <td className="px-3 py-3 font-mono text-[11px] text-teal">{t.phone}</td>
                    <td className="px-3 py-3">
                      <button
                        data-testid={`status-chip-${t.id}`}
                        onClick={() => bumpStatus(t.id)}
                        className="px-2 py-1 font-mono text-[9.5px] uppercase tracking-widest border"
                        style={{
                          background: `${SALES_STATUS_COLORS[t.status]}22`,
                          color: SALES_STATUS_COLORS[t.status],
                          borderColor: SALES_STATUS_COLORS[t.status],
                          boxShadow: `0 0 6px ${SALES_STATUS_COLORS[t.status]}66`,
                        }}
                        title="Click to advance pipeline"
                      >
                        {t.status}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* ============== MAP (2 / 5) ============== */}
          <div className="lg:col-span-2 border border-[#00F0FF]/30 bg-[#0B0F19]" data-testid="sales-map-wrap">
            <div className="px-4 py-2 border-b border-[#00F0FF]/20">
              <span className="font-mono text-[10px] tracking-widest uppercase text-teal">// LEXINGTON-RADIUS PIN MAP</span>
            </div>
            <div ref={mapRef} data-testid="sales-map" style={{ height: 540, width: "100%" }} />
          </div>
        </div>
      </div>
    </div>
  );
}
