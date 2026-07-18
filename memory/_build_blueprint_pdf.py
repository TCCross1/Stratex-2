"""Blueprint → professional PDF builder.

Reads the two blueprint markdown files and renders them into a single
enterprise-grade PDF with a cover page, table of contents, page numbers,
and a revision-history page.

Preview-only. Uses Playwright which is already installed in the preview
container. Does not touch production.
"""
from __future__ import annotations

import asyncio
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MEMORY = Path("/app/memory")
BLUEPRINT_MD = MEMORY / "NEXTGEN_ARCHITECTURE_BLUEPRINT_v1.2.md"
REDLINE_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REDLINE_v1.1_to_v1.2.md"
ADRs_MD = MEMORY / "NEXTGEN_ARCHITECTURE_ADRs_v1.1.md"
SUMMARY_MD = MEMORY / "NEXTGEN_EXECUTIVE_SUMMARY_v1.1.md"
APPENDIX_MD = MEMORY / "NEXTGEN_ARCHITECTURE_REVIEW_APPENDIX.md"

OUT_DIR = MEMORY / "_blueprint_out"
OUT_DIR.mkdir(exist_ok=True)
OUT_HTML = OUT_DIR / "blueprint_v1.2.html"
OUT_PDF = OUT_DIR / "STRATEX_NextGen_Architecture_Blueprint_v1.2.pdf"


def md_to_html(md: str) -> str:
    """Minimal markdown → HTML converter tuned for our documents.
    We deliberately do NOT pull in an external MD lib to keep this
    zero-dependency and reproducible on any container."""

    def _table(block: str) -> str:
        rows = [r for r in block.strip().split("\n") if r.strip()]
        if len(rows) < 2 or not rows[1].strip().startswith("|"):
            return f"<pre>{block}</pre>"
        header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
        body = []
        for r in rows[2:]:
            cells = [c.strip() for c in r.strip().strip("|").split("|")]
            body.append("<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>")
        return (
            "<table><thead><tr>"
            + "".join(f"<th>{c}</th>" for c in header)
            + "</tr></thead><tbody>"
            + "".join(body)
            + "</tbody></table>"
        )

    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        # Fenced code block
        if line.strip().startswith("```"):
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code.append(lines[j])
                j += 1
            out.append("<pre><code>" + "\n".join(code)
                       .replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                       + "</code></pre>")
            i = j + 1
            continue
        # Table block (starts with | ... | on two consecutive lines)
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            j = i
            block = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            out.append(_table("\n".join(block)))
            i = j
            continue
        # Headings
        if line.startswith("# "):
            out.append(f'<h1>{_inline(line[2:])}</h1>')
        elif line.startswith("## "):
            out.append(f'<h2>{_inline(line[3:])}</h2>')
        elif line.startswith("### "):
            out.append(f'<h3>{_inline(line[4:])}</h3>')
        elif line.startswith("#### "):
            out.append(f'<h4>{_inline(line[5:])}</h4>')
        elif line.strip() == "---":
            out.append('<hr/>')
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
            # collect a full list
            j = i
            items = []
            while j < len(lines) and (lines[j].strip().startswith("- ") or lines[j].strip().startswith("* ")):
                items.append(lines[j].strip()[2:])
                j += 1
            out.append("<ul>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ul>")
            i = j
            continue
        elif re.match(r"^\d+\.\s", line):
            j = i
            items = []
            while j < len(lines) and re.match(r"^\d+\.\s", lines[j]):
                items.append(re.sub(r"^\d+\.\s", "", lines[j]))
                j += 1
            out.append("<ol>" + "".join(f"<li>{_inline(x)}</li>" for x in items) + "</ol>")
            i = j
            continue
        elif line.strip() == "":
            out.append("")
        else:
            out.append(f'<p>{_inline(line)}</p>')
        i += 1
    return "\n".join(out)


def _inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def build_toc(md: str) -> str:
    """Extract H1/H2/H3 anchors for a TOC."""
    entries = []
    for line in md.split("\n"):
        m = re.match(r"^(#{1,3})\s+(.*)", line)
        if not m:
            continue
        depth = len(m.group(1))
        title = m.group(2).strip()
        entries.append((depth, title))
    lis = []
    for d, t in entries:
        cls = f"toc-l{d}"
        lis.append(f'<li class="{cls}">{_inline(t)}</li>')
    return "<ul class='toc'>" + "".join(lis) + "</ul>"


