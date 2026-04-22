from database.firestore_client import db
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter

from database.needs_db import update_need_status
from database.volunteers_db import update_volunteer_status

def save_assignment(need_id: str, volunteer_id: str) -> str:
    """
    Creates a new assignment and automatically updates the 
    status of both the volunteer and the community need.
    """
    doc = {
        "need_id": need_id,
        "volunteer_id": volunteer_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "resolved_at": None
    }
    
    # 1. Create the assignment record
    update_time, doc_ref = db.collection("assignments").add(doc)
    
    # 2. Update the connected systems! (This is the "Smart" part)
    update_need_status(need_id, "assigned")        # Need is no longer open
    update_volunteer_status(volunteer_id, False)   # Volunteer is now deployed
    
    print(f"🔗 Assignment {doc_ref.id} created: Volunteer {volunteer_id} -> Need {need_id}")
    return doc_ref.id

def resolve_assignment(doc_id: str, need_id: str, volunteer_id: str):
    """
    Marks the job as done, resolves the need, and frees up the volunteer.
    """
    
    db.collection("assignments").document(doc_id).update({
        "resolved_at": datetime.now(timezone.utc).isoformat()
    })
    
    update_need_status(need_id, "resolved")      
    update_volunteer_status(volunteer_id, True)   
    
    print(f"✅ Assignment {doc_id} resolved! Volunteer is free again.")


def get_assignments_by_volunteer_id(volunteer_id: str):
    """
    Returns assignment documents for a specific volunteer.
    Includes Firestore document IDs in each returned record.
    """
    docs = (
        db.collection("assignments")
        .where(filter=FieldFilter("volunteer_id", "==", volunteer_id))
        .stream()
    )
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]