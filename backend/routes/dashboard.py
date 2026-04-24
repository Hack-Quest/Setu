from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers, get_all_volunteers
from database.ngos_db import get_all_ngos

router = APIRouter(prefix="/dashboard")


@router.get("/reports")
def get_reports_endpoint():
    from database.needs_db import get_open_needs
    # Return directly as a list
    return get_open_needs()

@router.get("")
def dashboard():

    needs = get_open_needs()
    vols = get_available_volunteers()
    all_vols = get_all_volunteers()
    all_ngos = get_all_ngos()

    total_needs = len(needs)
    total_volunteers = len(all_vols)
    total_ngos = len(all_ngos)

    # 🔥 severity counts (Using safe .get() to prevent KeyErrors)
    critical = sum(1 for n in needs if n.get("severity") == "critical")
    high = sum(1 for n in needs if n.get("severity") == "high")
    medium = sum(1 for n in needs if n.get("severity") == "medium")
    low = sum(1 for n in needs if n.get("severity") == "low")

    # 🔥 FIXED flagged logic
    flagged = sum(1 for n in needs if n.get("trust_score", 100) < 50)

    # 🔥 unmatched (simple version)
    unmatched = sum(1 for n in needs if n.get("status") == "open")

    recent_need = needs[-1] if needs else None

    return {
        "total_needs": total_needs,
        "total_volunteers": total_volunteers,
        "total_ngos": total_ngos,
        "critical_cases": critical,
        "high_priority_cases": high,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "flagged_cases": flagged,
        "unmatched_cases": unmatched,
        "recent_need": recent_need,
        "reports": needs
    }