def build_html():
    blueprint_md = BLUEPRINT_MD.read_text()
    appendix_md = APPENDIX_MD.read_text()
    redline_md = REDLINE_MD.read_text()
    adrs_md = ADRs_MD.read_text()
    summary_md = SUMMARY_MD.read_text()
    combined_md = (
        summary_md + "\n\n---\n\n"
        + blueprint_md + "\n\n---\n\n"
        + redline_md + "\n\n---\n\n"
        + adrs_md + "\n\n---\n\n"
        + "# ORIGINAL v1.0 REVIEW APPENDIX (Q1-Q14)\n"
        + "*Preserved verbatim for reference. Answers superseded where v1.1 §§10–17 address them.*\n\n"
        + appendix_md
    )

    body_html = md_to_html(combined_md)
    toc_html = build_toc(combined_md)

    today = "February 26, 2026"  # explicit per v1.1 correction §16

    html = f"""
<!doctype html>
<html><head><meta charset="utf-8"/>
<title>STRATEX Core NextGen Architecture Blueprint v1.2</title>
<style>
  @page {{
    size: Letter;
    margin: 22mm 18mm 22mm 18mm;
    @top-left {{
      content: "STRATEX™ · CROSS AI SOFTWARES INC. · CONFIDENTIAL — PROPRIETARY";
      font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 8pt;
      color: #667; letter-spacing: 0.14em;
    }}
    @top-right {{
      content: "NextGen Architecture Blueprint v1.2";
      font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 8pt;
      color: #667; letter-spacing: 0.10em;
    }}
    @bottom-center {{
      content: "Page " counter(page) " of " counter(pages);
      font-family: 'Helvetica Neue', Arial, sans-serif; font-size: 8pt;
      color: #667;
    }}
  }}
  @page :first {{
    margin: 0;
    @top-left {{ content: ""; }}
    @top-right {{ content: ""; }}
    @bottom-center {{ content: ""; }}
  }}
  html, body {{
    color: #0F1620; background: #FFFFFF;
    font-family: 'Helvetica Neue', 'Segoe UI', Arial, sans-serif;
    font-size: 10.5pt; line-height: 1.55;
    -webkit-font-smoothing: antialiased;
  }}
  .cover {{
    page-break-after: always;
    padding: 0; margin: 0;
    background: linear-gradient(180deg, #02060B 0%, #050B16 60%, #061826 100%);
    color: #EAF2FB;
    min-height: 100vh; height: 100vh;
    display: flex; flex-direction: column; justify-content: space-between;
    padding: 55mm 22mm 22mm 22mm; box-sizing: border-box;
    position: relative; overflow: hidden;
  }}
  .cover::before {{
    content: ""; position: absolute; inset: 0;
    background:
      radial-gradient(ellipse at 20% 0%, rgba(0,229,255,0.18) 0%, transparent 55%),
      radial-gradient(ellipse at 80% 100%, rgba(212,184,106,0.14) 0%, transparent 55%);
    pointer-events: none;
  }}
  .cover-top {{ position: relative; z-index: 1; }}
  .cover-bottom {{ position: relative; z-index: 1; }}
  .cover .kicker {{
    font-family: 'Courier New', monospace;
    letter-spacing: 0.32em; font-size: 9pt; text-transform: uppercase;
    color: #7EE9FF;
  }}
  .cover h1 {{
    font-size: 46pt; line-height: 1.02; letter-spacing: -0.01em;
    margin: 10mm 0 4mm 0; color: #FFFFFF; font-weight: 700;
  }}
  .cover .accent {{ color: #FFB020; text-shadow: 0 0 24px rgba(255,176,32,0.35); }}
  .cover .subtitle {{
    font-size: 14pt; line-height: 1.4;
    color: #C5D4E0; margin-top: 4mm; max-width: 140mm;
  }}
  .cover .meta {{
    font-family: 'Courier New', monospace;
    letter-spacing: 0.16em; font-size: 9pt;
    color: #7EE9FF; margin-top: 6mm;
  }}
  .cover .status-pill {{
    display: inline-block; padding: 4px 12px; border-radius: 999px;
    border: 1px solid rgba(255,176,32,0.6); color: #FFB020;
    font-family: 'Courier New', monospace; font-size: 8.5pt;
    letter-spacing: 0.22em; text-transform: uppercase; margin-top: 12mm;
  }}
  .cover .band {{
    border-top: 1px solid rgba(255,255,255,0.14);
    padding-top: 6mm; display: flex; justify-content: space-between;
    font-family: 'Courier New', monospace; font-size: 8.5pt;
    letter-spacing: 0.22em; text-transform: uppercase; color: #98A6B4;
  }}
  .toc-page {{ page-break-before: always; page-break-after: always; }}
  .toc-page h1 {{
    font-size: 22pt; letter-spacing: -0.005em; margin-bottom: 6mm;
    border-bottom: 2px solid #0F1620; padding-bottom: 3mm;
  }}
  ul.toc {{ list-style: none; padding-left: 0; margin: 4mm 0; }}
  ul.toc li {{ margin: 1.5mm 0; }}
  ul.toc li.toc-l1 {{ font-weight: 700; font-size: 11pt; margin-top: 3mm; }}
  ul.toc li.toc-l2 {{ padding-left: 8mm; font-size: 10pt; color: #333; }}
  ul.toc li.toc-l3 {{ padding-left: 16mm; font-size: 9.5pt; color: #555; }}

  h1 {{ font-size: 20pt; margin: 8mm 0 3mm 0; page-break-after: avoid; color: #0F1620; }}
  h2 {{ font-size: 14pt; margin: 6mm 0 2.5mm 0; page-break-after: avoid;
        border-bottom: 1px solid #C4CFD9; padding-bottom: 2mm; color: #0F1620; }}
  h3 {{ font-size: 12pt; margin: 5mm 0 2mm 0; page-break-after: avoid; color: #223140; }}
  h4 {{ font-size: 11pt; margin: 4mm 0 1.5mm 0; page-break-after: avoid; color: #223140; }}
  p {{ margin: 0 0 3mm 0; }}
  ul, ol {{ margin: 0 0 4mm 6mm; }}
  li {{ margin: 1mm 0; }}
  table {{
    width: 100%; border-collapse: collapse; margin: 3mm 0 5mm 0;
    font-size: 9pt; page-break-inside: avoid;
  }}
  thead th {{
    background: #0F1620; color: #E9F4FF; text-align: left;
    padding: 6px 8px; letter-spacing: 0.08em; font-size: 8.5pt;
    text-transform: uppercase;
  }}
  tbody td {{
    border-bottom: 1px solid #D8DEE5; padding: 5px 8px; vertical-align: top;
  }}
  tbody tr:nth-child(even) td {{ background: #F5F8FB; }}
  code {{
    background: #0F1620; color: #7EE9FF; padding: 1px 4px; border-radius: 3px;
    font-family: 'Courier New', monospace; font-size: 9pt;
  }}
  pre {{
    background: #0F1620; color: #E9F4FF; padding: 8px 10px; border-radius: 4px;
    overflow-x: auto; font-family: 'Courier New', monospace; font-size: 8.5pt;
    line-height: 1.35; page-break-inside: avoid;
  }}
  pre code {{ background: transparent; color: inherit; padding: 0; }}
  hr {{ border: 0; border-top: 1px solid #C4CFD9; margin: 8mm 0; }}
  strong {{ color: #0F1620; }}
  em {{ color: #223140; }}
</style></head>
<body>

<!-- COVER -->
<section class="cover">
  <div class="cover-top">
    <div class="kicker">// CROSS AI SOFTWARES INC. · EXECUTIVE ARCHITECTURE</div>
    <h1>NextGen<br/>Architecture<br/><span class="accent">Blueprint</span></h1>
    <div class="subtitle">
      Residential Property Intelligence Operating System —
      Stratex Core · Stratex Passport · Stratex Habitat.
      Version 1.1 executive review package incorporating 20 v1.1 corrections + 10 v1.2 consistency corrections.
    </div>
    <div class="status-pill">STATUS · REVISED v1.2 · AWAITING EXECUTIVE APPROVAL</div>
    <div class="meta">
      VERSION 1.2 · REVISED {today} · CONFIDENTIAL — PROPRIETARY
    </div>
  </div>
  <div class="cover-bottom">
    <div class="band">
      <span>STRATEX™ · A CROSS AI SOFTWARES INC. PRODUCT</span>
      <span>PREPARED BY TC · AI PRODUCT MANAGER</span>
    </div>
  </div>
</section>

<!-- TABLE OF CONTENTS -->
<section class="toc-page">
  <h1>Table of Contents</h1>
  {toc_html}
</section>

<!-- MAIN BODY -->
<section class="body">
  {body_html}
</section>

</body></html>"""
    OUT_HTML.write_text(html, encoding="utf-8")
    return html


async def _render():
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{OUT_HTML}", wait_until="networkidle")
        await page.pdf(
            path=str(OUT_PDF),
            format="Letter",
            print_background=True,
            display_header_footer=False,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()


if __name__ == "__main__":
    print("Building HTML …")
    build_html()
    print(f"HTML: {OUT_HTML} ({OUT_HTML.stat().st_size} bytes)")
    print("Rendering PDF via Playwright …")
    asyncio.run(_render())
    print(f"PDF: {OUT_PDF} ({OUT_PDF.stat().st_size:,} bytes)")
