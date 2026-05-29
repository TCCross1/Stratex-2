/**
 * /contractor/deliverable/:jobId — Print-ready STRATEX™ deliverable packet.
 *
 * Shortcut: /deliverable/demo  →  uses the canonical AD-KY041 seed.
 *
 * This is exactly what the contractor hands to the homeowner. Optimized for
 * both screen review and print/PDF export (Cmd-P → Save as PDF).
 */
import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Printer, MapPin, User, CalendarClock, Wind, ShieldCheck, Plane, FileText, Layers, AlertTriangle, RotateCw } from "lucide-react";
import { api } from "@/lib/api";

const TEAL = "#00F5D4";
const ORANGE = "#FF5400";
const NICKEL = "#3A4350";
const INK = "#0B0F19";
const PAPER = "#F7F8FA";
const PAPER_INK = "#0F141C";

const USD = (n) =>
  Number(n || 0).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 2 });

function fmtDT(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", timeZoneName: "short" });
  } catch { return iso; }
}

export default function ContractorDeliverable() {
  const { jobId } = useParams();
  const effectiveId = jobId || "crown-demo";
  const [pkt, setPkt] = useState(null);
  const [err, setErr] = useState(null);

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

  if (err) return <FailPanel err={err}/>;
  if (!pkt) return (
    <div className="min-h-screen bg-[#0B0F19] text-silver flex items-center justify-center">
      <div className="font-mono text-[11px] uppercase tracking-widest" style={{ color: TEAL }}>// ASSEMBLING DELIVERABLE…</div>
    </div>
  );

  return (
    <div className="min-h-screen" style={{ background: INK, color: "#E2E8F0" }} data-testid="deliverable-root">
      <PrintCSS/>

      {/* Screen-only toolbar */}
      <div className="no-print sticky top-0 z-30 flex items-center justify-between px-4 py-3 border-b backdrop-blur"
           style={{ background: "rgba(11,15,25,0.85)", borderColor: NICKEL }}>
        <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: TEAL }}>
          // STRATEX™ DELIVERABLE · {pkt.deliverable_id}
        </div>
        <div className="flex gap-2">
          <button onClick={() => window.location.reload()}
            className="font-mono text-[10px] uppercase tracking-widest border px-3 py-1.5 inline-flex items-center gap-2"
            style={{ borderColor: `${TEAL}55`, color: TEAL }}
            data-testid="deliverable-refresh">
            <RotateCw size={11}/> Refresh
          </button>
          <button onClick={() => window.print()}
            className="font-mono text-[10px] uppercase tracking-widest px-4 py-1.5 inline-flex items-center gap-2"
            style={{ background: TEAL, color: INK }}
            data-testid="deliverable-print">
            <Printer size={12}/> Print / Save as PDF
          </button>
        </div>
      </div>

      {/* Paper sheet */}
      <article className="mx-auto my-6 print:my-0 shadow-2xl print:shadow-none" style={{
        background: PAPER, color: PAPER_INK, width: "min(900px, 100%)", padding: "44px 56px",
      }} data-testid="deliverable-paper">
        <Letterhead pkt={pkt}/>
        <ClientFlightBlock pkt={pkt}/>
        <RoofComposition pkt={pkt}/>
        <AnomalyFindings pkt={pkt}/>
        <PricingTable pkt={pkt}/>
        <SignatureBlock pkt={pkt}/>
        <Footer pkt={pkt}/>
      </article>
    </div>
  );
}

/* -------------------- Sub-components -------------------- */

function Letterhead({ pkt }) {
  return (
    <header className="flex items-start justify-between pb-5 mb-5"
            style={{ borderBottom: `2px solid ${INK}` }}>
      <div className="flex items-center gap-3">
        <svg width="58" height="58" viewBox="0 0 100 100" style={{ filter: "drop-shadow(0 0 6px rgba(0,245,212,0.4))" }}>
          <polygon points="50,8 92,84 8,84" fill="none" stroke={TEAL} strokeWidth="4"/>
          <polygon points="50,28 78,76 22,76" fill={ORANGE} opacity="0.85"/>
          <circle cx="50" cy="60" r="6" fill={INK}/>
        </svg>
        <div>
          <div className="text-2xl font-bold tracking-[0.18em]" style={{ color: INK, fontFamily: "'JetBrains Mono', monospace" }}>STRATEX™</div>
          <div className="text-[10px] tracking-[0.32em] uppercase" style={{ color: NICKEL }}>
            {pkt.platform.tagline}
          </div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-[10px] tracking-[0.28em] uppercase font-mono" style={{ color: NICKEL }}>Deliverable</div>
        <div className="text-sm font-mono mt-0.5" style={{ color: INK }}>{pkt.deliverable_id}</div>
        <div className="text-[10px] font-mono mt-1" style={{ color: NICKEL }}>
          Generated · {new Date(pkt.generated_at).toLocaleDateString()}
        </div>
        <div className="text-[10px] font-mono" style={{ color: NICKEL }}>
          Report Engine v{pkt.platform.report_version}
        </div>
      </div>
    </header>
  );
}

