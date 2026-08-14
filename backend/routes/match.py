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
_SENSITIVE_KEYWORDS = {
    "medical", "doctor", "nurse", "ambulance", "bleeding", "injury", "injuries",
    "hospital", "trapped", "collapse", "building collapse", "drowning",
    "evacuation", "fire", "earthquake", "landslide", "tsunami", "cyclone",
    "rescue", "cpr", "unconscious", "casualty", "casualties", "first-aid", "first aid"
}

# Canonical skill mappings to standard emergency domains
SKILL_MAP = {
    "medical": {
        "medical", "first-aid", "first aid", "doctor", "nurse", "paramedic",
        "cpr", "health", "medic", "healthcare", "emt", "clinical", "triage"
    },
    "rescue": {
        "rescue", "search and rescue", "search & rescue", "sar", "evacuation",
        "swimming", "lifeguard", "firefighting", "disaster response", "extrication"
    },
    "supplies": {
        "supplies", "food", "cooking", "ration", "distribution", "relief supplies",
        "relief", "provisions", "water", "blankets", "tents", "hygiene", "pack"
    },
    "food": {
        "supplies", "food", "cooking", "ration", "distribution", "relief supplies",
        "relief", "provisions", "water", "pack"
    },
    "logistics": {
        "logistics", "driving", "driver", "transport", "transportation",
        "vehicle", "delivery", "warehouse", "loading", "truck", "van", "dispatch"
    },
    "shelter": {
        "shelter", "construction", "carpentry", "housing", "tent setup", "logistics", "supplies"
    },
}

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
# Sensitive Case Classification & Safe Fallback
# ---------------------------------------------------------------------------
def is_sensitive_case(need: dict) -> bool:
    """
    Determines whether a need is a sensitive / high-risk case requiring Tier 1.
    If classification is missing, 'Not Specified', unknown, or ambiguous,
    fails safely by enforcing Tier 1 verification.
    """
    raw_category = str(need.get("category") or "").strip().lower()
    raw_help = str(need.get("help_needed") or "").strip().lower()
    raw_disaster = str(need.get("disaster_type") or "").strip().lower()
    raw_desc = str(need.get("description") or "").strip().lower()

    # 1. Direct match on sensitive categories
    if raw_category in _SENSITIVE_CATEGORIES or raw_help in _SENSITIVE_CATEGORIES:
        return True

    # 2. Check for high-risk disaster keywords in text/disaster type/category
    combined_text = f"{raw_category} {raw_help} {raw_disaster} {raw_desc}"
    if any(keyword in combined_text for keyword in _SENSITIVE_KEYWORDS):
        return True

    # 3. Check for missing or uncertain classification -> FAIL SAFELY to Tier 1
    unspecified_values = {"", "not specified", "unknown", "none", "null", "undefined", "n/a", "other"}
    category_specified = raw_category not in unspecified_values
    help_specified = raw_help not in unspecified_values

    # If neither category nor help_needed is clearly specified, fail safely to Tier 1
    if not category_specified and not help_specified:
        return True

    return False


# ---------------------------------------------------------------------------
# Skill Compatibility Matching
# ---------------------------------------------------------------------------
def get_canonical_category(need: dict) -> str:
    """Extract canonical need category from need object."""
    cat = str(need.get("category") or "").strip().lower()
    if cat in SKILL_MAP:
        return cat
    
    help_needed = str(need.get("help_needed") or "").strip().lower()
    if help_needed in SKILL_MAP:
        return help_needed

    disaster = str(need.get("disaster_type") or "").strip().lower()
    if disaster in SKILL_MAP:
        return disaster

    combined = f"{cat} {help_needed} {disaster}".lower()
    for canonical, synonyms in SKILL_MAP.items():
        if any(syn in combined for syn in synonyms):
            return canonical

    return cat or "other"


