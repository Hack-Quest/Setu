from fastapi import APIRouter, HTTPException, Depends
from backend.models import NGOInput
from database.ngos_db import save_ngo, get_ngo, get_all_ngos
from backend.auth import verify_token
from database.geocoding import get_coordinates
from database.firestore_client import db
from database.needs_db import get_need_by_id
from google.cloud.firestore_v1.base_query import FieldFilter

router = APIRouter(prefix="/ngo", tags=["NGO"])


@router.get("/list")
def list_ngos():
    """Public endpoint — returns all registered NGOs."""
    try:
        ngos = get_all_ngos()
        safe_fields = ["id", "ngo_name", "owner_name", "description", "type", "location", "email",
                       "phone", "verified", "registered_at", "region"]
        sanitized = []
        for ngo in ngos:
            # Map legacy data to new fields
            ngo_name = ngo.get("ngo_name")
            owner_name = ngo.get("owner_name")
            
            # --- AUTO-MIGRATE ON READ (as requested by user to fix DB) ---
            if not ngo_name:
                ngo_name = "Helping Hands Foundation"
                owner_name = ngo.get("name", "Admin")
                try:
                    from database.firestore_client import db
                    db.collection("ngos").document(ngo["id"]).update({
                        "ngo_name": ngo_name,
                        "owner_name": owner_name
                    })
                    print(f"🔧 Backfilled NGO {ngo['id']} with {ngo_name}")
                except Exception as e:
                    print(f"⚠️ Could not backfill NGO {ngo['id']}: {e}")
            # -------------------------------------------------------------
            
            # Combine to the expected structured format
            sanitized_ngo = {k: v for k, v in ngo.items() if k in safe_fields}
            sanitized_ngo["ngo_name"] = ngo_name
            sanitized_ngo["owner_name"] = owner_name
            sanitized_ngo.setdefault("verified", False)
            sanitized_ngo.setdefault("email", ngo.get("email", ""))
            sanitized_ngo.setdefault("description", ngo.get("description", ""))
            sanitized.append(sanitized_ngo)

        print(f"✅ Returned {len(sanitized)} structured NGOs")
        if sanitized:
            print(f"Sample NGO: {sanitized[0]}")

        return {"ok": True, "data": sanitized}
    except Exception as e:
        print(f"❌ list_ngos error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/register")
def register_ngo(data: NGOInput, token: str = Depends(verify_token)):
    """Webhook/Forms endpoint for NGO registration"""
    try:
        print(f"📥 Received NGO Registration payload: {data}")
        coords = get_coordinates(data.location) if data.location else None
        ngo_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        if coords:
            ngo_dict["lat"] = coords.get("lat", ngo_dict.get("lat", 0.0))
            ngo_dict["lng"] = coords.get("lng", ngo_dict.get("lng", 0.0))
            
        ngo_dict.pop("verified", None)
        doc_id = save_ngo(ngo_dict)
        return {"message": "NGO registered successfully", "id": doc_id}
    except Exception as e:
        print("❌ NGO Registration Error:", e, flush=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ngo_id}")
def get_ngo_details(ngo_id: str):
    """Retrieve details of an NGO"""
    ngo = get_ngo(ngo_id)
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found")
    return ngo


@router.get("/{ngo_id}/dashboard")
def get_ngo_dashboard(ngo_id: str):
    ngo = get_ngo(ngo_id)
    if not ngo:
        raise HTTPException(status_code=404, detail="NGO not found")

    volunteer_docs = list(
        db.collection("volunteers")
        .where(filter=FieldFilter("ngo_id", "==", ngo_id))
        .stream()
    )
    managed_volunteers = []
    for doc in volunteer_docs:
        volunteer = {"id": doc.id, **doc.to_dict()}
        volunteer.setdefault(
            "role", "+".join(volunteer.get("skills", [])) or "Volunteer"
        )
        volunteer.setdefault(
            "status", "On Call" if volunteer.get("available", True) else "Deployed"
        )
        volunteer.setdefault("zone", volunteer.get("location", "Assigned region"))
        volunteer.setdefault("skills", volunteer.get("skills", []))
        managed_volunteers.append(volunteer)

    assignment_docs = list(db.collection("assignments").stream())
    active_assignments = []
    for doc in assignment_docs:
        assignment = {"id": doc.id, **doc.to_dict()}
        if assignment.get("resolved_at") is not None:
            continue

        need = get_need_by_id(assignment.get("need_id")) or {}
        volunteer = None
        volunteer_id = assignment.get("volunteer_id")
        if volunteer_id:
            volunteer_snap = db.collection("volunteers").document(str(volunteer_id)).get()
            if volunteer_snap.exists:
                volunteer = {"id": volunteer_snap.id, **volunteer_snap.to_dict()}

        active_assignments.append(
            {
                "id": assignment["id"],
                "title": need.get("summary_en")
                or need.get("description")
                or f"Need {assignment.get('need_id')}",
                "location": need.get("location_text")
                or need.get("category")
                or "Unknown",
                "lead": volunteer.get("name") if volunteer else "Unassigned",
                "priority": need.get("priority", "Low"),
                "status": need.get("status", "open"),
                "eta": "TBD",
            }
        )

    verified_professionals = sum(
        1
        for volunteer in managed_volunteers
        if volunteer.get("ngo_verified") or volunteer.get("ngo_id")
    )

    return {
        "ngo": ngo,
        "stats": {
            "active_assignments": len(active_assignments),
            "managed_volunteers": len(managed_volunteers),
            "verified_professionals": verified_professionals,
        },
        "active_assignments": active_assignments,
        "managed_volunteers": managed_volunteers,
    }
