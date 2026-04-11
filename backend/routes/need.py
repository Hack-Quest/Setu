from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
import os
import json

from backend.models import NeedInput
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need, check_corroboration
from database.verification import calculate_trust_score

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
        ai_consistency = ai_result.get("consistency", 5)  # New: AI believability score (0-10)

        # 🌍 STEP 2 — Location (geocoding)
        coords = get_coordinates(data.location)
        lat = coords.get("lat")
        lng = coords.get("lng")

        # 🔍 STEP 3 — Corroboration check (how many nearby same-category reports in the last 2h?)
        corroborating_count = check_corroboration(lat, lng, category)
        print(f"[Corroboration] Found {corroborating_count} nearby report(s) in the last 2 hours.")

        # 🧮 STEP 4 — Trust score calculation
        trust_result = calculate_trust_score(
            data_dict={
                "lat": lat,
                "lng": lng,
                "reporter_phone": data.reporter_phone,
                "disaster_type": data.disaster_type,
            },
            ai_consistency=ai_consistency,
            corroborating_reports_count=corroborating_count
        )
        print(f"[Trust Score] Score: {trust_result['score']} | Action: {trust_result['dispatch_action']}")

        # 🧩 STEP 5 — Final data assembly
        final_data = {
            "description": data.description,
            "category": category,
            "severity": severity,
            "lat": lat,
            "lng": lng,
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "pending",
            # Trust verification results
            "trust_score": trust_result["score"],
            "dispatch_action": trust_result["dispatch_action"],
            "verification_reasons": trust_result["reasons"],
        }

        # 💾 STEP 6 — Save to Firestore
        doc_id = save_need(final_data)
        final_data["id"] = doc_id
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