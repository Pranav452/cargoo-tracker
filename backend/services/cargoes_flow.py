import os
import httpx
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_URL = os.getenv("CARGOES_FLOW_API_URL")
API_KEY = os.getenv("CARGOES_FLOW_API_KEY")
ORG_TOKEN = os.getenv("CARGOES_FLOW_ORG_TOKEN")

async def get_sea_shipment(container_number: str):
    """
    Fetches Sea/Intermodal shipment data from Cargoes Flow API.
    Returns structured dict or None if not found/error.
    """
    if not API_KEY or not ORG_TOKEN:
        print("❌ Error: Missing API Keys in .env")
        return None

    # Clean the input (Standardize to Upper Case, No Spaces/Dashes)
    clean_number = container_number.upper().replace(" ", "").replace("-", "")
    print(f"🌊 API Request: {clean_number}")

    headers = {
        "X-DPW-ApiKey": API_KEY,
        "X-DPW-Org-Token": ORG_TOKEN,
        "Content-Type": "application/json",
        # Mimic a browser to avoid Cloudflare blocks
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    params = {
        "shipmentType": "INTERMODAL_SHIPMENT",
        "containerNumber": clean_number,
        "includeUniqueContainers": "true",
        "_limit": "20"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_URL, headers=headers, params=params, timeout=15.0)

            if response.status_code == 200:
                data = response.json()
                
                # Check if we got a valid list response
                if isinstance(data, list) and len(data) > 0:
                    shipment = data[0] # Take the first match
                    
                    # --- DATA EXTRACTION ---
                    # 1. CO2 Emissions
                    co2_val = shipment.get("emissions", {}).get("co2e", {}).get("value")
                    co2_unit = shipment.get("emissions", {}).get("co2e", {}).get("unit", "kg")
                    co2_str = f"{co2_val} {co2_unit}" if co2_val else "N/A"

                    # 2. Arrival Date (ETA)
                    # We check 'destinationOceanPortEta' first, then 'promisedEta'
                    eta = shipment.get("destinationOceanPortEta") or shipment.get("promisedEta") or "N/A"

                    # 3. Status Summary
                    # We construct a raw summary for the AI to polish later
                    status = shipment.get("status", "Unknown")
                    sub_status = shipment.get("subStatus1", "")
                    
                    print(f"✅ API Success for {clean_number}")
                    
                    return {
                        "source": "Cargoes Flow API",
                        "container": clean_number,
                        "carrier": shipment.get("carrierScac") or "Unknown",
                        "eta": eta,
                        "co2": co2_str,
                        "status": status,
                        "sub_status": sub_status,
                        "raw_data": shipment # Keep full data for AI analysis
                    }
                else:
                    print(f"🔸 API returned 200 but no data for {clean_number}")
                    return None
            
            elif response.status_code == 404:
                print(f"🔸 Not Found in API (404)")
                return None
            
            elif response.status_code == 401:
                print("⛔ API Authorization Failed (Check .env keys)")
                return None
            
            else:
                print(f"⚠️ API Error {response.status_code}: {response.text}")
                return None

    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return None