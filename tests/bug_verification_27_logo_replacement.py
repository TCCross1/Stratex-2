"""
Focused Playwright checks for bug verification iteration 27.

Target bug: approved STRATEX CORE logo must replace legacy/screenshot/hand-drawn
logo in root launcher and /nextgen brand locations.

This file documents the browser checks executed through the testing browser tool.
"""

PREVIEW_URL = "https://stratex-quant.preview.emergentagent.com/"


async def run(page):
    console_errors = []
    failed_logo_responses = []

    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("response", lambda resp: failed_logo_responses.append(f"{resp.status} {resp.url}") if "/brand/stratex-core-logo.png" in resp.url and resp.status >= 400 else None)

    await page.set_viewport_size({"width": 1920, "height": 1080})
    await page.goto(PREVIEW_URL, wait_until="networkidle")

    async def img_info(selector):
        loc = page.locator(selector).first()
        await loc.wait_for(state="visible", timeout=15000)
        box = await loc.bounding_box()
        info = await loc.evaluate("""(img) => ({
            src: img.currentSrc || img.src,
            naturalWidth: img.naturalWidth,
            naturalHeight: img.naturalHeight,
            complete: img.complete,
            alt: img.alt,
            className: img.className,
            boxShadow: getComputedStyle(img).boxShadow,
            backgroundColor: getComputedStyle(img).backgroundColor
        })""")
        return {**info, "box": box}

    root_checks = {
        "nav": await img_info('[data-testid="nav-home-logo"] img'),
        "rail": await img_info('[data-testid="rail-home"] img'),
        "splash": await img_info('[data-testid="splash-stratex-core-logo"]'),
    }
    cta = page.locator('[data-testid="splash-enter-core-cta"]').first()
    await cta.wait_for(state="visible", timeout=10000)
    print("ROOT_LOGOS", root_checks)
    print("CTA_TEXT", await cta.inner_text())

    await cta.click()
    await page.wait_for_timeout(1200)
    print("CTA_FINAL_URL", page.url)

    await page.goto(PREVIEW_URL + "ceo/login", wait_until="networkidle")
    await page.locator('[data-testid="ceo-email"]').fill("Tony@Stratexdrone.com")
    await page.locator('[data-testid="ceo-password"]').fill("1111")
    await page.locator('[data-testid="ceo-submit"]').click()
    await page.wait_for_load_state("networkidle")
    await page.goto(PREVIEW_URL + "nextgen", wait_until="networkidle")

    nextgen_desktop = {
        "shell_visible": await page.locator('[data-testid="nextgen-shell"]').is_visible(),
        "rail_brand": await img_info('[data-testid="nx-rail-brand-image"]'),
        "hero": await img_info('[data-testid="brand-logo-full"]'),
    }
    print("NEXTGEN_DESKTOP", nextgen_desktop)

    await page.set_viewport_size({"width": 390, "height": 844})
    await page.goto(PREVIEW_URL + "nextgen", wait_until="networkidle")
    mobile_header = await img_info('[data-testid="nx-mobile-header-logo"]')
    print("NEXTGEN_MOBILE", {"mobile_header": mobile_header})

    error_text = await page.evaluate("""() => {
        const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
        return errorElements.map(el => el.textContent).join(", ");
    }""")
    if error_text:
        print(f"Found error message: {error_text}")
    else:
        print("No error messages found on the page")

    print("CONSOLE_ERRORS", console_errors)
    print("FAILED_LOGO_RESPONSES", failed_logo_responses)
