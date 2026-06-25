"""Build a 9-page Future-Noire HTML report from a Stratex analysis dict.

This module is imported by /app/backend/routes/demo_scan.py to produce
the HTML that Playwright then renders into a tabloid (11x17) landscape
PDF.
"""
from __future__ import annotations

from html import escape
from typing import Any


def _usd(n: float) -> str:
    try:
        return f"${n:,.2f}"
    except Exception:
        return "$0.00"


def _sev_color(s: str) -> str:
    return {
        "URGENT": "#FF2D78", "SEVERE": "#FF2D78", "HIGH": "#FF7B00",
        "MED": "#FFB020", "FAILED": "#FF2D78", "WORN": "#FFB020",
        "LOW": "#00FF9C", "NONE": "#7C8A9E", "OK": "#00FF9C",
    }.get(s, "#00E5FF")


CSS = r"""
@page { size: 17in 11in; margin: 0; }
* { box-sizing: border-box; margin: 0; padding: 0; }
:root {
  --bg: #02060B; --bg2: #0B1320; --card: rgba(15,22,34,0.65);
  --cyan: #4DF6FF; --amber: #FFB020; --green: #00FF9C;
  --mag: #FF2D78; --orange: #FF7B00; --silver: #E2E8F0;
  --muted: #7C8A9E; --line: rgba(77,246,255,0.18);
}
html, body { background: var(--bg); color: var(--silver);
  font-family: 'Space Grotesk', 'Helvetica Neue', sans-serif; }
.mono { font-family: 'JetBrains Mono', monospace; }
.page { width: 17in; height: 11in; padding: 0.55in 0.65in; position: relative;
  background:
    radial-gradient(ellipse at 80% 10%, rgba(77,246,255,0.07) 0%, transparent 50%),
    radial-gradient(ellipse at 10% 90%, rgba(255,123,0,0.06) 0%, transparent 50%),
    linear-gradient(180deg, #03070D 0%, #02060B 100%);
  page-break-after: always; overflow: hidden; }
.page:last-child { page-break-after: auto; }

/* === STRATEX OFFICIAL WORDMARK === */
.wm { font-family: 'Space Grotesk', sans-serif; font-weight: 700;
  letter-spacing: 0.04em; line-height: 1; display: inline-flex; align-items: baseline;
  white-space: nowrap; }
.wm .strat {
  background: linear-gradient(180deg, #FFFFFF 0%, #B6BFCB 70%, #8A95A3 100%);
  -webkit-background-clip: text; background-clip: text; color: transparent;
  -webkit-text-fill-color: transparent;
}
.wm .ex {
  color: transparent; -webkit-text-stroke: 1.4px #4DF6FF;
  text-shadow: 0 0 5px rgba(77,246,255,0.85), 0 0 12px rgba(77,246,255,0.5);
  font-style: italic; margin-left: 0.04em;
}
.wm .tm { color: #4DF6FF; opacity: 0.9; margin-left: 0.16em; }

.hdr { display: flex; justify-content: space-between; align-items: center;
  border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 18px; }
.hdr .crumb { font-family: 'JetBrains Mono', monospace; font-size: 9px;
  color: var(--muted); letter-spacing: 0.22em; }
.eyebrow { font-family: 'JetBrains Mono', monospace; font-size: 9px;
  color: var(--cyan); letter-spacing: 0.32em; }
h1 { font-size: 42px; font-weight: 700; letter-spacing: -0.02em;
  margin-top: 4px; color: #fff; }
h2 { font-size: 11px; letter-spacing: 0.28em; color: var(--amber);
  font-family: 'JetBrains Mono', monospace; margin-bottom: 10px; }
.frame { background: var(--card); border: 1px solid var(--line);
  border-radius: 6px; padding: 16px; backdrop-filter: blur(8px); }
.frame.cyan { border-color: rgba(0,229,255,0.45); box-shadow: 0 0 28px rgba(0,229,255,0.10) inset; }
.frame.amber { border-color: rgba(255,176,32,0.45); box-shadow: 0 0 28px rgba(255,176,32,0.10) inset; }
.frame.green { border-color: rgba(0,255,156,0.45); box-shadow: 0 0 28px rgba(0,255,156,0.10) inset; }
.frame.mag   { border-color: rgba(255,45,120,0.45); box-shadow: 0 0 28px rgba(255,45,120,0.10) inset; }
.kpi { display: flex; flex-direction: column; gap: 4px; }
.kpi .l { font-family: 'JetBrains Mono', monospace; font-size: 8px;
  color: var(--muted); letter-spacing: 0.22em; }
.kpi .v { font-family: 'Space Grotesk', sans-serif; font-size: 26px;
  font-weight: 700; color: #fff; }
.kpi .u { font-size: 10px; color: var(--muted); font-family: 'JetBrains Mono', monospace; }
table { width: 100%; border-collapse: collapse; font-family: 'JetBrains Mono', monospace;
  font-size: 9.5px; color: var(--silver); }
thead th { text-align: left; padding: 8px 10px; color: var(--cyan);
  font-size: 8.5px; letter-spacing: 0.18em; border-bottom: 1px solid rgba(0,229,255,0.35);
  background: rgba(0,229,255,0.05); }
tbody td { padding: 7px 10px; border-bottom: 1px solid rgba(255,255,255,0.04); }
tbody tr:nth-child(even) td { background: rgba(255,255,255,0.015); }
.right { text-align: right; }
.pill { display: inline-block; padding: 2px 8px; border-radius: 100px;
  font-family: 'JetBrains Mono', monospace; font-size: 8px; letter-spacing: 0.14em;
  border: 1px solid currentColor; }
.gauge { display: inline-block; width: 110px; height: 70px; position: relative; }
.gauge svg { width: 100%; height: 100%; }
.classif { position: absolute; bottom: 16px; left: 0; right: 0; text-align: center;
  font-family: 'JetBrains Mono', monospace; font-size: 8px; letter-spacing: 0.28em;
  color: var(--muted); }
.glow-cyan  { color: var(--cyan);  text-shadow: 0 0 4px currentColor; }
.glow-amber { color: var(--amber); text-shadow: 0 0 4px currentColor; }
.glow-green { color: var(--green); text-shadow: 0 0 4px currentColor; }
.glow-mag   { color: var(--mag);   text-shadow: 0 0 4px currentColor; }
.glow-orange{ color: var(--orange);text-shadow: 0 0 4px currentColor; }
.row { display: grid; gap: 14px; }
.row.c2 { grid-template-columns: 1fr 1fr; }
.row.c3 { grid-template-columns: 1fr 1fr 1fr; }
.row.c4 { grid-template-columns: 1fr 1fr 1fr 1fr; }
.tag { font-family: 'JetBrains Mono', monospace; font-size: 8px;
  color: var(--muted); letter-spacing: 0.18em; }
"""


# ── CONTRACTOR BRANDING ──────────────────────────────────────────────────
# Active contractor for the demo. Replace / extend by passing
# `_contractor` in the analysis dict to override per-job.
CONTRACTOR_DEFAULT = {
    "business_name": "American Roofing Company",
    "tagline": "Changing the Industry",
    "primary_contact": "Anthony Cross",
    "contact_title": "Master Contractor",
    "license_no": "BC-0043",
    "license_level": "MASTER · RESIDENTIAL & COMMERCIAL",
    "address": "Lexington, KY · Regency Road District",
    "phone": "(859) 555-0143",
    "website": "americanroofing.co",
}


def _contractor_logo_svg(height: int = 44) -> str:
    """Embed the OFFICIAL American Roofing Company logo (red house + USA map
    background + 'Changing The Industry' tagline) as a base64 <img>.
    Inlined so Playwright never needs an HTTP fetch during PDF render.
    """
    from pathlib import Path
    logo_b64_path = Path(__file__).parent / "_american_logo_b64.txt"
    try:
        b64 = logo_b64_path.read_text().strip()
        return (
            f'<img src="data:image/jpeg;base64,{b64}" '
            f'alt="American Roofing Company" '
            f'style="height:{height}px;width:auto;display:block;'
            f'border-radius:4px;box-shadow:0 0 12px rgba(215,40,47,0.35);"/>'
        )
    except Exception:
        # Fallback: text-only stamp if asset missing
        return (
            f'<span style="font-family:\'Space Grotesk\',sans-serif;font-weight:800;'
            f'font-size:{height}px;color:#fff;letter-spacing:-0.01em;">'
            f'American<span style="color:#D7282F;"> Roofing Co.</span></span>'
        )


def _contractor_band(a: dict) -> str:
    """Top contractor-branded band — sits above the STRATEX header on every page."""
    ct = {**CONTRACTOR_DEFAULT, **a.get("_contractor", {})}
    return f"""
    <div style="display:flex;justify-content:space-between;align-items:center;
                gap:16px;padding:10px 16px;margin-bottom:12px;border-radius:6px;
                background:linear-gradient(90deg, rgba(215,40,47,0.10) 0%, rgba(8,14,24,0.65) 60%, rgba(215,40,47,0.05) 100%);
                border:1px solid rgba(215,40,47,0.45);">
      <div style="display:flex;align-items:center;gap:18px;">
        {_contractor_logo_svg(72)}
        <div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;
                       font-size:17px;color:#fff;letter-spacing:-0.01em;">
            {escape(ct['business_name'])}
            <span class="mono" style="color:#D7282F;font-size:9.5px;letter-spacing:.22em;margin-left:8px;">
              · {escape(ct['tagline'])}
            </span>
          </div>
          <div class="mono" style="font-size:9.5px;color:var(--muted);letter-spacing:.18em;margin-top:3px;">
            {escape(ct['primary_contact'])} · {escape(ct['contact_title'])}
            &nbsp;·&nbsp; LIC {escape(ct['license_no'])} · {escape(ct['license_level'])}
          </div>
        </div>
      </div>
      <div class="mono" style="text-align:right;font-size:9.5px;color:var(--muted);letter-spacing:.18em;line-height:1.55;">
        {escape(ct['address'])}<br/>
        {escape(ct['phone'])} · {escape(ct['website'])}
      </div>
    </div>
    """


def _wordmark(size: int = 14) -> str:
    """Render the official STRATEX wordmark at the given pixel size."""
    return f"""<span class="wm" style="font-size:{size}px;">
      <span class="strat">STRAT</span><span class="ex">EX</span><span class="tm" style="font-size:{int(size*0.36)}px;">™</span>
    </span>"""


def _glyph(size: int = 40) -> str:
    """Render the STRATEX roof+facet brand glyph as inline SVG."""
    return f"""<svg viewBox="0 0 80 64" width="{size}" height="{int(size*0.8)}"
      style="filter: drop-shadow(0 0 {size//6}px rgba(77,246,255,0.55));">
      <path d="M8 50 L40 12 L72 50" fill="none" stroke="#4DF6FF" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
      <path d="M16 50 L16 56 L64 56 L64 50" fill="none" stroke="#4DF6FF" stroke-width="2.5" stroke-linejoin="round"/>
      <path d="M8 50 Q4 56 12 60" fill="none" stroke="#4DF6FF" stroke-width="2.5" stroke-linecap="round"/>
      <path d="M30 30 L52 22 L60 36 L52 50 L34 50 Z" fill="rgba(255,123,0,0.18)" stroke="#FF7B00" stroke-width="1.8" stroke-linejoin="round"/>
      <line x1="42" y1="30" x2="46" y2="50" stroke="#FF7B00" stroke-width="1" opacity="0.7"/>
      <line x1="30" y1="40" x2="60" y2="36" stroke="#FF7B00" stroke-width="1" opacity="0.5"/>
    </svg>"""


