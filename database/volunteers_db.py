from database.firestore_client import db
from datetime import datetime, timezone
import bcrypt
import hmac
from google.cloud.firestore_v1.base_query import FieldFilter


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hash_value: str) -> bool:
    """Verify password against hash"""
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hash_value.encode("utf-8"))
    except Exception:
        return False


def register_volunteer_auth(
    email: str, password: str, name: str, phone: str, location: str, skills: list
) -> dict:
    """Register a new volunteer with email and password authentication"""

    existing = (
        db.collection("volunteers_auth")
        .where(filter=FieldFilter("email", "==", email))
        .stream()
    )
    if list(existing):
        return {"error": "Email already registered"}

    password_hash = hash_password(password)

    from database.geocoding import get_coordinates
    coords = get_coordinates(location)

    volunteer_data = {
        "email": email,
        "password_hash": password_hash,
        "name": name,
        "phone": phone,
        "location": location,
        "skills": (
            [s.lower().strip() for s in skills]
            if isinstance(skills, list)
            else [skills.lower().strip()]
        ),
        "lat": coords.get("lat", 0.0) if coords else 0.0,
        "lng": coords.get("lng", 0.0) if coords else 0.0,
        "available": True,
        "registered_at": datetime.now(timezone.utc).isoformat(),
    }

    update_time, doc_ref = db.collection("volunteers_auth").add(volunteer_data)

    # 🔥 ALSO SAVE IN MAIN VOLUNTEERS COLLECTION (FOR MATCHING)
    main_ref = db.collection("volunteers").document()

    main_ref.set({
        "id": main_ref.id,
        "name": name,
        "phone": phone,
        "skills": volunteer_data["skills"],
        "lat": volunteer_data["lat"],
        "lng": volunteer_data["lng"],
        "available": True,
        "active_assignments": 0,
    })

    print(f"🦸 Volunteer registered with ID: {main_ref.id}")
    return {"success": True, "volunteer_id": main_ref.id}


def login_volunteer(email: str, password: str) -> dict:
    docs = (
        db.collection("volunteers_auth")
        .where(filter=FieldFilter("email", "==", email))
        .stream()
    )
    volunteer_list = list(docs)

    if not volunteer_list:
        return {"error": "Invalid email or password"}

    volunteer_doc = volunteer_list[0]
    volunteer_data = volunteer_doc.to_dict()

    if not verify_password(password, volunteer_data.get("password_hash", "")):
        return {"error": "Invalid email or password"}

    return {
        "success": True,
        "volunteer_id": volunteer_doc.id,
        "name": volunteer_data.get("name"),
        "email": volunteer_data.get("email"),
    }


def save_volunteer(data: dict) -> str:
    """
    Registers a new volunteer in Firestore.
    Automatically marks them as available for deployment.
    """

    # Normalize skills
    if "skills" in data and isinstance(data["skills"], list):
        data["skills"] = [s.lower().strip() for s in data["skills"]]

    # 🔥 FIXED GEOLOGIC (ROBUST)
    from database.geocoding import get_coordinates

    location_text = data.get("location") or data.get("location_text") or ""

    coords = get_coordinates(location_text)

    if not coords:
        print(f"⚠️ Geocoding failed for location: {location_text}")

    data["lat"] = coords.get("lat", 0.0) if coords else 0.0
    data["lng"] = coords.get("lng", 0.0) if coords else 0.0

    # 🔥 SAFETY CHECK
    if data["lat"] == 0.0 and data["lng"] == 0.0:
        print("❌ WARNING: Volunteer saved with invalid coordinates")

    data["available"] = True
    data["active_assignments"] = 0
    data["registered_at"] = datetime.now(timezone.utc).isoformat()

    update_time, doc_ref = db.collection("volunteers").add(data)

    print(f"Volunteer registered: {doc_ref.id}")
    return doc_ref.id


def get_available_volunteers(category: str = None) -> list:
    docs = (
        db.collection("volunteers")
        .where(filter=FieldFilter("available", "==", True))
        .stream()
    )
    volunteers = [{"id": doc.id, **doc.to_dict()} for doc in docs]

    if category:
        volunteers = [v for v in volunteers if category in v.get("skills", [])]

    return volunteers


def update_volunteer_status(doc_id: str, is_available: bool):
    db.collection("volunteers").document(doc_id).update(
        {
            "available": is_available,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    status_text = "Available" if is_available else "Deployed"
    print(f"🔄 Volunteer {doc_id} status updated to: {status_text}")


def get_all_volunteers() -> list:
    docs = db.collection("volunteers").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]