def is_skill_compatible(need: dict, volunteer: dict) -> bool:
    """
    Checks if a volunteer's skills are compatible with the emergency need.
    A volunteer without relevant skills will not be matched.
    """
    raw_skills = volunteer.get("skills") or []
    if isinstance(raw_skills, str):
        raw_skills = [raw_skills]

    v_skills = [s.strip().lower() for s in raw_skills if s and isinstance(s, str)]
    if not v_skills:
        return False

    sensitive = is_sensitive_case(need)
    # General wildcard skills only permitted for non-sensitive cases
    if ("all" in v_skills or "general" in v_skills) and not sensitive:
        return True

    canonical_cat = get_canonical_category(need)
    if canonical_cat in SKILL_MAP:
        required_tags = SKILL_MAP[canonical_cat]
        for s in v_skills:
            if s in required_tags:
                return True
            if any(tag in s or s in tag for tag in required_tags):
                return True
        return False

    # Fallback to direct field matching
    need_fields = [
        str(need.get("category") or "").lower(),
        str(need.get("help_needed") or "").lower(),
        str(need.get("disaster_type") or "").lower(),
    ]
    for s in v_skills:
        if any(s in f or f in s for f in need_fields if f and f != "not specified"):
            return True

    return False


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
    severity = str(need.get("severity") or "medium").lower()
    weight   = SEVERITY_WEIGHT.get(severity, 80)

    n_lat = float(need.get("lat") or 0.0)
    n_lng = float(need.get("lng") or 0.0)
    v_lat = float(volunteer.get("lat") or 0.0)
    v_lng = float(volunteer.get("lng") or 0.0)

    dist_km     = _haversine_km(n_lat, n_lng, v_lat, v_lng)
    tier_bonus  = 50 if volunteer.get("ngo_verified") else 0
    penalty     = AVAILABILITY_PENALTY if not volunteer.get("available", True) else 0

    score = (weight / (dist_km + 1)) + tier_bonus - penalty
    return score, dist_km


def find_best_volunteer(need: dict, all_volunteers: list) -> dict | None:
    """
    Returns the highest-scoring eligible and skill-compatible volunteer,
    or None if no suitable candidate exists.
    """
    # Step 1: Availability filter
    available = [
        v for v in all_volunteers
        if v.get("available", True) and (v.get("active_assignments") or 0) < 3
    ]
    if not available:
        return None

    # Step 2: Skill compatibility filter (Strict: no fallback to incompatible volunteers)
    skilled = [v for v in available if is_skill_compatible(need, v)]
    if not skilled:
        return None

    # Step 3: Tier enforcement for sensitive/uncertain categories
    sensitive = is_sensitive_case(need)
    if sensitive:
        tier1_pool = [v for v in skilled if v.get("ngo_verified") is True]
        if not tier1_pool:
            return None  # Hard block: sensitive cases require Tier 1
        pool = tier1_pool
    else:
        pool = skilled

    # Step 4: Distance & composite scoring
    scored = []
    for v in pool:
        score, dist_km = _compute_score(need, v)
        if dist_km <= MAX_DISPATCH_KM:
            scored.append((score, dist_km, v))

    scored.sort(key=lambda x: x[0], reverse=True)
    if not scored:
        return None

    best_score, best_dist, best_vol = scored[0]
    result = dict(best_vol)
    result["_score"]       = best_score
    result["_distance_km"] = best_dist
    return result


