from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token
from database.firestore_client import db

router = APIRouter(prefix="/assignment")

@router.post("/volunteer/{need_id}")
def accept_need(
    need_id: str,
    token: str = Depends(verify_token)
):
    """
    Endpoint for a volunteer to 'claim' a need.
    Uses deferred import to prevent circular dependency crashes.
    """
    # 🏃 Move import here to prevent circular dependency at startup
    from database.assignments_db import save_assignment 
    
    # Get volunteer UID from the verified Firebase token
    volunteer_id = token.get("uid") 
    if not volunteer_id:
         raise HTTPException(status_code=401, detail="User ID (UID) missing from token.")
    
    try:
        assignment_id = save_assignment(need_id, volunteer_id)
        return {
            "status": "assigned",
            "assignment_id": assignment_id,
            "message": f"Volunteer {volunteer_id} is now handling Need {need_id}"
        }
    except Exception as e:
        # Log the error for Cloud Run debugging
        print(f"Error in accept_need: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/volunteer/{volunteer_id}")
def get_volunteer_assignments(
    volunteer_id: str,
    token: str = Depends(verify_token)
):
    from database.needs_db import get_need_by_id
    from database.assignments_db import get_assignments_by_volunteer_id
    
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
    token: str = Depends(verify_token)
):
    """
    Volunteer calls this to close a case.
    Marks assignment resolved and frees the volunteer status.
    """
    from database.assignments_db import resolve_assignment

    doc_ref = db.collection("assignments").document(assignment_id)
    snap = doc_ref.get()
    
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Assignment '{assignment_id}' not found")

    doc = snap.to_dict()

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

    resolve_assignment(assignment_id, need_id, volunteer_id)

    return {
        "status": "resolved",
        "assignment_id": assignment_id,
        "message": "Case closed. Volunteer is now available again."
    }