def _hdr(crumb: str, project: dict, contractor_band: bool = True) -> str:
    pid = escape(project.get("id", "—"))
    addr = escape(project.get("address", "—"))
    city = escape(project.get("city_state", ""))
    band = _contractor_band({"project": project}) if contractor_band else ""
    return f"""
    {band}
    <div class="hdr">
      <div style="display:flex;align-items:center;gap:14px;">
        {_glyph(34)}
        {_wordmark(20)}
        <div class="mono tag" style="margin-left:12px;color:#fff;letter-spacing:.18em;font-size:9px;color:var(--muted);">
          PROJECT {pid} · {addr} · {city}
        </div>
      </div>
      <div class="crumb">{escape(crumb)}</div>
    </div>
    """


def _gauge_svg(pct: int, color: str) -> str:
    # half-donut gauge
    pct = max(0, min(100, int(pct)))
    angle = pct * 1.8 - 90  # -90..+90
    return f"""<svg viewBox="0 0 120 70">
      <path d="M 10 65 A 50 50 0 0 1 110 65" stroke="rgba(255,255,255,0.10)" stroke-width="10" fill="none"/>
      <path d="M 10 65 A 50 50 0 0 1 110 65" stroke="{color}" stroke-width="10" fill="none"
            stroke-dasharray="{pct * 1.57} 1000" filter="url(#g)"/>
      <defs><filter id="g"><feGaussianBlur stdDeviation="2"/></filter></defs>
      <text x="60" y="62" text-anchor="middle" fill="#fff"
            font-family="JetBrains Mono" font-size="14" font-weight="700">{pct}%</text>
    </svg>"""


def page_cover(a: dict) -> str:
    p = a["project"]; q = a["quant"]; t = a["totals"]
    return f"""
    <div class="page">
      {_hdr("CONFIDENTIAL · STRATEGIC FORENSIC AUDIT", p)}
      <!-- HERO CONTRACTOR LOCK-UP -->
      <div style="display:flex;align-items:center;justify-content:space-between;gap:24px;
                  padding:18px 22px;margin-bottom:18px;border-radius:8px;
                  background:linear-gradient(120deg, rgba(215,40,47,0.16) 0%, rgba(8,14,24,0.85) 55%, rgba(0,229,255,0.10) 100%);
                  border:1.5px solid rgba(215,40,47,0.55);
                  box-shadow:0 0 28px rgba(215,40,47,0.20) inset;">
        <div style="display:flex;align-items:center;gap:22px;">
          {_contractor_logo_svg(120)}
          <div>
            <div style="font-family:'Space Grotesk',sans-serif;font-weight:800;
                         font-size:30px;color:#fff;letter-spacing:-0.01em;line-height:1.05;">
              American <span style="color:#D7282F;">Roofing Company</span>
            </div>
            <div class="mono" style="font-size:12px;color:#D7282F;letter-spacing:.28em;margin-top:6px;">
              CHANGING THE INDUSTRY
            </div>
            <div class="mono" style="font-size:10px;color:var(--muted);letter-spacing:.18em;margin-top:8px;">
              LICENSED MASTER CONTRACTOR · BC-0043 · OSHA · DRONE PILOT
            </div>
          </div>
        </div>
        <div style="text-align:right;">
          <div class="mono" style="font-size:9px;color:var(--cyan);letter-spacing:.32em;">
            COMMISSIONED FORENSIC AUDIT
          </div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:18px;color:#fff;margin-top:4px;">
            {escape(p['address'])}
          </div>
          <div class="mono" style="font-size:10px;color:var(--muted);letter-spacing:.2em;margin-top:2px;">
            {escape(p.get('city_state',''))}
          </div>
          <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.18em;margin-top:8px;">
            SCAN {escape(p.get('scan_date',''))} · GROUND-TRUTH <span class="glow-green">±{p.get('ground_truth_cm',0.78)} cm</span>
          </div>
        </div>
      </div>
      <div style="display:flex;align-items:flex-end;gap:24px;margin-bottom:18px;">
        {_glyph(80)}
        {_wordmark(72)}
      </div>
      <div class="eyebrow">FORENSIC ENVELOPE AUDIT · V1.0</div>
      <h1>Strategic Thermal<br/><span class="glow-cyan">Reconnaissance Report</span></h1>
      <div class="row c4" style="margin-top:30px;">
        <div class="frame cyan kpi"><div class="l">TOTAL SQUARES</div><div class="v">{q['total_squares']:.2f}</div><div class="u">SQ (100 sf)</div></div>
        <div class="frame amber kpi"><div class="l">SHINGLE LAYERS</div><div class="v">{q['shingle_layers_detected']} / {q['code_max_layers']}</div><div class="u">DETECTED / CODE MAX</div></div>
        <div class="frame green kpi"><div class="l">FACETS</div><div class="v">{q['facet_count']}</div><div class="u">DISTINCT PLANES</div></div>
        <div class="frame mag kpi"><div class="l">ANOMALIES FLAGGED</div><div class="v">{len(a['anomalies'])}</div><div class="u">FORENSIC HOTSPOTS</div></div>
      </div>
      <div class="row c2" style="margin-top:24px;">
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">EXECUTIVE SUMMARY · GRAND TOTAL RANGE</h2>
          <div class="mono" style="font-size:42px;color:#fff;letter-spacing:-0.02em;">
            <span class="glow-cyan">{_usd(t['grand_total_low_usd'])}</span>
            <span style="color:var(--muted);font-size:18px;"> &nbsp;→&nbsp; </span>
            <span class="glow-amber">{_usd(t['grand_total_high_usd'])}</span>
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:10px;letter-spacing:.14em;">
            MATERIALS {_usd(t['materials_usd'])} · LABOR {_usd(t['labor_usd'])}
            {'· TEAR-OFF ' + _usd(t['tear_off_usd']) if t['tear_off_usd'] else ''}
            · UNFORESEEN {_usd(t['side_quote_low_usd'])}–{_usd(t['side_quote_high_usd'])}
          </div>
        </div>
        <div class="frame {'mag' if a['water_retention']['tear_off_recommended'] else 'green'}">
          <h2 style="color:{'var(--mag)' if a['water_retention']['tear_off_recommended'] else 'var(--green)'};">
            STRATEX RECOMMENDATION
          </h2>
          <div style="font-family:'Space Grotesk';font-size:24px;font-weight:700;color:#fff;letter-spacing:-0.01em;">
            {escape(a['shingle_recommendation']['action'].replace('_',' '))}
          </div>
          <div class="mono" style="color:var(--silver);font-size:10px;margin-top:8px;line-height:1.5;">
            {escape(a['water_retention']['tear_off_rationale'])}
          </div>
        </div>
      </div>
    </div>
    """


def page_executive(a: dict) -> str:
    p = a["project"]; e = a["envelope_scores"]; tasks = a["priority_tasks"]; thermal = a["thermal_findings"]
    tasks_html = "".join(
        f"""<div class="row" style="grid-template-columns: 18px 70px 1fr 90px;gap:10px;align-items:center;padding:8px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
          <div class="mono" style="color:var(--muted);font-size:11px;">{t['rank']}</div>
          <div class="pill" style="color:{_sev_color(t['severity'])};">{escape(t['severity'])}</div>
          <div style="font-size:11px;color:#fff;">{escape(t['task'])}</div>
          <div class="mono right glow-green" style="font-size:10px;">${t['annual_savings_usd']:,.0f}/yr</div>
        </div>""" for t in tasks)
    therm_html = "".join(
        f"""<div class="row" style="grid-template-columns: 1fr 90px 70px;gap:10px;align-items:center;padding:6px 0;border-bottom:1px solid rgba(255,255,255,0.04);">
          <div style="font-size:10px;color:var(--silver);">{escape(tf['label'])}</div>
          <div class="mono right" style="font-size:10px;color:#fff;">{escape(tf['reading'])}</div>
          <div class="pill right" style="color:{_sev_color(tf['severity'])};">{escape(tf['severity'])}</div>
        </div>""" for tf in thermal)
    return f"""
    <div class="page">
      {_hdr("PAGE 01 · EXECUTIVE ENVELOPE SUMMARY", p)}
      <div class="eyebrow">01 · EXECUTIVE ENVELOPE SUMMARY</div>
      <h1 style="font-size:34px;">Building <span class="glow-amber">Envelope Score</span></h1>
      <div class="row c3" style="margin-top:24px;">
        <div class="frame mag" style="text-align:center;">
          <h2 style="color:var(--mag);">ENERGY DEFICIENCY</h2>
          <div class="gauge">{_gauge_svg(e['energy_deficiency_pct'], '#FF2D78')}</div>
          <div class="mono" style="color:var(--mag);font-size:10px;margin-top:6px;letter-spacing:.18em;">DEFICIENT</div>
        </div>
        <div class="frame amber" style="text-align:center;">
          <h2 style="color:var(--amber);">VENTILATION</h2>
          <div class="gauge">{_gauge_svg(e['ventilation_pct'], '#FFB020')}</div>
          <div class="mono" style="color:var(--amber);font-size:10px;margin-top:6px;letter-spacing:.18em;">POOR</div>
        </div>
        <div class="frame cyan" style="text-align:center;">
          <h2 style="color:var(--cyan);">OVERALL ENVELOPE</h2>
          <div style="font-family:'Space Grotesk';font-size:60px;font-weight:700;color:#fff;line-height:1;margin:14px 0 4px;">
            {e['overall_envelope']}<span style="color:var(--muted);font-size:24px;">/100</span>
          </div>
          <div class="mono" style="color:var(--cyan);font-size:10px;letter-spacing:.18em;">COMPOSITE</div>
        </div>
      </div>
      <div class="row c2" style="margin-top:22px;">
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">AI-PRIORITIZED MAINTENANCE QUEUE</h2>
          {tasks_html}
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">THERMAL FORENSIC FINDINGS</h2>
          {therm_html}
        </div>
      </div>
    </div>
    """


