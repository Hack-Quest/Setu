import json
import sys

try:
    import requests
except ImportError:
    print("Error: The 'requests' library is not installed.")
    print("Please run: pip install requests")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"
# We include the token we found in need.py just in case it's still partially required.
HEADERS = {
    "Authorization": "Bearer hackathon-secret"
}

def print_response(response):
    try:
        print("\n--- API Response ---")
        print(f"Status Code: {response.status_code}")
        print(json.dumps(response.json(), indent=2))
        print("--------------------\n")
    except Exception as e:
        print(f"\n--- API Error ---")
        print(f"Status Code: {response.status_code}")
        print(response.text)
        print("-----------------\n")

def report_need():
    print("\n" + "="*30)
    print("        REPORT A NEED")
    print("="*30)
    reporter_name = input("Reporter Name: ")
    reporter_phone = input("Reporter Phone: ")
    location = input("Location (e.g., Delhi, Mumbai): ")
    disaster_type = input("Disaster Type (e.g., Flood, Earthquake): ")
    help_needed = input("Briefly, what help is needed? ")
    description = input("Detailed Description (used by AI): ")
    
    data = {
        "reporter_name": reporter_name,
        "reporter_phone": reporter_phone,
        "location": location,
        "disaster_type": disaster_type,
        "help_needed": help_needed,
        "description": description
    }
    
    print("\nSending request to /need ...")
    response = requests.post(f"{BASE_URL}/need", json=data, headers=HEADERS)
    print_response(response)


def register_volunteer():
    print("\n" + "="*30)
    print("      REGISTER VOLUNTEER")
    print("="*30)
    name = input("Volunteer Name: ")
    location = input("Location (e.g., Delhi, Mumbai): ")
    skills_input = input("Skills (comma-separated, e.g., medical, food, rescue): ")
    
    skills = [s.strip().lower() for s in skills_input.split(",") if s.strip()]
    
    data = {
        "name": name,
        "location": location,
        "skills": skills
    }
    
    print("\nSending request to /volunteer ...")
    response = requests.post(f"{BASE_URL}/volunteer", json=data)
    print_response(response)

def get_matches():
    print("\n" + "="*30)
    print("        MATCHING SYSTEM")
    print("="*30)
    print("Getting matches from /match ...")
    response = requests.get(f"{BASE_URL}/match")
    print_response(response)

def view_dashboard():
    print("\n" + "="*30)
    print("           DASHBOARD")
    print("="*30)
    print("Fetching dashboard metrics from /dashboard ...")
    response = requests.get(f"{BASE_URL}/dashboard")
    print_response(response)

def main():
    while True:
        print("\n" + "#"*40)
        print("          SETU SYSTEM TESTER")
        print("#"*40)
        print(" 1. Report a Need (POST /need)")
        print(" 2. Register a Volunteer (POST /volunteer)")
        print(" 3. Run Matching (GET /match)")
        print(" 4. View Dashboard (GET /dashboard)")
        print(" 5. Exit")
        print("#"*40)
        
        choice = input("\nSelect an option (1-5): ")
        
        if choice == '1':
            report_need()
        elif choice == '2':
            register_volunteer()
        elif choice == '3':
            get_matches()
        elif choice == '4':
            view_dashboard()
        elif choice == '5':
            print("Exiting test app. Goodbye!")
            break
        else:
            print("Invalid option. Please enter a number between 1 and 5.")

if __name__ == "__main__":
    main()
