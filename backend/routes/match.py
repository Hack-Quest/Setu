from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token
from database.needs_db import get_open_needs, get_need_by_id
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment
import math

router = APIRouter(prefix="/match")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEVERITY_WEIGHT = {
    "critical": 1000,
    "very high": 500,
    "high": 200,
    "medium": 80,
    "low": 20,
}
SEVERITY_ORDER = {"critical": 0, "very high": 1, "high": 2, "medium": 3, "low": 4}

_SENSITIVE_CATEGORIES = {"medical", "rescue"}

MAX_DISPATCH_KM = 50.0
AVAILABILITY_PENALTY = 30  # deducted for recently assigned / unavailable volunteer


# ---------------------------------------------------------------------------
# Haversine distance helper
# ---------------------------------------------------------------------------
def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Composite-score volunteer selection
# ---------------------------------------------------------------------------
def _compute_score(need: dict, volunteer: dict) -> tuple[float, float]:
    """
    Returns (score, distance_km).

    score = (severity_weight / (distance_km + 1)) + tier_bonus - availability_penalty

    • tier_bonus        = +50  if NGO-verified (Tier 1)
    • availability_penalty = +30 deducted if volunteer.available is False
    """
    severity = need.get("severity", "medium").lower()
    weight   = SEVERITY_WEIGHT.get(severity, 80)

    n_lat = need.get("lat") or 0.0
    n_lng = need.get("lng") or 0.0
    v_lat = volunteer.get("lat") or 0.0
    v_lng = volunteer.get("lng") or 0.0

    dist_km     = _haversine_km(n_lat, n_lng, v_lat, v_lng)
    tier_bonus  = 50 if volunteer.get("ngo_verified") else 0
    penalty     = AVAILABILITY_PENALTY if not volunteer.get("available", True) else 0

    score = (weight / (dist_km + 1)) + tier_bonus - penalty
    return score, dist_km


def find_best_volunteer(need: dict, all_volunteers: list) -> dict | None:
    """
    Returns the highest-scoring volunteer, or None if no suitable candidate.
    Attaches _score and _distance_km to the returned dict for transparency.
    """
    need_category = need.get("category", "").lower()

    # Step 1: skill filter (case-insensitive), fallback to full pool
    skilled = [
        v for v in all_volunteers
        if need_category in [s.lower() for s in v.get("skills", [])]
    ]
    if not skilled:
        skilled = all_volunteers

    # Step 2: tier enforcement for sensitive categories
    is_sensitive = need_category in _SENSITIVE_CATEGORIES
    tier1 = [v for v in skilled if v.get("ngo_verified") is True]
    tier2 = [v for v in skilled if not v.get("ngo_verified")]

    if is_sensitive and not tier1:
        return None  # hard block

    pool = tier1 if is_sensitive else (tier1 + tier2)
    if not pool:
        return None

    # Step 3: rank by composite score
    scored = []
    for v in pool:
        if not v.get("available", True):
            continue

        score, dist_km = _compute_score(need, v)
        scored.append((score, dist_km, v))  # 🔥 MISSING LINE

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return None
    best_score, best_dist, best_vol = scored[0]

    # Attach computed values so callers can include them in responses
    result = dict(best_vol)
    result["_score"]       = best_score
    result["_distance_km"] = best_dist
    return result


