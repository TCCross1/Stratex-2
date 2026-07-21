// frontend/src/components/OpsDashboard.jsx
// STRATEX MASTER EXECUTIVE COMMAND CENTER (CENTCOM)
// PURPOSE: GLOBAL OPERATIONAL WORKSPACE & REAL-TIME STRATEGIC COCKPIT (DIRECTIVE 009)

import React, { useState, useEffect, useMemo, useRef } from "react";
import { Link } from "react-router-dom";
import {
  Activity, Shield, ShieldCheck, AlertCircle, AlertTriangle, Info, Clock,
  DollarSign, Calendar, MapPin, Search, Plus, Filter, RefreshCw, BarChart2,
  TrendingUp, Layers, CheckCircle, Eye, Check, X, FileText, Cpu, Server,
  Database, Globe, Play, Pause, ChevronRight, ChevronDown, User, Users,
  Clipboard, Layers3, Radio, HardDrive, HelpCircle, Wind, Droplet, Sun,
  Sparkles, Send, Trash, Briefcase, Award, Wifi, Terminal, Zap, ShieldAlert
} from "lucide-react";
import {
  ResponsiveContainer, AreaChart, Area, BarChart, Bar, LineChart, Line,
  XAxis, YAxis, Tooltip, Legend, CartesianGrid, PieChart, Pie, Cell
} from "recharts";
import {
  nxOverview, nxHealth, nxMe, nxListProperties, nxListMissions, nxAudit
} from "@/nextgen/api";
import { toast } from "sonner";

// ─────────────────────────────────────────────────────────────────────
// CONSTANTS & SEED DATA (Failsafe & Premium Content)
// ─────────────────────────────────────────────────────────────────────

const REGIONS = ["ALL", "WEST", "EAST", "SOUTH", "CENTRAL"];

const ACCENT_COLORS = {
  cyan: "#00F2FE",
  orange: "#FF5400",
  gold: "#FFB020",
  green: "#00FF9C",
  crimson: "#FF2D78",
  slate: "#6D7B8F",
};

const INITIAL_ALERTS = [
  { id: "alt-1", category: "Critical", source: "AI", title: "Sub-surface Moisture Anomaly", text: "Severe moisture entrapment (>85% mass saturation) detected on Facet 3 of PR-8820 (Seattle Terminal). AI confidence 94.2%.", at: "01:12:45", status: "New", assignedTo: null },
  { id: "alt-2", category: "Warning", source: "Weather", title: "Approaching High Wind Advisory", text: "Doppler radar shows wind shear (>22 knots) heading toward Lexington, KY. Active drone flights suspended.", at: "01:08:12", status: "New", assignedTo: null },
  { id: "alt-3", category: "Security", source: "Property", title: "Unauthorized Geofence Breach", text: "Ground-level GPS signal detected inside FAA restricted buffer Zone-B for Atlanta operations.", at: "00:55:01", status: "Acknowledged", assignedTo: "Operator Delta" },
  { id: "alt-4", category: "Operational", source: "Fleet", title: "MDU Solar Core Low Voltage", text: "Unit 3 trailer solar charging efficiency below 18% due to overcast canopy. Backup battery engaged.", at: "00:42:19", status: "New", assignedTo: null },
  { id: "alt-5", category: "Mission", source: "Mission", title: "Payload Transmission Delay", text: "Mission MS-4902 failed to finalize. Raw imagery uploads retrying from Field Rig 2. Link speed: 2.1 Mbps.", at: "00:30:10", status: "Resolved", assignedTo: "Sarah Jenkins" },
  { id: "alt-6", category: "AI", source: "AI", title: "Consensus Divergence Detected", text: "Moisture Agent & Pitch Agent disagree on structural deterioration factor on PR-912. Pending Human Review.", at: "00:15:33", status: "New", assignedTo: null },
];

const INITIAL_TIMELINE = [
  { id: "t-1", type: "MISSION_STARTED", text: "Mission MS-4921 initialized autonomously", region: "WEST", operator: "Unit 3 (DJI M3TD)", at: "01:28:10", details: "Target: 742 Maple St, Seattle. Solar grid charging optimal." },
  { id: "t-2", type: "PASSPORT_UPDATED", text: "Property Passport DNA updated for PR-104", region: "EAST", operator: "System Engine", at: "01:20:45", details: "Hardened write path secured: v4.1 DNA schema appended with thermal radiometric layer." },
  { id: "t-3", type: "AI_REVIEW", text: "AI Validation completed: 5/5 Consensus", region: "WEST", operator: "AI Consensus Board", at: "01:15:00", details: "Thermal scan analysis approved. Radiometric mass match: 98.7% confidence." },
  { id: "t-4", type: "REPORT_PUBLISHED", text: "Structural Integrity Report published", region: "CENTRAL", operator: "Doug Piercy (CEO)", at: "01:02:15", details: "PDF published and SHA-256 ledgered. Co-sign status: ACTIVE." },
  { id: "t-5", type: "CONTRACT_SIGNED", text: "Commercial Roofing Contract signed", region: "SOUTH", operator: "Apex Roofing Group", at: "00:48:30", details: "Project: Atlanta Terminal. Valuation: $184,500.00 MTD pipeline credit." },
  { id: "t-6", type: "WARRANTY_REGISTERED", text: "GAF Golden Pledge Warranty Registered", region: "EAST", operator: "Homeowner Portal", at: "00:35:12", details: "Registered for PR-218 Pine Ave. Duration: 25 years full coverage." },
  { id: "t-7", type: "CONTRACTOR_ASSIGNED", text: "Contractor assigned to repair sequence", region: "WEST", operator: "System Dispatcher", at: "00:22:40", details: "Apex Team B dispatched to 742 Maple St for moisture extraction." },
  { id: "t-8", type: "PROPERTY_UPDATED", text: "New property identity resolved & registered", region: "SOUTH", operator: "Regional Switchboard", at: "00:10:05", details: "Resolved 218 Pine Ave, Atlanta. Structural footprint: 14,200 sq ft." },
  { id: "t-9", type: "MISSION_COMPLETED", text: "Mission MS-3810 aerial capture finalized", region: "CENTRAL", operator: "Sarah Jenkins", at: "23:45:00", details: "128 raw radiometric files successfully uploaded to storage pool." },
  { id: "t-10", type: "CRITICAL_FINDING", text: "Critical moisture risk escalation ledgered", region: "WEST", operator: "Moisture Agent v2", at: "23:15:22", details: "Classified as CRITICAL moisture intrusion. Emergency mitigation suggested." },
];

const MAP_LOCATIONS = [
  { id: "loc-1", type: "Property", name: "Seattle Terminal (PR-8820)", lat: 47.61, lng: -122.33, region: "WEST", status: "Critical Anomaly", value: "$4.2M Asset", label: "742 Maple St, Seattle" },
  { id: "loc-2", type: "Mission", name: "Mission MS-4921 Flight Path", lat: 47.63, lng: -122.35, region: "WEST", status: "Active (In Flight)", value: "DJI M3TD Telemetry", label: "Scanning Zone C" },
  { id: "loc-3", type: "Operator", name: "Sarah Jenkins Mobile Unit", lat: 45.51, lng: -122.68, region: "WEST", status: "On-site / Transit", value: "Signal Encryped", label: "Portland, OR Sector" },
  { id: "loc-4", type: "Contractor", name: "Apex Roofing Group HQ", lat: 33.74, lng: -84.39, region: "SOUTH", status: "Contractor Assigned", value: "A-Class Partner", label: "Atlanta, GA Hub" },
  { id: "loc-5", type: "Fleet", name: "MDU-3 Autonomous Trailer", lat: 38.04, lng: -84.50, region: "CENTRAL", status: "Charging Core", value: "Starlink Active", label: "Lexington, KY" },
  { id: "loc-6", type: "Property", name: "Lexington Plaza (PR-104)", lat: 38.06, lng: -84.48, region: "CENTRAL", status: "Optimal Health", value: "$1.8M Asset", label: "120 Oak Rd, Lexington" },
  { id: "loc-7", type: "Fleet", name: "MDU-1 Autonomous Trailer", lat: 32.78, lng: -96.80, region: "CENTRAL", status: "Standby Mode", value: "GPS Locked", label: "Dallas, TX Depot" },
  { id: "loc-8", type: "Property", name: "Miami Terminal (PR-218)", lat: 25.76, lng: -80.19, region: "EAST", status: "Pending Review", value: "$3.5M Asset", label: "218 Pine Ave, Miami" },
];

const ANALYTICS_REVENUE = [
  { month: "Jan", Revenue: 210000, Forecast: 220000 },
  { month: "Feb", Revenue: 245000, Forecast: 250000 },
  { month: "Mar", Revenue: 285400, Forecast: 300000 },
  { month: "Apr", Revenue: 340000, Forecast: 350000 },
  { month: "May", Revenue: 412000, Forecast: 400000 },
  { month: "Jun", Revenue: 498000, Forecast: 480000 },
  { month: "Jul", Revenue: 585000, Forecast: 570000 },
];

const ANALYTICS_MISSIONS = [
  { week: "Wk 25", Completed: 12, Scheduled: 14, Delayed: 2 },
  { week: "Wk 26", Completed: 18, Scheduled: 16, Delayed: 1 },
  { week: "Wk 27", Completed: 22, Scheduled: 20, Delayed: 0 },
  { week: "Wk 28", Completed: 29, Scheduled: 24, Delayed: 3 },
  { week: "Wk 29", Completed: 35, Scheduled: 30, Delayed: 4 },
  { week: "Wk 30", Completed: 42, Scheduled: 35, Delayed: 2 },
];

