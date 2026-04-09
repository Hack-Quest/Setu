from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment

router = APIRouter()

@router.get("/match")
def match_needs():

    matches = []

    for need in get_open_needs():

        best_volunteer = None

        for vol in get_available_volunteers():

            skills = vol.get("skills", [])
            location = vol.get("location", "").lower()

            # ✅ Skill match
            if need["category"] in skills:

                # ✅ Location match
                if location in need["description"].lower() or True:
                    best_volunteer = vol
                    break

        match = {
            "need_id": need["id"],
            "need_description": need["description"],
            "severity": need["severity"],
            "assigned_volunteer": best_volunteer.get("name") if best_volunteer else None,
            "status": "assigned" if best_volunteer else "unassigned"
        }

        if best_volunteer:
            save_assignment(need["id"], best_volunteer["id"])

        matches.append(match)

    return {
        "total_matches": len(matches),
        "matches": matches
    }