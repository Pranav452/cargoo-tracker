from services.hmm_session import hmm_session

async def drive_hmm(container_number: str):
    """
    Official HMM Driver - Persistent Mode
    Uses the globally open browser session.
    """
    try:
        # Ensure session is running
        await hmm_session.start()
        
        # Fetch data using existing token
        content = await hmm_session.fetch_data(container_number)
        
        if not content or "JS_ERROR" in content or "No Data" in content:
            # Maybe token expired? Try one refresh
            print("   ⚠️ Fetch failed. Refreshing session...")
            await hmm_session.refresh_hmm_session() # Or restart
            content = await hmm_session.fetch_data(container_number)

        return {
            "source": "HMM Official (Persistent)",
            "container": container_number,
            "raw_data": content
        }

    except Exception as e:
        print(f"   ❌ HMM Driver Failed: {e}")
        return None