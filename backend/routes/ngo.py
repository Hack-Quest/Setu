from fastapi import APIRouter, HTTPException, Depends
from backend.models import NGOInput
from database.ngos_db import save_ngo, get_ngo
from backend.auth import verify_token
from database.geocoding import get_coordinates

router = APIRouter(prefix="/ngo", tags=["NGO"])

@router.post("/register")
def register_ngo(data: NGOInput, token: str = Depends(verify_token)):
    """Webhook/Forms endpoint for NGO registration"""
    try:
        coords = get_coordinates(data.location) or {"lat": 0.0, "lng": 0.0}
        ngo_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
        ngo_dict["lat"] = coords["lat"]
        ngo_dict["lng"] = coords["lng"]
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
