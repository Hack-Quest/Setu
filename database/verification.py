import os
from datetime import datetime, timedelta, timezone

import dotenv
import requests
from google.cloud.firestore_v1.base_query import FieldFilter

dotenv.load_dotenv()

HIGH_STAKES_CATEGORIES = {"rescue"}
HIGH_STAKES_DISASTER_KEYWORDS = {
    "flood",
    "earthquake",
    "collapse",
    "building collapse",
    "landslide",
    "tsunami",
    "cyclone",
    "drowning",
    "fire",
}


def _normalize_text(value: str | None) -> str:
    return str(value or "").strip().lower()


def _is_valid_coordinates(lat, lng) -> bool:
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return False

    if not (-90 <= lat_f <= 90 and -180 <= lng_f <= 180):
        return False

    # 0,0 is used by fallback code when geocoding fails.
    if lat_f == 0.0 and lng_f == 0.0:
        return False

    return True


def _build_common_only_score(base_score: int) -> int:
    # Keeps pass-through reports reviewable without inflating them to auto-dispatch.
    return min(max(35 + int(base_score * 1.5), 0), 100)


def run_common_validation(data_dict: dict) -> dict:
    """
    Common checks that run for every report before trust scoring:
    - reporter phone format
    - geocoded location coordinates

    Returns:
        {
            "passed": bool,
            "phone_ok": bool,
            "coords_ok": bool,
            "base_score": int,          # 0..20 (10 per successful common check)
            "score": int,               # pass-through score derived from common checks
            "status": str,              # "Verified" | "Pending Verification"
            "reasons": list[str]
        }
    """
    reasons = []
    base_score = 0

    phone = (
        str(data_dict.get("reporter_phone", ""))
        .strip()
        .replace(" ", "")
        .replace("-", "")
    )
    phone_ok = phone.isdigit() and len(phone) == 10
    if phone_ok:
        base_score += 10
        reasons.append("+10: Common check passed — valid 10-digit phone number")
    else:
        reasons.append("+0: Common check failed — phone number missing or invalid")

    lat = data_dict.get("lat")
    lng = data_dict.get("lng")
    coords_ok = _is_valid_coordinates(lat, lng)
    if coords_ok:
        base_score += 10
        reasons.append("+10: Common check passed — valid geocoded coordinates")
    else:
        reasons.append("+0: Common check failed — location could not be geocoded")

    passed = phone_ok and coords_ok
    return {
        "passed": passed,
        "phone_ok": phone_ok,
        "coords_ok": coords_ok,
        "base_score": base_score,
        "score": _build_common_only_score(base_score),
        "status": "Verified" if passed else "Pending Verification",
        "reasons": reasons,
    }


def is_high_stakes_disaster(ai_category: str | None, disaster_type: str | None) -> bool:
    category = _normalize_text(ai_category)
    disaster = _normalize_text(disaster_type)
    return category in HIGH_STAKES_CATEGORIES or any(
        keyword in disaster for keyword in HIGH_STAKES_DISASTER_KEYWORDS
    )


def build_common_only_trust_result(
    common_validation: dict,
    ai_category: str | None = None,
    disaster_type: str | None = None,
) -> dict:
    """Builds a trust result when complex layers are intentionally skipped."""
    base_score = min(max(int(common_validation.get("base_score", 0)), 0), 20)
    score = _build_common_only_score(base_score)
    reasons = list(common_validation.get("reasons", []))
    reasons.append(
        (
            "+0: Complex trust layers skipped for non high-stakes report "
            f"(category='{_normalize_text(ai_category) or 'unknown'}', disaster='{_normalize_text(disaster_type) or 'unknown'}')"
        )
    )

    if common_validation.get("passed"):
        dispatch_action = "verified_common"
    else:
        dispatch_action = "pending_verification"

    return {
        "score": score,
        "dispatch_action": dispatch_action,
        "reasons": reasons,
    }


