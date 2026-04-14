from fastapi import APIRouter, Depends
from backend.auth import verify_token                    # ✅ Centralised auth
from database.volunteers_db import save_volunteer, get_available_volunteers
from backend.models import VolunteerInput
from database.geocoding import get_coordinates

router = APIRouter()

@router.post("/volunteer")
def create_volunteer(data: VolunteerInput, token: str = Depends(verify_token)):  # ✅ Auth guard

    try:
        volunteer_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        
        # 🌍 Auto-geocode location
        coords = get_coordinates(data.location)
        if coords:
            volunteer_dict["lat"] = coords.get("lat", 0.0)
            volunteer_dict["lng"] = coords.get("lng", 0.0)

        print("Incoming Volunteer Data:", volunteer_dict)

        save_volunteer(volunteer_dict)

        return {
            "message": "volunteer added",
            "total_volunteers": len(get_available_volunteers())
        }

    except Exception as e:
        return {"error": str(e)}