/**
 * /contractor/deliverable/:jobId/deck — STRATEX™ Drone-Scan Report Deck.
 *
 * Companion to /contractor/deliverable/:jobId — same data, presented as a
 * 10-slide investor / homeowner walkthrough. One section per slide, paginated
 * for landscape PDF export.
 *
 * Shortcuts:
 *   /deck/demo                    → canonical AD-KY041 demo
 *   /contractor/deliverable/:jobId/deck
 *
 * PDF export:
 *   "Download PDF" button → window.print() with @page landscape + page-break
 *   between every slide so Save-as-PDF emits one slide per page.
 */
import React, { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Printer, ChevronLeft, ChevronRight, Plane, Layers, Ruler, Droplets,
  AlertTriangle, Hammer, FileText, Trash, ShieldCheck, Wind, Award,
  User, MapPin, CalendarClock, Wrench,
} from "lucide-react";
import { api } from "@/lib/api";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";
const INK = "#0B0F19";
const SILVER = "#E2E8F0";
const PAPER_BLACK = "#11181C";

const USD = (n) =>
  Number(n || 0).toLocaleString("en-US", {
    style: "currency", currency: "USD", minimumFractionDigits: 2,
  });

function fmtDT(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", {
      month: "short", day: "numeric", year: "numeric",
      hour: "numeric", minute: "2-digit",
    });
  } catch { return iso; }
}

export default function DeliverableDeck() {
  const { jobId } = useParams();
  const effectiveId = jobId || "crown-demo";
  const [pkt, setPkt] = useState(null);
  const [err, setErr] = useState(null);
  const [idx, setIdx] = useState(0);

  useEffect(() => {
    (async () => {
      try {
        const r = await api.get(`/contractor/deliverable/${encodeURIComponent(effectiveId)}`);
        setPkt(r.data);
      } catch (e) {
        setErr(e?.response?.data?.detail || e.message);
      }
    })();
  }, [effectiveId]);

  const slides = useMemo(() => (pkt ? buildSlides(pkt) : []), [pkt]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === "ArrowRight" || e.key === " ")
        setIdx((i) => Math.min(slides.length - 1, i + 1));
      if (e.key === "ArrowLeft")
        setIdx((i) => Math.max(0, i - 1));
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [slides.length]);

  if (err) return <FailPanel err={err}/>;
  if (!pkt) return (
    <div className="min-h-screen bg-[#0B0F19] flex items-center justify-center">
      <div className="font-mono text-[11px] uppercase tracking-widest" style={{ color: TEAL }}>
        // ASSEMBLING DECK…
      </div>
    </div>
  );

  const current = slides[idx];

  return (
    <div className="min-h-screen" style={{ background: INK, color: SILVER }} data-testid="deck-root">
      <DeckCSS/>

      {/* Screen-only toolbar */}
      <div className="no-print sticky top-0 z-40 flex flex-wrap items-center justify-between gap-2 px-3 py-3 border-b backdrop-blur"
           style={{ background: "rgba(11,15,25,0.9)", borderColor: NICKEL }}>
        <div className="font-mono text-[10px] tracking-widest uppercase truncate min-w-0 max-w-full sm:max-w-none" style={{ color: TEAL }}>
          // STRATEX™ DECK · {pkt.deliverable_id}
        </div>
        <div className="flex items-center gap-2 sm:gap-3">
          <div className="hidden sm:block font-mono text-[10px] uppercase tracking-widest" style={{ color: NICKEL }} data-testid="deck-progress">
            Slide <span style={{ color: SILVER }}>{idx + 1}</span> / {slides.length}
          </div>
          <button onClick={() => setIdx(Math.max(0, idx - 1))}
            disabled={idx === 0}
            className="font-mono text-[10px] uppercase tracking-widest border px-2.5 py-1.5 inline-flex items-center gap-1 disabled:opacity-40"
            style={{ borderColor: NICKEL, color: SILVER }}
            data-testid="deck-prev"
            aria-label="Previous slide">
            <ChevronLeft size={12}/><span className="hidden sm:inline">Prev</span>
          </button>
          <button onClick={() => setIdx(Math.min(slides.length - 1, idx + 1))}
            disabled={idx === slides.length - 1}
            className="font-mono text-[10px] uppercase tracking-widest border px-2.5 py-1.5 inline-flex items-center gap-1 disabled:opacity-40"
            style={{ borderColor: NICKEL, color: SILVER }}
            data-testid="deck-next"
            aria-label="Next slide">
            <span className="hidden sm:inline">Next</span> <ChevronRight size={12}/>
          </button>
          <button onClick={() => window.print()}
            className="font-mono text-[10px] uppercase tracking-widest px-3 sm:px-4 py-1.5 inline-flex items-center gap-2"
            style={{ background: TEAL, color: INK }}
            data-testid="deck-download-pdf">
            <Printer size={12}/><span className="hidden sm:inline">Download </span>PDF
          </button>
        </div>
        {/* Mobile slide counter — wraps below toolbar */}
        <div className="sm:hidden w-full font-mono text-[9px] uppercase tracking-widest text-center" style={{ color: NICKEL }} data-testid="deck-progress-mobile">
          Slide <span style={{ color: SILVER }}>{idx + 1}</span> / {slides.length}
        </div>
      </div>

      {/* Screen view: only the current slide */}
      <div className="screen-deck flex items-center justify-center" style={{ minHeight: "calc(100vh - 56px)" }}>
        <SlideFrame slide={current} idx={idx} total={slides.length} pkt={pkt}/>
      </div>

      {/* Print view: all slides stacked, one per page */}
      <div className="print-deck">
        {slides.map((s, i) => (
          <SlideFrame key={i} slide={s} idx={i} total={slides.length} pkt={pkt} printable/>
        ))}
      </div>

      {/* Footer dot-nav (screen only) */}
      <div className="no-print fixed bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5"
           data-testid="deck-dots">
        {slides.map((_, i) => (
          <button key={i} onClick={() => setIdx(i)}
            className="transition-all"
            style={{
              width: i === idx ? 22 : 8,
              height: 4,
              background: i === idx ? TEAL : NICKEL,
              borderRadius: 1,
            }}
            data-testid={`deck-dot-${i}`}
            aria-label={`Go to slide ${i + 1}`}/>
        ))}
      </div>
    </div>
  );
}