def calculate_trust_score(
    data_dict: dict,
    ai_consistency: int,
    corroborating_reports_count: int,
    ai_category: str | None = None,
    base_score: int = 0,
) -> dict:
    """
    Multi-layered trust scoring engine. Grades an incoming disaster report 0-100.

    Layers:
        Common checks run separately via run_common_validation (up to 20 pts baseline).
        Layer 2 (AI consistency):    up to 30 pts
        Layer 3 (External APIs):     up to 20 pts
        Layer 4 (Corroboration):     up to 40 pts (overall cap is 100)

    Category-based routing:
        - Complex trust layers are for high-stakes disasters only.
        - Non high-stakes reports receive a common-validation pass-through result.

    Returns:
        {
            "score":             int,            # 0-100
            "dispatch_action":   str,            # "auto_dispatch" | "human_review" | "flagged"
            "reasons":           list[str]       # human-readable explanation of each contribution
        }
    """
    try:
        base_score = min(max(int(base_score), 0), 20)
        score = base_score
        reasons = [f"+{base_score}: Common validation baseline (phone + geocoding)"]

        disaster_type = str(data_dict.get("disaster_type", "")).lower().strip()
        if not is_high_stakes_disaster(ai_category, disaster_type):
            reasons.append(
                "+0: Complex trust layers bypassed for non high-stakes report"
            )
            pass_through_score = _build_common_only_score(base_score)
            return {
                "score": pass_through_score,
                "dispatch_action": (
                    "human_review" if pass_through_score >= 50 else "flagged"
                ),
                "reasons": reasons,
            }

        lat = data_dict.get("lat")
        lng = data_dict.get("lng")
        phone = (
            str(data_dict.get("reporter_phone", ""))
            .strip()
            .replace(" ", "")
            .replace("-", "")
        )

        # -20 SPAM CHECK: duplicate phone within the last 1 hour with 'Video Connected' status
        try:
            from database.firestore_client import db

            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            if phone.isdigit() and len(phone) == 10:
                duplicate_docs = (
                    db.collection("needs_reports")
                    .where(filter=FieldFilter("reporter_phone", "==", phone))
                    .where(filter=FieldFilter("timestamp", ">=", one_hour_ago))
                    .stream()
                )
                video_connected_found = any(
                    doc.to_dict().get("status") == "Video Connected"
                    for doc in duplicate_docs
                )
                if video_connected_found:
                    score -= 20
                    reasons.append(
                        "-20: SPAM — same phone already submitted a 'Video Connected' report in the last 1 hour"
                    )
                else:
                    reasons.append(
                        "+0: No duplicate phone spam detected in the last 1 hour"
                    )
            else:
                reasons.append("+0: Spam check skipped (invalid phone)")
        except Exception as spam_err:
            reasons.append(f"+0: Spam check failed ({spam_err})")

        # ------------------------------------------------------------------ #
        # LAYER 2 — AI Consistency score (max 30 pts)
        # Each consistency point (0-10) is worth 3 score points.
        # ------------------------------------------------------------------ #
        consistency_points = min(max(int(ai_consistency), 0), 10) * 3  # clamp 0-30
        score += consistency_points
        reasons.append(
            f"+{consistency_points}: AI consistency score ({ai_consistency}/10)"
        )

        # ------------------------------------------------------------------ #
        # LAYER 3 — External Weather/Disaster API Correlation (max 20 pts)
        # Triggered only for high-stakes disasters.
        # ------------------------------------------------------------------ #
        # What users report vs what OpenWeatherMap reports
        WATER_DISASTERS = {"flood", "rain", "cyclone", "storm"}
        OWM_WATER_WEATHER = {"rain", "thunderstorm", "drizzle"}

        try:
            api_key = os.getenv("WEATHER_API")
            if lat is not None and lng is not None and api_key:
                resp = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lng, "appid": api_key},
                    timeout=5,
                )
                resp.raise_for_status()  # Catch HTTP errors

                # OWM returns weather[0].main (e.g., 'Rain', 'Clear', 'Clouds')
                weather_condition = resp.json()["weather"][0]["main"].lower()

                # Check for correlation
                if (
                    disaster_type in WATER_DISASTERS
                    and weather_condition in OWM_WATER_WEATHER
                ):
                    score += 20
                    reasons.append(
                        f"+20: Disaster type '{disaster_type}' corroborated by live weather API ({weather_condition})"
                    )
                else:
                    reasons.append(
                        f"+0: Live weather API ({weather_condition}) did not correlate with '{disaster_type}'"
                    )
            else:
                reasons.append(
                    "+0: Weather check skipped (Missing coordinates or OWM_API_KEY)"
                )

        except Exception as weather_err:
            reasons.append(f"+0: Weather API check failed ({weather_err})")

        # ------------------------------------------------------------------ #
        # LAYER 4 — Corroboration by nearby recent reports (max 40 pts)
        # ------------------------------------------------------------------ #
        if corroborating_reports_count >= 2:
            score += 40
            reasons.append(
                f"+40: {corroborating_reports_count} corroborating reports nearby in the last 2 hours"
            )
        elif corroborating_reports_count == 1:
            score += 25
            reasons.append("+25: 1 corroborating report nearby in the last 2 hours")
        else:
            reasons.append("+0: No nearby corroborating reports found")

        # ------------------------------------------------------------------ #
        # Final score — cap at 100
        # ------------------------------------------------------------------ #
        final_score = min(score, 100)

        # Determine dispatch action
        if final_score >= 80:
            dispatch_action = "auto_dispatch"
        elif final_score >= 50:
            dispatch_action = "human_review"
        else:
            dispatch_action = "flagged"

        return {
            "score": final_score,
            "dispatch_action": dispatch_action,
            "reasons": reasons,
        }

    except Exception as e:
        # Never crash the intake route — return a safe middle-ground score
        print(f"[Verification] Trust score calculation failed: {e}. Defaulting to 50.")
        return {
            "score": 50,
            "dispatch_action": "human_review",
            "reasons": [f"Verification engine error — defaulted to 50: {e}"],
        }
