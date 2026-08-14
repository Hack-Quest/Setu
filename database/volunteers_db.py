from database.postgres_client import get_db_cursor
from datetime import datetime, timezone
import bcrypt
import uuid

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
    email = email.lower().strip()

    # Check duplicate email
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT 1 FROM volunteers_auth WHERE email = %s", (email,))
        if cur.fetchone():
            return {"error": "Email already registered"}

    password_hash = hash_password(password)

    from database.geocoding import get_coordinates
    coords = get_coordinates(location)
    
    if not coords or coords.get("lat") == 0 or coords.get("lng") == 0:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400,
            detail=f"Invalid or unresolvable location: {location}"
        )

    skills_normalized = (
        [s.lower().strip() for s in skills]
        if isinstance(skills, list)
        else [skills.lower().strip()]
    )

    volunteer_id = uuid.uuid4().hex
    registered_at = datetime.now(timezone.utc)

    # We save in both tables using a transaction (commit=True)
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO volunteers_auth (
                id, email, password_hash, name, phone, location, skills, lat, lng, available, registered_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                volunteer_id, email, password_hash, name, phone, location,
                skills_normalized, coords["lat"], coords["lng"], True, registered_at
            )
        )

        cur.execute(
            """
            INSERT INTO volunteers (
                id, name, email, phone, skills, lat, lng, available, active_assignments, registered_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                volunteer_id, name, email, phone, skills_normalized,
                coords["lat"], coords["lng"], True, 0, registered_at
            )
        )

    print(f"[OK] Volunteer registered with ID: {volunteer_id}")
    return {"success": True, "volunteer_id": volunteer_id}


def login_volunteer(email: str, password: str) -> dict:
    """Login volunteer with email and password"""
    email = email.lower().strip()
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM volunteers_auth WHERE email = %s", (email,))
        row = cur.fetchone()

    if not row:
        return {"error": "Invalid email or password"}

    if not verify_password(password, row.get("password_hash", "")):
        return {"error": "Invalid email or password"}

    return {
        "success": True,
        "volunteer_id": row.get("id"),
        "name": row.get("name"),
        "email": row.get("email"),
    }


def save_volunteer(data) -> str:
    """
    Registers a new volunteer in Supabase PostgreSQL.
    Automatically marks them as available for deployment.
    """
    # Normalize skills
    if isinstance(data, dict) and "skills" in data and isinstance(data["skills"], list):
        data["skills"] = [s.lower().strip() for s in data["skills"]]

    from database.geocoding import get_coordinates

    # Handle both dict and object
    if isinstance(data, dict):
        location_text = data.get("location") or data.get("location_text") or ""
        lat = float(data.get("lat", 0.0))
        lng = float(data.get("lng", 0.0))
    else:
        location_text = getattr(data, "location", None) or getattr(data, "location_text", None) or ""
        lat = float(getattr(data, "lat", 0.0))
        lng = float(getattr(data, "lng", 0.0))

    print("📍 LOCATION RECEIVED:", location_text)

    # Skip geocoding if coordinates are already provided
    if lat != 0.0 and lng != 0.0:
        coords = {"lat": lat, "lng": lng}
        if not location_text.strip():
            location_text = f"{lat}, {lng}"
    else:
        if not location_text.strip():
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail="Location is required"
            )

        coords = get_coordinates(location_text)

        if not coords or coords.get("lat") is None or coords.get("lng") is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=400,
                detail=f"Invalid or unresolvable location: {location_text}"
            )

    # Normalize incoming format
    if isinstance(data, dict):
        data_dict = dict(data)
    else:
        data_dict = data.dict()

    doc_id = data_dict.get("id") or data_dict.get("volunteer_id") or uuid.uuid4().hex
    
    data_dict["id"] = doc_id
    data_dict["location"] = location_text
    data_dict["lat"] = coords["lat"]
    data_dict["lng"] = coords["lng"]
    data_dict["available"] = True
    data_dict["active_assignments"] = data_dict.get("active_assignments", 0)
    
    reg_at = data_dict.get("registered_at")
    if reg_at:
        if isinstance(reg_at, datetime):
            data_dict["registered_at"] = reg_at
        else:
            try:
                data_dict["registered_at"] = datetime.fromisoformat(reg_at)
            except ValueError:
                data_dict["registered_at"] = datetime.now(timezone.utc)
    else:
        data_dict["registered_at"] = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        # Check if already exists
        cur.execute("SELECT 1 FROM volunteers WHERE id = %s", (doc_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute(
                """
                UPDATE volunteers SET 
                    name = %s, email = %s, phone = %s, skills = %s, lat = %s, lng = %s, 
                    available = %s, active_assignments = %s, registered_at = %s, 
                    ngo_id = %s, ngo_verified = %s, specialty = %s, ngo_affiliation = %s, 
                    verification_code = %s, updated_at = %s
                WHERE id = %s
                """,
                (
                    data_dict.get("name"), data_dict.get("email"), data_dict.get("phone"), data_dict.get("skills"),
                    data_dict["lat"], data_dict["lng"], data_dict["available"], data_dict["active_assignments"],
                    data_dict["registered_at"], data_dict.get("ngo_id"), data_dict.get("ngo_verified", False),
                    data_dict.get("specialty"), data_dict.get("ngo_affiliation"), data_dict.get("verification_code"),
                    datetime.now(timezone.utc), doc_id
                )
            )
        else:
            cur.execute(
                """
                INSERT INTO volunteers (
                    id, name, email, phone, skills, lat, lng, available, active_assignments, registered_at, 
                    ngo_id, ngo_verified, specialty, ngo_affiliation, verification_code
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id, data_dict.get("name"), data_dict.get("email"), data_dict.get("phone"), data_dict.get("skills"),
                    data_dict["lat"], data_dict["lng"], data_dict["available"], data_dict["active_assignments"],
                    data_dict["registered_at"], data_dict.get("ngo_id"), data_dict.get("ngo_verified", False),
                    data_dict.get("specialty"), data_dict.get("ngo_affiliation"), data_dict.get("verification_code")
                )
            )

    print(f"[OK] Volunteer registered: {doc_id}")
    return doc_id


def get_available_volunteers(category: str = None) -> list:
    """Fetch available volunteers, optionally filtered by skill category"""
    with get_db_cursor(commit=False) as cur:
        if category:
            cur.execute(
                "SELECT * FROM volunteers WHERE available = TRUE AND %s = ANY(skills)",
                (category.lower().strip(),)
            )
        else:
            cur.execute("SELECT * FROM volunteers WHERE available = TRUE")
        
        rows = cur.fetchall()
        for row in rows:
            if row.get("registered_at"):
                row["registered_at"] = row["registered_at"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()
        return rows


def update_volunteer_status(doc_id: str, is_available: bool):
    """Update availability status of a volunteer"""
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE volunteers SET 
                available = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (is_available, datetime.now(timezone.utc), doc_id)
        )
    status_text = "Available" if is_available else "Deployed"
    print(f"[INFO] Volunteer {doc_id} status updated to: {status_text}")


def get_all_volunteers() -> list:
    """Fetch all volunteers from database"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM volunteers")
        rows = cur.fetchall()
        for row in rows:
            if row.get("registered_at"):
                row["registered_at"] = row["registered_at"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()
        return rows