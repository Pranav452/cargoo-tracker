import asyncio
from playwright.async_api import async_playwright
from services.utils import (
    STEALTH_ARGS, 
    create_stealth_context, 
    human_type, 
    human_delay,
    human_mouse_movement,
    human_scroll,
    random_viewport_scroll,
    kill_cookie_banners
)


async def drive_cma(container_number: str):
    """
    CMA CGM Driver with Advanced Stealth
    Uses headful mode, fingerprint spoofing, and human behavior simulation
    to bypass enterprise-grade WAF protection.
    
    URL: https://www.cma-cgm.com/ebusiness/tracking
    """
    print(f"[CMA] Official Site Tracking: {container_number}")
    
    async with async_playwright() as p:
        # Launch in HEADFUL mode for local interactive debugging
        browser = await p.chromium.launch(
            headless=False,
            args=STEALTH_ARGS
        )
        
        # Create stealth context with fingerprint spoofing
        context = await create_stealth_context(browser)
        page = await context.new_page()

        try:
            # 1. Navigate to tracking page with human-like timing
            print("   -> Navigating to CMA CGM tracking page...")
            await page.goto(
                "https://www.cma-cgm.com/ebusiness/tracking",
                wait_until="domcontentloaded",
                timeout=60000
            )
            
            # Initial human delay to let page fully load
            await human_delay(2000, 4000)
            
            # Simulate human behavior - move mouse around
            await human_mouse_movement(page)
            
            # 2. Handle cookie consent banner
            print("   -> Checking for cookie banner...")
            await kill_cookie_banners(page)
            
            # Additional CMA-specific cookie selectors
            cma_cookie_selectors = [
                "#onetrust-accept-btn-handler",
                "button[id*='accept']",
                "button:has-text('Accept')",
                "button:has-text('I Accept')",
                ".cookie-accept",
                "[data-testid='cookie-accept']"
            ]
            
            for sel in cma_cookie_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=2000):
                        print(f"   -> Found cookie button: {sel}")
                        await page.locator(sel).first.click()
                        await human_delay(1000, 2000)
                        break
                except:
                    continue
            
            # 3. Simulate natural browsing - scroll around
            await random_viewport_scroll(page)
            await human_delay(500, 1500)
            
            # 4. Find the tracking input field
            print("   -> Looking for tracking input field...")
            
            # Common selectors for CMA tracking input
            input_selectors = [
                "input[name*='tracking']",
                "input[name*='container']",
                "input[placeholder*='container']",
                "input[placeholder*='tracking']",
                "input[id*='tracking']",
                "input[id*='container']",
                "#trackingNumber",
                ".tracking-input",
                "input[type='text']"
            ]
            
            input_selector = None
            for sel in input_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=3000):
                        input_selector = sel
                        print(f"   -> Found input: {sel}")
                        break
                except:
                    continue
            
            if not input_selector:
                print("   -> Could not find tracking input. Taking screenshot...")
                await page.screenshot(path="cma_no_input.png")
                
                # Try to get page content for debugging
                content = await page.content()
                if "Access blocked" in content or "blocked" in content.lower():
                    print("   -> ACCESS BLOCKED detected. WAF triggered.")
                    await browser.close()
                    return {
                        "source": "CMA CGM Official",
                        "container": container_number,
                        "status": "Blocked",
                        "raw_data": "Access blocked by WAF. Consider using a residential proxy."
                    }
                
                await browser.close()
                return None
            
            # 5. Move mouse to input and click
            await human_mouse_movement(page)
            
            # Scroll to the input if needed
            await page.locator(input_selector).first.scroll_into_view_if_needed()
            await human_delay(300, 700)
            
            # Click on the input
            await page.locator(input_selector).first.click()
            await human_delay(200, 500)
            
            # 6. Type container number with human-like delays
            print(f"   -> Typing container number: {container_number}")
            await human_type(page, input_selector, container_number)
            await human_delay(500, 1000)
            
            # 7. Find and click the search button or press Enter
            print("   -> Submitting search...")
            
            search_button_selectors = [
                "button[type='submit']",
                "button:has-text('Search')",
                "button:has-text('Track')",
                "button:has-text('Find')",
                ".search-button",
                "[data-testid='search-button']",
                "input[type='submit']"
            ]
            
            search_clicked = False
            for sel in search_button_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=2000):
                        await human_mouse_movement(page)
                        await page.locator(sel).first.click()
                        search_clicked = True
                        print(f"   -> Clicked search button: {sel}")
                        break
                except:
                    continue
            
            if not search_clicked:
                # Fallback: press Enter
                print("   -> No search button found. Pressing Enter...")
                await page.press(input_selector, "Enter")
            
            # 8. Wait for results to load
            print("   -> Waiting for results...")
            await human_delay(3000, 5000)
            
            try:
                await page.wait_for_load_state("networkidle", timeout=30000)
            except:
                print("   -> Network idle timeout. Continuing...")
            
            await human_delay(1000, 2000)
            
            # 9. Check for blocked access
            page_content = await page.content()
            if "Access blocked" in page_content or "blocked" in page_content.lower():
                print("   -> ACCESS BLOCKED detected after search.")
                await page.screenshot(path="cma_blocked.png")
                await browser.close()
                return {
                    "source": "CMA CGM Official",
                    "container": container_number,
                    "status": "Blocked",
                    "raw_data": "Access blocked by WAF. Consider using a residential proxy."
                }
            
            # 10. Extract tracking results
            print("   -> Extracting tracking data...")
            
            # Look for result containers
            result_selectors = [
                ".tracking-result",
                ".shipment-details",
                ".container-info",
                "[data-testid='tracking-result']",
                ".result-container",
                "table.tracking",
                ".tracking-table"
            ]
            
            result_content = None
            for sel in result_selectors:
                try:
                    if await page.locator(sel).first.is_visible(timeout=2000):
                        result_content = await page.locator(sel).first.inner_text()
                        print(f"   -> Found result container: {sel}")
                        break
                except:
                    continue
            
            if not result_content:
                # Fallback: get the main content area
                try:
                    result_content = await page.inner_text("main")
                except:
                    result_content = await page.inner_text("body")
            
            # Check for "not found" type messages
            error_indicators = [
                "not found",
                "no results",
                "invalid",
                "no tracking",
                "no data"
            ]
            
            if any(indicator in result_content.lower() for indicator in error_indicators):
                print("   -> Container not found in CMA system.")
                await browser.close()
                return {
                    "source": "CMA CGM Official",
                    "container": container_number,
                    "status": "Not Found",
                    "raw_data": result_content[:500] if result_content else "No tracking data found"
                }
            
            # Take a screenshot for debugging
            await page.screenshot(path="cma_result.png")
            
            await browser.close()
            
            print(f"   -> Successfully extracted {len(result_content)} characters of tracking data")
            
            return {
                "source": "CMA CGM Official",
                "container": container_number,
                "raw_data": result_content
            }

        except Exception as e:
            print(f"   -> CMA Driver Error: {e}")
            try:
                await page.screenshot(path="cma_error.png")
            except:
                pass
            
            try:
                await browser.close()
            except:
                pass
            
            # Return None to allow fallback to manual check message
            return None