def page_facade(a: dict) -> str:
    p = a["project"]
    anomalies_html = "".join(
        f"""<tr>
          <td><span class="pill" style="color:{_sev_color(an['severity'])};">{escape(an['severity'])}</span></td>
          <td>{escape(an['id'])}</td>
          <td>{escape(an['type'])}</td>
          <td>{escape(an['location'])}</td>
          <td class="right">{an['confidence_pct']:.1f}%</td>
          <td class="right">{an['area_sqft']:.1f}</td>
          <td>{escape(an['diagnosis'])}</td>
          <td class="right glow-amber">{_usd(an['repair_estimate_usd'])}</td>
        </tr>""" for an in a["anomalies"])
    return f"""
    <div class="page">
      {_hdr("PAGE 02 · ROOF VENTILATION & FACADE FORENSIC ANALYSIS", p)}
      <div class="eyebrow">02 · FORENSIC OVERLAY</div>
      <h1 style="font-size:30px;">Sub-surface <span class="glow-mag">Anomaly Atlas</span></h1>
      <div class="row c2" style="margin-top:22px;align-items:start;">
        <div class="frame amber">
          <h2 style="color:var(--amber);">RADIOMETRIC OVERLAY · ROOF</h2>
          <img src="assets/render_full_twin.png" style="width:100%;border-radius:4px;display:block;"/>
          <div class="mono" style="font-size:9px;color:var(--muted);margin-top:8px;letter-spacing:.14em;">
            CYAN: scan-vector overlay · ORANGE: thermal hotspot · Confidence threshold ≥ 85%
          </div>
        </div>
        <div class="frame mag">
          <h2 style="color:var(--mag);">ANOMALY LEDGER</h2>
          <table>
            <thead><tr><th>SEV</th><th>ID</th><th>TYPE</th><th>LOCATION</th><th class="right">CONF</th><th class="right">SF</th><th>DIAGNOSIS</th><th class="right">EST</th></tr></thead>
            <tbody>{anomalies_html}</tbody>
          </table>
        </div>
      </div>
    </div>
    """


def page_digital_twin(a: dict) -> str:
    p = a["project"]; q = a["quant"]
    return f"""
    <div class="page">
      {_hdr("PAGE 03 · TRIPLE-LAYER DIGITAL TWIN", p)}
      <div class="eyebrow">03 · TRIPLE-LAYER DIGITAL TWIN</div>
      <h1 style="font-size:30px;">Layered <span class="glow-cyan">CAD/BIM Twin</span></h1>
      <div class="row c3" style="margin-top:22px;">
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">LAYER 01 · FINISHED SLATE</h2>
          <img src="assets/render_layer1_shingle.png" style="width:100%;border-radius:4px;display:block;"/>
          <div class="mono" style="font-size:9px;color:var(--muted);margin-top:6px;letter-spacing:.12em;">
            Squares <span style="color:#fff">{q['total_squares']:.2f}</span> · Pitch <span style="color:#fff">{escape(q['pitch_predominant'])}</span>
          </div>
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">LAYER 02 · DECKING + UNDERLAYMENT</h2>
          <img src="assets/render_layer2_decking.png" style="width:100%;border-radius:4px;display:block;"/>
          <div class="mono" style="font-size:9px;color:var(--muted);margin-top:6px;letter-spacing:.12em;">
            7/16" CDX · I&amp;W shield at valleys/eaves · {q['shingle_layers_detected']} existing shingle layer(s)
          </div>
        </div>
        <div class="frame green">
          <h2 style="color:var(--green);">LAYER 03 · STRUCTURAL FRAMING</h2>
          <img src="assets/render_layer3_framing.png" style="width:100%;border-radius:4px;display:block;"/>
          <div class="mono" style="font-size:9px;color:var(--muted);margin-top:6px;letter-spacing:.12em;">
            2x8 rafters @ 16" o.c. · LVL ridge · Hurricane ties <span class="glow-green">VERIFIED</span>
          </div>
        </div>
      </div>
      <div class="row c4" style="margin-top:18px;">
        <div class="frame kpi"><div class="l">VALLEYS</div><div class="v">{q['valleys_lf']:.1f}</div><div class="u">LINEAR FT</div></div>
        <div class="frame kpi"><div class="l">GABLES</div><div class="v">{q['gables_lf']:.1f}</div><div class="u">LINEAR FT</div></div>
        <div class="frame kpi"><div class="l">RIDGES</div><div class="v">{q['ridges_lf']:.1f}</div><div class="u">LINEAR FT</div></div>
        <div class="frame kpi"><div class="l">EAVES</div><div class="v">{q['eaves_lf']:.1f}</div><div class="u">LINEAR FT</div></div>
      </div>
    </div>
    """


def page_window_schedule(a: dict) -> str:
    p = a["project"]
    rows = "".join(
        f"""<tr>
          <td class="mono glow-cyan">{escape(w['id'])}</td>
          <td>{escape(w['location'])}</td>
          <td>{escape(w['shape'])}</td>
          <td class="right">{w['width_in']:.0f}"</td>
          <td class="right">{w['height_in']:.0f}"</td>
          <td class="right">{w['qty']}</td>
          <td class="right">{w['u_factor']:.2f}</td>
          <td><span class="pill" style="color:{_sev_color(w['leak_severity'])};">{escape(w['leak_severity'])}</span></td>
        </tr>""" for w in a["window_schedule"])
    return f"""
    <div class="page">
      {_hdr("PAGE 04 · WINDOW SCHEDULE", p)}
      <div class="eyebrow">04 · WINDOW SCHEDULE</div>
      <h1 style="font-size:30px;">Fenestration <span class="glow-cyan">Schedule</span></h1>
      <div class="frame cyan" style="margin-top:22px;">
        <table>
          <thead><tr><th>ID</th><th>LOCATION</th><th>SHAPE</th><th class="right">W</th><th class="right">H</th><th class="right">QTY</th><th class="right">U-FACTOR</th><th>LEAK SEV</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """


def page_door_schedule(a: dict) -> str:
    p = a["project"]
    rows = "".join(
        f"""<tr>
          <td class="mono glow-amber">{escape(d['id'])}</td>
          <td>{escape(d['location'])}</td>
          <td>{escape(d['shape'])}</td>
          <td class="right">{d['width_in']:.0f}"</td>
          <td class="right">{d['height_in']:.0f}"</td>
          <td class="right">{d['qty']}</td>
          <td><span class="pill" style="color:{_sev_color(d['weatherstrip_status'])};">{escape(d['weatherstrip_status'])}</span></td>
        </tr>""" for d in a["door_schedule"])
    return f"""
    <div class="page">
      {_hdr("PAGE 05 · DOOR SCHEDULE", p)}
      <div class="eyebrow">05 · EXTERIOR DOOR SCHEDULE</div>
      <h1 style="font-size:30px;">Exterior Door <span class="glow-amber">Schedule</span></h1>
      <div class="frame amber" style="margin-top:22px;">
        <table>
          <thead><tr><th>ID</th><th>LOCATION</th><th>SHAPE</th><th class="right">W</th><th class="right">H</th><th class="right">QTY</th><th>WEATHERSTRIP</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """


def page_bom(a: dict) -> str:
    p = a["project"]
    rows = "".join(
        f"""<tr>
          <td>{escape(b['category'])}</td>
          <td>{escape(b['material'])}</td>
          <td class="mono">{escape(b['sku'])}</td>
          <td class="right">{b['qty']:g}</td>
          <td>{escape(b['unit'])}</td>
          <td class="right">{_usd(b['unit_cost_usd'])}</td>
          <td class="right glow-cyan">{_usd(b['line_total_usd'])}</td>
        </tr>""" for b in a["bom"])
    return f"""
    <div class="page">
      {_hdr("PAGE 06 · BILL OF MATERIALS", p)}
      <div class="eyebrow">06 · STRATEX QUANT™ BOM</div>
      <h1 style="font-size:30px;">Bill of <span class="glow-cyan">Materials</span></h1>
      <div class="frame cyan" style="margin-top:22px;">
        <table>
          <thead><tr><th>CATEGORY</th><th>MATERIAL</th><th>SKU</th><th class="right">QTY</th><th>UNIT</th><th class="right">UNIT COST</th><th class="right">LINE TOTAL</th></tr></thead>
          <tbody>{rows}</tbody>
          <tfoot><tr><td colspan="6" class="right" style="padding-top:10px;color:var(--muted);letter-spacing:.18em;">MATERIALS TOTAL</td>
            <td class="right" style="padding-top:10px;font-size:13px;color:#fff;font-weight:700;">{_usd(a['totals']['materials_usd'])}</td></tr></tfoot>
        </table>
      </div>
    </div>
    """


def page_labor(a: dict) -> str:
    p = a["project"]; l = a["labor"]
    return f"""
    <div class="page">
      {_hdr("PAGE 07 · LABOR · NATIONAL & REGIONAL AVERAGES", p)}
      <div class="eyebrow">07 · LABOR ALLOCATION</div>
      <h1 style="font-size:30px;">Crew <span class="glow-green">Economics</span></h1>
      <div class="row c2" style="margin-top:22px;">
        <div class="frame green">
          <h2 style="color:var(--green);">RATE BENCHMARK</h2>
          <div class="row c2" style="margin-top:6px;">
            <div class="kpi"><div class="l">NATIONAL AVG / SQ</div><div class="v">{_usd(l['national_avg_per_sq'])}</div></div>
            <div class="kpi"><div class="l">REGIONAL AVG / SQ</div><div class="v glow-green">{_usd(l['regional_avg_per_sq'])}</div></div>
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:14px;letter-spacing:.16em;">
            REGION: <span style="color:#fff">{escape(l['region'])}</span> · APPLIED:
            <span class="glow-green">{_usd(l['applied_per_sq'])}/SQ</span>
          </div>
        </div>
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">CREW PLAN</h2>
          <div class="row c3" style="margin-top:6px;">
            <div class="kpi"><div class="l">CREW SIZE</div><div class="v">{l['crew_size']}</div></div>
            <div class="kpi"><div class="l">DAYS</div><div class="v">{l['days_estimated']:.1f}</div></div>
            <div class="kpi"><div class="l">LABOR TOTAL</div><div class="v glow-cyan">{_usd(l['labor_total_usd'])}</div></div>
          </div>
        </div>
      </div>
    </div>
    """


def page_side_quote(a: dict) -> str:
    p = a["project"]; t = a["totals"]
    rows = "".join(
        f"""<tr>
          <td>{escape(x['item'])}</td>
          <td class="right">{x['probability_pct']}%</td>
          <td class="right">{_usd(x['low_usd'])}</td>
          <td class="right">{_usd(x['high_usd'])}</td>
          <td>{escape(x['note'])}</td>
        </tr>""" for x in a["side_quote_unforeseen"])
    return f"""
    <div class="page">
      {_hdr("PAGE 08 · SIDE QUOTE · UNFORESEEN REPAIRS", p)}
      <div class="eyebrow">08 · CONTINGENCY ENVELOPE</div>
      <h1 style="font-size:30px;">Unforeseen <span class="glow-amber">Repair Reserve</span></h1>
      <div class="frame amber" style="margin-top:22px;">
        <table>
          <thead><tr><th>ITEM</th><th class="right">PROB</th><th class="right">LOW</th><th class="right">HIGH</th><th>NOTE</th></tr></thead>
          <tbody>{rows}</tbody>
          <tfoot><tr><td colspan="2" class="right" style="padding-top:10px;color:var(--muted);letter-spacing:.18em;">RESERVE RANGE</td>
            <td class="right glow-amber" style="padding-top:10px;font-size:13px;font-weight:700;">{_usd(t['side_quote_low_usd'])}</td>
            <td class="right glow-mag" style="padding-top:10px;font-size:13px;font-weight:700;">{_usd(t['side_quote_high_usd'])}</td>
            <td></td></tr></tfoot>
        </table>
      </div>
    </div>
    """


