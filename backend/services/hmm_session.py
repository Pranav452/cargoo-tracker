import asyncio
import re
import json
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS

class HMMSession:
    _instance = None

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.csrf_token = None
        self.cookie_header = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = HMMSession()
        return cls._instance

    async def start(self):
        """Launches the browser and gets the HMM Token ONCE."""
        if self.browser:
            return

        print("   🚀 STARTING PERSISTENT HMM SESSION...")
        self.playwright = await async_playwright().start()
        
        # HEADLESS=FALSE (Visual Mode)
        self.browser = await self.playwright.chromium.launch(
            headless=False, 
            args=STEALTH_ARGS + ["--disable-http2"]
        )
        
        self.context = await self.browser.new_context(ignore_https_errors=True)
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.page = await self.context.new_page()
        
        # Navigate and Get Token
        try:
            print("   🔄 Fetching HMM Token (One-time setup)...")
            await self.page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=60000, wait_until="domcontentloaded")
            
            # Wait for Token
            try:
                await self.page.wait_for_selector("meta[name='_csrf']", state="attached", timeout=15000)
                self.csrf_token = await self.page.locator("meta[name='_csrf']").get_attribute("content")
                print(f"   ✅ Token Acquired: {self.csrf_token[:10]}...")
            except:
                print("   ⚠️ Token not in DOM. Checking HTML...")
                content = await self.page.content()
                match = re.search(r'name="_csrf"\s+content="([^"]+)"', content)
                if match: 
                    self.csrf_token = match.group(1)
                    print(f"   ✅ Token Acquired via Regex.")
        except Exception as e:
            print(f"   ❌ Failed to initialize HMM Session: {e}")

    async def fetch_data(self, container_number):
        """Uses the existing page to fetch data without reloading."""
        if not self.page or not self.csrf_token:
            print("   ⚠️ Session lost. Restarting...")
            await self.close()
            await self.start()

        print(f"   ⚡ Fast Fetching: {container_number}")
        
        api_url = "/e-service/general/trackNTrace/selectTrackNTrace.do"
        
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
        
        return await self.page.evaluate(js_code, {
            "url": api_url,
            "token": self.csrf_token,
            "container": container_number
        })

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        self.browser = None
        self.csrf_token = None

# Global Singleton
hmm_session = HMMSession.get_instance()