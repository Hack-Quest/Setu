from database.postgres_client import get_db_cursor
from datetime import datetime, timezone
import uuid

# =========================
# 🏢 NGO CORE FUNCTIONS
# =========================

def save_ngo(data: dict) -> str:
    """Register and save a new NGO"""
    doc_id = data.get("id") or uuid.uuid4().hex
    
    data.setdefault("verified", False)
    
    reg_at = data.get("registered_at")
    if reg_at:
        if isinstance(reg_at, datetime):
            data["registered_at"] = reg_at
        else:
            try:
                data["registered_at"] = datetime.fromisoformat(reg_at)
            except ValueError:
                data["registered_at"] = datetime.now(timezone.utc)
    else:
        data["registered_at"] = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        # Check if already exists
        cur.execute("SELECT 1 FROM ngos WHERE id = %s", (doc_id,))
        exists = cur.fetchone()
        
        if exists:
            cur.execute(
                """
                UPDATE ngos SET 
                    ngo_name = %s, owner_name = %s, description = %s, type = %s, 
                    location = %s, email = %s, phone = %s, verified = %s, 
                    registered_at = %s, verified_at = %s, region = %s, 
                    reg_number = %s, lat = %s, lng = %s, radius = %s
                WHERE id = %s
                """,
                (
                    data.get("ngo_name") or data.get("name"), data.get("owner_name") or data.get("name"),
                    data.get("description"), data.get("type"), data.get("location"), data.get("email"),
                    data.get("phone"), data.get("verified"), data["registered_at"], data.get("verified_at"),
                    data.get("region"), data.get("reg_number"), data.get("lat"), data.get("lng"),
                    data.get("radius"), doc_id
                )
            )
        else:
            cur.execute(
                """
                INSERT INTO ngos (
                    id, ngo_name, owner_name, description, type, location, email, phone, 
                    verified, registered_at, verified_at, region, reg_number, lat, lng, radius
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    doc_id, data.get("ngo_name") or data.get("name"), data.get("owner_name") or data.get("name"),
                    data.get("description"), data.get("type"), data.get("location"), data.get("email"),
                    data.get("phone"), data.get("verified"), data["registered_at"], data.get("verified_at"),
                    data.get("region"), data.get("reg_number"), data.get("lat"), data.get("lng"),
                    data.get("radius")
                )
            )

    print(f"[OK] NGO registered with ID: {doc_id}")
    return doc_id


def get_ngo(ngo_id: str) -> dict | None:
    """Retrieve an NGO by ID"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM ngos WHERE id = %s", (ngo_id,))
        row = cur.fetchone()
        
    if row:
        if row.get("registered_at"):
            row["registered_at"] = row["registered_at"].isoformat()
        if row.get("verified_at"):
            row["verified_at"] = row["verified_at"].isoformat()
        return row
    print(f"[WARN] NGO with ID '{ngo_id}' not found.")
    return None


def verify_ngo(ngo_id: str, verified: bool = True) -> bool:
    """Verify or unverify an NGO"""
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT 1 FROM ngos WHERE id = %s", (ngo_id,))
        if not cur.fetchone():
            print(f"[WARN] Cannot verify — NGO '{ngo_id}' not found.")
            return False
            
        cur.execute(
            """
            UPDATE ngos SET 
                verified = %s,
                verified_at = %s
            WHERE id = %s
            """,
            (verified, datetime.now(timezone.utc), ngo_id)
        )

    status = "[OK] Verified" if verified else "[INFO] Unverified"
    print(f"{status} NGO: {ngo_id}")
    return True


def get_ngo_by_email(email: str) -> dict | None:
    """Retrieve an NGO by its email address"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM ngos WHERE email = %s", (email.strip().lower(),))
        row = cur.fetchone()
        
    if row:
        if row.get("registered_at"):
            row["registered_at"] = row["registered_at"].isoformat()
        if row.get("verified_at"):
            row["verified_at"] = row["verified_at"].isoformat()
        return row
    return None


def get_all_ngos() -> list:
    """Retrieve all registered NGOs"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM ngos")
        rows = cur.fetchall()
        for row in rows:
            if row.get("registered_at"):
                row["registered_at"] = row["registered_at"].isoformat()
            if row.get("verified_at"):
                row["verified_at"] = row["verified_at"].isoformat()
        return rows


# =========================
# 📊 STATS FUNCTIONS
# =========================

def get_ngo_stats() -> dict:
    """Get count stats for NGOs"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT COUNT(*) as total FROM ngos")
        total_ngos = cur.fetchone()["total"]
        
        cur.execute("SELECT COUNT(*) as total FROM ngos WHERE verified = TRUE")
        verified_ngos = cur.fetchone()["total"]
        
    return {
        "total_ngos": total_ngos,
        "verified_ngos": verified_ngos
    }


def get_volunteer_stats() -> dict:
    """Get count stats for volunteers"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT COUNT(*) as total FROM volunteers")
        total_volunteers = cur.fetchone()["total"]
        
    return {
        "total_volunteers": total_volunteers
    }


def get_report_stats() -> dict:
    """Get count stats for needs reports"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT COUNT(*) as total FROM needs_reports")
        total_reports = cur.fetchone()["total"]
        
    return {
        "total_reports": total_reports
    }


# =========================
# 🚀 COMBINED DASHBOARD STATS
# =========================

def get_dashboard_stats() -> dict:
    """Get consolidated dashboard stats"""
    ngo_stats = get_ngo_stats()
    volunteer_stats = get_volunteer_stats()
    report_stats = get_report_stats()

    return {
        "total_reports": report_stats["total_reports"],
        "total_volunteers": volunteer_stats["total_volunteers"],
        "total_ngos": ngo_stats["total_ngos"],
        "verified_ngos": ngo_stats["verified_ngos"]
    }