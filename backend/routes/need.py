from fastapi import APIRouter, Depends
import os

from backend.models import NeedInput
from backend.auth import verify_token
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need, check_corroboration
from database.verification import calculate_trust_score

router = APIRouter()

@router.post("/need")
def create_need(
    data: NeedInput,
    token: str = Depends(verify_token)
):
    try:
        # STEP 1 — AI processing (Gemini/Groq Fallback)
        ai_result = process_need_text(data.description)
        category = ai_result.get("category", "general")
        severity = ai_result.get("severity", "low")
        ai_consistency = ai_result.get("consistency", 5)

        # STEP 2 — Location & Corroboration
        coords = get_coordinates(data.location)
        lat, lng = coords.get("lat"), coords.get("lng")
        corroborating_count = check_corroboration(lat, lng, category)

        # STEP 3 — Trust Score Calculation
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

        # STEP 4 — Final Data Assembly
        final_data = {
            "description": data.description,
            "category": category,
            "severity": severity,
            "lat": lat,
            "lng": lng,
            "status": "pending",
            "trust_score": trust_result["score"],
            "dispatch_action": trust_result["dispatch_action"],
            "verification_reasons": trust_result["reasons"],
        }

        # STEP 5 — Save to Firestore
        doc_id = save_need(final_data)
        final_data["id"] = doc_id
        
        return final_data

    except Exception as e:
        print(f"❌ Error in /need: {e}")
        return {"error": str(e), "category": "general", "severity": "low"}