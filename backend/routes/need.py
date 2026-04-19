from fastapi import APIRouter, Depends, BackgroundTasks
from backend.models import NeedInput
from backend.auth import verify_token
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need, check_corroboration
from database.verification import calculate_trust_score
from notifications.gmail_alert import send_alert

router = APIRouter(prefix="/need")  # ✅ IMPORTANT

needs_storage = []

async def broadcast_high_trust_report(report_data: dict):
    try:
        from backend.main import manager
        await manager.broadcast_json(report_data)
        print("📡 Broadcasted high-trust report via WebSocket JS", flush=True)
    except ImportError as e:
        print(f"⚠️ Could not import websocket manager: {e}", flush=True)
    except Exception as e:
        print(f"⚠️ WS Broadcast Error: {e}", flush=True)

def process_and_save_need(data: NeedInput, background_tasks: BackgroundTasks):
    """Core logic separated so it can be called internally (webhook) or via API."""
    try:
        print("📥 Incoming Data:", data)

        # 🔵 INPUT VALIDATION
        if len(data.description.strip()) < 10:
            return {"error": "Description too short"}

        # 🧠 AI PROCESSING
        ai_result = process_need_text(data.description)

        if not isinstance(ai_result, dict):
            raise Exception("AI did not return valid JSON")

        category = ai_result.get("category", "general")
        severity = ai_result.get("severity", "low")
        ai_consistency = int(ai_result.get("consistency", 5))

        if ai_consistency <= 3:
            confidence = "low"
        elif ai_consistency <= 6:
            confidence = "medium"
        else:
            confidence = "high"

        # 🔥 CATEGORY FALLBACK (IMPORTANT FOR MATCHING)
        if category == "other":
            category = data.help_needed

        flag = "suspicious" if confidence == "low" else "verified"

        # 🌍 LOCATION
        # ✅ FIXED: Using data.location based on models.py
        coords = get_coordinates(data.location_text) or {"lat": 0, "lng": 0}
        # 🛡️ VERIFICATION
        corroboration_count = check_corroboration(
            coords["lat"], coords["lng"], category
        )

        trust_result = calculate_trust_score(
            (data.model_dump() if hasattr(data, "model_dump") else data.dict()) | coords,
            ai_consistency,
            corroboration_count,
        )

        trust_score = trust_result["score"]

        # 🟢 PRIORITY LOGIC
        if trust_score > 70:
            priority = "HIGH"
        elif trust_score > 40:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # 🧩 FINAL DATA
        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": category,
            "severity": severity,
            "location_text": data.location_text, # Passed to DB for logging
            "confidence": confidence,
            "flag": flag,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "open",
            "trust_score": trust_score,
            "trust_reasons": trust_result.get("reasons", []),
            "dispatch_action": trust_result.get("dispatch_action", "manual"),
            "priority": priority,
        }

        # 💾 SAVE
        save_need(final_data)
        needs_storage.append(final_data)

        # 🚨 EMAIL TRIGGER
        if final_data["dispatch_action"] == "auto_dispatch" and trust_score > 60:
            background_tasks.add_task(send_alert, final_data)

        # 🌐 WEBSOCKET BROADCAST
        if trust_score > 70:
            background_tasks.add_task(broadcast_high_trust_report, final_data)

        print("✅ Final Data:", final_data)

        return final_data

    except Exception as e:
        print("❌ Error:", e)
        return {
            "error": str(e),
            "message": "Fallback response used"
        }


@router.post("")
def create_need(
    data: NeedInput,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token)
):
    """API endpoint wrapper."""
    return process_and_save_need(data, background_tasks)