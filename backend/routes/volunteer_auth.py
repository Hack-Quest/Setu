from fastapi import APIRouter, HTTPException
from backend.models import VolunteerRegisterInput, VolunteerLoginInput, SendOTPInput, VerifyOTPInput
from database.volunteers_db import register_volunteer_auth, login_volunteer
from backend.auth import SECRET_TOKEN
import random
from backend.email_utils import send_otp_email
from database.otp_db import save_otp, verify_otp_in_db
from database.ngos_db import get_ngo_by_email
from database.firestore_client import db
from google.cloud.firestore_v1.base_query import FieldFilter

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
            "volunteer_id": result["volunteer_id"],
            "token": SECRET_TOKEN
        }
    except HTTPException:
        raise
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
            "email": result["email"],
            "token": SECRET_TOKEN
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-otp")
def send_otp_endpoint(data: SendOTPInput):
    """Generate and send an OTP to the user's email."""
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Save OTP to database
    save_otp(data.email, otp)
    
    # Send email

    success = send_otp_email(data.email, otp)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
        
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp")
def verify_otp_endpoint(data: VerifyOTPInput):
    """Verify OTP and determine user role for login."""
    try:
        print("VERIFY OTP INPUT:", data.model_dump() if hasattr(data, "model_dump") else data.dict())
        
        is_valid = verify_otp_in_db(data.email, data.otp)
        if not is_valid:
            raise HTTPException(status_code=401, detail="Invalid or expired OTP")
            
        email = data.email.strip().lower()
        
        # Check if NGO
        ngo = get_ngo_by_email(email)
        if ngo:
            return {
                "token": SECRET_TOKEN,
                "role": "ngo",
                "id": ngo["id"]
            }
            
        # 🔍 Fetch volunteer from DB
        volunteers = db.collection("volunteers_auth").where(filter=FieldFilter("email", "==", email)).get()
        print("VOLUNTEER QUERY RESULT:", len(volunteers))
        
        volunteer_id = None
        if volunteers and len(volunteers) > 0:
            volunteer_id = volunteers[0].id
            
        if volunteer_id:
            return {
                "token": SECRET_TOKEN,
                "role": "volunteer",
                "id": volunteer_id,
                "volunteer_id": volunteer_id,
                "email": email
            }
            
        # User does not exist, redirect to registration
        return {
            "token": SECRET_TOKEN,
            "role": "new_user",
            "id": None,
            "volunteer_id": None
        }

    except HTTPException:
        raise
    except Exception as e:
        print("VERIFY OTP ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")
