from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers

router = APIRouter()

@router.get("/dashboard")
def dashboard():

    needs = get_open_needs()
    vols = get_available_volunteers()

    total_needs = len(needs)
    total_volunteers = len(vols)

    high = sum(1 for n in needs if n["severity"] == "high")
    medium = sum(1 for n in needs if n["severity"] == "medium")
    low = sum(1 for n in needs if n["severity"] == "low")

    recent_need = needs[-1] if needs else None

    return {
        "total_needs": total_needs,
        "total_volunteers": total_volunteers,
        "high_priority_cases": high,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "recent_need": recent_need
    }