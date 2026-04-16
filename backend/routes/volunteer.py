from fastapi import APIRouter, Depends
from backend.auth import verify_token
from database.volunteers_db import save_volunteer, get_available_volunteers
from backend.models import VolunteerInput
from database.geocoding import get_coordinates

# ✅ Swap passlib for the native, modern bcrypt library
import bcrypt

router = APIRouter()

def get_password_hash(password: str) -> str:
    # bcrypt requires bytes, so we encode the string to utf-8
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), salt)
    # Decode back to a string so Firestore can save it cleanly
    return hashed_bytes.decode('utf-8')

@router.post("/volunteer")
def create_volunteer(data: VolunteerInput, token: str = Depends(verify_token)):
    try:
        volunteer_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        
        # 🔒 SECURITY: Hash the password and remove the plain text one
        raw_password = volunteer_dict.pop("password")
        volunteer_dict["password_hash"] = get_password_hash(raw_password)
        
        # 🌍 Auto-geocode location
        coords = get_coordinates(data.location)
        if coords:
            volunteer_dict["lat"] = coords.get("lat", 0.0)
            volunteer_dict["lng"] = coords.get("lng", 0.0)

        # 🧹 Clean up the location string so it isn't saved to DB
        volunteer_dict.pop("location", None)

        print("Incoming Volunteer Data:", volunteer_dict)

        save_volunteer(volunteer_dict)

        return {
            "message": "volunteer added",
            "total_volunteers": len(get_available_volunteers())
        }

    except Exception as e:
        print(f"❌ Route Error: {e}")
        return {"error": str(e)}