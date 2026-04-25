from database.firestore_client import db
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter

# These helpers ensure the statuses are synced across collections
from database.needs_db import update_need_status
from database.volunteers_db import update_volunteer_status

def save_assignment(need_id: str, volunteer_id: str) -> str:
    """
    Creates a new assignment and automatically updates the 
    status of both the volunteer and the community need.
    """

    # 🔥 NEW: Fetch volunteer details
    vol_ref = db.collection("volunteers").document(volunteer_id)
    vol_doc = vol_ref.get()
    vol_data = vol_doc.to_dict() if vol_doc.exists else {}

    # 🔥 NEW: Fetch need details
    need_ref = db.collection("needs_reports").document(need_id)
    need_doc = need_ref.get()
    need_data = need_doc.to_dict() if need_doc.exists else {}

    # 🔥 UPDATED: enriched assignment document
    doc = {
        "need_id": need_id,
        "need_description": need_data.get("description", ""),
        "need_location": need_data.get("location_text", ""),

        "volunteer_id": volunteer_id,
        "volunteer_name": vol_data.get("name", ""),
        "volunteer_phone": vol_data.get("phone", ""),

        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "status": "assigned",
        "resolved_at": None
    }
    
    # 1. Create the assignment record
    _, doc_ref = db.collection("assignments").add(doc)
    
    # 2. Update the connected systems (Atomic-like updates)
    update_need_status(need_id, "assigned")        
    update_volunteer_status(volunteer_id, False)   
    
    vol_ref = db.collection("volunteers").document(volunteer_id)
    vol_doc = vol_ref.get()

    if vol_doc.exists:
        vol_data = vol_doc.to_dict()
        current = vol_data.get("active_assignments", 0)

        vol_ref.update({
            "active_assignments": current + 1
        })

        if current + 1 >= 3:
            vol_ref.update({"available": False})
    
    print(f"🔗 Assignment {doc_ref.id} created: Volunteer {volunteer_id} -> Need {need_id}")
    return doc_ref.id


def resolve_assignment(doc_id: str, need_id: str, volunteer_id: str):
    """
    Marks the job as done, resolves the need, and frees up the volunteer.
    """
    db.collection("assignments").document(doc_id).update({
        "status": "resolved",
        "resolved_at": datetime.now(timezone.utc).isoformat()
    })
    
    update_need_status(need_id, "resolved")      
    update_volunteer_status(volunteer_id, True)   
    
    vol_ref = db.collection("volunteers").document(volunteer_id)
    vol_doc = vol_ref.get()

    if vol_doc.exists:
        vol_data = vol_doc.to_dict()
        current = vol_data.get("active_assignments", 0)

        new_count = max(0, current - 1)

        vol_ref.update({
            "active_assignments": new_count
        })

        if new_count < 3:
            vol_ref.update({"available": True})
    
    print(f"✅ Assignment {doc_id} resolved! Volunteer is free again.")


def get_assignments_by_volunteer_id(volunteer_id: str):
    docs = (
        db.collection("assignments")
        .where(filter=FieldFilter("volunteer_id", "==", volunteer_id))
        .stream()
    )
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]