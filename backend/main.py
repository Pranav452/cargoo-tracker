import sys
import asyncio

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# Services
from services.browser_manager import browser_manager
from services.cargoes_flow import get_sea_shipment
from services.ai_service import parse_tracking_data
from services.sea.hmm import drive_hmm_batch
# Add other drivers (MSC, Hapag) imports here as needed

app = FastAPI(title="MP Cargo V2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup Event to Launch Browser ONCE
@app.on_event("startup")
async def startup_event():
    print("🌟 Server Starting... Initializing Browser Manager...")
    await browser_manager.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    await browser_manager.close()

class BatchRequest(BaseModel):
    containers: List[dict] # [{number: "...", carrier: "..."}]

@app.post("/api/track/batch")
async def track_batch(request: BatchRequest):
    results = []
    
    # 1. SEGREGATE BY CARRIER
    hmm_containers = []
    others = []
    
    for item in request.containers:
        num = item['number']
        carrier = item['carrier'].lower()
        
        # 2. TIER 1: CARGOES FLOW API (Parallel Checks)
        # We check API for EVERYONE first.
        api_data = await get_sea_shipment(num)
        
        if api_data:
            results.append({
                "tracking_number": num,
                "carrier": item['carrier'],
                "status": api_data.get("status"),
                "live_eta": api_data.get("eta"),
                "smart_summary": f"API Status: {api_data.get('sub_status')}. CO2: {api_data.get('co2')}",
                "source": "Cargoes Flow API"
            })
            continue # Done with this one
        
        # If API failed, sort into buckets for drivers
        if "hmm" in carrier or "hyundai" in carrier:
            hmm_containers.append(num)
        else:
            others.append(num) # MSC, Hapag, etc need individual loops later

    # 3. TIER 2: BATCH DRIVERS
    
    # --- HMM BATCH ---
    if hmm_containers:
        raw_html = await drive_hmm_batch(hmm_containers)
        if raw_html:
            # We pass the BULK HTML to AI to parse specific numbers
            # Note: For production, we might want to split the HTML per container using BeautifulSoup
            # For now, we let AI parse it per container (might be token heavy)
            for num in hmm_containers:
                 # In a real batch, we'd parse the HTML locally to find the specific row for 'num'
                 # But for now, let's just send the whole table to AI for that number
                 ai_result = await parse_tracking_data(raw_html, "HMM")
                 results.append({
                    "tracking_number": num,
                    "carrier": "HMM",
                    "status": ai_result.get("status"),
                    "live_eta": ai_result.get("latest_date"),
                    "smart_summary": ai_result.get("summary"),
                    "source": "HMM Official (Batch)"
                 })
        else:
            # Mark all as failed
            for num in hmm_containers:
                results.append({"tracking_number": num, "status": "Error", "summary": "HMM Batch Failed"})

    # --- OTHERS (Individual Drivers) ---
    # You can loop through 'others' here and call drive_msc / drive_hapag one by one
    for num in others:
         results.append({"tracking_number": num, "status": "Not Found", "summary": "No driver or API data"})

    return results