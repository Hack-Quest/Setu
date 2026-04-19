from fastapi import APIRouter, HTTPException
from backend.models import VolunteerRegisterInput, VolunteerLoginInput
from database.volunteers_db import register_volunteer_auth, login_volunteer

router = APIRouter()

@router.post("/register")
def register_volunteer(data: VolunteerRegisterInput):
    """Register a new volunteer with email and password"""
    try:
        result = register_volunteer_auth(
            email=data.email,
            password=data.password,
            name=data.name,
            phone=data.phone,
            location=data.location,
            skills=data.skills
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return {
            "message": "Volunteer registered successfully",
            "volunteer_id": result["volunteer_id"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
def login_volunteer_endpoint(data: VolunteerLoginInput):
    """Login volunteer with email and password"""
    try:
        result = login_volunteer(data.email, data.password)
        
        if "error" in result:
            raise HTTPException(status_code=401, detail=result["error"])
        
        return {
            "message": "Login successful",
            "volunteer_id": result["volunteer_id"],
            "name": result["name"],
            "email": result["email"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
