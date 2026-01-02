import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS, human_type, kill_cookie_banners

async def drive_hmm(container_number: str):
    """
    Official HMM Driver (Server-Ready)
    - Headless: TRUE (Required for EC2/Railway)
    - Protocol: HTTP/1.1 Forced (Prevents blocking)
    - Logic: JS-based clicking for reliability
    """
    print(f"🚢 [HMM] Official Site Tracking: {container_number}")
    
    async with async_playwright() as p:
        # Add --disable-http2 to prevent ERR_HTTP2_PROTOCOL_ERROR on HMM site
        custom_args = STEALTH_ARGS + ["--disable-http2"]
        browser = await p.chromium.launch(headless=True, args=custom_args)
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            print("   -> Navigating to HMM...")
            await page.goto("https://www.hmm21.com/company.do", timeout=90000, wait_until="domcontentloaded")
            await asyncio.sleep(3) # Let assets load

            # 3. Handle Cookies
            await kill_cookie_banners(page)

            # 4. Click 'Track & Trace' Tab (Using JS Injection)
            # This is more reliable than selectors because layout shifts don't break it
            print("   -> Switching to Track & Trace Tab...")
            found_tab = await page.evaluate("""() => {
                const tabs = Array.from(document.querySelectorAll('li, div, a, span'));
                const target = tabs.find(el => el.textContent.trim() === 'Track & Trace');
                if (target) {
                    target.click();
                    return true;
                }
                return false;
            }""")
            
            if not found_tab:
                print("   ⚠️ JS Click failed, trying Playwright text selector...")
                await page.click("text=Track & Trace")
            
            # Wait for the input area to slide down
            await page.wait_for_selector(".tracktace", state="visible", timeout=10000)

            # 5. Select Radio Button
            print("   -> Selecting Container Radio...")
            await page.click("label[for='radio-id4']")
            await asyncio.sleep(0.5)

            # 6. Input Number
            print("   -> Typing Number...")
            input_selector = "#selectTnt"
            await page.click(input_selector)
            await human_type(page, input_selector, container_number)
            await asyncio.sleep(0.5)  # Small delay after typing

            # 7. Click Search
            print("   -> Clicking Search...")
            try:
                # Wait for button to be visible and clickable
                await page.wait_for_selector("button.retreve", state="visible", timeout=5000)
                # Try clicking the button first
                await page.click("button.retreve")
                print("   -> Button clicked successfully")
            except Exception as e:
                print(f"   -> Button click failed: {e}, trying JavaScript function...")
                # Fallback: Call the JavaScript function directly
                try:
                    await page.evaluate("gotoTrkNTrc()")
                    print("   -> JavaScript function called successfully")
                except Exception as js_error:
                    print(f"   -> JavaScript function call failed: {js_error}")
                    # Last resort: Try pressing Enter on the input
                    await page.press(input_selector, "Enter")
                    print("   -> Pressed Enter as fallback")

            # 8. Wait for Results
            print("   -> Waiting for results...")
            try:
                # HMM Results can take time. We wait for the specific "Tracking Result" header.
                await page.wait_for_selector("text=Tracking Result", timeout=40000)
                
                # Expand specific sections if needed (HMM sometimes collapses them)
                # But usually grabbing body is enough
                await asyncio.sleep(2)
                
                # We grab the BODY to ensure we get the full timeline
                # The AI needs the "Arrival" column in the "Vessel Movement" table
                content = await page.inner_text("body")
                
                print(f"   ✅ Data Extracted ({len(content)} chars)")
                
                await browser.close()
                return {
                    "source": "HMM Official",
                    "container": container_number,
                    "raw_data": content
                }

            except Exception as e:
                print(f"   ⚠️ Result Timeout: {e}")
                # Last ditch effort: grab whatever text is visible
                content = await page.inner_text("body")
                await browser.close()
                return {
                    "source": "HMM Partial",
                    "container": container_number,
                    "raw_data": content
                }

        except Exception as e:
            print(f"   ❌ HMM Driver Crashed: {e}")
            await browser.close()
            return None