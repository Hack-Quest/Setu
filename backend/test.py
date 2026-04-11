import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"
# Matches the secret in your need.py
HEADERS = {"Authorization": "Bearer hackathon-secret"} 

def print_header(title):
    print(f"\n{'='*50}\n🚀 {title}\n{'='*50}")

def test_scenario(name, endpoint, payload, expected_action=None):
    print(f"\n▶️ Running Scenario: {name}")
    try:
        response = requests.post(f"{BASE_URL}{endpoint}", json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()
        
        print(f"✅ Success! Server responded with HTTP 200.")
        
        # If testing a Need, check the Trust Score engine results
        if "trust_score" in data:
            print(f"   🛡️ Trust Score: {data.get('trust_score')}/100")
            print(f"   🚦 Action: {data.get('dispatch_action')}")
            print(f"   📝 Reasons: {data.get('verification_reasons', [])}")
            
            if expected_action and data.get('dispatch_action') != expected_action:
                print(f"   ⚠️ WARNING: Expected '{expected_action}' but got '{data.get('dispatch_action')}'")
        
        return data
    except requests.exceptions.ConnectionError:
        print("🚨 ERROR: Connection Refused. Is your FastAPI server running on port 8000?")
        return None
    except Exception as e:
        print(f"🚨 HTTP Error: {e}")
        if response is not None:
            print(f"   Response output: {response.text}")
        return None

def main():
    print_header("STARTING SYSTEM-WIDE INTEGRATION TESTS")

    # ---------------------------------------------------------
    # SCENARIO 1: The Perfect Report (High Trust -> Auto Dispatch)
    # ---------------------------------------------------------
    perfect_need = {
        "reporter_name": "Rahul Sharma",
        "reporter_phone": "9876543210", # Valid 10-digit
        "location": "Gomti Nagar, Lucknow", # Valid location
        "disaster_type": "flood",
        "help_needed": "evacuation",
        "description": "The Gomti river overflowed. Water is knee-deep in Sector 4 and rising fast. Need immediate rescue for elderly neighbors."
    }
    test_scenario("High-Trust Flood Report", "/need", perfect_need, "auto_dispatch")


    # ---------------------------------------------------------
    # SCENARIO 2: The Lazy Spammer (Low Trust -> Flagged)
    # ---------------------------------------------------------
    spam_need = {
        "reporter_name": "Anon",
        "reporter_phone": "123", # Invalid phone
        "location": "asdfghjkl", # Invalid location
        "disaster_type": "earthquake",
        "help_needed": "food",
        "description": "send food fast plz" # Vague AI consistency
    }
    test_scenario("Suspicious Spam Report", "/need", spam_need, "flagged")


    # ---------------------------------------------------------
    # SCENARIO 3: The Corroboration Trigger (Layer 4 Bonus)
    # ---------------------------------------------------------
    print("\n▶️ Running Scenario: Corroboration Check")
    print("   Submitting a second flood report in the same area to trigger Layer 4...")
    corroborating_need = {
        "reporter_name": "Priya Singh",
        "reporter_phone": "9123456780",
        "location": "Gomti Nagar, Lucknow",
        "disaster_type": "flood",
        "help_needed": "boat",
        "description": "Water is entering our ground floor. Need a boat for 3 people."
    }
    test_scenario("Corroborating Flood Report", "/need", corroborating_need, "auto_dispatch")


    # ---------------------------------------------------------
    # SCENARIO 4: Volunteer Registration
    # ---------------------------------------------------------
    print_header("TESTING VOLUNTEER PIPELINE")
    volunteer_data = {
        "name": "NDRF Rescue Agent 01",
        "location": "Hazratganj, Lucknow",
        "skills": ["rescue", "medical", "boat"],
        "phone": "9998887776"
    }
    test_scenario("Registering Expert Volunteer", "/volunteer", volunteer_data)


    # ---------------------------------------------------------
    # SCENARIO 5: The Match Engine
    # ---------------------------------------------------------
    print_header("TESTING SMART ASSIGNMENT ENGINE")
    try:
        # Give the DB a second to settle
        time.sleep(2) 
        print("Calling GET /match ...")
        res = requests.get(f"{BASE_URL}/match")
        res.raise_for_status()
        match_data = res.json()
        print(f"✅ Matching Engine ran successfully!")
        print(f"   Matches Made: {match_data.get('new_matches_made', 0)}")
        print(json.dumps(match_data.get('matches', []), indent=2))
    except Exception as e:
        print(f"🚨 Match Engine Error: {e}")

    # ---------------------------------------------------------
    # SCENARIO 6: Dashboard Statistics
    # ---------------------------------------------------------
    print_header("TESTING DASHBOARD FEED")
    try:
        res = requests.get(f"{BASE_URL}/dashboard")
        res.raise_for_status()
        dash_data = res.json()
        print("✅ Dashboard stats fetched successfully!")
        print(json.dumps(dash_data, indent=2))
    except Exception as e:
        print(f"🚨 Dashboard Error: {e}")

    print("\n" + "="*50)
    print("🎉 ALL INTEGRATION TESTS COMPLETE!")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()