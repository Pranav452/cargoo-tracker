from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- SERVICES ---
from services.cargoes_flow import get_sea_shipment
from services.ai_service import parse_tracking_data

# --- SEA DRIVERS ---
from services.sea.msc import drive_msc
from services.sea.hapag import drive_hapag
from services.sea.cma import drive_cma
from services.sea.hmm import drive_hmm

app = FastAPI(title="MP Cargo V2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class TrackRequest(BaseModel):
    number: str
    carrier: str = "Unknown"

@app.post("/api/track/sea")
async def track_sea(request: TrackRequest):
    # ---------------------------------------------------------
    # TIER 1: CARGOES FLOW API (The Fast Lane)
    # ---------------------------------------------------------
    data = await get_sea_shipment(request.number)
    if data:
        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": data.get("status"),
            "live_eta": data.get("eta"),
            "smart_summary": f"API Status: {data.get('sub_status')}. CO2: {data.get('co2')}",
            "raw_data_snippet": "Source: Cargoes Flow API"
        }

    # ---------------------------------------------------------
    # TIER 2: OFFICIAL DRIVERS (The Custom Scripts)
    # ---------------------------------------------------------
    print("   🐢 API didn't have data. Switching to Official Driver...")

    carrier_name = request.carrier.lower()
    scrape_data = None

    # Routing Logic
    if "msc" in carrier_name:
        scrape_data = await drive_msc(request.number)
    elif "hapag" in carrier_name:
        scrape_data = await drive_hapag(request.number)
    elif "cma" in carrier_name:
        scrape_data = await drive_cma(request.number)
    elif "hmm" in carrier_name or "hyundai" in carrier_name:
        scrape_data = await drive_hmm(request.number)

    # ---------------------------------------------------------
    # AI PARSING & RESPONSE
    # ---------------------------------------------------------
    if scrape_data and scrape_data.get("raw_data"):
        print("   🧠 Sending raw text to AI for analysis...")

        ai_result = await parse_tracking_data(scrape_data["raw_data"], request.carrier)

        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": ai_result.get("status"),
            "live_eta": ai_result.get("latest_date"),
            "smart_summary": ai_result.get("summary"),
            "raw_data_snippet": "Source: Official Driver"
        }

    # If API failed AND Driver failed/doesn't exist
    return {
        "source": "System",
        "status": "Not Found",
        "message": "Container not found in API, and no Official Driver available."
    }