import uvicorn
import sys
import asyncio

if __name__ == "__main__":
    # CRITICAL FIX: Forces Windows to allow the browser to open
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # Run the server programmatically
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True
    )