/* ============================================================
   SLIDE BUILDER — translates the deliverable payload into a
   structured slide array.
   ============================================================ */

function buildSlides(pkt) {
  return [
    { kind: "cover" },
    { kind: "flight" },
    { kind: "roof" },
    { kind: "geometrics" },
    { kind: "moisture" },
    { kind: "anomalies" },
    { kind: "phases" },
    { kind: "pricing" },
    { kind: "disposal" },
    { kind: "signoff" },
  ].filter((s) => isPopulated(s.kind, pkt));
}

function isPopulated(kind, pkt) {
  switch (kind) {
    case "geometrics": return !!pkt.geometrics_extended && Object.keys(pkt.geometrics_extended).length > 0;
    case "moisture":   return (pkt.moisture_diagnostics || []).length > 0;
    case "anomalies":  return (pkt.anomalies || []).length > 0;
    case "phases":     return !!pkt.financial_phases && Object.keys(pkt.financial_phases).length > 0;
    case "disposal":   return !!pkt.disposal_logistics && Object.keys(pkt.disposal_logistics).length > 0;
    default:           return true;
  }
}

/* ============================================================
   SLIDE FRAME — single 16:9 page (used both onscreen + print).
   ============================================================ */

function SlideFrame({ slide, idx, total, pkt, printable }) {
  return (
    <section
      className={`deck-slide ${printable ? "deck-slide-print" : ""}`}
      data-testid={`deck-slide-${slide.kind}`}
      style={{
        background: `linear-gradient(135deg, ${INK} 0%, #0F1521 70%, #131B2C 100%)`,
        color: SILVER,
        border: `1px solid ${NICKEL}`,
        position: "relative",
        overflow: "hidden",
      }}>
      {/* Decorative neon corner */}
      <div style={{
        position: "absolute", top: 0, left: 0, width: 120, height: 120,
        background: `radial-gradient(circle at 0 0, ${TEAL}33, transparent 60%)`,
        pointerEvents: "none",
      }}/>
      <div style={{
        position: "absolute", bottom: 0, right: 0, width: 220, height: 220,
        background: `radial-gradient(circle at 100% 100%, ${ORANGE}1A, transparent 60%)`,
        pointerEvents: "none",
      }}/>

      <div className="deck-content">
        <SlideHeader slide={slide} idx={idx} total={total} pkt={pkt}/>
        <SlideBody slide={slide} pkt={pkt}/>
      </div>

      <SlideFooter idx={idx} total={total} pkt={pkt}/>
    </section>
  );
}

function SlideHeader({ slide, idx, total, pkt }) {
  const meta = SLIDE_META[slide.kind] || { title: slide.kind.toUpperCase(), Icon: FileText };
  if (slide.kind === "cover") return null;
  return (
    <header className="flex items-center justify-between pb-3 mb-5"
            style={{ borderBottom: `1px solid ${NICKEL}` }}>
      <div className="flex items-center gap-3">
        <div className="flex items-center justify-center" style={{
          width: 38, height: 38, borderRadius: 2,
          background: `${TEAL}14`, border: `1px solid ${TEAL}55`,
        }}>
          <meta.Icon size={18} color={TEAL}/>
        </div>
        <div>
          <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>
            // SECTION {String(idx + 1).padStart(2, "0")} OF {String(total).padStart(2, "0")}
          </div>
          <h1 className="text-[20px] font-bold tracking-wide" style={{ color: SILVER, fontFamily: "'JetBrains Mono', monospace" }}>
            {meta.title}
          </h1>
        </div>
      </div>
      <div className="text-right">
        <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>STRATEX™ Deck</div>
        <div className="font-mono text-[10px]" style={{ color: TEAL }}>{pkt.deliverable_id}</div>
      </div>
    </header>
  );
}

