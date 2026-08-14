"""
backend/test_backend.py
========================
Tests for:
  - backend/auth.py
  - backend/models.py
  - backend/main.py  (WebSocketManager, health/config routes)
  - backend/routes/need.py
  - backend/routes/volunteer.py
  - backend/routes/volunteer_auth.py
  - backend/routes/match.py
  - backend/routes/dashboard.py
  - backend/routes/assignment.py
  - backend/routes/ngo.py

All database, Gemini, geocoding, and external I/O are mocked.

Run from project root:
    pytest backend/test_backend.py -v
"""

import asyncio
import json
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock
from dotenv import load_dotenv

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(dotenv_path="config/.env")

VALID_TOKEN = os.getenv("SECRET_TOKEN")
if not VALID_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")
AUTH_HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


# -----------------------------------------------------------------------------
# SHARED FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """Full FastAPI TestClient with all external I/O mocked."""
    fake_cursor = MagicMock()
    fake_cursor.fetchone.return_value = None
    fake_cursor.fetchall.return_value = []

    with patch("database.postgres_client.get_db_cursor") as mock_db_cursor, \
         patch("ai_processing.gemini_processor.client") as mock_gemini:

        mock_db_cursor.return_value.__enter__.return_value = fake_cursor

        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "category": "food", "severity": "medium", "consistency": 7,
            "summary_en": "Food emergency", "summary_local": "Khana chahiye"
        })
        mock_gemini.models.generate_content.return_value = mock_resp

        from fastapi.testclient import TestClient
        from backend.main import app
        yield TestClient(app)


# -----------------------------------------------------------------------------
# AUTH MODULE
# -----------------------------------------------------------------------------

class TestAuth:

    def test_verify_token_correct(self):
        from backend.auth import verify_token, SECRET_TOKEN
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=SECRET_TOKEN)
        assert verify_token(creds) == SECRET_TOKEN

    def test_verify_token_wrong_raises_401(self):
        from fastapi import HTTPException
        from backend.auth import verify_token
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(creds)
        assert exc_info.value.status_code == 401
        assert "Invalid" in exc_info.value.detail


# -----------------------------------------------------------------------------
# WEBSOCKET MANAGER
# -----------------------------------------------------------------------------

