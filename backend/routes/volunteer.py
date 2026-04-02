from fastapi import APIRouter

router = APIRouter()

# 🧠 In-memory storage
volunteers = []

@router.post("/volunteer")
def create_volunteer(data: dict):

    try:
        print("Incoming Volunteer Data:", data)

        volunteers.append(data)

        return {
            "message": "volunteer added",
            "total_volunteers": len(volunteers)
        }

    except Exception as e:
        return {"error": str(e)}