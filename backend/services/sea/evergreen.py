import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_evergreen(container_number: str):
    """
    Evergreen Driver (Via ShipmentLink)
    URL: https://ct.shipmentlink.com/servlet/TDB1_CargoTracking.do
    """
    print(f"🚢 [Evergreen] Tracking via ShipmentLink: {container_number}")
    
    async with async_playwright() as p:
        # Use headful mode for local debugging
        browser = await p.chromium.launch(headless=False, args=STEALTH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # 1. Navigate to ShipmentLink tracking page
            print("   -> Navigating to ShipmentLink...")
            await page.goto("https://ct.shipmentlink.com/servlet/TDB1_CargoTracking.do", timeout=60000)
            await asyncio.sleep(2)

            # 2. Handle cookie banners
            await kill_cookie_banners(page)
            
            # Additional check for ShipmentLink specific cookie button
            try:
                accept_all = page.locator("button:has-text('Accept All')")
                if await accept_all.is_visible(timeout=3000):
                    print("   🍪 Clicking 'Accept All' cookies...")
                    await accept_all.click()
                    await asyncio.sleep(1)
            except:
                pass

            # 3. Select "Container No." radio button (IMPORTANT: s_bl is checked by default, not s_cntr!)
            print("   -> Selecting 'Container No.' radio button...")
            radio_selector = "input#s_cntr"
            await page.wait_for_selector(radio_selector, state="visible", timeout=10000)
            
            # Click the radio button to select Container No.
            await page.click(radio_selector, force=True)
            await asyncio.sleep(1)
            
            # Verify it's checked
            is_checked = await page.is_checked(radio_selector)
            print(f"   -> Container No. radio button checked: {is_checked}")

            # 4. Input container number
            print("   -> Entering container number...")
            input_selector = "input#NO"  # Use ID selector
            await page.wait_for_selector(input_selector, state="visible")
            
            # Focus and clear the input
            await page.focus(input_selector)
            await asyncio.sleep(0.5)
            
            # Use evaluate to ensure the field is ready
            await page.evaluate(f"""
                const input = document.querySelector('input#NO');
                if (input) {{
                    input.focus();
                    input.value = '';
                }}
            """)
            await asyncio.sleep(0.5)
            
            # Type the container number
            await page.type(input_selector, container_number, delay=100)
            await asyncio.sleep(1)
            
            # Verify the value was entered
            entered_value = await page.input_value(input_selector)
            print(f"   -> Entered value: {entered_value}")

            # 5. Submit the form
            print("   -> Submitting form...")
            # Instead of clicking the button, directly call the JavaScript function
            # This avoids issues with multiple buttons and visibility
            await asyncio.sleep(1)
            print("   -> Calling frmSubmit(13, 2) via JavaScript...")
            await page.evaluate("frmSubmit(13, 2)")

            # 6. Wait for results to load
            print("   -> Waiting for results...")
            try:
                # Wait for either results or error message
                await page.wait_for_load_state("networkidle", timeout=20000)
                await asyncio.sleep(3)  # Give time for content to fully render
            except Exception as e:
                print(f"   ⚠️ Network idle timeout: {e}")

            # 7. Extract tracking details
            print("   -> Extracting tracking data...")
            
            # Check for error messages first
            error_selectors = [
                "text=No information",
                "text=not found",
                "text=invalid",
                ".error-message"
            ]
            
            for error_sel in error_selectors:
                try:
                    if await page.locator(error_sel).is_visible(timeout=1000):
                        print("   ❌ Container not found or error message detected.")
                        await browser.close()
                        return None
                except:
                    continue

            # Extract the full page content
            # ShipmentLink typically displays results in tables or divs
            content = await page.inner_text("body")
            
            await browser.close()
            
            # Basic validation - check if we got meaningful data
            if len(content) < 100 or "TDB1_CargoTracking" in content:
                print("   ⚠️ Insufficient tracking data received.")
                return None

            print(f"   ✅ Successfully extracted {len(content)} characters of tracking data")
            
            return {
                "source": "Evergreen (via ShipmentLink)",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ Evergreen Driver Failed: {e}")
            try:
                await browser.close()
            except:
                pass
            return None

