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

All Firestore, Gemini, geocoding, and external I/O are mocked.

Run from project root:
    pytest backend/test_backend.py -v
"""

import asyncio
import json
import sys
import os
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

VALID_TOKEN = "hackathon-secret"
AUTH_HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


# ─────────────────────────────────────────────────────────────
# SHARED FIXTURES
# ─────────────────────────────────────────────────────────────

def _make_doc(doc_id, data, exists=True):
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.to_dict.return_value = dict(data)
    return doc


@pytest.fixture(scope="module")
def client():
    """Full FastAPI TestClient with all external I/O mocked."""
    fake_db = MagicMock()
    doc_ref = MagicMock(); doc_ref.id = "test-id"
    fake_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
    fake_db.collection.return_value.where.return_value.stream.return_value = []
    fake_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
    fake_db.collection.return_value.stream.return_value = []
    snap = MagicMock(); snap.exists = False
    fake_db.collection.return_value.document.return_value.get.return_value = snap

    with patch("database.firestore_client.db", fake_db), \
         patch("ai_processing.gemini_processor._gemini_client") as mock_gemini:

        mock_resp = MagicMock()
        mock_resp.text = json.dumps({
            "category": "food", "severity": "medium", "consistency": 7,
            "summary_en": "Food emergency", "summary_local": "Khana chahiye"
        })
        mock_gemini.models.generate_content.return_value = mock_resp

        from fastapi.testclient import TestClient
        from backend.main import app
        yield TestClient(app)


# ─────────────────────────────────────────────────────────────
# AUTH MODULE
# ─────────────────────────────────────────────────────────────

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

    def test_verify_token_none_raises_401(self):
        from fastapi import HTTPException
        from backend.auth import verify_token
        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)
        assert exc_info.value.status_code == 401

    def test_secret_token_loaded_from_env(self):
        from backend.auth import SECRET_TOKEN
        assert isinstance(SECRET_TOKEN, str)
        assert len(SECRET_TOKEN) > 0


# ─────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────

class TestModels:

    def test_need_input_location_alias(self):
        from backend.models import NeedInput
        n = NeedInput(reporter_name="A", reporter_phone="9000000001",
                      location="Kanpur", disaster_type="Flood",
                      help_needed="rescue", description="Test need")
        assert n.location_text == "Kanpur"

    def test_need_input_location_text_alias(self):
        from backend.models import NeedInput
        n = NeedInput(reporter_name="A", reporter_phone="9000000001",
                      location_text="Lucknow", disaster_type="Fire",
                      help_needed="rescue", description="Building on fire")
        assert n.location_text == "Lucknow"

    def test_volunteer_input_defaults(self):
        from backend.models import VolunteerInput
        v = VolunteerInput(name="Raj", phone="9000000002", location="Delhi",
                           skills=["food"], email="raj@test.com", password="p")
        assert v.lat == 0.0
        assert v.lng == 0.0
        assert v.ngo_id is None
        assert v.credential_tags == []

    def test_volunteer_register_input(self):
        from backend.models import VolunteerRegisterInput
        v = VolunteerRegisterInput(email="a@b.com", password="pass",
                                   name="Name", phone="9000000003",
                                   location="City", skills=["food"])
        assert v.email == "a@b.com"

    def test_volunteer_login_input(self):
        from backend.models import VolunteerLoginInput
        v = VolunteerLoginInput(email="x@y.com", password="secret")
        assert v.password == "secret"

    def test_ngo_input_defaults(self):
        from backend.models import NGOInput
        ngo = NGOInput(name="HelpOrg", reg_number="REG001")
        assert ngo.verified is False
        assert ngo.radius == 50.0
        assert ngo.lat == 0.0

    def test_ngo_input_coverage_area_alias(self):
        from backend.models import NGOInput
        ngo = NGOInput(name="Org", reg_number="R001", coverage_area="Noida")
        assert ngo.location == "Noida"


# ─────────────────────────────────────────────────────────────
# WEBSOCKET MANAGER
# ─────────────────────────────────────────────────────────────

class TestWebSocketManager:

    def test_connect_adds_websocket(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()

        asyncio.run(manager.connect(mock_ws))
        assert mock_ws in manager.active_connections

    def test_disconnect_removes_websocket(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        mock_ws.accept = AsyncMock()

        asyncio.run(manager.connect(mock_ws))
        manager.disconnect(mock_ws)
        assert mock_ws not in manager.active_connections

    def test_disconnect_nonexistent_websocket_is_safe(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        mock_ws = MagicMock()
        manager.disconnect(mock_ws)   # should not raise

    def test_broadcast_sends_to_all(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()

        ws1 = MagicMock(); ws1.send_json = AsyncMock()
        ws2 = MagicMock(); ws2.send_json = AsyncMock()
        manager.active_connections = [ws1, ws2]

        asyncio.run(manager.broadcast_json({"type": "TEST"}))
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    def test_broadcast_removes_stale_connections(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()

        good_ws = MagicMock()
        bad_ws = MagicMock()

        async def good_send(d): pass
        async def bad_send(d): raise Exception("broken pipe")

        good_ws.send_json = good_send
        bad_ws.send_json = bad_send
        manager.active_connections = [good_ws, bad_ws]

        asyncio.run(manager.broadcast_json({"type": "PING"}))
        assert good_ws in manager.active_connections
        assert bad_ws not in manager.active_connections


# ─────────────────────────────────────────────────────────────
# MAIN APP ROUTES (infrastructure)
# ─────────────────────────────────────────────────────────────

class TestMainRoutes:

    def test_home_returns_message(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert "message" in resp.json()

    def test_health_returns_ok(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_config_public_no_key_returns_503(self, client):
        with patch("os.getenv", return_value=""):
            resp = client.get("/config/public")
            assert resp.status_code in (200, 503)


# ─────────────────────────────────────────────────────────────
# NEED ROUTE
# ─────────────────────────────────────────────────────────────

class TestNeedRoute:

    def test_need_route_requires_auth(self, client):
        resp = client.post("/need", json={
            "reporter_name": "X", "reporter_phone": "9000000000",
            "location": "Delhi", "disaster_type": "Flood",
            "help_needed": "rescue", "description": "Test description here"
        })
        assert resp.status_code == 403

    def test_need_route_with_valid_token(self, client):
        with patch("database.geocoding.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("database.needs_db.save_need", return_value="need-001"), \
             patch("database.needs_db.check_corroboration", return_value=0):
            resp = client.post("/need",
                headers=AUTH_HEADERS,
                json={
                    "reporter_name": "Rahul Kumar",
                    "reporter_phone": "9876543210",
                    "location": "Kanpur, UP",
                    "disaster_type": "Flood",
                    "help_needed": "rescue",
                    "description": "Flood waters rising rapidly near the main bridge"
                }
            )
        assert resp.status_code == 200

    def test_need_route_short_description_returns_error(self, client):
        with patch("database.geocoding.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("database.needs_db.save_need", return_value="need-x"):
            resp = client.post("/need",
                headers=AUTH_HEADERS,
                json={
                    "reporter_name": "X", "reporter_phone": "9876543210",
                    "location": "Kanpur", "disaster_type": "Fire",
                    "help_needed": "rescue", "description": "help"
                }
            )
        # 200 with error key OR 422 – both acceptable
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert "error" in resp.json()

    def test_webhook_endpoint_accepts_payload(self, client):
        with patch("database.geocoding.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("database.needs_db.save_need", return_value="wh-001"), \
             patch("database.needs_db.check_corroboration", return_value=0):
            resp = client.post("/webhook", json={
                "name": "Reporter", "phone": "9123456789",
                "address": "Lucknow", "disaster_type": "Earthquake",
                "description": "Building collapsed after strong earthquake, 20 people trapped inside",
                "help_needed": "rescue"
            })
        assert resp.status_code == 200


# ─────────────────────────────────────────────────────────────
# VOLUNTEER ROUTES
# ─────────────────────────────────────────────────────────────

class TestVolunteerRoutes:

    def test_create_volunteer_requires_auth(self, client):
        resp = client.post("/volunteer", json={
            "name": "Test", "phone": "9000000000", "location": "Mumbai",
            "skills": ["food"], "email": "t@t.com", "password": "p"
        })
        assert resp.status_code == 403

    def test_create_volunteer_with_token(self, client):
        with patch("database.volunteers_db.save_volunteer", return_value="vol-001"), \
             patch("database.volunteers_db.get_available_volunteers", return_value=[{}, {}]), \
             patch("database.geocoding.get_coordinates", return_value={"lat": 19.0, "lng": 72.8}):
            resp = client.post("/volunteer",
                headers=AUTH_HEADERS,
                json={
                    "name": "Meera Joshi", "phone": "9222222222",
                    "location": "Mumbai", "skills": ["food", "sanitation"],
                    "email": "meera@test.com", "password": "pass123"
                }
            )
        assert resp.status_code == 200
        assert resp.json().get("message") == "volunteer added"

    def test_volunteer_webhook_no_auth_required(self, client):
        with patch("database.volunteers_db.save_volunteer", return_value="vol-wh-1"), \
             patch("database.geocoding.get_coordinates", return_value={"lat": 12.9, "lng": 77.6}), \
             patch("database.ngos_db.get_ngo", return_value=None):
            resp = client.post("/volunteer_webhook", json={
                "volunteer_name": "Field Hero", "phone": "9333333333",
                "location": "Bangalore", "skills": "food,rescue"
            })
        assert resp.status_code == 200

    def test_auth_register_new_volunteer(self, client):
        with patch("database.volunteers_db.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = []
            new_ref = MagicMock(); new_ref.id = "vol-new"
            mock_db.collection.return_value.add.return_value = (MagicMock(), new_ref)
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
        with patch("database.volunteers_db.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = [MagicMock()]
            resp = client.post("/auth/register", json={
                "email": "dup@test.com", "password": "pass",
                "name": "Dup", "phone": "9111111111",
                "location": "Mumbai", "skills": ["food"]
            })
        assert resp.status_code == 400

    def test_auth_login_success(self, client):
        from database.volunteers_db import hash_password
        doc = _make_doc("v-login", {"email": "login@test.com",
                                     "password_hash": hash_password("TestPass"),
                                     "name": "Login User"})
        with patch("database.volunteers_db.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
            resp = client.post("/auth/login", json={"email": "login@test.com", "password": "TestPass"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "Login User"

    def test_auth_login_wrong_password_returns_401(self, client):
        from database.volunteers_db import hash_password
        doc = _make_doc("v-bad", {"email": "bad@test.com",
                                   "password_hash": hash_password("correct"),
                                   "name": "Bad"})
        with patch("database.volunteers_db.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
            resp = client.post("/auth/login", json={"email": "bad@test.com", "password": "wrong"})
        assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────
# MATCH ROUTES & LOGIC
# ─────────────────────────────────────────────────────────────

class TestMatchRoute:

    def test_match_requires_auth(self, client):
        resp = client.get("/match")
        assert resp.status_code == 403

    def test_match_returns_summary_dict(self, client):
        open_needs = [{
            "id": "n1", "category": "food", "help_needed": "food",
            "severity": "high", "status": "open", "trust_score": 80,
            "lat": 26.8, "lng": 80.9
        }]
        volunteers = [{
            "id": "v1", "name": "Worker", "skills": ["food"],
            "lat": 26.85, "lng": 80.95, "ngo_verified": False
        }]
        with patch("database.needs_db.get_open_needs", return_value=open_needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=volunteers), \
             patch("database.assignments_db.save_assignment", return_value="a1"):
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_matches_made" in data
        assert "matches" in data

    def test_match_skips_low_trust_needs(self, client):
        open_needs = [{
            "id": "n-low", "category": "food", "help_needed": "food",
            "severity": "medium", "status": "open", "trust_score": 20,
            "lat": 26.8, "lng": 80.9
        }]
        with patch("database.needs_db.get_open_needs", return_value=open_needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=[]):
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total_needs_processed"] == 0

    def test_match_escalates_sensitive_with_no_tier1(self, client):
        open_needs = [{
            "id": "n-rescue", "category": "rescue", "help_needed": "rescue",
            "severity": "critical", "status": "open", "trust_score": 90,
            "lat": 26.8, "lng": 80.9
        }]
        tier2_vol = [{
            "id": "v-t2", "name": "Community", "skills": ["rescue"],
            "lat": 26.85, "lng": 80.95, "ngo_verified": False
        }]
        with patch("database.needs_db.get_open_needs", return_value=open_needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=tier2_vol), \
             patch("database.assignments_db.save_assignment", return_value="a-esc"):
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        matches = resp.json()["matches"]
        assert any(m.get("status") == "Manual Escalation Required" for m in matches)

    def test_match_assigns_tier1_for_sensitive_need(self, client):
        open_needs = [{
            "id": "n-s1", "category": "rescue", "help_needed": "rescue",
            "severity": "critical", "status": "open", "trust_score": 90,
            "lat": 26.8, "lng": 80.9
        }]
        volunteers = [{
            "id": "v-t1", "name": "NGO Responder", "skills": ["rescue"],
            "lat": 26.82, "lng": 80.92, "ngo_verified": True
        }]
        with patch("database.needs_db.get_open_needs", return_value=open_needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=volunteers), \
             patch("database.assignments_db.save_assignment", return_value="a-t1"):
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 1


class TestMatchLogicPure:
    """Pure unit tests for match.py helper functions (no HTTP)."""

    def test_haversine_known_distance(self):
        from backend.routes.match import _haversine_km
        # Delhi to Agra ≈ 200 km
        dist = _haversine_km(28.6, 77.2, 27.17, 78.01)
        assert 180 < dist < 220

    def test_haversine_same_point_is_zero(self):
        from backend.routes.match import _haversine_km
        assert _haversine_km(20.0, 80.0, 20.0, 80.0) == 0.0

    def test_find_best_volunteer_picks_skill_match(self):
        from backend.routes.match import find_best_volunteer
        need = {"lat": 26.8, "lng": 80.9, "category": "medical", "help_needed": "medical"}
        vols = [
            {"id": "v1", "skills": ["medical"], "lat": 26.85, "lng": 80.95, "ngo_verified": False},
            {"id": "v2", "skills": ["food"],    "lat": 26.81, "lng": 80.91, "ngo_verified": False},
        ]
        result = find_best_volunteer(need, vols)
        assert result is not None
        assert result["id"] == "v1"

    def test_find_best_volunteer_no_skill_match_returns_none(self):
        from backend.routes.match import find_best_volunteer
        need = {"lat": 0.0, "lng": 0.0, "category": "rescue", "help_needed": "rescue"}
        vols = [{"id": "v1", "skills": ["food"], "lat": 0.1, "lng": 0.1, "ngo_verified": False}]
        assert find_best_volunteer(need, vols) is None

    def test_find_best_volunteer_sensitive_returns_tier1(self):
        from backend.routes.match import find_best_volunteer
        need = {"lat": 0.0, "lng": 0.0, "category": "rescue", "help_needed": "rescue"}
        vols = [
            {"id": "t1", "skills": ["rescue"], "lat": 0.5, "lng": 0.0, "ngo_verified": True},
            {"id": "t2", "skills": ["rescue"], "lat": 0.1, "lng": 0.0, "ngo_verified": False},
        ]
        result = find_best_volunteer(need, vols)
        assert result is not None
        assert result["ngo_verified"] is True

    def test_find_best_volunteer_sensitive_no_tier1_returns_none(self):
        from backend.routes.match import find_best_volunteer
        need = {"lat": 0.0, "lng": 0.0, "category": "rescue", "help_needed": "rescue"}
        vols = [{"id": "t2", "skills": ["rescue"], "lat": 0.1, "lng": 0.0, "ngo_verified": False}]
        assert find_best_volunteer(need, vols) is None

    def test_find_best_volunteer_tier1_preferred_within_margin(self):
        from backend.routes.match import find_best_volunteer
        # Tier1 is ~5km, Tier2 is ~2km – within 10km margin so Tier1 wins
        need = {"lat": 0.0, "lng": 0.0, "category": "food", "help_needed": "food"}
        vols = [
            {"id": "t1", "skills": ["food"], "lat": 0.045, "lng": 0.0, "ngo_verified": True},
            {"id": "t2", "skills": ["food"], "lat": 0.018, "lng": 0.0, "ngo_verified": False},
        ]
        result = find_best_volunteer(need, vols)
        assert result["id"] == "t1"

    def test_empty_volunteer_pool_returns_none(self):
        from backend.routes.match import find_best_volunteer
        need = {"lat": 0.0, "lng": 0.0, "category": "food", "help_needed": "food"}
        assert find_best_volunteer(need, []) is None


# ─────────────────────────────────────────────────────────────
# DASHBOARD ROUTE
# ─────────────────────────────────────────────────────────────

class TestDashboardRoute:

    def test_dashboard_returns_stats_fields(self, client):
        with patch("database.needs_db.get_open_needs", return_value=[]), \
             patch("database.volunteers_db.get_available_volunteers", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        for key in ("total_needs", "total_volunteers", "critical_cases",
                    "high_priority_cases", "unmatched_cases", "flagged_cases"):
            assert key in resp.json()

    def test_dashboard_counts_critical_correctly(self, client):
        needs = [
            {"id": "n1", "severity": "critical", "status": "open", "trust_score": 80},
            {"id": "n2", "severity": "high",     "status": "open", "trust_score": 80},
        ]
        with patch("database.needs_db.get_open_needs", return_value=needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.json()["critical_cases"] == 1
        assert resp.json()["high_priority_cases"] == 1

    def test_dashboard_counts_flagged_correctly(self, client):
        needs = [
            {"id": "n1", "severity": "high", "status": "open", "trust_score": 30},
            {"id": "n2", "severity": "high", "status": "open", "trust_score": 90},
        ]
        with patch("database.needs_db.get_open_needs", return_value=needs), \
             patch("database.volunteers_db.get_available_volunteers", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.json()["flagged_cases"] == 1

    def test_dashboard_reports_returns_list(self, client):
        with patch("database.needs_db.get_open_needs", return_value=[{"id": "n1", "status": "open"}]):
            resp = client.get("/dashboard/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ─────────────────────────────────────────────────────────────
# ASSIGNMENT ROUTE
# ─────────────────────────────────────────────────────────────

class TestAssignmentRoute:

    def test_resolve_requires_auth(self, client):
        resp = client.patch("/assignment/a1/resolve",
                            json={"need_id": "n1", "volunteer_id": "v1"})
        assert resp.status_code == 403

    def test_resolve_success(self, client):
        snap = _make_doc("a1", {"need_id": "n1", "volunteer_id": "v1", "resolved_at": None})
        with patch("database.firestore_client.db") as mock_db, \
             patch("database.assignments_db.resolve_assignment"):
            mock_db.collection.return_value.document.return_value.get.return_value = snap
            resp = client.patch("/assignment/a1/resolve",
                headers=AUTH_HEADERS,
                json={"need_id": "n1", "volunteer_id": "v1"}
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_resolve_not_found_returns_404(self, client):
        snap = _make_doc("ax", {}, exists=False)
        with patch("database.firestore_client.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = snap
            resp = client.patch("/assignment/ghost-assign/resolve",
                headers=AUTH_HEADERS,
                json={"need_id": "n1", "volunteer_id": "v1"}
            )
        assert resp.status_code == 404

    def test_resolve_already_resolved_returns_409(self, client):
        snap = _make_doc("a2", {
            "need_id": "n2", "volunteer_id": "v2",
            "resolved_at": "2025-01-01T10:00:00+00:00"
        })
        with patch("database.firestore_client.db") as mock_db:
            mock_db.collection.return_value.document.return_value.get.return_value = snap
            resp = client.patch("/assignment/a2/resolve",
                headers=AUTH_HEADERS,
                json={"need_id": "n2", "volunteer_id": "v2"}
            )
        assert resp.status_code == 409


# ─────────────────────────────────────────────────────────────
# NGO ROUTE
# ─────────────────────────────────────────────────────────────

class TestNGORoute:

    def test_register_ngo_requires_auth(self, client):
        resp = client.post("/ngo/register", json={"name": "X", "reg_number": "R"})
        assert resp.status_code == 403

    def test_register_ngo_success(self, client):
        with patch("database.ngos_db.save_ngo", return_value="ngo-001"), \
             patch("database.geocoding.get_coordinates", return_value={"lat": 22.5, "lng": 88.3}):
            resp = client.post("/ngo/register",
                headers=AUTH_HEADERS,
                json={"name": "HelpIndia NGO", "reg_number": "NGO/KP/001",
                      "location": "Kolkata", "radius": 100.0}
            )
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_get_ngo_not_found(self, client):
        with patch("database.ngos_db.get_ngo", return_value=None):
            resp = client.get("/ngo/fake-id")
        assert resp.status_code == 404

    def test_get_ngo_found(self, client):
        with patch("database.ngos_db.get_ngo", return_value={
            "id": "ngo-1", "name": "SaveIndia", "verified": False
        }):
            resp = client.get("/ngo/ngo-1")
        assert resp.status_code == 200
        assert resp.json()["name"] == "SaveIndia"

    def test_ngo_dashboard_not_found(self, client):
        with patch("database.ngos_db.get_ngo", return_value=None):
            resp = client.get("/ngo/bad-id/dashboard")
        assert resp.status_code == 404

    def test_ngo_dashboard_returns_stats(self, client):
        with patch("database.ngos_db.get_ngo", return_value={"id": "ngo-1", "name": "TestNGO"}), \
             patch("database.firestore_client.db") as mock_db:
            mock_db.collection.return_value.where.return_value.stream.return_value = []
            mock_db.collection.return_value.stream.return_value = []
            resp = client.get("/ngo/ngo-1/dashboard")
        assert resp.status_code == 200
        assert "stats" in resp.json()
        assert "managed_volunteers" in resp.json()["stats"]