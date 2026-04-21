"""
╔══════════════════════════════════════════════════════════════╗
║           🌍  SETU AI — COMMAND LINE INTERFACE              ║
║           Full-Feature Offline + Online Control Panel        ║
╚══════════════════════════════════════════════════════════════╝

Usage (from project root, with backend running):
    python setu_cli.py

The backend must be started first in a separate terminal:
    uvicorn backend.main:app --reload

All features available:
  • Submit SOS (via /webhook)
  • Submit Need directly (via /need)
  • Register volunteer (webhook / auth)
  • Login volunteer
  • Register NGO
  • View NGO dashboard
  • View live tactical dashboard
  • Run AI matching engine
  • Resolve an assignment
  • View open needs list
  • AI triage test (offline)
  • Geocoding test (offline)
  • System health check
"""

import requests
import time
import sys
import os
import json
from getpass import getpass

# ──────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────
BASE_URL = os.getenv("SETU_BASE_URL", "http://127.0.0.1:8000")
SECRET_TOKEN = os.getenv("SETU_SECRET_TOKEN", "hackathon-secret")

HEADERS = {"Authorization": f"Bearer {SECRET_TOKEN}", "Content-Type": "application/json"}

REQUEST_TIMEOUT = 15  # seconds


# ──────────────────────────────────────────────────────────────
# TERMINAL COLOURS
# ──────────────────────────────────────────────────────────────
class C:
    HEADER   = '\033[95m'
    BLUE     = '\033[94m'
    CYAN     = '\033[96m'
    GREEN    = '\033[92m'
    YELLOW   = '\033[93m'
    RED      = '\033[91m'
    BOLD     = '\033[1m'
    UNDERLINE = '\033[4m'
    END      = '\033[0m'

def red(t):    return f"{C.RED}{t}{C.END}"
def green(t):  return f"{C.GREEN}{t}{C.END}"
def yellow(t): return f"{C.YELLOW}{t}{C.END}"
def cyan(t):   return f"{C.CYAN}{t}{C.END}"
def bold(t):   return f"{C.BOLD}{t}{C.END}"


# ──────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────
def clear():
    os.system('cls' if os.name == 'nt' else 'clear')

def pause():
    input(f"\n{cyan('Press Enter to return to menu...')}")

def divider(char="─", width=65):
    print(char * width)

def section(title: str):
    divider()
    print(bold(cyan(f"  {title}")))
    divider()

def slow_print(text: str, delay=0.018):
    for ch in text:
        sys.stdout.write(ch); sys.stdout.flush(); time.sleep(delay)
    print()

def _post(path: str, payload: dict, auth=True):
    h = HEADERS if auth else {"Content-Type": "application/json"}
    return requests.post(f"{BASE_URL}{path}", json=payload, headers=h, timeout=REQUEST_TIMEOUT)

def _get(path: str, auth=False):
    h = HEADERS if auth else {}
    return requests.get(f"{BASE_URL}{path}", headers=h, timeout=REQUEST_TIMEOUT)

def _patch(path: str, payload: dict):
    return requests.patch(f"{BASE_URL}{path}", json=payload, headers=HEADERS, timeout=REQUEST_TIMEOUT)

def print_json(data: dict):
    """Pretty-print a dict with colour-coded keys."""
    for k, v in data.items():
        val_str = str(v)
        if isinstance(v, (int, float)):
            val_str = yellow(val_str)
        elif isinstance(v, bool):
            val_str = green(val_str) if v else red(val_str)
        elif isinstance(v, list):
            val_str = cyan(str(v))
        elif isinstance(v, dict):
            val_str = "\n" + json.dumps(v, indent=6)
        print(f"  {bold(k)}: {val_str}")


# ──────────────────────────────────────────────────────────────
# BANNER
# ──────────────────────────────────────────────────────────────
def banner():
    clear()
    print(cyan(bold("═" * 65)))
    print(cyan(bold("   🌍  SETU AI — AUTONOMOUS DISASTER RESPONSE CLI")))
    print(cyan(bold("   Disaster · Dispatch · Relief")))
    print(cyan(bold("═" * 65)))
    print(f"  Backend  : {yellow(BASE_URL)}")
    print(f"  Auth     : {green('Bearer token loaded')}")
    print()


