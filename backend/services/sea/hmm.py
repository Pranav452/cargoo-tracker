from services.browser_manager import browser_manager
from services.utils import human_type

async def drive_hmm_persistent(container_number: str):
    """
    HMM Driver using the Global Persistent Browser.
    """
    print(f"🚢 [HMM] Persistent Tracking: {container_number}")
    
    # Get the open page
    page = await browser_manager.get_page()
    
    # Ensure we have a token (refresh if needed)
    if not browser_manager.hmm_token:
        await browser_manager.refresh_hmm_session()

    token = browser_manager.hmm_token
    if not token:
        return None

    # Use the Page Context to fire the API request
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
    
    content = await page.evaluate(js_code, {
        "url": api_url,
        "token": token,
        "container": container_number
    })
    
    if "JS_ERROR" in content or "No Data" in content:
        return None
        
    return {
        "source": "HMM Official (Persistent)",
        "container": container_number,
        "raw_data": content
    }