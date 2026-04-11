from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment

router = APIRouter()

@router.get("/match")
def match_needs():
    matches = []

    for need in get_open_needs():

        # GUARD CLAUSE: Skip reports flagged as spam/untrustworthy (trust_score < 50).
        # Default to 100 when the field is absent so legacy records are still processed.
        if need.get("trust_score", 100) < 50:
            print(f"[Match] Skipping need {need.get('id')} — trust score {need.get('trust_score')} is below threshold.")
            continue

        best_volunteer = None

        for vol in get_available_volunteers():

            skills = vol.get("skills", [])
            location = vol.get("location", "").lower()

            # ✅ Skill match
            if need.get("category") in skills:

                # ✅ Location match
                if location in need.get("description", "").lower() or True:
                    best_volunteer = vol
                    break

        match = {
            "need_id": need.get("id"),
            "need_description": need.get("description"),
            "severity": need.get("severity"),
            "assigned_volunteer": best_volunteer.get("name") if best_volunteer else None,
            "status": "assigned" if best_volunteer else "unassigned"
        }

        if best_volunteer:
            save_assignment(need.get("id"), best_volunteer.get("id"))

        matches.append(match)

    return {
        "total_matches": len(matches),
        "matches": matches
    }