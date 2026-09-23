from database.postgres_client import get_db_cursor
from datetime import datetime, timezone
import uuid

# These helpers ensure the statuses are synced across collections
from database.needs_db import update_need_status
from database.volunteers_db import update_volunteer_status

def save_assignment(need_id: str, volunteer_id: str) -> str:
    """
    Creates a new assignment and atomically updates both
    the volunteer and the need status in a single database transaction.
    """
    doc_id = uuid.uuid4().hex
    assigned_at = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        # 1. Fetch volunteer and lock row
        cur.execute(
            "SELECT id, name, phone, active_assignments, available FROM volunteers WHERE id = %s FOR UPDATE",
            (volunteer_id,)
        )
        vol_data = cur.fetchone()
        if not vol_data:
            raise ValueError(f"Volunteer '{volunteer_id}' not found")

        if vol_data.get("active_assignments", 0) >= 3:
            raise ValueError(f"Volunteer '{volunteer_id}' has reached maximum active assignments")

        # 2. Fetch need and lock row
        cur.execute(
            "SELECT id, description, location_text, status FROM needs_reports WHERE id = %s FOR UPDATE",
            (need_id,)
        )
        need_data = cur.fetchone()
        if not need_data:
            raise ValueError(f"Need '{need_id}' not found")

        # Prevent duplicate active assignment if need is already assigned, resolved, or rejected
        if need_data.get("status") in ("assigned", "resolved", "rejected"):
            raise ValueError(f"Need '{need_id}' is already {need_data['status']}")

        # 3. Create the assignment record
        cur.execute(
            """
            INSERT INTO assignments (
                id, need_id, need_description, need_location, volunteer_id, 
                volunteer_name, volunteer_phone, assigned_at, status, resolved_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                doc_id, need_id, need_data.get("description", ""), need_data.get("location_text", ""),
                volunteer_id, vol_data.get("name", ""), vol_data.get("phone", ""),
                assigned_at, "assigned", None
            )
        )

        # 4. Update need status to assigned
        cur.execute(
            """
            UPDATE needs_reports SET 
                status = 'assigned',
                updated_at = %s
            WHERE id = %s
            """,
            (assigned_at, need_id)
        )

        # 5. Atomically update volunteer active_assignments counter & availability
        cur.execute(
            """
            UPDATE volunteers SET 
                active_assignments = active_assignments + 1,
                available = CASE WHEN active_assignments + 1 >= 3 THEN FALSE ELSE TRUE END,
                updated_at = %s
            WHERE id = %s
            """,
            (assigned_at, volunteer_id)
        )

    print(f"[INFO] Assignment {doc_id} created: Volunteer {volunteer_id} -> Need {need_id}")
    return doc_id


def resolve_assignment(doc_id: str, need_id: str, volunteer_id: str):
    """
    Marks the job as done, resolves the need, and frees up the volunteer.
    All operations are committed in a single atomic database transaction.
    """
    resolved_at = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        # 1. Update assignment status
        cur.execute(
            """
            UPDATE assignments SET 
                status = 'resolved',
                resolved_at = %s
            WHERE id = %s
            """,
            (resolved_at, doc_id)
        )

        # 2. Update need status
        cur.execute(
            """
            UPDATE needs_reports SET 
                status = 'resolved',
                updated_at = %s
            WHERE id = %s
            """,
            (resolved_at, need_id)
        )

        # 3. Atomically decrement volunteer active_assignments counter & restore availability
        cur.execute(
            """
            UPDATE volunteers SET 
                active_assignments = GREATEST(0, active_assignments - 1),
                available = TRUE,
                updated_at = %s
            WHERE id = %s
            """,
            (resolved_at, volunteer_id)
        )

    print(f"[OK] Assignment {doc_id} resolved! Volunteer is free again.")
    return True


def get_assignments_by_volunteer_id(volunteer_id: str):
    """Fetch assignments associated with a volunteer"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM assignments WHERE volunteer_id = %s", (volunteer_id,))
        rows = cur.fetchall()
        for row in rows:
            if row.get("assigned_at") and hasattr(row["assigned_at"], "isoformat"):
                row["assigned_at"] = row["assigned_at"].isoformat()
            if row.get("resolved_at") and hasattr(row["resolved_at"], "isoformat"):
                row["resolved_at"] = row["resolved_at"].isoformat()
        return rows


def get_assignment_by_id(assignment_id: str) -> dict | None:
    """Fetch assignment by its ID"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM assignments WHERE id = %s", (assignment_id,))
        row = cur.fetchone()
    if row:
        if row.get("assigned_at") and hasattr(row["assigned_at"], "isoformat"):
            row["assigned_at"] = row["assigned_at"].isoformat()
        if row.get("resolved_at") and hasattr(row["resolved_at"], "isoformat"):
            row["resolved_at"] = row["resolved_at"].isoformat()
        return row
    return None