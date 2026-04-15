from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers

router = APIRouter(prefix="/dashboard")


<<<<<<< Updated upstream
@router.get("")
=======
@router.get("/dashboard")
>>>>>>> Stashed changes
def dashboard():

    needs = get_open_needs()
    vols = get_available_volunteers()

    total_needs = len(needs)
    total_volunteers = len(vols)

<<<<<<< Updated upstream
    # 🔥 severity counts
    critical = sum(1 for n in needs if n.get("severity") == "critical")
    high = sum(1 for n in needs if n.get("severity") == "high")
    medium = sum(1 for n in needs if n.get("severity") == "medium")
    low = sum(1 for n in needs if n.get("severity") == "low")

    # 🔥 FIXED flagged logic
    flagged = sum(1 for n in needs if n.get("trust_score", 100) < 50)

    # 🔥 unmatched (simple version)
    unmatched = sum(1 for n in needs if n.get("status") == "open")
=======
    critical = sum(1 for n in needs if n["severity"] == "critical")
    high = sum(1 for n in needs if n["severity"] == "high")
    medium = sum(1 for n in needs if n["severity"] == "medium")
    low = sum(1 for n in needs if n["severity"] == "low")
>>>>>>> Stashed changes

    recent_need = needs[-1] if needs else None

    return {
        "total_needs": total_needs,
        "total_volunteers": total_volunteers,
<<<<<<< Updated upstream
        "critical_cases": critical,
        "high_priority_cases": high,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "flagged_cases": flagged,
        "unmatched_cases": unmatched,
        "recent_need": recent_need
    }
=======
        "critical_priority_cases": critical,
        "high_priority_cases": high + critical,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "recent_need": recent_need,
    }
>>>>>>> Stashed changes
