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

All Firestore, Google Maps, and external HTTP calls are mocked.

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


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def _make_doc(doc_id: str, data: dict, exists: bool = True):
    doc = MagicMock()
    doc.id = doc_id
    doc.exists = exists
    doc.to_dict.return_value = dict(data)
    return doc

def _make_db_with_add(new_id: str = "generated-id"):
    fake_db = MagicMock()
    doc_ref = MagicMock()
    doc_ref.id = new_id
    fake_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
    return fake_db


# ─────────────────────────────────────────────────────────────
# VOLUNTEERS DB
# ─────────────────────────────────────────────────────────────

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
        assert h1 != h2  # bcrypt salts are random

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

    @patch("database.volunteers_db.db")
    def test_save_volunteer_sets_available_true(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "vol-1"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.volunteers_db import save_volunteer
        result = save_volunteer({"name": "Ravi", "skills": ["medical"]})
        assert result == "vol-1"
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert saved["available"] is True

    @patch("database.volunteers_db.db")
    def test_save_volunteer_sets_registered_at(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "vol-2"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.volunteers_db import save_volunteer
        save_volunteer({"name": "Priya"})
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert "registered_at" in saved

    @patch("database.volunteers_db.db")
    def test_get_available_volunteers_returns_list(self, mock_db):
        doc = _make_doc("v1", {"name": "Priya", "available": True})
        mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
        from database.volunteers_db import get_available_volunteers
        result = get_available_volunteers()
        assert isinstance(result, list)
        assert result[0]["id"] == "v1"
        assert result[0]["name"] == "Priya"

    @patch("database.volunteers_db.db")
    def test_get_available_volunteers_empty(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        from database.volunteers_db import get_available_volunteers
        assert get_available_volunteers() == []

    @patch("database.volunteers_db.db")
    def test_update_volunteer_status_called_correctly(self, mock_db):
        from database.volunteers_db import update_volunteer_status
        update_volunteer_status("vol-42", False)
        mock_db.collection.return_value.document.assert_called_with("vol-42")
        update_dict = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert update_dict["available"] is False

    @patch("database.volunteers_db.db")
    def test_login_volunteer_wrong_email(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        from database.volunteers_db import login_volunteer
        result = login_volunteer("ghost@test.com", "pass")
        assert "error" in result

    @patch("database.volunteers_db.db")
    def test_login_volunteer_wrong_password(self, mock_db):
        from database.volunteers_db import hash_password
        doc = _make_doc("v99", {"email": "u@t.com", "password_hash": hash_password("correct"), "name": "U"})
        mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
        from database.volunteers_db import login_volunteer
        result = login_volunteer("u@t.com", "wrong")
        assert "error" in result

    @patch("database.volunteers_db.db")
    def test_login_volunteer_success(self, mock_db):
        from database.volunteers_db import hash_password
        doc = _make_doc("v10", {"email": "ok@t.com", "password_hash": hash_password("secret"), "name": "OK"})
        mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
        from database.volunteers_db import login_volunteer
        result = login_volunteer("ok@t.com", "secret")
        assert result.get("success") is True
        assert result["name"] == "OK"

    @patch("database.volunteers_db.db")
    def test_register_volunteer_auth_duplicate_email(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = [MagicMock()]
        from database.volunteers_db import register_volunteer_auth
        result = register_volunteer_auth("dup@t.com", "p", "Dup", "9999999999", "Delhi", ["food"])
        assert "error" in result
        assert "already" in result["error"].lower()

    @patch("database.volunteers_db.db")
    def test_register_volunteer_auth_new_user(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        doc_ref = MagicMock(); doc_ref.id = "new-vol"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        with patch("database.geocoding.get_coordinates", return_value={"lat": 28.6, "lng": 77.2}):
            from database.volunteers_db import register_volunteer_auth
            result = register_volunteer_auth("new@t.com", "pass", "New", "9000000001", "Delhi", ["food"])
        assert result.get("success") is True
        assert result["volunteer_id"] == "new-vol"


# ─────────────────────────────────────────────────────────────
# NEEDS DB
# ─────────────────────────────────────────────────────────────

class TestNeedsDB:

    @patch("database.needs_db.db")
    def test_save_need_sets_status_open(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "need-1"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.needs_db import save_need
        result = save_need({"description": "Flood"})
        assert result == "need-1"
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert saved["status"] == "open"

    @patch("database.needs_db.db")
    def test_save_need_sets_timestamp(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "need-2"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.needs_db import save_need
        save_need({"description": "Earthquake"})
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert "timestamp" in saved

    @patch("database.needs_db.db")
    def test_get_open_needs_returns_list(self, mock_db):
        doc = _make_doc("n1", {"category": "rescue", "status": "open"})
        mock_db.collection.return_value.where.return_value.stream.return_value = [doc]
        from database.needs_db import get_open_needs
        result = get_open_needs()
        assert isinstance(result, list)
        assert result[0]["id"] == "n1"
        assert result[0]["category"] == "rescue"

    @patch("database.needs_db.db")
    def test_get_open_needs_empty(self, mock_db):
        mock_db.collection.return_value.where.return_value.stream.return_value = []
        from database.needs_db import get_open_needs
        assert get_open_needs() == []

    @patch("database.needs_db.db")
    def test_get_need_by_id_found(self, mock_db):
        doc = _make_doc("n2", {"description": "Flood evacuation needed"})
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.needs_db import get_need_by_id
        result = get_need_by_id("n2")
        assert result["id"] == "n2"
        assert result["description"] == "Flood evacuation needed"

    @patch("database.needs_db.db")
    def test_get_need_by_id_missing(self, mock_db):
        doc = _make_doc("nx", {}, exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.needs_db import get_need_by_id
        assert get_need_by_id("nx") is None

    @patch("database.needs_db.db")
    def test_update_need_status(self, mock_db):
        from database.needs_db import update_need_status
        update_need_status("n5", "resolved")
        update_dict = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert update_dict["status"] == "resolved"

    @patch("database.needs_db.db")
    def test_check_corroboration_returns_int(self, mock_db):
        doc = _make_doc("n3", {
            "category": "flood",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lat": 26.5, "lng": 80.3
        })
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [doc]
        from database.needs_db import check_corroboration
        result = check_corroboration(26.5, 80.3, "flood")
        assert isinstance(result, int)

    @patch("database.needs_db.db")
    def test_check_corroboration_no_nearby_returns_zero(self, mock_db):
        doc = _make_doc("n4", {
            "category": "flood",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "lat": 10.0, "lng": 10.0   # far from query coords
        })
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = [doc]
        from database.needs_db import check_corroboration
        result = check_corroboration(26.5, 80.3, "flood")
        assert result == 0

    @patch("database.needs_db.db")
    def test_check_corroboration_handles_exception(self, mock_db):
        mock_db.collection.return_value.where.side_effect = Exception("Firestore error")
        from database.needs_db import check_corroboration
        result = check_corroboration(26.5, 80.3, "flood")
        assert result == 0


# ─────────────────────────────────────────────────────────────
# NGOs DB
# ─────────────────────────────────────────────────────────────

class TestNGOsDB:

    @patch("database.ngos_db.db")
    def test_save_ngo_sets_verified_false_by_default(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "ngo-1"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.ngos_db import save_ngo
        result = save_ngo({"name": "HelpOrg", "reg_number": "REG001"})
        assert result == "ngo-1"
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert saved["verified"] is False

    @patch("database.ngos_db.db")
    def test_save_ngo_does_not_override_explicit_verified(self, mock_db):
        """verified=False default should not overwrite data that already has it."""
        doc_ref = MagicMock(); doc_ref.id = "ngo-2"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.ngos_db import save_ngo
        save_ngo({"name": "TrustedOrg", "reg_number": "REG002", "verified": False})
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert saved["verified"] is False

    @patch("database.ngos_db.db")
    def test_save_ngo_sets_registered_at(self, mock_db):
        doc_ref = MagicMock(); doc_ref.id = "ngo-3"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.ngos_db import save_ngo
        save_ngo({"name": "NewOrg"})
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert "registered_at" in saved

    @patch("database.ngos_db.db")
    def test_get_ngo_found(self, mock_db):
        doc = _make_doc("ngo-4", {"name": "SaveIndia", "verified": True})
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.ngos_db import get_ngo
        result = get_ngo("ngo-4")
        assert result["id"] == "ngo-4"
        assert result["name"] == "SaveIndia"

    @patch("database.ngos_db.db")
    def test_get_ngo_missing_returns_none(self, mock_db):
        doc = _make_doc("nx", {}, exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.ngos_db import get_ngo
        assert get_ngo("no-such-ngo") is None

    @patch("database.ngos_db.db")
    def test_verify_ngo_success(self, mock_db):
        doc = _make_doc("ngo-5", {})
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.ngos_db import verify_ngo
        assert verify_ngo("ngo-5", verified=True) is True
        update_dict = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert update_dict["verified"] is True

    @patch("database.ngos_db.db")
    def test_verify_ngo_not_found_returns_false(self, mock_db):
        doc = _make_doc("nx", {}, exists=False)
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.ngos_db import verify_ngo
        assert verify_ngo("ghost-ngo") is False

    @patch("database.ngos_db.db")
    def test_verify_ngo_sets_verified_at_timestamp(self, mock_db):
        doc = _make_doc("ngo-6", {})
        mock_db.collection.return_value.document.return_value.get.return_value = doc
        from database.ngos_db import verify_ngo
        verify_ngo("ngo-6")
        update_dict = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert "verified_at" in update_dict


# ─────────────────────────────────────────────────────────────
# ASSIGNMENTS DB
# ─────────────────────────────────────────────────────────────

class TestAssignmentsDB:

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_save_assignment_returns_id(self, mock_db, mock_upd_need, mock_upd_vol):
        doc_ref = MagicMock(); doc_ref.id = "assign-1"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.assignments_db import save_assignment
        result = save_assignment("need-1", "vol-1")
        assert result == "assign-1"

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_save_assignment_marks_need_assigned(self, mock_db, mock_upd_need, mock_upd_vol):
        doc_ref = MagicMock(); doc_ref.id = "a2"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.assignments_db import save_assignment
        save_assignment("need-2", "vol-2")
        mock_upd_need.assert_called_with("need-2", "assigned")

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_save_assignment_sets_volunteer_unavailable(self, mock_db, mock_upd_need, mock_upd_vol):
        doc_ref = MagicMock(); doc_ref.id = "a3"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.assignments_db import save_assignment
        save_assignment("need-3", "vol-3")
        mock_upd_vol.assert_called_with("vol-3", False)

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_save_assignment_stores_resolved_at_none(self, mock_db, mock_upd_need, mock_upd_vol):
        doc_ref = MagicMock(); doc_ref.id = "a4"
        mock_db.collection.return_value.add.return_value = (MagicMock(), doc_ref)
        from database.assignments_db import save_assignment
        save_assignment("need-4", "vol-4")
        saved = mock_db.collection.return_value.add.call_args[0][0]
        assert saved["resolved_at"] is None

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_resolve_assignment_marks_need_resolved(self, mock_db, mock_upd_need, mock_upd_vol):
        from database.assignments_db import resolve_assignment
        resolve_assignment("assign-9", "need-9", "vol-9")
        mock_upd_need.assert_called_with("need-9", "resolved")

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_resolve_assignment_frees_volunteer(self, mock_db, mock_upd_need, mock_upd_vol):
        from database.assignments_db import resolve_assignment
        resolve_assignment("assign-9", "need-9", "vol-9")
        mock_upd_vol.assert_called_with("vol-9", True)

    @patch("database.assignments_db.update_volunteer_status")
    @patch("database.assignments_db.update_need_status")
    @patch("database.assignments_db.db")
    def test_resolve_assignment_sets_resolved_at(self, mock_db, mock_upd_need, mock_upd_vol):
        from database.assignments_db import resolve_assignment
        resolve_assignment("assign-10", "need-10", "vol-10")
        update_dict = mock_db.collection.return_value.document.return_value.update.call_args[0][0]
        assert "resolved_at" in update_dict


# ─────────────────────────────────────────────────────────────
# GEOCODING
# ─────────────────────────────────────────────────────────────

class TestGeocoding:

    @patch("database.geocoding.requests.get")
    @patch("database.geocoding.os.getenv", return_value=None)
    def test_osm_returns_coordinates(self, _env, mock_get):
        mock_get.return_value.json.return_value = [{"lat": "26.8467", "lon": "80.9462"}]
        from database.geocoding import get_coordinates
        result = get_coordinates("Lucknow, India")
        assert result is not None
        assert abs(result["lat"] - 26.8467) < 0.01
        assert abs(result["lng"] - 80.9462) < 0.01

    @patch("database.geocoding.requests.get")
    @patch("database.geocoding.os.getenv", return_value=None)
    def test_empty_osm_response_returns_none(self, _env, mock_get):
        mock_get.return_value.json.return_value = []
        from database.geocoding import get_coordinates
        result = get_coordinates("asdfghjklqwertyuiop")
        assert result is None

    @patch("database.geocoding.requests.get")
    @patch("database.geocoding.os.getenv", return_value=None)
    def test_network_error_returns_none(self, _env, mock_get):
        mock_get.side_effect = Exception("Network failure")
        from database.geocoding import get_coordinates
        result = get_coordinates("Kanpur")
        assert result is None

    @patch("database.geocoding.requests.get")
    @patch("database.geocoding.os.getenv", return_value=None)
    def test_returns_float_coords(self, _env, mock_get):
        mock_get.return_value.json.return_value = [{"lat": "28.6139", "lon": "77.2090"}]
        from database.geocoding import get_coordinates
        result = get_coordinates("New Delhi")
        assert isinstance(result["lat"], float)
        assert isinstance(result["lng"], float)

    @patch("database.geocoding.googlemaps.Client")
    @patch("database.geocoding.os.getenv", return_value="fake-api-key")
    def test_google_maps_used_when_key_present(self, _env, mock_gmaps_cls):
        mock_client = MagicMock()
        mock_gmaps_cls.return_value = mock_client
        mock_client.geocode.return_value = [
            {"geometry": {"location": {"lat": 19.076, "lng": 72.877}}}
        ]
        from database.geocoding import get_coordinates
        result = get_coordinates("Mumbai")
        assert result is not None
        assert abs(result["lat"] - 19.076) < 0.01

    @patch("database.geocoding.googlemaps.Client")
    @patch("database.geocoding.requests.get")
    @patch("database.geocoding.os.getenv", return_value="fake-key")
    def test_google_failure_falls_back_to_osm(self, _env, mock_get, mock_gmaps_cls):
        mock_gmaps_cls.return_value.geocode.side_effect = Exception("Maps quota")
        mock_get.return_value.json.return_value = [{"lat": "13.082", "lon": "80.270"}]
        from database.geocoding import get_coordinates
        result = get_coordinates("Chennai")
        assert result is not None


# ─────────────────────────────────────────────────────────────
# VERIFICATION
# ─────────────────────────────────────────────────────────────

class TestVerification:

    # — run_common_validation —

    def test_common_validation_passes_valid_data(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 26.84, "lng": 80.94})
        assert result["passed"] is True
        assert result["phone_ok"] is True
        assert result["coords_ok"] is True

    def test_common_validation_fails_short_phone(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "123", "lat": 26.0, "lng": 80.0})
        assert result["phone_ok"] is False
        assert result["passed"] is False

    def test_common_validation_fails_non_digit_phone(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "abcdefghij", "lat": 26.0, "lng": 80.0})
        assert result["phone_ok"] is False

    def test_common_validation_fails_zero_coords(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 0.0, "lng": 0.0})
        assert result["coords_ok"] is False
        assert result["passed"] is False

    def test_common_validation_fails_out_of_range_coords(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 999.0, "lng": 80.0})
        assert result["coords_ok"] is False

    def test_common_validation_missing_phone_fails(self):
        from database.verification import run_common_validation
        result = run_common_validation({"lat": 26.0, "lng": 80.0})
        assert result["phone_ok"] is False

    def test_common_validation_base_score_max_20(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0})
        assert result["base_score"] <= 20

    def test_common_validation_returns_reasons_list(self):
        from database.verification import run_common_validation
        result = run_common_validation({"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0})
        assert isinstance(result["reasons"], list)
        assert len(result["reasons"]) >= 2

    # — is_high_stakes_disaster —

    def test_high_stakes_rescue_category(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("rescue", "general") is True

    def test_high_stakes_flood_disaster(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("food", "flood") is True

    def test_high_stakes_earthquake(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("shelter", "earthquake") is True

    def test_high_stakes_tsunami(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("medical", "tsunami") is True

    def test_not_high_stakes_education_rain(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("education", "rain") is False

    def test_not_high_stakes_food_drought(self):
        from database.verification import is_high_stakes_disaster
        assert is_high_stakes_disaster("food", "drought") is False

    # — build_common_only_trust_result —

    def test_build_common_only_trust_result_structure(self):
        from database.verification import build_common_only_trust_result, run_common_validation
        common = run_common_validation({"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0})
        result = build_common_only_trust_result(common, "food", "drought")
        assert "score" in result
        assert "dispatch_action" in result
        assert "reasons" in result

    def test_build_common_only_trust_score_range(self):
        from database.verification import build_common_only_trust_result, run_common_validation
        common = run_common_validation({"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0})
        result = build_common_only_trust_result(common, "food", "drought")
        assert 0 <= result["score"] <= 100

    # — calculate_trust_score —

    @patch("database.firestore_client.db")
    def test_calculate_trust_score_returns_dict(self, mock_db):
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
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

    @patch("database.firestore_client.db")
    def test_calculate_trust_score_within_range(self, mock_db):
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        with patch("requests.get") as mock_weather, patch("os.getenv", return_value=None):
            mock_weather.return_value.json.return_value = {"weather": [{"main": "Clear"}]}
            from database.verification import calculate_trust_score
            result = calculate_trust_score(
                {"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0,
                 "category": "rescue", "disaster_type": "flood"},
                ai_consistency=5, corroborating_reports_count=0,
                ai_category="rescue", base_score=20
            )
        assert 0 <= result["score"] <= 100

    @patch("database.firestore_client.db")
    def test_calculate_trust_score_corroboration_boosts_score(self, mock_db):
        mock_db.collection.return_value.where.return_value.where.return_value.stream.return_value = []
        with patch("requests.get") as mock_weather, patch("os.getenv", return_value=None):
            mock_weather.return_value.json.return_value = {"weather": [{"main": "Clear"}]}
            from database.verification import calculate_trust_score

            no_corr = calculate_trust_score(
                {"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0,
                 "category": "rescue", "disaster_type": "flood"},
                ai_consistency=5, corroborating_reports_count=0,
                ai_category="rescue", base_score=20
            )
            with_corr = calculate_trust_score(
                {"reporter_phone": "9876543210", "lat": 26.0, "lng": 80.0,
                 "category": "rescue", "disaster_type": "flood"},
                ai_consistency=5, corroborating_reports_count=3,
                ai_category="rescue", base_score=20
            )
        assert with_corr["score"] > no_corr["score"]