# ---------------------------------------------------------------------------
# Main match route — global priority ordering
# ---------------------------------------------------------------------------
@router.get("")
def match_needs(token: str = Depends(verify_token)):
    """
    Runs the global priority matching pass:
    1. Sort all open needs by severity (critical first).
    2. Assign the best available volunteer to each need in order.
    3. Track used volunteers so no volunteer is double-dispatched.
    """
    open_needs = get_open_needs()

    # Sort needs by severity weight (descending) for global priority dispatch
    open_needs.sort(
        key=lambda n: SEVERITY_ORDER.get(str(n.get("severity", "low")).lower(), 4)
    )

    all_volunteers = get_available_volunteers()
    assigned_volunteer_ids: set[str] = set()
    matches = []

    for need in open_needs:

        # Skip low-trust reports
        if need.get("trust_score", 100) < 50:
            continue

        need_id  = need.get("id")
        need_category = (need.get("category") or "").lower()
        is_sensitive  = need_category in _SENSITIVE_CATEGORIES
        severity      = (need.get("severity") or "low").lower()

        # Available pool = not used in this run
        available_pool = [
            v for v in all_volunteers
            if v.get("id") not in assigned_volunteer_ids
        ]
        # 🔥 MULTI-VOLUNTEER LOGIC (CORRECT PLACEMENT)

        MAX_VOLUNTEERS_PER_NEED = 3

        scored = []

        for v in available_pool:
            if not v.get("available", True):
                continue

            score, dist_km = _compute_score(need, v)

            if dist_km <= MAX_DISPATCH_KM:
                scored.append((score, dist_km, v))

        scored.sort(key=lambda x: x[0], reverse=True)

        selected = scored[:MAX_VOLUNTEERS_PER_NEED]

        if not selected:
            matches.append({
                "need_id": need_id,
                "severity": severity,
                "status": "pending",
                "reason": "No suitable volunteers found."
            })
            continue

        assigned_list = []

        for score, dist_km, vol in selected:
            save_assignment(need_id, vol.get("id"))
            assigned_volunteer_ids.add(vol.get("id"))

            assigned_list.append({
                "volunteer_id": vol.get("id"),
                "name": vol.get("name"),
                "distance_km": round(dist_km, 2),
                "score": round(score, 2),
            })

        matches.append({
            "need_id": need_id,
            "severity": severity,
            "category": need_category,
            "assigned_volunteers": assigned_list,
            "status": "assigned",
            "count": len(assigned_list)
        })

    return {
        "total_matches_made":    sum(1 for m in matches if m["status"] == "assigned"),
        "total_needs_processed": len(matches),
        "matches":               matches,
    }


# ---------------------------------------------------------------------------
# Debug endpoint — for demo transparency
# ---------------------------------------------------------------------------
@router.get("/debug/{need_id}")
def debug_match(need_id: str, token: str = Depends(verify_token)):
    """
    Returns a full score breakdown for every available volunteer against a
    specific need. Use this to explain matching decisions during the demo.
    """
    need = get_need_by_id(need_id)
    if not need:
        raise HTTPException(status_code=404, detail=f"Need '{need_id}' not found.")

    all_volunteers = get_available_volunteers()
    breakdown = []

    for v in all_volunteers:
        score, dist_km = _compute_score(need, v)
        tier_bonus = 50 if v.get("ngo_verified") else 0
        penalty    = AVAILABILITY_PENALTY if not v.get("available", True) else 0
        severity   = (need.get("severity") or "medium").lower()
        weight     = SEVERITY_WEIGHT.get(severity, 80)
        skilled    = (need.get("category", "").lower() in
                      [s.lower() for s in v.get("skills", [])])

        breakdown.append({
            "volunteer_id":         v.get("id"),
            "volunteer_name":       v.get("name"),
            "ngo_verified":         v.get("ngo_verified", False),
            "skills":               v.get("skills", []),
            "skill_match":          skilled,
            "distance_km":          round(dist_km, 2),
            "severity_weight":      weight,
            "tier_bonus":           tier_bonus,
            "availability_penalty": penalty,
            "score":                round(score, 2),
        })

    breakdown.sort(key=lambda x: x["score"], reverse=True)

    return {
        "need_id":       need_id,
        "need_category": need.get("category"),
        "need_severity": need.get("severity"),
        "need_location": need.get("location_text"),
        "volunteers_evaluated": len(breakdown),
        "best_volunteer": breakdown[0] if breakdown else None,
        "all_scores":    breakdown,
    }
