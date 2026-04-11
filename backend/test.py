import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": "Bearer hackathon-secret"} 


def print_header(title):
    print(f"\n{'='*50}\n🚀 {title}\n{'='*50}")


def test_scenario(name, endpoint, payload, expected_action=None, use_auth=True):
    print(f"\n▶️ Running Scenario: {name}")
    try:
        headers = HEADERS if use_auth else {}

        response = requests.post(
            f"{BASE_URL}{endpoint}",
            json=payload,
            headers=headers
        )

        response.raise_for_status()
        data = response.json()

        print(f"✅ Success! Server responded with HTTP 200.")

        # Trust score check (if exists)
        if "trust_score" in data:
            print(f"   🛡️ Trust Score: {data.get('trust_score')}/100")
            print(f"   🚦 Action: {data.get('dispatch_action')}")
            print(f"   📝 Reasons: {data.get('verification_reasons', [])}")

            if expected_action and data.get('dispatch_action') != expected_action:
                print(f"   ⚠️ WARNING: Expected '{expected_action}' but got '{data.get('dispatch_action')}'")

        return data

    except requests.exceptions.ConnectionError:
        print("🚨 ERROR: Connection Refused. Is your FastAPI server running?")
        return None

    except Exception as e:
        print(f"🚨 HTTP Error: {e}")
        try:
            print(f"Response output: {response.text}")
        except:
            pass
        return None


def main():
    print_header("STARTING SYSTEM-WIDE INTEGRATION TESTS")

    # ---------------------------------------------------------
    # SCENARIO 1: Perfect Need
    # ---------------------------------------------------------
    perfect_need = {
        "reporter_name": "Rahul Sharma",
        "reporter_phone": "9876543210",
        "location": "Gomti Nagar, Lucknow",
        "disaster_type": "flood",
        "help_needed": "evacuation",
        "description": "Water rising fast, need urgent rescue."
    }
    test_scenario("High-Trust Flood Report", "/need", perfect_need, "auto_dispatch")

    # ---------------------------------------------------------
    # 🔗 NEW SCENARIO: WEBHOOK TEST (IMPORTANT)
    # ---------------------------------------------------------
    print_header("TESTING WEBHOOK (/webhook)")

    webhook_data = {
        "description": "Need medical help urgently",
        "location": "Delhi",
        "disaster_type": "earthquake",
        "help_needed": "medical"
    }

    test_scenario(
        "Webhook Flow Test",
        "/webhook",
        webhook_data,
        use_auth=False  # 🔥 webhook me token nahi hota
    )

    # ---------------------------------------------------------
    # SCENARIO 2: Spam
    # ---------------------------------------------------------
    spam_need = {
        "reporter_name": "Anon",
        "reporter_phone": "123",
        "location": "asdfghjkl",
        "disaster_type": "earthquake",
        "help_needed": "food",
        "description": "send food fast"
    }
    test_scenario("Suspicious Spam Report", "/need", spam_need, "flagged")

    # ---------------------------------------------------------
    # SCENARIO 3: Volunteer
    # ---------------------------------------------------------
    print_header("TESTING VOLUNTEER PIPELINE")

    volunteer_data = {
        "name": "Rescue Volunteer",
        "location": "Delhi",
        "skills": ["rescue", "medical"],
        "phone": "9998887776"
    }

    test_scenario("Register Volunteer", "/volunteer", volunteer_data)

    # ---------------------------------------------------------
    # SCENARIO 4: Matching
    # ---------------------------------------------------------
    print_header("TESTING MATCHING")

    try:
        time.sleep(2)
        res = requests.get(f"{BASE_URL}/match")
        res.raise_for_status()
        data = res.json()

        print("✅ Matching Engine ran successfully!")
        print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"🚨 Match Engine Error: {e}")

    # ---------------------------------------------------------
    # SCENARIO 5: Dashboard
    # ---------------------------------------------------------
    print_header("TESTING DASHBOARD")

    try:
        res = requests.get(f"{BASE_URL}/dashboard")
        res.raise_for_status()
        data = res.json()

        print("✅ Dashboard working!")
        print(json.dumps(data, indent=2))

    except Exception as e:
        print(f"🚨 Dashboard Error: {e}")

    print("\n" + "="*50)
    print("🎉 ALL TESTS COMPLETE!")
    print("="*50 + "\n")


if __name__ == "__main__":
    main()