def page_tearoff(a: dict) -> str:
    if not a["water_retention"]["tear_off_recommended"]:
        return ""
    p = a["project"]; w = a["water_retention"]; t = a["totals"]
    return f"""
    <div class="page">
      {_hdr("PAGE 09 · TEAR-OFF RECOMMENDATION", p)}
      <div class="eyebrow">09 · TEAR-OFF MANDATE</div>
      <h1 style="font-size:32px;">Full <span class="glow-mag">Tear-Off + New Install</span> Required</h1>
      <div class="row c2" style="margin-top:22px;">
        <div class="frame mag">
          <h2 style="color:var(--mag);">WATER RETENTION PROBABILITY</h2>
          <div style="font-family:'Space Grotesk';font-size:90px;font-weight:700;color:#fff;line-height:1;">
            {w['probability_pct']}%
          </div>
          <div class="mono" style="color:var(--mag);font-size:11px;margin-top:8px;letter-spacing:.18em;">
            DEPTH EST {w['depth_estimate_in']:.2f}" · MULTI-SEASON ENTRAPMENT
          </div>
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">RATIONALE</h2>
          <p style="font-size:13px;color:var(--silver);line-height:1.55;">{escape(w['tear_off_rationale'])}</p>
          <div style="margin-top:14px;padding-top:14px;border-top:1px solid rgba(255,176,32,0.25);">
            <div class="tag">TEAR-OFF COST INCLUDED</div>
            <div style="font-family:'Space Grotesk';font-size:32px;font-weight:700;color:#fff;margin-top:4px;">
              {_usd(t['tear_off_usd'])}
            </div>
          </div>
        </div>
      </div>
    </div>
    """


def page_wall_envelope(a: dict) -> str:
    if "walls" not in a or "siding_package" not in a:
        return ""
    p = a["project"]; w = a["walls"]; s = a["siding_package"]
    elev_rows = "".join(
        f"""<tr>
          <td class="mono glow-cyan">{escape(e['label'])}</td>
          <td class="right">{e['gross_sf']:.1f}</td>
          <td class="right">{e['net_sf']:.1f}</td>
          <td class="right">
            <span class="pill" style="color:{_sev_color('HIGH' if e['moisture_saturation_pct']>25 else 'MED' if e['moisture_saturation_pct']>12 else 'LOW')};">
              {e['moisture_saturation_pct']}%
            </span>
          </td>
        </tr>""" for e in w["elevations"])
    acc_rows = "".join(
        f"""<tr>
          <td>{escape(x['name'])}</td>
          <td class="right">{x['qty']:g}</td>
          <td>{escape(x['unit'])}</td>
          <td class="right">{_usd(x['unit_cost_usd'])}</td>
          <td class="right glow-cyan">{_usd(x['line_total_usd'])}</td>
        </tr>""" for x in s["accessories"])
    return f"""
    <div class="page">
      {_hdr("PAGE · WALL ENVELOPE + SIDING PACKAGE", p)}
      <div class="eyebrow">· WALL ENVELOPE & SIDING PACKAGE · GEOMETRY + MATERIAL AGENT</div>
      <h1 style="font-size:30px;">Vertical <span class="glow-cyan">Envelope</span> +
        <span class="glow-amber">{escape(s['primary_material'])}</span> Package</h1>
      <div class="row c4" style="margin-top:22px;">
        <div class="frame kpi"><div class="l">GROSS WALL SF</div><div class="v">{w['total_gross_wall_sf']:.0f}</div><div class="u">PRE-SUBTRACTION</div></div>
        <div class="frame kpi"><div class="l">FENESTRATION</div><div class="v glow-amber">{w['fenestration_subtraction_sf']:.0f}</div><div class="u">WINDOWS + DOORS</div></div>
        <div class="frame kpi"><div class="l">NET WALL SF</div><div class="v glow-cyan">{w['net_wall_sf']:.0f}</div><div class="u">SIDING TARGET</div></div>
        <div class="frame kpi"><div class="l">WALL HEIGHT</div><div class="v">{w['wall_height_ft']:.1f}'</div><div class="u">EAVE-TO-GRADE</div></div>
      </div>
      <div class="row c2" style="margin-top:18px;align-items:start;">
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">ELEVATION BREAKDOWN</h2>
          <table>
            <thead><tr><th>ELEV.</th><th class="right">GROSS SF</th><th class="right">NET SF</th><th class="right">MOISTURE</th></tr></thead>
            <tbody>{elev_rows}</tbody>
          </table>
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">SIDING PACKAGE · {escape(s['primary_material'])}</h2>
          <div class="mono" style="font-size:10px;color:var(--muted);margin-bottom:8px;letter-spacing:.14em;">
            PROFILE: <span style="color:#fff">{escape(s['profile'])}</span> ·
            COLOR: <span style="color:#fff">{escape(s['color'])}</span>
          </div>
          <table>
            <thead><tr><th>ACCESSORY</th><th class="right">QTY</th><th>UNIT</th><th class="right">UNIT</th><th class="right">LINE</th></tr></thead>
            <tbody>{acc_rows}</tbody>
            <tfoot><tr><td colspan="4" class="right" style="padding-top:10px;color:var(--muted);letter-spacing:.18em;">SIDING SUBTOTAL</td>
              <td class="right" style="padding-top:10px;font-size:13px;color:#fff;font-weight:700;">{_usd(s['subtotal_usd'])}</td></tr></tfoot>
          </table>
        </div>
      </div>
    </div>
    """


def page_wall_moisture(a: dict) -> str:
    if "moisture_vapor" not in a:
        return ""
    p = a["project"]; m = a["moisture_vapor"]
    rows = "".join(
        f"""<tr>
          <td class="mono glow-mag">{escape(z['id'])}</td>
          <td>{escape(z['elevation'])}</td>
          <td class="right">{z['area_sf']:.1f}</td>
          <td class="right"><span class="pill" style="color:{_sev_color('HIGH' if z['moisture_pct']>30 else 'MED' if z['moisture_pct']>20 else 'LOW')};">{z['moisture_pct']}%</span></td>
          <td class="right"><span class="pill" style="color:{_sev_color('URGENT' if z['damage_probability_pct']>60 else 'HIGH' if z['damage_probability_pct']>40 else 'MED')};">{z['damage_probability_pct']}%</span></td>
          <td>{escape(z['remediation_action'])}</td>
          <td class="right glow-amber">{_usd(z['estimate_usd'])}</td>
        </tr>""" for z in m["thermal_saturation_zones"])
    vc = m["vapor_barrier_condition"]
    return f"""
    <div class="page">
      {_hdr("PAGE · WALL MOISTURE + VAPOR BARRIER ANALYSIS", p)}
      <div class="eyebrow">· WALL MOISTURE + VAPOR BARRIER · THERMAL AGENT</div>
      <h1 style="font-size:30px;">Sub-Siding <span class="glow-mag">Moisture Atlas</span></h1>
      <div class="row c3" style="margin-top:22px;">
        <div class="frame {'mag' if vc != 'OK' else 'green'}">
          <h2 style="color:{'var(--mag)' if vc != 'OK' else 'var(--green)'};">VAPOR BARRIER STATUS</h2>
          <div style="font-family:'Space Grotesk';font-size:34px;font-weight:700;color:#fff;line-height:1;margin-top:6px;">
            {escape(vc)}
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:8px;letter-spacing:.16em;">
            {'BARRIER PRESENT' if m['vapor_barrier_present'] else 'BARRIER ABSENT'} · INFRARED-CONFIRMED
          </div>
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">ZONES FLAGGED</h2>
          <div style="font-family:'Space Grotesk';font-size:60px;font-weight:700;color:#fff;line-height:1;">
            {len(m['thermal_saturation_zones'])}
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:8px;letter-spacing:.16em;">THERMAL ANOMALY ZONES · WALL CAVITY</div>
        </div>
        <div class="frame mag">
          <h2 style="color:var(--mag);">REMEDIATION TOTAL</h2>
          <div style="font-family:'Space Grotesk';font-size:34px;font-weight:700;color:#fff;line-height:1;margin-top:6px;">
            {_usd(m['total_remediation_usd'])}
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:8px;letter-spacing:.16em;">ROLLED INTO MATERIALS TOTAL</div>
        </div>
      </div>
      <div class="frame mag" style="margin-top:18px;">
        <h2 style="color:var(--mag);">THERMAL SATURATION ZONES · WALL CAVITY</h2>
        <table>
          <thead><tr><th>ID</th><th>ELEV.</th><th class="right">AREA SF</th><th class="right">MOISTURE</th><th class="right">DAMAGE PROB.</th><th>REMEDIATION</th><th class="right">EST.</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """


def page_energy_leakage(a: dict) -> str:
    if "energy_leakage" not in a:
        return ""
    p = a["project"]; e = a["energy_leakage"]
    rows = "".join(
        f"""<tr>
          <td>{escape(s['label'])}</td>
          <td>{escape(s['location'])}</td>
          <td class="right"><span class="pill" style="color:{_sev_color('HIGH' if s['btu_loss_pct']>15 else 'MED' if s['btu_loss_pct']>10 else 'LOW')};">{s['btu_loss_pct']}%</span></td>
          <td class="right glow-mag">${s['annual_dollar_loss']:.0f}/yr</td>
          <td>{escape(s['remediation'])}</td>
        </tr>""" for s in e["leak_sources"])
    return f"""
    <div class="page">
      {_hdr("PAGE · ENERGY LEAKAGE ATLAS", p)}
      <div class="eyebrow">· ENERGY LEAKAGE ATLAS · ENERGY AGENT</div>
      <h1 style="font-size:30px;">Envelope <span class="glow-amber">Air-Leak</span> Profile</h1>
      <div class="row c3" style="margin-top:22px;">
        <div class="frame mag">
          <h2 style="color:var(--mag);">BLOWER-DOOR ACH₅₀ (EST.)</h2>
          <div style="font-family:'Space Grotesk';font-size:60px;font-weight:700;color:#fff;line-height:1;margin-top:6px;">
            {e['blower_door_ach50_estimated']:.1f}
          </div>
          <div class="mono" style="color:var(--mag);font-size:10px;margin-top:6px;letter-spacing:.16em;">TARGET ≤ 3.0 · LEAKY ENVELOPE</div>
        </div>
        <div class="frame amber">
          <h2 style="color:var(--amber);">ANNUAL ENERGY LOSS</h2>
          <div style="font-family:'Space Grotesk';font-size:40px;font-weight:700;color:#fff;line-height:1;margin-top:6px;">
            {e['annual_kbtu_lost_estimated']:,.0f}<span style="font-size:14px;color:var(--muted);"> kBTU</span>
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:8px;letter-spacing:.16em;">SEASONAL LOSS · CONDITIONED ENVELOPE</div>
        </div>
        <div class="frame green">
          <h2 style="color:var(--green);">ANNUAL DOLLAR LOSS</h2>
          <div style="font-family:'Space Grotesk';font-size:40px;font-weight:700;color:#fff;line-height:1;margin-top:6px;">
            {_usd(e['annual_dollar_loss'])}<span style="font-size:14px;color:var(--muted);"> /yr</span>
          </div>
          <div class="mono" style="color:var(--green);font-size:10px;margin-top:8px;letter-spacing:.16em;">RECOVERABLE WITH REMEDIATION</div>
        </div>
      </div>
      <div class="frame amber" style="margin-top:18px;">
        <h2 style="color:var(--amber);">LEAK-SOURCE LEDGER</h2>
        <table>
          <thead><tr><th>SOURCE</th><th>LOCATION</th><th class="right">BTU LOSS</th><th class="right">$/YR</th><th>RECOMMENDED FIX</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
    """


