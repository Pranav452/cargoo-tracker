import asyncio
import random
from playwright.async_api import async_playwright

async def drive_sea_fallback(container_number: str):
    """
    Universal Sea Fallback: Track-Trace Container Module.
    Used when Cargoes Flow API returns no data.
    """
    print(f"⚓ [Fallback] Routing {container_number} to Track-Trace...")
    
    async with async_playwright() as p:
        # Launch Browser (Headless=False for debugging, change to True later)
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        try:
            await page.goto("https://www.track-trace.com/container", timeout=60000)
            
            # 1. Input
            await page.fill("input[name='number']", container_number)
            
            # 2. Click Track & Catch New Tab
            async with page.expect_popup() as popup_info:
                await page.click("#wc-multi-form-button_direct")
            
            # 3. Switch to the New Tab
            new_page = await popup_info.value
            await new_page.wait_for_load_state("domcontentloaded")
            
            # 4. Handle "I'm Sure" Interstitial (Revenue Protection)
            print("   -> Checking for Interstitial...")
            try:
                # Look for button text "I'm sure, continue with"
                btn = new_page.get_by_text("I'm sure, continue with", exact=False)
                if await btn.is_visible(timeout=5000):
                    print("   -> Clicking Interstitial...")
                    await btn.click()
                    await new_page.wait_for_load_state("domcontentloaded")
            except: 
                pass

            # 5. Wait for external site to load (Hapag/MSC frame)
            print("   -> Waiting for results...")
            await asyncio.sleep(8) 
            
            # 6. Extract Data
            # We grab the full text. The AI will parse the dates/status later.
            content = await new_page.inner_text("body")
            
            await browser.close()
            
            if len(content) < 50:
                return None
                
            return {
                "source": "Track-Trace Fallback",
                "container": container_number,
                "raw_text": content
            }

        except Exception as e:
            print(f"   ❌ Fallback Error: {e}")
            await browser.close()
            return None