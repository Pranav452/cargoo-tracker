from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Import Services
from services.cargoes_flow import get_sea_shipment
from services.sea.msc import drive_msc # <--- MSC Driver

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
    carrier: str = "Unknown" # We need to know the carrier to pick the driver

@app.post("/api/track/sea")
async def track_sea(request: TrackRequest):
    # 1. TIER 1: Cargoes Flow API
    data = await get_sea_shipment(request.number)
    if data:
        return data
    
    # 2. TIER 2: Custom Drivers (Official Sites)
    print("   🐢 API didn't have data. Switching to Official Driver...")
    
    carrier_name = request.carrier.lower()
    scrape_data = None

    # Routing Logic
    if "msc" in carrier_name:
        scrape_data = await drive_msc(request.number)
    
    # We will add elif "hapag" ... elif "cma" ... later

    if scrape_data:
        return scrape_data

    return {
        "source": "System",
        "status": "Not Found",
        "message": f"Container not found in API, and no driver exists for '{request.carrier}' yet."
    }