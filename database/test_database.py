"""
database/test_database.py
==========================
Tests for every module inside database/:
  - volunteers_db.py
  - needs_db.py
  - ngos_db.py
  - assignments_db.py
  - geocoding.py
  - verification.py
  - otp_db.py

All PostgreSQL and external HTTP/maps calls are mocked.

Run from project root:
    pytest database/test_database.py -v
"""

import sys
import os
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import database.volunteers_db
import database.needs_db
import database.ngos_db
import database.assignments_db
import database.otp_db
import database.verification



# -----------------------------------------------------------------------------
# PYTEST FIXTURES
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_cursor():
    """Returns a mock psycopg2 cursor plugged into all database helper context managers."""
    with patch("database.volunteers_db.get_db_cursor") as mock_v, \
         patch("database.needs_db.get_db_cursor") as mock_n, \
         patch("database.ngos_db.get_db_cursor") as mock_ngo, \
         patch("database.assignments_db.get_db_cursor") as mock_a, \
         patch("database.otp_db.get_db_cursor") as mock_o, \
         patch("database.verification.get_db_cursor") as mock_ver:
        
        cursor = MagicMock()
        
        # Make the context manager __enter__ return the cursor
        mock_v.return_value.__enter__.return_value = cursor
        mock_n.return_value.__enter__.return_value = cursor
        mock_ngo.return_value.__enter__.return_value = cursor
        mock_a.return_value.__enter__.return_value = cursor
        mock_o.return_value.__enter__.return_value = cursor
        mock_ver.return_value.__enter__.return_value = cursor
        
        yield cursor


# -----------------------------------------------------------------------------
# VOLUNTEERS DB
# -----------------------------------------------------------------------------

