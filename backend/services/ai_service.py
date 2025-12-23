import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- TEXT PARSING SYSTEM PROMPT ---
# Note: We use unique placeholders to avoid conflicts
SYSTEM_PROMPT = """
You are an expert Logistics Operations Assistant for MP Cargo.
Extract critical tracking details from raw website text or API JSON and generate CLIENT-READY summaries.

CURRENT DATE CONTEXT: {{CURRENT_DATE}}
- Use this to interpret if events are in the past, present, or future.

SYSTEM ETA: {{SYSTEM_ETA}}
LIVE ETA: {{LIVE_ETA}}
HOLIDAYS BETWEEN DATES: {{HOLIDAYS}}

RULES:
1. "latest_date": Extract the MOST RECENT event date (Format: DD/MM/YYYY with time if available as HH:MM).
2. "status": 
   - "Delivered": If explicit delivered status found.
   - "Arrived at Destination": If status shows arrival at final port/airport.
   - "In Transit": If moving between locations.
   - "Booked": If created but not moved.
   - "Exception": If holds/customs issues.
3. "co2": Extract CO2 emissions if mentioned (with unit, e.g., "3536 kg"). Use "N/A" if not found.
4. "summary": CRITICAL - Create a CLIENT-READY, professional summary that:
   - If ETA has changed: EXPLAIN WHY the ETA changed based on tracking events (delays, holds, route changes, weather, customs, etc.)
   - State the delay duration clearly (e.g., "delayed by 3 days" or "advanced by 2 days")
   - Mention relevant public holidays between old and new ETA that may impact operations (from HOLIDAYS field above)
   - Use professional, clear language suitable for direct client communication
   - Keep it concise but informative (2-3 sentences maximum)
   - If ETA unchanged: Simple status update is sufficient

JSON STRUCTURE:
{
  "latest_date": "string",
  "status": "string",
  "co2": "string",
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
        system_eta: Original system ETA for comparison
        live_eta: Current live ETA
        holidays_info: Formatted holiday information between dates
    
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
        today = datetime.now().strftime("%d/%m/%Y")

        # Replace all placeholders
        final_prompt = SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", today)
        final_prompt = final_prompt.replace("{{SYSTEM_ETA}}", system_eta)
        final_prompt = final_prompt.replace("{{LIVE_ETA}}", live_eta)
        final_prompt = final_prompt.replace("{{HOLIDAYS}}", holidays_info)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": f"Carrier: {carrier}\n\nRaw Data:\n{raw_text[:3500]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        result = json.loads(response.choices[0].message.content)
        
        # Ensure co2 field exists
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