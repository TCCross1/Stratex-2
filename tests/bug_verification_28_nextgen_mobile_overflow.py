"""
Focused Playwright checks for bug verification iteration 28.

Target bug/regression: STRATEX CORE logo replacement must remain in root and
/nextgen desktop locations, and the follow-up /nextgen mobile 390x844 overflow
fix must keep the mobile header logo centered with visible/non-overflowing
bottom navigation and working More sheet.
"""

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright


PREVIEW_URL = "https://stratex-quant.preview.emergentagent.com"
REPORT_PATH = Path("/app/test_reports/bug_verification_28_raw.json")


async def img_info(page, selector):
    loc = page.locator(selector).first
    await loc.wait_for(state="visible", timeout=15000)
    box = await loc.bounding_box()
    info = await loc.evaluate(
        """(img) => ({
            src: img.currentSrc || img.src,
            naturalWidth: img.naturalWidth,
            naturalHeight: img.naturalHeight,
            complete: img.complete,
            alt: img.alt,
            className: img.className,
            visible: !!(img.offsetWidth || img.offsetHeight || img.getClientRects().length)
        })"""
    )
    return {**info, "box": box}


async def collect_scroll_metrics(page):
    return await page.evaluate(
        """() => {
            const doc = document.documentElement;
            const body = document.body;
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;
            const widest = Array.from(document.querySelectorAll('*')).map((el) => {
                const r = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    testid: el.getAttribute('data-testid') || '',
                    id: el.id || '',
                    cls: typeof el.className === 'string' ? el.className.slice(0, 160) : '',
                    width: Math.round(r.width * 100) / 100,
                    left: Math.round(r.left * 100) / 100,
                    right: Math.round(r.right * 100) / 100,
                    scrollWidth: el.scrollWidth || 0,
                    text: (el.textContent || '').trim().slice(0, 80)
                };
            }).filter((x) => x.width > viewportWidth + 1 || x.right > viewportWidth + 1 || x.left < -1 || x.scrollWidth > viewportWidth + 1)
              .sort((a, b) => Math.max(b.width, b.scrollWidth) - Math.max(a.width, a.scrollWidth))
              .slice(0, 12);
            return {
                viewportWidth,
                viewportHeight,
                documentScrollWidth: doc.scrollWidth,
                bodyScrollWidth: body ? body.scrollWidth : null,
                documentClientWidth: doc.clientWidth,
                bodyClientWidth: body ? body.clientWidth : null,
                scrollX: window.scrollX,
                widest
            };
        }"""
    )