class TestWebSocketManager:

    @pytest.mark.asyncio
    async def test_connect_adds_to_connections(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws = MagicMock()
        # Mock the coroutine
        ws.accept = AsyncMock()
        await manager.connect(ws)
        assert ws in manager.active_connections
        ws.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_disconnect_removes_connection(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws = MagicMock()
        manager.active_connections.append(ws)
        manager.disconnect(ws)
        assert ws not in manager.active_connections

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws1 = MagicMock(); ws1.send_json = AsyncMock()
        ws2 = MagicMock(); ws2.send_json = AsyncMock()
        manager.active_connections.extend([ws1, ws2])
        await manager.broadcast_json({"msg": "hello"})
        ws1.send_json.assert_called_with({"msg": "hello"})
        ws2.send_json.assert_called_with({"msg": "hello"})


# -----------------------------------------------------------------------------
# APP BASIC ROUTES
# -----------------------------------------------------------------------------

class TestBasicRoutes:

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "database" in resp.json()

    def test_get_config(self, client):
        resp = client.get("/config/public")
        assert resp.status_code == 200
        data = resp.json()
        assert "google_maps_api_key" in data


# -----------------------------------------------------------------------------
# NEED ROUTES
# -----------------------------------------------------------------------------

class TestNeedRoute:

    def test_webhook_requires_auth(self, client):
        resp = client.post("/need", json={"description": "Test need"})
        assert resp.status_code == 401

    def test_webhook_validation_fail_short_desc(self, client):
        with patch("backend.routes.need.process_need_text", return_value={"category": "rescue", "severity": "medium", "consistency": 5}), \
             patch("backend.routes.need.get_coordinates", return_value={"lat": 12.3, "lng": 45.6}), \
             patch("backend.routes.need.save_need", return_value="need-short"):
            resp = client.post("/need", json={"description": "Need food immediately", "location": "Delhi"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "secondary_review"
        assert "reasons" in resp.json()

    def test_webhook_success_general(self, client):
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("backend.routes.need.save_need", return_value="need-001"), \
             patch("backend.routes.need.check_corroboration", return_value=2), \
             patch("backend.routes.need.process_need_text", return_value={"category": "logistics", "severity": "medium", "consistency": 9}):
            
            resp = client.post("/need", json={
                "name": "Victim A", "phone": "9876543210",
                "address": "Kanpur, India",
                "disaster_type": "flood", "help_needed": "food",
                "description": "Stranded in Kanpur flood without food for 2 days"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "open"
        assert data["need_id"] == "need-001"
        assert "trust_score" in data

    def test_webhook_success_critical(self, client):
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("backend.routes.need.save_need", return_value="need-x"), \
             patch("backend.routes.need.check_corroboration", return_value=2), \
             patch("backend.routes.need.process_need_text", return_value={"category": "rescue", "severity": "critical", "consistency": 10}):
            
            resp = client.post("/need", json={
                "name": "Victim B", "phone": "9900000001",
                "address": "Kanpur",
                "disaster_type": "accident", "help_needed": "medical",
                "description": "Building collapse! Severe bleeding, please send medical help immediately"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "open"
        assert data["need_id"] == "need-x"

    def test_webhook_missing_coords_falls_back(self, client):
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("backend.routes.need.save_need", return_value="wh-001"), \
             patch("backend.routes.need.check_corroboration", return_value=0), \
             patch("backend.routes.need.process_need_text", return_value={"category": "logistics", "severity": "low", "consistency": 9}):
            
            resp = client.post("/need", json={
                "name": "Victim C", "phone": "9900000002",
                "address": "Delhi", "disaster_type": "rain", "help_needed": "shelter",
                "description": "Water logging inside house, need dry shelter"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["need_id"] == "wh-001"


# -----------------------------------------------------------------------------
# VOLUNTEER ROUTES
# -----------------------------------------------------------------------------

class TestVolunteerRoute:

    def test_volunteer_webhook_requires_auth(self, client):
        resp = client.post("/volunteer", json={})
        assert resp.status_code == 401

    def test_volunteer_webhook_success(self, client):
        with patch("backend.main.save_volunteer", return_value="vol-001"), \
             patch("backend.main.get_coordinates", return_value={"lat": 19.0, "lng": 72.8}):
            
            resp = client.post("/volunteer_webhook", json={
                "volunteer_name": "Ravi", "phone": "9898989898",
                "skills": "first-aid", "location": "Mumbai"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["status"] == "registered"
        assert resp.json()["volunteer_id"] == "vol-001"

    def test_volunteer_webhook_missing_location_falls_back(self, client):
        with patch("backend.main.save_volunteer", return_value="vol-wh-1"), \
             patch("backend.main.get_coordinates", return_value={"lat": 12.9, "lng": 77.6}), \
             patch("backend.main.get_ngo", return_value=None):
            
            resp = client.post("/volunteer_webhook", json={
                "volunteer_name": "Sita", "phone": "9000000010",
                "skills": "cooking", "location": "Bengaluru"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["volunteer_id"] == "vol-wh-1"


# -----------------------------------------------------------------------------
# VOLUNTEER AUTH ROUTES
# -----------------------------------------------------------------------------

class TestVolunteerAuth:

    def test_auth_register_new_volunteer(self, client):
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = None  # Email not taken
            mock_get_db.return_value.__enter__.return_value = cursor
            with patch("database.geocoding.get_coordinates", return_value={"lat": 28.6, "lng": 77.2}):
                resp = client.post("/auth/register", json={
                    "email": "newvol@test.com", "password": "SecurePass123",
                    "name": "Deepak Kumar", "phone": "9000000001",
                    "location": "New Delhi", "skills": ["medical", "rescue"]
                })
        assert resp.status_code == 200
        assert "volunteer_id" in resp.json()
        assert "token" in resp.json()

    def test_auth_register_duplicate_email_returns_400(self, client):
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = {"id": "vol-1"}  # Email duplicate
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/register", json={
                "email": "dup@test.com", "password": "pass",
                "name": "Dup", "phone": "9111111111",
                "location": "Mumbai", "skills": ["food"]
            })
        assert resp.status_code == 400

    def test_auth_login_success(self, client):
        from database.volunteers_db import hash_password
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = {
                "id": "v-login", "email": "login@test.com",
                "password_hash": hash_password("TestPass"), "name": "Login User"
            }
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/login", json={"email": "login@test.com", "password": "TestPass"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Login User"

    def test_auth_login_wrong_password_returns_401(self, client):
        from database.volunteers_db import hash_password
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = {
                "id": "v-bad", "email": "bad@test.com",
                "password_hash": hash_password("correct"), "name": "Bad"
            }
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/login", json={"email": "bad@test.com", "password": "wrong"})
        assert resp.status_code == 401


# -----------------------------------------------------------------------------
# MATCH ROUTES & LOGIC
# -----------------------------------------------------------------------------

class TestMatchRoutes:

    def test_run_matcher_unauthorized(self, client):
        resp = client.get("/match")
        assert resp.status_code == 401

    def test_run_matcher_no_needs(self, client):
        with patch("backend.routes.match.get_open_needs", return_value=[]), \
             patch("backend.routes.match.get_available_volunteers", return_value=[]):
            
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 0

    def test_run_matcher_with_successful_tiered_match(self, client):
        open_needs = [
            {"id": "n1", "category": "rescue", "lat": 28.6, "lng": 77.2, "status": "open", "trust_score": 80}
        ]
        # Tier 1 volunteer has same coordinates
        volunteers = [
            {"id": "vol-t1", "ngo_id": "ngo-1", "skills": ["rescue"], "lat": 28.6, "lng": 77.2, "available": True, "ngo_verified": True}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers), \
             patch("backend.routes.match.save_assignment", return_value="a-t1"):
            
            resp = client.get("/match", headers=AUTH_HEADERS)
    
        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 1
        assert len(resp.json()["matches"]) == 1
        assert resp.json()["matches"][0]["status"] == "assigned"


# -----------------------------------------------------------------------------
# DASHBOARD ROUTES
# -----------------------------------------------------------------------------

class TestDashboardRoutes:

    def test_get_global_dashboard_stats(self, client):
        needs = [
            {"id": "1", "status": "open", "category": "food", "severity": "medium"},
            {"id": "2", "status": "resolved", "category": "medical", "severity": "critical"}
        ]
        with patch("backend.routes.dashboard.get_open_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_available_volunteers", return_value=[]):
            
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        assert "reports" in resp.json()
        assert resp.json()["total_needs"] == 2

    def test_get_dashboard_reports_list(self, client):
        with patch("database.needs_db.get_all_needs", return_value=[{"id": "n1", "status": "open"}]):
            resp = client.get("/dashboard/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# -----------------------------------------------------------------------------
# ASSIGNMENT ROUTE
# -----------------------------------------------------------------------------

class TestAssignmentRoute:

    def test_resolve_requires_auth(self, client):
        resp = client.patch("/assignment/a1/resolve")
        assert resp.status_code == 401

    def test_resolve_success(self, client):
        assignment = {"id": "a1", "need_id": "n1", "volunteer_id": "v1", "resolved_at": None}
        with patch("database.assignments_db.get_assignment_by_id", return_value=assignment), \
             patch("database.assignments_db.resolve_assignment"):
            resp = client.patch("/assignment/a1/resolve",
                headers=AUTH_HEADERS
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_resolve_not_found_returns_404(self, client):
        with patch("database.assignments_db.get_assignment_by_id", return_value=None):
            resp = client.patch("/assignment/ghost-assign/resolve",
                headers=AUTH_HEADERS
            )
        assert resp.status_code == 404

    def test_resolve_already_resolved_returns_409(self, client):
        assignment = {
            "id": "a2", "need_id": "n2", "volunteer_id": "v2",
            "resolved_at": "2025-01-01T10:00:00+00:00"
        }
        with patch("database.assignments_db.get_assignment_by_id", return_value=assignment):
            resp = client.patch("/assignment/a2/resolve",
                headers=AUTH_HEADERS
            )
        assert resp.status_code == 409

    def test_get_volunteer_assignments_success(self, client):
        expected = [
            {"id": "a1", "need_id": "n1", "volunteer_id": "v1", "resolved_at": None},
            {"id": "a2", "need_id": "n2", "volunteer_id": "v1", "resolved_at": None},
        ]
        with patch("database.assignments_db.get_assignments_by_volunteer_id", return_value=expected):
            resp = client.get("/assignment/volunteer/v1", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json() == expected

    def test_get_volunteer_assignments_requires_auth(self, client):
        resp = client.get("/assignment/volunteer/v1")
        assert resp.status_code == 401


# -----------------------------------------------------------------------------
# NGO ROUTE
# -----------------------------------------------------------------------------

class TestNGORoute:

    def test_register_ngo_success(self, client):
        with patch("database.ngos_db.save_ngo", return_value="ngo-001"), \
             patch("database.geocoding.get_coordinates", return_value={"lat": 22.5, "lng": 88.3}):
            resp = client.post("/ngo/register",
                json={"name": "HelpIndia NGO", "reg_number": "NGO/KP/001",
                      "location": "Kolkata", "radius": 100.0}
            )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_get_ngo_not_found(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value=None):
            resp = client.get("/ngo/fake-id")
        assert resp.status_code == 404

    def test_get_ngo_found(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value={
            "id": "ngo-1", "ngo_name": "SaveIndia", "verified": False
        }):
            resp = client.get("/ngo/ngo-1")
        assert resp.status_code == 200
        assert resp.json()["ngo_name"] == "SaveIndia"

    def test_ngo_dashboard_not_found(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value=None):
            resp = client.get("/ngo/bad-id/dashboard")
        assert resp.status_code == 404

    def test_ngo_dashboard_returns_stats(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value={"id": "ngo-1", "ngo_name": "TestNGO"}), \
             patch("backend.routes.ngo.get_db_cursor") as mock_get_cursor:
            cursor = MagicMock()
            cursor.fetchall.side_effect = [
                [{"id": f"v{i}", "skills": ["medical"]} for i in range(5)], # volunteers
                [] # assignments
            ]
            mock_get_cursor.return_value.__enter__.return_value = cursor
            resp = client.get("/ngo/ngo-1/dashboard")
        assert resp.status_code == 200
        assert "stats" in resp.json()
        assert resp.json()["stats"]["managed_volunteers"] == 5
        assert resp.json()["stats"]["active_assignments"] == 0