function SlideFooter({ idx, total, pkt }) {
  return (
    <footer className="deck-footer flex items-center justify-between"
            style={{ borderTop: `1px solid ${NICKEL}55`, color: NICKEL }}>
      <span className="font-mono text-[9px] tracking-[0.3em] uppercase">
        STRATEX™ · Strategic Thermal Reconnaissance · Report v{pkt.platform.report_version}
      </span>
      <span className="font-mono text-[9px] tabular-nums tracking-[0.3em] uppercase">
        {String(idx + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
      </span>
    </footer>
  );
}

/* ============================================================
   SLIDE BODIES
   ============================================================ */

const SLIDE_META = {
  cover:      { title: "Drone-Scan Report",       Icon: Plane },
  flight:     { title: "Flight Record",           Icon: Plane },
  roof:       { title: "Roof Composition · Digital Twin", Icon: Layers },
  geometrics: { title: "Quantified Geometry",     Icon: Ruler },
  moisture:   { title: "Sub-Surface Moisture Diagnostics", Icon: Droplets },
  anomalies:  { title: "Anomaly Findings",        Icon: AlertTriangle },
  phases:     { title: "Project Phase Breakdown", Icon: Hammer },
  pricing:    { title: "Standard Pricing",        Icon: FileText },
  disposal:   { title: "Disposal · Overall Project Value", Icon: Trash },
  signoff:    { title: "Acceptance & Sign-off",   Icon: ShieldCheck },
};

function SlideBody({ slide, pkt }) {
  switch (slide.kind) {
    case "cover":      return <CoverSlide pkt={pkt}/>;
    case "flight":     return <FlightSlide pkt={pkt}/>;
    case "roof":       return <RoofSlide pkt={pkt}/>;
    case "geometrics": return <GeometricsSlide pkt={pkt}/>;
    case "moisture":   return <MoistureSlide pkt={pkt}/>;
    case "anomalies":  return <AnomaliesSlide pkt={pkt}/>;
    case "phases":     return <PhasesSlide pkt={pkt}/>;
    case "pricing":    return <PricingSlide pkt={pkt}/>;
    case "disposal":   return <DisposalSlide pkt={pkt}/>;
    case "signoff":    return <SignoffSlide pkt={pkt}/>;
    default:           return null;
  }
}

/* --- Slide 1 · Cover --- */
function CoverSlide({ pkt }) {
  return (
    <div className="h-full flex flex-col justify-between" data-testid="deck-cover">
      <div className="flex items-center gap-4">
        <svg width="76" height="76" viewBox="0 0 100 100"
             style={{ filter: `drop-shadow(0 0 12px ${TEAL}66)` }}>
          <polygon points="50,8 92,84 8,84" fill="none" stroke={TEAL} strokeWidth="4"/>
          <polygon points="50,28 78,76 22,76" fill={ORANGE} opacity="0.9"/>
          <circle cx="50" cy="60" r="6" fill={INK}/>
        </svg>
        <div>
          <div className="text-[40px] font-bold tracking-[0.18em]"
               style={{ color: SILVER, fontFamily: "'JetBrains Mono', monospace" }}>STRATEX™</div>
          <div className="text-[11px] font-mono tracking-[0.4em] uppercase" style={{ color: TEAL }}>
            Strategic Thermal Reconnaissance
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="text-[10px] font-mono tracking-[0.4em] uppercase" style={{ color: ORANGE }}>
          // Drone-Scan Comprehensive Report
        </div>
        <h1 className="text-[52px] font-bold leading-[1.05] mt-3 tracking-tight" style={{ color: SILVER }}>
          {pkt.site.address}
        </h1>
        <div className="text-[16px] mt-3 font-mono" style={{ color: NICKEL }}>
          Prepared for <span style={{ color: SILVER }}>{pkt.client.name}</span> · by{" "}
          <span style={{ color: SILVER }}>{pkt.contractor.company}</span>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4 mt-6">
        <CoverStat label="Deliverable ID" value={pkt.deliverable_id} accent={TEAL}/>
        <CoverStat label="Project Code"  value={pkt.flight.project_code} accent={ORANGE}/>
        <CoverStat label="Pilot"          value={pkt.flight.pilot_name}/>
        <CoverStat label="Generated"      value={new Date(pkt.generated_at).toLocaleDateString()}/>
      </div>
    </div>
  );
}

function CoverStat({ label, value, accent }) {
  return (
    <div style={{
      background: PAPER_BLACK, border: `1px solid ${NICKEL}55`,
      padding: "14px 16px", borderRadius: 2,
      borderTop: accent ? `2px solid ${accent}` : undefined,
    }}>
      <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>{label}</div>
      <div className="text-[14px] font-mono mt-1 font-bold truncate" style={{ color: accent || SILVER }}>{value}</div>
    </div>
  );
}

/* --- Slide 2 · Flight Record --- */
function FlightSlide({ pkt }) {
  const f = pkt.flight || {};
  const w = f.weather || {};
  const t = f.telemetry || {};
  return (
    <div className="grid grid-cols-12 gap-4" data-testid="deck-flight">
      <div className="col-span-7 space-y-3">
        <KV icon={Plane} label="Project Code"  value={f.project_code} highlight/>
        <KV icon={User}  label="Pilot in Command" value={f.pilot_name}/>
        <KV icon={CalendarClock} label="Started"   value={fmtDT(f.started_at)}/>
        <KV icon={CalendarClock} label="Completed" value={fmtDT(f.completed_at)}/>
        <KV icon={Wind} label="Weather at Capture"
            value={`${w.sky || "—"} · ${w.temperature_f ?? "—"}°F · wind ${w.wind_mph ?? "—"} / gust ${w.gust_mph ?? "—"} mph`}/>
        <KV icon={ShieldCheck} label="Calibration"
            value={`ε ${w.emissivity ?? "—"} · ${w["ε_corrected"] ? "Radiometrically corrected" : "Uncorrected"}`}/>
      </div>
      <div className="col-span-5 grid grid-cols-2 gap-3">
        <BigStat label="Frames" value={t.frames_captured ?? "—"} unit="captured" accent={TEAL}/>
        <BigStat label="Passes" value={t.passes ?? "—"} unit="orbits" accent={ORANGE}/>
        <BigStat label="RTK Lock" value={`${t.rtk_lock_pct ?? "—"}%`} unit="precision" accent={TEAL}/>
        <BigStat label="Uplink" value={`${t.uplink_avg_dbm ?? "—"} dBm`} unit="avg signal" accent={NICKEL}/>
      </div>
    </div>
  );
}

/* --- Slide 3 · Roof Composition --- */
function RoofSlide({ pkt }) {
  const r = pkt.roof || {};
  const facets = r.facets || [];
  return (
    <div className="grid grid-cols-12 gap-4" data-testid="deck-roof">
      <div className="col-span-7">
        <div className="grid grid-cols-3 gap-3 mb-3">
          <BigStat label="Total Squares" value={Number(r.total_squares || 0).toFixed(2)} unit="sq" accent={TEAL}/>
          <BigStat label="Total Sq Ft"   value={Number(r.total_sqft || 0).toLocaleString()} unit="ft²" accent={ORANGE}/>
          <BigStat label="Valleys" value={`${Number(r.valleys_lf_total || 0).toFixed(1)}`} unit="lf"/>
        </div>
        <div className="text-[10px] font-mono tracking-[0.25em] uppercase mb-2" style={{ color: NICKEL }}>
          Facet Roll-up
        </div>
        <div className="border" style={{ borderColor: NICKEL, background: PAPER_BLACK }}>
          <table className="w-full">
            <thead>
              <tr style={{ background: INK, color: TEAL }}>
                <th className="px-3 py-1.5 text-left text-[9px] uppercase tracking-widest font-mono">Facet</th>
                <th className="px-3 py-1.5 text-left text-[9px] uppercase tracking-widest font-mono">Label</th>
                <th className="px-3 py-1.5 text-right text-[9px] uppercase tracking-widest font-mono">Sq Ft</th>
                <th className="px-3 py-1.5 text-right text-[9px] uppercase tracking-widest font-mono">Pitch</th>
                <th className="px-3 py-1.5 text-right text-[9px] uppercase tracking-widest font-mono">Exp</th>
              </tr>
            </thead>
            <tbody>
              {facets.slice(0, 8).map((f) => (
                <tr key={f.id} className="border-t" style={{ borderColor: `${NICKEL}55` }}>
                  <td className="px-3 py-1 font-mono text-[10px]" style={{ color: SILVER }}>{f.id}</td>
                  <td className="px-3 py-1 text-[11px]" style={{ color: SILVER }}>{f.label}</td>
                  <td className="px-3 py-1 font-mono text-[10px] text-right tabular-nums" style={{ color: SILVER }}>{f.sqft}</td>
                  <td className="px-3 py-1 font-mono text-[10px] text-right tabular-nums" style={{ color: SILVER }}>{f.pitch}</td>
                  <td className="px-3 py-1 font-mono text-[10px] text-right tabular-nums" style={{ color: SILVER }}>{f.exposure}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid grid-cols-2 gap-3 mt-3">
          <KV label="Primary Material" value={r.primary_material}/>
          <KV label="Sub-Layer"        value={r.sub_layer_material}/>
        </div>
      </div>
      <div className="col-span-5">
        <div className="text-[10px] font-mono tracking-[0.25em] uppercase mb-2" style={{ color: NICKEL }}>
          3D Digital Twin · Forensic Overlay
        </div>
        {pkt.twin_reference_url ? (
          <figure className="border" style={{ borderColor: TEAL, boxShadow: `0 0 24px ${TEAL}22` }}>
            <img src={pkt.twin_reference_url} alt="STRATEX 3D Digital Twin" className="w-full h-auto block"/>
          </figure>
        ) : (
          <div className="border h-full flex items-center justify-center min-h-[260px]"
               style={{ borderColor: NICKEL, background: PAPER_BLACK }}>
            <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: NICKEL }}>
              // TWIN REFERENCE UNAVAILABLE
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* --- Slide 4 · Quantified Geometry --- */
function GeometricsSlide({ pkt }) {
  const g = pkt.geometrics_extended || {};
  const items = [
    { label: "Roof · Net Squares",     value: g.total_squares_net,         unit: "sq",  Icon: Layers, accent: TEAL },
    { label: "Valley · Linear Feet",   value: g.valley_linear_feet,        unit: "lf",  Icon: Ruler,  accent: ORANGE },
    { label: "Rake & Gable · Linear",  value: g.rake_gable_linear_feet,    unit: "lf",  Icon: Ruler,  accent: "#7C3AED" },
    { label: "Wall Siding · Net Area", value: g.net_wall_siding_area_sqft, unit: "ft²", Icon: Layers, accent: "#B8865B" },
  ];
  return (
    <div className="grid grid-cols-2 gap-4" data-testid="deck-geometrics">
      {items.map((it) => (
        <div key={it.label}
          className="relative overflow-hidden"
          style={{
            background: `linear-gradient(135deg, ${PAPER_BLACK} 0%, ${INK} 100%)`,
            border: `1px solid ${NICKEL}55`,
            padding: "26px 28px",
            borderRadius: 2,
          }}>
          <div className="absolute top-0 left-0 right-0 h-[3px]" style={{ background: it.accent }}/>
          <div className="absolute -right-4 -top-4 opacity-[0.08]">
            <it.Icon size={112} color={it.accent}/>
          </div>
          <div className="relative">
            <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>{it.label}</div>
            <div className="font-mono mt-3" style={{ color: SILVER }}>
              <span className="text-[44px] font-bold tabular-nums" style={{ color: it.accent }}>
                {Number(it.value || 0).toLocaleString("en-US", {
                  minimumFractionDigits: (it.value || 0) % 1 ? 2 : 0,
                  maximumFractionDigits: 2,
                })}
              </span>
              <span className="text-[14px] ml-2" style={{ color: NICKEL }}>{it.unit}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

/* --- Slide 5 · Moisture --- */
function MoistureSlide({ pkt }) {
  const rows = pkt.moisture_diagnostics || [];
  const SEVERITY_TONE = {
    CRITICAL: { chip: "#DC2626", label: "Critical" },
    ELEVATED: { chip: ORANGE,    label: "Elevated" },
    MILD:     { chip: "#CA8A04", label: "Mild"     },
    LOW:      { chip: "#16A34A", label: "Low"      },
  };
  return (
    <div className="space-y-2" data-testid="deck-moisture">
      {rows.slice(0, 5).map((d, i) => {
        const tone = SEVERITY_TONE[d.severity] || SEVERITY_TONE.MILD;
        return (
          <article key={i}
            className="grid grid-cols-12 gap-4 items-center"
            style={{
              background: PAPER_BLACK,
              border: `1px solid ${NICKEL}55`,
              borderLeft: `4px solid ${tone.chip}`,
              padding: "12px 18px",
              borderRadius: 2,
            }}>
            <div className="col-span-3">
              <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: NICKEL }}>Grid</div>
              <div className="font-mono font-bold text-[14px] mt-0.5" style={{ color: SILVER }}>{d.grid_id}</div>
              <div className="text-[10px]" style={{ color: NICKEL }}>{d.location}</div>
            </div>
            <div className="col-span-3">
              <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: NICKEL }}>Concern</div>
              <div className="font-mono text-[11px] mt-1" style={{ color: SILVER }}>{d.concern_code}</div>
              <div className="inline-flex items-center gap-1 mt-1 px-1.5 py-0.5"
                style={{ background: `${tone.chip}22`, color: tone.chip, border: `1px solid ${tone.chip}`, borderRadius: 2 }}>
                <span className="text-[9px] font-mono tracking-[0.2em] uppercase font-bold">{tone.label}</span>
              </div>
            </div>
            <div className="col-span-2">
              <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: NICKEL }}>Probability</div>
              <div className="font-mono font-bold text-[22px] mt-1 tabular-nums" style={{ color: tone.chip }}>
                {d.probability_pct}<span className="text-[12px]" style={{ color: NICKEL }}>%</span>
              </div>
              <div className="mt-1 h-[3px] rounded overflow-hidden" style={{ background: `${tone.chip}22` }}>
                <div style={{ width: `${d.probability_pct}%`, height: "100%", background: tone.chip }}/>
              </div>
            </div>
            <div className="col-span-4">
              <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: NICKEL }}>Field Note</div>
              <div className="text-[11px] mt-1 leading-snug" style={{ color: SILVER }}>{d.notes}</div>
            </div>
          </article>
        );
      })}
    </div>
  );
}

/* --- Slide 6 · Anomalies --- */
function AnomaliesSlide({ pkt }) {
  const anomalies = (pkt.anomalies || []).slice(0, 3);
  return (
    <div className="grid grid-cols-3 gap-4" data-testid="deck-anomalies">
      {anomalies.map((a) => (
        <article key={a.id} className="flex flex-col"
          style={{
            background: PAPER_BLACK,
            border: `1px solid ${ORANGE}55`,
            borderTop: `3px solid ${ORANGE}`,
            padding: "14px 16px",
            borderRadius: 2,
          }}>
          <div className="font-mono text-[9px] tracking-[0.25em] uppercase" style={{ color: ORANGE }}>
            // {a.severity || "P1"} · {a.id} · Facet {a.facet}
          </div>
          <div className="text-[16px] font-bold mt-1" style={{ color: SILVER }}>{a.kind}</div>
          <div className="text-[11px] mt-2" style={{ color: NICKEL }}>
            <strong style={{ color: SILVER }}>{a.area_sqft}</strong> ft² affected · depth{" "}
            <strong style={{ color: SILVER }}>{a.depth_in}″</strong>
          </div>
          <div className="text-[11px] mt-2 leading-snug" style={{ color: SILVER }}>
            <span style={{ color: NICKEL }}>Remediation:</span> {a.remediation}
          </div>
          <div className="mt-auto pt-3 flex items-center justify-between"
               style={{ borderTop: `1px solid ${NICKEL}55` }}>
            <span className="font-mono text-[9px] tracking-widest uppercase px-2 py-0.5"
              style={{ background: INK, color: TEAL, border: `1px solid ${TEAL}55` }}>
              Conf {Number(a.confidence_pct).toFixed(1)}%
            </span>
            <span className="font-mono text-[13px] font-bold tabular-nums" style={{ color: ORANGE }}>
              {USD(a.remediation_cost_usd)}
            </span>
          </div>
        </article>
      ))}
    </div>
  );
}

/* --- Slide 7 · Project Phases --- */
function PhasesSlide({ pkt }) {
  const PHASE_META = {
    framing: { label: "Framing", Icon: Wrench, accent: "#7C3AED" },
    roofing: { label: "Roofing", Icon: Hammer, accent: ORANGE     },
    gutters: { label: "Gutters", Icon: Droplets, accent: TEAL    },
    siding:  { label: "Siding",  Icon: Layers, accent: "#B8865B" },
  };
  const phases = pkt.financial_phases || {};
  const keys = Object.keys(phases);
  const total = keys.reduce((s, k) => s + (Number(phases[k]?.total_price_usd) || 0), 0);
  const hours = keys.reduce((s, k) => s + (Number(phases[k]?.estimated_man_hours) || 0), 0);

  return (
    <div className="flex flex-col gap-2" data-testid="deck-phases">
      {keys.map((k) => {
        const ph = phases[k] || {};
        const meta = PHASE_META[k] || { label: k, Icon: Wrench, accent: NICKEL };
        const pct = total > 0 ? (Number(ph.total_price_usd) / total) * 100 : 0;
        return (
          <article key={k}
            className="grid grid-cols-12 gap-4 items-center"
            style={{
              background: `linear-gradient(90deg, ${PAPER_BLACK} 0%, ${INK} 100%)`,
              border: `1px solid ${NICKEL}55`,
              padding: "12px 18px",
              borderRadius: 2,
            }}>
            <div className="col-span-3 flex items-center gap-3">
              <div className="flex items-center justify-center" style={{
                width: 38, height: 38, borderRadius: 2,
                background: `${meta.accent}14`, border: `1px solid ${meta.accent}55`,
              }}>
                <meta.Icon size={18} color={meta.accent}/>
              </div>
              <div>
                <div className="text-[9px] font-mono tracking-[0.28em] uppercase" style={{ color: NICKEL }}>Phase</div>
                <div className="font-bold text-[14px] tracking-wide" style={{ color: SILVER }}>{meta.label}</div>
              </div>
            </div>
            <div className="col-span-5">
              <div className="text-[11px] leading-snug" style={{ color: SILVER }}>{ph.scope || "—"}</div>
              <div className="mt-1.5 flex items-center gap-3 text-[10px] font-mono tabular-nums" style={{ color: NICKEL }}>
                <span>{ph.estimated_man_hours} man-hours</span>
                <span>·</span>
                <span>{pct.toFixed(1)}% of total</span>
              </div>
              <div className="mt-1 h-[3px] rounded overflow-hidden" style={{ background: `${meta.accent}1F` }}>
                <div style={{ width: `${pct}%`, height: "100%", background: meta.accent }}/>
              </div>
            </div>
            <div className="col-span-4 text-right">
              <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: NICKEL }}>Phase Total</div>
              <div className="font-mono font-bold text-[20px] tabular-nums mt-0.5" style={{ color: meta.accent }}>
                {USD(ph.total_price_usd)}
              </div>
            </div>
          </article>
        );
      })}
      <div className="grid grid-cols-2 gap-3 mt-2">
        <div style={{ background: INK, color: TEAL, padding: "10px 16px", borderRadius: 2, border: `1px solid ${TEAL}55` }}>
          <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: `${TEAL}99` }}>Combined Man-Hours</div>
          <div className="font-mono text-[18px] font-bold tabular-nums">{hours.toLocaleString()}</div>
        </div>
        <div style={{ background: INK, color: ORANGE, padding: "10px 16px", borderRadius: 2, border: `1px solid ${ORANGE}55` }} className="text-right">
          <div className="text-[9px] font-mono tracking-[0.25em] uppercase" style={{ color: `${ORANGE}99` }}>Phase Subtotal</div>
          <div className="font-mono text-[18px] font-bold tabular-nums">{USD(total)}</div>
        </div>
      </div>
    </div>
  );
}

