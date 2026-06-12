import requests
import sys
import os
import io

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and type(sys.stdout).__name__ == "TextIOWrapper":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and type(sys.stderr).__name__ == "TextIOWrapper":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import json
from getpass import getpass
import csv
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

# ================= CONFIG =================
BASE_URL = os.getenv("SETU_API_BASE_URL") or os.getenv("SETU_BASE_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BASE_URL:
    print("❌ ERROR: SETU_BASE_URL not set in config/.env")
    sys.exit(1)
if not SECRET_TOKEN:
    print("❌ ERROR: SECRET_TOKEN not set in config/.env")
    sys.exit(1)

HEADERS = {
    "Authorization": f"Bearer {SECRET_TOKEN}",
    "Content-Type": "application/json"
}

REQUEST_TIMEOUT = 15

# ================= COLORS =================
class C:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    END = '\033[0m'

def red(t): return f"{C.RED}{t}{C.END}"
def green(t): return f"{C.GREEN}{t}{C.END}"
def yellow(t): return f"{C.YELLOW}{t}{C.END}"
def cyan(t): return f"{C.CYAN}{t}{C.END}"
def bold(t): return f"{C.BOLD}{t}{C.END}"

# ================= HELPERS =================
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input("\nPress Enter to continue...")

def section(title):
    print("\n" + "="*60)
    print(bold(cyan(title)))
    print("="*60)

def _post(path, payload, auth=True):
    headers = HEADERS if auth else {"Content-Type": "application/json"}
    return requests.post(f"{BASE_URL}{path}", json=payload, headers=headers, timeout=REQUEST_TIMEOUT)

def _get(path, auth=False):
    headers = HEADERS if auth else {}
    return requests.get(f"{BASE_URL}{path}", headers=headers, timeout=REQUEST_TIMEOUT)

def safe_json(res):
    try:
        return res.json()
    except:
        return {"error": res.text}

def handle_response(res):
    if res.status_code != 200:
        print(red(f"❌ Error {res.status_code}: {res.text}"))
        return None
    return safe_json(res)

def print_json(data):
    print(json.dumps(data, indent=2))

# ================= LOGIN =================
def login():
    section("LOGIN")

    email = input("Email: ")
    password = getpass("Password: ")

    res = _post("/auth/login", {"email": email, "password": password}, auth=False)
    data = handle_response(res)
    if not data:
        pause()
        return

    if "token" in data:
        HEADERS["Authorization"] = f"Bearer {data['token']}"
        print(green("✅ Login successful"))

        role = data.get("role")
        if role == "ngo":
            print(cyan("Logged in as NGO"))
        elif role == "volunteer":
            print(cyan("Logged in as Volunteer"))
        else:
            print(yellow("Unknown role"))
    else:
        print_json(data)

    pause()

# ================= NGO =================
def register_ngo():
    section("REGISTER NGO")

    payload = {
        "name": input("NGO Name: "),
        "reg_number": input("Registration Number: "),
        "location": input("Location: "),
        "radius": float(input("Radius (default 50): ") or "50"),
        "email": input("Email (optional): ") or None,
        "password": getpass("Password (optional): ") or None
    }

    res = _post("/ngo/register", payload)
    data = handle_response(res)
    if not data:
        pause()
        return

    print_json(data)

    if "id" in data:
        print(green("✅ NGO CREATED"))
        print("👉 NGO ID:", data["id"])

    pause()

# ================= VOLUNTEER (AUTH) =================
def register_volunteer():
    section("REGISTER VOLUNTEER (LOGIN USER)")

    skills_input = input("Skills (comma separated): ")

    payload = {
        "name": input("Name: "),
        "email": input("Email: "),
        "password": getpass("Password: "),
        "phone": input("Phone: "),
        "location": input("Location: "),
        "skills": [s.strip().lower() for s in skills_input.split(",") if s.strip()]
    }

    res = _post("/auth/register", payload, auth=False)
    data = handle_response(res)
    if not data:
        pause()
        return

    print(green("✅ Volunteer Registered (Login Enabled)"))
    print_json(data)

    pause()

# ================= NEED =================
def create_need():
    section("CREATE NEED")

    print("\n--- DISASTER CONTEXT ---")
    print("1. Flood\n2. Fire\n3. Earthquake\n4. Medical\n5. Other")
    disaster_choice = input("Choose: ")

    disaster_map = {
        "1": "flood",
        "2": "fire",
        "3": "earthquake",
        "4": "medical",
        "5": "other"
    }

    disaster = disaster_map.get(disaster_choice, "other")

    print("\n--- NEED TYPE ---")
    print("1. Medical\n2. Transport\n3. Food\n4. Rescue\n5. Shelter")
    help_choice = input("Choose: ")

    help_map = {
        "1": "medical",
        "2": "transport",
        "3": "food",
        "4": "rescue",
        "5": "shelter"
    }

    help_needed = help_map.get(help_choice, "general")

    payload = {
        "disaster_type": disaster,
        "help_needed": help_needed,
        "category": help_needed,
        "need_type": f"{disaster}_{help_needed}",
        "reporter_name": input("Reporter Name: "),
        "reporter_phone": input("Phone: "),
        "location_text": input("Location: "),
        "description": input("Description: "),
        "lat": 26.45,
        "lng": 80.33
    }

    print("\n📤 Sending:", payload)

    res = _post("/need", payload)
    data = handle_response(res)
    if not data:
        pause()
        return

    print(green("\n✅ Need Created"))
    print_json(data)

    print(yellow("\n⚡ Running matching..."))
    match = _get("/match", auth=True)
    print_json(safe_json(match))

    pause()

# ================= BULK UPLOAD =================
def bulk_upload_volunteers():
    section("BULK VOLUNTEER UPLOAD")

    file_path = input("CSV file path: ")
    ngo_id = input("NGO ID: ")

    try:
        with open(file_path, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)

            success = failed = 0

            for row in reader:
                # Skills may be a comma-separated string in CSV
                raw_skills = row.get("skills") or row.get("Skills") or ""
                skills_list = [s.strip().lower() for s in raw_skills.split(",") if s.strip()]

                payload = {
                    "name": row.get("name") or row.get("Name") or "Unknown",
                    "phone": str(row.get("phone") or row.get("Phone") or "0000000000"),
                    "location": row.get("location") or row.get("Location") or "",
                    "skills": skills_list,
                    "email": row.get("email") or f"vol_{os.urandom(4).hex()}@setu.internal",
                    "password": "BulkUpload!1",
                    "ngo_id": ngo_id
                }

                res = _post("/volunteer", payload, auth=True)

                if res.status_code == 200:
                    success += 1
                else:
                    failed += 1
                    print(red(f"  ❌ Failed for {payload['name']}: {res.text}"))

    except Exception as e:
        print(red(f"Error: {e}"))

    pause()

# ================= MATCH =================
def run_match():
    section("MATCHING ENGINE")

    res = _get("/match", auth=True)
    data = safe_json(res)

    for m in data.get("matches", []):
        status = m.get("status")
        need_id = m.get("need_id")
        severity = m.get("severity", "low")

        if status == "assigned":
            volunteers = m.get("assigned_volunteers", [])
            vol_names = ", ".join([f"{v.get('name', 'Unknown')} ({v.get('distance_km', 'N/A')}km)" for v in volunteers])
            print(green(
                f"🚑 Need {need_id} [{severity.upper()}] → Assigned to: {vol_names}"
            ))
        else:
            print(yellow(
                f"⚠️ Need {need_id} [{severity.upper()}] → {m.get('reason', 'No match')}"
            ))

    pause()

# ================= ASSIGNMENTS =================
def check_assignments():
    section("CHECK ASSIGNMENTS")

    vid = input("Volunteer ID: ")
    res = _get(f"/assignment/volunteer/{vid}", auth=True)
    print_json(safe_json(res))

    pause()

# ================= NGO DASHBOARD =================
def ngo_dashboard():
    section("NGO DASHBOARD")

    ngo_id = input("NGO ID: ")
    res = _get(f"/ngo/{ngo_id}/dashboard", auth=True)
    print_json(safe_json(res))

    pause()

# ================= HEALTH =================
def health():
    section("HEALTH CHECK")
    res = _get("/health")
    print_json(safe_json(res))
    pause()

# ================= MENU =================
def main():
    while True:
        clear()
        print(bold("===== SETU CLI =====\n"))
        print("0. Login")
        print("1. Register NGO")
        print("2. Register Volunteer (Login User)")
        print("3. Create Need")
        print("4. Run Matching")
        print("5. Check Volunteer Assignments")
        print("6. NGO Dashboard")
        print("7. Health Check")
        print("8. Bulk Upload Volunteers (CSV)")
        print("9. Exit\n")

        choice = input("Choose: ")

        if choice == "0": login()
        elif choice == "1": register_ngo()
        elif choice == "2": register_volunteer()
        elif choice == "3": create_need()
        elif choice == "4": run_match()
        elif choice == "5": check_assignments()
        elif choice == "6": ngo_dashboard()
        elif choice == "7": health()
        elif choice == "8": bulk_upload_volunteers()
        elif choice == "9": sys.exit()
        else:
            print("Invalid choice")

        pause()

if __name__ == "__main__":
    main()