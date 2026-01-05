import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SYSTEM_PROMPT = """
You are a Logistics Data Auditor.
Your job is to extract the **ESTIMATED ARRIVAL DATE** at the **FINAL DESTINATION**.

CURRENT DATE: {{CURRENT_DATE}}

RULES:
1. **Find the Date:** Look for "ETA", "Arrival", "Discharge" at the final destination (e.g., Antwerp, Le Havre).
2. **Format:** DD-MMM-YYYY (e.g., 15-Jan-2026).
3. **Status Logic (Strict):**
   - If the Date is in the FUTURE -> "In Transit"
   - If the Date is in the PAST -> "Arrived"
   - If you see "Delivered" -> "Delivered"
4. **Summary:**
   - Keep it under 10 words.
   - Example: "Arrived at Antwerp on 12-Dec-2025."
   - Example: "In Transit. ETA Antwerp: 15-Jan-2026."

JSON OUTPUT:
{
  "latest_date": "string",
  "status": "string",
  "summary": "string"
}
"""

async def parse_tracking_data(raw_text: str, carrier: str, system_eta: str = "N/A", live_eta: str = "N/A", holidays_info: str = "No holidays between dates"):
    """
    Parse tracking data with AI and generate client-ready summaries.
    
    Args:
        raw_text: Raw tracking data from website/API (can be JSON string or text)
        carrier: Carrier name
        system_eta: Original system ETA for comparison (kept for backward compatibility)
        live_eta: Current live ETA (kept for backward compatibility)
        holidays_info: Formatted holiday information between dates (kept for backward compatibility)
    
    Returns:
        Dict with latest_date, status, co2, and summary
    """
    try:
        # Basic check to avoid wasting tokens on empty data
        if not raw_text or len(raw_text) < 50:
             return {"latest_date": "N/A", "status": "Error", "summary": "No data extracted.", "co2": "N/A"}

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
        print(f"   ⚠️ AI Error: {e}")
        return {
            "latest_date": "Error", 
            "status": "AI Failed", 
            "co2": "N/A",
            "summary": "Error."
        }

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