const ANALYTICS_PARTNERS = [
  { name: "Apex Roofing", Projects: 18, Efficiency: 96, Revenue: 145000 },
  { name: "Southeastern", Projects: 12, Efficiency: 92, Revenue: 98000 },
  { name: "Northwest Storm", Projects: 14, Efficiency: 95, Revenue: 120000 },
  { name: "CVIce Shield", Projects: 8, Efficiency: 98, Revenue: 64000 },
  { name: "Texas Diagnostic", Projects: 11, Efficiency: 89, Revenue: 78000 },
];

const ANALYTICS_OPERATORS = [
  { name: "Sarah Jenkins", Scans: 48, Reliability: 99.4, Status: "Active" },
  { name: "Marcus Brody", Scans: 36, Reliability: 98.2, Status: "Standby" },
  { name: "Elena Rostova", Scans: 42, Reliability: 99.1, Status: "Transit" },
  { name: "James Vance", Scans: 28, Reliability: 95.6, Status: "On Leave" },
];

// ─────────────────────────────────────────────────────────────────────
// COMPONENT MAIN EXPORT
// ─────────────────────────────────────────────────────────────────────

export default function OpsDashboard({ portal = "ceo" }) {
  const [activeTab, setActiveTab] = useState("overview");
  const [selectedRegion, setSelectedRegion] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [simulationActive, setSimulationActive] = useState(true);
  const [liveClock, setLiveClock] = useState("");
  const [tickerIndex, setTickerIndex] = useState(0);

  // Live state managers initialized with our heavy datasets
  const [alerts, setAlerts] = useState(INITIAL_ALERTS);
  const [timeline, setTimeline] = useState(INITIAL_TIMELINE);
  const [mapPins, setMapPins] = useState(MAP_LOCATIONS);
  const [mapLayers, setMapLayers] = useState({
    weather: true,
    airspace: true,
    risk: true,
  });

  // Map focus target for click-to-center zoom mechanics
  const [focusedPin, setFocusedPin] = useState(null);

  // NextGen DB variables loaded from endpoints when available
  const [liveData, setLiveData] = useState({
    overview: null,
    health: null,
    properties: [],
    missions: [],
    audit: [],
    me: null,
  });
  const [loading, setLoading] = useState(true);

  // ─────────────────────────────────────────────────────────────────────
  // TIME & TICKER CLOCK EFFECT
  // ─────────────────────────────────────────────────────────────────────
  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setLiveClock(now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }));
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // ─────────────────────────────────────────────────────────────────────
  // API INGEST MECHANICS (Merge NextGen & Failsafe Mock)
  // ─────────────────────────────────────────────────────────────────────
  const loadNextGenData = async () => {
    try {
      const [ov, h, props, miss, aud, m] = await Promise.all([
        nxOverview().catch(() => null),
        nxHealth().catch(() => null),
        nxListProperties().catch(() => null),
        nxListMissions().catch(() => null),
        nxAudit().catch(() => null),
        nxMe().catch(() => null),
      ]);

      setLiveData({
        overview: ov,
        health: h,
        properties: props?.items || [],
        missions: miss?.items || [],
        audit: aud?.items || [],
        me: m,
      });
    } catch (err) {
      console.warn("[CENTCOM] NextGen API fallback engaged.", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadNextGenData();
  }, []);

  // ─────────────────────────────────────────────────────────────────────
  // LIVE FEED SIMULATOR (Task 13 - Standardized Event Emitter)
  // ─────────────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!simulationActive) return;

    const interval = setInterval(() => {
      // Rotate through a series of dynamic real-world platform events
      const simEvents = [
        {
          type: "MISSION_COMPLETED",
          text: "Mission MS-7201 aerial scan completed successfully",
          region: "WEST",
          operator: "Elena Rostova",
          details: "Volumetric moisture mapping fully calibrated against 3D roof plane.",
        },
        {
          type: "PASSPORT_UPDATED",
          text: "Durable Property Passport updated: PR-9401",
          region: "SOUTH",
          operator: "System Outbox",
          details: "Contractor Apex assigned to dispatch pipeline. DNA index recalibrated.",
        },
        {
          type: "CRITICAL_FINDING",
          text: "Critical Sub-surface Saturation Breach: PR-104",
          region: "CENTRAL",
          operator: "Moisture AI Agent",
          details: "Mass volume anomaly exceeding standard threshold. Localized deterioration risk registered.",
        },
        {
          type: "REPORT_PUBLISHED",
          text: "Certified Insurance Diagnostic report exported",
          region: "EAST",
          operator: "Doug Piercy (CEO)",
          details: "Verification token generated. Double SHA-256 registered to blockchain.",
        },
        {
          type: "AI_REVIEW",
          text: "AI Processing Queue: Multi-agent consensus achieved",
          region: "WEST",
          operator: "Platform Intelligence",
          details: "Radiometric verification matches visual facet edge limits. Precision score: 99.8%.",
        },
      ];

      const currentSimEvent = simEvents[tickerIndex % simEvents.length];
      const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false });
      
      // Emit standardized Event model per Task 13 directive
      const newEventId = `sim-ev-${Date.now()}`;
      const newEvent = {
        id: newEventId,
        type: currentSimEvent.type,
        text: currentSimEvent.text,
        region: currentSimEvent.region,
        operator: currentSimEvent.operator,
        at: timeStr,
        details: currentSimEvent.details,
      };

      setTimeline((prev) => [newEvent, ...prev.slice(0, 15)]);

      // Occasionally trigger corresponding Alert per Task 8
      if (Math.random() > 0.4) {
        const isCritical = currentSimEvent.type === "CRITICAL_FINDING";
        const newAlert = {
          id: `sim-alt-${Date.now()}`,
          category: isCritical ? "Critical" : "Warning",
          source: isCritical ? "AI" : "Mission",
          title: isCritical ? "Critical Wet Insulation Detected" : "Telemetry Transmission Alert",
          text: `Event reference: ${currentSimEvent.text}. Operator dispatched: ${currentSimEvent.operator}`,
          at: timeStr,
          status: "New",
          assignedTo: null,
        };
        setAlerts((prev) => [newAlert, ...prev.slice(0, 10)]);
        toast.error(`CENTCOM ALERT: ${newAlert.title}`, {
          description: newAlert.text,
          duration: 4000,
        });
      } else {
        toast.info(`Platform Event: ${currentSimEvent.type}`, {
          description: currentSimEvent.text,
          duration: 3000,
        });
      }

      setTickerIndex((prev) => prev + 1);
    }, 9000);

    return () => clearInterval(interval);
  }, [simulationActive, tickerIndex]);

  // ─────────────────────────────────────────────────────────────────────
  // INTERACTIVE HANDLERS (Task 8 - Alert State Machine)
  // ─────────────────────────────────────────────────────────────────────
  const handleAcknowledgeAlert = (id) => {
    setAlerts((prev) =>
      prev.map((alt) =>
        alt.id === id ? { ...alt, status: "Acknowledged", assignedTo: "Executive Dispatch" } : alt
      )
    );
    toast.success("Alert Acknowledged by CENTCOM");
  };

  const handleAssignAlert = (id, personnel) => {
    setAlerts((prev) =>
      prev.map((alt) =>
        alt.id === id ? { ...alt, status: "Assigned", assignedTo: personnel } : alt
      )
    );
    toast.success(`Alert Assigned to ${personnel}`);
  };

  const handleResolveAlert = (id) => {
    setAlerts((prev) =>
      prev.map((alt) =>
        alt.id === id ? { ...alt, status: "Resolved" } : alt
      )
    );
    toast.success("Alert Marked as Resolved");
  };

  const handleArchiveAlert = (id) => {
    setAlerts((prev) =>
      prev.map((alt) =>
        alt.id === id ? { ...alt, status: "Archived" } : alt
      )
    );
    toast("Alert Moved to Archives");
  };

  // ─────────────────────────────────────────────────────────────────────
  // FILTER MECHANICS (Region & Search)
  // ─────────────────────────────────────────────────────────────────────
  const filteredTimeline = useMemo(() => {
    return timeline.filter((item) => {
      const regionMatch = selectedRegion === "ALL" || item.region.toUpperCase() === selectedRegion;
      const searchMatch = !searchQuery || 
        item.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.type.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.operator.toLowerCase().includes(searchQuery.toLowerCase());
      return regionMatch && searchMatch;
    });
  }, [timeline, selectedRegion, searchQuery]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((item) => {
      if (item.status === "Archived") return false; // Hide archived from main inbox
      const searchMatch = !searchQuery || 
        item.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.text.toLowerCase().includes(searchQuery.toLowerCase()) ||
        item.category.toLowerCase().includes(searchQuery.toLowerCase());
      return searchMatch;
    });
  }, [alerts, searchQuery]);

  const filteredPins = useMemo(() => {
    return mapPins.filter((pin) => {
      const regionMatch = selectedRegion === "ALL" || pin.region.toUpperCase() === selectedRegion;
      const searchMatch = !searchQuery ||
        pin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        pin.status.toLowerCase().includes(searchQuery.toLowerCase()) ||
        pin.label.toLowerCase().includes(searchQuery.toLowerCase());
      return regionMatch && searchMatch;
    });
  }, [mapPins, selectedRegion, searchQuery]);

  // ─────────────────────────────────────────────────────────────────────
  // SUB-COMPONENT: METRIC CARD
  // ─────────────────────────────────────────────────────────────────────
  const MetricCard = ({ title, value, sub, trend, trendColor, labelColor = "text-[#6D7B8F]" }) => {
    return (
      <div className="bg-[#0D121F] border border-[#1A2333] hover:border-[#00F2FE]/40 transition rounded-lg p-5 flex flex-col justify-between relative overflow-hidden group">
        <span className="absolute top-0 left-0 w-2 h-0.5 bg-[#00F2FE] group-hover:w-full transition-all duration-300" />
        <div>
          <div className={`font-mono text-[10px] tracking-widest uppercase ${labelColor}`}>{title}</div>
          <div className="font-sans text-2xl font-bold tracking-tight text-white mt-1 group-hover:text-[#00F2FE] transition-colors">{value}</div>
        </div>
        <div className="flex items-center justify-between mt-3 pt-2 border-t border-[#161F2E]">
          <span className="text-[11px] text-[#6D7B8F] font-mono">{sub}</span>
          {trend && (
            <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${trendColor || "text-[#00FF9C] bg-[#00FF9C]/10 border-[#00FF9C]/20"}`}>
              {trend}
            </span>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-[#070A13] text-[#A0AEC0] font-sans overflow-x-hidden antialiased">
      {/* ── CENTRALIZED EVENT ARCHITECTURE BANNER (Task 13) ── */}
      <div className="bg-[#10141D] border-b border-[#00F2FE]/15 px-4 sm:px-6 py-2 flex flex-col md:flex-row items-center justify-between gap-2.5">
        <div className="flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[#00FF9C] opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-[#00FF9C]"></span>
          </span>
          <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-white font-semibold">
            CENTCOM ACTIVE NODE: DIRECTIVE-009 SPECIFICATION
          </span>
        </div>
        <div className="flex items-center gap-4 text-[10.5px] font-mono">
          <span className="text-[#6D7B8F]">WORKSPACE FEED: <strong className="text-white">EVENT-DRIVEN (OUTBOX)</strong></span>
          <div className="flex items-center gap-2 border-l border-[#1F2937] pl-4">
            <span className="text-[#6D7B8F]">SIMULATOR STATUS</span>
            <button
              onClick={() => setSimulationActive(!simulationActive)}
              className={`px-2 py-0.5 rounded text-[9.5px] uppercase font-bold tracking-wider transition ${
                simulationActive 
                  ? "bg-[#00FF9C]/10 text-[#00FF9C] border border-[#00FF9C]/30 hover:bg-[#00FF9C]/25" 
                  : "bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/25"
              }`}
            >
              {simulationActive ? "LIVE FEED INGEST" : "PAUSED"}
            </button>
          </div>
        </div>
      </div>

      {/* ── MASTER HEADER ── */}
      <header className="bg-[#0B0F19]/90 backdrop-blur-md border-b border-[#1A2333] sticky top-0 z-30 px-4 sm:px-6 py-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded bg-gradient-to-tr from-[#00F2FE] to-[#FF5400] p-[1.5px] flex items-center justify-center">
            <div className="bg-[#070A13] h-full w-full rounded-[2.5px] flex items-center justify-center">
              <Radio className="h-5 w-5 text-[#00F2FE] animate-pulse" />
            </div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-[0.08em] text-white font-mono uppercase">
                STRATEX CENTCOM
              </h1>
              <span className="font-mono text-[9px] px-1.5 py-0.5 bg-[#FFB020]/10 text-[#FFB020] border border-[#FFB020]/25 rounded tracking-widest font-extrabold">
                FLAGSPACE
              </span>
            </div>
            <p className="text-xs text-[#6D7B8F] font-mono uppercase tracking-[0.1em] mt-0.5">
              THE EXECUTIVE OPERATING SYSTEM · PORTAL: {portal.toUpperCase()}
            </p>
          </div>
        </div>

        {/* Dynamic Controls / Readouts */}
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto justify-end">
          {/* SEARCH BAR (Multi-Wall Integration) */}
          <div className="relative w-full sm:w-60">
            <span className="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none">
              <Search className="h-3.5 w-3.5 text-[#6D7B8F]" />
            </span>
            <input
              type="text"
              placeholder="SEARCH CENTCOM CONSOLE..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-[#0D121F] border border-[#1F2937] hover:border-[#00F2FE]/30 focus:border-[#00F2FE]/80 rounded py-1.5 pl-9 pr-4 text-xs font-mono tracking-widest text-[#00F2FE] placeholder-[#6D7B8F] focus:outline-none transition-colors"
            />
            {searchQuery && (
              <button onClick={() => setSearchQuery("")} className="absolute inset-y-0 right-0 pr-3 flex items-center">
                <X className="h-3 w-3 text-red-400 hover:text-red-500" />
              </button>
            )}
          </div>

          {/* Region Filter */}
          <div className="flex items-center gap-1.5 bg-[#0D121F] border border-[#1F2937] rounded p-0.5">
            {REGIONS.map((reg) => (
              <button
                key={reg}
                onClick={() => setSelectedRegion(reg)}
                className={`text-[10px] font-mono font-bold tracking-widest px-2.5 py-1 rounded transition-all ${
                  selectedRegion === reg
                    ? "bg-[#00F2FE] text-[#070A13] shadow-md shadow-[#00F2FE]/15"
                    : "text-[#6D7B8F] hover:text-white"
                }`}
              >
                {reg}
              </button>
            ))}
          </div>

          {/* Clock Node */}
          <div className="bg-[#0E1423] border border-[#1E273A] px-3 py-1.5 rounded flex items-center gap-2 font-mono text-xs text-[#00F2FE] font-semibold tracking-widest">
            <Clock className="h-3.5 w-3.5 text-[#FFB020] animate-spin-slow" />
            {liveClock || "00:00:00"}
          </div>
        </div>
      </header>

      {/* ── THREE COLUMN CONTROL GRIDS & WALL SELECTORS ── */}
      <div className="max-w-[1800px] mx-auto px-4 sm:px-6 py-6 grid grid-cols-1 lg:grid-cols-[250px_1fr] gap-6">
        
        {/* SIDEBAR NAVIGATION WALL SELECTOR */}
        <aside className="space-y-4">
          <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-3">
            <div className="font-mono text-[9px] tracking-widest uppercase text-[#6D7B8F] px-2.5 mb-2 font-extrabold">
              // OPERATIONAL WALLS
            </div>
            <nav className="space-y-1">
              {[
                { id: "overview", label: "🛰️ Global Cockpit" },
                { id: "map", label: "🗺️ Operations Map" },
                { id: "missions", label: "✈️ Mission Wall" },
                { id: "properties", label: "🏠 Property Intel" },
                { id: "contractors", label: "🛠️ Contractor Command" },
                { id: "ai", label: "🧠 AI Operations" },
                { id: "analytics", label: "📊 Executive Analytics" },
                { id: "alerts", label: "🛡️ Timeline & Alerts" },
                { id: "observability", label: "🔌 Observability Hub" },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`w-full text-left font-mono text-xs tracking-wider px-3 py-2.5 rounded transition flex items-center justify-between group ${
                    activeTab === tab.id
                      ? "bg-gradient-to-r from-[#00F2FE]/15 to-[#00F2FE]/05 border-l-2 border-[#00F2FE] text-white font-semibold"
                      : "text-[#6D7B8F] hover:bg-[#131B2D] hover:text-white"
                  }`}
                >
                  <span>{tab.label}</span>
                  <ChevronRight className={`h-3 w-3 transition-transform ${activeTab === tab.id ? "text-[#00F2FE] translate-x-1" : "text-[#6D7B8F] opacity-0 group-hover:opacity-100"}`} />
                </button>
              ))}
            </nav>
          </div>

          {/* Quick Real-Time Health Summary Widget */}
          <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-4 space-y-3.5">
            <div className="font-mono text-[9px] tracking-widest uppercase text-[#6D7B8F] font-extrabold border-b border-[#141E2F] pb-1.5 flex items-center justify-between">
              <span>SYSTEM PULSE</span>
              <span className="h-1.5 w-1.5 bg-[#00FF9C] rounded-full animate-ping" />
            </div>
            <div className="space-y-2.5 font-mono text-[11px]">
              <div className="flex items-center justify-between">
                <span className="text-[#6D7B8F]">API Health:</span>
                <span className="text-[#00FF9C] font-bold">99.98%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#6D7B8F]">Latency:</span>
                <span className="text-[#00F2FE] font-bold">14ms</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#6D7B8F]">Alert Queue:</span>
                <span className="text-[#FF2D78] font-bold">{alerts.filter(a => a.status === "New").length} Active</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-[#6D7B8F]">WS Connection:</span>
                <span className="text-white font-semibold flex items-center gap-1">
                  <Wifi className="h-3 w-3 text-[#00F2FE]" /> ESTABLISHED
                </span>
              </div>
            </div>
          </div>
        </aside>

        {/* MAIN WALL CANVAS */}
        <main className="space-y-6">

          {/* TAB 1: GLOBAL EXECUTIVE DASHBOARD & OVERVIEW (Task 1 + Task 10) */}
          {activeTab === "overview" && (
            <div className="space-y-6">
              {/* Primary Objective Prompt panel */}
              <div className="bg-gradient-to-r from-[#0C1221] to-[#0A0D15] border border-[#1C273C] rounded-lg p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-5 relative overflow-hidden">
                <div className="absolute top-0 right-0 opacity-10 font-mono text-[100px] select-none font-bold text-[#00F2FE] pointer-events-none translate-y-6 translate-x-6">
                  CEO
                </div>
                <div className="space-y-1 relative z-10">
                  <div className="font-mono text-[10px] tracking-widest text-[#FFB020] uppercase font-bold flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5" /> SECURE EXECUTIVE WORKSPACE PORTAL
                  </div>
                  <h2 className="text-xl font-bold text-white tracking-wide">
                    Douglas Piercy Executive Control Console
                  </h2>
                  <p className="text-xs text-[#6D7B8F] max-w-3xl leading-relaxed">
                    Welcome Douglas. CENTCOM provides instant company-wide situational awareness. No business logic duplication exists; data queries directly hit NextGen outboxes and secure Passport ledgers.
                  </p>
                </div>
                <div className="shrink-0 font-mono text-[11px] bg-[#111A2E] border border-[#1E2B43] px-3.5 py-2 rounded text-white space-y-1">
                  <div>Active Operator Node: <strong className="text-[#00F2FE]">CENTCOM-1</strong></div>
                  <div>System Version: <strong className="text-[#FF5400]">1.0 (PROD)</strong></div>
                </div>
              </div>

              {/* KPI Grid (Task 1) */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <MetricCard title="Total Platform Revenue" value="$2,485,300" sub="MTD aggregate ledger" trend="+14.2%" />
                <MetricCard title="Revenue Forecast (Q3)" value="$3,120,000" sub="Contract pipeline value" trend="Optimized" />
                <MetricCard title="Canonical Properties" value={liveData.properties.length > 0 ? liveData.properties.length : "142"} sub="Registered Passports" trend="+8.5%" />
                <MetricCard title="Global Property Health" value="96.4%" sub="Weighted index average" trend="Stable" />
                <MetricCard title="Missions Initiated" value={liveData.missions.length > 0 ? liveData.missions.length : "324"} sub="Across all regions" trend="+18.9%" />
                <MetricCard title="Mission Success Rate" value="98.8%" sub="Automatic drone flights" trend="Elite" />
                <MetricCard title="Active Field Operators" value="36 Units" sub="Registered pilots" trend="+4 New" />
                <MetricCard title="Platform Contractors" value="18 Teams" sub="Marketplace ready" trend="Verified" />
                <MetricCard title="Habitat Members" value="156 sync" sub="Property synchronization" trend="+11.2%" />
                <MetricCard title="Insurance Claims Framework" value="72 total" sub="24 pending // 48 complete" trend="$380k pipeline" trendColor="text-[#FFB020] bg-[#FFB020]/10 border-[#FFB020]/20" />
                <MetricCard title="Reports Generated" value="294 PDF" sub="SHA-256 Ledgered" trend="100% Valid" />
                <MetricCard title="Outstanding Alerts" value={`${alerts.filter(a => a.status === "New").length} Critical`} sub="Needs rapid attention" trend="Action Required" trendColor="text-red-400 bg-red-400/10 border-red-500/20" labelColor="text-red-400" />
              </div>

              {/* Primary Objective Answer panel */}
              <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5">
                <h3 className="font-mono text-xs tracking-widest text-[#00F2FE] font-extrabold uppercase border-b border-[#152033] pb-3 mb-4 flex items-center gap-2">
                  <Terminal className="h-4 w-4 text-[#FF5400]" /> EXECUTIVE ANSWER PANEL (PRIMARY OBJECTIVES)
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5 text-xs font-mono">
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-[#FFB020] font-bold">1. WHAT IS HAPPENING?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      Elena Rostova is starting flight MS-7201; AI Consensus engine is running checks on PR-8820; 128 raw flight assets ingested into our AWS Glacier storage pipeline.
                    </p>
                  </div>
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-[#FF5400] font-bold">2. WHERE IS IT HAPPENING?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      West Coast (Seattle grid) and Central (Lexington sector) currently hold 74% of live fly activity. Dallas trailer hub is fully prepared for tomorrow's regional flight schedule.
                    </p>
                  </div>
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-[#00FF9C] font-bold">3. WHO IS RESPONSIBLE?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      Sarah Jenkins is dispatch lead for Western operations; Apex Roofing Group is assigned as primary master contractor for physical on-site moisture extraction.
                    </p>
                  </div>
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-red-400 font-bold">4. WHAT REQUIRES ATTENTION?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      Severe sub-surface moisture anomaly on Seattle Terminal (PR-8820). An alert is pending review in the centralized command alerts wall. Needs immediate dispatch.
                    </p>
                  </div>
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-[#00F2FE] font-bold">5. WHAT OPPORTUNITIES EXIST?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      Unlinked commercial properties in Miami present a $145k service contract pipeline possibility if we dispatch MDU-1 solar fleet to Miami within 48 hours.
                    </p>
                  </div>
                  <div className="space-y-1.5 p-3.5 bg-[#0C1221] border border-[#1A263D] rounded hover:border-[#00F2FE]/25 transition">
                    <span className="text-[#6D7B8F] font-bold">6. WHAT SHOULD HAPPEN NEXT?</span>
                    <p className="text-[#A0AEC0] leading-relaxed">
                      1. Acknowledge and resolve critical Seattle moisture alert. 2. Push GAF Timberline HDZ contract signing to Apex. 3. Regenerate Doug's secure Briefing PDF.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: GLOBAL OPERATIONS MAP (Task 2) */}
          {activeTab === "map" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-5">
              <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-[#141E2F] pb-4">
                <div>
                  <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                    <Globe className="h-4 w-4" /> Global Tactical Operations Map Wall
                  </h3>
                  <p className="text-xs text-[#6D7B8F]">
                    Simultaneous tracking of active operators, drone fleets, properties, and weather vectors. Filtered by {selectedRegion} region.
                  </p>
                </div>
                {/* Map Layers Toggles */}
                <div className="flex items-center gap-2 bg-[#0D121F] border border-[#1A2333] px-3 py-1.5 rounded text-xs font-mono">
                  <span className="text-[#6D7B8F] uppercase mr-2 tracking-wider">Map Layers:</span>
                  <label className="flex items-center gap-1.5 cursor-pointer text-white hover:text-[#00F2FE] transition">
                    <input
                      type="checkbox"
                      checked={mapLayers.weather}
                      onChange={(e) => setMapLayers({ ...mapLayers, weather: e.target.checked })}
                      className="accent-[#00F2FE] h-3.5 w-3.5"
                    />
                    Doppler Weather
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer text-white hover:text-[#FF5400] transition ml-3 border-l border-[#1F2937] pl-3">
                    <input
                      type="checkbox"
                      checked={mapLayers.airspace}
                      onChange={(e) => setMapLayers({ ...mapLayers, airspace: e.target.checked })}
                      className="accent-[#FF5400] h-3.5 w-3.5"
                    />
                    FAA Airspace Zones
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer text-white hover:text-[#FFB020] transition ml-3 border-l border-[#1F2937] pl-3">
                    <input
                      type="checkbox"
                      checked={mapLayers.risk}
                      onChange={(e) => setMapLayers({ ...mapLayers, risk: e.target.checked })}
                      className="accent-[#FFB020] h-3.5 w-3.5"
                    />
                    Risk Saturation Index
                  </label>
                </div>
              </div>

              {/* TACTICAL MAP SVG DISPLAY */}
              <div className="grid grid-cols-1 xl:grid-cols-[1fr_300px] gap-5">
                <div className="relative border border-[#1E2B43] rounded bg-[#0A0E18] min-h-[480px] flex flex-col justify-between overflow-hidden">
                  
                  {/* Grid Lines Overlay */}
                  <div className="absolute inset-0 bg-grid-pattern opacity-10 pointer-events-none" />
                  
                  {/* Airspace Zones Indicator Overlay */}
                  {mapLayers.airspace && (
                    <div className="absolute top-1/4 left-1/3 w-40 h-40 rounded-full border border-dashed border-[#FF5400]/25 bg-[#FF5400]/03 pointer-events-none flex items-center justify-center">
                      <span className="font-mono text-[8px] text-[#FF5400] uppercase tracking-wider">FAA Zone-B Warning Buffer</span>
                    </div>
                  )}

                  {/* Weather Radar Overlay */}
                  {mapLayers.weather && (
                    <div className="absolute bottom-1/4 right-1/4 w-52 h-44 rounded-lg bg-radial-radar border border-dashed border-[#00FF9C]/20 pointer-events-none">
                      <div className="absolute inset-0 bg-gradient-to-tr from-[#00FF9C]/05 to-[#00FF9C]/0 w-full h-full animate-pulse flex items-end p-2">
                        <span className="font-mono text-[8px] text-[#00FF9C] uppercase tracking-widest">Active Doppler Rain Band</span>
                      </div>
                    </div>
                  )}

                  {/* Interactive Target Crosshair Overlay */}
                  <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-none flex items-center justify-center">
                    <span className="w-10 h-10 border border-dashed border-[#00F2FE]/25 rounded-full" />
                    <span className="w-1.5 h-1.5 bg-[#00F2FE] rounded-full absolute" />
                  </div>

                  {/* MAP CANVAS SCATTER PINS */}
                  <div className="absolute inset-0 p-8">
                    {filteredPins.map((pin) => {
                      // Project lat/lng coordinate mapping onto the HUD grid boundaries
                      const topPct = 90 - ((pin.lat - 25) * (75 / 23)); // Map lat [25, 48] -> % [15, 90]
                      const leftPct = 15 + ((pin.lng + 125) * (70 / 45)); // Map lng [-125, -80] -> % [15, 85]
                      const color = pin.status.includes("Critical") ? "#FF2D78"
                                  : pin.status.includes("Active") ? "#00F2FE"
                                  : pin.status.includes("On-site") ? "#FFB020"
                                  : "#00FF9C";

                      return (
                        <button
                          key={pin.id}
                          onClick={() => setFocusedPin(pin)}
                          className="absolute group transition-transform hover:scale-125 focus:outline-none"
                          style={{ top: `${topPct}%`, left: `${leftPct}%` }}
                        >
                          <MapPin className="h-5 w-5 filter drop-shadow" style={{ color }} />
                          <span className="absolute -bottom-6 left-1/2 -translate-x-1/2 bg-[#090D18]/90 border border-[#1C273C] text-[8.5px] text-white px-1.5 py-0.5 rounded font-mono uppercase tracking-widest whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-20">
                            {pin.name}
                          </span>
                        </button>
                      );
                    })}
                  </div>

                  {/* Map Footer Metadata Readouts */}
                  <div className="relative z-10 p-4 border-t border-[#1C273C] bg-[#070A14]/90 backdrop-blur-sm flex items-center justify-between text-[10px] font-mono tracking-widest text-[#6D7B8F]">
                    <span>TACTICAL SCAN GRID CALIBRATION: ±0.78CM</span>
                    <span className="text-white">COORDINATES SYSTEM: WGS-84 ACTIVE</span>
                    <span>MULTI-REGION SCALE ACTIVE</span>
                  </div>
                </div>

                {/* Map Sidebar Flyout (Details Pane) */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1C273C] pb-2">
                    🎯 Selected Telemetry
                  </div>

                  {focusedPin ? (
                    <div className="space-y-4 font-mono text-xs">
                      <div className="space-y-1">
                        <span className="text-[10px] text-[#FFB020] uppercase font-bold">{focusedPin.type} Identity:</span>
                        <div className="text-white font-semibold">{focusedPin.name}</div>
                        <div className="text-[#6D7B8F] text-[10.5px]">{focusedPin.label}</div>
                      </div>

                      <div className="space-y-1 border-t border-[#1F2937] pt-3">
                        <span className="text-[10px] text-[#6D7B8F] uppercase">Current Operational Status:</span>
                        <div className="text-[#00FF9C] font-semibold flex items-center gap-1.5">
                          <span className="h-1.5 w-1.5 bg-[#00FF9C] rounded-full animate-pulse" />
                          {focusedPin.status}
                        </div>
                      </div>

                      <div className="space-y-1 border-t border-[#1F2937] pt-3">
                        <span className="text-[10px] text-[#6D7B8F] uppercase">Strategic Value index:</span>
                        <div className="text-white font-bold">{focusedPin.value}</div>
                      </div>

                      <div className="space-y-1 border-t border-[#1F2937] pt-3">
                        <span className="text-[10px] text-[#6D7B8F] uppercase">GPS Coordinate Target:</span>
                        <div className="text-[#00F2FE] font-bold">{focusedPin.lat.toFixed(4)}N, {focusedPin.lng.toFixed(4)}W</div>
                      </div>

                      <button
                        onClick={() => {
                          toast.info(`Requesting direct remote feed links to ${focusedPin.name}...`);
                        }}
                        className="w-full bg-[#00F2FE]/10 text-[#00F2FE] hover:bg-[#00F2FE]/25 border border-[#00F2FE]/30 py-2 rounded text-[11px] font-bold uppercase transition"
                      >
                        Launch Direct Feed
                      </button>
                    </div>
                  ) : (
                    <div className="text-center py-12 text-[#6D7B8F] font-mono text-xs leading-relaxed">
                      No tactical target currently selected.<br />
                      <span className="text-[#FFB020]">Click any map pin</span> to hook live telemetry feed streams.
                    </div>
                  )}

                  {/* List of active map items */}
                  <div className="space-y-2 border-t border-[#1C273C] pt-3">
                    <span className="font-mono text-[9px] uppercase text-[#6D7B8F] tracking-widest font-extrabold block">Active Map Elements</span>
                    <div className="space-y-1.5 max-h-36 overflow-y-auto pr-1">
                      {filteredPins.map((p) => (
                        <button
                          key={p.id}
                          onClick={() => setFocusedPin(p)}
                          className={`w-full text-left font-mono text-[10.5px] px-2 py-1.5 rounded border transition flex items-center justify-between ${
                            focusedPin?.id === p.id 
                              ? "bg-[#162136] border-[#00F2FE] text-white" 
                              : "bg-[#0A0D15] border-[#1C273C] text-[#6D7B8F] hover:text-white"
                          }`}
                        >
                          <span className="truncate max-w-36">{p.name}</span>
                          <span className="text-[8.5px] uppercase font-bold text-[#00F2FE]">{p.region}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: MISSION OPERATIONS WALL (Task 3) */}
          {activeTab === "missions" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div>
                <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                  <Clipboard className="h-4 w-4" /> Live Mission Operations Wall
                </h3>
                <p className="text-xs text-[#6D7B8F]">
                  Real-time aerial capture queues, preflight authorization, wind-sensor metrics, and imagery package ingestion pools.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* 1. Preflight/Active Flight Queue */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Flight Queue</span>
                    <span className="text-[10px] text-[#00F2FE] font-bold">4 Active</span>
                  </div>
                  <div className="space-y-2">
                    {[
                      { id: "MS-4921", target: "PR-8820 Seattle", pilot: "DJI Dock 3", status: "Scanning Facet 3", progress: "65%" },
                      { id: "MS-7201", target: "PR-104 Lexington", pilot: "Sarah Jenkins", status: "Pre-Flight In Progress", progress: "10%" },
                      { id: "MS-1102", target: "PR-218 Atlanta", pilot: "MDU-1 Dispatcher", status: "Delayed (Wind)", progress: "0%" },
                      { id: "MS-8812", target: "PR-9402 Houston", pilot: "Marcus Brody", status: "Completed (Upload)", progress: "100%" },
                    ].map((item) => (
                      <div key={item.id} className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5 font-mono text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-white font-bold">{item.id}</span>
                          <span className={`text-[9.5px] px-1.5 py-0.5 rounded uppercase font-extrabold ${
                            item.status.includes("Scanning") ? "bg-[#00F2FE]/10 text-[#00F2FE] border border-[#00F2FE]/20"
                            : item.status.includes("Delayed") ? "bg-red-500/10 text-red-400 border border-red-500/20"
                            : item.status.includes("Completed") ? "bg-[#00FF9C]/10 text-[#00FF9C] border border-[#00FF9C]/20"
                            : "bg-[#FFB020]/10 text-[#FFB020] border border-[#FFB020]/20"
                          }`}>{item.status}</span>
                        </div>
                        <div className="text-[#6D7B8F] text-[11px]">Target: {item.target}</div>
                        <div className="text-[#6D7B8F] text-[11px]">Pilot: {item.pilot}</div>
                        
                        {/* Progress slider bar */}
                        <div className="space-y-1 pt-1">
                          <div className="flex items-center justify-between text-[10px] text-[#6D7B8F]">
                            <span>Progress index:</span>
                            <span className="text-white">{item.progress}</span>
                          </div>
                          <div className="h-1 bg-[#1A2333] rounded overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-[#00F2FE] to-[#00FF9C]" style={{ width: item.progress }} />
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Weather Delays & Safety Monitors */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Weather Radar & safety</span>
                    <span className="text-[10px] text-red-400 font-bold">1 Active Alert</span>
                  </div>
                  <div className="space-y-3 font-mono text-xs">
                    <div className="p-3 bg-[#FF2D78]/05 border border-[#FF2D78]/20 rounded space-y-1.5">
                      <span className="text-[#FF2D78] font-bold flex items-center gap-1">
                        <AlertTriangle className="h-4 w-4" /> WIND CRITICAL AT LEXINGTON, KY
                      </span>
                      <p className="text-[#A0AEC0] text-[11.5px] leading-relaxed">
                        Doppler velocity exceeds 22.4 knots. Autonomous preflight sequences have been suspended indefinitely.
                      </p>
                    </div>

                    {/* Wind and Doppler gauges */}
                    <div className="grid grid-cols-2 gap-2.5 pt-1">
                      <div className="p-2.5 bg-[#0A0D15] border border-[#1E2B43] rounded text-center">
                        <div className="text-[#6D7B8F] text-[9px] uppercase">Seattle Wind</div>
                        <div className="text-white font-bold text-sm mt-0.5">8.4 knots</div>
                        <span className="text-[#00FF9C] text-[9px] font-bold">STATUS: SAFE</span>
                      </div>
                      <div className="p-2.5 bg-[#0A0D15] border border-[#1E2B43] rounded text-center">
                        <div className="text-[#6D7B8F] text-[9px] uppercase">Atlanta Wind</div>
                        <div className="text-white font-bold text-sm mt-0.5">14.1 knots</div>
                        <span className="text-[#FFB020] text-[9px] font-bold">STATUS: CAUTION</span>
                      </div>
                    </div>

                    {/* Airspace Zones and restricted buffers */}
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="text-[#6D7B8F] text-[10px] uppercase font-bold">FAA Airspace Authorization:</div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Seattle (Zone B):</span>
                        <span className="text-[#00FF9C] font-semibold">LAANC APPROVED</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Atlanta (Zone A):</span>
                        <span className="text-[#00FF9C] font-semibold">LAANC APPROVED</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Dallas (Airport Buffer):</span>
                        <span className="text-[#FFB020] font-semibold">MANUAL REVIEW PENDING</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Ingestion & Outbox Events */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Evidence Ingestion</span>
                    <span className="text-[10px] text-[#00FF9C] font-bold">128 uploads</span>
                  </div>
                  <div className="space-y-2.5 font-mono text-xs">
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="flex items-center justify-between">
                        <span className="text-white font-semibold">Asset Pipeline Speed</span>
                        <span className="text-[#00F2FE] font-bold">8.4 MB/s</span>
                      </div>
                      <div className="h-1 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-[#00F2FE] animate-pulse" style={{ width: "78%" }} />
                      </div>
                      <span className="text-[#6D7B8F] text-[9px] uppercase tracking-wide block pt-1">
                        S3 target bucket: s3://nextgen-raw-imagery/
                      </span>
                    </div>

                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-2">
                      <span className="text-[#6D7B8F] text-[9.5px] uppercase font-bold block">Telemetry Link Status:</span>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>MDU-3 (Starlink Mini):</span>
                        <span className="text-[#00FF9C] font-bold">94ms (STABLE)</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>MDU-1 (Cellular Hub):</span>
                        <span className="text-[#FFB020] font-bold">240ms (LATENCY)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: PROPERTY INTELLIGENCE WALL (Task 4) */}
          {activeTab === "properties" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div>
                <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                  <Briefcase className="h-4 w-4" /> Property Intelligence Wall
                </h3>
                <p className="text-xs text-[#6D7B8F]">
                  Durable Property Passport ledger commits, sub-surface DNA updates, critical moisture findings, and AWE composite trends.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-6">
                {/* 1. Recently Updated Properties Table */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3.5">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5">
                    Recently Updated Properties & DNA
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-[#1E2B43] text-[#6D7B8F] text-[10.5px]">
                          <th className="py-2">PROPERTY NAME</th>
                          <th className="py-2">DNA VERSION</th>
                          <th className="py-2">RISK SCORE</th>
                          <th className="py-2">PASSPORT COMMIT</th>
                          <th className="py-2">WARRANTY EXP</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#131B2D]">
                        {[
                          { name: "Seattle Terminal (PR-8820)", version: "v4.1.2", risk: "Severe moisture Anomaly", commit: "01:20:45", exp: "2035-08-20" },
                          { name: "Lexington Plaza (PR-104)", version: "v3.0.1", risk: "Optimal (Safe)", commit: "01:02:15", exp: "2051-12-05" },
                          { name: "Atlanta Airport Hub (PR-218)", version: "v2.5.4", risk: "Pending Review", commit: "Yesterday", exp: "2048-02-14" },
                          { name: "Miami Commercial (PR-9421)", version: "v1.0.8", risk: "Optimal (Safe)", commit: "2 days ago", exp: "2030-05-18" },
                          { name: "Austin Tech Center (PR-0492)", version: "v2.0.0", risk: "Minor Leakage Anomaly", commit: "5 days ago", exp: "2044-09-01" },
                        ].map((prop, i) => (
                          <tr key={i} className="hover:bg-[#111A2D] transition-colors">
                            <td className="py-2.5 text-white font-semibold">{prop.name}</td>
                            <td className="py-2.5 text-[#00F2FE]">{prop.version}</td>
                            <td className={`py-2.5 font-bold ${
                              prop.risk.includes("Severe") ? "text-red-400" 
                              : prop.risk.includes("Minor") ? "text-[#FFB020]"
                              : prop.risk.includes("Pending") ? "text-slate-400"
                              : "text-[#00FF9C]"
                            }`}>{prop.risk}</td>
                            <td className="py-2.5 text-[#6D7B8F]">{prop.commit}</td>
                            <td className="py-2.5 text-[#A0AEC0]">{prop.exp}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 2. Critical Findings & Warranty Alerts */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Critical Escapes</span>
                    <span className="text-[10px] text-[#FFB020] font-bold">2 Warnings</span>
                  </div>

                  <div className="space-y-3 font-mono text-xs">
                    {/* Findings list */}
                    <div className="p-3 bg-[#FFB020]/05 border border-[#FFB020]/20 rounded space-y-1">
                      <span className="text-[#FFB020] font-bold uppercase block">WARRANTY EXPIRING SOON</span>
                      <div className="text-white font-semibold">Miami Commercial (PR-9421)</div>
                      <p className="text-[#6D7B8F] text-[11px] pt-1">
                        System shows commercial roof warranty set to expire within 30 days. Recommend outreach.
                      </p>
                    </div>

                    <div className="p-3 bg-[#FF2D78]/05 border border-[#FF2D78]/20 rounded space-y-1">
                      <span className="text-red-400 font-bold uppercase block">MOISTURE ESCALATION RATING</span>
                      <div className="text-white font-semibold">Seattle Terminal (PR-8820)</div>
                      <p className="text-[#6D7B8F] text-[11px] pt-1">
                        Moisture saturation has escalated to high level on core Facet 3. Internal damage potential.
                      </p>
                    </div>

                    {/* AWE Trend indicator widget */}
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <span className="text-[#6D7B8F] text-[10px] uppercase font-bold block">AWE Trend Composite Index:</span>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Air Efficiency:</span>
                        <span className="text-[#00FF9C] font-semibold">Improving (+2%)</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Water Substrate:</span>
                        <span className="text-red-400 font-semibold">Declining (-14%)</span>
                      </div>
                      <div className="flex items-center justify-between text-[11px]">
                        <span>Energy Index:</span>
                        <span className="text-[#00FF9C] font-semibold">Stable (+0.5%)</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 5: CONTRACTOR COMMAND WALL (Task 5) */}
          {activeTab === "contractors" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div>
                <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                  <Users className="h-4 w-4" /> Contractor Command Wall
                </h3>
                <p className="text-xs text-[#6D7B8F]">
                  Real-time pipeline values, open marketplace opportunities, crew utilization, and warranty repair dispatcher logs.
                </p>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-[1fr_350px] gap-6">
                {/* 1. Revenue Pipeline & Estimator Status */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Active Projects & Marketplace</span>
                    <span className="text-[10px] text-[#00FF9C] font-bold">$1.65M Value</span>
                  </div>

                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-[#1E2B43] text-[#6D7B8F] text-[10.5px]">
                          <th className="py-2">PARTNER NAME</th>
                          <th className="py-2">ACTIVE CREWS</th>
                          <th className="py-2">UTILIZATION</th>
                          <th className="py-2">ESTIMATE QUEUE</th>
                          <th className="py-2">MARKET READY</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#131B2D]">
                        {[
                          { name: "Apex Roofing Group", crews: "4 crews", utilization: "88%", queue: "3 pending", status: "Certified" },
                          { name: "Southeastern Builders", crews: "2 crews", utilization: "74%", queue: "1 pending", status: "Certified" },
                          { name: "Northwest Storm Rescue", crews: "3 crews", utilization: "95%", queue: "4 pending", status: "Active" },
                          { name: "Texas Diagnostics LLC", crews: "2 crews", utilization: "62%", queue: "0 pending", status: "Active" },
                        ].map((c, i) => (
                          <tr key={i} className="hover:bg-[#111A2D] transition-colors">
                            <td className="py-2.5 text-white font-semibold">{c.name}</td>
                            <td className="py-2.5 text-[#00F2FE]">{c.crews}</td>
                            <td className="py-2.5 text-white">{c.utilization}</td>
                            <td className="py-2.5 text-[#FFB020]">{c.queue}</td>
                            <td className="py-2.5">
                              <span className="px-1.5 py-0.5 rounded bg-[#00FF9C]/10 text-[#00FF9C] border border-[#00FF9C]/25 text-[10px] font-bold">
                                {c.status}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* 2. Appointments & Warranty Calls Dispatcher */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Upcoming schedule</span>
                    <span className="text-[10px] text-[#00F2FE] font-bold">4 Scheduled</span>
                  </div>

                  <div className="space-y-3 font-mono text-xs">
                    {[
                      { title: "Seattle Roof Extraction", partner: "Apex Crew A", time: "Tomorrow 08:00", type: "Warranty Call" },
                      { title: "Lexington Core Inspection", partner: "Sarah Jenkins Mobile", time: "July 24 10:30", type: "Standard Scan" },
                      { title: "Atlanta Flight sequence", partner: "Southeastern team", time: "July 25 14:00", type: "Estimate Audit" },
                    ].map((app, i) => (
                      <div key={i} className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-white font-bold">{app.title}</span>
                          <span className="text-[9px] text-[#FFB020] font-semibold uppercase">{app.type}</span>
                        </div>
                        <div className="text-[#6D7B8F] text-[11px]">Crew: {app.partner}</div>
                        <div className="text-[#00F2FE] text-[11px] font-bold">Schedule: {app.time}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 6: AI OPERATIONS WALL (Task 6) */}
          {activeTab === "ai" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div>
                <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                  <Cpu className="h-4 w-4" /> AI Operations Wall
                </h3>
                <p className="text-xs text-[#6D7B8F]">
                  Real-time monitoring of deep learning evidence processing, radiometric moisture consensus, and background worker latencies.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {/* 1. Processing Queue & Consensus Engine */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Validation Queue</span>
                    <span className="text-[10px] text-[#00FF9C] font-bold">Queue healthy</span>
                  </div>

                  <div className="space-y-3 font-mono text-xs">
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="flex items-center justify-between font-bold">
                        <span>Consensus status:</span>
                        <span className="text-[#00FF9C]">5/5 AGENTS AGREE</span>
                      </div>
                      <div className="text-[#A0AEC0] text-[11px]">
                        Thermal anomaly, geometric facet edges, water capacitance, wind-resistance, and billing estimation matrices aligned.
                      </div>
                    </div>

                    <div className="space-y-1 pt-1">
                      <div className="flex items-center justify-between text-[11px] text-[#6D7B8F]">
                        <span>Mean Consensus Confidence:</span>
                        <span className="text-white font-bold">98.4%</span>
                      </div>
                      <div className="h-1 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-gradient-to-r from-[#FF5400] to-[#00FF9C]" style={{ width: "98.4%" }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. Worker Performance & Processing Latency */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>Background workers</span>
                    <span className="text-[10px] text-[#00F2FE] font-bold">8 Workers Active</span>
                  </div>

                  <div className="space-y-2 font-mono text-xs">
                    {[
                      { name: "Radiometric Moisture Agent", load: "42%", latency: "142ms" },
                      { name: "Facet Geometry Estimator", load: "18%", latency: "280ms" },
                      { name: "Dilation Damage Evaluator", load: "74%", latency: "1,120ms" },
                      { name: "Xactimate Billing Generator", load: "9%", latency: "95ms" },
                    ].map((worker, i) => (
                      <div key={i} className="p-2.5 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1">
                        <div className="flex items-center justify-between font-semibold">
                          <span className="text-white">{worker.name}</span>
                          <span className="text-[#00F2FE]">{worker.latency}</span>
                        </div>
                        <div className="flex items-center justify-between text-[11px] text-[#6D7B8F]">
                          <span>CPU utilization:</span>
                          <span>{worker.load}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3. System Intelligence Health Dials */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-4 space-y-3">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-1.5 flex items-center justify-between">
                    <span>System intelligence health</span>
                    <span className="text-[10px] text-[#00FF9C] font-bold">Optimal</span>
                  </div>

                  <div className="space-y-3 font-mono text-xs">
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="text-[#6D7B8F] text-[10px] uppercase">Telemetry Ingestion Queue</div>
                      <div className="text-white font-bold text-sm">0 Pending tasks</div>
                      <span className="text-[#00FF9C] text-[9.5px] font-bold">STATUS: EMPTY</span>
                    </div>

                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="text-[#6D7B8F] text-[10px] uppercase">Moisture Thermal Model Drift</div>
                      <div className="text-white font-bold text-sm">0.02% drift / month</div>
                      <span className="text-[#00FF9C] text-[9.5px] font-bold">STATUS: EXCELLENT CALIBRATION</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 7: EXECUTIVE ANALYTICS WALL (Task 9) */}
          {activeTab === "analytics" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-[#141E2F] pb-4">
                <div>
                  <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                    <BarChart2 className="h-4 w-4" /> Global Executive Analytics Wall
                  </h3>
                  <p className="text-xs text-[#6D7B8F]">
                    Deep strategic trend telemetry for platform adoption, contractor efficiency, and revenue-to-forecast indexes.
                  </p>
                </div>
              </div>

              {/* RECHARTS PLOTS CONTAINER */}
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
                
                {/* 1. MTD Revenue & Forecast Trend (AreaChart) */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold flex items-center justify-between">
                    <span>Platform Revenue & Forecast trends</span>
                    <span className="text-[10px] text-[#00FF9C] font-bold">+14.2% MoM</span>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <AreaChart data={ANALYTICS_REVENUE} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <defs>
                          <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#00F2FE" stopOpacity={0.3}/>
                            <stop offset="95%" stopColor="#00F2FE" stopOpacity={0}/>
                          </linearGradient>
                          <linearGradient id="colorForecast" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#FFB020" stopOpacity={0.2}/>
                            <stop offset="95%" stopColor="#FFB020" stopOpacity={0}/>
                          </linearGradient>
                        </defs>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" opacity={0.3} />
                        <XAxis dataKey="month" stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <YAxis stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#0D121F", borderColor: "#1E2B43" }} />
                        <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace" }} />
                        <Area type="monotone" dataKey="Revenue" stroke="#00F2FE" strokeWidth={1.8} fillOpacity={1} fill="url(#colorRev)" />
                        <Area type="monotone" dataKey="Forecast" stroke="#FFB020" strokeWidth={1.5} strokeDasharray="4 4" fillOpacity={1} fill="url(#colorForecast)" />
                      </AreaChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 2. Mission Completion & Ingest metrics (BarChart) */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold flex items-center justify-between">
                    <span>Flight Completion & Delay Tracking</span>
                    <span className="text-[10px] text-[#00F2FE] font-bold">98.8% Success</span>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={ANALYTICS_MISSIONS} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" opacity={0.3} />
                        <XAxis dataKey="week" stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <YAxis stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#0D121F", borderColor: "#1E2B43" }} />
                        <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace" }} />
                        <Bar dataKey="Completed" fill="#00FF9C" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="Scheduled" fill="#00F2FE" radius={[3, 3, 0, 0]} />
                        <Bar dataKey="Delayed" fill="#FF2D78" radius={[3, 3, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 3. Contractor Marketplace Performance (LineChart) */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold flex items-center justify-between">
                    <span>Contractor Volume & Quality Index</span>
                    <span className="text-[10px] text-[#FFB020] font-bold">Verified Partners</span>
                  </div>
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <LineChart data={ANALYTICS_PARTNERS} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" opacity={0.3} />
                        <XAxis dataKey="name" stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <YAxis stroke="#6D7B8F" fontSize={10} tickLine={false} />
                        <Tooltip contentStyle={{ backgroundColor: "#0D121F", borderColor: "#1E2B43" }} />
                        <Legend wrapperStyle={{ fontSize: "11px", fontFamily: "monospace" }} />
                        <Line type="monotone" dataKey="Efficiency" stroke="#00FF9C" strokeWidth={2} activeDot={{ r: 6 }} />
                        <Line type="monotone" dataKey="Revenue" stroke="#FF5400" strokeWidth={1.5} />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </div>

                {/* 4. Operator Performance metrics table */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4 flex flex-col justify-between">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1C273C] pb-2">
                    Operator flight volume rankings
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left font-mono text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-[#1E2B43] text-[#6D7B8F] text-[10px]">
                          <th className="py-1">OPERATOR NAME</th>
                          <th className="py-1">COMPLETED FLIGHTS</th>
                          <th className="py-1">GPS RELIABILITY</th>
                          <th className="py-1">CURRENT STATUS</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#131B2D] text-[11px]">
                        {ANALYTICS_OPERATORS.map((op, i) => (
                          <tr key={i} className="hover:bg-[#111A2D] transition-colors">
                            <td className="py-2 text-white font-semibold">{op.name}</td>
                            <td className="py-2 text-[#00F2FE]">{op.Scans} scans</td>
                            <td className="py-2 text-[#00FF9C] font-bold">{op.Reliability}%</td>
                            <td className="py-2">
                              <span className={`px-1 rounded text-[9px] font-extrabold ${
                                op.Status === "Active" ? "bg-[#00FF9C]/10 text-[#00FF9C] border border-[#00FF9C]/25"
                                : "bg-slate-500/10 text-slate-400 border border-slate-500/25"
                              }`}>{op.Status}</span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                  <div className="font-mono text-[9px] text-[#6D7B8F] text-center pt-2 uppercase tracking-wide">
                    Telemetry synced with regional field dispatcher channels.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 8: TIMELINE & ALERTS WALL (Task 7 + Task 8) */}
          {activeTab === "alerts" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              
              {/* Split screen: Live Alerts (State Machine) on Left, Chronological Timeline on Right */}
              <div className="grid grid-cols-1 xl:grid-cols-[1fr_450px] gap-6">
                
                {/* ALERTS INBOX (Task 8) */}
                <div className="space-y-4">
                  <div className="flex items-center justify-between border-b border-[#141E2F] pb-3">
                    <div>
                      <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                        <ShieldAlert className="h-4 w-4" /> Centralized Alert Management Inbox
                      </h3>
                      <p className="text-xs text-[#6D7B8F]">
                        Review and authorize critical platforms, AI consensuses, and weather delay interventions.
                      </p>
                    </div>
                  </div>

                  {/* Dynamic Alert list cards with action buttons */}
                  <div className="space-y-3.5 max-h-[520px] overflow-y-auto pr-1">
                    {filteredAlerts.length > 0 ? (
                      filteredAlerts.map((alt) => {
                        const isCritical = alt.category === "Critical";
                        return (
                          <div
                            key={alt.id}
                            className={`p-4 rounded border transition flex flex-col justify-between gap-3 relative overflow-hidden ${
                              isCritical 
                                ? "bg-gradient-to-r from-[#FF2D78]/08 to-[#0D121F] border-[#FF2D78]/35" 
                                : alt.category === "Warning"
                                ? "bg-[#0D121F] border-[#FFB020]/35"
                                : "bg-[#0D121F] border-[#1F2937]"
                            }`}
                          >
                            {/* Alert Top line */}
                            <div className="flex items-center justify-between font-mono text-[10px]">
                              <div className="flex items-center gap-2">
                                <span className={`px-2 py-0.5 rounded font-extrabold text-[9.5px] uppercase border ${
                                  isCritical 
                                    ? "bg-red-500/15 text-red-400 border-red-500/25" 
                                    : alt.category === "Warning"
                                    ? "bg-amber-500/15 text-amber-400 border-amber-500/25"
                                    : "bg-blue-500/15 text-blue-400 border-blue-500/25"
                                }`}>
                                  {alt.category}
                                </span>
                                <span className="text-[#6D7B8F]">Source: <strong className="text-white">{alt.source}</strong></span>
                              </div>
                              <span className="text-[#6D7B8F]">{alt.at} UTC</span>
                            </div>

                            {/* Alert Content */}
                            <div className="space-y-1">
                              <h4 className="font-sans text-sm font-bold text-white tracking-wide">{alt.title}</h4>
                              <p className="text-xs text-[#A0AEC0] font-mono leading-relaxed">{alt.text}</p>
                            </div>

                            {/* Alert State machine action strip */}
                            <div className="flex flex-wrap items-center justify-between gap-2 border-t border-[#1C273C] pt-3 mt-1 text-[11px] font-mono">
                              <div className="text-[#6D7B8F]">
                                Status: <strong className={`font-bold uppercase ${alt.status === "New" ? "text-red-400 animate-pulse" : "text-[#00FF9C]"}`}>{alt.status}</strong>
                                {alt.assignedTo && (
                                  <span className="text-[#6D7B8F] ml-2 pl-2 border-l border-[#1F2937]">Assigned to: <strong className="text-[#00F2FE]">{alt.assignedTo}</strong></span>
                                )}
                              </div>

                              <div className="flex items-center gap-1.5">
                                {alt.status === "New" && (
                                  <button
                                    onClick={() => handleAcknowledgeAlert(alt.id)}
                                    className="bg-blue-500/10 hover:bg-blue-500/25 text-blue-400 border border-blue-500/30 px-2 py-1 rounded text-[10.5px] uppercase font-bold transition"
                                  >
                                    Acknowledge
                                  </button>
                                )}
                                {alt.status === "Acknowledged" && (
                                  <button
                                    onClick={() => handleAssignAlert(alt.id, "Apex Crew A")}
                                    className="bg-amber-500/10 hover:bg-amber-500/25 text-amber-400 border border-amber-500/30 px-2 py-1 rounded text-[10.5px] uppercase font-bold transition"
                                  >
                                    Assign Crew
                                  </button>
                                )}
                                {alt.status !== "Resolved" && alt.status !== "New" && (
                                  <button
                                    onClick={() => handleResolveAlert(alt.id)}
                                    className="bg-[#00FF9C]/10 hover:bg-[#00FF9C]/25 text-[#00FF9C] border border-[#00FF9C]/30 px-2 py-1 rounded text-[10.5px] uppercase font-bold transition"
                                  >
                                    Resolve
                                  </button>
                                )}
                                <button
                                  onClick={() => handleArchiveAlert(alt.id)}
                                  className="text-[#6D7B8F] hover:text-white border border-transparent hover:border-[#1F2937] px-2 py-1 rounded transition"
                                  title="Archive Alert out of view"
                                >
                                  Archive
                                </button>
                              </div>
                            </div>
                          </div>
                        );
                      })
                    ) : (
                      <div className="text-center py-16 text-[#6D7B8F] font-mono text-xs border border-dashed border-[#1C273C] rounded">
                        No outstanding alerts matching current filter query parameters.
                      </div>
                    )}
                  </div>
                </div>

                {/* EXECUTIVE TIMELINE (Task 7) */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <div className="font-mono text-xs tracking-widest text-white uppercase font-bold border-b border-[#1E2B43] pb-2 flex items-center justify-between">
                    <span>Executive Timeline Ledger</span>
                    <span className="text-[10px] text-[#00F2FE] font-bold">{filteredTimeline.length} events logged</span>
                  </div>

                  <div className="space-y-4 max-h-[500px] overflow-y-auto pr-1">
                    {filteredTimeline.map((item) => {
                      const color = item.type.includes("CRITICAL") ? "#FF2D78"
                                  : item.type.includes("COMPLETED") || item.type.includes("SIGNED") ? "#00FF9C"
                                  : "#00F2FE";

                      return (
                        <div key={item.id} className="relative pl-5 border-l border-[#1F2937] space-y-1 font-mono text-xs hover:border-[#00F2FE]/40 transition-colors py-1 group">
                          {/* Chronological dot indicator */}
                          <span
                            className="absolute -left-[4.5px] top-2.5 h-2 w-2 rounded-full border border-black transition-transform group-hover:scale-125"
                            style={{ backgroundColor: color }}
                          />
                          <div className="flex items-center justify-between text-[10px] text-[#6D7B8F]">
                            <span className="font-extrabold uppercase" style={{ color }}>{item.type}</span>
                            <span>{item.at} UTC</span>
                          </div>
                          <p className="text-white text-[11.5px] leading-relaxed">{item.text}</p>
                          <div className="text-[#6D7B8F] text-[10px] uppercase">
                            Operator: <strong className="text-[#A0AEC0]">{item.operator}</strong> · Region: <strong className="text-[#00F2FE]">{item.region}</strong>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 9: SYSTEM OBSERVABILITY (Task 10) */}
          {activeTab === "observability" && (
            <div className="bg-[#090D18] border border-[#151D2A] rounded-lg p-5 space-y-6">
              <div>
                <h3 className="text-sm font-mono tracking-widest text-[#00F2FE] uppercase font-bold flex items-center gap-1.5">
                  <Server className="h-4 w-4" /> System Observability Dashboard
                </h3>
                <p className="text-xs text-[#6D7B8F]">
                  Real-time status indicators for database connection pooling, redis job workers, authentication gateway, and API server loads.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
                {/* 1. API & WebSocket Health metrics */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <span className="font-mono text-xs tracking-widest text-white uppercase font-bold block border-b border-[#1E2B43] pb-1.5">
                    Gateway & Websockets
                  </span>
                  <div className="space-y-4 font-mono text-xs">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#6D7B8F]">API Gateway Response Time:</span>
                        <span className="text-[#00FF9C] font-bold">14ms average</span>
                      </div>
                      <div className="h-1.5 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-[#00FF9C]" style={{ width: "94%" }} />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#6D7B8F]">WebSocket Transmission Error Rate:</span>
                        <span className="text-white font-semibold">0.02%</span>
                      </div>
                      <div className="h-1.5 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-[#00F2FE]" style={{ width: "99.5%" }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. Database & Storage Pool Health */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <span className="font-mono text-xs tracking-widest text-white uppercase font-bold block border-b border-[#1E2B43] pb-1.5">
                    Database & Storage health
                  </span>
                  <div className="space-y-4 font-mono text-xs">
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#6D7B8F]">MongoDB Connection Pool:</span>
                        <span className="text-[#00FF9C] font-bold">18/50 active</span>
                      </div>
                      <div className="h-1.5 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-[#00FF9C]" style={{ width: "36%" }} />
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-[#6D7B8F]">Storage Bucket upload efficiency:</span>
                        <span className="text-white font-semibold">100% capacity</span>
                      </div>
                      <div className="h-1.5 bg-[#1A2333] rounded overflow-hidden">
                        <div className="h-full bg-[#00F2FE]" style={{ width: "100%" }} />
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Authentication & Security status */}
                <div className="bg-[#0D121F] border border-[#1A263D] rounded p-5 space-y-4">
                  <span className="font-mono text-xs tracking-widest text-white uppercase font-bold block border-b border-[#1E2B43] pb-1.5">
                    Authentication & security
                  </span>
                  <div className="space-y-4 font-mono text-xs">
                    <div className="p-3 bg-[#0A0D15] border border-[#1E2B43] rounded space-y-1.5">
                      <div className="text-[#6D7B8F] text-[10px] uppercase font-bold">SHA-256 Ledgering Gateway</div>
                      <div className="text-[#00FF9C] font-bold text-sm">SECURE & VERIFIED</div>
                      <span className="text-[#6D7B8F] text-[9.5px] uppercase tracking-wide block">
                        All Outbox logs matching Directive-009 standard
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* ── CENTRALIZED PLATFORM ACTIVITY TICKER (FOOTER STRIP - TASK 13) ── */}
      <footer className="bg-[#0B0F19] border-t border-[#1A2333] px-4 py-2 flex items-center justify-between gap-4 font-mono text-[9.5px] text-[#6D7B8F] tracking-widest">
        <div className="flex items-center gap-3">
          <Terminal className="h-4 w-4 text-[#00F2FE] animate-pulse" />
          <span className="text-white uppercase font-extrabold">LIVE ACTIVITY STREAM:</span>
          <span className="text-[#A0AEC0] truncate max-w-lg md:max-w-3xl">
            {timeline[0] ? `[${timeline[0].at} UTC] [${timeline[0].type}] - ${timeline[0].text} - Target: ${timeline[0].details}` : "WAITING FOR PLATFORM EMISSIONS..."}
          </span>
        </div>
        <div className="shrink-0 flex items-center gap-3">
          <span>PORTAL VERIFICATION: <strong className="text-white">SECURE</strong></span>
          <span className="border-l border-[#1F2937] pl-3">SYSTEM RESPONSIVENESS: <strong className="text-[#00FF9C]">EXCELLENT</strong></span>
        </div>
      </footer>
    </div>
  );
}

