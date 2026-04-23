from database.firestore_client import db
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


def save_ngo(data: dict) -> str:
    """
    Persists a new NGO record to Firestore.
    Sets verified=False by default (admin/auth flow promotes it later).
    """
    data.setdefault("verified", False)
    data["registered_at"] = datetime.now(timezone.utc).isoformat()

    update_time, doc_ref = db.collection("ngos").add(data)

    print(f"🏢 NGO registered with ID: {doc_ref.id}")
    return doc_ref.id


def get_ngo(ngo_id: str) -> dict | None:
    """
    Retrieves a single NGO document by its Firestore document ID.
    Returns None if the document does not exist.
    """
    doc = db.collection("ngos").document(ngo_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    print(f"⚠️  NGO with ID '{ngo_id}' not found.")
    return None


def verify_ngo(ngo_id: str, verified: bool = True) -> bool:
    """
    Flips the verification flag on an NGO record.
    Returns True on success, False if the document does not exist.
    """
    doc_ref = db.collection("ngos").document(ngo_id)
    if not doc_ref.get().exists:
        print(f"⚠️  Cannot verify — NGO '{ngo_id}' not found.")
        return False

    doc_ref.update({
        "verified": verified,
        "verified_at": datetime.now(timezone.utc).isoformat()
    })
    status = "✅ Verified" if verified else "❌ Unverified"
    print(f"{status} NGO: {ngo_id}")
    return True


def get_ngo_by_email(email: str) -> dict | None:
    """
    Retrieves a single NGO document by its email address.
    Returns None if no such NGO exists.
    """
    docs = (
        db.collection("ngos")
        .where(filter=FieldFilter("email", "==", email))
        .stream()
    )
    ngo_list = list(docs)
    
    if not ngo_list:
        return None
        
    doc = ngo_list[0]
    return {"id": doc.id, **doc.to_dict()}
