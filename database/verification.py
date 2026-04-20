import os
import requests
import dotenv
from datetime import datetime, timezone, timedelta
dotenv.load_dotenv()

def calculate_trust_score(data_dict: dict, ai_consistency: int, corroborating_reports_count: int) -> dict:
    """
    Multi-layered trust scoring engine. Grades an incoming disaster report 0-100.

    Layers:
        Layer 1 (Automated checks):  up to 20 pts
        Layer 2 (AI consistency):    up to 30 pts
        Layer 3 (Live Weather API):  up to 20 pts
        Layer 4 (Corroboration):     up to 40 pts (but overall cap is 100)

    Returns:
        {
            "score":             int,            # 0-100
            "dispatch_action":   str,            # "auto_dispatch" | "human_review" | "flagged"
            "reasons":           list[str]       # human-readable explanation of each contribution
        }
    """
    try:
        score = 0
        reasons = []

        # ------------------------------------------------------------------ #
        # LAYER 1 — Automated sanity checks (max 20 pts)
        # ------------------------------------------------------------------ #

        # +10 if geocoding produced valid coordinates
        lat = data_dict.get("lat")
        lng = data_dict.get("lng")
        if lat is not None and lng is not None:
            score += 10
            reasons.append("+10: Valid location coordinates found")
        else:
            reasons.append("+0: Location could not be geocoded")

        # +10 if reporter's phone is exactly 10 digits
        phone = str(data_dict.get("reporter_phone", "")).strip().replace(" ", "").replace("-", "")
        if phone.isdigit() and len(phone) == 10:
            score += 10
            reasons.append("+10: Valid 10-digit phone number")
        else:
            reasons.append("+0: Phone number missing or invalid")

        # -20 SPAM CHECK: duplicate phone within the last 1 hour with 'Video Connected' status
        try:
            from database.firestore_client import db
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            if phone.isdigit() and len(phone) == 10:
                duplicate_docs = (
                    db.collection("needs_reports")
                    .where("reporter_phone", "==", phone)
                    .where("timestamp", ">=", one_hour_ago)
                    .stream()
                )
                video_connected_found = any(
                    doc.to_dict().get("status") == "Video Connected"
                    for doc in duplicate_docs
                )
                if video_connected_found:
                    score -= 20
                    reasons.append("-20: SPAM — same phone already submitted a 'Video Connected' report in the last 1 hour")
                else:
                    reasons.append("+0: No duplicate phone spam detected in the last 1 hour")
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
        reasons.append(f"+{consistency_points}: AI consistency score ({ai_consistency}/10)")

        # ------------------------------------------------------------------ #
        # LAYER 3 — Live Weather API Correlation (max 20 pts)
        # Hits OpenWeatherMap to verify conditions at the exact lat/lng
        # ------------------------------------------------------------------ #
        disaster_type = str(data_dict.get("disaster_type", "")).lower().strip()
        
        # What users report vs what OpenWeatherMap reports
        WATER_DISASTERS = {"flood", "rain", "cyclone", "storm"}
        OWM_WATER_WEATHER = {"rain", "thunderstorm", "drizzle"} 

        try:
            api_key = os.getenv("WEATHER_API")
            if lat is not None and lng is not None and api_key:
                resp = requests.get(
                    "https://api.openweathermap.org/data/2.5/weather",
                    params={"lat": lat, "lon": lng, "appid": api_key},
                    timeout=5
                )
                resp.raise_for_status() # Catch HTTP errors
                
                # OWM returns weather[0].main (e.g., 'Rain', 'Clear', 'Clouds')
                weather_condition = resp.json()["weather"][0]["main"].lower()
                
                # Check for correlation
                if disaster_type in WATER_DISASTERS and weather_condition in OWM_WATER_WEATHER:
                    score += 20
                    reasons.append(f"+20: Disaster type '{disaster_type}' corroborated by live weather API ({weather_condition})")
                else:
                    reasons.append(f"+0: Live weather API ({weather_condition}) did not correlate with '{disaster_type}'")
            else:
                reasons.append("+0: Weather check skipped (Missing coordinates or OWM_API_KEY)")
                
        except Exception as weather_err:
            reasons.append(f"+0: Weather API check failed ({weather_err})")

        # ------------------------------------------------------------------ #
        # LAYER 4 — Corroboration by nearby recent reports (max 40 pts)
        # ------------------------------------------------------------------ #
        if corroborating_reports_count >= 2:
            score += 40
            reasons.append(f"+40: {corroborating_reports_count} corroborating reports nearby in the last 2 hours")
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
            "reasons": reasons
        }

    except Exception as e:
        # Never crash the intake route — return a safe middle-ground score
        print(f"[Verification] Trust score calculation failed: {e}. Defaulting to 50.")
        return {
            "score": 50,
            "dispatch_action": "human_review",
            "reasons": [f"Verification engine error — defaulted to 50: {e}"]
        }