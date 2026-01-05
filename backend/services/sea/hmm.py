import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS

async def drive_hmm(container_number: str):
    """
    Official HMM Driver - Native API Mode (Visible)
    """
    print(f"🚢 [HMM] Native API Tracking: {container_number}")
    
    async with async_playwright() as p:
        # Use headful mode for local debugging
        browser = await p.chromium.launch(
            headless=False,
            args=STEALTH_ARGS + ["--disable-http2"]
        )
        
        context = await browser.new_context(ignore_https_errors=True)
        
        # Inject stealth script
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()

        try:
            # 1. Navigate to get Session
            print("   -> Navigating to HMM...")
            await page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=60000)
            
            # 2. Get Token
            try:
                csrf_element = page.locator("meta[name='_csrf']").first
                await csrf_element.wait_for(state="attached", timeout=5000)
                token = await csrf_element.get_attribute("content")
            except:
                print("   ⚠️ Token not found in DOM. Trying HTML regex...")
                import re
                html = await page.content()
                match = re.search(r'name="_csrf"\s+content="([^"]+)"', html)
                token = match.group(1) if match else ""

            # 3. Send API Request via Browser Context
            print("   -> Sending API Request...")
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

            response = await context.request.post(api_url, headers=headers, data=payload)
            
            if response.status == 200:
                content = await response.text()
                await browser.close()
                return {
                    "source": "HMM Official",
                    "container": container_number,
                    "raw_data": content
                }
            else:
                await browser.close()
                return None

        except Exception as e:
            print(f"   ❌ HMM Failed: {e}")
            await browser.close()
            return None