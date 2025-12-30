import asyncio
import random
import os

# Enhanced Stealth Args to make Headless Chrome look like a real browser
STEALTH_ARGS = [
    '--disable-blink-features=AutomationControlled',
    '--disable-infobars',
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--window-size=1920,1080',
    '--disable-dev-shm-usage',
    '--disable-accelerated-2d-canvas',
    '--disable-gpu',
    '--lang=en-US,en',
]

# Realistic Chrome user agent
CHROME_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Navigator override script to remove automation detection
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});

Object.defineProperty(navigator, 'plugins', {
    get: () => [
        { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer', description: 'Portable Document Format' },
        { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: '' },
        { name: 'Native Client', filename: 'internal-nacl-plugin', description: '' }
    ]
});

Object.defineProperty(navigator, 'languages', {
    get: () => ['en-US', 'en']
});

Object.defineProperty(navigator, 'platform', {
    get: () => 'Win32'
});

Object.defineProperty(navigator, 'hardwareConcurrency', {
    get: () => 8
});

Object.defineProperty(navigator, 'deviceMemory', {
    get: () => 8
});

window.chrome = {
    runtime: {},
    loadTimes: function() {},
    csi: function() {},
    app: {}
};

Object.defineProperty(navigator, 'permissions', {
    get: () => ({
        query: async (params) => ({ state: 'granted', onchange: null })
    })
});

// Override WebGL vendor and renderer
const getParameterProxyHandler = {
    apply: function(target, thisArg, argumentsList) {
        const param = argumentsList[0];
        const gl = thisArg;
        if (param === 37445) { // UNMASKED_VENDOR_WEBGL
            return 'Google Inc. (NVIDIA)';
        }
        if (param === 37446) { // UNMASKED_RENDERER_WEBGL
            return 'ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)';
        }
        return Reflect.apply(target, thisArg, argumentsList);
    }
};

try {
    const canvas = document.createElement('canvas');
    const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
    if (gl) {
        gl.getParameter = new Proxy(gl.getParameter.bind(gl), getParameterProxyHandler);
    }
} catch (e) {}
"""


def get_proxy_config():
    """Returns proxy config from environment variables if set"""
    proxy_url = os.getenv("PROXY_URL")
    if proxy_url:
        return {"server": proxy_url}
    return None


async def create_stealth_context(browser):
    """
    Create a browser context with realistic fingerprinting to avoid detection.
    Includes proper headers, viewport, locale, and navigator overrides.
    """
    proxy_config = get_proxy_config()
    
    context_options = {
        "viewport": {"width": 1920, "height": 1080},
        "user_agent": CHROME_USER_AGENT,
        "locale": "en-US",
        "timezone_id": "America/New_York",
        "permissions": [],
        "extra_http_headers": {
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
            "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
        }
    }
    
    if proxy_config:
        context_options["proxy"] = proxy_config
    
    context = await browser.new_context(**context_options)
    
    # Inject stealth scripts to remove automation detection
    await context.add_init_script(STEALTH_INIT_SCRIPT)
    
    return context


async def human_delay(min_ms=1000, max_ms=3000):
    """Add random human-like delays between actions"""
    delay = random.randint(min_ms, max_ms) / 1000
    await asyncio.sleep(delay)


async def human_mouse_movement(page):
    """
    Simulate human-like mouse movements across the page.
    Moves cursor to random positions with natural pauses.
    """
    for _ in range(random.randint(2, 5)):
        x = random.randint(100, 1800)
        y = random.randint(100, 900)
        await page.mouse.move(x, y, steps=random.randint(5, 15))
        await asyncio.sleep(random.uniform(0.1, 0.3))


async def human_scroll(page, direction="down", amount=None):
    """
    Simulate human-like scrolling behavior.
    Args:
        page: Playwright page object
        direction: "down" or "up"
        amount: Scroll amount in pixels (random if None)
    """
    if amount is None:
        amount = random.randint(200, 500)
    
    if direction == "up":
        amount = -amount
    
    # Scroll in smaller increments to appear natural
    increments = random.randint(3, 6)
    per_scroll = amount // increments
    
    for _ in range(increments):
        await page.mouse.wheel(0, per_scroll)
        await asyncio.sleep(random.uniform(0.05, 0.15))
    
    await asyncio.sleep(random.uniform(0.3, 0.7))


async def random_viewport_scroll(page):
    """
    Perform random scrolling to simulate natural browsing behavior.
    Scrolls down and optionally back up a bit.
    """
    # Scroll down
    await human_scroll(page, "down", random.randint(300, 600))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    
    # Sometimes scroll back up a little
    if random.random() > 0.5:
        await human_scroll(page, "up", random.randint(50, 150))
        await asyncio.sleep(random.uniform(0.3, 0.8))

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