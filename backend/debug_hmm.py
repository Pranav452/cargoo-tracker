import asyncio
import json
from playwright.async_api import async_playwright

CONTAINER_NUM = "KOCU4353105"

async def test_hmm_native_api():
    print(f"🕵️ STARTING PLAYWRIGHT NATIVE API DEBUG: {CONTAINER_NUM}")
    
    async with async_playwright() as p:
        # 1. Launch Browser
        # We disable HTTP2 to match the successful navigation settings
        browser = await p.chromium.launch(
            headless=False, 
            args=["--disable-http2"]
        )
        context = await browser.new_context(ignore_https_errors=True)
        page = await context.new_page()

        try:
            # 2. Navigate (Pass Firewall & Get Session)
            print("   -> Navigating to HMM...")
            await page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=60000)
            
            # 3. Get Token
            csrf_element = page.locator("meta[name='_csrf']").first
            if await csrf_element.count() == 0:
                print("   ❌ Token not found.")
                await browser.close()
                return
            
            token = await csrf_element.get_attribute("content")
            print(f"   ✅ Token Found: {token[:10]}...")

            # 4. Use Playwright's Native API Request (Shares Browser Context)
            print("   🚀 Sending POST via Browser Context...")
            
            api_url = "https://www.hmm21.com/e-service/general/trackNTrace/selectTrackNTrace.do"
            
            headers = {
                "Content-Type": "application/json; charset=UTF-8",
                "X-CSRF-TOKEN": token,
                "X-Requested-With": "XMLHttpRequest"
            }

            payload = {
                "type": "cntr",
                "listBl": [],
                "listCntr": [CONTAINER_NUM],
                "listBkg": [],
                "listPo": []
            }

            # context.request shares cookies automatically!
            response = await context.request.post(api_url, headers=headers, data=payload)
            
            print(f"   -> Status: {response.status}")
            
            if response.status == 200:
                text = await response.text()
                print(f"   ✅ SUCCESS! Data Length: {len(text)}")
                print(f"   📄 Snippet: {text[:300]}...")
            else:
                print(f"   ❌ Failed: {response.status} - {await response.text()}")

            await asyncio.sleep(2)

        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"   ❌ CRASH: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_hmm_native_api())