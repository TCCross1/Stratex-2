"""Directive 003 → professional PDF builder.

Renders NEXTGEN_SEQUENCE_DIAGRAMS_v1.0.md and NEXTGEN_CANONICAL_DATA_MODEL_v1.0.md
into two enterprise-grade PDFs matching the existing Blueprint v1.2 styling.
Preview-only. Playwright is already installed in the preview container.
Does not touch production.
"""
from __future__ import annotations

import asyncio
import re
from pathlib import Path

MEMORY = Path("/app/memory")
OUT_DIR = MEMORY / "_blueprint_out"
OUT_DIR.mkdir(exist_ok=True)

DOCS = [
    {
        "src": MEMORY / "NEXTGEN_SEQUENCE_DIAGRAMS_v1.0.md",
        "html": OUT_DIR / "sequence_diagrams_v1.0.html",
        "pdf": OUT_DIR / "STRATEX_NextGen_Sequence_Diagrams_v1.0.pdf",
        "cover_title": "NextGen<br/>Sequence<br/><span class='accent'>Diagrams</span>",
        "cover_subtitle": "24-diagram operational pack aligned to Blueprint v1.2. "
                          "Documentation only. No implementation authorized.",
        "header_right": "NextGen Sequence Diagrams v1.0",
        "status_pill": "STATUS · DRAFT v1.0 · AWAITING EXECUTIVE REVIEW",
    },
    {
        "src": MEMORY / "NEXTGEN_CANONICAL_DATA_MODEL_v1.0.md",
        "html": OUT_DIR / "canonical_data_model_v1.0.html",
        "pdf": OUT_DIR / "STRATEX_NextGen_Canonical_Data_Model_v1.0.pdf",
        "cover_title": "NextGen<br/>Canonical<br/><span class='accent'>Data Model</span>",
        "cover_subtitle": "Ten logical domains · entities · fields · invariants · "
                          "traceability. Logical specification only. No migrations.",
        "header_right": "NextGen Canonical Data Model v1.0",
        "status_pill": "STATUS · DRAFT v1.0 · AWAITING EXECUTIVE REVIEW",
    },
]


def _inline(s: str) -> str:
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    s = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"\*(.+?)\*", r"<em>\1</em>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def _table(block: str) -> str:
    rows = [r for r in block.strip().split("\n") if r.strip()]
    if len(rows) < 2 or not rows[1].strip().startswith("|"):
        return f"<pre>{block}</pre>"
    header = [c.strip() for c in rows[0].strip().strip("|").split("|")]
    body = []
    for r in rows[2:]:
        cells = [c.strip() for c in r.strip().strip("|").split("|")]
        body.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
    return (
        "<table><thead><tr>"
        + "".join(f"<th>{_inline(c)}</th>" for c in header)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table>"
    )


def md_to_html(md: str) -> str:
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        line = lines[i]
        # Fenced code block (renders mermaid as a code block; readable without a renderer)
        if line.strip().startswith("```"):
            fence = line.strip()
            lang = fence[3:].strip()
            j = i + 1
            code = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                code.append(lines[j])
                j += 1
            escaped = ("\n".join(code)
                       .replace("&", "&amp;")
                       .replace("<", "&lt;")
                       .replace(">", "&gt;"))
            cls = " class='mermaid-block'" if lang.lower() in {"mermaid"} else ""
            out.append(f"<pre{cls}><code>{escaped}</code></pre>")
            i = j + 1
            continue
        if line.strip().startswith("|") and i + 1 < len(lines) and lines[i + 1].strip().startswith("|"):
            j = i
            block = []
            while j < len(lines) and lines[j].strip().startswith("|"):
                block.append(lines[j])
                j += 1
            out.append(_table("\n".join(block)))
            i = j
            continue
        if line.startswith("# "):
            out.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("#### "):
            out.append(f"<h4>{_inline(line[5:])}</h4>")
        elif line.strip() == "---":
            out.append("<hr/>")
        elif line.strip().startswith("> "):
            out.append(f"<blockquote>{_inline(line.strip()[2:])}</blockquote>")
        elif line.strip().startswith("- ") or line.strip().startswith("* "):
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
            out.append(f"<p>{_inline(line)}</p>")
        i += 1
    return "\n".join(out)


