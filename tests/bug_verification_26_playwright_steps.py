"""
Focused Playwright steps for bug verification iteration 26.

This file mirrors the script executed through mcp_browser_automation against:
https://stratex-quant.preview.emergentagent.com/
"""

async def run(page):
    import time

    base = "https://stratex-quant.preview.emergentagent.com"

    def log(msg):
        print(f"[iter26] {msg}")

    async def expect_visible(selector, label, timeout=15000):
        loc = page.locator(selector).first
        await loc.wait_for(state="visible", timeout=timeout)
        box = await loc.bounding_box()
        assert box and box["width"] > 0 and box["height"] > 0, f"{label} has no visible box"
        log(f"PASS visible: {label} ({selector}) box={box}")
        return loc, box

    await page.set_viewport_size({"width": 1920, "height": 1080})

    # Public root: clear auth and verify new STRATEX CORE entry point is visible.
    await page.goto(f"{base}/?_ts={int(time.time())}", wait_until="domcontentloaded")
    await page.evaluate("localStorage.clear()")
    await page.goto(f"{base}/?_ts={int(time.time())}", wait_until="networkidle")
    await expect_visible('[data-testid="logo-splash"]', "Logo splash shell")
    await expect_visible('[data-testid="splash-stratex-core-logo"]', "STRATEX CORE hero logo")
    cta, cta_box = await expect_visible('[data-testid="splash-enter-core-cta"]', "Enter Stratex Core CTA")
    cta_text = (await cta.inner_text()).strip().upper()
    assert "ENTER STRATEX CORE" in cta_text, f"CTA text mismatch: {cta_text}"

    svg_info = await page.evaluate("""async () => {
      const r = await fetch('/brand/stratex-core-full.svg', { cache: 'no-store' });
      const txt = await r.text();
      return {
        ok: r.ok,
        status: r.status,
        hasTagline: txt.includes('ONE PROPERTY.') && txt.includes('ONE RECORD.') && txt.includes('LIFETIME INTELLIGENCE.'),
        hasCore: txt.includes('CORE'),
        hasOrangeX: txt.includes('fill="#FF7B00"') || txt.includes('stop-color="#FF7B00"'),
        hasHexagon: txt.includes('<polygon')
      };
    }""")
    assert svg_info["ok"] and svg_info["hasTagline"] and svg_info["hasCore"] and svg_info["hasOrangeX"] and svg_info["hasHexagon"], f"Brand SVG did not include required pieces: {svg_info}"
    log(f"PASS brand svg content: {svg_info}")

    banner, banner_box = await expect_visible('[data-testid="cross-ai-logo"]', "Subordinate CROSS AI banner")
    banner_style = await banner.evaluate("""el => {
      const cs = getComputedStyle(el);
      return { opacity: cs.opacity, maxHeight: cs.maxHeight, height: el.getBoundingClientRect().height };
    }""")
    assert float(banner_style["opacity"]) <= 0.71, f"Cross AI opacity not subordinate: {banner_style}"
    assert banner_style["maxHeight"] == "56px", f"Cross AI max-height not 56px: {banner_style}"
    assert banner_style["height"] <= 58, f"Cross AI rendered height too large: {banner_style}"
    assert banner_box["height"] < cta_box["height"] * 1.25, "Cross AI banner visually dominates CTA area"
    log(f"PASS Cross AI subordinate style: {banner_style}")

    # Legacy access regression: Info Hub still opens inline.
    await page.locator('[data-testid="splash-info-cta"]').click()
    await expect_visible('[data-testid="window-info"]', "Legacy Info Hub window")
    info_text = await page.locator('[data-testid="window-info"]').inner_text()
    assert "Recon Stack" in info_text or "STRATEX" in info_text, "Info Hub did not render legacy content"
    log("PASS legacy Info Hub opens from splash-info-cta")

    # Authenticate as CEO through the real UI.
    await page.goto(f"{base}/ceo/login", wait_until="networkidle")
    await expect_visible('[data-testid="ceo-login-form"]', "CEO login form")
    await page.locator('[data-testid="ceo-email"]').fill("Tony@Stratexdrone.com")
    await page.locator('[data-testid="ceo-password"]').fill("1111")
    await page.locator('[data-testid="ceo-submit"]').click()
    await page.wait_for_url("**/ceo/command", timeout=20000)
    token_present = await page.evaluate("!!localStorage.getItem('stratex_token')")
    assert token_present, "CEO login did not persist stratex_token"
    log("PASS CEO login succeeded and token persisted")

    # Authenticated root CTA should navigate to /nextgen and load the new command interface.
    await page.goto(f"{base}/?_ts={int(time.time())}", wait_until="networkidle")
    await expect_visible('[data-testid="splash-enter-core-cta"]', "Authenticated root Enter CTA")
    await page.locator('[data-testid="splash-enter-core-cta"]').click()
    await page.wait_for_url("**/nextgen", timeout=20000)
    await expect_visible('[data-testid="nextgen-shell"]', "NextGen shell after CTA")
    await expect_visible('[data-testid="nx-rail-brand"]', "STRATEX CORE left rail brand")
    await expect_visible('[data-testid="nx-hero"]', "NextGen Home hero")
    await expect_visible('[data-testid="nx-status-strip"]', "5-chip operational status strip")
    for chip in ["status-system", "status-tenant", "status-env", "status-phase", "status-sync"]:
        await expect_visible(f'[data-testid="{chip}"]', f"status chip {chip}")
    await expect_visible('[data-testid^="nx-primary-"]', "NextGen primary CTA card")
    await expect_visible('[data-testid="nx-awe-hero"]', "AWE composite band")
    log("PASS Enter CTA loads complete NextGen command interface")

    # App launcher STRATEX tile at top routes to /nextgen while authenticated.
    await page.goto(f"{base}/?_ts={int(time.time())}", wait_until="networkidle")
    tile, tile_box = await expect_visible('[data-testid="app-icon-core"]', "STRATEX Core app launcher tile")
    rail_icons = await page.evaluate("""() => Array.from(document.querySelectorAll('[data-testid^="app-icon-"]')).map((el, idx) => ({idx, testid: el.getAttribute('data-testid'), y: el.getBoundingClientRect().y}))""")
    assert rail_icons and rail_icons[0]["testid"] == "app-icon-core", f"STRATEX tile is not first app icon: {rail_icons[:3]}"
    await tile.click()
    await page.wait_for_url("**/nextgen", timeout=20000)
    await expect_visible('[data-testid="nextgen-shell"]', "NextGen shell after rail tile")
    log("PASS app-icon-core is first rail tile and routes to /nextgen")

    error_text = await page.evaluate("""() => {
    const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
    return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")

    print("ITER26_RESULT: PASS")