def page_profitability(a: dict) -> str:
    if "profitability" not in a:
        return ""
    p = a["project"]; pr = a["profitability"]
    # Build a CSS conic-gradient pie chart from the splits
    splits = [
        ("MATERIALS",   pr["materials_pct"],   "#4DF6FF"),
        ("LABOR",       pr["labor_pct"],       "#FFB020"),
        ("CONTINGENCY", pr.get("contingency_pct", 0), "#FF2D78"),
        ("OVERHEAD",    pr["overhead_pct"],    "#FF7B00"),
        ("PROFIT",      pr["profit_pct"],      "#00FF9C"),
    ]
    cum = 0.0
    pie_stops = []
    for label, pct, color in splits:
        start = cum
        cum += pct
        pie_stops.append(f"{color} {start:.1f}% {cum:.1f}%")
    pie_css = "conic-gradient(" + ", ".join(pie_stops) + ")"
    legend = "".join(
        f"""<div style="display:flex;align-items:center;gap:8px;font-family:'JetBrains Mono',monospace;font-size:10px;color:var(--silver);margin:6px 0;">
          <span style="width:12px;height:12px;background:{c};border-radius:2px;box-shadow:0 0 6px {c};"></span>
          <span style="flex:1;">{label}</span>
          <span style="color:#fff;font-weight:700;">{pct:.1f}%</span>
        </div>""" for label, pct, c in splits
    )
    return f"""
    <div class="page">
      {_hdr("PAGE · PROFITABILITY & PROJECT MARGINS", p)}
      <div class="eyebrow">· PROFITABILITY & PROJECT MARGINS</div>
      <h1 style="font-size:30px;">Project <span class="glow-green">Margin</span> Overview</h1>
      <div class="row c2" style="margin-top:22px;align-items:center;">
        <div class="frame green" style="text-align:center;">
          <h2 style="color:var(--green);">COST COMPOSITION</h2>
          <div style="display:flex;justify-content:center;margin:16px 0;">
            <div style="width:220px;height:220px;border-radius:50%;background:{pie_css};
              box-shadow:0 0 32px rgba(77,246,255,0.18); position:relative;">
              <div style="position:absolute;inset:50px;border-radius:50%;background:#02060B;
                display:flex;flex-direction:column;align-items:center;justify-content:center;">
                <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.16em;">GROSS COST</div>
                <div style="font-family:'Space Grotesk',sans-serif;font-size:18px;font-weight:700;color:#fff;">
                  {_usd(pr['gross_project_cost'])}
                </div>
              </div>
            </div>
          </div>
          <div style="text-align:left;max-width:260px;margin:0 auto;">{legend}</div>
        </div>
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">FINANCIAL SUMMARY</h2>
          <table>
            <tbody>
              <tr><td>GROSS PROJECT REVENUE</td><td class="right glow-cyan">{_usd(pr['gross_project_cost'])}</td></tr>
              <tr><td>TOTAL MATERIALS</td><td class="right">{_usd(a['totals']['materials_usd'])}</td></tr>
              <tr><td>TOTAL LABOR</td><td class="right">{_usd(a['totals']['labor_usd'])}</td></tr>
              <tr><td>CONTINGENCY (tear-off + reserve)</td><td class="right">{_usd(pr.get('contingency_usd', 0))}</td></tr>
              <tr><td>OVERHEAD (10%)</td><td class="right">{_usd(pr['overhead_usd'])}</td></tr>
              <tr><td>PROJECTED NET PROFIT (20%)</td><td class="right glow-green">{_usd(pr['projected_net_profit_usd'])}</td></tr>
            </tbody>
          </table>
          <div class="mono" style="font-size:10px;color:var(--muted);margin-top:14px;line-height:1.5;">
            {escape(pr['commentary'])}
          </div>
        </div>
      </div>
    </div>
    """


def page_labor_gantt(a: dict) -> str:
    if "labor_gantt" not in a:
        return ""
    p = a["project"]; rows = a["labor_gantt"]
    total_days = max(r["start_day"] + r["duration"] for r in rows)
    bars = "".join(
        f"""<tr>
          <td style="width:34%;">{escape(r['phase'])}</td>
          <td class="mono" style="width:14%;color:var(--muted);">{escape(r['crew'])}</td>
          <td style="width:8%;" class="right">{r['duration']:.2f} d</td>
          <td>
            <div style="position:relative;height:14px;background:rgba(255,255,255,0.05);border-radius:2px;">
              <div style="position:absolute;left:{r['start_day']/total_days*100:.1f}%;
                width:{r['duration']/total_days*100:.1f}%;height:14px;
                background:linear-gradient(90deg,#4DF6FF,#FFB020);
                box-shadow:0 0 8px rgba(77,246,255,0.45);border-radius:2px;"></div>
            </div>
          </td>
        </tr>""" for r in rows
    )
    return f"""
    <div class="page">
      {_hdr("PAGE · LABOR & MAN-HOURS · GANTT SEQUENCE", p)}
      <div class="eyebrow">· LABOR SEQUENCE · GANTT TIMELINE</div>
      <h1 style="font-size:30px;">Crew <span class="glow-amber">Choreography</span></h1>
      <div class="frame cyan" style="margin-top:22px;">
        <table>
          <thead><tr><th>PHASE</th><th>CREW</th><th class="right">DURATION</th><th>TIMELINE · {total_days:.1f} d</th></tr></thead>
          <tbody>{bars}</tbody>
        </table>
      </div>
    </div>
    """


def _iso_component(label: str, code: str, spec: str, paths_svg: str, accent: str = "cyan") -> str:
    """Render a single isometric component card (J/F-Channel · Starter · Finish Trim · etc.)."""
    accent_hex = {
        "cyan": "#4DF6FF", "amber": "#FFB020", "green": "#00FF9C",
        "mag": "#FF2D78", "orange": "#FF7B00",
    }.get(accent, "#4DF6FF")
    return f"""
    <div class="frame {accent}" style="padding:14px;display:flex;flex-direction:column;gap:8px;">
      <div style="display:flex;justify-content:space-between;align-items:baseline;">
        <div>
          <div class="mono" style="font-size:8px;letter-spacing:.26em;color:{accent_hex};">CODE · {escape(code)}</div>
          <div style="font-size:14px;color:#fff;font-weight:600;margin-top:2px;letter-spacing:.02em;">{escape(label)}</div>
        </div>
        <span class="pill" style="color:{accent_hex};">ASSEMBLY</span>
      </div>
      <div style="background:rgba(2,6,11,0.55);border:1px solid rgba(255,255,255,0.06);border-radius:4px;
                  padding:8px;display:flex;align-items:center;justify-content:center;height:104px;">
        <svg viewBox="0 0 200 110" width="100%" height="100%"
             style="filter: drop-shadow(0 0 6px {accent_hex}55);">
          {paths_svg}
        </svg>
      </div>
      <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.16em;line-height:1.55;">
        {escape(spec)}
      </div>
    </div>
    """


