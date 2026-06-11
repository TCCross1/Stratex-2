/**
 * OpsDashboard — STRATEX™ Phase 2 cockpit (IMG_2541-aligned).
 *
 * Used by BOTH CEO and GM portals. The `portal` prop swaps the endpoint
 * + the header label + sidebar route prefix; the rest of the layout is
 * identical so QXO/ABC/<future supplier> GMs see a properly-scaled
 * version of the exact same cockpit.
 *
 * Layout (top-down, IMG_2541 1:1 reference):
 *   Left sidebar (60px)   ── icon nav (Home/Sales/Fleet/Assets/P&L/Stores/Settings/Help)
 *   Top header            ── STRATEX wordmark + role title + notification + avatar
 *   KPI strip             ── 4 framed neon cards (Scans Completed/Scheduled/Sales Quotes/Closed Sales)
 *   Middle row            ── OPEN JOBS table | Calendar (7-day) | USA Map (Mobile Units)
 *   Bottom row            ── Sales Goal | Fleet Status | Assets | Assets | P&L
 *
 * Brand bible v4.0 (cyan #00E5FF, amber #FFB020, green #00FF9C, magenta #FF2D78).
 */
import React, { useEffect, useState, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  Home, DollarSign, Truck, Package, FileText, Store,
  Settings, HelpCircle, Bell, LogOut, ChevronDown,
  Plane, CloudRain, Cloud, Sun, Zap, Activity, MapPin,
} from "lucide-react";

const C = {
  cyan:    "#00E5FF",
  amber:   "#FFB020",
  green:   "#00FF9C",
  magenta: "#FF2D78",
  purple:  "#C084FC",
  blue:    "#3B82F6",
  text:    "#E2E8F0",
  muted:   "#7C8A9E",
  ink:     "#0A0E1A",
  card:    "#0F1729",
  cardAlt: "#0B1220",
  divider: "#1E293B",
};

const USD = (n) => Number(n || 0).toLocaleString("en-US",
  { style: "currency", currency: "USD", maximumFractionDigits: 0 });

const WeatherIcon = ({ k, size = 18 }) => {
  if (k === "rain")  return <CloudRain size={size} color={C.amber}/>;
  if (k === "cloud") return <Cloud size={size} color={C.muted}/>;
  return <Sun size={size} color={C.amber}/>;
};

const SIDEBAR_ITEMS = [
  { key: "home",     icon: Home,      label: "Home",     path: "" },
  { key: "sales",    icon: DollarSign, label: "Sales",   path: "/sales" },
  { key: "fleet",    icon: Truck,     label: "Fleet",    path: "/fleet" },
  { key: "assets",   icon: Package,   label: "Assets",   path: "/assets" },
  { key: "pnl",      icon: FileText,  label: "P&L Statement", path: "/pnl" },
  { key: "stores",   icon: Store,     label: "Stores",   path: "/suppliers" },
  { key: "settings", icon: Settings,  label: "Settings", path: "/settings" },
  { key: "help",     icon: HelpCircle,label: "Help",     path: "/help" },
];

