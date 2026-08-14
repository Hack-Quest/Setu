from database.postgres_client import get_db_cursor
from datetime import datetime, timezone
import uuid

# These helpers ensure the statuses are synced across collections
from database.needs_db import update_need_status
from database.volunteers_db import update_volunteer_status

def save_assignment(need_id: str, volunteer_id: str) -> str:
    """
    Creates a new assignment and automatically updates the 
    status of both the volunteer and the community need.
    """
    # Fetch volunteer details
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM volunteers WHERE id = %s", (volunteer_id,))
        vol_data = cur.fetchone() or {}

    # Fetch need details
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM needs_reports WHERE id = %s", (need_id,))
        need_data = cur.fetchone() or {}

    doc_id = uuid.uuid4().hex
    assigned_at = datetime.now(timezone.utc)

    # 1. Create the assignment record
    with get_db_cursor(commit=True) as cur:
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
    
    # 2. Update the connected systems (Atomic-like updates)
    update_need_status(need_id, "assigned")        
    update_volunteer_status(volunteer_id, False)   

    # Update active assignments counter
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT active_assignments FROM volunteers WHERE id = %s", (volunteer_id,))
        vol_row = cur.fetchone()
        if vol_row:
            current = vol_row.get("active_assignments", 0) or 0
            new_count = current + 1
            available = False if new_count >= 3 else True
            
            cur.execute(
                """
                UPDATE volunteers SET 
                    active_assignments = %s,
                    available = %s
                WHERE id = %s
                """,
                (new_count, available, volunteer_id)
            )
    
    print(f"[INFO] Assignment {doc_id} created: Volunteer {volunteer_id} -> Need {need_id}")
    return doc_id


def resolve_assignment(doc_id: str, need_id: str, volunteer_id: str):
    """
    Marks the job as done, resolves the need, and frees up the volunteer.
    """
    resolved_at = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            UPDATE assignments SET 
                status = 'resolved',
                resolved_at = %s
            WHERE id = %s
            """,
            (resolved_at, doc_id)
        )
    
    update_need_status(need_id, "resolved")      
    update_volunteer_status(volunteer_id, True)   
    
    with get_db_cursor(commit=True) as cur:
        cur.execute("SELECT active_assignments FROM volunteers WHERE id = %s", (volunteer_id,))
        vol_row = cur.fetchone()
        if vol_row:
            current = vol_row.get("active_assignments", 0) or 0
            new_count = max(0, current - 1)
            available = True if new_count < 3 else False
            
            cur.execute(
                """
                UPDATE volunteers SET 
                    active_assignments = %s,
                    available = %s
                WHERE id = %s
                """,
                (new_count, available, volunteer_id)
            )
    
    print(f"[OK] Assignment {doc_id} resolved! Volunteer is free again.")


def get_assignments_by_volunteer_id(volunteer_id: str):
    """Fetch assignments associated with a volunteer"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM assignments WHERE volunteer_id = %s", (volunteer_id,))
        rows = cur.fetchall()
        for row in rows:
            if row.get("assigned_at"):
                row["assigned_at"] = row["assigned_at"].isoformat()
            if row.get("resolved_at"):
                row["resolved_at"] = row["resolved_at"].isoformat()
        return rows


def get_assignment_by_id(assignment_id: str) -> dict | None:
    """Fetch assignment by its ID"""
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM assignments WHERE id = %s", (assignment_id,))
        row = cur.fetchone()
    if row:
        if row.get("assigned_at"):
            row["assigned_at"] = row["assigned_at"].isoformat()
        if row.get("resolved_at"):
            row["resolved_at"] = row["resolved_at"].isoformat()
        return row
    return None