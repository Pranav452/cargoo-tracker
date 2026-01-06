import asyncio
import re
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS

async def drive_hmm(container_number: str):
    """
    Official HMM Driver - DOM Fetch Strategy
    Executes the API call INSIDE the browser context using JavaScript.
    This bypasses UI clicking issues AND Firewall/TLS fingerprinting.
    """
    print(f"🚢 [HMM] Native API Tracking (DOM Fetch): {container_number}")
    
    async with async_playwright() as p:
        # Keep headless=False so it looks like a real user (God Mode)
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
            # 1. Load Page to establish session & get Cookies
            print("   -> Fetching HMM Session...")
            await page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=60000, wait_until="domcontentloaded")
            
            # Wait for CSRF token to be present in DOM
            try:
                await page.wait_for_selector("meta[name='_csrf']", state="attached", timeout=15000)
            except:
                pass

            # 2. Get Token
            token = await page.locator("meta[name='_csrf']").get_attribute("content")
            
            # Fallback to HTML regex if DOM fails
            if not token:
                print("   ⚠️ Token not found in DOM. Checking HTML source...")
                content = await page.content()
                match = re.search(r'name="_csrf"\s+content="([^"]+)"', content)
                if match: token = match.group(1)
            
            if not token:
                print("   ❌ Fatal: Could not find CSRF Token.")
                await browser.close()
                return None

            # 3. INJECT JAVASCRIPT FETCH
            # This runs inside the browser page, sharing all cookies and fingerprint
            print(f"   -> Executing Browser Fetch with Token: {token[:10]}...")
            
            api_url = "/e-service/general/trackNTrace/selectTrackNTrace.do"
            
            # We define the payload and headers in Python, then pass to JS
            js_code = """
                async ({ url, token, container }) => {
                    try {
                        const response = await fetch(url, {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json; charset=UTF-8',
                                'X-CSRF-TOKEN': token,
                                'X-Requested-With': 'XMLHttpRequest'
                            },
                            body: JSON.stringify({
                                "type": "cntr",
                                "listBl": [],
                                "listCntr": [container],
                                "listBkg": [],
                                "listPo": []
                            })
                        });
                        return await response.text();
                    } catch (err) {
                        return "JS_ERROR: " + err.toString();
                    }
                }
            """
            
            # Execute the JS
            content = await page.evaluate(js_code, {
                "url": api_url,
                "token": token,
                "container": container_number
            })
            
            # Check response
            if "JS_ERROR" in content:
                print(f"   ❌ Browser Fetch Error: {content}")
                await browser.close()
                return None
            
            if "No Data" in content or len(content) < 200:
                 print("   -> API returned empty/short data.")
            else:
                 print(f"   ✅ Success! Retrieved {len(content)} chars via JS.")

            await browser.close()
            
            return {
                "source": "HMM Official (JS Fetch)",
                "container": container_number,
                "raw_data": content
            }

        except Exception as e:
            print(f"   ❌ HMM Driver Failed: {e}")
            await browser.close()
            return None