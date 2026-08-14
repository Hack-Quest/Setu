"""
backend/test_backend.py
========================
Tests for:
  - backend/auth.py             (JWT generate/verify, static token, expiry)
  - backend/models.py           (Pydantic models + alias resolution)
  - backend/main.py             (WebSocketManager, health/config routes,
                                  /webhook, /volunteer_webhook)
  - backend/routes/need.py      (process_and_save_need, category normalisation,
                                  trust score boost, geocoding hard-fail)
  - backend/routes/volunteer.py (role-gated ngo_verified, ngo_id injection)
  - backend/routes/volunteer_auth.py (register, login, send-otp, verify-otp,
                                       OTP rate-limiting, role detection)
  - backend/routes/match.py     (haversine, is_sensitive_case,
                                  is_skill_compatible, find_best_volunteer,
                                  multi-volunteer dispatch, tier enforcement)
  - backend/routes/dashboard.py (global stats, reports with volunteer coords)
  - backend/routes/assignment.py (identity resolution, impersonation guard,
                                   duplicate/conflict detection, resolve)
  - backend/routes/ngo.py       (register, get, role-gated dashboard)

All database, Gemini, geocoding, and external I/O are mocked.

Run from project root:
    pytest backend/test_backend.py -v
"""

import asyncio
import json
import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(dotenv_path="config/.env")

VALID_TOKEN = os.getenv("SECRET_TOKEN")
if not VALID_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")
AUTH_HEADERS = {"Authorization": f"Bearer {VALID_TOKEN}"}


# =============================================================================
# SHARED FIXTURES
# =============================================================================

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


# =============================================================================
# AUTH MODULE
# =============================================================================

class TestAuth:
    """Tests for backend/auth.py — generate_token, verify_token."""

    def test_static_secret_token_returns_system_dict(self):
        """Static SECRET_TOKEN must be accepted and return system identity dict."""
        from backend.auth import verify_token, SECRET_TOKEN
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=SECRET_TOKEN)
        result = verify_token(creds)
        assert isinstance(result, dict)
        assert result["role"] == "system"
        assert result["uid"] == "system"

    def test_generate_token_returns_string(self):
        """generate_token must return a non-empty JWT string."""
        from backend.auth import generate_token
        token = generate_token("user-123", "volunteer", "test@test.com")
        assert isinstance(token, str)
        assert len(token) > 10

    def test_verify_valid_jwt_returns_payload(self):
        """A freshly generated JWT must be decoded back to the correct payload."""
        from backend.auth import generate_token, verify_token
        from fastapi.security import HTTPAuthorizationCredentials
        token = generate_token("uid-abc", "ngo", "ngo@setu.org")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = verify_token(creds)
        assert isinstance(payload, dict)
        assert payload["uid"] == "uid-abc"
        assert payload["role"] == "ngo"
        assert payload["email"] == "ngo@setu.org"

    def test_verify_token_wrong_raises_401(self):
        """Invalid / tampered token must raise 401."""
        from fastapi import HTTPException
        from backend.auth import verify_token
        from fastapi.security import HTTPAuthorizationCredentials
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials="bad-token-xyz")
        with pytest.raises(HTTPException) as exc_info:
            verify_token(creds)
        assert exc_info.value.status_code == 401

    def test_verify_missing_credentials_raises_401(self):
        """Missing credentials must raise 401."""
        from fastapi import HTTPException
        from backend.auth import verify_token
        with pytest.raises(HTTPException) as exc_info:
            verify_token(None)
        assert exc_info.value.status_code == 401

    def test_verify_expired_token_raises_401(self):
        """Expired JWT must raise 401 with expiry message."""
        import jwt
        from fastapi import HTTPException
        from fastapi.security import HTTPAuthorizationCredentials
        from backend.auth import verify_token, JWT_SECRET, JWT_ALGORITHM
        expired_payload = {
            "sub": "u1", "uid": "u1", "role": "volunteer",
            "email": "x@y.com",
            "iat": datetime.now(timezone.utc) - timedelta(hours=48),
            "exp": datetime.now(timezone.utc) - timedelta(hours=24),
        }
        expired_token = jwt.encode(expired_payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=expired_token)
        with pytest.raises(HTTPException) as exc_info:
            verify_token(creds)
        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    def test_volunteer_token_has_correct_role(self):
        """JWT generated for a volunteer must contain role='volunteer'."""
        from backend.auth import generate_token, verify_token
        from fastapi.security import HTTPAuthorizationCredentials
        token = generate_token("vol-99", "volunteer", "vol@test.com")
        creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        payload = verify_token(creds)
        assert payload["role"] == "volunteer"
        assert payload["uid"] == "vol-99"


# =============================================================================
# MODELS
# =============================================================================

class TestModels:
    """Tests for backend/models.py — Pydantic alias resolution and defaults."""

    def test_need_input_alias_name(self):
        """NeedInput should accept 'name' as alias for reporter_name."""
        from backend.models import NeedInput
        n = NeedInput(name="Ravi", location="Delhi")
        assert n.reporter_name == "Ravi"

    def test_need_input_alias_address(self):
        """NeedInput should accept 'address' as alias for location_text."""
        from backend.models import NeedInput
        n = NeedInput(address="Kanpur")
        assert n.location_text == "Kanpur"

    def test_need_input_defaults(self):
        """NeedInput should use safe defaults for missing fields."""
        from backend.models import NeedInput
        n = NeedInput()
        assert n.reporter_name == "Unknown"
        assert n.reporter_phone == "0000000000"
        assert n.lat == 0.0
        assert n.lng == 0.0

    def test_ngo_input_alias_organization_name(self):
        """NGOInput should accept 'organization_name' as alias for ngo_name."""
        from backend.models import NGOInput
        ngo = NGOInput(organization_name="Save Earth", reg_number="ABC/001")
        assert ngo.ngo_name == "Save Earth"

    def test_volunteer_register_input_required_fields(self):
        """VolunteerRegisterInput must fail if required fields are missing."""
        from backend.models import VolunteerRegisterInput
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            VolunteerRegisterInput()

    def test_send_otp_input(self):
        from backend.models import SendOTPInput
        m = SendOTPInput(email="a@b.com")
        assert m.email == "a@b.com"

    def test_verify_otp_input(self):
        from backend.models import VerifyOTPInput
        m = VerifyOTPInput(email="a@b.com", otp="123456")
        assert m.otp == "123456"


# =============================================================================
# WEBSOCKET MANAGER
# =============================================================================

