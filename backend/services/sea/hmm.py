import asyncio
import re
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type

async def drive_hmm(container_number: str):
    """
    Official HMM Driver - Form Interaction Strategy
    Actually fills the form and submits it like a real user.
    """
    print(f"🚢 [HMM] Official Site Tracking: {container_number}")
    
    async with async_playwright() as p:
        custom_args = STEALTH_ARGS + [
            "--disable-http2", 
            "--no-zygote",
            "--window-size=1920,1080"
        ]
        
        browser = await p.chromium.launch(
            headless=False,  
            args=custom_args
        )
        
        context = await browser.new_context(
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        # Hide automation flags
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        try:
            # 1. Load the tracking page
            print("   -> Loading HMM tracking page...")
            await page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", 
                          timeout=60000, 
                          wait_until="domcontentloaded")
            
            # Wait a bit for page to settle
            await asyncio.sleep(2)
            
            # 2. Find and fill the TOP SEARCH BAR in the header
            print(f"   -> Entering container number in top search bar: {container_number}")
            
            # The top search bar has placeholder "B/L, Booking, CNTR No., Keywords"
            # Try multiple possible selectors for the header search input
            input_selectors = [
                "input[placeholder*='B/L']",
                "input[placeholder*='CNTR']",
                "input[placeholder*='Keywords']",
                "header input[type='text']",
                ".header-search input",
                "#searchInput"
            ]
            
            input_found = False
            used_selector = None
            for selector in input_selectors:
                try:
                    await page.wait_for_selector(selector, state="visible", timeout=5000)
                    print(f"   ✅ Found top search bar with selector: {selector}")
                    
                    # Click and type
                    await page.click(selector)
                    await asyncio.sleep(0.5)
                    await page.fill(selector, "")  # Clear first
                    await human_type(page, selector, container_number)
                    
                    input_found = True
                    used_selector = selector
                    break
                except:
                    continue
            
            if not input_found:
                print("   ❌ Could not find top search bar")
                await page.screenshot(path="/tmp/hmm_no_input.png")
                await browser.close()
                return None
            
            # 3. Press Enter or click search icon in the header
            print("   -> Submitting search (pressing Enter)...")
            
            # Just press Enter on the search input
            await page.press(used_selector, "Enter")
            
            # 4. Wait for results to load
            print("   -> Waiting for results...")
            
            # Wait for either results or error message
            try:
                # Wait for page to update (look for common result indicators)
                await page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(2)  # Extra time for dynamic content
                print("   ✅ Page loaded")
            except:
                print("   ⚠️ Timeout waiting for results, proceeding anyway...")
            
            # 5. Extract the tracking data
            print("   -> Extracting tracking data...")
            
            # Take screenshot for debugging
            from datetime import datetime
            screenshot_path = f"/tmp/hmm_result_{container_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await page.screenshot(path=screenshot_path)
            print(f"   📸 Screenshot saved: {screenshot_path}")
            
            # Get the page content
            content = await page.content()
            
            # Also try to get specific result areas
            result_selectors = [
                ".result-area",
                "#resultArea", 
                ".tracking-result",
                "table.result",
                ".container-info"
            ]
            
            result_text = ""
            for selector in result_selectors:
                try:
                    element = page.locator(selector)
                    if await element.count() > 0:
                        result_text += await element.first.inner_text()
                        result_text += "\n\n"
                except:
                    continue
            
            # If we found specific result areas, use those; otherwise use full page
            if result_text.strip():
                final_content = result_text
                print(f"   ✅ Extracted {len(final_content)} chars from result area")
            else:
                # Fallback to body text
                final_content = await page.inner_text("body")
                print(f"   ✅ Extracted {len(final_content)} chars from page body")
            
            # Save response for debugging
            debug_file = f"/tmp/hmm_response_{container_number}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            with open(debug_file, "w") as f:
                f.write(f"Container: {container_number}\n")
                f.write(f"Length: {len(final_content)}\n")
                f.write("="*80 + "\n")
                f.write(final_content)
            print(f"   📝 Response saved to: {debug_file}")

            await browser.close()
            
            return {
                "source": "HMM Official (Form Interaction)",
                "container": container_number,
                "raw_data": final_content
            }

        except Exception as e:
            print(f"   ❌ HMM Driver Failed: {e}")
            try:
                await page.screenshot(path="/tmp/hmm_crash.png")
                print("   📸 Crash screenshot saved to /tmp/hmm_crash.png")
            except:
                pass
            await browser.close()
            return None