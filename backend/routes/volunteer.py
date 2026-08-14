import traceback
from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token                    # ✅ Centralised auth
from database.volunteers_db import save_volunteer, get_available_volunteers, get_all_volunteers, hash_password
from backend.models import VolunteerInput
from database.geocoding import get_coordinates

router = APIRouter()


@router.post("/volunteer")
def create_volunteer(data: VolunteerInput, token: dict = Depends(verify_token)):  # ✅ Auth guard
    try:
        volunteer_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()

        # 🔒 SECURITY: Hash the password; never store plaintext
        raw_password = volunteer_dict.pop("password")
        volunteer_dict["password_hash"] = hash_password(raw_password)

        # 🔒 SECURITY: Strip privileged tiered fields — only an authenticated NGO may set these.
        # A volunteer registering themselves must not be able to self-promote their tier.
        if isinstance(token, dict):
            role = token.get("role")
            uid = token.get("uid")
            if role == "ngo":
                # Force volunteer's NGO ID to be the authenticated NGO's ID
                volunteer_dict["ngo_id"] = uid
                # Verify if the NGO itself is verified in PostgreSQL
                ngo = get_ngo(uid)
                volunteer_dict["ngo_verified"] = bool(ngo and ngo.get("verified"))
            elif role == "system":
                # For system/tests, preserve the submitted NGO ID if verified
                ngo_id = volunteer_dict.get("ngo_id")
                if ngo_id:
                    ngo = get_ngo(ngo_id)
                    volunteer_dict["ngo_verified"] = bool(ngo and ngo.get("verified"))
                else:
                    volunteer_dict["ngo_verified"] = False
            else:
                # Regular volunteer cannot self-verify or self-associate
                volunteer_dict.pop("ngo_id", None)
                volunteer_dict["ngo_verified"] = False
        else:
            volunteer_dict.pop("ngo_id", None)
            volunteer_dict["ngo_verified"] = False

        volunteer_dict.pop("credential_tags", None)

        # Geocoding and location handling is now centralized in save_volunteer()
        print("📥 Incoming Volunteer Data:", volunteer_dict)

        doc_id = save_volunteer(volunteer_dict)

        return {
            "message": "volunteer added",
            "status": "registered",
            "volunteer_id": doc_id,
            "id": doc_id,
            "total_volunteers": len(get_available_volunteers())
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        print(f"❌ Route Error: {e}")
        return {"error": str(e)}


@router.get("/volunteers")
def list_volunteers(token: dict = Depends(verify_token)):
    """Public endpoint — returns all registered volunteers."""
    try:
        volunteers = get_all_volunteers()
        # Strip sensitive fields before sending to frontend
        safe_fields = ["id", "name", "skills", "available", "location",
                       "active_assignments", "ngo_id", "registered_at",
                       "ngo_verified", "credential_tags"]
        sanitized = [
            {k: v for k, v in vol.items() if k in safe_fields}
            for vol in volunteers
        ]
        return sanitized
    except Exception as e:
        print(f"❌ list_volunteers error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


