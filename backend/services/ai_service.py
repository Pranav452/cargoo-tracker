import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- STRICT PROMPT FOR ETA ACCURACY ---
# Uses {{CURRENT_DATE}} to determine Past vs Future
SYSTEM_PROMPT = """
You are a Logistics Coordinator.
Your goal is to extract the **ESTIMATED ARRIVAL DATE (ETA)** at the **FINAL DESTINATION**.

CURRENT DATE: {{CURRENT_DATE}}

RULES FOR "latest_date" (THE LIVE ETA):
1. **PRIORITY 1 (Destination Arrival - HIGHEST):** Look for dates in the "Destination" column or row, NOT "Discharging Port".
   - If you see both "Discharging Port" and "Destination" dates at the same location, **ALWAYS PICK THE DESTINATION DATE** (it's usually later).
   - Example: If "Discharging Port: Antwerp - Arrival: 09-Jan-2026" and "Destination: Antwerp - Arrival: 10-Jan-2026", **YOU MUST PICK 10-Jan-2026**.
   - Look for labels like "Destination", "Final Destination", "Final Arrival", or "Destination Arrival".

2. **PRIORITY 2 (Future Arrival at Final Port):** If no explicit "Destination" date exists, look for dates labeled "ETA", "Arrival", "Berthing", or "ETB" at the FINAL DESTINATION port.
   - If you see "Departure: 12-Dec" and "Arrival: 17-Jan", **YOU MUST PICK 17-Jan**.
   - Even if the date is in the future (2026), USE IT.
   
3. **PRIORITY 3 (Past Arrival):** If the shipment has already arrived, use the "Arrival" or "Discharge" date at destination.

4. **PRIORITY 4 (In Transit - No ETA):** Only if NO arrival date is mentioned, use the last "Departure" date.

5. **CRITICAL:** Never use "Discharging Port" date if a "Destination" date exists. The Destination date is the TRUE final arrival.

6. **FORMAT:** Convert to **DD-MMM-YYYY** (e.g., 17-Jan-2026). Do NOT use ISO format.

RULES FOR "status":
- **"In Transit"**: If the extracted ETA is in the **FUTURE** relative to {{CURRENT_DATE}}.
- **"Arrived"**: If the extracted ETA is in the **PAST** and text confirms arrival.
- **"Booked"**: If no movement events exist yet.

RULES FOR "summary":
- Explicitly mention the Destination and the Date.
- Example: "In transit to Antwerp. Expected Arrival: 17-Jan-2026."

JSON STRUCTURE:
{
  "latest_date": "string",
  "status": "string",
  "summary": "string"
}
"""

async def parse_tracking_data(
    raw_text: str, 
    carrier: str, 
    system_eta: str = "N/A", 
    live_eta: str = "N/A", 
    holidays_info: str = "No holidays between dates"
):
    """
    Parse tracking data with AI and generate client-ready summaries.
    
    Args:
        raw_text: Raw tracking data from website/API
        carrier: Carrier name
        system_eta: Original system ETA for comparison (kept for backward compatibility)
        live_eta: Current live ETA (kept for backward compatibility)
        holidays_info: Formatted holiday information between dates (kept for backward compatibility)
    
    Returns:
        Dict with latest_date, status, co2, and summary
    """
    try:
        if not raw_text or len(raw_text) < 50:
             return {
                 "latest_date": "N/A", 
                 "status": "Error", 
                 "co2": "N/A",
                 "summary": "Insufficient data."
             }

        # CALCULATE TODAY'S DATE
        today = datetime.now().strftime("%d-%b-%Y")
        final_prompt = SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", today)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": f"Carrier: {carrier}\n\nRaw Data:\n{raw_text[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        result = json.loads(response.choices[0].message.content)
        
        # Ensure co2 field exists for backward compatibility
        if "co2" not in result:
            result["co2"] = "N/A"
        
        return result
    except Exception as e:
        print(f"   ⚠️ AI Parse Error: {e}")
        return {
            "latest_date": "Error", 
            "status": "AI Parse Failed", 
            "co2": "N/A",
            "summary": "Error analyzing data."
        }

# --- VISION CAPTCHA SOLVER ---
async def solve_captcha_image(base64_image: str):
    print("   🤖 Asking GPT-4o to solve CAPTCHA...")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What is the text in this captcha? Return ONLY the text."},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            }
                        }
                    ]
                }
            ],
            max_tokens=10
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ❌ Vision Error: {e}")
        return None