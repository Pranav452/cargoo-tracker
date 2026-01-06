import asyncio
from playwright.async_api import async_playwright
from services.utils import STEALTH_ARGS

class BrowserManager:
    _instance = None
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.hmm_token = None
        self.is_initialized = False

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = BrowserManager()
        return cls._instance

    async def initialize(self):
        if self.is_initialized:
            return

        print("   🚀 STARTING PERSISTENT BROWSER (GOD MODE)...")
        self.playwright = await async_playwright().start()
        
        # HEADLESS=FALSE so you can see it working
        self.browser = await self.playwright.chromium.launch(
            headless=False, 
            args=STEALTH_ARGS + ["--disable-http2"]
        )
        
        self.context = await self.browser.new_context(
            ignore_https_errors=True,
            viewport={'width': 1920, 'height': 1080}
        )
        
        # Inject stealth
        await self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        self.page = await self.context.new_page()
        self.is_initialized = True
        
        # Pre-load HMM Session immediately on startup
        await self.refresh_hmm_session()

    async def refresh_hmm_session(self):
        print("   🔄 Refreshing HMM Session & Token...")
        try:
            await self.page.goto("https://www.hmm21.com/e-service/general/trackNTrace/TrackNTrace.do", timeout=60000, wait_until="domcontentloaded")
            
            # Wait for CSRF
            try:
                await self.page.wait_for_selector("meta[name='_csrf']", state="attached", timeout=10000)
                self.hmm_token = await self.page.locator("meta[name='_csrf']").get_attribute("content")
                print(f"   ✅ HMM Token Acquired: {self.hmm_token[:10]}...")
            except:
                print("   ⚠️ Could not get HMM Token via DOM.")
        except Exception as e:
            print(f"   ❌ Failed to refresh HMM session: {e}")

    async def get_page(self):
        if not self.is_initialized:
            await self.initialize()
        return self.page

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

# Global Instance
browser_manager = BrowserManager.get_instance()