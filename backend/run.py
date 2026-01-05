import uvicorn
import sys
import asyncio

if __name__ == "__main__":
    # 1. FORCE WINDOWS TO SUPPORT BROWSERS
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    print("🚀 Starting Server in Windows Mode...")
    
    # 2. RUN WITHOUT RELOAD (Required for Windows+Playwright stability)
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=False  # <--- MUST BE FALSE ON WINDOWS FOR PLAYWRIGHT
    )