export default function OpsDashboard({ portal = "ceo" }) {
  const nav = useNavigate();
  const { user, logout } = useAuth();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");

  const endpoint = portal === "ceo" ? "/ops/kpis" : "/ops/kpis/supplier";
  const routePrefix = portal === "ceo" ? "/ceo" : "/admin";
  const headerTitle = portal === "ceo"
    ? "CEO OPERATIONS DASHBOARD"
    : "GM BRANCH OPERATIONS DASHBOARD";

  const load = useCallback(async () => {
    try {
      const { data } = await api.get(endpoint);
      setData(data);
      setErr("");
    } catch (e) {
      setErr(e?.response?.data?.detail || "Unable to load Ops feed");
    }
  }, [endpoint]);
  useEffect(() => { load(); const id = setInterval(load, 30_000); return () => clearInterval(id); }, [load]);

  return (
    <div data-testid={`ops-dashboard-${portal}`}
         style={{ minHeight: "100vh", background: C.ink, color: C.text,
                  display: "grid", gridTemplateColumns: "72px 1fr",
                  fontFamily: "'JetBrains Mono', monospace" }}>

      {/* ============ LEFT SIDEBAR ============ */}
      <aside style={{
        background: "#06080F",
        borderRight: `1px solid ${C.divider}`,
        padding: "16px 0",
        display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
      }}>
        <div style={{
          width: 40, height: 40, borderRadius: 8,
          background: `linear-gradient(135deg, ${C.cyan}, #0891b2)`,
          display: "grid", placeItems: "center", marginBottom: 12,
          boxShadow: `0 0 18px ${C.cyan}99, 0 0 36px ${C.cyan}44`,
          color: "#000", fontWeight: 900, fontSize: 18,
        }}>S</div>
        {SIDEBAR_ITEMS.map(({ key, icon: Icon, label, path }) => (
          <button key={key}
            data-testid={`sidebar-${key}`}
            onClick={() => path && nav(`${routePrefix}${path}`)}
            style={{
              width: 52, padding: "10px 0",
              background: key === "home" ? `${C.cyan}11` : "transparent",
              border: "none",
              borderLeft: key === "home" ? `2px solid ${C.cyan}` : "2px solid transparent",
              color: key === "home" ? C.cyan : C.muted,
              display: "flex", flexDirection: "column", alignItems: "center", gap: 4,
              cursor: "pointer",
              transition: "color 150ms, background 150ms",
            }}
            onMouseEnter={(e)=>{ e.currentTarget.style.color = C.cyan; }}
            onMouseLeave={(e)=>{ if (key !== "home") e.currentTarget.style.color = C.muted; }}>
            <Icon size={18} style={{ filter: key === "home" ? `drop-shadow(0 0 4px ${C.cyan})` : "none" }}/>
            <span style={{ fontSize: 7.5, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              {label.split(" ")[0]}
            </span>
          </button>
        ))}
      </aside>

      {/* ============ MAIN ============ */}
      <main style={{ padding: "20px 24px 60px", overflow: "auto" }}>
        {/* TOP HEADER */}
        <header style={{
          display: "flex", justifyContent: "space-between", alignItems: "center",
          paddingBottom: 18, borderBottom: `1px solid ${C.divider}`,
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <div style={{
              fontFamily: "'Space Grotesk', sans-serif",
              fontSize: 26, fontWeight: 800, color: C.cyan,
              textShadow: `0 0 14px ${C.cyan}88`,
              letterSpacing: "0.04em",
            }}>
              STRATEX
            </div>
            <div style={{ width: 1, height: 24, background: C.divider }}/>
            <div style={{
              fontSize: 13, letterSpacing: "0.18em", color: C.text,
              textTransform: "uppercase", fontWeight: 700,
            }}>
              {headerTitle}
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div data-testid="ops-bell"
                 style={{ position: "relative", color: C.muted, cursor: "pointer" }}>
              <Bell size={18}/>
              <span style={{
                position: "absolute", top: -4, right: -4,
                width: 8, height: 8, borderRadius: "50%",
                background: C.magenta,
                boxShadow: `0 0 8px ${C.magenta}, 0 0 18px ${C.magenta}88`,
              }}/>
            </div>
            <div data-testid="ops-avatar"
                 style={{
                   display: "flex", alignItems: "center", gap: 10,
                   padding: "6px 12px", borderRadius: 22,
                   background: C.cardAlt, border: `1px solid ${C.divider}`,
                   cursor: "pointer",
                 }}>
              <div style={{
                width: 32, height: 32, borderRadius: "50%",
                background: `linear-gradient(135deg, ${C.cyan}, ${C.purple})`,
                display: "grid", placeItems: "center", color: "#000",
                fontWeight: 800, fontSize: 13,
                boxShadow: `0 0 10px ${C.cyan}55`,
              }}>
                {(user?.legal_name || user?.email || "U")[0]?.toUpperCase()}
              </div>
              <div>
                <div style={{ fontSize: 12, fontWeight: 700 }}>
                  {user?.legal_name || user?.email?.split("@")[0] || "Operator"}
                </div>
                <div style={{ fontSize: 9, color: C.muted, letterSpacing: "0.18em",
                              textTransform: "uppercase" }}>
                  ({(user?.role || "ceo").toUpperCase()})
                </div>
              </div>
              <ChevronDown size={14} color={C.muted}/>
            </div>
            <button onClick={logout} data-testid="ops-logout"
                    style={{
                      background: "transparent", border: `1px solid ${C.divider}`,
                      color: C.muted, padding: "6px 10px", borderRadius: 4,
                      fontSize: 10, letterSpacing: "0.18em", cursor: "pointer",
                      textTransform: "uppercase",
                    }}>
              <LogOut size={11} style={{ verticalAlign: -1, marginRight: 4 }}/>
              Sign out
            </button>
          </div>
        </header>

        {err && (
          <div style={{
            margin: "14px 0", padding: "10px 14px",
            background: `${C.magenta}11`, border: `1px solid ${C.magenta}55`,
            color: C.magenta, fontSize: 11,
          }}>
            {err}
          </div>
        )}

        {/* ============ KPI STRIP (4 framed neon cards) ============ */}
        <section style={{
          display: "grid", gap: 14, marginTop: 18,
          gridTemplateColumns: "repeat(4, 1fr)",
        }}>
          <KpiCard testid="kpi-scans-completed"
            label="Scans Completed:"
            value={data?.kpis?.scans_completed?.value || "—"}
            sub={data?.kpis?.scans_completed?.subtitle || ""}
            color={C.cyan} delta={data?.kpis?.scans_completed?.delta_pct}/>
          <KpiCard testid="kpi-scans-scheduled"
            label="Scans Scheduled:"
            value={data?.kpis?.scans_scheduled?.value || "—"}
            sub={data?.kpis?.scans_scheduled?.subtitle || "This Month"}
            color={C.magenta}/>
          <KpiCard testid="kpi-sales-quotes"
            label="Sales Quotes:"
            value={data?.kpis?.sales_quotes?.value || "—"}
            sub={data?.kpis?.sales_quotes?.subtitle || ""}
            color={C.blue}/>
          <KpiCard testid="kpi-closed-sales"
            label="Closed Sales:"
            value={data?.kpis?.closed_sales?.value || "—"}
            sub={data?.kpis?.closed_sales?.subtitle || ""}
            color={C.green}/>
        </section>

        {/* ============ MIDDLE ROW: jobs | calendar | map ============ */}
        <section style={{
          display: "grid", gap: 14, marginTop: 14,
          gridTemplateColumns: "minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.05fr)",
        }}>
          <OpenJobsCard jobs={data?.open_jobs || []}/>
          <CalendarCard week={data?.calendar || []}/>
          <FleetMapCard pins={data?.fleet || []} summary={data?.fleet_summary}/>
        </section>

        {/* ============ BOTTOM ROW: sales goal | fleet | assets | P&L ============ */}
        <section style={{
          display: "grid", gap: 14, marginTop: 14,
          gridTemplateColumns: "minmax(0, 2.4fr) repeat(4, minmax(0, 1fr))",
        }}>
          <SalesGoalCard goal={data?.sales_goal}/>
          <MiniStatCard testid="ministat-fleet" color={C.cyan}
            title="Fleet Status"
            big={`${data?.fleet_summary?.units_active || 0} Units Active/${data?.fleet_summary?.units_idle || 0} Idle`}/>
          <MiniStatCard testid="ministat-assets-1" color={C.purple}
            title="Assets"
            big={data?.fleet_summary?.total_assets || "2 Drones, 4 Units"}/>
          <MiniStatCard testid="ministat-assets-2" color={C.purple}
            title="Assets"
            big={data?.fleet_summary?.total_assets || "2 Drones, 4 Units"}/>
          <MiniStatCard testid="ministat-pnl" color={C.magenta}
            title="P&L Statement"
            big={`Profit: ${USD(data?.fleet_summary?.month_profit_usd || 125000)}`}/>
        </section>
      </main>

      <style>{`
        ::-webkit-scrollbar { width: 8px; height: 8px; }
        ::-webkit-scrollbar-thumb { background: ${C.divider}; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: ${C.cyan}55; }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// KPI tile
// ---------------------------------------------------------------------------
function KpiCard({ label, value, sub, color, delta, testid }) {
  return (
    <div data-testid={testid}
         style={{
           background: C.card,
           border: `2px solid ${color}`,
           borderRadius: 8,
           padding: "14px 18px",
           boxShadow: `0 0 0 1px ${color}22 inset, 0 0 24px ${color}33, 0 22px 50px -28px ${color}66`,
           position: "relative",
           minHeight: 110,
         }}>
      <div style={{
        color, fontSize: 11, fontWeight: 700,
        letterSpacing: "0.06em", textTransform: "uppercase",
        textShadow: `0 0 10px ${color}`,
        marginBottom: 4,
      }}>
        {label}
      </div>
      <div style={{
        color: "#FFFFFF", fontSize: 36, fontWeight: 800, letterSpacing: "0.02em",
        textShadow: `0 0 14px rgba(255,255,255,0.22)`,
        fontVariantNumeric: "tabular-nums",
        lineHeight: 1.05,
        marginTop: 4,
      }}>
        {typeof value === "number" ? value.toLocaleString() : value}
      </div>
      <div style={{ color: C.muted, fontSize: 11, marginTop: 6 }}>
        {sub}
        {delta != null && (
          <span style={{ color: delta >= 0 ? C.green : C.magenta, marginLeft: 6, fontWeight: 700 }}>
            {delta >= 0 ? "+" : ""}{delta}%
          </span>
        )}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Open Jobs card
// ---------------------------------------------------------------------------
function OpenJobsCard({ jobs }) {
  return (
    <Panel testid="openjobs-card" border={C.cyan} title="OPEN JOBS" subtitle="(Pending Closures)">
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 11 }}>
        <thead>
          <tr style={{ color: C.muted, textAlign: "left", letterSpacing: "0.1em",
                       textTransform: "uppercase", fontSize: 9.5 }}>
            <th style={th()}>Job #</th>
            <th style={th()}>Client Address</th>
            <th style={th({ textAlign: "right" })}>Quote $</th>
            <th style={th()}>Date Quoted</th>
            <th style={th()}>Status</th>
          </tr>
        </thead>
        <tbody>
          {jobs.map((j, i) => (
            <tr key={i} data-testid={`job-row-${i}`}
                style={{ borderTop: `1px solid ${C.divider}` }}>
              <td style={td({ color: C.cyan })}>{j.job_id}</td>
              <td style={td()}>{j.client_address}</td>
              <td style={td({ textAlign: "right", color: C.green })}>{USD(j.quote_usd)}</td>
              <td style={td({ color: C.muted })}>{j.date_quoted}</td>
              <td style={td()}>
                <span style={{
                  color: statusColor(j.status), fontSize: 10,
                  letterSpacing: "0.04em",
                }}>{j.status}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Panel>
  );
}
const th = (extra) => ({ padding: "6px 4px", fontWeight: 600, ...(extra||{}) });
const td = (extra) => ({ padding: "9px 4px", ...(extra||{}) });
const statusColor = (s) => {
  const k = (s || "").toLowerCase();
  if (k.includes("invoice")) return C.amber;
  if (k.includes("review"))  return C.cyan;
  return C.muted;
};

// ---------------------------------------------------------------------------
// Calendar card
// ---------------------------------------------------------------------------
function CalendarCard({ week }) {
  const today = new Date().toISOString().slice(0, 10);
  return (
    <Panel testid="calendar-card" border={C.purple} title="Scan Scheduling Calendar">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center",
                    marginBottom: 8 }}>
        <div style={{ color: C.text, fontSize: 12, fontWeight: 700, letterSpacing: "0.06em" }}>
          {week.length ? new Date(week[0].date_iso).toLocaleString("en-US",
            { month: "long", year: "numeric" }) : "—"}
        </div>
        <button style={{
          background: "transparent", border: `1px solid ${C.divider}`,
          color: C.muted, padding: "4px 10px", borderRadius: 3,
          fontSize: 10, letterSpacing: "0.1em", cursor: "pointer",
        }}>Today</button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(7, 1fr)", gap: 4 }}>
        {week.map((d) => {
          const isToday = d.date_iso === today;
          return (
            <div key={d.date_iso}
                 data-testid={`cal-day-${d.day_short}`}
                 style={{
                   background: isToday ? `${C.cyan}15` : "transparent",
                   border: `1px solid ${isToday ? C.cyan : C.divider}`,
                   borderRadius: 4,
                   padding: "6px 4px",
                   minHeight: 86,
                   boxShadow: isToday ? `0 0 14px ${C.cyan}33` : "none",
                 }}>
              <div style={{ fontSize: 9, color: C.muted, letterSpacing: "0.1em" }}>{d.day_short}</div>
              <div style={{ fontSize: 14, fontWeight: 700, color: isToday ? C.cyan : C.text }}>
                {d.month_short} {d.day_num}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 4, marginTop: 6 }}>
                <WeatherIcon k={d.weather} size={12}/>
                <span style={{ fontSize: 9, color: C.muted }}>{d.wind_mph} mph</span>
              </div>
              <div style={{ fontSize: 9, color: d.scan_count ? C.green : C.muted, marginTop: 4 }}>
                {d.scan_count ? `${d.scan_count} scan${d.scan_count === 1 ? "" : "s"}` : "—"}
              </div>
            </div>
          );
        })}
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Fleet Map card — USA SVG with pulsing dots + detail card
// ---------------------------------------------------------------------------
const USA_VB = { w: 460, h: 280 };
// rough lat/lng → SVG mapping (continental US bbox)
function llToXY(lat, lng) {
  const W = -125, E = -66, N = 50, S = 24;
  const x = ((lng - W) / (E - W)) * USA_VB.w;
  const y = ((N - lat) / (N - S)) * USA_VB.h;
  return [x, y];
}
function FleetMapCard({ pins, summary }) {
  const [hover, setHover] = useState(null);
  return (
    <Panel testid="fleet-map-card" border={C.blue} title="Mobile Units | USA Map">
      <svg viewBox={`0 0 ${USA_VB.w} ${USA_VB.h}`}
           style={{ width: "100%", height: 230, background: "#070B14",
                    border: `1px solid ${C.divider}`, borderRadius: 4 }}>
        {/* Subtle USA outline (rough silhouette) */}
        <path d="M40 70 L120 50 L210 50 L300 60 L380 70 L420 100 L415 160 L380 200 L320 220 L250 230 L180 230 L110 220 L60 180 L40 130 Z"
              fill="#0E1729" stroke={`${C.cyan}22`} strokeWidth="1"/>
        {/* Pulsing pins */}
        {pins.map((p, i) => {
          const [x, y] = llToXY(p.lat, p.lng);
          return (
            <g key={i} onMouseEnter={()=>setHover(p)} onMouseLeave={()=>setHover(null)}
               style={{ cursor: "pointer" }}>
              <circle cx={x} cy={y} r={8} fill={`${C.cyan}33`}>
                <animate attributeName="r" values="6;14;6" dur="2.2s" repeatCount="indefinite"/>
                <animate attributeName="opacity" values="0.4;0.1;0.4" dur="2.2s" repeatCount="indefinite"/>
              </circle>
              <circle cx={x} cy={y} r="3.5" fill={C.cyan}
                      style={{ filter: `drop-shadow(0 0 6px ${C.cyan})` }}/>
            </g>
          );
        })}
      </svg>

      {hover && (
        <div data-testid="fleet-map-detail"
             style={{
               marginTop: 8, padding: "10px 12px",
               background: C.cardAlt, border: `1px solid ${C.cyan}55`,
               borderRadius: 4, fontSize: 11,
               boxShadow: `0 0 18px ${C.cyan}33`,
             }}>
          <div style={{ color: C.cyan, fontWeight: 800, fontSize: 13,
                        textShadow: `0 0 8px ${C.cyan}` }}>
            {hover.city} ({hover.units} Units Active)
          </div>
          <div style={{ color: C.text, fontSize: 11, marginTop: 4 }}>
            Mobile Unit #{Math.floor(Math.random()*9)+1} · Progression: <span style={{ color: C.cyan }}>{hover.phase}</span>
          </div>
          <div style={{ display: "flex", gap: 10, marginTop: 6, color: C.muted, fontSize: 9 }}>
            <span><Truck size={10}/> Transit</span>
            <span>→</span>
            <span><Activity size={10}/> Assessment</span>
            <span>→</span>
            <span><Plane size={10}/> In Flight</span>
            <span>→</span>
            <span><Zap size={10}/> Data Transfer</span>
            <span>→</span>
            <span><MapPin size={10}/> Landing</span>
          </div>
        </div>
      )}
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Sales Goal card (progress bar)
// ---------------------------------------------------------------------------
function SalesGoalCard({ goal }) {
  const pct = goal?.progress_pct || 0;
  return (
    <Panel testid="salesgoal-card" border={C.green} title="Sales Goal: Mobile Unit Addition">
      <div style={{ display: "flex", justifyContent: "space-between",
                    alignItems: "center", marginBottom: 8 }}>
        <span style={{ color: C.muted, fontSize: 11 }}>
          {USD(goal?.captured_usd || 0)} / {USD(goal?.target_usd || 750000)}
        </span>
        <span style={{ color: C.green, fontSize: 11, fontWeight: 700,
                       textShadow: `0 0 8px ${C.green}` }}>
          {goal?.footnote || `${pct}% to next MDU`}
        </span>
      </div>
      <div style={{
        width: "100%", height: 10, background: `${C.green}22`,
        borderRadius: 5, overflow: "hidden",
      }}>
        <div data-testid="salesgoal-bar"
             style={{
               width: `${Math.min(100, pct)}%`, height: "100%",
               background: `linear-gradient(90deg, ${C.cyan}, ${C.green})`,
               boxShadow: `0 0 18px ${C.green}, 0 0 28px ${C.cyan}66`,
               transition: "width 0.6s ease",
             }}/>
      </div>
      <div style={{ marginTop: 8, color: C.muted, fontSize: 10, letterSpacing: "0.1em" }}>
        {pct}% to Next Unit
      </div>
    </Panel>
  );
}

// ---------------------------------------------------------------------------
// Mini stat card (bottom row 4-up)
// ---------------------------------------------------------------------------
function MiniStatCard({ title, big, color, testid }) {
  return (
    <div data-testid={testid}
         style={{
           background: C.card,
           border: `2px solid ${color}`,
           borderRadius: 6,
           padding: "10px 14px",
           boxShadow: `0 0 16px ${color}22, 0 0 0 1px ${color}22 inset`,
         }}>
      <div style={{
        color, fontSize: 9.5, fontWeight: 700,
        letterSpacing: "0.18em", textTransform: "uppercase",
        textShadow: `0 0 8px ${color}`,
      }}>{title}</div>
      <div style={{ color: C.text, fontSize: 12, fontWeight: 700, marginTop: 4 }}>
        {big}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Shared panel wrapper
// ---------------------------------------------------------------------------
function Panel({ children, title, subtitle, border, testid }) {
  return (
    <section data-testid={testid}
             style={{
               background: C.card,
               border: `1px solid ${border}55`,
               borderRadius: 8,
               padding: "12px 16px",
               minWidth: 0,
               boxShadow: `0 0 0 1px ${border}11 inset, 0 22px 50px -30px ${border}55`,
             }}>
      <div style={{ display: "flex", alignItems: "baseline", gap: 8, marginBottom: 8 }}>
        <h3 style={{
          color: border, fontSize: 11, fontWeight: 700,
          letterSpacing: "0.18em", textTransform: "uppercase",
          textShadow: `0 0 10px ${border}`,
          margin: 0,
        }}>{title}</h3>
        {subtitle && (
          <span style={{ color: C.muted, fontSize: 10, letterSpacing: "0.1em" }}>
            {subtitle}
          </span>
        )}
      </div>
      {children}
    </section>
  );
}
