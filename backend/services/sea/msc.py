import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_msc(container_number: str):
    """
    Official MSC Driver
    Strategy: JavaScript Injection to force input state and trigger search.
    """
    print(f"🚢 [MSC] Official Site Tracking: {container_number}")
    
    async with async_playwright() as p:
        # Use headful mode for local runs
        browser = await p.chromium.launch(headless=False, args=STEALTH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://www.msc.com/en/track-a-shipment", timeout=60000)
            
            # 1. Kill Cookies (Aggressive)
            await kill_cookie_banners(page)

            # 2. Input Handling
            print("   -> Finding Input...")
            input_selector = "#trackingNumber"
            await page.wait_for_selector(input_selector, state="visible")
            
            # Focus and Type
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)
            
            # 3. FORCE UPDATE (The Fix)
            # We inject JS to manually fire the 'input' event. 
            # This forces Alpine.js to realize "Oh, there is text here!"
            print("   -> Triggering JS Events...")
            await page.evaluate(f"""
                const input = document.querySelector('{input_selector}');
                input.value = '{container_number}';
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            """)
            
            await asyncio.sleep(1) # Let JS settle

            # 4. Trigger Search via Keyboard
            # Pressing Enter is usually safer than clicking buttons covered by overlays
            print("   -> Pressing Enter...")
            await page.press(input_selector, "Enter")

            # 5. Wait for Results
            print("   -> Waiting for response...")
            
            # Wait for EITHER the Error Box OR the Result Box
            # We assume one of these MUST appear.
            try:
                await page.wait_for_selector(
                    ".msc-flow-tracking__result, .msc-flow-tracking__error", 
                    timeout=15000
                )
                print("   ✅ Page updated.")
            except:
                print("   ⚠️ Wait timed out. Taking screenshot for debug...")
                await page.screenshot(path="msc_debug_error.png")
                # If timeout, we grab whatever text is visible as a last resort
            
            # 6. Extract Data
            # Check for error first
            error_el = page.locator(".msc-flow-tracking__error")
            if await error_el.is_visible():
                error_text = await error_el.inner_text()
                print(f"   -> Found Error Message: {error_text.strip()}")
                await browser.close()
                return {
                    "source": "MSC Official",
                    "container": container_number,
                    "status": "Not Found",
                    "raw_data": error_text.strip()
                }

            # Grab Result
            result_el = page.locator(".msc-flow-tracking__result")
            if await result_el.count() > 0:
                content = await result_el.first.inner_text()
            else:
                # Fallback to body if specific element missing
                content = await page.inner_text("body")
            
            await browser.close()
            
            return {
                "source": "MSC Official",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ MSC Driver Failed: {e}")
            try:
                await page.screenshot(path="msc_crash.png")
            except: pass
            await browser.close()
            return None