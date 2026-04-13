from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os

from backend.models import NeedInput
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need

# ✅ FIXED IMPORT
from notifications.gmail_alert import send_alert


# 🔐 Load env variables
load_dotenv()
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

router = APIRouter()

# 🔐 Security setup
security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials and credentials.credentials != SECRET_TOKEN:
        print(f"⚠ Warning: Invalid token received: {credentials.credentials}")
    return credentials.credentials if credentials else None


# 🧠 Temporary in-memory storage
needs_storage = []


@router.post("/need")
def create_need(
    data: NeedInput,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    try:
        print("📥 Incoming Data:", data)

        # 🧠 STEP 1 — AI processing
        ai_result = process_need_text(data.description)

        if not isinstance(ai_result, dict):
            raise Exception("AI did not return valid JSON")

        category = ai_result.get("category", "general")
        severity = ai_result.get("severity", "low")
        confidence = ai_result.get("confidence", "medium")

        # 🔥 IMPROVED DISPATCH LOGIC
        if severity in ["critical", "high"]:
            dispatch_action = "auto_dispatch"
        else:
            dispatch_action = "manual"

        # 🛡️ Flag
        flag = "suspicious" if confidence == "low" else "verified"

        # 🌍 STEP 2 — Location
        coords = get_coordinates(data.location)

        if not coords:
            coords = {"lat": 0, "lng": 0}

        # 🧩 STEP 3 — Final data
        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": category,
            "severity": severity,
            "confidence": confidence,
            "flag": flag,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "pending",
            "dispatch_action": dispatch_action
        }

        # 💾 Save
        save_need(final_data)
        needs_storage.append(final_data)

        # 🚨 EMAIL TRIGGER (NON-BLOCKING)
        if dispatch_action == "auto_dispatch":
            background_tasks.add_task(send_alert, final_data)

        print("✅ Final Data:", final_data)

        return final_data

    except Exception as e:
        print("❌ Error:", e)

        return {
            "error": str(e),
            "message": "Fallback response used",
            "category": "general",
            "severity": "low",
            "flag": "unknown"
        }