async def main():
    results = {
        "console_errors": [],
        "page_errors": [],
        "failed_requests": [],
        "failed_logo_responses": [],
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)

        async def ceo_login(pg):
            await pg.goto(PREVIEW_URL + "/ceo/login", wait_until="networkidle")
            await pg.locator('[data-testid="ceo-email"]').wait_for(state="visible", timeout=15000)
            await pg.locator('[data-testid="ceo-email"]').fill("Tony@Stratexdrone.com")
            await pg.locator('[data-testid="ceo-password"]').fill("1111")
            async with pg.expect_response(lambda r: "/api/auth/ceo/login" in r.url, timeout=15000) as resp_info:
                await pg.locator('[data-testid="ceo-submit"]').click()
            resp = await resp_info.value
            await pg.wait_for_timeout(1000)
            token = await pg.evaluate("localStorage.getItem('stratex_token')")
            assert resp.status == 200, f"CEO login failed with {resp.status}"
            assert token, "CEO login did not persist stratex_token"

        # Root regression checks at desktop size.
        desktop_context = await browser.new_context(viewport={"width": 1440, "height": 900})
        desktop_page = await desktop_context.new_page()
        desktop_page.on("console", lambda msg: results["console_errors"].append({"location": "desktop", "type": msg.type, "text": msg.text}) if msg.type == "error" else None)
        desktop_page.on("pageerror", lambda exc: results["page_errors"].append({"location": "desktop", "text": str(exc)}))
        desktop_page.on("requestfailed", lambda req: results["failed_requests"].append({"location": "desktop", "url": req.url, "failure": str(req.failure or "unknown")}))
        desktop_page.on("response", lambda resp: results["failed_logo_responses"].append(f"{resp.status} {resp.url}") if "/brand/stratex-core-logo.png" in resp.url and resp.status >= 400 else None)

        await desktop_page.goto(PREVIEW_URL + "/", wait_until="networkidle")
        results["root_logos"] = {
            "nav_home_logo": await img_info(desktop_page, '[data-testid="nav-home-logo"] img'),
            "rail_home": await img_info(desktop_page, '[data-testid="rail-home"] img'),
            "splash": await img_info(desktop_page, '[data-testid="splash-stratex-core-logo"]'),
        }

        # Desktop /nextgen rail brand regression. Login using real CEO flow.
        await ceo_login(desktop_page)
        await desktop_page.goto(PREVIEW_URL + "/nextgen", wait_until="networkidle")
        await desktop_page.locator('[data-testid="nextgen-shell"]').wait_for(state="visible", timeout=15000)
        results["nextgen_desktop"] = {
            "url": desktop_page.url,
            "rail_brand": await img_info(desktop_page, '[data-testid="nx-rail-brand-image"]'),
            "scroll": await collect_scroll_metrics(desktop_page),
        }
        await desktop_context.close()

        # Critical mobile check: viewport is set via new_context BEFORE navigation,
        # then login through the real /ceo/login flow before opening /nextgen.
        mobile_context = await browser.new_context(viewport={"width": 390, "height": 844})
        mobile_page = await mobile_context.new_page()
        mobile_page.on("console", lambda msg: results["console_errors"].append({"location": "mobile", "type": msg.type, "text": msg.text}) if msg.type == "error" else None)
        mobile_page.on("pageerror", lambda exc: results["page_errors"].append({"location": "mobile", "text": str(exc)}))
        mobile_page.on("requestfailed", lambda req: results["failed_requests"].append({"location": "mobile", "url": req.url, "failure": str(req.failure or "unknown")}))
        mobile_page.on("response", lambda resp: results["failed_logo_responses"].append(f"{resp.status} {resp.url}") if "/brand/stratex-core-logo.png" in resp.url and resp.status >= 400 else None)
        await ceo_login(mobile_page)
        await mobile_page.goto(PREVIEW_URL + "/nextgen", wait_until="networkidle")
        await mobile_page.locator('[data-testid="nextgen-shell"]').wait_for(state="visible", timeout=15000)
        await mobile_page.wait_for_timeout(500)

        logo = await img_info(mobile_page, '[data-testid="nx-mobile-header-logo"]')
        scroll = await collect_scroll_metrics(mobile_page)
        bottom_nav = await mobile_page.locator('[data-testid="nx-bottom-nav"]').bounding_box()
        nav_metrics = await mobile_page.locator('[data-testid="nx-bottom-nav"]').evaluate(
            """(nav) => {
                const r = nav.getBoundingClientRect();
                return {
                    visible: !!(nav.offsetWidth || nav.offsetHeight || nav.getClientRects().length),
                    left: r.left, right: r.right, width: r.width, height: r.height,
                    display: getComputedStyle(nav).display,
                    position: getComputedStyle(nav).position
                };
            }"""
        )
        viewport_center = 195
        logo_center = logo["box"]["x"] + logo["box"]["width"] / 2
        results["nextgen_mobile_initial"] = {
            "url": mobile_page.url,
            "logo": logo,
            "logoCenterX": logo_center,
            "viewportCenterX": viewport_center,
            "logoDeltaFromCenter": logo_center - viewport_center,
            "scroll": scroll,
            "bottomNav": {"box": bottom_nav, **nav_metrics},
        }

        # Regression: bottom nav five tabs reachable and More sheet opens.
        tab_results = []
        for testid, expected_path in [
            ("nx-tab-home", "/nextgen"),
            ("nx-tab-missions", "/nextgen/missions"),
            ("nx-tab-passport", "/nextgen/passport"),
            ("nx-tab-reports", "/nextgen/reports"),
        ]:
            loc = mobile_page.locator(f'[data-testid="{testid}"]').first
            await loc.wait_for(state="visible", timeout=10000)
            box = await loc.bounding_box()
            await loc.click()
            await mobile_page.wait_for_load_state("networkidle")
            await mobile_page.wait_for_timeout(250)
            tab_results.append({"testid": testid, "box": box, "url": mobile_page.url, "expectedPath": expected_path, "reachable": expected_path in mobile_page.url})

        more = mobile_page.locator('[data-testid="nx-tab-more"]').first
        await more.wait_for(state="visible", timeout=10000)
        more_box = await more.bounding_box()
        await more.click()
        await mobile_page.wait_for_timeout(500)
        sheet = mobile_page.locator('[data-testid="nx-more-sheet"]').first
        sheet_box = await sheet.bounding_box()
        sheet_state = await sheet.evaluate(
            """(el) => ({
                visible: !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length),
                className: el.className,
                transform: getComputedStyle(el).transform,
                ariaLabel: el.getAttribute('aria-label')
            })"""
        )
        tab_results.append({"testid": "nx-tab-more", "box": more_box, "url": mobile_page.url, "reachable": sheet_state["visible"] and "open" in sheet_state["className"]})

        # One representative sheet navigation item should be clickable.
        sheet_item = mobile_page.locator('[data-testid="nx-sheet-properties"]').first
        await sheet_item.wait_for(state="visible", timeout=10000)
        await sheet_item.click()
        await mobile_page.wait_for_load_state("networkidle")
        await mobile_page.wait_for_timeout(250)
        results["mobile_more_and_tabs"] = {
            "tabs": tab_results,
            "sheet": {"box": sheet_box, **sheet_state},
            "sheetNavigationUrl": mobile_page.url,
            "sheetNavigationWorked": "/nextgen/properties" in mobile_page.url,
            "postNavigationScroll": await collect_scroll_metrics(mobile_page),
        }

        error_text = await mobile_page.evaluate(
            """() => {
                const errorElements = Array.from(document.querySelectorAll('.error, [class*="error"], [id*="error"]'));
                return errorElements.map(el => el.textContent).join(", ");
            }"""
        )
        results["visible_error_text"] = error_text

        await mobile_context.close()
        await browser.close()

    REPORT_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    asyncio.run(main())