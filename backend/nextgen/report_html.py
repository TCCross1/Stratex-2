"""
Minimal HTML renderer for Property Intelligence Reports
Suitable for print / later PDF. Homeowner-safe mode strips contractor costs.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional


def _score_cell(label: str, score_obj: Any) -> str:
    if isinstance(score_obj, dict):
        val = score_obj.get("value")
        truth = score_obj.get("truth", "UNKNOWN")
    else:
        val, truth = score_obj, "UNKNOWN"
    display = escape(str(val) if val is not None else "—")
    return f"<div class='score'><span class='label'>{escape(label)}</span><span class='value'>{display}</span><span class='truth'>{escape(str(truth))}</span></div>"


def render_report_html(report: Dict[str, Any], *, homeowner_safe: bool = False) -> str:
    sections = report.get("sections") or {}
    exec_sum = sections.get("01_executive_summary") or {}
    scores = exec_sum.get("scores") or {}
    findings = sections.get("17_found_damages") or []
    materials = sections.get("15_materials_list") or []
    priority = sections.get("18_maintenance_priority_list") or []
    labor = sections.get("16_labor_report") or {}

    if homeowner_safe:
        # Strip cost-bearing fields
        materials = [
            {k: v for k, v in m.items() if k not in ("unit_cost", "total_cost")}
            if isinstance(m, dict) else m
            for m in materials
        ]
        labor = {k: v for k, v in labor.items() if "cost" not in k.lower()} if isinstance(labor, dict) else labor

    finding_rows = ""
    for f in findings:
        if not isinstance(f, dict):
            continue
        finding_rows += (
            f"<tr><td>{escape(str(f.get('severity','')))}</td>"
            f"<td>{escape(str(f.get('description','')))}</td>"
            f"<td>{escape(str(f.get('location','')))}</td>"
            f"<td>{escape(str(f.get('truth_classification', f.get('truth',''))))}</td></tr>"
        )

    mat_rows = ""
    for m in materials:
        if not isinstance(m, dict):
            continue
        mat_rows += (
            f"<tr><td>{escape(str(m.get('item','')))}</td>"
            f"<td>{escape(str(m.get('qty','')))}</td>"
            f"<td>{escape(str(m.get('unit','')))}</td>"
            f"<td>{escape(str(m.get('truth','')))}</td></tr>"
        )

    priority_lis = "".join(
        f"<li><strong>{escape(str(p.get('severity','')))}</strong> — {escape(str(p.get('description','')))}</li>"
        for p in priority if isinstance(p, dict)
    )

    title = "Property Report" if homeowner_safe else "Property Intelligence Report (Contractor)"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>{escape(str(report.get('report_id', title)))}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #111; background: #fafafa; }}
  h1 {{ font-size: 1.5rem; }}
  .meta {{ color: #555; margin-bottom: 1.5rem; }}
  .scores {{ display: flex; flex-wrap: wrap; gap: 1rem; margin: 1rem 0; }}
  .score {{ background: #fff; border: 1px solid #ddd; padding: 0.75rem 1rem; border-radius: 8px; min-width: 120px; }}
  .score .label {{ display: block; font-size: 0.75rem; color: #666; }}
  .score .value {{ font-size: 1.25rem; font-weight: 600; }}
  .score .truth {{ display: block; font-size: 0.7rem; color: #888; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; background: #fff; }}
  th, td {{ border: 1px solid #ddd; padding: 0.5rem; text-align: left; font-size: 0.9rem; }}
  th {{ background: #f0f0f0; }}
  .note {{ font-size: 0.8rem; color: #666; margin-top: 2rem; }}
</style>
</head>
<body>
  <h1>STRATEX — {escape(title)}</h1>
  <div class="meta">
    Report ID: {escape(str(report.get('report_id','')))}<br/>
    Property: {escape(str(report.get('property_id','')))}<br/>
    Generated: {escape(str(report.get('generated_at','')))}
  </div>
  <h2>Executive Scores</h2>
  <div class="scores">
    {_score_cell('Property', scores.get('property_score'))}
    {_score_cell('Roof', scores.get('roof_condition'))}
    {_score_cell('Energy', scores.get('energy_score'))}
    {_score_cell('Moisture', scores.get('moisture_score'))}
    {_score_cell('AWE Index', scores.get('awe_index'))}
  </div>
  <h2>Findings</h2>
  <table>
    <thead><tr><th>Severity</th><th>Description</th><th>Location</th><th>Truth</th></tr></thead>
    <tbody>{finding_rows or '<tr><td colspan="4">None</td></tr>'}</tbody>
  </table>
  <h2>Maintenance Priority</h2>
  <ol>{priority_lis or '<li>None listed</li>'}</ol>
  <h2>Materials</h2>
  <table>
    <thead><tr><th>Item</th><th>Qty</th><th>Unit</th><th>Truth</th></tr></thead>
    <tbody>{mat_rows or '<tr><td colspan="4">None</td></tr>'}</tbody>
  </table>
  <p class="note">
    Truth classifications: VERIFIED / ESTIMATED / PROJECTED / UNKNOWN / WITHHELD.
    Subsurface layers are never claimed as verified from exterior imagery alone.
    Authority: sealed mission package + Passport projections. Habitat is read-only.
  </p>
</body>
</html>"""
