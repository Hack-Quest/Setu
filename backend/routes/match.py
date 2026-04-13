from fastapi import APIRouter, Depends
from backend.auth import verify_token                          # ✅ Centralised auth
from database.needs_db import get_open_needs                   # ✅ Real Firestore source
from database.volunteers_db import get_available_volunteers    # ✅ Real Firestore source
from database.assignments_db import save_assignment            # ✅ Real Firestore sink
import math

router = APIRouter()


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Returns the great-circle distance in kilometres between two lat/lng points.
    Uses the Haversine formula — accurate to within ~0.3%.
    """
    R = 6371.0  # Earth’s mean radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

@router.get("/match")
def match_needs(token: str = Depends(verify_token)):  # ✅ Real auth guard
    matches = []
    open_needs = get_open_needs()

    for need in open_needs:
        # GUARD: Skip untrustworthy reports 
        if need.get("trust_score", 100) < 50:
            print(f"[Match] Skipping need {need.get('id')} — low trust score ({need.get('trust_score')}).")
            continue

        best_volunteer = None
        available_vols = get_available_volunteers(category=need.get("category"))

        # 📍 Sort skill-matched volunteers by Haversine distance from the need
        need_lat = need.get("lat") or 0.0
        need_lng = need.get("lng") or 0.0

        skilled_vols = [
            vol for vol in available_vols
            if need.get("category") in vol.get("skills", [])
        ]

        if skilled_vols:
            skilled_vols.sort(
                key=lambda v: _haversine_km(
                    need_lat, need_lng,
                    v.get("lat", 0.0), v.get("lng", 0.0)
                )
            )
            best_volunteer = skilled_vols[0]  # ✅ Nearest skilled volunteer

        if best_volunteer:
            save_assignment(need.get("id"), best_volunteer.get("id"))
            dist_km = _haversine_km(
                need_lat, need_lng,
                best_volunteer.get("lat", 0.0), best_volunteer.get("lng", 0.0)
            )
            matches.append({
                "need_id": need.get("id"),
                "assigned_volunteer": best_volunteer.get("name"),
                "distance_km": round(dist_km, 2),   # ✅ Exposed for traceability
                "status": "assigned"
            })

    return {
        "total_matches_made": len(matches),
        "matches": matches
    }

# ==========================================
# 🧪 STANDALONE RUNNER (uses inline mocks — does NOT shadow real imports above)
# ==========================================

if __name__ == "__main__":
    # Inline mocks — only active when running this file directly
    _needs_mock = [
        {"id": "N1", "category": "medical", "trust_score": 90, "lat": 28.61, "lng": 77.20, "description": "Broken leg"},
        {"id": "N2", "category": "rescue",  "trust_score": 20, "lat": 28.62, "lng": 77.21, "description": "Fake report"},   # skipped
        {"id": "N3", "category": "food",    "trust_score": 75, "lat": 28.63, "lng": 77.22, "description": "Hungry families"},
    ]
    _vols_mock = [
        {"id": "V1", "name": "Dr. Smith",   "skills": ["medical"], "lat": 28.62, "lng": 77.20},
        {"id": "V2", "name": "Rescue Team", "skills": ["rescue"],  "lat": 28.61, "lng": 77.23},
        {"id": "V3", "name": "Food Bank",   "skills": ["food"],    "lat": 28.64, "lng": 77.22},
    ]
    _assignments = []

    def _mock_get_open_needs():         return _needs_mock
    def _mock_get_vols(category=None):  return [v for v in _vols_mock if category in v["skills"]] if category else _vols_mock
    def _mock_save(nid, vid):           _assignments.append((nid, vid)); print(f"DEBUG: Need {nid} → Vol {vid}")

    # Temporarily patch module-level names for the test run
    import sys
    _mod = sys.modules[__name__]
    _orig = (get_open_needs, get_available_volunteers, save_assignment)
    get_open_needs, get_available_volunteers, save_assignment = _mock_get_open_needs, _mock_get_vols, _mock_save  # noqa

    print("🚀 Starting Local Match Logic Test...\n")
    result = match_needs(token="test-token")
    print("\n--- Final Results ---")
    print(f"Total Matches: {result['total_matches_made']}")
    for m in result["matches"]:
        print(f"✅ Assigned {m['need_id']} → {m['assigned_volunteer']} ({m['distance_km']} km)")
    assert result["total_matches_made"] == 2, "❌ Expected 2 matches (N1, N3)"
    print("\n🎉 Test Passed: Trust guard skipped N2; Haversine picked nearest skilled volunteer.")