/* --- Slide 8 · Pricing --- */
function PricingSlide({ pkt }) {
  const p = pkt.pricing || {};
  const lineItems = (p.line_items || []).slice(0, 6);
  const anomalyLines = (p.anomaly_remediations || []).slice(0, 4);
  return (
    <div className="grid grid-cols-12 gap-4" data-testid="deck-pricing">
      <div className="col-span-8">
        <div className="border" style={{ borderColor: NICKEL, background: PAPER_BLACK }}>
          <table className="w-full">
            <thead>
              <tr style={{ background: INK, color: TEAL }}>
                <th className="px-3 py-2 text-left text-[10px] uppercase tracking-widest font-mono">Line Item</th>
                <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest font-mono">Amount</th>
              </tr>
            </thead>
            <tbody>
              {lineItems.map((li, i) => (
                <tr key={i} className="border-t" style={{ borderColor: `${NICKEL}55` }}>
                  <td className="px-3 py-1.5 text-[11px]" style={{ color: SILVER }}>{li.label}</td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-right tabular-nums" style={{ color: SILVER }}>{USD(li.amount)}</td>
                </tr>
              ))}
              {anomalyLines.map((li, i) => (
                <tr key={`a${i}`} className="border-t" style={{ borderColor: `${NICKEL}55`, background: `${ORANGE}0A` }}>
                  <td className="px-3 py-1.5 text-[11px]" style={{ color: ORANGE }}>{li.label}</td>
                  <td className="px-3 py-1.5 font-mono text-[11px] text-right tabular-nums" style={{ color: ORANGE }}>{USD(li.amount)}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="border-t" style={{ borderColor: NICKEL }}>
                <td className="px-3 py-1.5 text-[11px] font-semibold" style={{ color: SILVER }}>Subtotal</td>
                <td className="px-3 py-1.5 font-mono text-[11px] text-right tabular-nums font-semibold" style={{ color: SILVER }}>{USD(p.subtotal_usd)}</td>
              </tr>
              <tr>
                <td className="px-3 py-1 text-[10px]" style={{ color: NICKEL }}>Overhead ({Math.round((p.overhead_pct || 0) * 100)}%)</td>
                <td className="px-3 py-1 font-mono text-[10px] text-right tabular-nums" style={{ color: NICKEL }}>{USD(p.overhead_usd)}</td>
              </tr>
              <tr>
                <td className="px-3 py-1 text-[10px]" style={{ color: NICKEL }}>Margin ({Math.round((p.margin_pct || 0) * 100)}%)</td>
                <td className="px-3 py-1 font-mono text-[10px] text-right tabular-nums" style={{ color: NICKEL }}>{USD(p.margin_usd)}</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
      <div className="col-span-4">
        <div style={{
          background: `linear-gradient(135deg, ${INK} 0%, #1B2233 100%)`,
          border: `1px solid ${TEAL}`,
          padding: "24px 22px",
          borderRadius: 2,
          boxShadow: `0 0 28px ${TEAL}22, inset 0 0 0 1px ${TEAL}33`,
        }}>
          <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: `${TEAL}AA` }}>Total Estimate</div>
          <div className="font-mono font-bold text-[34px] mt-2 tabular-nums leading-none"
               style={{ color: TEAL, textShadow: `0 0 10px ${TEAL}66` }}>
            {USD(p.total_usd)}
          </div>
          <div className="text-[10px] mt-3 font-mono leading-snug" style={{ color: NICKEL }}>
            Valid through <span style={{ color: SILVER }}>{p.valid_through_iso}</span><br/>
            ({p.valid_for_days} days from issue)
          </div>
          <div className="text-[10px] mt-3 font-mono leading-snug" style={{ color: NICKEL }}>
            Pricing subject to material market shifts &gt; 5%.
          </div>
        </div>
      </div>
    </div>
  );
}

/* --- Slide 9 · Disposal --- */
function DisposalSlide({ pkt }) {
  const d = pkt.disposal_logistics || {};
  return (
    <div className="grid grid-cols-3 gap-4" data-testid="deck-disposal">
      <div style={{ background: PAPER_BLACK, border: `1px solid ${NICKEL}55`, padding: "26px 28px", borderRadius: 2 }}>
        <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>Dumpster · Flat Fee</div>
        <div className="font-mono font-bold text-[36px] mt-3 tabular-nums" style={{ color: SILVER }}>
          {USD(d.dumpster_flat_fee_usd)}
        </div>
      </div>
      <div style={{ background: PAPER_BLACK, border: `1px solid ${NICKEL}55`, padding: "26px 28px", borderRadius: 2 }}>
        <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>Combined Man-Hours</div>
        <div className="font-mono font-bold text-[36px] mt-3 tabular-nums" style={{ color: SILVER }}>
          {Number(d.total_combined_man_hours || 0).toLocaleString()}
        </div>
      </div>
      <div style={{
        background: `linear-gradient(135deg, ${INK} 0%, #1B2233 100%)`,
        border: `1px solid ${TEAL}`,
        padding: "26px 28px",
        borderRadius: 2,
        boxShadow: `0 0 28px ${TEAL}22, inset 0 0 0 1px ${TEAL}33`,
      }}>
        <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: `${TEAL}AA` }}>Overall Project Value</div>
        <div className="font-mono font-bold text-[36px] mt-3 tabular-nums" style={{ color: TEAL, textShadow: `0 0 10px ${TEAL}66` }}>
          {USD(d.overall_total_project_value_usd)}
        </div>
      </div>
    </div>
  );
}

