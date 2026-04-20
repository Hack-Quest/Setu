from fastapi import APIRouter, Depends, BackgroundTasks
from backend.models import NeedInput
from backend.auth import verify_token
from ai_processing.gemini_processor import process_need_text
from database.geocoding import get_coordinates
from database.needs_db import save_need, check_corroboration
from database.verification import (
    build_common_only_trust_result,
    calculate_trust_score,
    is_high_stakes_disaster,
    run_common_validation,
)
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
        summary_en = ai_result.get("summary_en", "Emergency reported.")
        summary_local = ai_result.get("summary_local", "Aapaatkaaleen sthiti (Emergency reported).")

        if ai_consistency <= 3:
            confidence = "low"
        elif ai_consistency <= 6:
            confidence = "medium"
        else:
            confidence = "high"

        # 🔥 CATEGORY FALLBACK (IMPORTANT FOR MATCHING)
        if category == "other":
            category = data.help_needed

        # 🌍 LOCATION
        coords_raw = get_coordinates(data.location_text) or {}
        lat = coords_raw.get("lat")
        lng = coords_raw.get("lng")
        coords = {
            "lat": lat if lat is not None else 0,
            "lng": lng if lng is not None else 0,
        }

        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        verification_payload = payload | {
            "lat": lat,
            "lng": lng,
            "category": category,
            "disaster_type": data.disaster_type,
        }

        # ✅ Common validation must run for every report.
        common_validation = run_common_validation(verification_payload)
        high_stakes = is_high_stakes_disaster(category, data.disaster_type)

        flag = "suspicious" if confidence == "low" else "verified"
        status = "open"
        corroboration_count = 0

        if not common_validation.get("passed"):
            status = "Pending Verification"
            flag = "pending_verification"
            trust_result = build_common_only_trust_result(
                common_validation,
                category,
                data.disaster_type,
            )
            trust_result["dispatch_action"] = "pending_verification"
        elif high_stakes:
            if lat is not None and lng is not None:
                corroboration_count = check_corroboration(lat, lng, category)

            trust_result = calculate_trust_score(
                verification_payload,
                ai_consistency,
                corroboration_count,
                category,
                common_validation.get("base_score", 0),
            )
        else:
            trust_result = build_common_only_trust_result(
                common_validation,
                category,
                data.disaster_type,
            )

        trust_score = trust_result["score"]

        # 🟢 PRIORITY LOGIC
        severity_key = str(severity).strip().lower()
        if severity_key in {"critical", "very high"}:
            priority = "HIGH"
        elif severity_key in {"high", "medium"}:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # 🧩 FINAL DATA
        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": category,
            "severity": severity,
            "summary_en": summary_en,
            "summary_local": summary_local,
            "location_text": data.location_text, # Passed to DB for logging
            "confidence": confidence,
            "flag": flag,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": status,
            "trust_score": trust_score,
            "trust_reasons": trust_result.get("reasons", []),
            "dispatch_action": trust_result.get("dispatch_action", "manual"),
            "priority": priority,
        }

        # 💾 SAVE
        doc_id = save_need(final_data)
        final_data["id"] = doc_id
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