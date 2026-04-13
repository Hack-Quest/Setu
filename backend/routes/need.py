from fastapi import APIRouter, Depends, BackgroundTasks

from backend.models import NeedInput
from backend.auth import verify_token                          # ✅ Centralised auth
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need, check_corroboration  # ✅ Corroboration helper
from database.verification import calculate_trust_score        # ✅ Trust engine
from notifications.gmail_alert import send_alert

router = APIRouter()


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

        # 🛡️ STEP 2b — Trust verification (wired to verification.py)
        corroboration_count = check_corroboration(coords["lat"], coords["lng"], category)
        ai_consistency = int(ai_result.get("confidence_score", 5))  # 0-10 scale from Gemini
        trust_result = calculate_trust_score(data.__dict__ | coords, ai_consistency, corroboration_count)
        trust_score = trust_result["score"]

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
            "trust_score": trust_score,                        # ✅ Now populated from verification.py
            "trust_reasons": trust_result["reasons"],
            "dispatch_action": trust_result["dispatch_action"] # ✅ Overrides AI-only dispatch decision
        }

        # 💾 Save
        save_need(final_data)
        needs_storage.append(final_data)

        # 🚨 EMAIL TRIGGER (NON-BLOCKING)
        if final_data.get("dispatch_action") == "auto_dispatch" and final_data.get("trust_score", 0) > 60:
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