# ---------------------------------------------------------------------------
# Main match route — global priority ordering
# ---------------------------------------------------------------------------
@router.get("")
def match_needs(token: dict = Depends(verify_token)):
    """
    Runs the global priority matching pass:
    1. Sort all open needs by severity (critical first).
    2. Enforce skill compatibility, availability, and Tier 1 verification.
    3. Assign the best available volunteer(s) to each need in order.
    4. Track used volunteers so no volunteer is double-dispatched in the same run.
    """
    if isinstance(token, dict):
        if token.get("role") not in ["system", "ngo"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: only NGOs or system administrators can trigger matching"
            )
            
    open_needs = get_open_needs()


    # Sort needs by severity weight (descending) for global priority dispatch
    open_needs.sort(
        key=lambda n: SEVERITY_ORDER.get(str(n.get("severity", "low")).lower(), 4)
    )

    all_volunteers = get_available_volunteers()
    assigned_volunteer_ids: set[str] = set()
    matches = []

    for need in open_needs:
        trust = need.get("trust_score", 100)
        severity = (need.get("severity") or "low").lower()

        # Smart trust gating
        if severity in ["critical", "very high"]:
            pass  # always allow high severity
        elif trust < 50:
            continue

        need_id = need.get("id")
        need_category = str(need.get("category") or need.get("help_needed") or "").lower()
        sensitive = is_sensitive_case(need)

        # Available pool = not already assigned in this run & available in DB
        available_pool = [
            v for v in all_volunteers
            if v.get("id") not in assigned_volunteer_ids
            and v.get("available", True)
            and (v.get("active_assignments") or 0) < 3
        ]

        # Skill filtering
        skilled_pool = [v for v in available_pool if is_skill_compatible(need, v)]

        if sensitive:
            tier1_pool = [v for v in skilled_pool if v.get("ngo_verified") is True]
            if not tier1_pool:
                matches.append({
                    "need_id": need_id,
                    "severity": severity,
                    "category": need_category or "sensitive",
                    "status": "Manual Escalation Required",
                    "assigned_volunteer": "Unassigned",
                    "volunteer_tier": "None",
                    "reason": "Sensitive category requires Tier 1 NGO verification."
                })
                continue
            candidate_pool = tier1_pool
        else:
            if not skilled_pool:
                matches.append({
                    "need_id": need_id,
                    "severity": severity,
                    "category": need_category or "general",
                    "status": "pending",
                    "assigned_volunteer": "Unassigned",
                    "volunteer_tier": "None",
                    "reason": "No volunteers found with required skills."
                })
                continue
            candidate_pool = skilled_pool

        MAX_VOLUNTEERS_PER_NEED = 3
        scored = []

        for v in candidate_pool:
            score, dist_km = _compute_score(need, v)
            if dist_km <= MAX_DISPATCH_KM:
                scored.append((score, dist_km, v))

        scored.sort(key=lambda x: x[0], reverse=True)
        selected = scored[:MAX_VOLUNTEERS_PER_NEED]

        if not selected:
            matches.append({
                "need_id": need_id,
                "severity": severity,
                "category": need_category,
                "status": "pending",
                "assigned_volunteer": "Unassigned",
                "volunteer_tier": "None",
                "reason": "No suitable volunteers found within dispatch radius."
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

        first_vol = selected[0][2]
        tier_label = "Tier 1 (NGO-Verified)" if first_vol.get("ngo_verified") else "Tier 2 (Community)"

        matches.append({
            "need_id": need_id,
            "severity": severity,
            "category": need_category,
            "assigned_volunteer": assigned_list[0]["name"] if assigned_list else "Unassigned",
            "volunteer_tier": tier_label,
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
def debug_match(need_id: str, token: dict = Depends(verify_token)):
    """
    Returns a full score breakdown for every available volunteer against a
    specific need. Use this to explain matching decisions during the demo.
    """
    if isinstance(token, dict):
        if token.get("role") not in ["system", "ngo"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: only NGOs or system administrators can view match debug breakdowns"
            )

    need = get_need_by_id(need_id)
    if not need:
        raise HTTPException(status_code=404, detail=f"Need '{need_id}' not found.")


    all_volunteers = get_available_volunteers()
    sensitive = is_sensitive_case(need)
    breakdown = []

    for v in all_volunteers:
        score, dist_km = _compute_score(need, v)
        tier_bonus = 50 if v.get("ngo_verified") else 0
        penalty    = AVAILABILITY_PENALTY if not v.get("available", True) else 0
        severity   = (need.get("severity") or "medium").lower()
        weight     = SEVERITY_WEIGHT.get(severity, 80)
        skilled    = is_skill_compatible(need, v)
        tier_ok    = (not sensitive) or bool(v.get("ngo_verified"))

        breakdown.append({
            "volunteer_id":         v.get("id"),
            "volunteer_name":       v.get("name"),
            "ngo_verified":         v.get("ngo_verified", False),
            "skills":               v.get("skills", []),
            "skill_match":          skilled,
            "tier_eligible":        tier_ok,
            "distance_km":          round(dist_km, 2),
            "within_radius":        dist_km <= MAX_DISPATCH_KM,
            "severity_weight":      weight,
            "tier_bonus":           tier_bonus,
            "availability_penalty": penalty,
            "score":                round(score, 2),
        })

    breakdown.sort(key=lambda x: x["score"], reverse=True)

    return {
        "need_id":               need_id,
        "need_category":         need.get("category"),
        "is_sensitive":          sensitive,
        "need_severity":         need.get("severity"),
        "need_location":         need.get("location_text"),
        "volunteers_evaluated":  len(breakdown),
        "best_volunteer":        breakdown[0] if breakdown else None,
        "all_scores":            breakdown,
    }
