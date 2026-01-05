import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- HOLIDAY CONTEXT ---
HOLIDAYS = """
MAJOR HOLIDAYS (India & France) to consider for delays:
- Jan 1: New Year
- Jan 26: Republic Day (IN)
- May 1: Labor Day (FR)
- May 8: Victory Day (FR)
- Jul 14: Bastille Day (FR)
- Aug 15: Independence (IN) / Assumption (FR)
- Oct 2: Gandhi Jayanti (IN)
- Nov 1: All Saints (FR)
- Nov 11: Armistice (FR)
- Dec 25: Christmas
- Floating: Diwali, Holi, Eid (Check dates dynamically if possible)
"""

# --- STRICT PARSING PROMPT ---
SYSTEM_PROMPT = f"""
You are a Logistics Data Auditor for MP Cargo.
Your job is to determine the REAL STATUS and provide a BUSINESS CONTEXT SUMMARY.

CURRENT DATE: {{CURRENT_DATE}}

{HOLIDAYS}

INPUT DATA:
You will receive raw tracking text or JSON.

LOGIC RULES:
1. **LIVE ETA**: 
   - Parse the Estimated Arrival at the FINAL DESTINATION (e.g., Antwerp, Le Havre).
   - Format: DD-MMM-YYYY (e.g., 15-Jan-2026).
   - If 'eta_raw' is null/N/A, output "N/A".

2. **STATUS**:
   - "Delivered": If delivered to consignee.
   - "Arrived at Port": If discharged at final port but not delivered.
   - "In Transit": If ETA is in the FUTURE.
   - "Delayed": If ETA is in the PAST (by >2 days) and not arrived.

3. **SMART SUMMARY (The "Why"):**
   - Keep it under 15 words.
   - Mention if the shipment is Early, On Time, or Late.
   - **Crucial:** If the ETA falls near a Holiday (from the list above), add a note: "Possible delay due to [Holiday]."
   - Example: "Arrived early at Antwerp. Clearance pending."
   - Example: "In Transit. ETA 26-Jan (Republic Day IN holiday risk)."

JSON OUTPUT FORMAT:
{{
  "latest_date": "string",
  "status": "string",
  "summary": "string"
}}
"""


async def parse_tracking_data(
    raw_text: str,
    carrier: str,
    system_eta: str = "N/A",
    live_eta: str = "N/A",
    holidays_info: str = "No holidays between dates",
):
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
            return {
                "latest_date": "N/A",
                "status": "Error",
                "summary": "No data extracted.",
                "co2": "N/A",
            }

        # Pre-parse JSON if it comes from an API
        try:
            data = json.loads(raw_text)
            raw_text = json.dumps(data)
        except Exception:
            # If not valid JSON, just pass the raw text as-is
            pass

        today = datetime.now().strftime("%d-%b-%Y")
        final_prompt = SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", today)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Carrier: {carrier}\n"
                        f"System ETA: {system_eta}\n"
                        f"Live ETA (if known): {live_eta}\n"
                        f"Holiday Info (between system and live ETA): {holidays_info}\n\n"
                        f"Data:\n{raw_text[:4000]}"
                    ),
                },
            ],
            response_format={"type": "json_object"},
            temperature=0,
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
            "status": "AI Failed",
            "co2": "N/A",
            "summary": "Error analyzing data.",
        }


async def solve_captcha_image(base64_image: str):
    """
    Solve a CAPTCHA image using OpenAI Vision (kept from previous implementation).
    """
    print("   🤖 Asking GPT-4o to solve CAPTCHA...")
    try:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "What is the text in this captcha? Return ONLY the text.",
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            max_tokens=10,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"   ❌ Vision Error: {e}")
        return None
