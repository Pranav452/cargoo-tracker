import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_hmm(container_number: str):
    """
    Official HMM (Hyundai) Driver - Testing Version
    Follows user-specified sequence: Menu -> Radio -> Input -> Search
    """
    print(f"🚢 [HMM] Official Site Tracking: {container_number}")

    async with async_playwright() as p:
        # Add --disable-http2 to prevent ERR_HTTP2_PROTOCOL_ERROR on HMM site
        custom_args = STEALTH_ARGS + ["--disable-http2"]
        browser = await p.chromium.launch(headless=True, args=custom_args)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            # Go to the HMM site
            print("   -> Navigating to HMM website...")
            await page.goto("https://www.hmm21.com/company.do", wait_until="domcontentloaded", timeout=90000)
            # Wait a bit for any dynamic content
            await asyncio.sleep(2)

            # 1. Kill Cookies
            await kill_cookie_banners(page)

            # 2. CLICK THE "Track & Trace" MENU TAB
            print("   -> 1. Scrolling down and clicking 'Track & Trace' tab...")
            
            # Just scroll down to where the tabs are (about 600px down)
            await page.mouse.wheel(0, 600)
            await asyncio.sleep(1)
            
            # Now click the second li in any visible div.tabs that has "Track & Trace"
            # Use JavaScript to be more reliable
            await page.evaluate("""
                const tabs = document.querySelectorAll('div.tabs ul li');
                for (let tab of tabs) {
                    if (tab.textContent.includes('Track & Trace')) {
                        tab.click();
                        break;
                    }
                }
            """)
            print("      -> Clicked 'Track & Trace' tab.")
            
            # CRITICAL: Wait for the .tracktace div to become visible
            print("      -> Waiting for Track & Trace section to appear...")
            await page.wait_for_selector("div.tracktace", state="visible", timeout=10000)
            print("      -> Track & Trace section is now visible.")

            # 3. CLICK THE "Container No." RADIO LABEL
            print("   -> 2. Selecting 'Container No.' radio button...")
            container_label = page.locator("label[for='radio-id4']")
            await container_label.wait_for(state="visible")
            await container_label.click()

            # 4. INPUT THE NUMBER
            print("   -> 3. Typing Container Number...")
            input_selector = "#selectTnt"
            await page.wait_for_selector(input_selector, state="visible")
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)

            # 5. CLICK SEARCH (the one inside .tracktace section)
            print("   -> 4. Clicking Search...")
            search_button = page.locator("div.tracktace button.retreve")
            await search_button.click()

            # 6. WAIT FOR RESULTS
            print("   -> 5. Waiting for results...")

            # Wait for the results to load in the same window
            try:
                await page.wait_for_selector("text=Tracking Result", timeout=25000)
                print("   -> Results loaded successfully.")
                await asyncio.sleep(2)
                content = await page.inner_text(".contents, #contents")
            except Exception as e:
                print(f"   ⚠️ Result wait timed out: {e}. Grabbing body.")
                content = await page.inner_text("body")

            await browser.close()

            return {
                "source": "HMM Official",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ HMM Driver Crashed: {e}")
            await browser.close()
            return None
