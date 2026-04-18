import requests
import time
import json
from database.ngos_db import verify_ngo

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": "Bearer hackathon-secret"}

def print_step(text):
    print(f"\n--- {text} ---")

def main():
    # 1. Register and Verify NGO (The Tier 1 Anchor)
    print_step("NGO SETUP")
    ngo_res = requests.post(f"{BASE_URL}/ngo/register", json={
        "name": "Delhi Trauma Center", 
        "reg_number": f"REG-{int(time.time())}", 
        "lat": 28.61, "lng": 77.20, "radius": 50.0
    }).json()
    ngo_id = ngo_res["id"]
    verify_ngo(ngo_id, True) # Flip verified bit in Firestore [cite: 33]
    print(f"✅ NGO {ngo_id} verified as Tier 1")

    # 2. Register Volunteers
    print_step("VOLUNTEER REGISTRATION")
    # TIER 1: Use 'Medical' (Capitalized) to match the skill sensitivity map 
    requests.post(f"{BASE_URL}/volunteer_webhook", json={
        "volunteer_name": "Dr. Khanna", "phone": "9999911111",
        "skills": "Medical", "location": "Connaught Place", "ngo_id": ngo_id
    })
    
    # TIER 2: Community volunteer
    requests.post(f"{BASE_URL}/volunteer_webhook", json={
        "volunteer_name": "Sam Helper", "phone": "9999922222",
        "skills": "Medical", "location": "Connaught Place"
    })

    # 3. SCENARIO 1: NO TRUST (Spam Check)
    print_step("SCENARIO 1: SPAM FILTER")
    res1 = requests.post(f"{BASE_URL}/webhook", json={
        "name": "Spammer", "phone": "123", "address": "nowhere",
        "description": "short", "disaster_type": "none", "help_needed": "none"
    }).json()
    # Should trigger fallback or error in backend 
    print(f"Result: {res1.get('data', {}).get('dispatch_action', 'Blocked')}")

    # 4. SCENARIO 3: TIERED MATCHING
    print_step("SCENARIO 3: TIERED MATCHING")
    # Detailed description ensures trust > 80 
    sos_payload = {
        "name": "Victim", "phone": "9876543210", "address": "Connaught Place, New Delhi",
        "disaster_type": "Accident", "help_needed": "Medical",
        "description": "CRITICAL: Major road accident at Inner Circle. Multiple casualties. Need immediate trauma support."
    }
    res3 = requests.post(f"{BASE_URL}/webhook", json=sos_payload).json()
    need_id = res3["data"]["id"] # Use 'id' from NeedInput response 
    
    print(f"SOS Reported. Trust Score: {res3['data']['trust_score']}")
    print("Waiting for Firestore sync...")
    time.sleep(3)
    
    matches = requests.get(f"{BASE_URL}/match", headers=HEADERS).json()
    
    found = False
    for m in matches.get("matches", []):
        if m["need_id"] == need_id:
            found = True
            print(f"✅ Assigned: {m['assigned_volunteer']} | Tier: {m['volunteer_tier']}")
    
    if not found:
        print("❌ Match Engine failed to assign. Check Matcher radiuses.")

if __name__ == "__main__":
    main()