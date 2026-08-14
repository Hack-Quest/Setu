import traceback
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

router = APIRouter(prefix="/need")

needs_storage = []


# 🧠 NEW: Secondary AI Review
def secondary_review(description: str):
    """Second-pass AI validation for mid-confidence reports."""
    result = process_need_text(description)

    # Slight boost if consistent
    adjustment = 5 if result["consistency"] > 6 else -5

    return {
        "adjustment": adjustment,
        "reason": f"Secondary AI consistency: {result['consistency']}"
    }


# 🚀 AUTO MATCH (unchanged)
def _auto_match_for_need(need_id: str):
    from database.needs_db import get_need_by_id
    from database.volunteers_db import get_available_volunteers
    from database.assignments_db import save_assignment
    from backend.routes.match import find_best_volunteer, MAX_DISPATCH_KM

    need = get_need_by_id(need_id)
    if not need:
        return

    volunteers = get_available_volunteers()
    best = find_best_volunteer(need, volunteers)

    if not best:
        return

    if best.get("_distance_km", 999) <= MAX_DISPATCH_KM:
        save_assignment(need_id, best["id"])


# 🧠 CORE FUNCTION
def process_and_save_need(data: NeedInput, background_tasks: BackgroundTasks):
    try:
        # 1️⃣ BASIC VALIDATION
        if len(data.description.strip()) < 10:
            return {"error": "Description too short"}

        # 2️⃣ AI CLASSIFICATION
        ai_result = process_need_text(data.description)

        category = ai_result["category"]
        CATEGORY_NORMALIZATION = {
            "collapse": "rescue",
            "building collapse": "rescue",
            "earthquake": "rescue",
            "flood": "logistics",
            "water shortage": "logistics",
            "medical emergency": "medical",
            "fire": "rescue",
        }

        category = CATEGORY_NORMALIZATION.get(category.lower(), category.lower())
        severity = ai_result["severity"]
        consistency = ai_result["consistency"]

        # 3️⃣ GEOLOCATION
        lat = data.lat
        lng = data.lng
        
        # Geocode only if exact coords aren't provided
        if lat == 0.0 and lng == 0.0 and data.location_text.strip() and data.location_text != "Unknown Location":
            coords = get_coordinates(data.location_text)
            
            # Fallback: if the form was mapped backwards, the real address might be in the description under "Help:"
            if (not coords or coords.get("lat") == 0) and "Help: " in data.description:
                fallback_loc = data.description.split("Help: ")[-1].strip()
                if fallback_loc and fallback_loc != "Not Specified":
                    coords = get_coordinates(fallback_loc)

            # 🚨 HARD FAIL (MANDATORY)
            if not coords or coords.get("lat") == 0 or coords.get("lng") == 0:
                from fastapi import HTTPException
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid or unresolvable location: {data.location_text}"
                )

            lat = coords["lat"]
            lng = coords["lng"]
        # 🚨 FINAL SAFETY CHECK (DO NOT SKIP)
        if lat == 0.0 and lng == 0.0:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Geocoding failed — coordinates are invalid"
            )
            
        # Fallback string representation if none provided
        if lat != 0.0 and lng != 0.0 and (not data.location_text.strip() or data.location_text == "Unknown Location"):
            data.location_text = f"{lat}, {lng}"

        payload = data.model_dump() if hasattr(data, "model_dump") else data.dict()

        verification_payload = payload | {
            "lat": lat,
            "lng": lng,
            "category": category,
        }

        # 4️⃣ COMMON VALIDATION
        common_validation = run_common_validation(verification_payload)

        if not common_validation["passed"]:
            trust_result = build_common_only_trust_result(
                common_validation,
                category,
                data.disaster_type,
            )
        else:
            corroboration = check_corroboration(lat, lng, category)

            trust_result = calculate_trust_score(
                verification_payload,
                consistency,
                corroboration,
                category,
                common_validation.get("base_score", 0),
            )

        trust_score = trust_result["score"]
        # 🔥 BOOST trust for realistic inputs
        if len(data.description.split()) > 8:
            trust_score += 10

        # Cap at 100
        trust_score = min(trust_score, 100)

        # 🧠 5️⃣ TIERED TRIAGE SYSTEM (FIXED)
        if trust_score <= 30:
            dispatch_action = "rejected"
        elif 31 <= trust_score <= 75:
            review = secondary_review(data.description)
            trust_score += review["adjustment"]
            trust_score = max(0, min(trust_score, 100))
            dispatch_action = "secondary_review"
        else:
            dispatch_action = "auto_dispatch"

        # 6️⃣ PRIORITY
        if severity in ["critical", "very high"]:
            priority = "HIGH"
        elif severity in ["high", "medium"]:
            priority = "MEDIUM"
        else:
            priority = "LOW"

        # 7️⃣ FINAL OBJECT
        final_data = {
            "description": data.description,
            "category": category,
            "severity": severity,
            "lat": lat,
            "lng": lng,
            "trust_score": trust_score,
            "dispatch_action": dispatch_action,
            "priority": priority,
            "status": "secondary_review" if dispatch_action == "secondary_review" else ("rejected" if dispatch_action == "rejected" else "open"),
            "flag": "verified" if trust_score > 50 else "suspicious",
            "reasons": trust_result.get("reasons", []),
        }

        # 💾 SAVE
        doc_id = save_need(final_data)
        final_data["id"] = doc_id
        final_data["need_id"] = doc_id
        needs_storage.append(final_data)

        # 🚀 AUTO ACTIONS
        if dispatch_action == "auto_dispatch":
            background_tasks.add_task(_auto_match_for_need, doc_id)
            background_tasks.add_task(send_alert, final_data)

        return final_data

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}


@router.post("")
def create_need(
    data: NeedInput,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_token),
):
    return process_and_save_need(data, background_tasks)