import sys
import os
import unittest
import requests
import time
import uuid
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.ngos_db import verify_ngo, save_ngo
from database.postgres_client import get_db_cursor
from database.volunteers_db import save_volunteer

load_dotenv(dotenv_path="config/.env")

BASE_URL = os.getenv("SETU_BASE_URL") or "http://127.0.0.1:8080"
SECRET_TOKEN = os.getenv("SECRET_TOKEN")

if not BASE_URL:
    raise RuntimeError("SETU_BASE_URL is not set.")
if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set.")

class TestAuthSecurity(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.run_id = str(uuid.uuid4())[:8]
        cls.ngo_a_email = f"ngo_a_{cls.run_id}@test.com"
        cls.ngo_b_email = f"ngo_b_{cls.run_id}@test.com"
        cls.vol_a_email = f"vol_a_{cls.run_id}@test.com"
        cls.vol_b_email = f"vol_b_{cls.run_id}@test.com"
        
        # 1. Create two test NGOs
        cls.ngo_a_id = save_ngo({
            "ngo_name": f"NGO A {cls.run_id}",
            "owner_name": "Owner A",
            "reg_number": f"REG-A-{cls.run_id}",
            "location": "Delhi",
            "email": cls.ngo_a_email,
            "lat": 28.6139,
            "lng": 77.2090,
            "radius": 50.0,
            "verified": True
        })
        verify_ngo(cls.ngo_a_id, True)

        cls.ngo_b_id = save_ngo({
            "ngo_name": f"NGO B {cls.run_id}",
            "owner_name": "Owner B",
            "reg_number": f"REG-B-{cls.run_id}",
            "location": "Mumbai",
            "email": cls.ngo_b_email,
            "lat": 19.0760,
            "lng": 72.8777,
            "radius": 50.0,
            "verified": True
        })
        verify_ngo(cls.ngo_b_id, True)

        # 2. Register two test volunteers via standard registration
        # Vol A
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": f"Volunteer A {cls.run_id}",
            "email": cls.vol_a_email,
            "password": "securepassword",
            "phone": "9999900001",
            "location": "Delhi",
            "skills": ["medical"]
        })
        assert resp.status_code in [200, 201]
        cls.vol_a_id = resp.json()["volunteer_id"]

        # Vol B
        resp = requests.post(f"{BASE_URL}/auth/register", json={
            "name": f"Volunteer B {cls.run_id}",
            "email": cls.vol_b_email,
            "password": "securepassword",
            "phone": "9999900002",
            "location": "Mumbai",
            "skills": ["rescue"]
        })
        assert resp.status_code in [200, 201]
        cls.vol_b_id = resp.json()["volunteer_id"]

        # 3. Log in both volunteers & NGOs to acquire their custom JWT tokens
        # Vol A JWT
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": cls.vol_a_email,
            "password": "securepassword"
        })
        cls.vol_a_token = resp.json()["token"]

        # Vol B JWT
        resp = requests.post(f"{BASE_URL}/auth/login", json={
            "email": cls.vol_b_email,
            "password": "securepassword"
        })
        cls.vol_b_token = resp.json()["token"]

        # Get NGO A JWT via OTP verification helper
        # Save a mock OTP for NGO A directly in DB to bypass SMTP email delivery in test
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO otps (email, otp, expires_at, created_at) VALUES (%s, %s, NOW() + INTERVAL '10 minutes', NOW()) ON CONFLICT (email) DO UPDATE SET otp=EXCLUDED.otp",
                (cls.ngo_a_email, "123456")
            )
        resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
            "email": cls.ngo_a_email,
            "otp": "123456"
        })
        cls.ngo_a_token = resp.json()["token"]

        # Get NGO B JWT
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO otps (email, otp, expires_at, created_at) VALUES (%s, %s, NOW() + INTERVAL '10 minutes', NOW()) ON CONFLICT (email) DO UPDATE SET otp=EXCLUDED.otp",
                (cls.ngo_b_email, "654321")
            )
        resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
            "email": cls.ngo_b_email,
            "otp": "654321"
        })
        cls.ngo_b_token = resp.json()["token"]

    # --- TEST CASES ---

    def test_unauthenticated_request(self):
        """Verify that requests without an Authorization header are blocked (401)"""
        endpoints = [
            (requests.get, f"{BASE_URL}/dashboard"),
            (requests.get, f"{BASE_URL}/dashboard/reports"),
            (requests.get, f"{BASE_URL}/volunteers"),
            (requests.post, f"{BASE_URL}/need"),
            (requests.get, f"{BASE_URL}/match"),
            (requests.post, f"{BASE_URL}/assignment/volunteer/dummy"),
        ]
        for method, url in endpoints:
            resp = method(url)
            self.assertEqual(resp.status_code, 401, f"Expected 401 for unauthenticated request to {url}, got {resp.status_code}")

    def test_authenticated_volunteer_success(self):
        """Verify that an authenticated volunteer can access dashboard details"""
        headers = {"Authorization": f"Bearer {self.vol_a_token}"}
        
        # Can access dashboard aggregates
        resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)

        # Can access detailed report list
        resp = requests.get(f"{BASE_URL}/dashboard/reports", headers=headers)
        self.assertEqual(resp.status_code, 200)

    def test_authenticated_ngo_success(self):
        """Verify that an NGO can access dashboard and NGO list"""
        headers = {"Authorization": f"Bearer {self.ngo_a_token}"}
        
        resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)

        resp = requests.get(f"{BASE_URL}/ngo/{self.ngo_a_id}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 200)

    def test_wrong_role_matching_rejection(self):
        """Verify that a volunteer cannot trigger matching engine (needs NGO/system role)"""
        headers = {"Authorization": f"Bearer {self.vol_a_token}"}
        resp = requests.get(f"{BASE_URL}/match", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.text)

    def test_wrong_role_match_debug_rejection(self):
        """Verify that a volunteer cannot query match debug breakdowns"""
        headers = {"Authorization": f"Bearer {self.vol_a_token}"}
        resp = requests.get(f"{BASE_URL}/match/debug/dummy", headers=headers)
        self.assertEqual(resp.status_code, 403)

    def test_volunteer_access_another_volunteer_assignments_rejection(self):
        """Verify that Volunteer A cannot view assignments of Volunteer B (IDOR prevention)"""
        headers = {"Authorization": f"Bearer {self.vol_a_token}"}
        resp = requests.get(f"{BASE_URL}/assignment/volunteer/{self.vol_b_id}", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json().get("detail", ""))

    def test_ngo_access_another_ngo_dashboard_rejection(self):
        """Verify that NGO A cannot view NGO B's tactical dashboard (IDOR prevention)"""
        headers = {"Authorization": f"Bearer {self.ngo_a_token}"}
        resp = requests.get(f"{BASE_URL}/ngo/{self.ngo_b_id}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Access denied", resp.json().get("detail", ""))

    def test_expired_or_invalid_token_rejection(self):
        """Verify that invalid tokens are rejected with 401"""
        headers = {"Authorization": "Bearer badtoken123"}
        resp = requests.get(f"{BASE_URL}/dashboard", headers=headers)
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid token", resp.json().get("detail", ""))

    def test_otp_expired_check(self):
        """Verify that expired OTP codes return 401"""
        email = f"expired_otp_{self.run_id}@test.com"
        # Insert directly into DB with an expired date
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO otps (email, otp, expires_at, created_at) VALUES (%s, %s, NOW() - INTERVAL '1 minute', NOW() - INTERVAL '11 minutes')",
                (email, "999999")
            )
        resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
            "email": email,
            "otp": "999999"
        })
        self.assertEqual(resp.status_code, 401)
        self.assertIn("Invalid or expired OTP", resp.json().get("detail", ""))

    def test_otp_wrong_too_many_times(self):
        """Verify that wrong OTP attempts are capped at 5 and lock verification / delete active OTP"""
        email = f"brute_force_{self.run_id}@test.com"
        
        # Save active OTP
        with get_db_cursor(commit=True) as cur:
            cur.execute(
                "INSERT INTO otps (email, otp, expires_at, created_at) VALUES (%s, %s, NOW() + INTERVAL '10 minutes', NOW())",
                (email, "888888")
            )
            
        # Call verify-otp 4 times with wrong code (should return attempts remaining)
        for i in range(1, 5):
            resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
                "email": email,
                "otp": "000000"
            })
            self.assertEqual(resp.status_code, 401)
            self.assertIn(f"{5 - i} attempts remaining", resp.json().get("detail", ""))
            
        # 5th attempt (should trigger account lock and invalidate OTP)
        resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
            "email": email,
            "otp": "000000"
        })
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Too many failed attempts. OTP has been invalidated.", resp.json().get("detail", ""))

        # Verify that the OTP record was indeed deleted from the database
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT 1 FROM otps WHERE email = %s", (email,))
            row = cur.fetchone()
        self.assertIsNone(row, "Expired/locked OTP was not deleted from the database")

        # Verify that subsequent attempts are immediately blocked
        resp = requests.post(f"{BASE_URL}/auth/verify-otp", json={
            "email": email,
            "otp": "888888" # Real OTP, but it's locked/deleted
        })
        self.assertEqual(resp.status_code, 429)

    def test_otp_resend_abuse_rate_limit(self):
        """Verify that users cannot spam request OTP emails (60 seconds resend cooldown)"""
        email = f"resend_limit_{self.run_id}@test.com"
        
        # 1st request (success)
        resp = requests.post(f"{BASE_URL}/auth/send-otp", json={"email": email})
        self.assertEqual(resp.status_code, 200)

        # 2nd request (immediate cooldown rejection)
        resp = requests.post(f"{BASE_URL}/auth/send-otp", json={"email": email})
        self.assertEqual(resp.status_code, 429)
        self.assertIn("Please wait", resp.json().get("detail", ""))

    def test_volunteer_unauthorized_tier1_promotion_rejection(self):
        """Verify that registering a volunteer via public webhook cannot self-promote them to Tier 1"""
        # We try to supply NGO A's ID in the public unauthenticated webhook
        phone = f"0000{self.run_id[:6]}"
        resp = requests.post(f"{BASE_URL}/volunteer_webhook", json={
            "volunteer_name": f"Hacker Medic {self.run_id}",
            "email": f"hacker_{self.run_id}@test.com",
            "phone": phone,
            "skills": "Medical",
            "location": "Delhi",
            "ngo_id": self.ngo_a_id
        })
        self.assertEqual(resp.status_code, 200)
        vol_id = resp.json()["volunteer_id"]
        
        # Verify that ngo_verified is set to FALSE in database (no automatic promotion allowed via public endpoint)
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT ngo_verified FROM volunteers WHERE id = %s", (vol_id,))
            ngo_verified = cur.fetchone()["ngo_verified"]
        self.assertFalse(ngo_verified, "Volunteer was automatically verified as Tier 1 via public unauthenticated webhook")

if __name__ == '__main__':
    unittest.main(verbosity=2)
