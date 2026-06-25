
import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto("file:///app/stratex_pitch/_claim_cache/claim_877D9E3C8FC3.html")
        await page.wait_for_load_state("networkidle")
        await page.pdf(path="/app/stratex_pitch/_claim_cache/claim_877D9E3C8FC3.pdf", format="Tabloid", landscape=True,
                       print_background=True,
                       margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        await browser.close()

asyncio.run(main())
