from services.browser_manager import browser_manager

async def drive_hmm_batch(container_list: list):
    """
    HMM Driver - Batch Mode via Persistent Browser
    """
    print(f"🚢 [HMM] Batch Tracking {len(container_list)} containers...")
    
    # Ensure browser is ready
    page = await browser_manager.get_page()
    token = browser_manager.hmm_token
    
    if not token:
        await browser_manager.refresh_hmm_session()
        token = browser_manager.hmm_token

    if not token:
        return {"error": "Could not acquire HMM Token"}

    # INJECT JS FETCH (Batch)
    api_url = "/e-service/general/trackNTrace/selectTrackNTrace.do"
    
    js_code = """
        async ({ url, token, containers }) => {
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
                        "listCntr": containers, # SENDING THE FULL LIST
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
    
    # Execute
    content = await page.evaluate(js_code, {
        "url": api_url,
        "token": token,
        "containers": container_list
    })
    
    if "JS_ERROR" in content or "No Data" in content:
        print("   ❌ HMM Batch Failed or Empty")
        return None
        
    print(f"   ✅ HMM Batch Success! Received {len(content)} chars.")
    return content