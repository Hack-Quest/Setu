from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token                    # ✅ Centralised auth
from database.volunteers_db import save_volunteer, get_available_volunteers, get_all_volunteers, hash_password
from backend.models import VolunteerInput
from database.geocoding import get_coordinates

router = APIRouter()


@router.post("/volunteer")
def create_volunteer(data: VolunteerInput, token: str = Depends(verify_token)):  # ✅ Auth guard
    try:
        volunteer_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()

        # 🔒 SECURITY: Hash the password; never store plaintext
        raw_password = volunteer_dict.pop("password")
        volunteer_dict["password_hash"] = hash_password(raw_password)

        # 🔒 SECURITY: Strip privileged tiered fields — only an authenticated NGO may set these.
        # A volunteer registering themselves must not be able to self-promote their tier.
        volunteer_dict.pop("ngo_id", None)
        volunteer_dict.pop("credential_tags", None)

        # 🌍 Auto-geocode location
        coords = get_coordinates(data.location)
        if coords:
            volunteer_dict["lat"] = coords.get("lat", 0.0)
            volunteer_dict["lng"] = coords.get("lng", 0.0)

        # 🧹 Don't persist the raw location string
        volunteer_dict.pop("location", None)

        print("📥 Incoming Volunteer Data:", volunteer_dict)

        save_volunteer(volunteer_dict)

        return {
            "message": "volunteer added",
            "total_volunteers": len(get_available_volunteers())
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Route Error: {e}")
        return {"error": str(e)}


@router.get("/volunteers")
def list_volunteers():
    """Public endpoint — returns all registered volunteers."""
    try:
        volunteers = get_all_volunteers()
        # Strip sensitive fields before sending to frontend
        safe_fields = ["id", "name", "skills", "available", "location",
                       "active_assignments", "ngo_id", "registered_at"]
        sanitized = [
            {k: v for k, v in vol.items() if k in safe_fields}
            for vol in volunteers
        ]
        return sanitized
    except Exception as e:
        print(f"❌ list_volunteers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

