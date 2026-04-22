from fastapi import APIRouter, Depends
from backend.auth import verify_token
from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment
import math

router = APIRouter(prefix="/match")  # ✅ IMPORTANT

# ---------------------------------------------------------------------------
# Severity weights for composite scoring
# ---------------------------------------------------------------------------
SEVERITY_WEIGHT = {
    "critical": 1000,
    "very high": 500,
    "high": 200,
    "medium": 80,
    "low": 20,
}

# Skill sensitivity: these categories require NGO-verified (Tier 1) volunteers.
_SENSITIVE_CATEGORIES = {"medical", "rescue"}

# Maximum dispatch radius (km).
MAX_DISPATCH_KM = 50.0


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
def find_best_volunteer(need: dict, all_volunteers: list) -> dict | None:
    """
    Composite-score dispatch:

    score = (severity_weight / (distance_km + 1)) + tier_bonus

    • Sensitive needs (medical/rescue) → NGO-verified (Tier 1) pool only;
      returns None (hard block) if no Tier 1 volunteer is available.
    • All other needs → Tier 1 + Tier 2 pool with a +50 bonus for Tier 1.
    • Highest score wins.
    """
    need_lat      = need.get("lat", 0.0)
    need_lng      = need.get("lng", 0.0)
    need_category = need.get("category", "").lower()
    severity      = need.get("severity", "medium").lower()
    weight        = SEVERITY_WEIGHT.get(severity, 80)

    # ── Step 1: skill filter (case-insensitive) ──────────────────────────
    skilled = [
        v for v in all_volunteers
        if need_category in [s.lower() for s in v.get("skills", [])]
    ]
    if not skilled:
        skilled = all_volunteers  # fallback: no skill filter

    # ── Step 2: tier split ───────────────────────────────────────────────
    is_sensitive = need_category in _SENSITIVE_CATEGORIES
    tier1 = [v for v in skilled if v.get("ngo_verified") is True]
    tier2 = [v for v in skilled if not v.get("ngo_verified")]

    if is_sensitive and not tier1:
        return None  # hard block: no NGO-verified volunteer for sensitive need

    pool = tier1 if is_sensitive else (tier1 + tier2)
    if not pool:
        return None

    # ── Step 3: score and select ─────────────────────────────────────────
    def composite_score(v):
        v_lat = v.get("lat") or 0.0
        v_lng = v.get("lng") or 0.0
        n_lat = need_lat or 0.0
        n_lng = need_lng or 0.0
        dist = _haversine_km(n_lat, n_lng, v_lat, v_lng)
        tier_bonus = 50 if v.get("ngo_verified") else 0
        return (weight / (dist + 1)) + tier_bonus

    return max(pool, key=composite_score)


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------
@router.get("")
def match_needs(token: str = Depends(verify_token)):
    matches = []
    open_needs = get_open_needs()

    # 🚨 TRIAGE: Higher severity gets first pick of available volunteers
    severity_order = {"critical": 0, "very high": 1, "high": 2, "medium": 3, "low": 4}
    open_needs.sort(key=lambda n: severity_order.get(str(n.get("severity", "low")).lower(), 4))

    # Pre-fetch volunteers once; pool is updated in-memory as assignments are made
    all_volunteers = get_available_volunteers()
    assigned_ids: set[str] = set()

    for need in open_needs:

        # 🔴 Skip low-trust reports
        if need.get("trust_score", 100) < 50:
            continue

        need_lat = need.get("lat", 0.0)
        need_lng = need.get("lng", 0.0)
        need_id  = need.get("id")

        # Available pool = not yet assigned in this run
        available_pool = [v for v in all_volunteers if v.get("id") not in assigned_ids]

        best_vol = find_best_volunteer(need, available_pool)

        # ── Sensitive need with no Tier 1 volunteer found ─────────────────
        need_category = need.get("category", "").lower()
        is_sensitive  = need_category in _SENSITIVE_CATEGORIES

        if best_vol is None and is_sensitive:
            matches.append({
                "need_id":            need_id,
                "category":           need_category,
                "assigned_volunteer": None,
                "status":             "Manual Escalation Required",
                "reason":             "No NGO-verified (Tier 1) responder available for a sensitive need.",
            })
            continue

        if best_vol is None:
            # General need, no volunteer at all
            matches.append({
                "need_id":            need_id,
                "assigned_volunteer": "No suitable volunteer found",
                "status":             "pending",
            })
            continue

        n_lat = need_lat or 0.0
        n_lng = need_lng or 0.0
        v_lat = best_vol.get("lat") or 0.0
        v_lng = best_vol.get("lng") or 0.0

        dist_km = _haversine_km(n_lat, n_lng, v_lat, v_lng)

        if dist_km <= MAX_DISPATCH_KM:
            save_assignment(need_id, best_vol.get("id"))
            assigned_ids.add(best_vol.get("id"))

            tier_label = "Tier 1 (NGO-Verified)" if best_vol.get("ngo_verified") else "Tier 2 (Community)"
            matches.append({
                "need_id":            need_id,
                "assigned_volunteer": best_vol.get("name"),
                "volunteer_tier":     tier_label,
                "volunteer_id":       best_vol.get("id"),
                "distance_km":        round(dist_km, 2),
                "status":             "assigned",
            })
        else:
            matches.append({
                "need_id":            need_id,
                "assigned_volunteer": "No nearby volunteer",
                "status":             "pending",
                "reason":             f"Nearest match is {round(dist_km, 2)} km away (limit: {MAX_DISPATCH_KM} km).",
            })

    return {
        "total_matches_made": sum(1 for m in matches if m["status"] == "assigned"),
        "total_needs_processed": len(matches),
        "matches": matches,
    }
