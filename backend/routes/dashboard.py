from fastapi import APIRouter, Depends
from backend.auth import verify_token

from database.needs_db import get_open_needs, get_all_needs
from database.volunteers_db import get_available_volunteers, get_all_volunteers
from database.ngos_db import get_all_ngos
from database.postgres_client import get_db_cursor

router = APIRouter(prefix="/dashboard")


@router.get("/reports")
def get_reports_endpoint():
    """
    Returns all disaster needs reports joined with assigned volunteer metadata,
    specifically serializing volunteer_lat and volunteer_lng for the map UI.
    """
    docs = get_all_needs()
    reports = []
    
    # 1. Fetch all assignments and volunteer details
    try:
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT id, need_id, volunteer_id, status, resolved_at FROM assignments")
            assignments_rows = cur.fetchall()
            
            cur.execute("SELECT id, name, phone, lat, lng FROM volunteers")
            volunteers_rows = cur.fetchall()

        need_to_vols = {}  # need_id -> list of volunteer_ids
        for a in assignments_rows:
            n_id = a.get("need_id")
            v_id = a.get("volunteer_id")
            if n_id and v_id:
                # Prioritize active/unresolved assignments
                if a.get("status") == "assigned" or a.get("resolved_at") is None:
                    need_to_vols.setdefault(n_id, []).append(v_id)
                elif n_id not in need_to_vols:
                    need_to_vols.setdefault(n_id, []).append(v_id)
                
        # 2. Map volunteer details including geolocation coordinates
        vol_dict = {}
        for v in volunteers_rows:
            v_id = v.get("id")
            vol_dict[v_id] = {
                "id": v_id,
                "name": v.get("name") or "Volunteer",
                "phone": v.get("phone") or "",
                "lat": float(v["lat"]) if v.get("lat") is not None else None,
                "lng": float(v["lng"]) if v.get("lng") is not None else None,
            }
    except Exception as e:
        print("Error joining volunteers for dashboard reports:", e)
        need_to_vols = {}
        vol_dict = {}
    
    # 3. Attach volunteer coordinates and assignment details to each report
    for r in docs:
        r_id = r.get("id")
        
        assigned_vols = []
        if r_id in need_to_vols:
            for v_id in need_to_vols[r_id]:
                if v_id in vol_dict:
                    assigned_vols.append(vol_dict[v_id])
                else:
                    assigned_vols.append({
                        "id": v_id,
                        "name": "Unknown Volunteer",
                        "phone": "",
                        "lat": None,
                        "lng": None
                    })
        
        # Normalize assignment status
        is_assigned = bool(
            len(assigned_vols) > 0 or
            r.get("assigned_to") or
            r.get("volunteer_id") or
            r.get("assignedVolunteerId") or
            r.get("assigned") is True or
            str(r.get("status")).lower() == "assigned"
        )
        
        r["assigned"] = is_assigned
        current_status = str(r.get("status") or "").lower()
        if current_status not in ["resolved", "rejected"]:
            r["status"] = "assigned" if is_assigned else "open"
        r["assigned_volunteers"] = assigned_vols
        
        # Populate top-level fields required by frontend map.html
        if assigned_vols:
            primary_vol = assigned_vols[0]
            r["volunteer_id"] = primary_vol.get("id")
            r["volunteer_name"] = primary_vol.get("name")
            r["volunteer_phone"] = primary_vol.get("phone")
            r["volunteer_lat"] = primary_vol.get("lat")
            r["volunteer_lng"] = primary_vol.get("lng")
        else:
            r["volunteer_id"] = None
            r["volunteer_name"] = None
            r["volunteer_phone"] = None
            r["volunteer_lat"] = None
            r["volunteer_lng"] = None
        
        reports.append(r)
        
    print("TOTAL REPORTS RETURNED:", len(reports))
    return reports


@router.get("")
def dashboard():
    needs = get_open_needs()
    vols = get_available_volunteers()
    all_vols = get_all_volunteers()
    all_ngos = get_all_ngos()

    total_needs = len(needs)
    total_volunteers = len(all_vols)
    total_ngos = len(all_ngos)

    critical = sum(1 for n in needs if str(n.get("severity", "")).lower() == "critical")
    high = sum(1 for n in needs if str(n.get("severity", "")).lower() == "high")
    medium = sum(1 for n in needs if str(n.get("severity", "")).lower() == "medium")
    low = sum(1 for n in needs if str(n.get("severity", "")).lower() == "low")

    flagged = sum(1 for n in needs if n.get("trust_score", 100) < 50)
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