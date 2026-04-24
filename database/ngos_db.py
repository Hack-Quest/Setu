from database.firestore_client import db
from datetime import datetime, timezone
from google.cloud.firestore_v1.base_query import FieldFilter


# =========================
# 🏢 NGO CORE FUNCTIONS (UNCHANGED)
# =========================

def save_ngo(data: dict) -> str:
    data.setdefault("verified", False)
    data["registered_at"] = datetime.now(timezone.utc).isoformat()

    update_time, doc_ref = db.collection("ngos").add(data)

    print(f"🏢 NGO registered with ID: {doc_ref.id}")
    return doc_ref.id


def get_ngo(ngo_id: str) -> dict | None:
    doc = db.collection("ngos").document(ngo_id).get()
    if doc.exists:
        return {"id": doc.id, **doc.to_dict()}
    print(f"⚠️  NGO with ID '{ngo_id}' not found.")
    return None


def verify_ngo(ngo_id: str, verified: bool = True) -> bool:
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


def get_all_ngos() -> list:
    docs = db.collection("ngos").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


# =========================
# 📊 STATS FUNCTIONS (NEW)
# =========================

def get_ngo_stats() -> dict:
    ngos = db.collection("ngos").stream()

    total_ngos = 0
    verified_ngos = 0

    for doc in ngos:
        total_ngos += 1
        data = doc.to_dict()

        if data.get("verified"):
            verified_ngos += 1

    return {
        "total_ngos": total_ngos,
        "verified_ngos": verified_ngos
    }


def get_volunteer_stats() -> dict:
    volunteers = db.collection("volunteers").stream()

    total_volunteers = 0

    for _ in volunteers:
        total_volunteers += 1

    return {
        "total_volunteers": total_volunteers
    }


def get_report_stats() -> dict:
    reports = db.collection("needs_reports").stream()

    total_reports = 0

    for _ in reports:
        total_reports += 1

    return {
        "total_reports": total_reports
    }


# =========================
# 🚀 COMBINED DASHBOARD STATS
# =========================

def get_dashboard_stats() -> dict:
    ngo_stats = get_ngo_stats()
    volunteer_stats = get_volunteer_stats()
    report_stats = get_report_stats()

    return {
        "total_reports": report_stats["total_reports"],
        "total_volunteers": volunteer_stats["total_volunteers"],
        "total_ngos": ngo_stats["total_ngos"],
        "verified_ngos": ngo_stats["verified_ngos"]
    }