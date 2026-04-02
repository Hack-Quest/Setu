from fastapi import APIRouter

from backend.routes.need import needs_storage
from backend.routes.volunteer import volunteers

router = APIRouter()

@router.get("/dashboard")
def dashboard():

    total_needs = len(needs_storage)
    total_volunteers = len(volunteers)

    high = sum(1 for n in needs_storage if n["severity"] == "high")
    medium = sum(1 for n in needs_storage if n["severity"] == "medium")
    low = sum(1 for n in needs_storage if n["severity"] == "low")

    recent_need = needs_storage[-1] if needs_storage else None

    return {
        "total_needs": total_needs,
        "total_volunteers": total_volunteers,
        "high_priority_cases": high,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "recent_need": recent_need
    }