import sys
import asyncio

# --- WINDOWS FIX (Must be at the top for Uvicorn) ---
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- SERVICES ---
from services.hmm_session import hmm_session 

from services.cargoes_flow import get_sea_shipment
from services.ai_service import parse_tracking_data

# --- SEA DRIVERS ---
from services.sea.msc import drive_msc
from services.sea.hapag import drive_hapag
from services.sea.cma import drive_cma
# We will update hmm to use the browser manager
# from services.sea.hmm import drive_hmm 

app = FastAPI(title="MP Cargo V2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LIFECYCLE EVENTS (Keep Browser Open) ---
@app.on_event("startup")
async def startup_event():
    print("🌟 Server Starting... Warming up HMM Browser...")
    await hmm_session.start()

@app.on_event("shutdown")
async def shutdown_event():
    print("💤 Server Stopping... Closing Browser...")
    await hmm_session.close()

class TrackRequest(BaseModel):
    number: str
    carrier: str = "Unknown"

# --- SEA ENDPOINT ---
@app.post("/api/track/sea")
async def track_sea(request: TrackRequest):
    # 1. API Check
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
    
    # 2. Driver Check
    print("   🐢 API didn't have data. Switching to Official Driver...")
    carrier_name = request.carrier.lower()
    scrape_data = None

    if "msc" in carrier_name:
        scrape_data = await drive_msc(request.number)
    elif "hapag" in carrier_name:
        scrape_data = await drive_hapag(request.number)
    elif "cma" in carrier_name:
        scrape_data = await drive_cma(request.number)
    elif "hmm" in carrier_name or "hyundai" in carrier_name:
        # Import here to avoid circular imports if modified
        from services.sea.hmm import drive_hmm_persistent
        scrape_data = await drive_hmm_persistent(request.number)
    
    # 3. AI Analysis
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

    return {
        "source": "System",
        "status": "Not Found",
        "message": "Container not found in API or Driver."
    }

# --- AIR ENDPOINT ---
@app.post("/api/track/air")
async def track_air(request: TrackRequest):
    # Keep your existing Air logic here or return Not Implemented for now
    return {
        "source": "System",
        "status": "Pending",
        "message": "Air tracking under maintenance."
    }