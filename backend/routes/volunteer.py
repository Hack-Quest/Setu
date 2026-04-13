from fastapi import APIRouter, Depends
from backend.auth import verify_token                    # ✅ Centralised auth
from database.volunteers_db import save_volunteer, get_available_volunteers

router = APIRouter()

@router.post("/volunteer")
def create_volunteer(data: dict, token: str = Depends(verify_token)):  # ✅ Auth guard

    try:
        print("Incoming Volunteer Data:", data)

        save_volunteer(data)

        return {
            "message": "volunteer added",
            "total_volunteers": len(get_available_volunteers())
        }

    except Exception as e:
        return {"error": str(e)}