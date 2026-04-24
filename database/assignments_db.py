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
    doc = {
        "need_id": need_id,
        "volunteer_id": volunteer_id,
        "assigned_at": datetime.now(timezone.utc).isoformat(),
        "status": "assigned",
        "resolved_at": None
    }
    
    # 1. Create the assignment record
    _, doc_ref = db.collection("assignments").add(doc)
    
    # 2. Update the connected systems (Atomic-like updates)
    # Set the Need status to 'assigned' so it disappears from the 'open' list
    update_need_status(need_id, "assigned")        
    
    # Set the Volunteer's availability to False (they are now busy)
    update_volunteer_status(volunteer_id, False)   
    
    print(f"🔗 Assignment {doc_ref.id} created: Volunteer {volunteer_id} -> Need {need_id}")
    return doc_ref.id

def resolve_assignment(doc_id: str, need_id: str, volunteer_id: str):
    """
    Marks the job as done, resolves the need, and frees up the volunteer.
    """
    # 1. Update assignment record
    db.collection("assignments").document(doc_id).update({
        "status": "resolved",
        "resolved_at": datetime.now(timezone.utc).isoformat()
    })
    
    # 2. Update need status to 'resolved'
    update_need_status(need_id, "resolved")      
    
    # 3. Set volunteer 'is_available' back to True
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