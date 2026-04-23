import requests
import time
import sys
import os
from dotenv import load_dotenv

# ===== LOAD ENV =====
load_dotenv(dotenv_path="config/.env")

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
TOKEN = os.getenv("SECRET_TOKEN")

if not TOKEN:
    print("❌ ERROR: SECRET_TOKEN not found in .env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# ===== UI =====
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def banner():
    clear()
    print("="*60)
    print("SETU AI - COMMAND TERMINAL")
    print("="*60)

# ===== HELPERS =====

def request(method, endpoint, payload=None):
    try:
        url = f"{BASE_URL}{endpoint}"
        if method == "GET":
            res = requests.get(url, headers=HEADERS, timeout=10)
        else:
            res = requests.post(url, json=payload, headers=HEADERS, timeout=10)

        return res.json()
    except Exception as e:
        print("❌ ERROR:", e)
        return None

# ===== CORE FUNCTIONS =====

def register_volunteer():
    print("\n--- REGISTER VOLUNTEER ---")

    name = input("Name: ")
    phone = input("Phone: ")
    location = input("Location: ")
    skills = input("Skills (comma separated): ")
    email = input("Email: ")
    password = input("Password: ")

    payload = {
        "name": name,
        "phone": phone,
        "location": location,
        "skills": [s.strip().lower() for s in skills.split(",")],
        "lat": 26.45,
        "lng": 80.33,
        "email": email,
        "password": password,
        "ngo_id": "ngo1",
        "credential_tags": [],
        
        # 🔥 CRITICAL FOR MATCHING
        "available": True,
        "ngo_verified": True
    }

    res = request("POST", "/volunteer", payload)
    print("\nResponse:", res)
    if res and "id" in res:
        print("👉 Volunteer ID:", res["id"])


def create_need():
    print("\n--- CREATE EMERGENCY NEED ---")

    desc = input("Describe emergency: ")

    payload = {
        "category": "medical",
        "severity": "critical",
        "lat": 26.45,
        "lng": 80.33,
        "description": desc,

        "reporter_name": "CLI User",
        "reporter_phone": "9999999999",
        "location_text": "Kanpur CLI",
        "disaster_type": "medical emergency",
        "help_needed": "medical"
    }

    print("\nCreating need...")
    res = request("POST", "/need", payload)
    print("Need:", res)

    print("\nTriggering matching...")
    match = request("GET", "/match")
    print("Match:", match)


def check_assignments():
    vid = input("Enter volunteer_id: ")

    res = request("GET", f"/assignment/volunteer/{vid}")
    print("\nAssignments:", res)


def dashboard():
    res = request("GET", "/dashboard")
    print("\nDashboard:", res)

def register_ngo():
    print("\n--- REGISTER NGO ---")

    name = input("NGO Name: ")
    email = input("Email: ")
    location = input("Location: ")

    reg_number = input("Registration Number (leave blank for auto): ")
    if not reg_number:
        import time
        reg_number = f"REG-{int(time.time())}"

    payload = {
        "name": name,
        "email": email,
        "location": location,
        "reg_number": reg_number
    }

    print("\n📤 Sending payload:", payload)  # DEBUG LINE

    res = request("POST", "/ngo/register", payload)
    print("\nResponse:", res)

    if res and "id" in res:
        print("👉 NGO ID:", res["id"])

def add_tier1_volunteer():
    print("\n--- ADD NGO VERIFIED VOLUNTEER ---")

    name = input("Name: ")
    phone = input("Phone: ")
    location = input("Location: ")
    skills = input("Skills (comma separated): ")
    email = input("Email: ")
    password = input("Password: ")
    ngo_id = input("NGO ID: ")

    payload = {
        "name": name,
        "phone": phone,
        "location": location,
        "skills": [s.strip().lower() for s in skills.split(",")],
        "lat": 26.45,
        "lng": 80.33,
        "email": email,
        "password": password,
        "ngo_id": ngo_id,
        "credential_tags": [],

        # 🔥 THIS IS THE KEY DIFFERENCE
        "ngo_verified": True,
        "available": True
    }

    res = request("POST", "/volunteer", payload)
    print(res)

def run_matching():
    print("\nRunning matching engine...")
    res = request("GET", "/match")
    print(res)

def view_all_assignments():
    res = request("GET", "/assignments")
    print(res)



# ===== MAIN LOOP =====

def main():
    while True:
        banner()
        print("1. Register NGO")
        print("2. Add NGO Verified Volunteer")
        print("3. Register Volunteer (Normal)")
        print("4. Create Emergency Need")
        print("5. Run Matching Engine")
        print("6. Check Volunteer Assignments")
        print("7. View Dashboard")
        print("8. Exit")

        choice = input("Choose: ")

        if choice == "1":
            register_ngo()
        elif choice == "2":
            add_tier1_volunteer()
        elif choice == "3":
            register_volunteer()
        elif choice == "4":
            create_need()
        elif choice == "5":
            run_matching()
        elif choice == "6":
            check_assignments()
        elif choice == "7":
            dashboard()
        elif choice == "8":
            sys.exit(0)
        else:
            print("Invalid choice")

        input("\nPress Enter to continue...")


if __name__ == "__main__":
    main()