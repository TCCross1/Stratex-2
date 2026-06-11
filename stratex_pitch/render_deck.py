"""STRATEX™ pitch deck PDF generator.

Renders /app/stratex_pitch/deck.html into a landscape 17×11 PDF using the
same Playwright Chromium pipeline that powers contractor deliverables.

Run:
    python3 /app/stratex_pitch/render_deck.py
"""
import asyncio
import os
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
HTML = ROOT / "deck.html"
OUT  = ROOT / "STRATEX_Piercy_Briefing.pdf"


async def main():
    from playwright.async_api import async_playwright

    if not HTML.exists():
        raise SystemExit(f"deck.html missing at {HTML}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )
        ctx = await browser.new_context(viewport={"width": 1632, "height": 1056})
        page = await ctx.new_page()
        await page.goto(f"file://{HTML}", wait_until="networkidle", timeout=60_000)
        # Wait for embedded fonts to settle
        await page.wait_for_timeout(2_500)
        await page.pdf(
            path=str(OUT),
            width="17in",
            height="11in",
            print_background=True,
            prefer_css_page_size=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )
        await browser.close()
        size_mb = os.path.getsize(OUT) / 1_048_576
        print(f"✓ PDF generated: {OUT} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    asyncio.run(main())
