import sys
import os
import io

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and type(sys.stdout).__name__ == "TextIOWrapper":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and type(sys.stderr).__name__ == "TextIOWrapper":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import time
from google.cloud.firestore_v1.base_query import FieldFilter
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.ngos_db import verify_ngo
from database.firestore_client import db

load_dotenv(dotenv_path="config/.env")

BASE_URL = os.getenv("SETU_BASE_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BASE_URL:
    raise RuntimeError("SETU_BASE_URL is not set. Add it to config/.env.")
if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")


def run_test():
    print("\n--- 1. Register Mock NGO ---")
    ngo_payload = {
        "name": "Global MedRescue NGO",
        "reg_number": "REG-" + str(int(time.time())),
        "lat": 28.6139,
        "lng": 77.2090,
        "radius": 50.0,
    }

    resp = requests.post(f"{BASE_URL}/ngo/register", json=ngo_payload)
    resp.raise_for_status()
    ngo_id = resp.json()["id"]
    print(f"NGO registered. ID: {ngo_id}")

    print("\n--- 2. Verify Mock NGO ---")
    verify_ngo(ngo_id, True)

    print("\n--- 3. Register Tier 1 Volunteer (NGO Assigned) ---")
    tier1_payload = {
        "volunteer_name": "Tier 1 Medic",
        "phone": "9999911111",
        "skills": "Medical",
        "location": "Gurugram",
        "ngo_id": ngo_id,
    }
    resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=tier1_payload)
    resp.raise_for_status()
    tier1_id = resp.json().get("id")
    print(f"Tier 1 Volunteer Registered (ID: {tier1_id})")

    print("\n--- 4. Register Tier 2 Volunteer (Community) ---")
    tier2_payload = {
        "volunteer_name": "Tier 2 Medic",
        "phone": "9999922222",
        "skills": "Medical",
        "location": "India Gate, New Delhi",
    }
    resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=tier2_payload)
    resp.raise_for_status()
    tier2_id = resp.json().get("id")
    print(f"Tier 2 Volunteer Registered (ID: {tier2_id})")

    # Give geocoding a second
    time.sleep(2)

    # Force reliable coordinates for the test:
    # Need Location: Lat 28.6130, Lng 77.2090
    # Tier 1 Vol: Lat 28.6100, Lng 77.2000 (~1.5 km away)
    # Tier 2 Vol: Lat 28.6120, Lng 77.2085 (~0.2 km away)
    db.collection("volunteers").document(tier1_id).update(
        {"lat": 28.6100, "lng": 77.2000}
    )
    db.collection("volunteers").document(tier2_id).update(
        {"lat": 28.6120, "lng": 77.2085}
    )

    print("\n--- 5. Report 'Medical' SOS ---")
    need_payload = {
        "name": "Accident Victim",
        "phone": "1231231234",
        "address": "Connaught Place, New Delhi",
        "disaster_type": "accident",
        "help_needed": "Medical",
        "description": "Urgent medical needed",
    }

    resp = requests.post(f"{BASE_URL}/webhook", json=need_payload)
    resp.raise_for_status()
    need_response = resp.json()
    need_id = need_response["data"]["id"]
    print(f"Need reported. ID: {need_id}")

    # Wait for the AI processing to run in the background
    print("Waiting for AI processing...")
    time.sleep(5)

    # Overwrite the Need's coordinate to be precise
    db.collection("needs_reports").document(need_id).update({"lat": 28.6130, "lng": 77.2090})

    print("\n--- 6. Running Match Engine manually to ensure assignment ---")
    headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
    resp = requests.get(f"{BASE_URL}/match", headers=headers)
    resp.raise_for_status()

    print("\n--- 7. Verifying Assignment ---")
    docs = (
        db.collection("assignments")
        .where(filter=FieldFilter("need_id", "==", need_id))
        .stream()
    )
    assignments = list(docs)

    if len(assignments) == 0:
        print("❌ No assignments found for this need.")
    else:
        assigned_vol_id = assignments[0].to_dict().get("volunteer_id")
        print(f"Assigned Volunteer ID: {assigned_vol_id}")
        if assigned_vol_id == tier1_id:
            print(
                "✅ SUCCESS: Tier 1 Medic was correctly chosen over closer Tier 2 Medic for sensitive 'Medical' SOS."
            )
        elif assigned_vol_id == tier2_id:
            print("❌ FAILURE: Closer Tier 2 Medic was chosen instead of Tier 1.")
        else:
            print("❌ Unknown volunteer assigned.")


if __name__ == "__main__":
    run_test()
