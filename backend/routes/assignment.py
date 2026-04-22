from fastapi import APIRouter, Depends, HTTPException
from backend.auth import verify_token
from database.assignments_db import resolve_assignment, get_assignments_by_volunteer_id
from database.firestore_client import db

router = APIRouter(prefix="/assignment")


@router.get("/volunteer/{volunteer_id}")
def get_volunteer_assignments(
    volunteer_id: str,
    token: str = Depends(verify_token)
):
    from database.needs_db import get_need_by_id
    assignments = get_assignments_by_volunteer_id(volunteer_id)
    
    # Join with need details
    result = []
    for a in assignments:
        need_data = get_need_by_id(a["need_id"])
        if need_data:
            # Merge assignment metadata and need data
            merged = {**need_data, **a}
            # Remove duplicated id fields if necessary or keep assignment id as assignment_id
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
    Marks the assignment resolved, sets need → 'resolved', frees the volunteer.
    """
    # Guard: make sure the assignment actually exists before touching it
    doc_ref = db.collection("assignments").document(assignment_id)
    snap = doc_ref.get()
    if not snap.exists:
        raise HTTPException(status_code=404, detail=f"Assignment '{assignment_id}' not found")

    doc = snap.to_dict()

    # Prevent double-resolve
    if doc.get("resolved_at") is not None or doc.get("status") == "resolved":
        raise HTTPException(status_code=409, detail="Assignment already resolved")

    need_id = doc.get("need_id")
    volunteer_id = doc.get("volunteer_id")
    if not need_id or not volunteer_id:
        raise HTTPException(
            status_code=422,
            detail="Assignment missing need_id or volunteer_id"
        )

    resolve_assignment(assignment_id, need_id, volunteer_id)

    return {
        "status": "resolved",
        "assignment_id": assignment_id,
        "need_id": need_id,
        "volunteer_id": volunteer_id,
        "message": "Case closed. Volunteer is now available again."
    }
