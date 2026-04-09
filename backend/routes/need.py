from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os
import json

from backend.models import NeedInput
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need

# 🔐 Load env variables
load_dotenv()
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

router = APIRouter()

# 🔐 Security setup
security = HTTPBearer(auto_error=False)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):

    # ✅ TEMP (testing mode – no blocking)
    if credentials and credentials.credentials != SECRET_TOKEN:
        print(f"⚠ Warning: Invalid token received: {credentials.credentials}")

    return credentials.credentials if credentials else None


# 🧠 In-memory storage (temporary)
needs_storage = []





# 🔥 MAIN ROUTE
@router.post("/need")
def create_need(
    data: NeedInput,
    token: str = Depends(verify_token)
):

    try:
        print("📥 Incoming Data:", data)

        # 🧠 STEP 1 — AI processing
        ai_result = process_need_text(data.description)

        # 🛡️ Safe parsing
        if not isinstance(ai_result, dict):
            raise Exception("AI did not return valid JSON")

        category = ai_result.get("category", "general")
        severity = ai_result.get("severity", "low")

        # 🌍 STEP 2 — Location (mock)
        coords = get_coordinates(data.location)

        # 🧩 STEP 3 — Final data
        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": category,
            "severity": severity,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "pending"
        }

        # 💾 STEP 4 — Save
        save_need(final_data)
        needs_storage.append(final_data)

        print("✅ Final Data:", final_data)

        return final_data

    except Exception as e:
        print("❌ Error:", e)

        # 🔴 Fallback (never break demo)
        return {
            "error": str(e),
            "message": "Fallback response used",
            "category": "general",
            "severity": "low"
        }