import asyncio
import random

# Stealth Args to make Headless Chrome look like a real browser
STEALTH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-infobars',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--window-size=1920,1080',
]

async def human_type(page, selector, text):
    """
    Robust Typing: Clears field, types slowly, and VERIFIES the result.
    If typing fails (jumbled), it retries.
    """
    element = page.locator(selector)
    await element.wait_for(state="visible")
    await element.highlight()

    # Retry loop in case of jumbled text
    for attempt in range(3):
        try:
            # 1. Clear the field safely
            await element.click()
            await element.fill("") 
            # Double tap clear to be sure (Ctrl+A + Backspace)
            # await element.press("Control+A") 
            # await element.press("Backspace")

            # 2. Type Slowly (Increased delay to 150-300ms)
            for char in text:
                await element.type(char, delay=random.randint(150, 300))
            
            # 3. Verify
            # Allow a tiny moment for JS to settle
            await asyncio.sleep(0.5)
            current_value = await element.input_value()
            
            # Remove spaces/dashes for comparison
            clean_current = current_value.replace(" ", "").replace("-", "").upper()
            clean_target = text.replace(" ", "").replace("-", "").upper()

            if clean_current == clean_target:
                print(f"   ✅ Typed correctly: {current_value}")
                return # Success!
            
            print(f"   ⚠️ Typing mismatch (Attempt {attempt+1}): Got '{current_value}', Expected '{text}'. Retrying...")
            await asyncio.sleep(1)

        except Exception as e:
            print(f"   ⚠️ Typing Error: {e}")
    
    # If all attempts fail, try the brute-force 'fill' (instant paste)
    print("   ⚠️ Typing failed. Attempting brute-force fill...")
    await element.fill(text)

async def kill_cookie_banners(page):
    """Clicks 'Accept', 'Allow', or 'Agree' buttons."""
    try:
        # Common selectors for cookie consent
        selectors = [
            "#onetrust-accept-btn-handler",
            "button:has-text('Accept All')",
            "button:has-text('Allow all')",
            "button:has-text('I Agree')",
            "button:has-text('Agree')",
            ".cc-btn.cc-accept"
        ]
        for sel in selectors:
            if await page.locator(sel).first.is_visible(timeout=2000):
                print("   🍪 Cookie banner detected. Clicking...")
                await page.locator(sel).first.click()
                await asyncio.sleep(1) # Wait for banner to disappear
                return
    except:
        pass