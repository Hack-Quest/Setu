import requests
import time
import sys
import os
import json

# Configuration from your existing environment
BASE_URL = "http://127.0.0.1:8000"
HEADERS = {"Authorization": "Bearer hackathon-secret"}

class Colors:
    GREEN = '\033[92m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def run_step(name):
    print(f"\n{Colors.BOLD}🚀 [STEP] {name}...{Colors.ENDC}")

def verify_response(resp, stage_name):
    if resp.status_code == 200:
        print(f"{Colors.GREEN}✅ {stage_name} Successful{Colors.ENDC}")
        return resp.json()
    else:
        print(f"{Colors.FAIL}❌ {stage_name} Failed: {resp.status_code}{Colors.ENDC}")
        print(resp.text)
        sys.exit(1)

def main():
    print(f"{Colors.BOLD}=== SETU UNIVERSAL SYSTEM INTEGRATION TEST ==={Colors.ENDC}")
    
    # --- 1. HEALTH CHECK ---
    run_step("System Health Check")
    health = requests.get(f"{BASE_URL}/health")
    verify_response(health, "Health Check")

    # --- 2. NGO ONBOARDING ---
    run_step("Registering & Verifying Tier 1 NGO")
    ngo_payload = {
        "name": "Global MedRescue",
        "reg_number": f"REG-{int(time.time())}",
        "lat": 28.6139,
        "lng": 77.2090,
        "radius": 50.0
    }
    ngo_data = requests.post(f"{BASE_URL}/ngo/register", json=ngo_payload)
    ngo_res = verify_response(ngo_data, "NGO Registration")
    ngo_id = ngo_res["id"]
    
    # We use verify_ngo from your ngos_db internally or via an admin route
    # For this test, we assume the backend handles initial NGO state.
    print(f"NGO ID: {ngo_id} (Awaiting Manual Admin Verification for Tier 1 Priority)")

    # --- 3. TIERED VOLUNTEER REGISTRATION ---
    run_step("Registering Tiered Volunteers")
    # Tier 1: NGO-Linked
    t1_payload = {
        "volunteer_name": "Dr. Sarah (Tier 1)",
        "phone": "9998887771",
        "skills": "Medical",
        "location": "New Delhi",
        "ngo_id": ngo_id
    }
    t1_resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=t1_payload)
    verify_response(t1_resp, "Tier 1 Registration")

    # Tier 2: Community-Led
    t2_payload = {
        "volunteer_name": "Local Helper (Tier 2)",
        "phone": "9998887772",
        "skills": "Medical",
        "location": "Noida"
    }
    t2_resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=t2_payload)
    verify_response(t2_resp, "Tier 2 Registration")

    # --- 4. SOS INTAKE & AI PROCESSING ---
    run_step("Transmitting Medical SOS Signal")
    sos_payload = {
        "name": "Emergency Reporter",
        "phone": "9876543210",
        "address": "Connaught Place, New Delhi",
        "disaster_type": "accident",
        "help_needed": "Medical",
        "description": "Severe road accident, multiple casualties near CP. High urgency medical help required."
    }
    sos_data = requests.post(f"{BASE_URL}/webhook", json=sos_payload)
    sos_res = verify_response(sos_data, "SOS Intake")
    data_part = sos_res.get("data", {})
    need_id = data_part.get("id") or data_part.get("need_id")

    if not need_id:
        print(f"❌ Failed to find ID. Full Response: {sos_res}")
        sys.exit(1)
    
    print(f"Report Verified. Trust Score: {sos_res['data'].get('trust_score')}/100")
    print("Waiting 3 seconds for AI Classification and Firestore sync...")
    time.sleep(3)

    # --- 5. MATCH ENGINE EXECUTION ---
    run_step("Triggering Autonomous Dispatch Engine")
    match_data = requests.get(f"{BASE_URL}/match", headers=HEADERS)
    match_res = verify_response(match_data, "Match Engine")
    
    print(f"Matches Made: {match_res['total_matches_made']}")
    for m in match_res["matches"]:
        if m["need_id"] == need_id:
            print(f"Match Result: {m['status']} -> {m.get('assigned_volunteer')} [{m.get('volunteer_tier')}]")

    # --- 6. DASHBOARD TELEMETRY ---
    run_step("Verifying Tactical Dashboard Data")
    dash_data = requests.get(f"{BASE_URL}/dashboard")
    dash_res = verify_response(dash_data, "Dashboard Fetch")
    print(f"Active Needs: {dash_res['total_needs']} | Available Volunteers: {dash_res['total_volunteers']}")

    # --- 7. NOTIFICATION LOGGING ---
    run_step("Verifying Email Alert Pipeline")
    # This checks if the gmail_alert.py logic was triggered during SOS intake
    if sos_res["data"].get("dispatch_action") == "auto_dispatch":
        print(f"{Colors.GREEN}✅ Alert System Triggered (Check {os.getenv('GMAIL_RECEIVER')}){Colors.ENDC}")
    else:
        print("ℹ️ Alert not triggered (Low severity or Trust Score)")

    print(f"\n{Colors.BOLD}{Colors.GREEN}🎉 ALL SYSTEMS NOMINAL: SETU INTEGRATION PASSED{Colors.ENDC}")

if __name__ == "__main__":
    main()