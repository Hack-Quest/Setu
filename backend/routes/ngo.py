from fastapi import APIRouter, HTTPException
from backend.models import NGOInput
from database.ngos_db import save_ngo, get_ngo

router = APIRouter(prefix="/ngo", tags=["NGO"])

@router.post("/register")
def register_ngo(data: NGOInput):
    """Webhook/Forms endpoint for NGO registration"""
    try:
        ngo_dict = data.model_dump() if hasattr(data, "model_dump") else data.dict()
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
