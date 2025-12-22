from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Services
from services.cargoes_flow import get_sea_shipment
from services.ai_service import parse_tracking_data # <--- THE BRAIN
from services.sea.msc import drive_msc
from services.sea.hapag import drive_hapag
from services.sea.cma import drive_cma
from services.sea.fallback import drive_sea_fallback

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
    # TIER 1: Cargoes Flow API (Already structured, no AI needed)
    # ---------------------------------------------------------
    data = await get_sea_shipment(request.number)
    if data:
        # API returns clean JSON, so we just pass it through
        # We might want to standardize keys here to match AI output if needed
        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": data.get("status"),
            "live_eta": data.get("eta"),
            "smart_summary": f"API Status: {data.get('sub_status')}. CO2: {data.get('co2')}",
            "raw_data_snippet": "Source: Cargoes Flow API"
        }
    
    # ---------------------------------------------------------
    # TIER 2: Custom Drivers (Returns MESSY Raw Text)
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
    
    # ---------------------------------------------------------
    # TIER 3: Universal Fallback (If Tier 2 failed or no driver)
    # ---------------------------------------------------------
    if not scrape_data:
        print("   ⚓ Driver missing or failed. Using Universal Fallback...")
        scrape_data = await drive_sea_fallback(request.number)

    # ---------------------------------------------------------
    # THE AI STEP (Cleaning the Mess)
    # ---------------------------------------------------------
    if scrape_data and scrape_data.get("raw_data"):
        print("   🧠 Sending raw text to AI for analysis...")
        
        # THIS IS THE MISSING PIECE
        ai_result = await parse_tracking_data(scrape_data["raw_data"], request.carrier)
        
        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": ai_result.get("status"),
            "live_eta": ai_result.get("latest_date"),
            "smart_summary": ai_result.get("summary"),
            "raw_data_snippet": scrape_data["raw_data"][:200] + "..."
        }

    return {
        "source": "System",
        "status": "Not Found",
        "message": f"Container not found in API, Driver, or Fallback."
    }