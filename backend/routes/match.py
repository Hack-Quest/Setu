from fastapi import APIRouter

from backend.routes.need import needs_storage
from backend.routes.volunteer import volunteers

router = APIRouter()

@router.get("/match")
def match_needs():

    matches = []

    for need in needs_storage:

        best_volunteer = None

        for vol in volunteers:

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

        matches.append(match)

    return {
        "total_matches": len(matches),
        "matches": matches
    }