function ClientFlightBlock({ pkt }) {
  return (
    <section className="grid grid-cols-2 gap-6 mb-6" data-testid="deliverable-client-flight">
      <Block title="PREPARED FOR" testid="deliverable-client">
        <Row icon={User} label="Client" value={pkt.client.name}/>
        <Row icon={MapPin} label="Property" value={pkt.site.address}/>
        <Row label="Email" value={pkt.client.email}/>
        <Row label="Phone" value={pkt.client.phone}/>
      </Block>
      <Block title="PREPARED BY">
        <Row label="Contractor" value={pkt.contractor.company} bold/>
        <Row label="Region" value={pkt.contractor.address}/>
      </Block>

      <Block title="FLIGHT RECORD" wide testid="deliverable-flight">
        <div className="grid grid-cols-2 gap-x-6 gap-y-1">
          <Row icon={Plane} label="Project Code" value={pkt.flight.project_code} bold/>
          <Row icon={User} label="Pilot in Command" value={pkt.flight.pilot_name}/>
          <Row icon={CalendarClock} label="Flight Started" value={fmtDT(pkt.flight.started_at)}/>
          <Row icon={CalendarClock} label="Flight Completed" value={fmtDT(pkt.flight.completed_at)}/>
          <Row icon={Wind} label="Weather at Capture"
               value={`${pkt.flight.weather.sky || "—"} · ${pkt.flight.weather.temperature_f ?? "—"}°F · wind ${pkt.flight.weather.wind_mph ?? "—"}/${pkt.flight.weather.gust_mph ?? "—"}mph`}/>
          <Row icon={ShieldCheck} label="Calibration"
               value={`ε ${pkt.flight.weather.emissivity ?? "—"} · ${pkt.flight.weather.ε_corrected ? "Radiometrically corrected" : "Uncorrected"}`}/>
          <Row label="Frames Captured" value={`${pkt.flight.telemetry.frames_captured ?? "—"} · ${pkt.flight.telemetry.passes ?? "—"} passes`}/>
          <Row label="RTK / Uplink"
               value={`${pkt.flight.telemetry.rtk_lock_pct ?? "—"}% lock · ${pkt.flight.telemetry.uplink_avg_dbm ?? "—"} dBm avg`}/>
        </div>
      </Block>
    </section>
  );
}

function RoofComposition({ pkt }) {
  const r = pkt.roof || {};
  return (
    <section className="mb-6" data-testid="deliverable-roof">
      <SectionTitle icon={Layers} label="ROOF COMPOSITION · DIGITAL TWIN"/>
      <div className="grid grid-cols-3 gap-3">
        <Metric label="Total Squares" value={r.total_squares?.toFixed(2)}/>
        <Metric label="Total Sq Ft" value={r.total_sqft?.toLocaleString()}/>
        <Metric label="Valley Linear Ft" value={r.valleys_lf_total ? `${r.valleys_lf_total.toFixed(2)} lf` : "—"}/>
        <Metric label="Primary Material" value={r.primary_material} wide/>
        <Metric label="Sub-Layer" value={r.sub_layer_material} wide/>
      </div>

      <div className="mt-4 grid grid-cols-[1.2fr_1fr] gap-3">
        <table className="w-full border" style={{ borderColor: NICKEL, background: "#fff" }}>
          <thead>
            <tr style={{ background: INK, color: TEAL }}>
              <th className="px-3 py-2 text-left text-[10px] uppercase tracking-widest font-mono">Facet</th>
              <th className="px-3 py-2 text-left text-[10px] uppercase tracking-widest font-mono">Label</th>
              <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest font-mono">Sq Ft</th>
              <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest font-mono">Pitch</th>
              <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest font-mono">Exp</th>
            </tr>
          </thead>
          <tbody>
            {(r.facets || []).map((f) => (
              <tr key={f.id} className="border-t" style={{ borderColor: "#E4E7EC" }}>
                <td className="px-3 py-2 font-mono text-[11px]">{f.id}</td>
                <td className="px-3 py-2 text-[12px]">{f.label}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-right">{f.sqft}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-right">{f.pitch}</td>
                <td className="px-3 py-2 font-mono text-[11px] text-right">{f.exposure}</td>
              </tr>
            ))}
          </tbody>
        </table>

        {pkt.twin_reference_url && (
          <figure className="border" style={{ borderColor: NICKEL }}>
            <img src={pkt.twin_reference_url} alt="STRATEX 3D Digital Twin Reference" className="w-full h-auto block"/>
            <figcaption className="px-2 py-1 font-mono text-[9.5px] tracking-widest uppercase"
                        style={{ background: INK, color: TEAL }}>
              3D Digital Twin · Forensic Overlay
            </figcaption>
          </figure>
        )}
      </div>
    </section>
  );
}