# ──────────────────────────────────────────────────────────────
# 1. HEALTH CHECK
# ──────────────────────────────────────────────────────────────
def health_check(verbose=True):
    try:
        resp = _get("/health")
        if resp.status_code == 200:
            if verbose:
                print(green("✅  Backend is online and healthy."))
                print_json(resp.json())
            return True
        else:
            if verbose:
                print(red(f"❌  Unexpected status: {resp.status_code}"))
            return False
    except requests.exceptions.ConnectionError:
        if verbose:
            print(red(f"❌  Cannot reach backend at {BASE_URL}"))
            print(yellow("   Start backend with: uvicorn backend.main:app --reload"))
        return False
    except Exception as e:
        if verbose:
            print(red(f"❌  Health check error: {e}"))
        return False


# ──────────────────────────────────────────────────────────────
# 2. SUBMIT SOS via webhook
# ──────────────────────────────────────────────────────────────
def submit_sos():
    section("🚨  SUBMIT SOS  — Webhook Mode")
    name          = input(bold("Reporter Name         : "))
    phone         = input(bold("Reporter Phone (10 digits): "))
    address       = input(bold("Location / Address    : "))
    disaster_type = input(bold("Disaster Type         : "))
    description   = input(bold("Emergency Description : "))

    payload = {
        "name": name, "phone": phone,
        "address": address, "disaster_type": disaster_type,
        "description": description
    }

    slow_print(yellow("\n[SETU]  Transmitting to AI Verification Engine..."), 0.01)

    try:
        resp = _post("/webhook", payload, auth=False)
        if resp.status_code == 200:
            data = resp.json().get("data", resp.json())
            slow_print(green("✅  AI Analysis Complete!"), 0.02)
            divider()
            print_json({
                "Severity"   : data.get("severity", "N/A"),
                "Category"   : data.get("category", "N/A"),
                "Trust Score": f"{data.get('trust_score', 'N/A')}/100",
                "Confidence" : data.get("confidence", "N/A"),
                "Action"     : str(data.get("dispatch_action", "N/A")).replace("_", " ").upper(),
                "Summary EN" : data.get("summary_en", ""),
                "Summary HI" : data.get("summary_local", ""),
            })
        else:
            print(red(f"❌  Server Error ({resp.status_code}): {resp.text}"))
    except requests.exceptions.Timeout:
        print(red("❌  Timeout: AI engine took too long."))
    except Exception as e:
        print(red(f"❌  Error: {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 3. SUBMIT NEED via /need (authenticated)
# ──────────────────────────────────────────────────────────────
def submit_need():
    section("📋  SUBMIT NEED  — Authenticated API Mode")
    name          = input(bold("Reporter Name         : "))
    phone         = input(bold("Reporter Phone (10 digits): "))
    location      = input(bold("Location              : "))
    disaster_type = input(bold("Disaster Type         : "))
    help_needed   = input(bold("Help Needed (skill tag): "))
    description   = input(bold("Emergency Description : "))

    payload = {
        "reporter_name": name, "reporter_phone": phone,
        "location": location, "disaster_type": disaster_type,
        "help_needed": help_needed, "description": description
    }

    slow_print(yellow("\n[SETU]  Processing with full trust-score pipeline..."), 0.01)

    try:
        resp = _post("/need", payload, auth=True)
        if resp.status_code == 200:
            data = resp.json()
            slow_print(green("✅  Need registered!"), 0.02)
            divider()
            print_json({
                "Need ID"    : data.get("id", "N/A"),
                "Severity"   : data.get("severity", "N/A"),
                "Category"   : data.get("category", "N/A"),
                "Trust Score": f"{data.get('trust_score', 'N/A')}/100",
                "Action"     : str(data.get("dispatch_action", "N/A")).replace("_", " ").upper(),
                "Status"     : data.get("status", "N/A"),
                "Verification Mode": data.get("verification_mode", "N/A"),
            })
        else:
            print(red(f"❌  Error ({resp.status_code}): {resp.text}"))
    except requests.exceptions.Timeout:
        print(red("❌  Timeout."))
    except Exception as e:
        print(red(f"❌  Error: {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 4. REGISTER VOLUNTEER (webhook, no auth)
# ──────────────────────────────────────────────────────────────
def register_volunteer_webhook():
    section("🦸  REGISTER VOLUNTEER  — Webhook Mode")
    name     = input(bold("Volunteer Name        : "))
    phone    = input(bold("Phone Number          : "))
    location = input(bold("Home Base / Location  : "))
    skills   = input(bold("Skills (comma-sep)    : "))

    payload = {
        "volunteer_name": name, "phone": phone,
        "location": location, "skills": skills
    }

    slow_print(yellow("\n[SETU]  Geocoding and saving volunteer..."), 0.01)

    try:
        resp = _post("/volunteer_webhook", payload, auth=False)
        if resp.status_code == 200:
            data = resp.json()
            slow_print(green(f"✅  Volunteer Registered!  DB ID: {data.get('id', 'N/A')}"), 0.02)
        else:
            print(red(f"❌  Error ({resp.status_code}): {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 5. REGISTER VOLUNTEER (auth endpoint)
# ──────────────────────────────────────────────────────────────
def register_volunteer_auth():
    section("🔐  VOLUNTEER SELF-REGISTRATION  — Auth Mode")
    email    = input(bold("Email                 : "))
    password = getpass(bold("Password              : "))
    name     = input(bold("Full Name             : "))
    phone    = input(bold("Phone (10 digits)     : "))
    location = input(bold("Current Location      : "))
    skills   = input(bold("Skills (comma-sep)    : "))

    payload = {
        "email": email, "password": password,
        "name": name, "phone": phone,
        "location": location,
        "skills": [s.strip() for s in skills.split(",")]
    }

    try:
        resp = _post("/auth/register", payload, auth=False)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"✅  Registered!  ID: {data.get('volunteer_id')}  Token: {data.get('token')}"))
        else:
            print(red(f"❌  ({resp.status_code}): {resp.json().get('detail', resp.text)}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 6. LOGIN VOLUNTEER
# ──────────────────────────────────────────────────────────────
def login_volunteer():
    section("🔑  VOLUNTEER LOGIN")
    email    = input(bold("Email    : "))
    password = getpass(bold("Password : "))

    try:
        resp = _post("/auth/login", {"email": email, "password": password}, auth=False)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"✅  Welcome back, {data.get('name')}!"))
            print(f"   Volunteer ID : {yellow(data.get('volunteer_id', 'N/A'))}")
            print(f"   Token        : {cyan(data.get('token', 'N/A'))}")
        elif resp.status_code == 401:
            print(red("❌  Invalid email or password."))
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 7. REGISTER NGO
# ──────────────────────────────────────────────────────────────
def register_ngo():
    section("🏢  REGISTER NGO")
    name       = input(bold("NGO Name              : "))
    reg_number = input(bold("Registration Number   : "))
    location   = input(bold("Coverage Area / City  : "))
    radius     = input(bold("Operational Radius (km, default 50): ") or "50")

    payload = {
        "name": name, "reg_number": reg_number,
        "location": location, "radius": float(radius or 50)
    }

    try:
        resp = _post("/ngo/register", payload, auth=True)
        if resp.status_code == 200:
            data = resp.json()
            print(green(f"✅  NGO Registered!  ID: {data.get('id')}"))
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 8. VIEW NGO DASHBOARD
# ──────────────────────────────────────────────────────────────
def view_ngo_dashboard():
    section("📊  NGO DASHBOARD")
    ngo_id = input(bold("NGO ID : "))

    try:
        resp = _get(f"/ngo/{ngo_id}/dashboard")
        if resp.status_code == 200:
            data = resp.json()
            stats = data.get("stats", {})
            print(bold("\n  ── NGO Statistics ──"))
            print(f"  Active Assignments  : {yellow(stats.get('active_assignments', 0))}")
            print(f"  Managed Volunteers  : {yellow(stats.get('managed_volunteers', 0))}")
            print(f"  Verified Professionals: {green(stats.get('verified_professionals', 0))}")

            assignments = data.get("active_assignments", [])
            if assignments:
                print(bold("\n  ── Active Assignments ──"))
                for a in assignments[:5]:
                    print(f"  [{a.get('priority','?')}] {a.get('title','?')} — Lead: {a.get('lead','?')}")

            volunteers = data.get("managed_volunteers", [])
            if volunteers:
                print(bold("\n  ── Managed Volunteers ──"))
                for v in volunteers[:5]:
                    print(f"  {v.get('name','?')} ({v.get('role','?')}) — {v.get('status','?')}")
        elif resp.status_code == 404:
            print(red(f"❌  NGO '{ngo_id}' not found."))
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 9. LIVE TACTICAL DASHBOARD
# ──────────────────────────────────────────────────────────────
def view_dashboard():
    section("📡  LIVE TACTICAL DASHBOARD")
    slow_print("  Fetching live telemetry from Firestore...", 0.01)

    try:
        resp = _get("/dashboard")
        if resp.status_code == 200:
            d = resp.json()
            print(f"\n{bold('  OVERVIEW')}")
            print(f"  Total Open Needs     : {yellow(d.get('total_needs', 0))}")
            print(f"  Available Volunteers : {green(d.get('total_volunteers', 0))}")

            print(f"\n{bold('  PRIORITY QUEUE')}")
            print(f"  {red('[!] Critical  :')} {d.get('critical_cases', 0)}")
            print(f"  {yellow('[-] High      :')} {d.get('high_priority_cases', 0)}")
            print(f"  {cyan('[~] Medium    :')} {d.get('medium_priority_cases', 0)}")
            print(f"  {green('[v] Low       :')} {d.get('low_priority_cases', 0)}")

            print(f"\n{bold('  SYSTEM QUEUES')}")
            print(f"  Unmatched Cases      : {yellow(d.get('unmatched_cases', 0))}")
            print(f"  Flagged for Review   : {red(d.get('flagged_cases', 0))}")

            recent = d.get("recent_need")
            if recent:
                print(f"\n{bold('  LATEST NEED')} : {recent.get('summary_en', 'N/A')}")
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 10. VIEW OPEN NEEDS LIST
# ──────────────────────────────────────────────────────────────
def view_open_needs():
    section("📋  OPEN NEEDS LIST")
    try:
        resp = _get("/dashboard/reports")
        if resp.status_code == 200:
            needs = resp.json()
            if not needs:
                print(green("  No open needs at this time."))
            else:
                for i, n in enumerate(needs, 1):
                    sev = n.get("severity", "?")
                    sev_coloured = red(sev) if sev == "critical" else yellow(sev)
                    print(f"  {bold(str(i))}. [{sev_coloured}]  ID: {n.get('id','?')}  "
                          f"Cat: {cyan(n.get('category','?'))}  "
                          f"Trust: {n.get('trust_score','?')}  "
                          f"Status: {n.get('status','?')}")
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 11. RUN AI MATCHING ENGINE
# ──────────────────────────────────────────────────────────────
def run_matching():
    section("🤖  AI MATCHING ENGINE")
    slow_print("  Running two-stage volunteer dispatch algorithm...", 0.01)

    try:
        resp = _get("/match", auth=True)
        if resp.status_code == 200:
            data = resp.json()
            print(f"\n  {bold('Total Needs Processed')} : {yellow(data.get('total_needs_processed', 0))}")
            print(f"  {bold('Matches Made')}          : {green(data.get('total_matches_made', 0))}")

            print(f"\n  {bold('Match Details:')}")
            for m in data.get("matches", []):
                status = m.get("status", "?")
                if status == "assigned":
                    line = (f"  ✅  Need {m.get('need_id','?')} → "
                            f"{green(m.get('assigned_volunteer','?'))} "
                            f"({m.get('volunteer_tier','?')}) "
                            f"{m.get('distance_km','?')} km")
                elif status == "Manual Escalation Required":
                    line = f"  🚨  Need {m.get('need_id','?')} → {red('ESCALATION REQUIRED')} — {m.get('reason','')}"
                else:
                    line = f"  ⏳  Need {m.get('need_id','?')} → {yellow('PENDING')} — {m.get('reason','')}"
                print(line)
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 12. RESOLVE ASSIGNMENT
# ──────────────────────────────────────────────────────────────
def resolve_assignment():
    section("✅  RESOLVE ASSIGNMENT")
    assignment_id = input(bold("Assignment ID   : "))
    need_id       = input(bold("Need ID         : "))
    volunteer_id  = input(bold("Volunteer ID    : "))

    try:
        resp = _patch(
            f"/assignment/{assignment_id}/resolve",
            {"need_id": need_id, "volunteer_id": volunteer_id}
        )
        if resp.status_code == 200:
            print(green("✅  Assignment resolved. Volunteer freed."))
            print_json(resp.json())
        elif resp.status_code == 404:
            print(red(f"❌  Assignment '{assignment_id}' not found."))
        elif resp.status_code == 409:
            print(yellow("⚠️   Assignment was already resolved."))
        else:
            print(red(f"❌  {resp.status_code}: {resp.text}"))
    except Exception as e:
        print(red(f"❌  {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 13. OFFLINE AI TRIAGE TEST
# ──────────────────────────────────────────────────────────────
def offline_ai_test():
    section("🧠  OFFLINE AI TRIAGE TEST")
    print(yellow("  (Requires GEMINI_API_KEY and GROQ_API_KEY in config/.env)"))
    description = input(bold("\nEnter emergency description: "))

    try:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)

        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT_DIR, "config", ".env"))

        from ai_processing.gemini_processor import process_need_text
        slow_print(yellow("  Processing with Gemini (fallback: Groq)..."), 0.015)
        result = process_need_text(description)

        print(f"\n{bold('  AI TRIAGE RESULT:')}")
        print_json(result)
    except Exception as e:
        print(red(f"❌  AI Test Error: {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# 14. OFFLINE GEOCODING TEST
# ──────────────────────────────────────────────────────────────
def offline_geocoding_test():
    section("🌍  OFFLINE GEOCODING TEST")
    address = input(bold("Enter address to geocode: "))

    try:
        ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        if ROOT_DIR not in sys.path:
            sys.path.insert(0, ROOT_DIR)

        from dotenv import load_dotenv
        load_dotenv(os.path.join(ROOT_DIR, "config", ".env"))

        from database.geocoding import get_coordinates
        slow_print(yellow("  Geocoding (Google Maps → OSM fallback)..."), 0.015)
        coords = get_coordinates(address)

        if coords:
            print(green(f"\n  ✅  Coordinates found!"))
            print(f"  Latitude  : {yellow(str(coords['lat']))}")
            print(f"  Longitude : {yellow(str(coords['lng']))}")
        else:
            print(red("  ❌  Could not geocode this address."))
    except Exception as e:
        print(red(f"❌  Geocoding Test Error: {e}"))
    pause()


# ──────────────────────────────────────────────────────────────
# MAIN MENU
# ──────────────────────────────────────────────────────────────
MENU = [
    ("",  bold(cyan("── OPERATIONS ──")),                      None),
    ("1",  "🚨  Submit SOS (Webhook)",                         submit_sos),
    ("2",  "📋  Submit Need (Authenticated API)",              submit_need),
    ("3",  "📡  View Live Dashboard",                          view_dashboard),
    ("4",  "📋  View Open Needs List",                         view_open_needs),
    ("5",  "🤖  Run AI Matching Engine",                       run_matching),
    ("6",  "✅  Resolve Assignment",                           resolve_assignment),
    ("",  bold(cyan("── VOLUNTEER ──")),                       None),
    ("7",  "🦸  Register Volunteer (Webhook)",                 register_volunteer_webhook),
    ("8",  "🔐  Register Volunteer (Auth/Self-Service)",       register_volunteer_auth),
    ("9",  "🔑  Login Volunteer",                              login_volunteer),
    ("",  bold(cyan("── NGO ──")),                             None),
    ("10", "🏢  Register NGO",                                 register_ngo),
    ("11", "📊  View NGO Dashboard",                           view_ngo_dashboard),
    ("",  bold(cyan("── TOOLS ──")),                           None),
    ("12", "💡  Health Check",                                 lambda: [health_check(), pause()]),
    ("13", "🧠  Offline AI Triage Test",                       offline_ai_test),
    ("14", "🌍  Offline Geocoding Test",                       offline_geocoding_test),
    ("",  bold(cyan("── SYSTEM ──")),                          None),
    ("0",  "🚪  Exit",                                         None),
]


def print_menu():
    for key, label, _ in MENU:
        if not key:
            print(f"\n  {label}")
        else:
            print(f"  [{bold(key):>3}]  {label}")
    print()


def main():
    print(yellow("  Pinging backend..."))
    if not health_check(verbose=False):
        print(yellow(f"\n  ⚠️   Backend not reachable at {BASE_URL}"))
        print(yellow("  Offline tools (13, 14) still work.\n"))
        time.sleep(1)

    while True:
        banner()
        print_menu()
        choice = input(bold("Command: ")).strip()

        for key, _, fn in MENU:
            if key == choice and fn is not None:
                try:
                    fn()
                except KeyboardInterrupt:
                    print(yellow("\n  [Cancelled]"))
                    time.sleep(0.5)
                break
        else:
            if choice == "0":
                slow_print(cyan("  Shutting down Setu CLI. Goodbye."))
                sys.exit(0)
            else:
                print(red("  ❌  Invalid option. Try again."))
                time.sleep(0.8)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{cyan('  Setu CLI terminated.')}")
        sys.exit(0)