def page_assembly_catalog(a: dict) -> str:
    """Page · 3D Component Catalog — isometric assembly grid for the bid envelope.

    Cards: J-Channel · F-Channel · Starter Strip · Finish Trim · Drip Edge ·
    Soffit Panel · Inside / Outside Corner · Utility Trim.  Each card carries an
    isometric SVG mockup, a trade code, and gauge / dimension spec line.
    """
    p = a["project"]

    # ──────────────────────────── Isometric SVG library ────────────────────────────
    # All paths use a 200×110 viewBox.  Stroke colors are baked here so we can vary
    # cyan / amber per card without rebuilding the whole SVG tree.

    j_channel = """
      <!-- J-Channel : isometric U-receiver -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M30 80 L130 30 L170 50 L170 76 L162 80 L162 56 L130 41 L38 86 Z"
              fill="rgba(77,246,255,0.10)" stroke="#4DF6FF" stroke-width="1.6"/>
        <path d="M30 80 L162 80 L170 76" stroke="#4DF6FF" stroke-width="1.4"/>
        <path d="M38 86 L130 41" stroke="#4DF6FF" stroke-width="1.0" stroke-dasharray="2 3" opacity="0.7"/>
        <path d="M150 72 L150 64 M155 70 L155 62 M160 68 L160 60" stroke="#4DF6FF" stroke-width="1.0" opacity="0.5"/>
      </g>"""

    f_channel = """
      <!-- F-Channel : isometric step section -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M30 84 L120 36 L172 56 L172 64 L130 48 L130 58 L86 80 L86 86 Z"
              fill="rgba(255,176,32,0.12)" stroke="#FFB020" stroke-width="1.6"/>
        <path d="M86 80 L172 64" stroke="#FFB020" stroke-width="1.0" stroke-dasharray="2 3" opacity="0.7"/>
        <path d="M40 88 L130 48" stroke="#FFB020" stroke-width="1.0" opacity="0.6"/>
        <circle cx="50" cy="84" r="1.2" fill="#FFB020"/>
        <circle cx="78" cy="70" r="1.2" fill="#FFB020"/>
        <circle cx="106" cy="56" r="1.2" fill="#FFB020"/>
      </g>"""

    starter_strip = """
      <!-- Starter Strip : long ribbon with anchor flange -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M22 70 L160 30 L178 38 L178 50 L160 42 L24 82 Z"
              fill="rgba(0,255,156,0.12)" stroke="#00FF9C" stroke-width="1.6"/>
        <path d="M24 82 L24 88 L160 48 L160 42" stroke="#00FF9C" stroke-width="1.4"/>
        <path d="M40 76 L44 68 M70 62 L74 54 M100 48 L104 40 M130 34 L134 26"
              stroke="#00FF9C" stroke-width="1.0" opacity="0.6"/>
      </g>"""

    finish_trim = """
      <!-- Finish Trim : capping bead -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M28 80 L120 32 L172 56 L172 72 L162 72 L162 60 L130 46 L40 88 Z"
              fill="rgba(255,45,120,0.12)" stroke="#FF2D78" stroke-width="1.6"/>
        <ellipse cx="100" cy="56" rx="58" ry="6" fill="none" stroke="#FF2D78" stroke-width="0.9" opacity="0.7"/>
        <path d="M40 88 L162 60" stroke="#FF2D78" stroke-width="0.9" stroke-dasharray="1 3" opacity="0.6"/>
      </g>"""

    drip_edge = """
      <!-- Drip Edge : L-flashing -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M28 72 L132 28 L170 44 L168 88 L160 92 L160 56 L36 100 Z"
              fill="rgba(255,123,0,0.12)" stroke="#FF7B00" stroke-width="1.6"/>
        <path d="M36 100 L160 56" stroke="#FF7B00" stroke-width="1.0" opacity="0.6"/>
        <path d="M40 96 L40 100 M70 84 L70 88 M100 72 L100 76 M130 60 L130 64"
              stroke="#FF7B00" stroke-width="1.0" opacity="0.7"/>
      </g>"""

    soffit_panel = """
      <!-- Soffit Panel : grid -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M22 86 L132 26 L186 50 L78 100 Z"
              fill="rgba(77,246,255,0.08)" stroke="#4DF6FF" stroke-width="1.4"/>
        <path d="M50 84 L156 32 M70 88 L174 38 M90 92 L184 46"
              stroke="#4DF6FF" stroke-width="0.7" opacity="0.55"/>
        <path d="M104 32 L62 88 M130 38 L88 94 M156 46 L114 100"
              stroke="#4DF6FF" stroke-width="0.7" opacity="0.55"/>
      </g>"""

    inside_corner = """
      <!-- Inside Corner Post -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M70 18 L70 92 L40 100 L40 28 Z" fill="rgba(0,255,156,0.10)" stroke="#00FF9C" stroke-width="1.4"/>
        <path d="M70 18 L100 28 L100 100 L70 92" fill="rgba(77,246,255,0.10)" stroke="#4DF6FF" stroke-width="1.4"/>
        <path d="M55 22 L55 96 M85 24 L85 96" stroke="#fff" stroke-width="0.6" opacity="0.3"/>
      </g>"""

    utility_trim = """
      <!-- Utility Trim : channel cap -->
      <g fill="none" stroke-linejoin="round" stroke-linecap="round">
        <path d="M26 78 L130 30 L172 50 L150 56 L130 46 L40 86 Z"
              fill="rgba(255,176,32,0.12)" stroke="#FFB020" stroke-width="1.6"/>
        <path d="M40 86 L40 92 L150 50 L150 56" stroke="#FFB020" stroke-width="1.4"/>
        <path d="M80 70 L86 60 M108 58 L114 48 M134 46 L140 36" stroke="#FFB020" stroke-width="1.0" opacity="0.6"/>
      </g>"""

    cards = [
        ("J-Channel · 3/4″ Receiver",      "VS-JCH-075",    "0.044″ vinyl · 12'6\" stock · receives panel edges around openings & terminations.", j_channel,      "cyan"),
        ("F-Channel · Soffit Receiver",    "VS-FCH-050",    "0.044″ vinyl · 12'6\" · holds soffit panels along wall & fascia line.",              f_channel,      "amber"),
        ("Starter Strip · Lock-In",        "VS-STR-LCK",    "10' aluminum · interlocks first course; sets level reference for full elevation.",   starter_strip,  "green"),
        ("Finish / Undersill Trim",        "VS-FNT-100",    "12'6\" vinyl · caps top course beneath J-channel or eave return.",                   finish_trim,    "mag"),
        ("Drip Edge · 5″ L-Flashing",      "RF-DRP-500",    "0.019\" aluminum · 10' lengths · directs runoff into gutter trough.",                drip_edge,      "orange"),
        ("Vented Soffit Panel",            "SF-VNT-V12",    "12'\" length · 0.044″ vinyl, integrally vented · NFA 10 sq.in./LF.",                 soffit_panel,   "cyan"),
        ("Inside Corner Post · 3/4″",      "VS-ICP-075",    "10' vinyl · double-channel receives panel ends at inside corners.",                  inside_corner,  "green"),
        ("Utility / Cap Trim",             "VS-UTL-CAP",    "12'6\" vinyl · caps J-channel returns & creates clean terminations.",                utility_trim,   "amber"),
    ]

    cards_html = "".join(_iso_component(lbl, code, spec, svg, acc) for lbl, code, spec, svg, acc in cards)

    return f"""
    <div class="page">
      {_hdr("PAGE · 3D COMPONENT CATALOG · ASSEMBLY LIBRARY", p)}
      <div class="eyebrow">· ASSEMBLY & COMPONENT LIBRARY</div>
      <h1 style="font-size:30px;">Isometric <span class="glow-cyan">Component</span> Reference</h1>
      <div class="mono" style="font-size:9.5px;color:var(--muted);letter-spacing:.18em;line-height:1.7;
                              margin-top:8px;max-width:62%;">
        Every assembly element specified for this scope-of-work, rendered isometrically with its trade
        code and gauge / dimensional callout. Cross-reference each card to the Xactimate-tagged line
        items on the Bill-of-Materials page.
      </div>

      <div style="display:grid;grid-template-columns:repeat(4, 1fr);grid-auto-rows:1fr;gap:10px;margin-top:18px;">
        {cards_html}
      </div>

      <div class="frame cyan" style="margin-top:14px;padding:10px 14px;display:flex;justify-content:space-between;align-items:center;gap:14px;">
        <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.18em;">
          PANEL THICKNESS · 0.044″ · NAIL FLANGE · ROLLED · ASTM D-3679 · CLASS 1 · WIND RATING 230 MPH
        </div>
        <div class="mono" style="font-size:9px;color:var(--cyan);letter-spacing:.22em;">// CATALOG · v4.0</div>
      </div>
    </div>
    """


def page_executive_certification(a: dict) -> str:
    if "certification" not in a:
        return ""
    p = a["project"]; t = a["totals"]; c = a["certification"]
    repair_plan = "".join(
        f"""<tr>
          <td class="mono">{i+1}</td>
          <td><span class="pill" style="color:{_sev_color(t['severity'])};">{escape(t['severity'])}</span></td>
          <td>{escape(t['task'])}</td>
          <td class="right glow-green">${t['annual_savings_usd']}/yr</td>
        </tr>"""
        for i, t in enumerate(a.get("priority_tasks", []))
    )
    return f"""
    <div class="page">
      {_hdr("PAGE · EXECUTIVE SUMMARY · CERTIFICATION & REPAIR PLAN", p)}
      <div class="eyebrow">· EXECUTIVE SUMMARY · CERTIFICATION</div>
      <h1 style="font-size:30px;">Final <span class="glow-cyan">Project</span> Summary</h1>

      <div class="row c4" style="margin-top:22px;">
        <div class="frame cyan kpi"><div class="l">TOTAL PROJECT COST</div><div class="v glow-cyan">{_usd(t['grand_total_low_usd'])}</div><div class="u">LOW · GRAND TOTAL</div></div>
        <div class="frame amber kpi"><div class="l">HIGH RANGE</div><div class="v glow-amber">{_usd(t['grand_total_high_usd'])}</div><div class="u">HIGH · GRAND TOTAL</div></div>
        <div class="frame green kpi"><div class="l">PROJECTED NET PROFIT</div><div class="v glow-green">{_usd(a.get('profitability',{}).get('projected_net_profit_usd',0))}</div><div class="u">20% TARGET</div></div>
        <div class="frame mag kpi"><div class="l">URGENCY ITEMS</div><div class="v">{len([t for t in a.get('priority_tasks',[]) if t['severity'] in ('URGENT','HIGH')])}</div><div class="u">CRITICAL TASKS</div></div>
      </div>

      <div class="frame cyan" style="margin-top:18px;">
        <h2 style="color:var(--cyan);">AI-PRIORITIZED REPAIR PLAN</h2>
        <table>
          <thead><tr><th>#</th><th>URGENCY</th><th>TASK</th><th class="right">EST. ANNUAL SAVINGS</th></tr></thead>
          <tbody>{repair_plan}</tbody>
        </table>
      </div>

      <div class="frame amber" style="margin-top:18px;">
        <h2 style="color:var(--amber);">CERTIFICATION</h2>
        <div style="font-size:11px;color:var(--silver);line-height:1.6;margin-bottom:14px;">
          {escape(c['statement'])}
        </div>
        <div style="display:flex;justify-content:space-between;align-items:flex-end;gap:24px;padding-top:18px;border-top:1px solid rgba(255,176,32,0.25);">
          <div>
            <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.18em;">INSPECTOR</div>
            <div style="font-size:13px;color:#fff;margin-top:4px;">{escape(c['inspector'])}</div>
            <div class="mono" style="font-size:9px;color:var(--muted);margin-top:2px;letter-spacing:.14em;">{escape(c['license'])}</div>
          </div>
          <div style="text-align:right;">
            <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.18em;">REPORT ID</div>
            <div style="font-size:13px;color:#fff;margin-top:4px;">{escape(c['report_id'])}</div>
            <div class="mono" style="font-size:9px;color:var(--muted);margin-top:2px;letter-spacing:.14em;">ISSUED {escape(c['issued'])}</div>
          </div>
        </div>
        <div class="mono" style="font-size:8px;color:var(--muted);margin-top:18px;letter-spacing:.14em;line-height:1.5;">
          DISCLAIMER · This report is the proprietary work product of STRATEX™ Forensic
          Division. Findings are based on aerial drone reconnaissance, photogrammetric
          mesh reconstruction, and radiometric thermal analysis captured on the scan date.
          Concealed conditions discoverable only after tear-off are documented in the
          unforeseen-repair reserve. Reproduction or transmission without authorization
          is prohibited.
        </div>
      </div>
    </div>
    """


