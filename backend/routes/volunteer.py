from fastapi import APIRouter
from database.volunteers_db import save_volunteer, get_available_volunteers

router = APIRouter()

@router.post("/volunteer")
def create_volunteer(data: dict):

    try:
        print("Incoming Volunteer Data:", data)

        save_volunteer(data)

        return {
            "message": "volunteer added",
            "total_volunteers": len(get_available_volunteers())
        }

    except Exception as e:
        return {"error": str(e)}