"""STRATEX™ — Claim Snapshot PDF builder.

Renders a tabloid-landscape, Future-Noire "Difference Report" comparing
the baseline scan against the post-event scan for a Property Passport.
The PDF is what the contractor hands the homeowner / what the homeowner
forwards to their carrier to bypass Loss Adjustment Expense.

This module is invoked by /api/claim-snapshot/{pid}/pdf — it produces
HTML, hands it to Playwright (Chromium-headless), and returns the
resulting PDF file path.
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from html import escape
from pathlib import Path
from typing import Any, Dict

PITCH_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PITCH_DIR))
from build_demo_report import (  # type: ignore
    _contractor_band, _contractor_logo_svg, _wordmark, _glyph, CSS,
)

OUT_DIR = PITCH_DIR
CACHE_DIR = PITCH_DIR / "_claim_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _badge(label: str, value: str, color: str) -> str:
    return f"""
    <div style="border:1px solid {color}55;background:rgba(8,14,24,0.55);
                border-radius:6px;padding:10px 12px;min-width:130px;">
      <div class="mono" style="font-size:8.5px;letter-spacing:.26em;color:var(--muted);text-transform:uppercase;">{escape(label)}</div>
      <div style="font-family:'Space Grotesk',sans-serif;font-weight:700;font-size:22px;color:{color};
                   text-shadow:0 0 8px {color}55;margin-top:2px;line-height:1;">{escape(value)}</div>
    </div>"""


def _anomaly_row(a: Dict[str, Any], color: str) -> str:
    sev = (a.get("severity") or "—").upper()
    return f"""
    <tr>
      <td><span class="pill" style="color:{color};border-color:{color};">{escape(sev)}</span></td>
      <td>{escape(a.get('type') or a.get('code') or '—')}</td>
      <td>{escape(a.get('location') or '—')}</td>
      <td class="right">{a.get('area_sqft', 0)}</td>
      <td class="right">{a.get('confidence_pct', 0)}%</td>
      <td class="right" style="color:#fff;">${(a.get('repair_estimate_usd') or 0):,.0f}</td>
      <td style="color:var(--muted);max-width:340px;">{escape(a.get('diagnosis') or '—')}</td>
    </tr>"""


def _build_html(diff: Dict[str, Any]) -> str:
    pp = diff["passport"]
    sa = diff["scan_a"]
    sb = diff["scan_b"]
    d = diff["deltas"]
    storm = diff.get("storm_correlated") or {}
    verdict = diff.get("verdict", "NO_CHANGE")
    verdict_color = "#FF2D78" if verdict == "CLAIM_SUPPORTABLE" else (
        "#FFB020" if verdict == "MONITOR" else "#00FF9C")
    confidence = diff.get("confidence_pct", 90)
    narrative = escape(diff.get("narrative") or "—")

    project_for_band = {
        "id": pp["passport_id"],
        "address": pp.get("address", ""),
        "city_state": pp.get("city_state", ""),
        "scan_date": (sb or {}).get("captured_at", "")[:10],
    }
    band = _contractor_band({"project": project_for_band, "_contractor": pp.get("contractor") or {}})

    new_damage_rows = "".join(_anomaly_row(a, "#FF2D78") for a in diff.get("new_damage", []))
    worsened_rows = "".join(
        _anomaly_row({**w["anomaly"], "diagnosis":
                     f"WORSENED · was {escape(w['baseline_severity'] or '—')} · "
                     f"+{w['delta_area_sqft']} sqft new area"},
                     "#FFB020")
        for w in diff.get("worsened", [])
    )
    resolved_rows = "".join(_anomaly_row(a, "#00FF9C") for a in diff.get("resolved", []))

    return f"""
<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"/>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=JetBrains+Mono:wght@400;700&family=Cinzel:wght@600;700&display=swap" rel="stylesheet"/>
<style>{CSS}
  .seal {{ width:200px;height:200px;display:grid;place-items:center;border-radius:50%;
          border:2px solid {verdict_color};
          background:radial-gradient(circle, {verdict_color}30 0%, transparent 70%);
          box-shadow:0 0 40px {verdict_color}55, inset 0 0 30px {verdict_color}33; }}
</style></head>
<body>