/* --- Slide 10 · Sign-off --- */
function SignoffSlide({ pkt }) {
  return (
    <div className="h-full flex flex-col" data-testid="deck-signoff">
      <div className="text-[12px] leading-relaxed max-w-[820px]" style={{ color: SILVER }}>
        This deliverable was assembled from radiometrically-corrected drone telemetry. STRATEX™ certifies
        the geometric measurements and forensic classifications above; remediation pricing reflects the
        contractor's standard schedule and is subject to on-site verification.
      </div>
      <div className="grid grid-cols-2 gap-10 mt-10">
        <div>
          <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>Authorized by</div>
          <div className="h-14 border-b mt-2" style={{ borderColor: SILVER }}/>
          <div className="text-[12px] mt-2" style={{ color: SILVER }}>
            <strong>{pkt.contractor.company}</strong> — Project Lead
          </div>
          {pkt.contractor.license_number && (
            <div className="text-[10px] font-mono mt-1 flex items-center gap-1.5" style={{ color: NICKEL }}>
              <Award size={11}/> License No. {pkt.contractor.license_number}
            </div>
          )}
        </div>
        <div>
          <div className="text-[10px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>Accepted by</div>
          <div className="h-14 border-b mt-2" style={{ borderColor: SILVER }}/>
          <div className="text-[12px] mt-2" style={{ color: SILVER }}>
            {pkt.client.name} — Homeowner / Property Owner
          </div>
          <div className="text-[10px] font-mono mt-1 flex items-center gap-1.5" style={{ color: NICKEL }}>
            <MapPin size={11}/> {pkt.site.address}
          </div>
        </div>
      </div>
      <div className="mt-auto pt-6 text-[10px] font-mono tracking-widest uppercase" style={{ color: NICKEL }}>
        // END OF DECK · STRATEX™ {pkt.deliverable_id}
      </div>
    </div>
  );
}