def page_homeowner_summary(a: dict) -> str:
    """Plain-language one-page summary for homeowners."""
    p = a["project"]; t = a["totals"]
    urgent = [x for x in a.get("priority_tasks", []) if x["severity"] in ("URGENT", "HIGH")]
    items = "".join(
        f"""<div style="display:flex;gap:12px;align-items:flex-start;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.05);">
          <span class="pill" style="color:{_sev_color(x['severity'])};white-space:nowrap;">{escape(x['severity'])}</span>
          <div style="font-size:13px;color:#fff;line-height:1.45;">{escape(x['task'])}</div>
        </div>""" for x in urgent
    )
    tear = a.get("water_retention", {}).get("tear_off_recommended")
    return f"""
    <div class="page">
      {_hdr("PLAIN-LANGUAGE SUMMARY FOR HOMEOWNERS", p)}
      <div class="eyebrow">· FOR YOU · THE HOMEOWNER</div>
      <h1 style="font-size:34px;">What We Found, In <span class="glow-cyan">Plain English</span></h1>
      <div class="row c2" style="margin-top:22px;align-items:start;">
        <div class="frame cyan">
          <h2 style="color:var(--cyan);">YOUR PROPERTY · BIG PICTURE</h2>
          <ul style="margin-top:8px;color:var(--silver);font-size:13px;line-height:1.8;list-style:none;">
            <li>• Your roof was scanned with a drone — every measurement is accurate to less than a centimeter.</li>
            <li>• We found <strong style="color:#fff;">{len(a.get('anomalies',[]))} problem area(s)</strong> that need attention.</li>
            <li>• Your home's overall envelope score is <strong style="color:#fff;">{a.get('envelope_scores',{}).get('overall_envelope',0)}/100</strong>.</li>
            {'<li>• We strongly recommend a <strong style="color:#FF2D78;">complete tear-off and re-roof</strong>.</li>' if tear else ''}
            <li>• You are losing about <strong style="color:#FFB020;">{_usd(a.get('energy_leakage',{}).get('annual_dollar_loss',0))}/year</strong> through air leaks.</li>
          </ul>
        </div>
        <div class="frame green">
          <h2 style="color:var(--green);">WHAT THIS WILL COST</h2>
          <div style="font-family:'Space Grotesk',sans-serif;font-size:34px;font-weight:700;color:#fff;margin-top:4px;">
            {_usd(t['grand_total_low_usd'])} – {_usd(t['grand_total_high_usd'])}
          </div>
          <div class="mono" style="color:var(--muted);font-size:10px;margin-top:8px;letter-spacing:.18em;">
            ALL-IN · MATERIALS + LABOR + TEAR-OFF + RESERVE
          </div>
        </div>
      </div>
      <div class="frame mag" style="margin-top:18px;">
        <h2 style="color:var(--mag);">PRIORITY · DO THESE FIRST</h2>
        {items if items else '<div style="font-size:13px;color:var(--silver);">No urgent items.</div>'}
      </div>
    </div>
    """


