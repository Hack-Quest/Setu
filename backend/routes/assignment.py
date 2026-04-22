from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.auth import verify_token
from database.assignments_db import resolve_assignment, get_assignments_by_volunteer_id
from database.firestore_client import db

router = APIRouter(prefix="/assignment")


class ResolvePayload(BaseModel):
    need_id: str
    volunteer_id: str


@router.get("/volunteer/{volunteer_id}")
def get_volunteer_assignments(
    volunteer_id: str,
    token: str = Depends(verify_token)
):
    return get_assignments_by_volunteer_id(volunteer_id)


@router.patch("/{assignment_id}/resolve")
def resolve(
    assignment_id: str,
    payload: ResolvePayload,
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
    if doc.get("resolved_at") is not None:
        raise HTTPException(status_code=409, detail="Assignment already resolved")

    resolve_assignment(assignment_id, payload.need_id, payload.volunteer_id)

    return {
        "status": "resolved",
        "assignment_id": assignment_id,
        "need_id": payload.need_id,
        "volunteer_id": payload.volunteer_id,
        "message": "Case closed. Volunteer is now available again."
    }