/* ============================================================
   PRIMITIVES
   ============================================================ */

function KV({ icon: Icon, label, value, highlight }) {
  return (
    <div className="flex items-center gap-3"
      style={{
        background: PAPER_BLACK, border: `1px solid ${NICKEL}55`,
        padding: "10px 14px", borderRadius: 2,
        borderLeft: highlight ? `3px solid ${TEAL}` : `1px solid ${NICKEL}55`,
      }}>
      {Icon && <Icon size={14} color={NICKEL}/>}
      <div className="flex-1 min-w-0">
        <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>{label}</div>
        <div className="text-[13px] font-mono mt-0.5 truncate"
             style={{ color: highlight ? TEAL : SILVER }}>{value || "—"}</div>
      </div>
    </div>
  );
}

function BigStat({ label, value, unit, accent }) {
  return (
    <div style={{
      background: PAPER_BLACK, border: `1px solid ${NICKEL}55`,
      padding: "14px 16px", borderRadius: 2,
      borderTop: accent ? `2px solid ${accent}` : undefined,
    }}>
      <div className="text-[9px] font-mono tracking-[0.3em] uppercase" style={{ color: NICKEL }}>{label}</div>
      <div className="font-mono mt-1.5" style={{ color: accent || SILVER }}>
        <span className="text-[22px] font-bold tabular-nums">{value}</span>
        {unit && <span className="text-[10px] ml-1.5" style={{ color: NICKEL }}>{unit}</span>}
      </div>
    </div>
  );
}

