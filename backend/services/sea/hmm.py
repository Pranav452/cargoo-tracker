import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_hmm(container_number: str):
    """
    Official HMM (Hyundai) Driver
    Fixed: Handles HTTP2 Protocol Errors.
    """
    print(f"🚢 [HMM] Official Site Tracking: {container_number}")

    async with async_playwright() as p:
        # Add --disable-http2 to args to prevent the protocol error
        custom_args = STEALTH_ARGS + ["--disable-http2"]

        browser = await p.chromium.launch(headless=True, args=custom_args)

        # Ignore HTTPS errors to be safe
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            await page.goto("https://www.hmm21.com/company.do", timeout=60000)

            # 1. Kill Cookies
            await kill_cookie_banners(page)

            # 2. Click "Track & Trace" Tab
            print("   -> Clicking 'Track & Trace' tab...")
            await page.click("text=Track & Trace")
            await asyncio.sleep(1)

            # 3. Select "Container No." Radio Button
            print("   -> Selecting 'Container No.'...")
            # Use label click to ensure radio is selected
            await page.click("label[for='radio-id4']")

            # 4. Input
            print("   -> Typing Container Number...")
            input_selector = "#selectTnt"
            await page.wait_for_selector(input_selector, state="visible")
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)

            # 5. Click Search (and wait for navigation/load)
            print("   -> Clicking Search...")

            # HMM often opens the result in the SAME container but refreshes the DOM
            # We wait for a specific element that only appears AFTER search
            await page.click("button.retreve")

            # 6. WAIT FOR RESULTS (The Critical Fix)
            print("   -> Waiting for results table...")

            try:
                # Wait for "Tracking Result" text or the specific result table class
                # Based on your raw text: "Tracking Result" is a header
                await page.wait_for_selector("text=Tracking Result", timeout=25000)

                # Wait a bit more for the rows to populate
                await asyncio.sleep(2)

                # Extract the specific container holding the data
                # This avoids grabbing the menu/footer noise
                # Try to target the main content area
                content = await page.inner_text(".contents, #contents, body")

            except:
                print("   ⚠️ specific selector timeout. Waiting for network idle...")
                await page.wait_for_load_state("networkidle")
                content = await page.inner_text("body")

            await browser.close()

            return {
                "source": "HMM Official",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ HMM Driver Failed: {e}")
            await browser.close()
            return None
