import requests
import time
import sys
import os
import io

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and type(sys.stdout).__name__ == "TextIOWrapper":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and type(sys.stderr).__name__ == "TextIOWrapper":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

# Configuration
BASE_URL = os.getenv("SETU_BASE_URL")
if not BASE_URL:
    raise RuntimeError("SETU_BASE_URL is not set. Add it to config/.env.")

# ANSI Colors for a cinematic terminal UI
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def slow_print(text, delay=0.02):
    """Prints text character by character for a hacker/cinematic effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear_screen()
    print(Colors.CYAN + Colors.BOLD + "=" * 65)
    print(" 🌍 SETU AI - AUTONOMOUS DISPATCH COMMAND CENTER")
    print("=" * 65 + Colors.ENDC)
    print(" Status: " + Colors.GREEN + "ONLINE & SECURE" + Colors.ENDC)
    print(" Target: " + Colors.WARNING + BASE_URL + Colors.ENDC + "\n")

def check_health():
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        return True
    except requests.exceptions.RequestException:
        return False

def submit_sos():
    print(Colors.FAIL + "\n--- [ INITIATE SOS PROTOCOL ] ---" + Colors.ENDC)
    name = input("Reporter Name: ")
    phone = input("Reporter Phone (10 digits): ")
    address = input("Location/Address: ")
    disaster_type = input("Disaster Type (e.g., Flood, Earthquake): ")
    description = input("Describe the Emergency: ")

    payload = {
        "name": name,
        "phone": phone,
        "address": address,
        "disaster_type": disaster_type,
        "description": description
    }

    print(Colors.WARNING + "\n[SYSTEM] Transmitting to Setu AI Verification Engine..." + Colors.ENDC)
    time.sleep(0.5)
    slow_print(Colors.BLUE + ">> Cross-referencing weather APIs & running NLP analysis..." + Colors.ENDC, 0.01)
    
    try:
        # ✅ Strict 10-second timeout prevents freezing
        response = requests.post(f"{BASE_URL}/webhook", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            slow_print(Colors.GREEN + "✅ Analysis Complete! Target Triage Locked." + Colors.ENDC)
            
            # Safely extract the AI nested data
            parsed = data.get("data", {})
            if not isinstance(parsed, dict):
                parsed = {}

            print(f"\n{Colors.BOLD}--- TACTICAL AI REPORT ---{Colors.ENDC}")
            print(f"Severity:     {Colors.FAIL}{str(parsed.get('severity', 'N/A')).upper()}{Colors.ENDC}")
            print(f"Category:     {Colors.CYAN}{str(parsed.get('category', 'N/A')).upper()}{Colors.ENDC}")
            print(f"Trust Score:  {Colors.WARNING}{parsed.get('trust_score', 'N/A')}/100{Colors.ENDC}")
            print(f"Confidence:   {Colors.GREEN}{str(parsed.get('confidence', 'N/A')).upper()}{Colors.ENDC}")
            print(f"Action:       {Colors.BOLD}{str(parsed.get('dispatch_action', 'N/A')).replace('_', ' ').upper()}{Colors.ENDC}")
        else:
            print(Colors.FAIL + f"❌ Server Error: {response.text}" + Colors.ENDC)
            
    except requests.exceptions.Timeout:
        print(Colors.FAIL + "❌ Connection Error: Read timed out (AI Engine took longer than 10s)." + Colors.ENDC)
    except requests.exceptions.RequestException as e:
        print(Colors.FAIL + f"❌ Connection Error: {e}" + Colors.ENDC)
    
    input("\nPress Enter to return to Command Center...")

def register_volunteer():
    print(Colors.BLUE + "\n--- [ VOLUNTEER FIELD REGISTRATION ] ---" + Colors.ENDC)
    name = input("Volunteer Name: ")
    phone = input("Phone Number: ")
    address = input("Home Base / Current Location: ")
    skills = input("Skills (comma separated, e.g., medical, rescue): ")

    payload = {
        "volunteer_name": name,
        "phone": phone,
        "location": address,
        "skills": skills
    }

    print(Colors.WARNING + "\n[SYSTEM] Geocoding coordinates and hashing credentials..." + Colors.ENDC)
    
    try:
        # ✅ Strict timeout applied
        response = requests.post(f"{BASE_URL}/volunteer_webhook", json=payload, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            slow_print(Colors.GREEN + f"✅ Volunteer Secured! Assigned DB ID: {data.get('id')}" + Colors.ENDC)
        else:
            print(Colors.FAIL + f"❌ Server Error: {response.text}" + Colors.ENDC)
            
    except requests.exceptions.Timeout:
        print(Colors.FAIL + "❌ Connection Error: Read timed out." + Colors.ENDC)
    except requests.exceptions.RequestException as e:
        print(Colors.FAIL + f"❌ Connection Error: {e}" + Colors.ENDC)

    input("\nPress Enter to return to Command Center...")

def view_dashboard():
    print(Colors.CYAN + "\n--- [ LIVE TACTICAL DASHBOARD ] ---" + Colors.ENDC)
    slow_print("Fetching live telemetry from Firestore...", 0.01)

    try:
        # ✅ Strict timeout applied
        response = requests.get(f"{BASE_URL}/dashboard", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"\n{Colors.BOLD}OVERVIEW:{Colors.ENDC}")
            print(f"Total Open Needs:      {data.get('total_needs', 0)}")
            print(f"Available Volunteers:  {data.get('total_volunteers', 0)}")
            
            print(f"\n{Colors.BOLD}PRIORITY QUEUE:{Colors.ENDC}")
            print(f"{Colors.FAIL}[!] Critical: {data.get('critical_cases', 0)}{Colors.ENDC}")
            print(f"{Colors.WARNING}[-] High:     {data.get('high_priority_cases', 0)}{Colors.ENDC}")
            print(f"{Colors.GREEN}[v] Medium:   {data.get('medium_priority_cases', 0)}{Colors.ENDC}")
            
            print(f"\n{Colors.BOLD}SYSTEM QUEUES:{Colors.ENDC}")
            print(f"Unmatched Cases:       {data.get('unmatched_cases', 0)}")
            print(f"Flagged for Review:    {data.get('flagged_cases', 0)}")
            
        else:
            print(Colors.FAIL + f"❌ Failed to fetch dashboard data: {response.text}" + Colors.ENDC)
            
    except requests.exceptions.Timeout:
        print(Colors.FAIL + "❌ Connection Error: Dashboard fetch timed out." + Colors.ENDC)
    except requests.exceptions.RequestException as e:
        print(Colors.FAIL + f"❌ Connection Error: {e}" + Colors.ENDC)

    input("\nPress Enter to return to Command Center...")

def main_menu():
    while True:
        show_banner()
        print("1. 🚨 Simulate SOS Report (Webhook Trigger)")
        print("2. 🦸 Register New Volunteer")
        print("3. 📊 View Live Tactical Dashboard")
        print("4. 🚪 Exit System\n")
        
        choice = input(Colors.BOLD + "Awaiting Command (1-4): " + Colors.ENDC)
        
        if choice == '1':
            submit_sos()
        elif choice == '2':
            register_volunteer()
        elif choice == '3':
            view_dashboard()
        elif choice == '4':
            slow_print("Shutting down Setu AI Command Center... Goodbye.")
            sys.exit(0)
        else:
            print(Colors.FAIL + "Invalid command. Try again." + Colors.ENDC)
            time.sleep(1)

if __name__ == "__main__":
    # Ensure backend is running before launching CLI
    print(Colors.WARNING + "Pinging Backend Server..." + Colors.ENDC)
    if not check_health():
        print(Colors.FAIL + f"\n🚨 CRITICAL ERROR: Could not connect to backend at {BASE_URL}" + Colors.ENDC)
        print("Please ensure your FastAPI server is running in another terminal:")
        print("Command: uvicorn backend.main:app --reload") # Updated to match your run command
        sys.exit(1)
    
    main_menu()