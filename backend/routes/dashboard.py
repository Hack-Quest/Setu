from fastapi import APIRouter

from database.needs_db import get_open_needs
from database.volunteers_db import get_available_volunteers, get_all_volunteers
from database.ngos_db import get_all_ngos

router = APIRouter(prefix="/dashboard")


@router.get("/reports")
def get_reports_endpoint():
    from database.needs_db import get_all_needs
    from database.firestore_client import db
    
    docs = get_all_needs()
    reports = []
    
    # 1. Fetch all assignments and group by need_id
    try:
        assignments_stream = db.collection("assignments").stream()
        need_to_vols = {}  # need_id -> list of volunteer_ids
        for a in assignments_stream:
            a_data = a.to_dict()
            n_id = a_data.get("need_id")
            v_id = a_data.get("volunteer_id")
            if n_id and v_id:
                need_to_vols.setdefault(n_id, []).append(v_id)
                
        # 2. Fetch all volunteers to map id -> name
        volunteers_stream = db.collection("volunteers").stream()
        vol_dict = {}
        for v in volunteers_stream:
            v_data = v.to_dict()
            vol_dict[v.id] = {
                "id": v.id,
                "name": v_data.get("volunteer_name") or v_data.get("name") or "Volunteer"
            }
    except Exception as e:
        print("Error joining volunteers:", e)
        need_to_vols = {}
        vol_dict = {}
    
    # 3. Attach to reports
    for r in docs:
        r_id = r.get("id")
        
        assigned_vols = []
        if r_id in need_to_vols:
            for v_id in need_to_vols[r_id]:
                if v_id in vol_dict:
                    assigned_vols.append(vol_dict[v_id])
                else:
                    assigned_vols.append({"id": v_id, "name": "Unknown Volunteer"})
        
        # Normalize assignment status
        is_assigned = bool(
            len(assigned_vols) > 0 or
            r.get("assigned_to") or
            r.get("volunteer_id") or
            r.get("assignedVolunteerId") or
            r.get("assigned") == True or
            str(r.get("status")).lower() == "assigned"
        )
        
        r["assigned"] = is_assigned
        r["status"] = "assigned" if is_assigned else "unassigned"
        r["assigned_volunteers"] = assigned_vols
        
        reports.append(r)
        
    print("TOTAL REPORTS RETURNED:", len(reports))
    
    return {
        "ok": True,
        "data": reports
    }

@router.get("")
def dashboard():

    needs = get_open_needs()
    vols = get_available_volunteers()
    all_vols = get_all_volunteers()
    all_ngos = get_all_ngos()

    total_needs = len(needs)
    total_volunteers = len(all_vols)
    total_ngos = len(all_ngos)

    # 🔥 severity counts (Using safe .get() to prevent KeyErrors)
    critical = sum(1 for n in needs if n.get("severity") == "critical")
    high = sum(1 for n in needs if n.get("severity") == "high")
    medium = sum(1 for n in needs if n.get("severity") == "medium")
    low = sum(1 for n in needs if n.get("severity") == "low")

    # 🔥 FIXED flagged logic
    flagged = sum(1 for n in needs if n.get("trust_score", 100) < 50)

    # 🔥 unmatched (simple version)
    unmatched = sum(1 for n in needs if n.get("status") == "open")

    recent_need = needs[-1] if needs else None

    return {
        "total_needs": total_needs,
        "total_volunteers": total_volunteers,
        "total_ngos": total_ngos,
        "critical_cases": critical,
        "high_priority_cases": high,
        "medium_priority_cases": medium,
        "low_priority_cases": low,
        "flagged_cases": flagged,
        "unmatched_cases": unmatched,
        "recent_need": recent_need,
        "reports": needs
    }