from database.firestore_client import db
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


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
    db.collection("needs_reports").document(doc_id).update(
        {"status": new_status, "updated_at": datetime.now(timezone.utc).isoformat()}
    )
    print(f"🔄 Need {doc_id} status updated to {new_status}")


def get_open_needs() -> list:
    """
    Fetches all currently unassigned/open needs for the volunteers to see.
    """
    # Query Firestore for only the "open" reports
    docs = (
        db.collection("needs_reports")
        .where(filter=FieldFilter("status", "==", "open"))
        .stream()
    )

    # Package the results nicely into a Python list
    return [{**doc.to_dict(), "id": doc.id} for doc in docs]


def get_need_by_id(doc_id: str) -> dict:
    """Fetches a single need by its exact Firestore document ID."""
    doc = db.collection("needs_reports").document(str(doc_id)).get()
    if doc.exists:
        return {**doc.to_dict(), "id": doc.id}
    return None


def check_corroboration(lat: float, lng: float, category: str) -> int:
    """
    Checks how many recent, nearby reports share the same category.

    - Time window: last 2 hours (filtered in Python to avoid composite index)
    - Distance check: within 0.05 degrees (~5km) in both lat and lng
    - Returns: count of matching corroborating reports (int)
    """
    try:
        from datetime import timedelta

        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        two_hours_ago_iso = two_hours_ago.isoformat()

        # Composite query using category equality and timestamp inequality
        # Requires composite index in firestore.indexes.json!
        docs = (
            db.collection("needs_reports")
            .where(filter=FieldFilter("category", "==", category))
            .where(filter=FieldFilter("timestamp", ">=", two_hours_ago_iso))
            .stream()
        )

        count = 0
        for doc in docs:
            d = doc.to_dict()

            # Manual time filter: only count reports from the last 2 hours
            doc_time_str = d.get("timestamp")
            if doc_time_str:
                try:
                    doc_time = datetime.fromisoformat(doc_time_str)
                    # Normalise to UTC if naive (safety for older records)
                    if doc_time.tzinfo is None:
                        doc_time = doc_time.replace(tzinfo=timezone.utc)
                    if doc_time < two_hours_ago:
                        continue  # Skip reports older than 2 hours
                except ValueError:
                    pass  # Unparseable timestamp — include anyway

            # Mock distance check: within ~0.05 degrees (~5km bounding box)
            doc_lat = d.get("lat")
            doc_lng = d.get("lng")
            if (
                doc_lat is not None
                and doc_lng is not None
                and lat is not None
                and lng is not None
            ):
                if abs(doc_lat - lat) <= 0.05 and abs(doc_lng - lng) <= 0.05:
                    count += 1
            else:
                # Coordinates unavailable — count category + time match alone
                count += 1

        return count

    except Exception as e:
        print(f"[Corroboration] Query failed: {e}. Defaulting to 0.")
        return 0
