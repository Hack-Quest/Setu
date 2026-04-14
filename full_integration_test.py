import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": "Bearer hackathon-secret"}


def print_header(title):
    print(f"\n{'='*50}\n🚀 {title}\n{'='*50}")


def test_scenario(name, endpoint, payload, expected_action=None):
    print(f"\n▶️ Running Scenario: {name}")
    try:
        response = requests.post(f"{BASE_URL}{endpoint}", json=payload, headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        print(f"✅ Success! HTTP 200")

        # 🧠 Check new fields
        if "trust_score" in data:
            print(f"   🛡️ Trust Score: {data.get('trust_score')}")
            print(f"   🚦 Dispatch: {data.get('dispatch_action')}")
            print(f"   ⭐ Priority: {data.get('priority')}")

        if "error" in data:
            print(f"   ❌ Error: {data.get('error')}")

        if expected_action and data.get("dispatch_action") != expected_action:
            print(f"   ⚠️ Expected {expected_action}, got {data.get('dispatch_action')}")

        return data

    except requests.exceptions.ConnectionError:
        print("🚨 ERROR: Server not running")
        return None
    except Exception as e:
        print(f"🚨 HTTP Error: {e}")
        if response is not None:
            print(response.text)
        return None


def main():
    print_header("FULL SYSTEM INTEGRATION TEST")

    # ---------------------------------------------------------
    # SCENARIO 1: VALID NEED (SHOULD PASS + PRIORITY)
    # ---------------------------------------------------------
    valid_need = {
        "reporter_name": "Rahul",
        "reporter_phone": "9876543210",
        "location": "Delhi",
        "disaster_type": "earthquake",
        "help_needed": "medical",
        "description": "Severe earthquake damage, multiple injured people need urgent medical help"
    }

    test_scenario("Valid Need (High Priority Expected)", "/need", valid_need)

    # ---------------------------------------------------------
    # SCENARIO 2: INVALID NEED (VALIDATION TEST)
    # ---------------------------------------------------------
    short_need = {
        "reporter_name": "Test",
        "reporter_phone": "123",
        "location": "Delhi",
        "disaster_type": "flood",
        "help_needed": "food",
        "description": "help"
    }

    test_scenario("Short Description (Validation Fail)", "/need", short_need)

    # ---------------------------------------------------------
    # SCENARIO 3: VOLUNTEER REGISTRATION
    # ---------------------------------------------------------
    print_header("VOLUNTEER TEST")

    volunteer_data = {
        "name": "Rescue Volunteer",
        "location": "Delhi",
        "skills": ["medical", "rescue"],
        "phone": "9998887776"
    }

    test_scenario("Volunteer Registration", "/volunteer", volunteer_data)

    # ---------------------------------------------------------
    # SCENARIO 4: MATCH ENGINE
    # ---------------------------------------------------------
    print_header("MATCHING TEST")

    try:
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/match", headers=HEADERS)
        res.raise_for_status()
        match_data = res.json()

        print("✅ Matching executed")
        print(f"   Matches: {match_data.get('total_matches_made')}")

        print(json.dumps(match_data.get("matches", []), indent=2))

    except Exception as e:
        print(f"🚨 Match Error: {e}")

    # ---------------------------------------------------------
    # SCENARIO 5: DASHBOARD
    # ---------------------------------------------------------
    print_header("DASHBOARD TEST")

    try:
        res = requests.get(f"{BASE_URL}/dashboard", headers=HEADERS)
        res.raise_for_status()
        dash_data = res.json()

        print("✅ Dashboard working")
        print(json.dumps(dash_data, indent=2))

    except Exception as e:
        print(f"🚨 Dashboard Error: {e}")

    print("\n" + "="*50)
    print("🎉 ALL TESTS COMPLETE")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()