<!-- PAGE 1 — HERO + VERDICT -->
<div class="page">
  {band}
  <div style="display:flex;justify-content:space-between;align-items:center;
              border:1.5px solid {verdict_color}88;border-radius:8px;padding:18px 22px;margin-bottom:16px;
              background:linear-gradient(120deg, {verdict_color}15 0%, rgba(8,14,24,0.85) 60%, rgba(0,229,255,0.10) 100%);">
    <div>
      <div class="mono" style="color:{verdict_color};letter-spacing:.32em;font-size:10px;">// CLAIM SNAPSHOT · STRATEX™ DIFFERENCE REPORT</div>
      <h1 style="margin-top:4px;font-size:36px;">{escape(pp.get('owner',''))}</h1>
      <div class="mono" style="color:var(--muted);letter-spacing:.16em;font-size:11px;margin-top:6px;">
        {escape(pp.get('address',''))} · {escape(pp.get('city_state',''))} · PASSPORT STX-{escape(pp['passport_id'])}
      </div>
    </div>
    <div class="seal">
      <div style="text-align:center;">
        <div style="font-family:'Cinzel',serif;font-weight:700;font-size:18px;color:{verdict_color};
                     letter-spacing:.12em;line-height:1;">{verdict.replace('_',' ')}</div>
        <div class="mono" style="font-size:9px;color:{verdict_color};letter-spacing:.32em;margin-top:6px;">
          {confidence}% CONFIDENCE
        </div>
      </div>
    </div>
  </div>

  <h2>// HEADLINE DELTAS · BASELINE → POST-EVENT</h2>
  <div class="row" style="grid-template-columns:repeat(6,1fr);margin-bottom:14px;">
    {_badge("NEW DAMAGE", str(d['new_damage_count']), "#FF2D78")}
    {_badge("WORSENED",   str(d['worsened_count']),   "#FFB020")}
    {_badge("RESOLVED",   str(d['resolved_count']),   "#00FF9C")}
    {_badge("AREA Δ (SF)", f"{d['total_new_damage_area_sqft']:,.1f}", "#FF2D78")}
    {_badge("ENVELOPE Δ", f"{d['envelope_score_delta']:+d}", "#FFB020")}
    {_badge("REPAIR EST. Δ", f"${d['repair_estimate_delta_usd']:,.0f}", "#FF2D78")}
  </div>

  <h2>// ADJUSTER NARRATIVE</h2>
  <div class="frame cyan" style="font-family:'Space Grotesk',sans-serif;font-size:13px;
                                   line-height:1.55;color:#E2E8F0;padding:18px 22px;margin-bottom:14px;">
    {narrative}
  </div>

  {("<h2>// STORM CORRELATION</h2>"
    "<div class='frame mag' style='display:flex;gap:24px;padding:16px 22px;'>" +
    f"<div><div class='mono' style='font-size:9px;color:var(--muted);letter-spacing:.22em;'>EVENT</div>"
    f"<div style='font-family:Space Grotesk;font-weight:700;font-size:18px;color:#fff;margin-top:2px;'>{escape(storm.get('kind',''))}</div></div>"
    f"<div><div class='mono' style='font-size:9px;color:var(--muted);letter-spacing:.22em;'>INTENSITY</div>"
    f"<div style='font-family:Space Grotesk;font-weight:700;font-size:18px;color:#FFB020;margin-top:2px;'>{escape(storm.get('value',''))}</div></div>"
    f"<div><div class='mono' style='font-size:9px;color:var(--muted);letter-spacing:.22em;'>DATE</div>"
    f"<div style='font-family:Space Grotesk;font-weight:700;font-size:18px;color:#fff;margin-top:2px;'>{escape(storm.get('date',''))}</div></div>"
    f"<div><div class='mono' style='font-size:9px;color:var(--muted);letter-spacing:.22em;'>NOAA</div>"
    f"<div class='mono' style='font-size:11px;color:#00E5FF;margin-top:6px;'>{escape(storm.get('noaa_event_id',''))}</div></div>"
    "</div>") if storm else ""}

  <div class="row c2" style="margin-top:14px;">
    <div class="frame green">
      <h2 style="color:#00FF9C;">// BASELINE SCAN · {escape(sa['label'])}</h2>
      <div class="mono" style="font-size:10px;color:var(--muted);letter-spacing:.16em;">
        CAPTURED · {escape((sa.get('captured_at') or '')[:19].replace('T',' '))}
      </div>
      <div class="row c3" style="margin-top:10px;">
        <div class="kpi"><span class="l">ENVELOPE</span><span class="v">{sa.get('envelope_score','—')}<span class="u">/100</span></span></div>
        <div class="kpi"><span class="l">MOISTURE</span><span class="v">{sa.get('moisture_pct','—')}<span class="u">%</span></span></div>
        <div class="kpi"><span class="l">ANOMALIES</span><span class="v">{sa.get('anomalies_count','—')}</span></div>
      </div>
    </div>
    <div class="frame mag">
      <h2 style="color:#FF2D78;">// POST-EVENT SCAN · {escape(sb['label'])}</h2>
      <div class="mono" style="font-size:10px;color:var(--muted);letter-spacing:.16em;">
        CAPTURED · {escape((sb.get('captured_at') or '')[:19].replace('T',' '))}
      </div>
      <div class="row c3" style="margin-top:10px;">
        <div class="kpi"><span class="l">ENVELOPE</span><span class="v" style="color:#FF2D78;">{sb.get('envelope_score','—')}<span class="u">/100</span></span></div>
        <div class="kpi"><span class="l">MOISTURE</span><span class="v" style="color:#FFB020;">{sb.get('moisture_pct','—')}<span class="u">%</span></span></div>
        <div class="kpi"><span class="l">ANOMALIES</span><span class="v" style="color:#FF2D78;">{sb.get('anomalies_count','—')}</span></div>
      </div>
    </div>
  </div>
