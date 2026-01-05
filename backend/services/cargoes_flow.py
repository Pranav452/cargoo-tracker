import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

API_BASE_URL = "https://connect.cargoes.com/flow/api/public_tracking/v1/shipments"
API_KEY = os.getenv("CARGOES_FLOW_API_KEY", "").strip()
ORG_TOKEN = os.getenv("CARGOES_FLOW_ORG_TOKEN", "").strip()

async def check_cargoes_flow(tracking_number: str, carrier_type: str):
    if not API_KEY or not ORG_TOKEN: return None

    clean_number = tracking_number.replace(" ", "").replace("-", "")
    print(f"   ⚡ API: Checking Cargoes Flow for {clean_number}...")

    params = {
        "shipmentType": "INTERMODAL_SHIPMENT" if carrier_type == "sea" else "AIR_SHIPMENT",
        "containerNumber" if carrier_type == "sea" else "awbNumber": clean_number,
        "includeUniqueContainers": "true",
        "_limit": "50"
    }

    headers = {
        "X-DPW-ApiKey": API_KEY,
        "X-DPW-Org-Token": ORG_TOKEN,
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(API_BASE_URL, params=params, headers=headers, timeout=20.0)

            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    shipment = data[0]
                    
                    # --- DEEP EXTRACTION STRATEGY ---
                    shipment_legs = shipment.get("shipmentLegs", {})
                    legs = shipment_legs.get("portToPort", {}) if isinstance(shipment_legs, dict) else {}
                    
                    # 1. Hunt for the REAL ETA (It hides in different places)
                    eta = (
                        legs.get("destinationOceanPortEta") or 
                        legs.get("lastPortEta") or 
                        legs.get("dischargePortEta") or
                        shipment.get("promisedEta") or 
                        "N/A"
                    )

                    # 2. Hunt for the REAL Status
                    # Sometimes main status is just "ACTIVE", we want "Vessel Departure"
                    events = shipment.get("shipmentEvents", [])
                    latest_event = (events[0].get("name") if isinstance(events, list) and len(events) > 0 and isinstance(events[0], dict) else None) or shipment.get("subStatus1")

                    # 3. Format Emissions
                    co2_val = shipment.get("emissions", {}).get("co2e", {}).get("value")
                    co2 = f"{float(co2_val):.2f} kg" if co2_val else "N/A"

                    # 4. Construct a Clean Summary for the AI
                    # We pre-digest the data so the AI doesn't have to guess
                    summary_data = {
                        "container": clean_number,
                        "carrier": shipment.get("carrierScac"),
                        "origin": legs.get("firstPort"),
                        "destination": legs.get("lastPort"),
                        "eta_raw": eta,
                        "latest_event": latest_event,
                        "co2": co2
                    }
                    
                    print(f"   ✅ API Success! Found ETA: {eta}")
                    return json.dumps(summary_data, indent=2)
                else:
                    print("   🔸 API returned 200 but list is empty.")
                    return None
            else:
                print(f"   🔸 API Error {response.status_code}")
                return None

    except Exception as e:
        print(f"   ⚠️ API Connection Failed: {e}")
        return None

# Backward compatibility wrapper
async def get_sea_shipment(container_number: str):
    """
    Wrapper for backward compatibility with main.py
    Calls check_cargoes_flow and converts JSON string to dict format
    """
    result = await check_cargoes_flow(container_number, "sea")
    if result:
        try:
            data = json.loads(result)
            # Convert to expected dict format for main.py
            return {
                "source": "Cargoes Flow API",
                "container": data.get("container"),
                "carrier": data.get("carrier") or "Unknown",
                "eta": data.get("eta_raw", "N/A"),
                "co2": data.get("co2", "N/A"),
                "status": data.get("latest_event") or "Unknown",
                "sub_status": data.get("latest_event", ""),
                "raw_data": data
            }
        except json.JSONDecodeError:
            return None
    return None
