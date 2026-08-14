from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token
from database.postgres_client import get_db_cursor

router = APIRouter(prefix="/assignment")

@router.post("/volunteer/{need_id}")
def accept_need(
    need_id: str,
    volunteer_id: str = None,
    token: dict = Depends(verify_token)
):
    """
    Endpoint for a volunteer to 'claim' a need.
    Uses deferred import to prevent circular dependency crashes.
    """
    # 🏃 Move import here to prevent circular dependency at startup
    from database.assignments_db import save_assignment 
    
    # Get volunteer ID from the verified token/session
    if isinstance(token, dict):
        if token.get("role") == "system":
            # For system/tests, allow passing volunteer_id as parameter
            resolved_volunteer_id = volunteer_id or token.get("uid")
        else:
            # Enforce that volunteers can only claim for themselves!
            resolved_volunteer_id = token.get("uid")
    else:
        resolved_volunteer_id = volunteer_id

    if not resolved_volunteer_id:
         raise HTTPException(status_code=400, detail="volunteer_id is required.")
    
    try:
         # Ensure volunteer exists in the database
         with get_db_cursor(commit=False) as cur:
             cur.execute("SELECT 1 FROM volunteers WHERE id = %s", (resolved_volunteer_id,))
             if not cur.fetchone():
                 raise HTTPException(status_code=404, detail=f"Volunteer '{resolved_volunteer_id}' not found.")

         assignment_id = save_assignment(need_id, resolved_volunteer_id)
         return {
             "status": "assigned",
             "assignment_id": assignment_id,
             "message": f"Volunteer {resolved_volunteer_id} is now handling Need {need_id}"
         }
    except HTTPException:
         raise
    except Exception as e:
         # Log the error for Cloud Run debugging
         print(f"Error in accept_need: {str(e)}")
         raise HTTPException(status_code=500, detail=str(e))

@router.get("/volunteer/{volunteer_id}")
def get_volunteer_assignments(
    volunteer_id: str,
    token: dict = Depends(verify_token)
):
    from database.needs_db import get_need_by_id
    from database.assignments_db import get_assignments_by_volunteer_id
    
    # 🔒 Authorization & Ownership Checks
    if isinstance(token, dict):
        role = token.get("role")
        uid = token.get("uid")
        if role == "volunteer" and uid != volunteer_id:
            raise HTTPException(status_code=403, detail="Access denied: cannot view another volunteer's assignments")
        elif role == "ngo":
            # Check if volunteer belongs to this NGO
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT ngo_id FROM volunteers WHERE id = %s", (volunteer_id,))
                row = cur.fetchone()
            if not row or row.get("ngo_id") != uid:
                raise HTTPException(status_code=403, detail="Access denied: volunteer does not belong to this NGO")
        elif role not in ["system", "volunteer", "ngo"]:
            raise HTTPException(status_code=403, detail="Access denied: unauthorized role")

    assignments = get_assignments_by_volunteer_id(volunteer_id)
    
    # Join with need details for frontend display
    result = []
    for a in assignments:
        need_data = get_need_by_id(a["need_id"])
        if need_data:
            # Merge assignment metadata and original need data
            merged = {**need_data, **a}
            merged["assignment_id"] = a["id"]
            merged["id"] = need_data["id"] 
            result.append(merged)
        else:
            result.append(a)
            
    return result

@router.patch("/{assignment_id}/resolve")
def resolve(
    assignment_id: str,
    token: dict = Depends(verify_token)
):
    """
    Volunteer calls this to close a case.
    Marks assignment resolved and frees the volunteer status.
    """
    from database.assignments_db import resolve_assignment, get_assignment_by_id

    doc = get_assignment_by_id(assignment_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail=f"Assignment '{assignment_id}' not found")

    # Prevent double-resolution
    if doc.get("resolved_at") is not None or doc.get("status") == "resolved":
        raise HTTPException(status_code=409, detail="Assignment already resolved")

    need_id = doc.get("need_id")
    volunteer_id = doc.get("volunteer_id")
    
    if not need_id or not volunteer_id:
        raise HTTPException(
            status_code=422,
            detail="Assignment data corrupted: missing need_id or volunteer_id"
        )

    # 🔒 Authorization & Ownership Checks
    if isinstance(token, dict):
        role = token.get("role")
        uid = token.get("uid")
        if role == "volunteer" and uid != volunteer_id:
            raise HTTPException(status_code=403, detail="Access denied: cannot resolve another volunteer's assignment")
        elif role == "ngo":
            # Check if volunteer belongs to this NGO
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT ngo_id FROM volunteers WHERE id = %s", (volunteer_id,))
                row = cur.fetchone()
            if not row or row.get("ngo_id") != uid:
                raise HTTPException(status_code=403, detail="Access denied: volunteer does not belong to this NGO")
        elif role not in ["system", "volunteer", "ngo"]:
            raise HTTPException(status_code=403, detail="Access denied: unauthorized role")

    resolve_assignment(assignment_id, need_id, volunteer_id)

    return {
        "status": "resolved",
        "assignment_id": assignment_id,
        "message": "Case closed. Volunteer is now available again."
    }