def build_toc(md: str) -> str:
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


def _style(header_right: str) -> str:
    return f"""
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
      content: "{header_right}";
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
  blockquote {{
    border-left: 3px solid #7EE9FF; margin: 3mm 0; padding: 2mm 4mm;
    background: #F5F8FB; color: #223140; font-size: 10pt;
  }}
  table {{
    width: 100%; border-collapse: collapse; margin: 3mm 0 5mm 0;
    font-size: 8.5pt; page-break-inside: avoid;
    table-layout: fixed; word-wrap: break-word;
  }}
  thead th {{
    background: #0F1620; color: #E9F4FF; text-align: left;
    padding: 5px 6px; letter-spacing: 0.08em; font-size: 7.5pt;
    text-transform: uppercase;
  }}
  tbody td {{
    border-bottom: 1px solid #D8DEE5; padding: 4px 6px; vertical-align: top;
    word-break: break-word;
  }}
  tbody tr:nth-child(even) td {{ background: #F5F8FB; }}
  code {{
    background: #0F1620; color: #7EE9FF; padding: 1px 4px; border-radius: 3px;
    font-family: 'Courier New', monospace; font-size: 8.5pt;
  }}
  pre {{
    background: #0F1620; color: #E9F4FF; padding: 8px 10px; border-radius: 4px;
    overflow-x: auto; font-family: 'Courier New', monospace; font-size: 8pt;
    line-height: 1.35; page-break-inside: avoid; white-space: pre-wrap;
  }}
  pre.mermaid-block {{
    background: #050B16; color: #7EE9FF; border: 1px solid #1E2A38;
  }}
  pre code {{ background: transparent; color: inherit; padding: 0; }}
  hr {{ border: 0; border-top: 1px solid #C4CFD9; margin: 8mm 0; }}
  strong {{ color: #0F1620; }}
  em {{ color: #223140; }}
</style>
"""


def build_html(doc: dict) -> str:
    md = doc["src"].read_text()
    body_html = md_to_html(md)
    toc_html = build_toc(md)
    today = "February 26, 2026"
    style = _style(doc["header_right"])
    html = f"""
<!doctype html>
<html><head><meta charset="utf-8"/>
<title>{doc['header_right']}</title>
{style}
</head>
<body>

<section class="cover">
  <div class="cover-top">
    <div class="kicker">// CROSS AI SOFTWARES INC. · EXECUTIVE DOCUMENTATION</div>
    <h1>{doc['cover_title']}</h1>
    <div class="subtitle">{doc['cover_subtitle']}</div>
    <div class="status-pill">{doc['status_pill']}</div>
    <div class="meta">
      VERSION 1.0 · CREATED {today} · CONFIDENTIAL — PROPRIETARY
    </div>
  </div>
  <div class="cover-bottom">
    <div class="band">
      <span>STRATEX™ · A CROSS AI SOFTWARES INC. PRODUCT</span>
      <span>PREPARED BY TC · AI PRODUCT MANAGER</span>
    </div>
  </div>
</section>

<section class="toc-page">
  <h1>Table of Contents</h1>
  {toc_html}
</section>

<section class="body">
  {body_html}
</section>

</body></html>"""
    doc["html"].write_text(html, encoding="utf-8")
    return html


async def render_pdf(doc: dict):
    from playwright.async_api import async_playwright
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(f"file://{doc['html']}", wait_until="networkidle")
        await page.pdf(
            path=str(doc["pdf"]),
            format="Letter",
            print_background=True,
            display_header_footer=False,
            margin={"top": "0", "bottom": "0", "left": "0", "right": "0"},
        )
        await browser.close()


async def main():
    for doc in DOCS:
        print(f"Building HTML for {doc['src'].name} …")
        build_html(doc)
        print(f"  HTML: {doc['html']} ({doc['html'].stat().st_size} bytes)")
        print(f"Rendering PDF …")
        await render_pdf(doc)
        print(f"  PDF: {doc['pdf']} ({doc['pdf'].stat().st_size:,} bytes)")


if __name__ == "__main__":
    asyncio.run(main())
