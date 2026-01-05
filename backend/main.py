import sys
import asyncio

# --- CRITICAL FIX FOR WINDOWS + PLAYWRIGHT ---
# This must run before anything else to allow the browser to launch
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
# ---------------------------------------------

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

# --- AIR DRIVERS (Commented Out) ---
# from services.air.air_india import drive_air_india
# from services.air.china_airlines import drive_china_airlines
# from services.air.silk_way import drive_silk_way
# from services.air.af_klm import drive_af_klm
# from services.air.etihad import drive_etihad
# from services.air.saudia import drive_saudia

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
        scrape_data = await drive_hmm(request.number)
    
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
        "message": "Container not found in API, and no Official Driver available."
    }

# --- AIR ENDPOINT (Commented Out) ---
# @app.post("/api/track/air")
# async def track_air(request: TrackRequest):
#     clean = request.number.replace(" ", "").replace("-", "")
#     prefix = clean[:3]
#     scrape_data = None
    
#     if prefix == "098": scrape_data = await drive_air_india(request.number)
#     elif prefix == "297": scrape_data = await drive_china_airlines(request.number)
#     elif prefix in ["501", "463"]: scrape_data = await drive_silk_way(request.number)
#     elif prefix in ["057", "074"]: scrape_data = await drive_af_klm(request.number)
#     elif prefix == "607": scrape_data = await drive_etihad(request.number)
#     elif prefix == "065": scrape_data = await drive_saudia(request.number)
    
#     if scrape_data and scrape_data.get("raw_data"):
#         ai_result = await parse_tracking_data(scrape_data["raw_data"], request.carrier)
#         return {
#             "tracking_number": request.number,
#             "carrier": request.carrier,
#             "status": ai_result.get("status"),
#             "live_eta": ai_result.get("latest_date"),
#             "smart_summary": ai_result.get("summary"),
#             "raw_data_snippet": "Source: Official Driver"
#         }

#     return {
#         "source": "System",
#         "status": "Not Found",
#         "message": "AWB not found or Driver not implemented."
#     }