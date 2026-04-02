from database.firestore_client import db
from datetime import datetime, timezone

def save_volunteer(data: dict) -> str:
    """
    Registers a new volunteer in Firestore.
    Automatically marks them as available for deployment.
    """
    data["available"] = True
    data["registered_at"] = datetime.now(timezone.utc).isoformat()
    
    update_time, doc_ref = db.collection("volunteers").add(data)
    
    print(f"🦸 Successfully registered volunteer with ID: {doc_ref.id}")
    return doc_ref.id

def get_available_volunteers() -> list:
    """
    Fetches a list of all volunteers who are currently free to help.
    """
    docs = db.collection("volunteers").where("available", "==", True).stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]

def update_volunteer_status(doc_id: str, is_available: bool):
    """
    Toggles a volunteer's availability (e.g., False when they are on a mission).
    """
    db.collection("volunteers").document(doc_id).update({
        "available": is_available,
        "updated_at": datetime.now(timezone.utc).isoformat()
    })
    status_text = "Available" if is_available else "Deployed"
    print(f"🔄 Volunteer {doc_id} status updated to: {status_text}")