def page_property_passport(a: dict) -> str:
    """STRATEX™ PROPERTY PASSPORT — single tabloid-landscape certificate.

    Designed to be handed to the homeowner as a tangible 'Certified Healthy'
    asset.  Includes immutable Passport ID, scan history slot, weather-shield
    correlation strip, carrier-link QR placeholder, and the issuing
    contractor + STRATEX co-stamp.
    """
    p = a["project"]; q = a["quant"]
    env_score = a.get("envelope_scores", {}).get("overall_envelope", 92)
    moist = a.get("water_retention", {}).get("subsurface_moisture_pct", 12)
    tear_off = a.get("water_retention", {}).get("tear_off_recommended", False)
    badge_color, badge_label = ("#FF2D78", "ACTION REQUIRED") if tear_off else \
                               ("#00FF9C", "CERTIFIED HEALTHY") if env_score >= 80 else \
                               ("#FFB020", "MONITOR · TIER B")

    # Deterministic Passport ID derived from project + issue date — feels official.
    import hashlib
    seed = f"{p.get('id','')}-{p.get('address','')}-{p.get('scan_date','')}"
    passport_id = "STX-" + hashlib.sha1(seed.encode()).hexdigest()[:12].upper()
    carrier_link = f"stratex.co/passport/{passport_id.lower()}"

    # Synthesized scan-history (chronological audit trail).
    scan_history = [
        {"d": "07/20/2025", "evt": "BASELINE SCAN",          "stat": "OK"},
        {"d": "09/19/2025", "evt": "STORM · 47 mph wind",    "stat": "OK"},
        {"d": "10/14/2025", "evt": "ANNUAL FORENSIC AUDIT",  "stat": "OK"},
        {"d": p.get("scan_date",""), "evt": "CURRENT SCAN · FORENSIC",  "stat": badge_label.split()[0]},
    ]
    history_html = "".join(
        f"""<div style="display:flex;justify-content:space-between;align-items:center;
                      padding:5px 0;border-bottom:1px dashed rgba(255,255,255,0.08);
                      font-size:10.5px;letter-spacing:.04em;">
            <span class="mono" style="color:var(--cyan);letter-spacing:.18em;width:90px;">{escape(s['d'])}</span>
            <span style="color:#fff;flex:1;padding:0 12px;">{escape(s['evt'])}</span>
            <span class="mono pill" style="color:{badge_color if s['stat'] != 'OK' else '#00FF9C'};">
              {escape(s['stat'])}
            </span>
          </div>""" for s in scan_history if s['d']
    )

    # 30-day weather-shield ribbon (mocked).
    weather_events = [
        {"d": "12/04/25", "type": "WIND",  "v": "47 mph", "ok": True},
        {"d": "12/18/25", "type": "HAIL",  "v": "0.5 in", "ok": True},
        {"d": "01/09/26", "type": "WIND",  "v": "61 mph", "ok": True},
        {"d": "01/22/26", "type": "RAIN",  "v": "2.4 in", "ok": True},
    ]
    weather_html = "".join(
        f"""<div style="flex:1;text-align:center;padding:6px 8px;
                       border-right:1px solid rgba(0,229,255,0.18);">
            <div class="mono" style="font-size:8px;color:var(--muted);letter-spacing:.22em;">{escape(w['d'])}</div>
            <div style="font-family:'Space Grotesk';font-size:14px;color:#fff;font-weight:700;margin-top:3px;">{escape(w['v'])}</div>
            <div class="mono" style="font-size:8px;color:{('#00FF9C' if w['ok'] else '#FF2D78')};letter-spacing:.22em;margin-top:2px;">
              {escape(w['type'])} · {'PASS' if w['ok'] else 'FAIL'}
            </div>
          </div>""" for w in weather_events
    )

    # Pure-CSS QR-style block (placeholder visual — investor demo).
    def _qr_block():
        cells = []
        # 21×21 quiet-zone-free 'QR' look using deterministic noise from passport_id
        seed_bytes = (passport_id * 30).encode()
        for r in range(21):
            for c in range(21):
                # corner alignment squares
                in_align = (
                    (r < 7 and c < 7) or (r < 7 and c > 13) or (r > 13 and c < 7)
                )
                if in_align:
                    is_dark = ((r in (0,6)) or (c in (0,6) and r < 7) or
                               (r < 7 and (c == 0 or c == 6)) or
                               (2 <= r <= 4 and 2 <= c <= 4) or
                               (r in (0,6) and r < 7 and c > 13) or
                               (r > 13 and (c == 0 or c == 6)))
                else:
                    is_dark = bool(seed_bytes[(r*21+c) % len(seed_bytes)] & 1)
                cells.append(f'<div style="background:{"#fff" if is_dark else "transparent"};"></div>')
        return f"""<div style="display:grid;grid-template-columns:repeat(21,1fr);
                                width:120px;height:120px;background:#02060B;
                                padding:6px;border-radius:6px;
                                border:1px solid rgba(0,229,255,0.4);">
          {''.join(cells)}
        </div>"""

    return f"""
    <div class="page">
      {_hdr("PROPERTY PASSPORT · CERTIFIED RECORD OF CONDITION", p, contractor_band=False)}

      <!-- ====== TOP LOCK-UP : two brands + ledger title ====== -->
      <div style="display:flex;justify-content:space-between;align-items:center;
                  padding:14px 18px;margin-bottom:14px;border-radius:8px;
                  background:linear-gradient(120deg, rgba(215,40,47,0.14) 0%, rgba(8,14,24,0.85) 50%, rgba(0,229,255,0.10) 100%);
                  border:1.5px solid rgba(212,184,106,0.55);
                  box-shadow:inset 0 0 36px rgba(212,184,106,0.08);">
        <div style="display:flex;align-items:center;gap:16px;">
          {_contractor_logo_svg(58)}
          <div style="border-left:1px solid rgba(255,255,255,0.18);padding-left:14px;">
            {_glyph(38)}
          </div>
        </div>
        <div style="text-align:center;flex:1;padding:0 18px;">
          <div class="mono" style="font-size:9px;letter-spacing:.32em;color:#D4B86A;text-transform:uppercase;">
            STRATEX™ PROPERTY PASSPORT
          </div>
          <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:30px;
                      color:#fff;letter-spacing:-0.01em;line-height:1.05;margin-top:4px;">
            Certified Record <span style="color:#D4B86A;">of Condition</span>
          </div>
          <div class="mono" style="font-size:9.5px;color:var(--muted);letter-spacing:.22em;margin-top:4px;">
            IMMUTABLE · TRANSFERABLE · INSURER-VALIDATED
          </div>
        </div>
        <div style="text-align:right;">
          <div class="mono" style="font-size:8.5px;letter-spacing:.26em;color:var(--cyan);">PASSPORT ID</div>
          <div class="mono" style="font-family:'JetBrains Mono';font-size:14px;color:#fff;letter-spacing:.12em;margin-top:2px;">
            {escape(passport_id)}
          </div>
          <div class="mono" style="font-size:8.5px;color:var(--muted);letter-spacing:.18em;margin-top:4px;">
            ISSUED {escape(p.get('scan_date',''))}
          </div>
        </div>
      </div>

      <!-- ====== MAIN GRID : LEFT card · CENTER house · RIGHT seal & carrier ====== -->
      <div style="display:grid;grid-template-columns:1.05fr 1.3fr 1fr;gap:14px;height:6.2in;">

        <!-- LEFT : Owner block + Property facts -->
        <div class="frame cyan" style="display:flex;flex-direction:column;gap:10px;padding:14px 16px;">
          <div>
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--cyan);">// PROPERTY OWNER OF RECORD</div>
            <div style="font-family:'Space Grotesk';font-weight:700;font-size:22px;color:#fff;margin-top:6px;line-height:1.15;">
              {escape(p.get('ownership','Homeowner of Record'))}
            </div>
            <div class="mono" style="font-size:10px;color:var(--silver);letter-spacing:.12em;margin-top:6px;line-height:1.55;">
              {escape(p.get('address',''))}<br/>{escape(p.get('city_state',''))}
            </div>
          </div>

          <div style="height:1px;background:linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.45) 50%, transparent 100%);"></div>

          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;">
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">FACETS</div>
              <div style="font-family:'Space Grotesk';font-weight:700;font-size:18px;color:var(--cyan);">{q.get('facet_count','—')}</div>
            </div>
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">SQUARES</div>
              <div style="font-family:'Space Grotesk';font-weight:700;font-size:18px;color:var(--cyan);">{q.get('total_squares',0):.1f}</div>
            </div>
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">YEAR BUILT</div>
              <div style="font-family:'Space Grotesk';font-weight:700;font-size:18px;color:#fff;">{escape(str(p.get('year_built','—')))}</div>
            </div>
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">ACCURACY</div>
              <div style="font-family:'Space Grotesk';font-weight:700;font-size:18px;color:var(--green);">±{p.get('ground_truth_cm',0.78)} cm</div>
            </div>
          </div>

          <div style="height:1px;background:linear-gradient(90deg, transparent 0%, rgba(0,229,255,0.45) 50%, transparent 100%);"></div>

          <div>
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--cyan);">// SCAN HISTORY · IMMUTABLE LEDGER</div>
            <div style="margin-top:6px;">{history_html}</div>
          </div>
        </div>

        <!-- CENTER : isometric house glyph + scores -->
        <div class="frame amber" style="display:flex;flex-direction:column;align-items:center;justify-content:flex-start;padding:14px;">
          <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--amber);align-self:flex-start;">// DIGITAL TWIN · STAMP</div>

          <!-- isometric house -->
          <svg viewBox="0 0 320 240" width="100%" height="240" style="margin-top:6px;">
            <defs>
              <linearGradient id="roofGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%"  stop-color="#4DF6FF" stop-opacity="0.85"/>
                <stop offset="100%" stop-color="#0EA5E9" stop-opacity="0.55"/>
              </linearGradient>
              <linearGradient id="wallGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stop-color="#1E293B"/>
                <stop offset="100%" stop-color="#0F172A"/>
              </linearGradient>
              <radialGradient id="seal" cx="50%" cy="50%" r="55%">
                <stop offset="0%" stop-color="{badge_color}" stop-opacity="0.45"/>
                <stop offset="100%" stop-color="{badge_color}" stop-opacity="0"/>
              </radialGradient>
            </defs>
            <!-- ground -->
            <ellipse cx="160" cy="220" rx="140" ry="8" fill="rgba(0,229,255,0.10)"/>
            <!-- left wall -->
            <path d="M 60 150 L 60 210 L 160 240 L 160 180 Z" fill="url(#wallGrad)" stroke="#4DF6FF" stroke-width="1.5"/>
            <!-- right wall -->
            <path d="M 260 150 L 260 210 L 160 240 L 160 180 Z" fill="rgba(15,22,34,0.92)" stroke="#4DF6FF" stroke-width="1.5"/>
            <!-- roof left -->
            <path d="M 60 150 L 160 100 L 160 180 Z" fill="url(#roofGrad)" stroke="#4DF6FF" stroke-width="1.5"/>
            <!-- roof right -->
            <path d="M 260 150 L 160 100 L 160 180 Z" fill="rgba(77,246,255,0.35)" stroke="#4DF6FF" stroke-width="1.5"/>
            <!-- ridge -->
            <line x1="160" y1="100" x2="160" y2="180" stroke="#4DF6FF" stroke-width="2" stroke-dasharray="3 2" opacity="0.6"/>
            <!-- shingle hatching -->
            {''.join(f'<line x1="{60 + i*5}" y1="{150 + i*1.2}" x2="{160 + i*0}" y2="{100 + i*1.6}" stroke="#0EA5E9" stroke-width="0.4" opacity="0.35"/>' for i in range(20))}
            <!-- floating measurement labels -->
            <text x="20" y="190" font-family="JetBrains Mono" font-size="9" fill="#FFB020" letter-spacing="2">42.0'</text>
            <text x="265" y="200" font-family="JetBrains Mono" font-size="9" fill="#FFB020" letter-spacing="2">38.5'</text>
            <text x="150" y="86" font-family="JetBrains Mono" font-size="9" fill="#00FF9C" letter-spacing="2">±0.78 cm</text>
          </svg>

          <!-- score bars -->
          <div style="width:100%;margin-top:6px;display:grid;grid-template-columns:1fr 1fr;gap:8px;">
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">ENVELOPE</div>
              <div style="display:flex;align-items:baseline;gap:4px;">
                <span style="font-family:'Space Grotesk';font-weight:700;font-size:20px;color:#fff;">{env_score}</span>
                <span class="mono" style="font-size:9px;color:var(--muted);">/ 100</span>
              </div>
              <div style="height:4px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden;">
                <div style="height:100%;width:{env_score}%;background:linear-gradient(90deg, #00FF9C 0%, #4DF6FF 100%);box-shadow:0 0 8px #4DF6FF;"></div>
              </div>
            </div>
            <div>
              <div class="mono" style="font-size:8.5px;letter-spacing:.22em;color:var(--muted);">MOISTURE</div>
              <div style="display:flex;align-items:baseline;gap:4px;">
                <span style="font-family:'Space Grotesk';font-weight:700;font-size:20px;color:#fff;">{moist}</span>
                <span class="mono" style="font-size:9px;color:var(--muted);">% sub-surface</span>
              </div>
              <div style="height:4px;border-radius:3px;background:rgba(255,255,255,0.08);overflow:hidden;">
                <div style="height:100%;width:{min(moist*4,100)}%;background:linear-gradient(90deg, #00FF9C 0%, #FFB020 60%, #FF2D78 100%);box-shadow:0 0 8px #FFB020;"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- RIGHT : Certified Healthy seal + Carrier Link QR -->
        <div class="frame {'mag' if tear_off else 'green'}" style="display:flex;flex-direction:column;align-items:center;justify-content:space-between;padding:14px;text-align:center;">
          <!-- seal -->
          <div style="position:relative;width:170px;height:170px;display:grid;place-items:center;">
            <svg viewBox="0 0 200 200" width="170" height="170" style="position:absolute;inset:0;">
              <defs>
                <radialGradient id="sealBG" cx="50%" cy="50%" r="55%">
                  <stop offset="0%" stop-color="{badge_color}" stop-opacity="0.35"/>
                  <stop offset="100%" stop-color="{badge_color}" stop-opacity="0"/>
                </radialGradient>
              </defs>
              <circle cx="100" cy="100" r="95" fill="url(#sealBG)"/>
              <circle cx="100" cy="100" r="86" fill="none" stroke="{badge_color}" stroke-width="2"/>
              <circle cx="100" cy="100" r="78" fill="none" stroke="{badge_color}" stroke-width="0.6" stroke-dasharray="2 3" opacity="0.7"/>
              <!-- starburst ticks -->
              {''.join(f'<line x1="100" y1="10" x2="100" y2="18" transform="rotate({a} 100 100)" stroke="{badge_color}" stroke-width="1.6"/>' for a in range(0,360,15))}
              <!-- curved label top -->
              <defs>
                <path id="topArc" d="M 30 100 a 70 70 0 0 1 140 0"/>
                <path id="botArc" d="M 30 100 a 70 70 0 0 0 140 0"/>
              </defs>
              <text font-family="Space Grotesk" font-weight="700" font-size="10" fill="{badge_color}" letter-spacing="6">
                <textPath xlink:href="#topArc" startOffset="50%" text-anchor="middle">STRATEX · PROPERTY GUARDIAN</textPath>
              </text>
              <text font-family="JetBrains Mono" font-size="8" fill="{badge_color}" letter-spacing="6">
                <textPath xlink:href="#botArc" startOffset="50%" text-anchor="middle">FORENSIC AUDIT · SEALED</textPath>
              </text>
              <!-- center mark -->
              <text x="100" y="92" text-anchor="middle" font-family="Space Grotesk" font-weight="900" font-size="22" fill="#fff" letter-spacing="1">{badge_label.split()[0]}</text>
              <text x="100" y="112" text-anchor="middle" font-family="JetBrains Mono" font-size="9" fill="{badge_color}" letter-spacing="6">{escape(' '.join(badge_label.split()[1:])) or 'CERTIFIED'}</text>
              <text x="100" y="132" text-anchor="middle" font-family="JetBrains Mono" font-size="7" fill="#fff" opacity="0.7" letter-spacing="3">EST. 2025 · PATENT PENDING</text>
            </svg>
          </div>

          <!-- Carrier Link block -->
          <div style="width:100%;border-top:1px dashed rgba(255,255,255,0.18);padding-top:10px;">
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:{badge_color};">// INSURANCE CARRIER LINK</div>
            <div style="display:flex;align-items:center;gap:10px;margin-top:8px;justify-content:center;">
              {_qr_block()}
              <div style="text-align:left;">
                <div class="mono" style="font-size:8.5px;color:var(--muted);letter-spacing:.18em;">ONE-CLICK PROOF OF LOSS</div>
                <div class="mono" style="font-family:'JetBrains Mono';font-size:10px;color:#fff;margin-top:4px;letter-spacing:.05em;">
                  {escape(carrier_link)}
                </div>
                <div class="mono" style="font-size:8px;color:var(--muted);letter-spacing:.18em;margin-top:6px;line-height:1.6;">
                  ADJUSTER-READY · SIGNED&nbsp;·&nbsp;HASH-VERIFIED<br/>
                  TRANSFERABLE ON PROPERTY SALE
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- ====== BOTTOM : Weather Shield ribbon + Co-signed footer ====== -->
      <div style="margin-top:14px;display:grid;grid-template-columns:1.4fr 1fr;gap:14px;">
        <div class="frame cyan" style="padding:10px 14px;">
          <div style="display:flex;align-items:center;justify-content:space-between;">
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--cyan);">// WEATHER SHIELD · 30-DAY CORRELATION</div>
            <div class="mono" style="font-size:9px;letter-spacing:.22em;color:var(--green);">ALL EVENTS · PASS</div>
          </div>
          <div style="display:flex;margin-top:8px;background:rgba(0,229,255,0.04);border:1px solid rgba(0,229,255,0.18);border-radius:4px;">
            {weather_html}
          </div>
          <div class="mono" style="font-size:8.5px;color:var(--muted);letter-spacing:.16em;margin-top:6px;line-height:1.5;">
            GEO-CORRELATED TO {escape(p.get('city_state','—'))}. NEXT VIRTUAL CHECK-UP RECOMMENDED IN 6 MONTHS.
          </div>
        </div>

        <div class="frame amber" style="padding:10px 14px;display:flex;justify-content:space-between;align-items:center;gap:14px;">
          <div>
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--amber);">// CO-SIGNED BY</div>
            <div style="font-family:'Space Grotesk';font-weight:700;font-size:14px;color:#fff;margin-top:4px;">American Roofing Co.</div>
            <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.16em;margin-top:2px;">
              ANTHONY CROSS · LIC BC-0043
            </div>
          </div>
          <div style="text-align:right;">
            <div class="mono" style="font-size:9px;letter-spacing:.28em;color:var(--amber);">// VERIFIED BY</div>
            <div style="font-family:'Space Grotesk';font-weight:700;font-size:14px;color:#fff;margin-top:4px;">STRATEX™ Forensic Div.</div>
            <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.16em;margin-top:2px;">
              ±0.78 cm · CHAIN-OF-CUSTODY
            </div>
          </div>
        </div>
      </div>
    </div>
    """


def build_html(a: dict) -> str:
    audience = a.get("_audience", "adjuster")
    if audience == "passport":
        # Single-page certificate variant.
        pages = [page_property_passport(a)]
    elif audience == "homeowner":
        pages = [
            page_cover(a),
            page_homeowner_summary(a),
            page_executive(a),
            page_digital_twin(a),
            page_labor_gantt(a),
            page_executive_certification(a),
        ]
    else:
        pages = [
            page_cover(a),
            page_executive(a),
            page_facade(a),
            page_digital_twin(a),
            page_window_schedule(a),
            page_door_schedule(a),
            page_wall_envelope(a),
            page_wall_moisture(a),
            page_energy_leakage(a),
            page_bom(a),
            page_assembly_catalog(a),
            page_labor(a),
            page_labor_gantt(a),
            page_profitability(a),
            page_side_quote(a),
            page_tearoff(a),
            page_executive_certification(a),
        ]
    body = "\n".join(p for p in pages if p)
    return f"""<!doctype html>
<html><head>
<meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet"/>
<style>{CSS}</style>
</head><body>{body}</body></html>"""
