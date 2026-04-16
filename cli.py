import requests
import time
import sys
import json
import os

# Configuration
BASE_URL = "http://127.0.0.1:8000"

# ANSI Colors for a beautiful terminal
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def slow_print(text, delay=0.03):
    """Prints text character by character for a cinematic effect."""
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def show_banner():
    clear_screen()
    print(Colors.CYAN + Colors.BOLD + "=" * 60)
    print(" 🌍 SETU AI - AUTONOMOUS DISPATCH COMMAND CENTER")
    print("=" * 60 + Colors.ENDC)
    print(" Status: " + Colors.GREEN + "ONLINE & CONNECTED" + Colors.ENDC)
    print(" Target: " + Colors.WARNING + BASE_URL + Colors.ENDC + "\n")

def check_health():
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        return True
    except requests.exceptions.ConnectionError:
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

    print(Colors.WARNING + "\n[SYSTEM] Transmitting to Setu AI Brain..." + Colors.ENDC)
    time.sleep(1)
    
    try:
        response = requests.post(f"{BASE_URL}/webhook", json=payload, timeout=10)
        data = response.json()
        
        if response.status_code == 200:
            slow_print(Colors.GREEN + "✅ Webhook Accepted! Processing AI Trust Score..." + Colors.ENDC)
            # Fetching the parsed data from the backend response
            parsed = data.get("data", {})
            print(f"\n{Colors.BOLD}--- AI ANALYSIS REPORT ---{Colors.ENDC}")
            print(f"Severity:     {Colors.FAIL}{parsed.get('severity', 'N/A').upper()}{Colors.ENDC}")
            print(f"Category:     {Colors.CYAN}{parsed.get('category', 'N/A').upper()}{Colors.ENDC}")
            print(f"Trust Score:  {Colors.WARNING}{parsed.get('trust_score', 'N/A')}/100{Colors.ENDC}")
            print(f"Action:       {Colors.BOLD}{parsed.get('dispatch_action', 'N/A').replace('_', ' ').upper()}{Colors.ENDC}")
        else:
            print(Colors.FAIL + f"❌ Error: {data}" + Colors.ENDC)
    except Exception as e:
        print(Colors.FAIL + f"❌ Connection Error: {e}" + Colors.ENDC)
    
    input("\nPress Enter to return to Command Center...")

def register_volunteer():
    print(Colors.BLUE + "\n--- [ VOLUNTEER REGISTRATION ] ---" + Colors.ENDC)
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

    print(Colors.WARNING + "\n[SYSTEM] Geocoding location and saving profile..." + Colors.ENDC)
    time.sleep(1)

    try:
        response = requests.post(f"{BASE_URL}/volunteer_webhook", json=payload)
        if response.status_code == 200:
            slow_print(Colors.GREEN + f"✅ Volunteer Registered! ID: {response.json().get('id')}" + Colors.ENDC)
        else:
            print(Colors.FAIL + f"❌ Error: {response.json()}" + Colors.ENDC)
    except Exception as e:
        print(Colors.FAIL + f"❌ Connection Error: {e}" + Colors.ENDC)

    input("\nPress Enter to return to Command Center...")

def view_dashboard():
    print(Colors.CYAN + "\n--- [ LIVE TACTICAL DASHBOARD ] ---" + Colors.ENDC)
    print("Fetching live telemetry from Firestore...")
    time.sleep(0.5)

    try:
        response = requests.get(f"{BASE_URL}/dashboard")
        if response.status_code == 200:
            data = response.json()
            print(f"\n{Colors.BOLD}OVERVIEW:{Colors.ENDC}")
            print(f"Total Open Needs:      {data.get('total_needs')}")
            print(f"Available Volunteers:  {data.get('total_volunteers')}")
            
            print(f"\n{Colors.BOLD}PRIORITY QUEUE:{Colors.ENDC}")
            print(f"{Colors.FAIL}[!] Critical: {data.get('critical_cases')}{Colors.ENDC}")
            print(f"{Colors.WARNING}[-] High:     {data.get('high_priority_cases')}{Colors.ENDC}")
            print(f"{Colors.GREEN}[v] Medium:   {data.get('medium_priority_cases')}{Colors.ENDC}")
            
            print(f"\n{Colors.BOLD}SYSTEM QUEUES:{Colors.ENDC}")
            print(f"Unmatched Cases:       {data.get('unmatched_cases')}")
            print(f"Flagged for Review:    {data.get('flagged_cases')}")
            
        else:
            print(Colors.FAIL + "❌ Failed to fetch dashboard data." + Colors.ENDC)
    except Exception as e:
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
    if not check_health():
        print(Colors.FAIL + f"🚨 CRITICAL ERROR: Could not connect to backend at {BASE_URL}" + Colors.ENDC)
        print("Please ensure your FastAPI server is running: 'uvicorn main:app --reload'")
        sys.exit(1)
    
    main_menu()