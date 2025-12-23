import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_hmm(container_number: str):
    """
    Official HMM (Hyundai) Driver
    URL: https://www.hmm21.com/company.do
    """
    print(f"🚢 [HMM] Official Site Tracking: {container_number}")

    async with async_playwright() as p:
        # Launch Headless=True for Production (Railway)
        browser = await p.chromium.launch(headless=True, args=STEALTH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto("https://www.hmm21.com/company.do", timeout=60000)

            # 1. Kill Cookies
            await kill_cookie_banners(page)

            # 2. Click "Track & Trace" Tab
            # Based on screenshot, it's likely a text link or tab header
            print("   -> Clicking 'Track & Trace' tab...")
            await page.click("text=Track & Trace")

            # Small pause for tab animation
            await asyncio.sleep(1)

            # 3. Select "Container No." Radio Button
            print("   -> Selecting 'Container No.'...")
            # We click the label because clicking the hidden radio input might fail
            await page.click("label[for='radio-id4']")

            # 4. Input
            print("   -> Typing Container Number...")
            input_selector = "#selectTnt"
            await page.wait_for_selector(input_selector, state="visible")
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)

            # 5. Click Search
            print("   -> Clicking Search...")
            # The button class from your HTML
            await page.click("button.retreve")

            # 6. Wait for Results
            print("   -> Waiting for results...")

            # HMM Search usually opens a popup or redirects.
            # If it redirects in the same tab:
            try:
                await page.wait_for_load_state("networkidle")
                # Wait for a table or specific result container
                await page.wait_for_selector("table, .contents, .result", timeout=20000)
            except:
                print("   ⚠️ Wait timeout. Grabbing whatever is on screen.")

            # 7. Extract Data
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