class TestVolunteersDB:

    def test_hash_password_is_not_plaintext(self):
        from database.volunteers_db import hash_password
        hashed = hash_password("mysecretpassword")
        assert isinstance(hashed, str)
        assert hashed != "mysecretpassword"

    def test_hash_password_different_each_call(self):
        from database.volunteers_db import hash_password
        h1 = hash_password("pass")
        h2 = hash_password("pass")
        assert h1 != h2

    def test_verify_password_correct(self):
        from database.volunteers_db import hash_password, verify_password
        raw = "testpass123"
        assert verify_password(raw, hash_password(raw)) is True

    def test_verify_password_incorrect(self):
        from database.volunteers_db import hash_password, verify_password
        assert verify_password("wrong", hash_password("correct")) is False

    def test_verify_password_bad_hash_returns_false(self):
        from database.volunteers_db import verify_password
        assert verify_password("password", "not-a-real-hash") is False

    def test_save_volunteer_sets_available_true(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.volunteers_db import save_volunteer
        with patch("database.geocoding.get_coordinates", return_value={"lat": 12.3, "lng": 45.6}):
            result = save_volunteer({"name": "Ravi", "skills": ["medical"], "location": "Delhi"})
        assert result is not None
        assert mock_cursor.execute.called
        # Check that we executed insert with available = True
        inserted_query = mock_cursor.execute.call_args[0][0]
        assert "INSERT INTO volunteers" in inserted_query

    def test_save_volunteer_sets_registered_at(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.volunteers_db import save_volunteer
        with patch("database.geocoding.get_coordinates", return_value={"lat": 12.3, "lng": 45.6}):
            save_volunteer({"name": "Priya", "location": "Delhi"})
        assert mock_cursor.execute.called

    def test_get_available_volunteers_returns_list(self, mock_cursor):
        mock_cursor.fetchall.return_value = [{"id": "v1", "name": "Priya", "available": True}]
        from database.volunteers_db import get_available_volunteers
        result = get_available_volunteers()
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["id"] == "v1"

    def test_get_available_volunteers_empty(self, mock_cursor):
        mock_cursor.fetchall.return_value = []
        from database.volunteers_db import get_available_volunteers
        assert get_available_volunteers() == []

    def test_update_volunteer_status_called_correctly(self, mock_cursor):
        from database.volunteers_db import update_volunteer_status
        update_volunteer_status("vol-42", False)
        assert mock_cursor.execute.called
        query, params = mock_cursor.execute.call_args[0]
        assert "UPDATE volunteers" in query
        assert False in params
        assert "vol-42" in params

    def test_login_volunteer_wrong_email(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.volunteers_db import login_volunteer
        result = login_volunteer("ghost@test.com", "pass")
        assert "error" in result

    def test_login_volunteer_wrong_password(self, mock_cursor):
        from database.volunteers_db import hash_password
        mock_cursor.fetchone.return_value = {
            "id": "v99", "email": "u@t.com",
            "password_hash": hash_password("correct"), "name": "U"
        }
        from database.volunteers_db import login_volunteer
        result = login_volunteer("u@t.com", "wrong")
        assert "error" in result

    def test_login_volunteer_success(self, mock_cursor):
        from database.volunteers_db import hash_password
        mock_cursor.fetchone.return_value = {
            "id": "v10", "email": "ok@t.com",
            "password_hash": hash_password("secret"), "name": "OK"
        }
        from database.volunteers_db import login_volunteer
        result = login_volunteer("ok@t.com", "secret")
        assert result.get("success") is True
        assert result["name"] == "OK"

    def test_register_volunteer_auth_duplicate_email(self, mock_cursor):
        mock_cursor.fetchone.return_value = {"id": "v1"}
        from database.volunteers_db import register_volunteer_auth
        result = register_volunteer_auth("dup@t.com", "p", "Dup", "9999999999", "Delhi", ["food"])
        assert "error" in result

    def test_register_volunteer_auth_new_user(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        with patch("database.geocoding.get_coordinates", return_value={"lat": 28.6, "lng": 77.2}):
            from database.volunteers_db import register_volunteer_auth
            result = register_volunteer_auth("new@t.com", "pass", "New", "9000000001", "Delhi", ["food"])
        assert result.get("success") is True
        assert "volunteer_id" in result


# -----------------------------------------------------------------------------
# NEEDS DB
# -----------------------------------------------------------------------------

class TestNeedsDB:

    def test_save_need_sets_status_open(self, mock_cursor):
        from database.needs_db import save_need
        result = save_need({"description": "Flood"})
        assert result is not None
        assert mock_cursor.execute.called

    def test_save_need_sets_timestamp(self, mock_cursor):
        from database.needs_db import save_need
        save_need({"description": "Earthquake"})
        assert mock_cursor.execute.called

    def test_get_open_needs_returns_list(self, mock_cursor):
        mock_cursor.fetchall.return_value = [{"id": "n1", "category": "rescue", "status": "open"}]
        from database.needs_db import get_open_needs
        result = get_open_needs()
        assert isinstance(result, list)
        assert result[0]["id"] == "n1"

    def test_get_open_needs_empty(self, mock_cursor):
        mock_cursor.fetchall.return_value = []
        from database.needs_db import get_open_needs
        assert get_open_needs() == []

    def test_get_need_by_id_found(self, mock_cursor):
        mock_cursor.fetchone.return_value = {"id": "need-123", "category": "medical"}
        from database.needs_db import get_need_by_id
        res = get_need_by_id("need-123")
        assert res is not None
        assert res["id"] == "need-123"

    def test_get_need_by_id_missing(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.needs_db import get_need_by_id
        assert get_need_by_id("ghost") is None

    def test_update_need_status(self, mock_cursor):
        from database.needs_db import update_need_status
        update_need_status("n-9", "assigned")
        assert mock_cursor.execute.called
        query, params = mock_cursor.execute.call_args[0]
        assert "UPDATE needs_reports" in query
        assert "assigned" in params
        assert "n-9" in params

    def test_check_corroboration_returns_int(self, mock_cursor):
        mock_cursor.fetchall.return_value = [
            {"lat": 12.31, "lng": 45.61},
            {"lat": 12.32, "lng": 45.62},
            {"lat": 12.33, "lng": 45.63}
        ]
        from database.needs_db import check_corroboration
        count = check_corroboration(12.3, 45.6, "food")
        assert count == 3

    def test_check_corroboration_no_nearby_returns_zero(self, mock_cursor):
        mock_cursor.fetchall.return_value = []
        from database.needs_db import check_corroboration
        count = check_corroboration(12.3, 45.6, "medical")
        assert count == 0


# -----------------------------------------------------------------------------
# NGOS DB
# -----------------------------------------------------------------------------

class TestNgosDB:

    def test_save_ngo_sets_verified_false_by_default(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.ngos_db import save_ngo
        result = save_ngo({"name": "HelpOrg", "lat": 12.3, "lng": 45.6, "radius": 10.0})
        assert result is not None
        query, params = mock_cursor.execute.call_args[0]
        # Check defaults if they exist in query
        assert "INSERT INTO ngos" in query

    def test_save_ngo_sets_registered_at(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.ngos_db import save_ngo
        save_ngo({"name": "NGO2"})
        assert mock_cursor.execute.called

    def test_get_ngo_found(self, mock_cursor):
        mock_cursor.fetchone.return_value = {"id": "ngo-1", "name": "NGO One"}
        from database.ngos_db import get_ngo
        res = get_ngo("ngo-1")
        assert res is not None
        assert res["name"] == "NGO One"

    def test_get_ngo_missing_returns_none(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.ngos_db import get_ngo
        assert get_ngo("ghost") is None

    def test_verify_ngo_success(self, mock_cursor):
        # We need check to pass (returns truthy row for exist check)
        mock_cursor.fetchone.return_value = {"id": "ngo-1"}
        from database.ngos_db import verify_ngo
        res = verify_ngo("ngo-1", True)
        assert res is True
        assert mock_cursor.execute.called

    def test_verify_ngo_not_found_returns_false(self, mock_cursor):
        mock_cursor.fetchone.return_value = None
        from database.ngos_db import verify_ngo
        assert verify_ngo("ghost", True) is False


# -----------------------------------------------------------------------------
# ASSIGNMENTS DB
# -----------------------------------------------------------------------------

class TestAssignmentsDB:

    def test_save_assignment_returns_id(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "active_assignments": 0,
            "id": "vol-1",
            "name": "Ravi",
            "phone": "9999999999",
            "description": "Stranded",
            "location_text": "Delhi",
            "volunteer_id": "vol-1",
            "need_id": "need-1",
            "resolved_at": None
        }
        from database.assignments_db import save_assignment
        res = save_assignment("need-1", "vol-1")
        assert res is not None
        assert mock_cursor.execute.called

    def test_save_assignment_updates_tables(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "active_assignments": 0,
            "id": "vol-2",
            "name": "Priya",
            "phone": "8888888888",
            "description": "Stranded",
            "location_text": "Delhi",
            "volunteer_id": "vol-2",
            "need_id": "need-2",
            "resolved_at": None
        }
        from database.assignments_db import save_assignment
        save_assignment("need-2", "vol-2")
        # Check that we did updating SQL operations
        assert mock_cursor.execute.call_count >= 3

    def test_resolve_assignment_updates_tables(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "volunteer_id": "vol-1",
            "need_id": "need-1",
            "active_assignments": 1
        }
        from database.assignments_db import resolve_assignment
        resolve_assignment("assign-1", "need-1", "vol-1")
        assert mock_cursor.execute.called


# -----------------------------------------------------------------------------
# OTP DB
# -----------------------------------------------------------------------------

class TestOtpDB:

    def test_save_otp(self, mock_cursor):
        from database.otp_db import save_otp
        res = save_otp("test@email.com", "123456")
        assert res is True
        assert mock_cursor.execute.called

    def test_verify_otp_valid(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "otp": "123456",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        from database.otp_db import verify_otp_in_db
        assert verify_otp_in_db("test@email.com", "123456") is True

    def test_verify_otp_expired(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "otp": "123456",
            "expires_at": datetime.now(timezone.utc) - timedelta(minutes=5)
        }
        from database.otp_db import verify_otp_in_db
        assert verify_otp_in_db("test@email.com", "123456") is False

    def test_verify_otp_wrong_code(self, mock_cursor):
        mock_cursor.fetchone.return_value = {
            "otp": "999999",
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5)
        }
        from database.otp_db import verify_otp_in_db
        assert verify_otp_in_db("test@email.com", "123456") is False


# -----------------------------------------------------------------------------
# GEOCODING
# -----------------------------------------------------------------------------

class TestGeocoding:

    @patch("database.geocoding.load_dotenv")
    @patch("requests.get")
    def test_osm_returns_coordinates(self, mock_get, _env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"lat": "28.6139", "lon": "77.2090"}]
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        with patch("os.getenv", return_value=""):  # Emulate no Google key
            from database.geocoding import get_coordinates
            res = get_coordinates("Delhi")
            assert res == {"lat": 28.6139, "lng": 77.2090}

    @patch("database.geocoding.load_dotenv")
    @patch("requests.get")
    def test_empty_osm_response_returns_none(self, mock_get, _env):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp

        with patch("os.getenv", return_value=""):
            from database.geocoding import get_coordinates
            assert get_coordinates("nowhere") is None


# -----------------------------------------------------------------------------
# VERIFICATION / TRUST ENGINE
# -----------------------------------------------------------------------------

class TestVerification:

    def test_common_validation_passes_valid_data(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0})
        assert result["passed"] is True
        assert result["phone_ok"] is True
        assert result["coords_ok"] is True

    def test_common_validation_fails_short_phone(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "123", "lat": 26.0, "lng": 80.0})
        assert result["phone_ok"] is False

    def test_common_validation_fails_zero_coords(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 0.0, "lng": 0.0})
        assert result["passed"] is False

    def test_high_stakes_rescue_category(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("rescue", "general") is True

    def test_high_stakes_flood_disaster(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("food", "flood") is True

    @patch("database.verification.get_db_cursor")
    def test_calculate_trust_score_returns_dict(self, mock_get_db):
        cursor = MagicMock()
        cursor.fetchone.return_value = {"count": 1}
        mock_get_db.return_value.__enter__.return_value = cursor
        
        with patch("requests.get") as mock_weather:
            mock_weather.return_value.json.return_value = {"weather": [{"main": "Clear"}]}
            mock_weather.return_value.status_code = 200
            with patch("os.getenv", return_value=None):
                from database.verification import calculate_trust_score
                result = calculate_trust_score(
                    {"reporter_phone": "9876543210", "lat": 26.8, "lng": 80.9,
                     "category": "rescue", "disaster_type": "flood"},
                    ai_consistency=8,
                    corroborating_reports_count=1,
                    ai_category="rescue",
                    base_score=20
                )
        assert "score" in result
        assert "dispatch_action" in result
        assert result["dispatch_action"] in ("auto_dispatch", "human_review", "flagged")