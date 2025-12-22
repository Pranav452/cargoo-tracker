import os
import json
from datetime import datetime
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# --- TEXT PARSING SYSTEM PROMPT ---
# Note: We use a unique placeholder {{CURRENT_DATE}} to avoid conflicts
SYSTEM_PROMPT = """
You are an expert Logistics Operations Assistant for MP Cargo.
Extract critical tracking details from raw website text or API JSON.

CURRENT DATE CONTEXT: {{CURRENT_DATE}}
- Use this to interpret if events are in the past, present, or future.

RULES:
1. "latest_date": Extract the MOST RECENT event date (Format: DD-Mon-YYYY).
2. "status": 
   - "Delivered": If explicit delivered status found.
   - "Arrived at Destination": If status shows arrival at final port/airport.
   - "In Transit": If moving between locations.
   - "Booked": If created but not moved.
   - "Exception": If holds/customs issues.
3. "summary": A concise, professional 1-sentence summary.

JSON STRUCTURE:
{
  "latest_date": "string",
  "status": "string",
  "summary": "string"
}
"""

async def parse_tracking_data(raw_text: str, carrier: str):
    try:
        if not raw_text or len(raw_text) < 50:
             return {"latest_date": "N/A", "status": "Error", "summary": "Insufficient data."}

        # CALCULATE TODAY'S DATE
        today = datetime.now().strftime("%d-%b-%Y")

        # Simple replacement to avoid format() errors with JSON braces
        final_prompt = SYSTEM_PROMPT.replace("{{CURRENT_DATE}}", today)

        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": final_prompt},
                {"role": "user", "content": f"Carrier: {carrier}\n\nRaw Data:\n{raw_text[:3500]}"}
            ],
            response_format={"type": "json_object"},
            temperature=0
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        print(f"   ⚠️ AI Parse Error: {e}")
        return {"latest_date": "Error", "status": "AI Parse Failed", "summary": "Error analyzing data."}

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