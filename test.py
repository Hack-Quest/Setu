import sys
import io

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and type(sys.stdout).__name__ == "TextIOWrapper":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and type(sys.stderr).__name__ == "TextIOWrapper":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import unittest
import requests
import time
import uuid
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path="config/.env")

BASE_URL = os.getenv("SETU_BASE_URL")
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BASE_URL:
    raise RuntimeError("SETU_BASE_URL is not set. Add it to config/.env.")
if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")

# Global state to pass data between sequential tests
class GlobalState:
    ngo_id = None
    volunteer_auth_token = None
    volunteer_id = None
    general_need_id = None
    sensitive_need_id = None


class TestSetuIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print(f"\n{'-'*50}")
        print(">>> Starting Setu Universal Integration Tests")
        print(f"{'-'*50}")
        # Unique identifier to avoid collisions on repeated runs
        cls.run_id = str(uuid.uuid4())[:8]

    # --- 1. HEALTH CHECK ---
    def test_01_health_check(self):
        """[NORMAL] Verify backend health endpoint"""
        resp = requests.get(f"{BASE_URL}/health")
        self.assertEqual(resp.status_code, 200, "Backend is not reachable")
        self.assertEqual(resp.json().get("status"), "ok")


    # --- 2. NGO ONBOARDING ---
    def test_02_ngo_registration(self):
        """[NORMAL] Register a new NGO"""
        payload = {
            "name": f"Global MedRescue Test-{self.run_id}",
            "reg_number": f"REG-{self.run_id}",
            "location": "New Delhi",
            "lat": 28.6139,
            "lng": 77.2090,
            "radius": 50.0
        }
        headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
        resp = requests.post(f"{BASE_URL}/ngo/register", json=payload, headers=headers)
        self.assertEqual(resp.status_code, 200, f"Failed NGO registration: {resp.text}")
        
        data = resp.json()
        self.assertIn("id", data)
        GlobalState.ngo_id = data["id"]


    # --- 3. AUTHENTICATION & VOLUNTEERS ---
    def test_03_volunteer_auth_registration(self):
        """[NORMAL] Register a volunteer via standard auth"""
        payload = {
            "name": "Test Auth Volunteer",
            "email": f"auth_{self.run_id}@test.com",
            "password": "securepassword",
            "phone": f"100{self.run_id[:7]}",
            "location": "Delhi",
            "skills": ["Medical", "Rescue"],
            "role": "volunteer"
        }
        resp = requests.post(f"{BASE_URL}/auth/register", json=payload)
        self.assertIn(resp.status_code, [200, 201], f"Auth register failed: {resp.text}")
        self.assertIn("volunteer_id", resp.json())
        
    def test_04_volunteer_auth_duplicate_email(self):
        """[EDGE] Attempt to register volunteer with duplicate email"""
        payload = {
            "name": "Duplicate Tester",
            "email": f"auth_{self.run_id}@test.com", # Same email as test 03
            "password": "securepassword",
            "phone": "0987654321",
            "location": "Delhi",
            "skills": ["Food"],
            "role": "volunteer"
        }
        resp = requests.post(f"{BASE_URL}/auth/register", json=payload)
        self.assertEqual(resp.status_code, 400, f"Duplicate test failed: {resp.text}")
        self.assertIn("Email already registered", resp.text)

    def test_05_volunteer_auth_login_fail(self):
        """[EDGE] Login with wrong password"""
        payload = {
            "email": f"auth_{self.run_id}@test.com",
            "password": "wrongpassword"
        }
        resp = requests.post(f"{BASE_URL}/auth/login", json=payload)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid email or password", resp.text)

    def test_06_volunteer_auth_login_success(self):
        """[NORMAL] Login with correct credentials"""
        payload = {
            "email": f"auth_{self.run_id}@test.com",
            "password": "securepassword"
        }
        resp = requests.post(f"{BASE_URL}/auth/login", json=payload)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertIn("token", data)
        self.assertIn("volunteer_id", data)
        GlobalState.volunteer_auth_token = data["token"]
        GlobalState.volunteer_id = data.get("volunteer_id")

    def test_07_volunteer_webhook_tier1(self):
        """[NORMAL] Register a Tier 1 (NGO-linked) volunteer via webhook"""
        self.assertIsNotNone(GlobalState.ngo_id, "NGO ID missing, dependent test failed")
        payload = {
            "volunteer_name": f"Dr. Sarah (Tier 1) {self.run_id}",
            "phone": f"9998{self.run_id[:6]}",
            "skills": "Medical, Rescue",
            "location": "New Delhi",
            "ngo_id": GlobalState.ngo_id
        }
        resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("id", resp.json())

    def test_08_volunteer_webhook_tier2(self):
        """[NORMAL] Register a Tier 2 (Community) volunteer via webhook"""
        payload = {
            "volunteer_name": f"Local Helper (Tier 2) {self.run_id}",
            "phone": f"9997{self.run_id[:6]}",
            "skills": "Medical", # Has medical, but is NOT tier 1
            "location": "Noida",
            "ngo_id": None
        }
        resp = requests.post(f"{BASE_URL}/volunteer_webhook", json=payload)
        self.assertEqual(resp.status_code, 200)


    # --- 4. SOS INTAKE & AI PROCESSING ---
    def test_09_sos_intake_validation_fail(self):
        """[EDGE] Submit an SOS with too short description"""
        payload = {
            "description": "short"
        }
        resp = requests.post(f"{BASE_URL}/webhook", json=payload)
        # Backend returns 200 with an "error" key inside the data dictionary
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.json().get("data", {}))

    def test_10_sos_intake_general_need(self):
        """[NORMAL] Submit a standard non-critical emergency"""
        payload = {
            "name": "General Reporter",
            "phone": "9876543210",
            "address": "Connaught Place, New Delhi",
            "disaster_type": "flood",
            "help_needed": "food",
            "description": f"[{self.run_id}] Need food and water supplies for 5 families stranded in heavy rain. It's not life threatening yet."
        }
        resp = requests.post(f"{BASE_URL}/webhook", json=payload)
        if resp.status_code == 429:
            print("  [WARN] Rate limited by AI API, skipping test_10")
            return
        self.assertEqual(resp.status_code, 200)
        data = resp.json().get("data", {})
        
        self.assertNotIn("error", data, f"AI Processing failed: {data.get('error')}")
        self.assertIn("id", data)
        GlobalState.general_need_id = data["id"]
        
        # Allow background processes to finish (e.g. Geocoding / AI saving)
        time.sleep(2)

    def test_11_sos_intake_sensitive_need(self):
        """[SPECIAL] Submit a critical, sensitive (medical/rescue) emergency"""
        payload = {
            "name": "Emergency Reporter",
            "phone": "9876543211",
            "address": "Connaught Place, New Delhi",
            "disaster_type": "accident",
            "help_needed": "Medical",
            "description": f"[{self.run_id}] Severe building collapse! Multiple casualties, bleeding heavily, need immediate rescue and medical help right now!"
        }
        resp = requests.post(f"{BASE_URL}/webhook", json=payload)
        if resp.status_code == 429:
            print("  [WARN] Rate limited by AI API, skipping test_11")
            return
        self.assertEqual(resp.status_code, 200)
        data = resp.json().get("data", {})
        
        self.assertNotIn("error", data, f"AI Processing failed: {data.get('error')}")
        self.assertIn("id", data)
        GlobalState.sensitive_need_id = data["id"]
        
        # High severity triggers `_auto_match_for_need` in background task
        time.sleep(3)


    # --- 5. MATCHING ENGINE ---
    def test_12_match_engine(self):
        """[NORMAL/SPECIAL] Execute Match Engine and verify logic"""
        # Provide hardcoded fallback secret to bypass Depend(verify_token) for the /match cron-like endpoint
        headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/match", headers=headers)
        self.assertEqual(resp.status_code, 200)
        
        data = resp.json()
        self.assertIn("matches", data)
        
        sensitive_match_status = None
        
        for m in data["matches"]:
            if m.get("need_id") == GlobalState.sensitive_need_id:
                sensitive_match_status = m["status"]
                # ── SENSITIVE LOGIC ASSERTION ──
                # If matched, it MUST be a Tier 1 (NGO-Verified) volunteer
                if sensitive_match_status == "assigned":
                    self.assertIn("Tier 1", m.get("volunteer_tier", ""))
                # Otherwise, it must be Manual Escalation or Pending
                else:
                    self.assertIn(sensitive_match_status, ["Manual Escalation Required", "pending"])
                    
        # Verification that the API endpoint successfully returned valid JSON
        self.assertIsInstance(data["total_matches_made"], int)


    # --- 6. DASHBOARDS ---
    def test_13_ngo_dashboard(self):
        """[NORMAL] Fetch NGO tactical dashboard"""
        if not GlobalState.ngo_id:
            self.skipTest("NGO ID not created")
            
        headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/ngo/{GlobalState.ngo_id}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ngo", resp.json())
        
    def test_14_global_dashboard(self):
        """[NORMAL] Fetch global platform dashboard aggregates"""
        headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("total_needs", data)
        self.assertIn("total_volunteers", data)

    def test_15_dashboard_reports_list(self):
        """[NORMAL] Fetch detailed report map listing"""
        headers = {"Authorization": f"Bearer {SECRET_TOKEN}"}
        resp = requests.get(f"{BASE_URL}/dashboard/reports", headers=headers)
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.json(), list)



if __name__ == '__main__':
    unittest.main(verbosity=2)