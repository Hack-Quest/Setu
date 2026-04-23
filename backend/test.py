import requests
import json
import time
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

BASE_URL = os.getenv("SETU_BASE_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BASE_URL:
    raise RuntimeError("SETU_BASE_URL is not set. Add it to config/.env.")
if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")

HEADERS = {"Authorization": f"Bearer {SECRET_TOKEN}"}

def print_section(title):
    print(f"\n{'='*60}\n🚀 {title}\n{'='*60}")

def run_comprehensive_test():
    print_section("SCENARIO 1: HIGH-TRUST EMERGENCY")
    need_1 = {
        "reporter_name": "Amit Patel",
        "reporter_phone": "9876543210",
        "location": "Gomti Nagar, Lucknow", 
        "disaster_type": "flood",
        "help_needed": "evacuation",
        "description": "Water has entered the ground floor. It is knee-deep and rising. Need a boat to evacuate elderly parents."
    }
    print("📤 SENDING INPUT:")
    print(json.dumps(need_1, indent=2))
    
    res_1 = requests.post(f"{BASE_URL}/need", json=need_1, headers=HEADERS)
    print("\n📥 RECEIVED OUTPUT:")
    print(json.dumps(res_1.json(), indent=2))


    print_section("SCENARIO 2: LOW-TRUST SPAM REPORT")
    need_2 = {
        "reporter_name": "Unknown",
        "reporter_phone": "12345", # Invalid phone
        "location": "nowhere",     # Un-geocodable location
        "disaster_type": "earthquake",
        "help_needed": "food",
        "description": "send food fast plz" # Vague AI text
    }
    print("📤 SENDING INPUT:")
    print(json.dumps(need_2, indent=2))
    
    res_2 = requests.post(f"{BASE_URL}/need", json=need_2, headers=HEADERS)
    print("\n📥 RECEIVED OUTPUT (Look at Trust Score & Action):")
    print(json.dumps(res_2.json(), indent=2))


    print_section("SCENARIO 3: REGISTERING VOLUNTEERS")
    vol_1 = {
        "name": "NDRF Agent Rahul",
        "location": "Hazratganj, Lucknow",
        "skills": ["rescue", "medical", "boat", "evacuation"],
        "phone": "9998887776"
    }
    print("📤 SENDING VOLUNTEER INPUT:")
    print(json.dumps(vol_1, indent=2))
    
    res_vol = requests.post(f"{BASE_URL}/volunteer", json=vol_1, headers=HEADERS)
    print("\n📥 RECEIVED OUTPUT:")
    print(json.dumps(res_vol.json(), indent=2))


    print_section("SCENARIO 4: THE MATCH ENGINE")
    print("⏳ Waiting 2 seconds for Firestore to settle...")
    time.sleep(2)
    
    print("📤 TRIGGERING GET /match...")
    res_match = requests.get(f"{BASE_URL}/match", headers=HEADERS)
    print("\n📥 RECEIVED MATCHES (Should assign Amit, but ignore the spammer):")
    print(json.dumps(res_match.json(), indent=2))


    print_section("SCENARIO 5: DASHBOARD DATA")
    print("📤 TRIGGERING GET /dashboard...")
    res_dash = requests.get(f"{BASE_URL}/dashboard") # Public route, no headers
    print("\n📥 RECEIVED DASHBOARD STATS:")
    print(json.dumps(res_dash.json(), indent=2))

    print(f"\n{'='*60}\n🎉 COMPREHENSIVE TEST COMPLETE!\n{'='*60}\n")

if __name__ == "__main__":
    run_comprehensive_test()