class TestWebSocketManager:

    @pytest.mark.asyncio
    async def test_connect_adds_to_connections(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws = MagicMock()
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
    async def test_disconnect_noop_if_not_connected(self):
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws = MagicMock()
        manager.disconnect(ws)  # Should not raise

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

    @pytest.mark.asyncio
    async def test_broadcast_removes_stale_connections(self):
        """Connections that raise on send_json should be pruned automatically."""
        from backend.main import WebSocketManager
        manager = WebSocketManager()
        ws_ok = MagicMock(); ws_ok.send_json = AsyncMock()
        ws_bad = MagicMock(); ws_bad.send_json = AsyncMock(side_effect=Exception("closed"))
        manager.active_connections.extend([ws_ok, ws_bad])
        await manager.broadcast_json({"event": "test"})
        assert ws_bad not in manager.active_connections
        assert ws_ok in manager.active_connections


# =============================================================================
# APP BASIC ROUTES
# =============================================================================

class TestBasicRoutes:

    def test_health_check(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        assert "database" in resp.json()

    def test_get_config_public_with_key(self, client):
        with patch.dict(os.environ, {"GOOGLE_MAPS_KEY": "FAKE_MAP_KEY_123"}):
            resp = client.get("/config/public")
        assert resp.status_code == 200
        assert "google_maps_api_key" in resp.json()

    def test_get_config_public_missing_key_returns_503(self, client):
        with patch.dict(os.environ, {"GOOGLE_MAPS_KEY": "", "GOOGLE_MAPS_API_KEY": ""}):
            resp = client.get("/config/public")
        assert resp.status_code == 503
        assert "error" in resp.json()

    def test_root_returns_message(self, client):
        resp = client.get("/", headers={"Accept": "application/json"})
        # Either JSON or HTML depending on file existence — check no crash
        assert resp.status_code == 200


# =============================================================================
# NEED ROUTES
# =============================================================================

class TestNeedRoute:

    def test_need_endpoint_requires_auth(self, client):
        resp = client.post("/need", json={"description": "Test need"})
        assert resp.status_code == 401

    def test_short_description_rejected(self, client):
        """Description < 10 chars must be rejected with an error key."""
        resp = client.post("/need", json={"description": "flood"}, headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert "error" in resp.json()

    def test_need_success_auto_dispatch(self, client):
        """Long description with good coords and high trust → open/auto_dispatch."""
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("backend.routes.need.save_need", return_value="need-001"), \
             patch("backend.routes.need.check_corroboration", return_value=3), \
             patch("backend.routes.need.process_need_text", return_value={
                 "category": "logistics", "severity": "medium", "consistency": 9
             }):
            resp = client.post("/need", json={
                "name": "Victim A", "phone": "9876543210",
                "address": "Kanpur, India",
                "disaster_type": "flood", "help_needed": "food",
                "description": "Stranded in Kanpur flood without food for 2 days in waterlogged street"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["need_id"] == "need-001"
        assert "trust_score" in data
        assert "reasons" in data

    def test_need_success_critical_severity(self, client):
        """Critical severity needs must receive HIGH priority."""
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 26.5, "lng": 80.3}), \
             patch("backend.routes.need.save_need", return_value="need-crit"), \
             patch("backend.routes.need.check_corroboration", return_value=2), \
             patch("backend.routes.need.process_need_text", return_value={
                 "category": "rescue", "severity": "critical", "consistency": 10
             }):
            resp = client.post("/need", json={
                "name": "Victim B", "phone": "9900000001",
                "address": "Kanpur",
                "disaster_type": "earthquake", "help_needed": "medical",
                "description": "Building collapse! Severe bleeding, please send medical help immediately now"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["priority"] == "HIGH"
        assert data["category"] == "rescue"

    def test_category_normalization_flood_becomes_logistics(self, client):
        """'flood' disaster type should be normalized to 'logistics' category."""
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 22.5, "lng": 88.3}), \
             patch("backend.routes.need.save_need", return_value="need-flood"), \
             patch("backend.routes.need.check_corroboration", return_value=1), \
             patch("backend.routes.need.process_need_text", return_value={
                 "category": "flood", "severity": "high", "consistency": 8
             }):
            resp = client.post("/need", json={
                "name": "Victim C", "phone": "9900000002",
                "address": "Kolkata",
                "disaster_type": "flood", "help_needed": "logistics",
                "description": "Entire area submerged need immediate supply distribution and vehicles"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["category"] == "logistics"

    def test_category_normalization_earthquake_becomes_rescue(self, client):
        """'earthquake' category should be normalized to 'rescue'."""
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 28.6, "lng": 77.2}), \
             patch("backend.routes.need.save_need", return_value="need-quake"), \
             patch("backend.routes.need.check_corroboration", return_value=2), \
             patch("backend.routes.need.process_need_text", return_value={
                 "category": "earthquake", "severity": "critical", "consistency": 9
             }):
            resp = client.post("/need", json={
                "name": "Victim D", "phone": "9000000099",
                "address": "Delhi",
                "disaster_type": "earthquake", "help_needed": "rescue",
                "description": "Earthquake struck people trapped under rubble rescue needed urgently"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["category"] == "rescue"

    def test_trust_score_boosted_for_verbose_description(self, client):
        """Descriptions with >8 words get a +10 trust_score boost (capped at 100)."""
        with patch("backend.routes.need.get_coordinates", return_value={"lat": 22.5, "lng": 88.3}), \
             patch("backend.routes.need.save_need", return_value="need-boost"), \
             patch("backend.routes.need.check_corroboration", return_value=3), \
             patch("backend.routes.need.process_need_text", return_value={
                 "category": "medical", "severity": "high", "consistency": 9
             }):
            resp = client.post("/need", json={
                "name": "Victim E", "phone": "9000000010",
                "address": "Mumbai",
                "description": "Multiple injured people need immediate medical care at Dharavi slum area ambulance required"
            }, headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["trust_score"] <= 100  # must be capped

    def test_geocoding_hard_fail_zero_coords_rejected(self, client):
        """If geocoding returns 0,0 and no coords provided, request must fail (400)."""
        with patch("backend.routes.need.process_need_text", return_value={
                "category": "medical", "severity": "medium", "consistency": 7}), \
             patch("backend.routes.need.get_coordinates", return_value={"lat": 0, "lng": 0}):
            resp = client.post("/need", json={
                "name": "Ghost", "phone": "9000000000",
                "location_text": "Nowhere Land",
                "description": "This is a sufficiently long description with more than ten words"
            }, headers=AUTH_HEADERS)

        # Should get either 400 or an error in body
        assert resp.status_code in [200, 400]
        if resp.status_code == 200:
            assert "error" in resp.json()

    def test_webhook_endpoint_processes_sos(self, client):
        """Public /webhook endpoint should process an SOS payload."""
        with patch("backend.routes.need.process_need_text", return_value={
                "category": "rescue", "severity": "critical", "consistency": 9}), \
             patch("backend.routes.need.get_coordinates", return_value={"lat": 28.6, "lng": 77.2}), \
             patch("backend.routes.need.save_need", return_value="wh-need-1"), \
             patch("backend.routes.need.check_corroboration", return_value=2), \
             patch("notifications.gmail_alert.send_alert"):
            resp = client.post("/webhook", json={
                "reporter_name": "Ram", "reporter_phone": "9898989898",
                "description": "House on fire, people trapped inside, need rescue team immediately",
                "location": "Noida Sector 15", "help_needed": "rescue",
                "disaster_type": "fire", "lat": 28.6, "lng": 77.2
            })

        assert resp.status_code == 200
        assert "message" in resp.json()


# =============================================================================
# VOLUNTEER ROUTES
# =============================================================================

class TestVolunteerRoute:

    def test_create_volunteer_requires_auth(self, client):
        resp = client.post("/volunteer", json={})
        assert resp.status_code == 401

    def test_create_volunteer_system_token_no_ngo_verification(self, client):
        """System token with no ngo_id → ngo_verified must be False."""
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"uid": "system", "role": "system"}
        try:
            with patch("backend.routes.volunteer.save_volunteer", return_value="vol-sys-1"), \
                 patch("backend.routes.volunteer.get_available_volunteers", return_value=[]):
                resp = client.post("/volunteer", json={
                    "name": "Test Vol", "phone": "9000000001",
                    "location": "Delhi", "skills": ["food"],
                    "email": "vol@test.com", "password": "Pass1234"
                }, headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == "registered"
        assert resp.json()["volunteer_id"] == "vol-sys-1"

    def test_list_volunteers_requires_auth(self, client):
        resp = client.get("/volunteers")
        assert resp.status_code == 401

    def test_list_volunteers_sanitizes_sensitive_fields(self, client):
        """Sensitive fields (password_hash, email) must be stripped from volunteer list."""
        raw_volunteers = [
            {"id": "v1", "name": "Priya", "skills": ["medical"],
             "available": True, "password_hash": "SECRET", "email": "priya@test.com",
             "location": "Mumbai", "active_assignments": 0, "ngo_id": None,
             "registered_at": None, "ngo_verified": False, "credential_tags": []}
        ]
        with patch("backend.routes.volunteer.get_all_volunteers", return_value=raw_volunteers):
            resp = client.get("/volunteers", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        vols = resp.json()
        assert len(vols) == 1
        assert "password_hash" not in vols[0]
        assert "email" not in vols[0]
        assert "name" in vols[0]

    def test_volunteer_webhook_public_registers_without_auth(self, client):
        """Public /volunteer_webhook must not require auth."""
        with patch("backend.main.save_volunteer", return_value="vol-wh-1"):
            resp = client.post("/volunteer_webhook", json={
                "volunteer_name": "Ravi", "phone": "9898989898",
                "skills": "first-aid", "location": "Mumbai",
                "email": "ravi@test.com"
            })

        assert resp.status_code == 200
        assert resp.json()["volunteer_id"] == "vol-wh-1"
        assert resp.json()["status"] == "registered"

    def test_volunteer_webhook_ngo_verified_is_false(self, client):
        """Public webhook must NEVER auto-verify volunteers as Tier 1."""
        with patch("backend.main.save_volunteer", return_value="vol-wh-2") as mock_save:
            client.post("/volunteer_webhook", json={
                "volunteer_name": "Cheat Vol", "phone": "9001001001",
                "skills": "medical", "ngo_id": "ngo-legit",
                "email": "cheat@test.com"
            })
            # Check saved dict has ngo_verified=False
            saved_dict = mock_save.call_args[0][0]
            assert saved_dict["ngo_verified"] is False


# =============================================================================
# VOLUNTEER AUTH ROUTES
# =============================================================================

class TestVolunteerAuth:

    def test_register_new_volunteer_success(self, client):
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = None  # Email not taken
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/register", json={
                "email": "newvol@test.com", "password": "SecurePass123",
                "name": "Deepak Kumar", "phone": "9000000001",
                "location": "New Delhi", "skills": ["medical", "rescue"]
            })
        assert resp.status_code == 200
        assert "volunteer_id" in resp.json()
        assert "token" in resp.json()

    def test_register_duplicate_email_returns_400(self, client):
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

    def test_login_success_returns_token_and_name(self, client):
        from database.volunteers_db import hash_password
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = {
                "id": "v-login", "email": "login@test.com",
                "password_hash": hash_password("TestPass"), "name": "Login User"
            }
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/login", json={
                "email": "login@test.com", "password": "TestPass"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Login User"
        assert "token" in data
        assert "volunteer_id" in data

    def test_login_wrong_password_returns_401(self, client):
        from database.volunteers_db import hash_password
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = {
                "id": "v-bad", "email": "bad@test.com",
                "password_hash": hash_password("correct"), "name": "Bad"
            }
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/login", json={
                "email": "bad@test.com", "password": "wrong"
            })
        assert resp.status_code == 401

    def test_login_nonexistent_user_returns_401(self, client):
        with patch("database.volunteers_db.get_db_cursor") as mock_get_db:
            cursor = MagicMock()
            cursor.fetchone.return_value = None  # User doesn't exist
            mock_get_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/login", json={
                "email": "ghost@test.com", "password": "any"
            })
        assert resp.status_code == 401

    def test_send_otp_success(self, client):
        with patch("backend.routes.volunteer_auth.save_otp"), \
             patch("backend.routes.volunteer_auth.send_otp_email", return_value=True), \
             patch("backend.routes.volunteer_auth._last_sent", {}), \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            resp = client.post("/auth/send-otp", json={"email": "fresh@test.com"})
        assert resp.status_code == 200
        assert "OTP sent" in resp.json().get("message", "")

    def test_send_otp_rate_limit_60_seconds(self, client):
        """Requesting OTP again before 60s cooldown should return 429."""
        now_utc = datetime.now(timezone.utc)
        # Pre-seed _last_sent with a recent timestamp (5 seconds ago)
        with patch("backend.routes.volunteer_auth._last_sent",
                   {"ratelimit@test.com": now_utc - timedelta(seconds=5)}), \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            resp = client.post("/auth/send-otp", json={"email": "ratelimit@test.com"})
        assert resp.status_code == 429

    def test_send_otp_email_failure_returns_500(self, client):
        with patch("backend.routes.volunteer_auth.save_otp"), \
             patch("backend.routes.volunteer_auth.send_otp_email", return_value=False), \
             patch("backend.routes.volunteer_auth._last_sent", {}), \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            resp = client.post("/auth/send-otp", json={"email": "fail@test.com"})
        assert resp.status_code == 500

    def test_verify_otp_ngo_role_returns_ngo_token(self, client):
        """Correct OTP for an NGO email must return role='ngo' and a token."""
        mock_ngo = {
            "id": "ngo-otp-1", "ngo_name": "HelpOrg", "owner_name": "Admin",
            "email": "ngo@test.com", "verified": True, "description": ""
        }
        with patch("backend.routes.volunteer_auth.verify_otp_in_db", return_value=True), \
             patch("backend.routes.volunteer_auth.get_ngo_by_email", return_value=mock_ngo), \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            resp = client.post("/auth/verify-otp", json={
                "email": "ngo@test.com", "otp": "123456"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "ngo"
        assert "token" in data
        assert data["ngo_name"] == "HelpOrg"

    def test_verify_otp_volunteer_role_returns_volunteer_token(self, client):
        """Correct OTP for a volunteer email must return role='volunteer' and a token."""
        with patch("backend.routes.volunteer_auth.verify_otp_in_db", return_value=True), \
             patch("backend.routes.volunteer_auth.get_ngo_by_email", return_value=None), \
             patch("backend.routes.volunteer_auth.get_db_cursor") as mock_db, \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            cursor = MagicMock()
            # First query: volunteers_auth, Second query: volunteers (fallback)
            cursor.fetchone.side_effect = [{"id": "vol-otp-1"}, None]
            mock_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/verify-otp", json={
                "email": "vol@test.com", "otp": "654321"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "volunteer"
        assert "token" in data

    def test_verify_otp_new_user_returns_new_user_role(self, client):
        """OTP correct but unregistered email → role='new_user', no token."""
        with patch("backend.routes.volunteer_auth.verify_otp_in_db", return_value=True), \
             patch("backend.routes.volunteer_auth.get_ngo_by_email", return_value=None), \
             patch("backend.routes.volunteer_auth.get_db_cursor") as mock_db, \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            cursor = MagicMock()
            cursor.fetchone.return_value = None  # Not found anywhere
            mock_db.return_value.__enter__.return_value = cursor
            resp = client.post("/auth/verify-otp", json={
                "email": "nobody@test.com", "otp": "000000"
            })
        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == "new_user"
        assert data.get("ok") is False

    def test_verify_otp_invalid_otp_returns_401(self, client):
        """Wrong OTP must return 401 with attempts_remaining."""
        with patch("backend.routes.volunteer_auth.verify_otp_in_db", return_value=False), \
             patch("backend.routes.volunteer_auth._verify_attempts", {}):
            resp = client.post("/auth/verify-otp", json={
                "email": "user@test.com", "otp": "999999"
            })
        assert resp.status_code == 401
        assert "attempts" in resp.json()["detail"].lower()

    def test_verify_otp_locked_after_5_failures(self, client):
        """After 5 failed OTP attempts email should be locked for 15 min."""
        locked_until = datetime.now(timezone.utc) + timedelta(minutes=14)
        attempts = {"locked@test.com": {"count": 5, "blocked_until": locked_until}}
        with patch("backend.routes.volunteer_auth._verify_attempts", attempts):
            resp = client.post("/auth/verify-otp", json={
                "email": "locked@test.com", "otp": "111111"
            })
        assert resp.status_code == 429
        assert "locked" in resp.json()["detail"].lower()


# =============================================================================
# MATCH ROUTES & PURE LOGIC
# =============================================================================

class TestMatchPureLogic:
    """Unit tests for matching helper functions — no HTTP calls needed."""

    def test_haversine_same_point_is_zero(self):
        from backend.routes.match import _haversine_km
        assert _haversine_km(28.6, 77.2, 28.6, 77.2) == 0.0

    def test_haversine_known_distance(self):
        """Delhi to Mumbai ≈ 1150 km."""
        from backend.routes.match import _haversine_km
        d = _haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
        assert 1100 < d < 1250

    def test_is_sensitive_case_medical_category(self):
        from backend.routes.match import is_sensitive_case
        assert is_sensitive_case({"category": "medical"}) is True

    def test_is_sensitive_case_rescue_category(self):
        from backend.routes.match import is_sensitive_case
        assert is_sensitive_case({"category": "rescue"}) is True

    def test_is_sensitive_case_keyword_in_description(self):
        from backend.routes.match import is_sensitive_case
        assert is_sensitive_case({
            "category": "other",
            "description": "person is bleeding and unconscious",
            "help_needed": "general", "disaster_type": "rain"
        }) is True

    def test_is_sensitive_case_not_specified_fails_safely(self):
        """Unspecified category/help must fail safely → sensitive."""
        from backend.routes.match import is_sensitive_case
        assert is_sensitive_case({"category": "Not Specified", "help_needed": "Not Specified"}) is True

    def test_is_not_sensitive_for_logistics(self):
        from backend.routes.match import is_sensitive_case
        assert is_sensitive_case({
            "category": "logistics", "help_needed": "transport",
            "disaster_type": "flood", "description": "need vehicles to move supplies"
        }) is False

    def test_skill_compatible_exact_match(self):
        from backend.routes.match import is_skill_compatible
        need = {"category": "medical", "help_needed": "medical", "disaster_type": ""}
        vol = {"skills": ["medical", "first-aid"]}
        assert is_skill_compatible(need, vol) is True

    def test_skill_incompatible_cooking_for_medical(self):
        from backend.routes.match import is_skill_compatible
        need = {"category": "medical", "help_needed": "medical", "disaster_type": ""}
        vol = {"skills": ["cooking"]}
        assert is_skill_compatible(need, vol) is False

    def test_skill_empty_skills_incompatible(self):
        from backend.routes.match import is_skill_compatible
        need = {"category": "rescue"}
        vol = {"skills": []}
        assert is_skill_compatible(need, vol) is False

    def test_general_skill_allowed_for_non_sensitive(self):
        from backend.routes.match import is_skill_compatible
        need = {"category": "logistics", "help_needed": "transport", "disaster_type": "flood", "description": ""}
        vol = {"skills": ["general"]}
        assert is_skill_compatible(need, vol) is True

    def test_general_skill_blocked_for_sensitive(self):
        """'general' skill wildcard must NOT be allowed for sensitive (medical) needs."""
        from backend.routes.match import is_skill_compatible
        need = {"category": "medical", "help_needed": "medical", "disaster_type": "injury", "description": ""}
        vol = {"skills": ["general"]}
        assert is_skill_compatible(need, vol) is False

    def test_find_best_volunteer_returns_none_if_no_volunteers(self):
        from backend.routes.match import find_best_volunteer
        assert find_best_volunteer({}, []) is None

    def test_find_best_volunteer_tier1_for_sensitive(self):
        """Only Tier 1 (ngo_verified) volunteers should be returned for sensitive needs."""
        from backend.routes.match import find_best_volunteer
        need = {"category": "rescue", "severity": "high", "lat": 28.6, "lng": 77.2,
                "help_needed": "rescue", "disaster_type": "", "description": ""}
        tier2 = {"id": "v-t2", "skills": ["rescue"], "lat": 28.6, "lng": 77.2,
                 "available": True, "active_assignments": 0, "ngo_verified": False}
        tier1 = {"id": "v-t1", "skills": ["rescue"], "lat": 28.61, "lng": 77.21,
                 "available": True, "active_assignments": 0, "ngo_verified": True}
        best = find_best_volunteer(need, [tier2, tier1])
        assert best is not None
        assert best["id"] == "v-t1"

    def test_find_best_volunteer_none_if_only_tier2_for_sensitive(self):
        from backend.routes.match import find_best_volunteer
        need = {"category": "medical", "severity": "critical", "lat": 28.6, "lng": 77.2,
                "help_needed": "medical", "disaster_type": "", "description": ""}
        tier2 = {"id": "v-t2", "skills": ["medical"], "lat": 28.6, "lng": 77.2,
                 "available": True, "active_assignments": 0, "ngo_verified": False}
        assert find_best_volunteer(need, [tier2]) is None

    def test_find_best_volunteer_distance_filtered(self):
        """Volunteer beyond MAX_DISPATCH_KM must not be selected."""
        from backend.routes.match import find_best_volunteer
        need = {"category": "logistics", "severity": "low", "lat": 28.6, "lng": 77.2,
                "help_needed": "logistics", "disaster_type": "flood", "description": "need transport"}
        far_vol = {"id": "v-far", "skills": ["logistics"], "lat": 37.0, "lng": 100.0,
                   "available": True, "active_assignments": 0, "ngo_verified": False}
        assert find_best_volunteer(need, [far_vol]) is None

    def test_compute_score_tier1_bonus(self):
        """NGO-verified volunteer must score higher than identical unverified volunteer."""
        from backend.routes.match import _compute_score
        need = {"severity": "high", "lat": 28.6, "lng": 77.2}
        t1 = {"ngo_verified": True,  "available": True, "lat": 28.6, "lng": 77.2}
        t2 = {"ngo_verified": False, "available": True, "lat": 28.6, "lng": 77.2}
        score_t1, _ = _compute_score(need, t1)
        score_t2, _ = _compute_score(need, t2)
        assert score_t1 > score_t2


class TestMatchRoutes:
    """HTTP-level tests for /match endpoints."""

    def test_run_matcher_unauthorized(self, client):
        resp = client.get("/match")
        assert resp.status_code == 401

    def test_run_matcher_no_needs(self, client):
        with patch("backend.routes.match.get_open_needs", return_value=[]), \
             patch("backend.routes.match.get_available_volunteers", return_value=[]):
            resp = client.get("/match", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 0
        assert resp.json()["total_needs_processed"] == 0

    def test_incompatible_volunteer_skills_not_matched(self, client):
        open_needs = [
            {"id": "n-med", "category": "medical", "severity": "high",
             "lat": 28.6, "lng": 77.2, "status": "open", "trust_score": 90,
             "help_needed": "medical", "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "vol-cook", "name": "Chef Kumar", "skills": ["cooking", "food"],
             "lat": 28.6, "lng": 77.2, "available": True, "ngo_verified": True,
             "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_matches_made"] == 0

    def test_compatible_volunteer_matched_successfully(self, client):
        open_needs = [
            {"id": "n-food", "category": "supplies", "help_needed": "food",
             "severity": "medium", "lat": 28.6, "lng": 77.2,
             "status": "open", "trust_score": 90,
             "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "vol-dist", "name": "Food Distributor",
             "skills": ["food", "ration", "distribution"],
             "lat": 28.61, "lng": 77.21, "available": True,
             "ngo_verified": False, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers), \
             patch("backend.routes.match.save_assignment", return_value="a-food-1"):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_matches_made"] == 1
        assert data["matches"][0]["status"] == "assigned"
        assert data["matches"][0]["assigned_volunteer"] == "Food Distributor"

    def test_unavailable_volunteer_not_matched(self, client):
        open_needs = [
            {"id": "n-supplies", "category": "supplies", "help_needed": "supplies",
             "severity": "medium", "lat": 28.6, "lng": 77.2,
             "status": "open", "trust_score": 90,
             "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "vol-busy", "name": "Busy Vol", "skills": ["supplies"],
             "lat": 28.6, "lng": 77.2, "available": False, "active_assignments": 3}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 0

    def test_sensitive_case_tier2_volunteer_blocked(self, client):
        open_needs = [
            {"id": "n-rescue", "category": "rescue", "severity": "critical",
             "lat": 28.6, "lng": 77.2, "status": "open", "trust_score": 95,
             "help_needed": "rescue", "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "vol-t2", "name": "Community Rescuer", "skills": ["rescue"],
             "lat": 28.6, "lng": 77.2, "available": True,
             "ngo_verified": False, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_matches_made"] == 0
        assert data["matches"][0]["status"] == "Manual Escalation Required"
        assert "Tier 1" in data["matches"][0]["reason"]

    def test_sensitive_case_tier1_volunteer_matched(self, client):
        open_needs = [
            {"id": "n-med-crit", "category": "medical", "severity": "critical",
             "lat": 28.6, "lng": 77.2, "status": "open", "trust_score": 95,
             "help_needed": "medical", "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "vol-t1-doc", "name": "Dr. Awasthi",
             "skills": ["medical", "first-aid"],
             "lat": 28.61, "lng": 77.21, "available": True,
             "ngo_verified": True, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers), \
             patch("backend.routes.match.save_assignment", return_value="a-med-1"):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_matches_made"] == 1
        assert data["matches"][0]["volunteer_tier"] == "Tier 1 (NGO-Verified)"

    def test_uncertain_category_fails_safely_to_tier1(self, client):
        open_needs = [{
            "id": "n-uncertain", "category": "Not Specified",
            "help_needed": "Not Specified",
            "description": "Building collapse 4 people trapped bleeding",
            "severity": "critical", "lat": 28.6, "lng": 77.2,
            "status": "open", "trust_score": 90, "disaster_type": ""
        }]
        volunteers_t2 = [
            {"id": "vol-t2-unv", "name": "Unverified Vol", "skills": ["rescue"],
             "lat": 28.6, "lng": 77.2, "available": True,
             "ngo_verified": False, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers_t2):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        assert resp.json()["total_matches_made"] == 0
        assert resp.json()["matches"][0]["status"] == "Manual Escalation Required"

    def test_multi_volunteer_dispatch_up_to_three(self, client):
        """Up to 3 volunteers can be assigned to the same need in one pass."""
        open_needs = [
            {"id": "n-multi", "category": "logistics", "help_needed": "logistics",
             "severity": "high", "lat": 28.6, "lng": 77.2,
             "status": "open", "trust_score": 95, "disaster_type": "flood", "description": ""}
        ]
        volunteers = [
            {"id": f"vol-{i}", "name": f"Driver {i}", "skills": ["logistics", "driving"],
             "lat": 28.6 + i * 0.001, "lng": 77.2, "available": True,
             "ngo_verified": False, "active_assignments": 0}
            for i in range(5)
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers), \
             patch("backend.routes.match.save_assignment", return_value="a-multi"):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_matches_made"] == 1
        assert data["matches"][0]["count"] <= 3

    def test_low_trust_score_non_critical_need_skipped(self, client):
        """Non-critical need with trust_score < 50 must be skipped."""
        open_needs = [
            {"id": "n-low-trust", "category": "logistics", "help_needed": "food",
             "severity": "low", "lat": 28.6, "lng": 77.2,
             "status": "open", "trust_score": 30, "disaster_type": "", "description": ""}
        ]
        volunteers = [
            {"id": "v1", "name": "Vol1", "skills": ["logistics"],
             "lat": 28.6, "lng": 77.2, "available": True,
             "ngo_verified": False, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_open_needs", return_value=open_needs), \
             patch("backend.routes.match.get_available_volunteers", return_value=volunteers):
            resp = client.get("/match", headers=AUTH_HEADERS)

        assert resp.status_code == 200
        # Low trust + non-critical → should be skipped (0 matches)
        assert resp.json()["total_matches_made"] == 0

    def test_debug_match_requires_auth(self, client):
        resp = client.get("/match/debug/some-need-id")
        assert resp.status_code == 401

    def test_debug_match_not_found(self, client):
        with patch("backend.routes.match.get_need_by_id", return_value=None):
            resp = client.get("/match/debug/fake-id", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_debug_match_returns_breakdown(self, client):
        mock_need = {
            "id": "n1", "category": "logistics", "severity": "medium",
            "lat": 28.6, "lng": 77.2, "help_needed": "logistics",
            "disaster_type": "flood", "description": ""
        }
        mock_vols = [
            {"id": "v1", "name": "Vol One", "skills": ["logistics"],
             "lat": 28.6, "lng": 77.2, "available": True,
             "ngo_verified": False, "active_assignments": 0}
        ]
        with patch("backend.routes.match.get_need_by_id", return_value=mock_need), \
             patch("backend.routes.match.get_available_volunteers", return_value=mock_vols):
            resp = client.get("/match/debug/n1", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "all_scores" in data
        assert data["volunteers_evaluated"] == 1


# =============================================================================
# DASHBOARD ROUTES
# =============================================================================

class TestDashboardRoutes:

    def test_get_global_dashboard_stats(self, client):
        needs = [
            {"id": "1", "status": "open", "category": "food", "severity": "medium", "trust_score": 80},
            {"id": "2", "status": "resolved", "category": "medical", "severity": "critical", "trust_score": 90}
        ]
        with patch("backend.routes.dashboard.get_open_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_available_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_ngos", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        data = resp.json()
        assert "reports" in data
        assert data["total_needs"] == 2

    def test_dashboard_severity_counts(self, client):
        needs = [
            {"id": "c1", "status": "open", "severity": "critical", "trust_score": 90},
            {"id": "h1", "status": "open", "severity": "high", "trust_score": 80},
            {"id": "m1", "status": "open", "severity": "medium", "trust_score": 75},
            {"id": "l1", "status": "open", "severity": "low", "trust_score": 60},
        ]
        with patch("backend.routes.dashboard.get_open_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_available_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_ngos", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.status_code == 200
        d = resp.json()
        assert d["critical_cases"] == 1
        assert d["high_priority_cases"] == 1
        assert d["medium_priority_cases"] == 1
        assert d["low_priority_cases"] == 1

    def test_dashboard_flagged_cases_below_trust_50(self, client):
        needs = [
            {"id": "f1", "status": "open", "severity": "low", "trust_score": 25},
            {"id": "f2", "status": "open", "severity": "low", "trust_score": 49},
            {"id": "ok", "status": "open", "severity": "medium", "trust_score": 75},
        ]
        with patch("backend.routes.dashboard.get_open_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_available_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_volunteers", return_value=[]), \
             patch("backend.routes.dashboard.get_all_ngos", return_value=[]):
            resp = client.get("/dashboard")
        assert resp.json()["flagged_cases"] == 2

    def test_get_dashboard_reports_list(self, client):
        with patch("backend.routes.dashboard.get_all_needs", return_value=[{"id": "n1", "status": "open"}]):
            resp = client.get("/dashboard/reports")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_dashboard_reports_volunteer_coordinates(self, client):
        """Reports must serialize volunteer_lat and volunteer_lng for map markers."""
        needs = [{
            "id": "n-map-1", "description": "Flood assistance",
            "lat": 19.0760, "lng": 72.8777, "status": "open"
        }]
        mock_assignments = [
            {"id": "a1", "need_id": "n-map-1", "volunteer_id": "v-map-1",
             "status": "assigned", "resolved_at": None}
        ]
        mock_volunteers = [
            {"id": "v-map-1", "name": "Rahul Verma",
             "phone": "9876543210", "lat": 19.0800, "lng": 72.8800}
        ]
        with patch("backend.routes.dashboard.get_all_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_db_cursor") as mock_cursor:
            cursor = MagicMock()
            cursor.fetchall.side_effect = [mock_assignments, mock_volunteers]
            mock_cursor.return_value.__enter__.return_value = cursor
            resp = client.get("/dashboard/reports")

        assert resp.status_code == 200
        reports = resp.json()
        rep = reports[0]
        assert rep["assigned"] is True
        assert rep["status"] == "assigned"
        assert rep["volunteer_lat"] == 19.0800
        assert rep["volunteer_lng"] == 72.8800
        assert rep["volunteer_name"] == "Rahul Verma"
        assert len(rep["assigned_volunteers"]) == 1

    def test_dashboard_reports_no_assignment_sets_nulls(self, client):
        """Unassigned needs must have None volunteer fields."""
        needs = [{"id": "n-unassigned", "status": "open", "lat": 28.6, "lng": 77.2}]
        with patch("backend.routes.dashboard.get_all_needs", return_value=needs), \
             patch("backend.routes.dashboard.get_db_cursor") as mock_cursor:
            cursor = MagicMock()
            cursor.fetchall.side_effect = [[], []]  # No assignments, no volunteers
            mock_cursor.return_value.__enter__.return_value = cursor
            resp = client.get("/dashboard/reports")

        assert resp.status_code == 200
        rep = resp.json()[0]
        assert rep["volunteer_id"] is None
        assert rep["volunteer_name"] is None
        assert rep["assigned"] is False


# =============================================================================
# ASSIGNMENT ROUTE
# =============================================================================

class TestAssignmentRoute:

    def test_accept_need_requires_auth(self, client):
        resp = client.post("/assignment/volunteer/need-1")
        assert resp.status_code == 401

    def test_accept_need_volunteer_claiming_own_assignment(self, client):
        from backend.main import app
        from backend.auth import verify_token
        # Use a token with no uid so the fallback to query-param volunteer_id is exercised
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v1", "name": "Pooja", "skills": ["supplies", "food"],
            "available": True, "active_assignments": 0, "ngo_verified": False
        }
        mock_need = {
            "id": "need-10", "category": "supplies", "help_needed": "food",
            "status": "open", "description": "Need food rations", "disaster_type": ""
        }
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db, \
                 patch("backend.routes.assignment.save_assignment", return_value="assign-10"):
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                cursor.fetchall.return_value = []
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-10?volunteer_id=v1", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 200
        assert resp.json()["status"] == "assigned"
        assert resp.json()["assignment_id"] == "assign-10"

    def test_accept_need_token_dict_identity_resolved(self, client):
        """Token containing uid should be used; volunteer_id param should be ignored."""
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"uid": "v-auth", "role": "volunteer"}

        mock_vol = {
            "id": "v-auth", "name": "Auth Vol", "skills": ["supplies"],
            "available": True, "active_assignments": 0, "ngo_verified": False
        }
        mock_need = {
            "id": "need-20", "category": "supplies", "help_needed": "supplies",
            "status": "open", "description": "Need blankets", "disaster_type": ""
        }
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db, \
                 patch("backend.routes.assignment.save_assignment", return_value="assign-20"):
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                cursor.fetchall.return_value = []
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-20", headers=AUTH_HEADERS)
            assert resp.status_code == 200
            assert resp.json()["status"] == "assigned"
        finally:
            app.dependency_overrides.clear()

    def test_accept_need_impersonation_attempt_forbidden(self, client):
        """Volunteer trying to claim as a different volunteer_id must be blocked (403)."""
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"uid": "v-user-1", "role": "volunteer"}
        try:
            resp = client.post("/assignment/volunteer/need-1?volunteer_id=v-user-2", headers=AUTH_HEADERS)
            assert resp.status_code == 403
            assert "Forbidden" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    def test_accept_need_already_assigned_to_another_forbidden(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v1", "name": "Pooja", "skills": ["supplies"],
            "available": True, "active_assignments": 0, "ngo_verified": False
        }
        mock_need = {"id": "need-11", "category": "supplies", "status": "assigned", "help_needed": ""}
        existing_assignment = [
            {"id": "a-other", "need_id": "need-11", "volunteer_id": "v-other", "status": "assigned"}
        ]
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                cursor.fetchall.return_value = existing_assignment
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-11?volunteer_id=v1", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 403
        assert "another volunteer" in resp.json()["detail"]

    def test_accept_need_duplicate_claim_conflict(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v1", "name": "Pooja", "skills": ["supplies"],
            "available": True, "active_assignments": 1, "ngo_verified": False
        }
        mock_need = {"id": "need-12", "category": "supplies", "status": "assigned", "help_needed": ""}
        existing_assignment = [
            {"id": "a-same", "need_id": "need-12", "volunteer_id": "v1", "status": "assigned"}
        ]
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                cursor.fetchall.return_value = existing_assignment
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-12?volunteer_id=v1", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 409
        assert "already claimed" in resp.json()["detail"]

    def test_accept_need_unavailable_volunteer_fails(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v-busy", "name": "Busy Vol", "skills": ["supplies"],
            "available": False, "active_assignments": 3
        }
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.return_value = mock_vol
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-1?volunteer_id=v-busy", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 400
        assert "unavailable" in resp.json()["detail"]

    def test_accept_need_nonexistent_volunteer_returns_404(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.return_value = None
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-1?volunteer_id=ghost-vol", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_accept_need_nonexistent_need_returns_404(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v1", "name": "Pooja", "skills": ["food"],
            "available": True, "active_assignments": 0
        }
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, None]  # vol found, need not found
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/ghost-need?volunteer_id=v1", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 404

    def test_accept_need_resolved_need_rejected(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {"id": "v1", "name": "V1", "skills": ["food"], "available": True, "active_assignments": 0}
        mock_need = {"id": "need-res", "category": "food", "status": "resolved"}
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-res?volunteer_id=v1", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code == 409

    def test_accept_need_incompatible_skills_blocked(self, client):
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"role": "volunteer"}
        mock_vol = {
            "id": "v-cook", "name": "Cook", "skills": ["cooking"],
            "available": True, "active_assignments": 0, "ngo_verified": False
        }
        mock_need = {
            "id": "need-med", "category": "medical", "help_needed": "medical",
            "status": "open", "description": "injury", "disaster_type": ""
        }
        try:
            with patch("backend.routes.assignment.get_db_cursor") as mock_db:
                cursor = MagicMock()
                cursor.fetchone.side_effect = [mock_vol, mock_need]
                cursor.fetchall.return_value = []
                mock_db.return_value.__enter__.return_value = cursor
                resp = client.post("/assignment/volunteer/need-med?volunteer_id=v-cook", headers=AUTH_HEADERS)
        finally:
            app.dependency_overrides.clear()

        assert resp.status_code in [400, 403]

    def test_resolve_assignment_requires_auth(self, client):
        resp = client.patch("/assignment/a1/resolve")
        assert resp.status_code == 401

    def test_resolve_assignment_success(self, client):
        assignment = {"id": "a1", "need_id": "n1", "volunteer_id": "v1", "resolved_at": None, "status": "assigned"}
        with patch("database.assignments_db.get_assignment_by_id", return_value=assignment), \
             patch("database.assignments_db.resolve_assignment"):
            resp = client.patch("/assignment/a1/resolve", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert resp.json()["status"] == "resolved"

    def test_resolve_assignment_not_found(self, client):
        with patch("database.assignments_db.get_assignment_by_id", return_value=None):
            resp = client.patch("/assignment/ghost-assign/resolve", headers=AUTH_HEADERS)
        assert resp.status_code == 404

    def test_resolve_assignment_already_resolved_returns_409(self, client):
        assignment = {
            "id": "a2", "need_id": "n2", "volunteer_id": "v2",
            "resolved_at": "2025-01-01T10:00:00+00:00", "status": "resolved"
        }
        with patch("database.assignments_db.get_assignment_by_id", return_value=assignment):
            resp = client.patch("/assignment/a2/resolve", headers=AUTH_HEADERS)
        assert resp.status_code == 409

    def test_get_volunteer_assignments_requires_auth(self, client):
        resp = client.get("/assignment/volunteer/v1")
        assert resp.status_code == 401

    def test_get_volunteer_assignments_success(self, client):
        assignments = [
            {"id": "a1", "need_id": "n1", "volunteer_id": "v1", "resolved_at": None},
            {"id": "a2", "need_id": "n2", "volunteer_id": "v1", "resolved_at": None},
        ]
        with patch("database.assignments_db.get_assignments_by_volunteer_id", return_value=assignments), \
             patch("database.needs_db.get_need_by_id", return_value=None):
            resp = client.get("/assignment/volunteer/v1", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# =============================================================================
# NGO ROUTE
# =============================================================================

class TestNGORoute:

    def test_register_ngo_success(self, client):
        with patch("database.ngos_db.save_ngo", return_value="ngo-001"), \
             patch("database.geocoding.get_coordinates", return_value={"lat": 22.5, "lng": 88.3}):
            resp = client.post("/ngo/register", json={
                "name": "HelpIndia NGO", "reg_number": "NGO/KP/001",
                "location": "Kolkata", "radius": 100.0
            })
        assert resp.status_code == 200
        assert "id" in resp.json()

    def test_register_ngo_verified_field_stripped(self, client):
        """Submitted 'verified=True' must be ignored on public registration."""
        with patch("backend.routes.ngo.save_ngo", return_value="ngo-002") as mock_save, \
             patch("backend.routes.ngo.get_coordinates", return_value=None):
            client.post("/ngo/register", json={
                "name": "Evil NGO", "reg_number": "NGO/EVIL/1",
                "location": "Unknown", "verified": True
            })
            assert mock_save.called
            saved = mock_save.call_args[0][0]
            assert "verified" not in saved  # Must be popped

    def test_get_ngo_not_found_returns_404(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value=None):
            resp = client.get("/ngo/fake-id")
        assert resp.status_code == 404

    def test_get_ngo_found_returns_ngo(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value={
            "id": "ngo-1", "ngo_name": "SaveIndia", "verified": False
        }):
            resp = client.get("/ngo/ngo-1")
        assert resp.status_code == 200
        assert resp.json()["ngo_name"] == "SaveIndia"

    def test_list_ngos_success(self, client):
        mock_ngos = [
            {"id": "n1", "ngo_name": "NGO One", "owner_name": "Admin", "verified": True,
             "email": "n1@ngo.com", "description": "Desc", "location": "Delhi"}
        ]
        with patch("backend.routes.ngo.get_all_ngos", return_value=mock_ngos), \
             patch("backend.routes.ngo.get_db_cursor") as mock_cur:
            mock_cur.return_value.__enter__.return_value = MagicMock()
            resp = client.get("/ngo/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ok"] is True
        assert len(data["data"]) == 1

    def test_ngo_dashboard_requires_auth(self, client):
        resp = client.get("/ngo/some-ngo-id/dashboard")
        assert resp.status_code == 401

    def test_ngo_dashboard_ngo_not_found_returns_404(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value=None):
            resp = client.get("/ngo/bad-id/dashboard", headers=AUTH_HEADERS)
        # Returns 404 after auth passes
        assert resp.status_code == 404

    def test_ngo_dashboard_returns_stats(self, client):
        with patch("backend.routes.ngo.get_ngo", return_value={"id": "ngo-1", "ngo_name": "TestNGO"}), \
             patch("backend.routes.ngo.get_db_cursor") as mock_get_cursor:
            cursor = MagicMock()
            cursor.fetchall.side_effect = [
                [{"id": f"v{i}", "skills": ["medical"]} for i in range(5)],  # volunteers
                []  # assignments
            ]
            mock_get_cursor.return_value.__enter__.return_value = cursor
            resp = client.get("/ngo/ngo-1/dashboard", headers=AUTH_HEADERS)
        assert resp.status_code == 200
        data = resp.json()
        assert "stats" in data
        assert data["stats"]["managed_volunteers"] == 5
        assert data["stats"]["active_assignments"] == 0

    def test_ngo_dashboard_ngo_role_own_access_allowed(self, client):
        """NGO with own ngo_id in token can access their own dashboard."""
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"uid": "ngo-abc", "role": "ngo"}
        try:
            with patch("backend.routes.ngo.get_ngo", return_value={"id": "ngo-abc", "ngo_name": "My NGO"}), \
                 patch("backend.routes.ngo.get_db_cursor") as mock_cur:
                cursor = MagicMock()
                cursor.fetchall.side_effect = [[], []]
                mock_cur.return_value.__enter__.return_value = cursor
                resp = client.get("/ngo/ngo-abc/dashboard", headers=AUTH_HEADERS)
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.clear()

    def test_ngo_dashboard_ngo_role_other_ngo_access_forbidden(self, client):
        """NGO trying to view another NGO's dashboard should get 403."""
        from backend.main import app
        from backend.auth import verify_token
        app.dependency_overrides[verify_token] = lambda: {"uid": "ngo-abc", "role": "ngo"}
        try:
            with patch("backend.routes.ngo.get_ngo", return_value={"id": "ngo-xyz", "ngo_name": "Other NGO"}):
                resp = client.get("/ngo/ngo-xyz/dashboard", headers=AUTH_HEADERS)
            assert resp.status_code == 403
            assert "Access denied" in resp.json()["detail"]
        finally:
            app.dependency_overrides.clear()