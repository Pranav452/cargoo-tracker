from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# --- SERVICES ---
from services.cargoes_flow import get_sea_shipment
from services.ai_service import parse_tracking_data
from services.date_utils import standardize_date, dates_are_equal, calculate_date_difference, get_date_range
from services.holiday_utils import get_holidays_between_dates, format_holidays_for_summary

# --- SEA DRIVERS ---
from services.sea.msc import drive_msc
from services.sea.hapag import drive_hapag
from services.sea.cma import drive_cma
from services.sea.hmm import drive_hmm
from services.sea.evergreen import drive_evergreen

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
    system_eta: str = "N/A"


@app.get("/health")
async def health_check():
    """
    Lightweight health endpoint for frontend connectivity status.
    """
    return {"status": "ok", "version": "v2.0"}

@app.post("/api/track/sea")
async def track_sea(request: TrackRequest):
    # ---------------------------------------------------------
    # TIER 1: CARGOES FLOW API (The Fast Lane)
    # ---------------------------------------------------------
    data = await get_sea_shipment(request.number)
    if data:
        live_eta = data.get("eta", "N/A")
        co2 = data.get("co2", "N/A")
        status = data.get("status")
        sub_status = data.get("sub_status", "")
        
        # Standardize system ETA if provided
        system_eta_standardized = standardize_date(request.system_eta)
        
        # Compare ETAs
        eta_changed = not dates_are_equal(request.system_eta, live_eta)
        
        # Calculate holidays if ETA changed
        holidays_info = "No holidays between dates"
        if eta_changed:
            start_date, end_date = get_date_range(request.system_eta, live_eta)
            if start_date and end_date:
                holidays = get_holidays_between_dates(start_date, end_date)
                holidays_info = format_holidays_for_summary(holidays)
        
        # Generate smart summary using AI if ETA changed, otherwise simple summary
        if eta_changed and data.get("raw_data"):
            print("   🧠 ETA changed - generating detailed AI summary...")
            # Use AI to generate enhanced summary
            ai_result = await parse_tracking_data(
                str(data.get("raw_data")),
                request.carrier,
                system_eta=system_eta_standardized,
                live_eta=live_eta,
                holidays_info=holidays_info
            )
            smart_summary = ai_result.get("summary", f"Status: {sub_status}")
        else:
            # Simple summary for unchanged ETA
            smart_summary = f"Status: {sub_status}" if sub_status else f"Status: {status}"
        
        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": status,
            "live_eta": live_eta,
            "co2": co2,
            "eta_changed": eta_changed,
            "smart_summary": smart_summary,
            "raw_data_snippet": "Source: Cargoes Flow API"
        }

    # CMA fallback: if Cargoes Flow has no data, skip browser driver
    carrier_name = request.carrier.lower()
    if "cma" in carrier_name:
        print("   ⚠️ CMA not in Cargoes Flow. Skipping driver; manual check required.")
        return {
            "source": "System",
            "status": "Manual Check Required",
            "co2": "N/A",
            "eta_changed": False,
            "message": "CMA CGM container not found in Cargoes Flow API. Please check manually at: https://www.cma-cgm.com/ebusiness/tracking"
        }

    # ---------------------------------------------------------
    # TIER 2: OFFICIAL DRIVERS (The Custom Scripts)
    # ---------------------------------------------------------
    print("   🐢 API didn't have data. Switching to Official Driver...")

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
    elif "evergreen" in carrier_name or "ever" in carrier_name:
        scrape_data = await drive_evergreen(request.number)

    # ---------------------------------------------------------
    # AI PARSING & RESPONSE
    # ---------------------------------------------------------
    if scrape_data and scrape_data.get("raw_data"):
        print("   🧠 Sending raw text to AI for analysis...")
        
        # Standardize system ETA if provided
        system_eta_standardized = standardize_date(request.system_eta)

        # First, get basic parsing to extract live ETA
        ai_result = await parse_tracking_data(
            scrape_data["raw_data"], 
            request.carrier,
            system_eta=system_eta_standardized,
            live_eta="Extracting...",
            holidays_info="Calculating..."
        )
        
        live_eta = standardize_date(ai_result.get("latest_date", "N/A"))
        co2 = ai_result.get("co2", "N/A")
        
        # Compare ETAs
        eta_changed = not dates_are_equal(request.system_eta, live_eta)
        
        # Calculate holidays if ETA changed
        holidays_info = "No holidays between dates"
        if eta_changed:
            start_date, end_date = get_date_range(request.system_eta, live_eta)
            if start_date and end_date:
                holidays = get_holidays_between_dates(start_date, end_date)
                holidays_info = format_holidays_for_summary(holidays)
                
                # Re-generate summary with holiday info if ETA changed
                print("   🧠 ETA changed - regenerating summary with holiday info...")
                ai_result = await parse_tracking_data(
                    scrape_data["raw_data"],
                    request.carrier,
                    system_eta=system_eta_standardized,
                    live_eta=live_eta,
                    holidays_info=holidays_info
                )

        return {
            "tracking_number": request.number,
            "carrier": request.carrier,
            "status": ai_result.get("status"),
            "live_eta": live_eta,
            "co2": co2,
            "eta_changed": eta_changed,
            "smart_summary": ai_result.get("summary"),
            "raw_data_snippet": "Source: Official Driver"
        }

    # If API failed AND Driver failed/doesn't exist
    # Provide helpful message based on carrier
    if "cma" in carrier_name:
        message = "CMA CGM container not found in API. Browser automation blocked by WAF. Please check manually at: https://www.cma-cgm.com/ebusiness/tracking"
    else:
        message = "Container not found in API, and no Official Driver available."
    
    return {
        "source": "System",
        "status": "Manual Check Required" if "cma" in carrier_name else "Not Found",
        "co2": "N/A",
        "eta_changed": False,
        "message": message
    }