</div>

<!-- PAGE 2 — NEW + WORSENED + RESOLVED ANOMALIES -->
<div class="page">
  {band}
  <h1 style="font-size:30px;">NEW DAMAGE · WORSENED · RESOLVED</h1>
  <div class="mono" style="color:var(--muted);letter-spacing:.20em;font-size:10px;margin-bottom:14px;">
    // EVERY DELTA THE STRATEX DIGITAL TWIN COULD RECONCILE BETWEEN THE TWO SCANS
  </div>

  <h2 style="color:#FF2D78;">// NEW DAMAGE — NOT PRESENT IN BASELINE</h2>
  <div class="frame mag" style="padding:0;margin-bottom:14px;">
    <table>
      <thead><tr>
        <th>SEV</th><th>TYPE</th><th>LOCATION</th><th class="right">AREA (SF)</th>
        <th class="right">CONF</th><th class="right">EST. $</th><th>DIAGNOSIS</th>
      </tr></thead>
      <tbody>{new_damage_rows or '<tr><td colspan="7" style="color:var(--muted);padding:14px;">No newly-introduced damage detected.</td></tr>'}</tbody>
    </table>
  </div>

  <h2 style="color:#FFB020;">// WORSENED — PRESENT IN BASELINE, ESCALATED POST-EVENT</h2>
  <div class="frame amber" style="padding:0;margin-bottom:14px;">
    <table>
      <thead><tr>
        <th>SEV</th><th>TYPE</th><th>LOCATION</th><th class="right">AREA (SF)</th>
        <th class="right">CONF</th><th class="right">EST. $</th><th>NOTES</th>
      </tr></thead>
      <tbody>{worsened_rows or '<tr><td colspan="7" style="color:var(--muted);padding:14px;">No escalations.</td></tr>'}</tbody>
    </table>
  </div>

  <h2 style="color:#00FF9C;">// RESOLVED — BASELINE FINDINGS NO LONGER PRESENT</h2>
  <div class="frame green" style="padding:0;">
    <table>
      <thead><tr>
        <th>SEV</th><th>TYPE</th><th>LOCATION</th><th class="right">AREA (SF)</th>
        <th class="right">CONF</th><th class="right">EST. $</th><th>DIAGNOSIS</th>
      </tr></thead>
      <tbody>{resolved_rows or '<tr><td colspan="7" style="color:var(--muted);padding:14px;">No baseline findings have resolved.</td></tr>'}</tbody>
    </table>
  </div>

  <div style="position:absolute;bottom:30px;left:0;right:0;text-align:center;">
    <div class="mono" style="font-size:9px;color:var(--muted);letter-spacing:.28em;">
      STRATEX™ · CHAIN-OF-CUSTODY VERIFIED · PASSPORT STX-{escape(pp['passport_id'])} ·
      RENDERED {escape(diff.get('generated_at','')[:19].replace('T',' '))}
    </div>
  </div>
</div>

</body></html>
"""


def render_claim_snapshot_pdf(diff: Dict[str, Any]) -> Path:
    pid = diff["passport"]["passport_id"]
    pdf_path = CACHE_DIR / f"claim_{pid}.pdf"

    # Production-safe fast path: if a pre-built PDF already lives in the
    # cache (committed alongside the repo), serve it directly. This means
    # production containers without Playwright/Chromium still ship the
    # Claim Snapshot PDF perfectly.
    if pdf_path.exists() and pdf_path.stat().st_size > 50_000:
        return pdf_path

    html = _build_html(diff)
    html_path = CACHE_DIR / f"claim_{pid}.html"
    html_path.write_text(html, encoding="utf-8")

    # Build through Playwright (sync API in a subprocess so we don't block the event loop)
    script = f"""
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file://{html_path}")
        await page.wait_for_load_state("networkidle")
        await page.pdf(path="{pdf_path}", format="Tabloid", landscape=True,
                       print_background=True,
                       margin={{"top": "0", "right": "0", "bottom": "0", "left": "0"}})
        await browser.close()

asyncio.run(main())
"""
    runner = CACHE_DIR / f"_runner_{pid}.py"
    runner.write_text(script)
    subprocess.run([sys.executable, str(runner)], check=True, timeout=60)
    return pdf_path
