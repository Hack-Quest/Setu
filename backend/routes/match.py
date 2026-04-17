from fastapi import APIRouter, Depends
from backend.auth import verify_token
from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers
from database.assignments_db import save_assignment
import math

router = APIRouter(prefix="/match")  # ✅ IMPORTANT

# ---------------------------------------------------------------------------
# Skill sensitivity map
# Skills listed here require ONLY NGO-verified (Tier 1) responders.
# All other skills allow Community (Tier 2) volunteers as a fallback.
# ---------------------------------------------------------------------------
SKILL_SENSITIVITY: dict[str, dict] = {
    "Medical":  {"tier1_only": True},
    "medical":  {"tier1_only": True},
    "Rescue":   {"tier1_only": True},
    "rescue":   {"tier1_only": True},
}

# Within this extra distance margin (km), a Tier 1 volunteer is always
# preferred over a Tier 2 volunteer for general (non-sensitive) needs.
TIER1_PREFERENCE_MARGIN_KM = 10.0

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
# Two-stage volunteer selection
# ---------------------------------------------------------------------------
def find_best_volunteer(need: dict, all_volunteers: list) -> dict | None:
    """
    Two-stage dispatch logic:

    Stage 1 – Filter by skill match, then split into:
        • Tier 1 (NGO-verified):  vol.get("ngo_verified") is True
        • Tier 2 (Community):     everyone else

    Stage 2 – Select best candidate:
        • Sensitive need  → Tier 1 pool only; return None if empty.
        • General need    → Merge pools but promote Tier 1 when the
                           closest Tier 1 is within TIER1_PREFERENCE_MARGIN_KM
                           of the closest Tier 2.

    Returns the chosen volunteer dict, or None if no eligible volunteer exists.
    """
    need_lat = need.get("lat", 0.0)
    need_lng = need.get("lng", 0.0)
    need_category  = need.get("category", "")
    need_help      = need.get("help_needed", "")

    # ── Step 1: skill filter ─────────────────────────────────────────────
    skilled = [
        v for v in all_volunteers
        if (need_category in v.get("skills", [])
            or need_help    in v.get("skills", []))
    ]

    if not skilled:
        return None

    # ── Step 2: tier split ───────────────────────────────────────────────
    tier1 = [v for v in skilled if v.get("ngo_verified") is True]
    tier2 = [v for v in skilled if v.get("ngo_verified") is not True]

    # Attach distance to each volunteer (avoids repeated calculation)
    def with_dist(pool):
        return sorted(
            [{"vol": v, "dist": _haversine_km(need_lat, need_lng,
                                               v.get("lat", 0.0),
                                               v.get("lng", 0.0))}
             for v in pool],
            key=lambda x: x["dist"]
        )

    # ── Step 3: sensitivity check ────────────────────────────────────────
    is_sensitive = (
        SKILL_SENSITIVITY.get(need_category, {}).get("tier1_only", False)
        or SKILL_SENSITIVITY.get(need_help,   {}).get("tier1_only", False)
    )

    if is_sensitive:
        # Sensitive need → Tier 1 ONLY
        ranked = with_dist(tier1)
        return ranked[0]["vol"] if ranked else None

    # ── Step 4: general need → merge with Tier 1 priority ────────────────
    ranked_t1 = with_dist(tier1)
    ranked_t2 = with_dist(tier2)

    if ranked_t1 and ranked_t2:
        best_t1_dist = ranked_t1[0]["dist"]
        best_t2_dist = ranked_t2[0]["dist"]
        # Prefer Tier 1 if it's within TIER1_PREFERENCE_MARGIN_KM of Tier 2
        if best_t1_dist <= best_t2_dist + TIER1_PREFERENCE_MARGIN_KM:
            return ranked_t1[0]["vol"]
        return ranked_t2[0]["vol"]

    if ranked_t1:
        return ranked_t1[0]["vol"]
    if ranked_t2:
        return ranked_t2[0]["vol"]

    return None


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------
@router.get("")
def match_needs(token: str = Depends(verify_token)):
    matches = []
    open_needs = get_open_needs()

    # 🚨 TRIAGE: Critical needs get first pick of available volunteers
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    open_needs.sort(key=lambda n: severity_order.get(n.get("severity", "low"), 3))

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
        need_category = need.get("category", "")
        need_help     = need.get("help_needed", "")
        is_sensitive  = (
            SKILL_SENSITIVITY.get(need_category, {}).get("tier1_only", False)
            or SKILL_SENSITIVITY.get(need_help,   {}).get("tier1_only", False)
        )

        if best_vol is None and is_sensitive:
            matches.append({
                "need_id":            need_id,
                "category":           need_category or need_help,
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

        dist_km = _haversine_km(
            need_lat, need_lng,
            best_vol.get("lat", 0.0),
            best_vol.get("lng", 0.0)
        )

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