function AnomalyFindings({ pkt }) {
  const anomalies = pkt.anomalies || [];
  if (anomalies.length === 0) return null;
  return (
    <section className="mb-6" data-testid="deliverable-anomalies">
      <SectionTitle icon={AlertTriangle} label="ANOMALY FINDINGS"/>
      <div className="space-y-3">
        {anomalies.map((a) => (
          <article key={a.id} className="border-l-4 p-3"
                   style={{ borderLeftColor: ORANGE, background: "#FFF7F2", borderColor: NICKEL }}>
            <div className="flex items-start justify-between gap-3 mb-2">
              <div>
                <div className="font-mono text-[10px] tracking-widest uppercase" style={{ color: ORANGE }}>
                  // {a.severity || "P1"} · {a.id} · Facet {a.facet}
                </div>
                <div className="text-[14px] font-semibold mt-0.5" style={{ color: INK }}>
                  {a.kind}
                </div>
              </div>
              <span className="font-mono text-[10px] tracking-widest uppercase px-2 py-0.5"
                    style={{ background: INK, color: TEAL }}>
                Confidence {Number(a.confidence_pct).toFixed(2)}%
              </span>
            </div>
            <div className="grid grid-cols-[1.2fr_1fr] gap-3">
              <div>
                <div className="text-[12px] leading-relaxed" style={{ color: PAPER_INK }}>
                  <strong>Affected area:</strong> {a.area_sqft} sq ft · depth {a.depth_in}″
                </div>
                <div className="text-[12px] mt-2 leading-relaxed" style={{ color: PAPER_INK }}>
                  <strong>Recommended remediation:</strong> {a.remediation}
                </div>
                <div className="font-mono text-[11px] mt-2" style={{ color: ORANGE }}>
                  Remediation cost · {USD(a.remediation_cost_usd)}
                </div>
              </div>
              {a.thumbnail_url && (
                <figure className="border" style={{ borderColor: NICKEL }}>
                  <img src={a.thumbnail_url} alt={`Anomaly ${a.id}`} className="w-full h-auto block"/>
                  <figcaption className="px-2 py-1 font-mono text-[9px] tracking-widest uppercase"
                              style={{ background: INK, color: TEAL }}>
                    Thermal capture · {a.id}
                  </figcaption>
                </figure>
              )}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function PricingTable({ pkt }) {
  const p = pkt.pricing || {};
  return (
    <section className="mb-6" data-testid="deliverable-pricing">
      <SectionTitle icon={FileText} label="STANDARD PRICING"/>
      <table className="w-full" style={{ background: "#fff", border: `1px solid ${NICKEL}` }}>
        <thead>
          <tr style={{ background: INK, color: TEAL }}>
            <th className="px-3 py-2 text-left text-[10px] uppercase tracking-widest font-mono">Line item</th>
            <th className="px-3 py-2 text-right text-[10px] uppercase tracking-widest font-mono">Amount</th>
          </tr>
        </thead>
        <tbody>
          {(p.line_items || []).map((li, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "#E4E7EC" }}>
              <td className="px-3 py-2 text-[12px]">{li.label}</td>
              <td className="px-3 py-2 font-mono text-[12px] text-right tabular-nums">{USD(li.amount)}</td>
            </tr>
          ))}
          {(p.anomaly_remediations || []).map((li, i) => (
            <tr key={`a${i}`} className="border-t" style={{ borderColor: "#E4E7EC", background: "#FFF7F2" }}>
              <td className="px-3 py-2 text-[12px]" style={{ color: ORANGE }}>{li.label}</td>
              <td className="px-3 py-2 font-mono text-[12px] text-right tabular-nums" style={{ color: ORANGE }}>{USD(li.amount)}</td>
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t" style={{ borderColor: NICKEL }}>
            <td className="px-3 py-2 text-[12px] font-semibold">Subtotal</td>
            <td className="px-3 py-2 font-mono text-[12px] text-right tabular-nums font-semibold">{USD(p.subtotal_usd)}</td>
          </tr>
          <tr><td className="px-3 py-1 text-[11px]" style={{ color: NICKEL }}>
                Overhead ({Math.round((p.overhead_pct || 0) * 100)}%)</td>
              <td className="px-3 py-1 font-mono text-[11px] text-right tabular-nums" style={{ color: NICKEL }}>{USD(p.overhead_usd)}</td></tr>
          <tr><td className="px-3 py-1 text-[11px]" style={{ color: NICKEL }}>
                Margin ({Math.round((p.margin_pct || 0) * 100)}%)</td>
              <td className="px-3 py-1 font-mono text-[11px] text-right tabular-nums" style={{ color: NICKEL }}>{USD(p.margin_usd)}</td></tr>
          <tr style={{ background: INK, color: TEAL }}>
            <td className="px-3 py-3 text-[13px] font-bold uppercase tracking-widest">Total · Estimate</td>
            <td className="px-3 py-3 font-mono text-[16px] text-right tabular-nums font-bold" data-testid="deliverable-total">{USD(p.total_usd)}</td>
          </tr>
        </tfoot>
      </table>
      <div className="text-[10px] mt-1.5 font-mono" style={{ color: NICKEL }}>
        Estimate valid through {p.valid_through_iso} ({p.valid_for_days} days). Pricing subject to material market shifts &gt;5%.
      </div>
    </section>
  );
}

function SignatureBlock({ pkt }) {
  return (
    <section className="grid grid-cols-2 gap-6 mt-6">
      <div>
        <div className="text-[10px] font-mono tracking-widest uppercase" style={{ color: NICKEL }}>Authorized by</div>
        <div className="h-12 border-b" style={{ borderColor: INK }}/>
        <div className="text-[11px] mt-1" style={{ color: INK }}>
          <strong>{pkt.contractor.company}</strong> — Project Lead
        </div>
      </div>
      <div>
        <div className="text-[10px] font-mono tracking-widest uppercase" style={{ color: NICKEL }}>Accepted by</div>
        <div className="h-12 border-b" style={{ borderColor: INK }}/>
        <div className="text-[11px] mt-1" style={{ color: INK }}>
          {pkt.client.name} — Homeowner / Property Owner
        </div>
      </div>
    </section>
  );
}

function Footer({ pkt }) {
  return (
    <footer className="mt-8 pt-3 text-[10px] font-mono" style={{ borderTop: `1px solid ${NICKEL}`, color: NICKEL }}>
      Generated by STRATEX™ Strategic Thermal Reconnaissance · {pkt.deliverable_id} ·
      {" "}This deliverable was assembled from radiometrically-corrected drone telemetry. STRATEX certifies
      the geometric measurements and forensic classifications above; remediation pricing reflects the
      contractor's standard schedule and is subject to on-site verification.
    </footer>
  );
}

function Block({ title, children, wide, testid }) {
  return (
    <div className={wide ? "col-span-2" : ""} data-testid={testid}>
      <div className="text-[10px] font-mono tracking-widest uppercase mb-1.5" style={{ color: NICKEL }}>
        {title}
      </div>
      <div className="space-y-0.5">{children}</div>
    </div>
  );
}

function Row({ icon: Icon, label, value, bold }) {
  return (
    <div className="flex items-center gap-2 text-[12px]" style={{ color: PAPER_INK }}>
      {Icon ? <Icon size={12} style={{ color: NICKEL }}/> : <span style={{ width: 12 }}/>}
      <span style={{ color: NICKEL, minWidth: 100 }}>{label}</span>
      <span style={{ fontWeight: bold ? 600 : 400 }}>{value}</span>
    </div>
  );
}

function SectionTitle({ icon: Icon, label }) {
  return (
    <div className="flex items-center gap-2 mb-2 pb-1" style={{ borderBottom: `1px solid ${INK}` }}>
      <Icon size={14} style={{ color: ORANGE }}/>
      <h2 className="text-[12px] font-bold tracking-[0.2em] uppercase" style={{ color: INK, fontFamily: "'JetBrains Mono', monospace" }}>
        {label}
      </h2>
    </div>
  );
}

function Metric({ label, value, wide }) {
  return (
    <div className={`border p-2 ${wide ? "col-span-3" : ""}`} style={{ borderColor: NICKEL, background: "#fff" }}>
      <div className="text-[9px] font-mono tracking-widest uppercase" style={{ color: NICKEL }}>{label}</div>
      <div className="text-[14px] font-semibold mt-0.5" style={{ color: INK }}>{value ?? "—"}</div>
    </div>
  );
}

function FailPanel({ err }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-[#0B0F19] p-8">
      <div className="border max-w-md p-6" style={{ borderColor: ORANGE, background: "rgba(255,84,0,0.06)" }}>
        <div className="font-mono text-[10px] tracking-widest uppercase mb-2" style={{ color: ORANGE }}>// DELIVERABLE FAILED</div>
        <p className="text-silver text-[13px]">{err}</p>
      </div>
    </div>
  );
}

function PrintCSS() {
  return (
    <style>{`
      @media print {
        .no-print { display: none !important; }
        body { background: #fff !important; }
        article { box-shadow: none !important; margin: 0 !important; }
        @page { size: letter; margin: 0.5in; }
      }
    `}</style>
  );
}
