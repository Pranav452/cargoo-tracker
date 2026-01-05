"""
Wrapper script to ensure Windows event loop policy is set before uvicorn starts.
Run this instead of: uvicorn main:app --reload
"""
import sys
import asyncio

# CRITICAL: Set event loop policy BEFORE any event loop is created
if sys.platform.startswith("win"):
    if hasattr(asyncio, 'WindowsSelectorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        print("✓ Windows event loop policy set for Playwright compatibility")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)


