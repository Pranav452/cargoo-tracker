import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type

async def drive_cma(container_number: str):
    """
    CMA CGM Driver (Via ParcelsApp Proxy)
    Reason: Official site has high-level WAF (Web Application Firewall) blocking.
    URL: https://parcelsapp.com/en/carriers/cma-cgm
    """
    print(f"🚢 [CMA] Routing via ParcelsApp (Bypassing WAF): {container_number}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=STEALTH_ARGS)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Go to the CMA specific page on ParcelsApp
            await page.goto("https://parcelsapp.com/en/carriers/cma-cgm", timeout=60000)
            
            # 1. Input
            # ParcelsApp usually has a big input box
            print("   -> Finding Input...")
            input_selector = "input.form-control"
            await page.wait_for_selector(input_selector, state="visible")
            
            # Clear and Type
            await page.click(input_selector)
            await page.fill(input_selector, "")
            await human_type(page, input_selector, container_number)
            
            # 2. Click Track
            print("   -> Clicking Track...")
            # The button usually has class 'btn-parcels'
            await page.click("button.btn-parcels")

            # 3. Wait for Results
            print("   -> Waiting for results (ParcelsApp)...")
            
            # ParcelsApp shows a spinner, then the results in a div called 'states' or 'tracking-info'
            try:
                # Wait for the spinner to go away or result to appear
                await asyncio.sleep(5)
                await page.wait_for_selector(".states, .tracking-info", timeout=30000)
            except:
                print("   ⚠️ specific selector timeout. Waiting for network idle...")
                await page.wait_for_load_state("networkidle")

            # 4. Extract Data
            # ParcelsApp puts the timeline in a nice list. We grab the text.
            content = await page.inner_text("body")
            
            await browser.close()
            
            # Check if ParcelsApp failed too
            if "No information about your package" in content:
                print("   ❌ ParcelsApp found no data.")
                return None

            return {
                "source": "CMA (via ParcelsApp)",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ CMA Driver Failed: {e}")
            await browser.close()
            return None