from database.postgres_client import get_db_cursor
from datetime import datetime, timezone, timedelta
import uuid

def save_need(data: dict) -> str:
    """Stores need into Supabase PostgreSQL"""
    doc_id = data.get("id") or uuid.uuid4().hex
    
    data["status"] = "open"
    
    timestamp = data.get("timestamp")
    if timestamp:
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp)
            except ValueError:
                timestamp = datetime.now(timezone.utc)
        elif not isinstance(timestamp, datetime):
            timestamp = datetime.now(timezone.utc)
    else:
        timestamp = datetime.now(timezone.utc)
        
    data["timestamp"] = timestamp

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO needs_reports (
                id, reporter_name, reporter_phone, location_text, description, lat, lng,
                severity, category, status, timestamp, updated_at, trust_score,
                summary_en, summary_local, disaster_type, help_needed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc_id, data.get("reporter_name"), data.get("reporter_phone"), data.get("location_text"),
                data.get("description"), data.get("lat"), data.get("lng"), data.get("severity"),
                data.get("category"), data["status"], data["timestamp"], data.get("updated_at"),
                data.get("trust_score"), data.get("summary_en"), data.get("summary_local"),
                data.get("disaster_type"), data.get("help_needed")
            )
        )

    print(f"[OK] Successfully saved need with ID: {doc_id}")
    return doc_id


def update_need_status(doc_id: str, new_status: str):
    """
    Updates the status of a need (e.g., from 'open' to 'assigned' or 'resolved').
    """
    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE needs_reports SET 
                status = %s,
                updated_at = %s
            WHERE id = %s
            """,
            (new_status, datetime.now(timezone.utc), doc_id)
        )
    print(f"[INFO] Need {doc_id} status updated to {new_status}")


def get_open_needs() -> list:
    """
    Fetches all currently unassigned/open needs for the volunteers to see.
    """
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM needs_reports WHERE status = 'open'")
        rows = cur.fetchall()
        for row in rows:
            if row.get("timestamp"):
                row["timestamp"] = row["timestamp"].isoformat()
            if row.get("updated_at"):
                row["updated_at"] = row["updated_at"].isoformat()
        return rows


def get_all_needs() -> list:
    """
    Fetches all needs from PostgreSQL regardless of status.
    """
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM needs_reports")
        rows = cur.fetchall()
        
    print("\n[DB DEBUG] fetching from 'needs_reports' table...")
    print(f"[DB DEBUG] TOTAL DOCS FOUND: {len(rows)}")
    
    for r in rows:
        if r.get("timestamp"):
            r["timestamp"] = r["timestamp"].isoformat()
        if r.get("updated_at"):
            r["updated_at"] = r["updated_at"].isoformat()
        print(f"[DB DEBUG] Doc {r.get('id')} -> {r}")
        
    return rows


def get_need_by_id(doc_id: str) -> dict | None:
    """Fetches a single need by its ID."""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM needs_reports WHERE id = %s", (str(doc_id),))
        row = cur.fetchone()
        
    if row:
        if row.get("timestamp"):
            row["timestamp"] = row["timestamp"].isoformat()
        if row.get("updated_at"):
            row["updated_at"] = row["updated_at"].isoformat()
        return row
    return None


def check_corroboration(lat: float, lng: float, category: str) -> int:
    """
    Checks how many recent, nearby reports share the same category.
    - Time window: last 2 hours
    - Distance check: within 0.05 degrees (~5km) in both lat and lng
    - Returns: count of matching corroborating reports (int)
    """
    try:
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)

        with get_db_cursor(commit=False) as cur:
            cur.execute(
                """
                SELECT lat, lng, timestamp FROM needs_reports
                WHERE category = %s AND timestamp >= %s
                """,
                (category, two_hours_ago)
            )
            rows = cur.fetchall()

        count = 0
        for r in rows:
            doc_lat = r.get("lat")
            doc_lng = r.get("lng")
            if (
                doc_lat is not None
                and doc_lng is not None
                and lat is not None
                and lng is not None
            ):
                if abs(doc_lat - lat) <= 0.05 and abs(doc_lng - lng) <= 0.05:
                    count += 1
            else:
                # Coordinates unavailable — count category + time match alone
                count += 1

        return count

    except Exception as e:
        print(f"[Corroboration] Query failed: {e}. Defaulting to 0.")
        return 0
