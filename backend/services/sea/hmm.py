import asyncio
import re
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS

async def drive_hmm(container_number: str):
    """
    Official HMM Driver - Network-Only Mode
    Strategy: Block ALL resources (CSS/JS/IMG). Download HTML text only.
    Extract Token via Regex. Fire API.
    """
    print(f"🚢 [HMM] Native API Tracking: {container_number}")
    
    async with async_playwright() as p:
        # USE "NEW" HEADLESS MODE (Harder to detect than standard headless)
        # We append it to args instead of using the headless=True flag
        custom_args = STEALTH_ARGS + [
            "--headless=new", 
            "--disable-http2", 
            "--disable-gpu",
            "--no-zygote"
        ]
        
        # Note: We set headless=False in the function call, but pass --headless=new in args.
        # This is a known trick to bypass detection.
        browser = await p.chromium.launch(
            headless=False,  
            args=custom_args
        )
        
        context = await browser.new_context(ignore_https_errors=True)
        
        # --- CRITICAL: BLOCK EVERYTHING ---
        # We abort loading anything that isn't the main HTML document.
        # This prevents the "Timeout" because we don't load the heavy site.
        await context.route("**/*", lambda route: route.continue_() 
            if route.request.resource_type == "document" 
            else route.abort()
        )

        page = await context.new_page()

        try:
            # 1. Get the HTML Source (Fast)
            print("   -> Fetching HMM Source Code (No Rendering)...")
            response = await page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=30000, wait_until="commit")
            
            # Wait a tiny bit for the response body to be available
            await asyncio.sleep(2)
            
            # Get raw HTML text
            html_content = await page.content()
            
            # 2. Extract Token using Regex (No Selectors)
            # Looking for: <meta name="_csrf" content="UUID"/>
            token = ""
            match = re.search(r'name="_csrf"\s+content="([^"]+)"', html_content)
            if match:
                token = match.group(1)
                # print(f"   -> Token found via Regex: {token[:10]}...")
            else:
                print("   ⚠️ Token not found in HTML. Trying without...")

            # 3. Construct API Request
            api_url = "https://www.hmm21.com/e-service/general/trackNTrace/selectTrackNTrace.do"
            
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "X-CSRF-TOKEN": token,
                "X-Requested-With": "XMLHttpRequest"
            }

            payload = {
                "type": "cntr",
                "listBl": [],
                "listCntr": [container_number],
                "listBkg": [],
                "listPo": []
            }

            # 4. Send Request via Browser Context
            print("   -> Sending API Request...")
            api_response = await context.request.post(api_url, headers=headers, data=payload)
            
            if api_response.status == 200:
                content = await api_response.text()
                
                if "No Data" in content or len(content) < 200:
                    print("   -> API returned success but empty data.")
                
                print(f"   ✅ Success! Retrieved {len(content)} chars.")
                await browser.close()
                
                return {
                    "source": "HMM Official (Native API)",
                    "container": container_number,
                    "raw_data": content
                }
            else:
                print(f"   ❌ API Failed: {api_response.status}")
                await browser.close()
                return None

        except Exception as e:
            print(f"   ❌ HMM Driver Failed: {e}")
            await browser.close()
            return None