import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type

async def drive_hapag(container_number: str):
    """
    Official Hapag-Lloyd Driver
    URL: https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html
    """
    print(f"🚢 [Hapag] Official Site Tracking: {container_number}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=STEALTH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html", timeout=60000)
            
            # 1. WAIT FOR & KILL POPUP (The Fix)
            print("   -> Waiting for OneTrust Cookie Popup...")
            try:
                # We use the EXACT ID you provided
                cookie_id = "#accept-recommended-btn-handler"
                
                # Wait explicitly for this element to exist in the DOM
                await page.wait_for_selector(cookie_id, state="visible", timeout=10000)
                
                print("   🍪 Found 'Select All'. Clicking...")
                # Force click in case it's animating
                await page.click(cookie_id, force=True)
                
                # Wait for it to disappear so it doesn't block the input
                await asyncio.sleep(2)
                print("   -> Popup dismissed.")
                
            except Exception as e:
                print(f"   ⚠️ Cookie banner did not appear or timed out: {e}")

            # 2. Input
            print("   -> Finding Input...")
            input_selector = '[id="tracing_by_container_f:hl12"]'
            
            # Fallback selector if ID changes
            if not await page.locator(input_selector).is_visible():
                input_selector = "input.hal-olb-input"

            await page.wait_for_selector(input_selector, state="visible")
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)
            
            # 3. Click Find
            print("   -> Clicking Find...")
            button_selector = '[id="tracing_by_container_f:hl25"]'
            
            if not await page.locator(button_selector).is_visible():
                button_selector = "button:has-text('Find')"

            await page.click(button_selector)

            # 4. Wait for Results
            print("   -> Waiting for results...")
            try:
                await page.wait_for_selector("table, .hal-table", timeout=20000)
            except:
                print("   ⚠️ Table selector timeout. Waiting for network idle...")
                await page.wait_for_load_state("networkidle")

            # 5. Extract Data
            content = await page.inner_text("body")
            
            await browser.close()
            
            return {
                "source": "Hapag Official",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ Hapag Driver Failed: {e}")
            await browser.close()
            return None