from fastapi import APIRouter, Depends
from backend.auth import verify_token
from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment
import math

router = APIRouter(prefix="/match")  # ✅ IMPORTANT


def _haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


@router.get("")
def match_needs(token: str = Depends(verify_token)):

    matches = []
    open_needs = get_open_needs()

    for need in open_needs:

        # 🔴 Skip low trust
        if need.get("trust_score", 100) < 50:
            continue

        best_volunteer = None

        available_vols = get_available_volunteers()

        # 🔥 IMPROVED MATCHING LOGIC
        skilled_vols = [
            vol for vol in available_vols
            if (
                need.get("category") in vol.get("skills", [])
                or need.get("help_needed") in vol.get("skills", [])
            )
        ]

        need_lat = need.get("lat", 0)
        need_lng = need.get("lng", 0)

        if skilled_vols:
            skilled_vols.sort(
                key=lambda v: _haversine_km(
                    need_lat, need_lng,
                    v.get("lat", 0), v.get("lng", 0)
                )
            )
            best_volunteer = skilled_vols[0]

        if best_volunteer:
            dist_km = _haversine_km(
                need_lat, need_lng,
                best_volunteer.get("lat", 0),
                best_volunteer.get("lng", 0)
            )

            if dist_km <= 50:
                save_assignment(need.get("id"), best_volunteer.get("id"))

                matches.append({
                    "need_id": need.get("id"),
                    "assigned_volunteer": best_volunteer.get("name"),
                    "distance_km": round(dist_km, 2),
                    "status": "assigned"
                })
            else:
                matches.append({
                    "need_id": need.get("id"),
                    "assigned_volunteer": "No nearby volunteer",
                    "status": "pending"
                })

        else:
            # 🟡 FALLBACK
            matches.append({
                "need_id": need.get("id"),
                "assigned_volunteer": "No suitable volunteer found",
                "status": "pending"
            })

    return {
        "total_matches_made": len(matches),
        "matches": matches
    }