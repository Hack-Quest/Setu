from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from backend.auth import verify_token
from database.postgres_client import get_db_cursor
from database.assignments_db import save_assignment

router = APIRouter(prefix="/assignment")


@router.post("/volunteer/{need_id}")
def accept_need(
    need_id: str,
    volunteer_id: Optional[str] = Query(None),
    token: any = Depends(verify_token),
):
    """
    Endpoint for a volunteer to 'claim' a need.
    - Derives volunteer identity from authenticated token/session when available.
    - Prevents claiming someone else's assignment or duplicate claims.
    - Enforces volunteer existence, capacity/availability, skill compatibility,
      and Tier 1 verification for sensitive cases.
    """
    from backend.routes.match import is_sensitive_case, is_skill_compatible

    # 1. Resolve volunteer identity
    token_uid = None
    if isinstance(token, dict):
        token_uid = (
            token.get("uid")
            or token.get("sub")
            or token.get("id")
            or token.get("volunteer_id")
        )

    if token_uid:
        # If token carries authenticated identity, verify client does not attempt impersonation
        if volunteer_id and volunteer_id != token_uid:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You cannot claim an assignment for another volunteer.",
            )
        resolved_volunteer_id = token_uid
    else:
        # Fallback to client-provided volunteer_id during static token transition
        resolved_volunteer_id = volunteer_id

    if not resolved_volunteer_id:
        raise HTTPException(status_code=400, detail="volunteer_id is required.")

    # 2. Check volunteer existence and availability in database
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM volunteers WHERE id = %s", (resolved_volunteer_id,))
        vol = cur.fetchone()

    if not vol:
        raise HTTPException(
            status_code=404, detail=f"Volunteer '{resolved_volunteer_id}' not found."
        )

    if not vol.get("available", True) or (vol.get("active_assignments") or 0) >= 3:
        raise HTTPException(
            status_code=400,
            detail=f"Volunteer '{resolved_volunteer_id}' is currently unavailable or has reached maximum active assignments.",
        )

    # 3. Check need existence and status
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM needs_reports WHERE id = %s", (need_id,))
        need = cur.fetchone()

    if not need:
        raise HTTPException(status_code=404, detail=f"Need '{need_id}' not found.")

    need_status = str(need.get("status") or "").lower()
    if need_status == "resolved":
        raise HTTPException(
            status_code=409, detail=f"Need '{need_id}' is already resolved."
        )
    if need_status == "rejected":
        raise HTTPException(
            status_code=400, detail=f"Need '{need_id}' was rejected."
        )

    # 4. Check existing assignments for this need
    with get_db_cursor(commit=False) as cur:
        cur.execute(
            """
            SELECT * FROM assignments 
            WHERE need_id = %s AND (status = 'assigned' OR resolved_at IS NULL)
            """,
            (need_id,),
        )
        existing_assignments = cur.fetchall()

    if existing_assignments:
        for ea in existing_assignments:
            if ea.get("volunteer_id") == resolved_volunteer_id:
                raise HTTPException(
                    status_code=409,
                    detail="Assignment already claimed by this volunteer.",
                )
        # Assigned to someone else
        raise HTTPException(
            status_code=403,
            detail="Need is already claimed by or assigned to another volunteer.",
        )

    # 5. Check eligibility: Tier 1 for sensitive cases, and skill compatibility
    if is_sensitive_case(need) and not vol.get("ngo_verified"):
        raise HTTPException(
            status_code=403,
            detail="Sensitive case requires Tier 1 NGO verification.",
        )

    if not is_skill_compatible(need, vol):
        raise HTTPException(
            status_code=400,
            detail="Volunteer skills are incompatible with this emergency.",
        )

    # 6. Save assignment and update statuses
    try:
        assignment_id = save_assignment(need_id, resolved_volunteer_id)
        return {
            "status": "assigned",
            "assignment_id": assignment_id,
            "message": f"Volunteer {resolved_volunteer_id} is now handling Need {need_id}",
        }
    except ValueError as ve:
        raise HTTPException(status_code=409, detail=str(ve))
    except Exception as e:
        print(f"Error in accept_need: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/volunteer/{volunteer_id}")
def get_volunteer_assignments(
    volunteer_id: str, token: dict = Depends(verify_token)
):
    from database.needs_db import get_need_by_id
    from database.assignments_db import get_assignments_by_volunteer_id

    if isinstance(token, dict):
        role = token.get("role")
        caller_id = (
            token.get("uid")
            or token.get("sub")
            or token.get("id")
            or token.get("volunteer_id")
        )
        if role == "volunteer" and caller_id != volunteer_id:
            raise HTTPException(
                status_code=403,
                detail="Access denied: cannot view another volunteer's assignments",
            )
        elif role == "ngo":
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT ngo_id FROM volunteers WHERE id = %s", (volunteer_id,))
                row = cur.fetchone()
            if not row or row.get("ngo_id") != caller_id:
                raise HTTPException(
                    status_code=403,
                    detail="Access denied: volunteer is not affiliated with your NGO",
                )
        elif role not in ["system", "ngo", "volunteer"]:
            raise HTTPException(
                status_code=403,
                detail="Access denied: unauthorized role",
            )

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
def resolve(assignment_id: str, token: dict = Depends(verify_token)):
    """
    Volunteer, NGO, or system calls this to close a case.
    Marks assignment resolved and frees the volunteer status.
    Enforces authorization:
      - Volunteer: must be the assigned volunteer (caller.uid == assignment.volunteer_id)
      - NGO: volunteer must belong to this NGO (volunteer.ngo_id == caller.uid)
      - System: allowed
      - Unknown/other: 403 Forbidden
    """
    from database.assignments_db import resolve_assignment, get_assignment_by_id

    doc = get_assignment_by_id(assignment_id)

    if not doc:
        raise HTTPException(
            status_code=404, detail=f"Assignment '{assignment_id}' not found"
        )

    need_id = doc.get("need_id")
    volunteer_id = doc.get("volunteer_id")

    if not need_id or not volunteer_id:
        raise HTTPException(
            status_code=422,
            detail="Assignment data corrupted: missing need_id or volunteer_id",
        )

    # 🔒 Authorization Check
    caller_role = token.get("role") if isinstance(token, dict) else None
    caller_uid = (
        token.get("uid") or token.get("sub") or token.get("id") or token.get("volunteer_id")
    ) if isinstance(token, dict) else None

    if caller_role == "system":
        pass  # System callers are authorized
    elif caller_role == "volunteer":
        if not caller_uid or caller_uid != volunteer_id:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: You can only resolve your own assignments."
            )
    elif caller_role == "ngo":
        # An NGO may resolve an assignment ONLY if the assigned volunteer belongs to that NGO
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT ngo_id FROM volunteers WHERE id = %s", (volunteer_id,))
            vol_row = cur.fetchone()
        if not vol_row or vol_row.get("ngo_id") != caller_uid:
            raise HTTPException(
                status_code=403,
                detail="Forbidden: Volunteer is not affiliated with your NGO."
            )
    else:
        raise HTTPException(
            status_code=403,
            detail="Forbidden: Unauthorized role to resolve assignments."
        )

    # Prevent double-resolution
    if doc.get("resolved_at") is not None or doc.get("status") == "resolved":
        raise HTTPException(
            status_code=409, detail="Assignment already resolved"
        )

    resolve_assignment(assignment_id, need_id, volunteer_id)

    return {
        "status": "resolved",
        "assignment_id": assignment_id,
        "message": "Case closed. Volunteer is now available again.",
    }
