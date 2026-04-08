from database.firestore_client import db
from datetime import datetime, timezone

def save_need(data: dict) -> str:
    """Stores need into Firestore"""

    # 1. System level tracking
    data["status"] = "open"
    data["timestamp"] = datetime.now(timezone.utc).isoformat()
    
    # 2. Push to the 'needs_reports' collection in Firestore
    update_time, doc_ref = db.collection("needs_reports").add(data)

    print(f"✅ Successfully saved need with ID: {doc_ref.id}")
    return doc_ref.id

def update_need_status(doc_id: str, new_status: str):
    """
    Updates the status of a need (e.g., from 'open' to 'assigned' or 'resolved').
    """
    db.collection("needs_reports").document(doc_id).update({
        "status": new_status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    print(f"🔄 Need {doc_id} status updated to {new_status}")
    
def get_open_needs() -> list:
    """
    Fetches all currently unassigned/open needs for the volunteers to see.
    """
    # Query Firestore for only the "open" reports
    docs = db.collection("needs_reports").where("status", "==", "open").stream()
    
    # Package the results nicely into a Python list
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

def get_need_by_id(doc_id: str) -> dict:
    """Fetches a single need by its exact Firestore document ID."""
    doc = db.collection("needs_reports").document(doc_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    return None