function FailPanel({ err }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0B0F19] p-8">
      <div className="border max-w-md p-6" style={{ borderColor: ORANGE, background: "rgba(255,84,0,0.06)" }}>
        <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: ORANGE }}>// DECK FAILED</div>
        <p className="text-silver text-[13px]">{err}</p>
      </div>
    </div>
  );
}

function DeckCSS() {
  return (
    <style>{`
      .deck-slide {
        width: min(1180px, 96vw);
        aspect-ratio: 16 / 9;
        padding: 44px 56px 28px 56px;
        margin: 16px auto;
        display: flex;
        flex-direction: column;
      }
      .deck-content {
        flex: 1;
        min-height: 0;
        display: flex;
        flex-direction: column;
      }
      .deck-content > :last-child { flex: 1; min-height: 0; }
      .deck-footer {
        margin-top: 16px;
        padding-top: 10px;
      }
      .screen-deck { display: block; }
      .print-deck  { display: none; }

      /* Mobile (<= 768px): drop 16:9, become tall scrollable cards */
      @media (max-width: 768px) {
        .screen-deck {
          align-items: flex-start !important;
          min-height: 0 !important;
        }
        .deck-slide {
          width: 100%;
          aspect-ratio: auto;
          min-height: calc(100vh - 88px);
          padding: 20px 16px 16px 16px;
          margin: 0 auto;
        }
        .deck-slide [class*="text-[40px]"] { font-size: 28px !important; }
        .deck-slide [class*="text-[52px]"] { font-size: 30px !important; line-height: 1.1 !important; }
        .deck-slide [class*="text-[44px]"] { font-size: 32px !important; }
        .deck-slide [class*="text-[36px]"] { font-size: 28px !important; }
        .deck-slide [class*="text-[34px]"] { font-size: 26px !important; }
        .deck-slide [class*="text-[22px]"] { font-size: 18px !important; }
        .deck-slide [class*="text-[20px]"] { font-size: 16px !important; }
        /* Collapse all multi-column grids to single column on phones */
        .deck-slide .grid.grid-cols-2,
        .deck-slide .grid.grid-cols-3,
        .deck-slide .grid.grid-cols-4,
        .deck-slide .grid.grid-cols-12 {
          grid-template-columns: 1fr !important;
        }
        /* Inside 12-col rows (moisture, phases), let children span full width */
        .deck-slide [class*="col-span-"] {
          grid-column: 1 / -1 !important;
        }
        /* Pricing table column needs horizontal scroll */
        [data-testid="deck-pricing"] table { min-width: 420px; }
        [data-testid="deck-pricing"] > div:first-child {
          overflow-x: auto;
          -webkit-overflow-scrolling: touch;
        }
        /* Roof facet table */
        [data-testid="deck-roof"] table { font-size: 10px; }
      }

      @media print {
        @page { size: letter landscape; margin: 0; }
        body { background: #0B0F19 !important; }
        .screen-deck, .no-print { display: none !important; }
        .print-deck { display: block !important; }
        .deck-slide-print {
          width: 11in;
          height: 8.5in;
          aspect-ratio: auto;
          min-height: 0 !important;
          margin: 0;
          page-break-after: always;
          break-after: page;
          box-shadow: none !important;
        }
        .deck-slide-print:last-child {
          page-break-after: auto;
          break-after: auto;
        }
      }
    `}</style>
  );
}
