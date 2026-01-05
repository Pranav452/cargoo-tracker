import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- HOLIDAY CONTEXT ---
HOLIDAYS = """
MAJOR HOLIDAYS:
- Jan 1: New Year
- Jan 26: Republic Day (IN)
- May 1: Labor Day
- Jul 14: Bastille Day (FR)
- Dec 25: Christmas
"""

# --- STRICT PROMPT FOR HMM ---
SYSTEM_PROMPT = f"""
You are a Logistics Data Auditor.
Your ONLY goal is to find the **ESTIMATED ARRIVAL (ETA)** at the **FINAL DESTINATION**.

CURRENT DATE: {{CURRENT_DATE}}
{HOLIDAYS}

INPUT DATA:
Raw text from shipping lines.

LOGIC RULES (STRICT):
1. **IGNORE HISTORY**: Ignore any dates in the past (e.g. 2023, 2024, early 2025).
2. **FIND DESTINATION**: Look for the column "Destination" or "Discharging Port" (e.g. Antwerp, Le Havre).
3. **FIND DATE**: 
   - In HMM tables, look for the row "Arrival(ETB)" or "Arrival".
   - Pick the **LATEST FUTURE DATE** you can find.
   - Example: If you see "2025-11-23" and "2026-01-18", PICK "2026-01-18".
4. **FORMAT**: DD-MMM-YYYY (e.g. 18-Jan-2026).

JSON OUTPUT:
{{
  "latest_date": "string",
  "status": "string", 
  "summary": "string"
}}
"""


async def parse_tracking_data(raw_text: str, carrier: str):
    try:
        if not raw_text or len(raw_text) < 50:
             return {"latest_date": "N/A", "status": "Error", "summary": "No data."}

        today = datetime.now().strftime("%d-%b-%Y")
        final_prompt = SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", today)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": f"Carrier: {carrier}\n\nData:\n{raw_text[:4000]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   ⚠️ AI Error: {e}")
        return {"latest_date": "Error", "status": "AI Failed", "summary": "Error."}


async def solve_captcha_image(base64_image: str):
    return None
