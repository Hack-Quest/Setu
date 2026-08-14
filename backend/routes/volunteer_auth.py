from fastapi import APIRouter, HTTPException
from backend.models import VolunteerRegisterInput, VolunteerLoginInput, SendOTPInput, VerifyOTPInput
from database.volunteers_db import register_volunteer_auth, login_volunteer
from backend.auth import generate_token, SECRET_TOKEN
import random
import threading
from datetime import datetime, timezone, timedelta
from backend.email_utils import send_otp_email
from database.otp_db import save_otp, verify_otp_in_db
from database.ngos_db import get_ngo_by_email
from database.postgres_client import get_db_cursor

router = APIRouter()

# Thread-safe in-memory tracking for rate limiting and attempt caps
_lock = threading.Lock()
_verify_attempts = {}  # email -> {"count": int, "blocked_until": datetime}
_last_sent = {}        # email -> last_sent_datetime


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
        
        jwt_token = generate_token(result["volunteer_id"], "volunteer", data.email.strip().lower())
        return {
            "message": "Volunteer registered successfully",
            "volunteer_id": result["volunteer_id"],
            "token": jwt_token
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
        
        jwt_token = generate_token(result["volunteer_id"], "volunteer", data.email.strip().lower())
        return {
            "message": "Login successful",
            "volunteer_id": result["volunteer_id"],
            "name": result["name"],
            "email": result["email"],
            "token": jwt_token
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-otp")
def send_otp_endpoint(data: SendOTPInput):
    """Generate and send an OTP to the user's email."""
    email = data.email.strip().lower()
    
    # 1. Enforce send rate limiting (60 seconds resend cooldown)
    now = datetime.now(timezone.utc)
    with _lock:
        last_sent_time = _last_sent.get(email)
        if last_sent_time and (now - last_sent_time) < timedelta(seconds=60):
            wait_seconds = int(60 - (now - last_sent_time).total_seconds())
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait_seconds} seconds before requesting another OTP."
            )
        _last_sent[email] = now
        
        # Reset attempt counter when a new OTP is requested/sent
        if email in _verify_attempts:
            _verify_attempts[email] = {"count": 0, "blocked_until": None}
            
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Save OTP to database
    save_otp(email, otp)
    
    # Send email
    success = send_otp_email(email, otp)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to send OTP email")
        
    return {"message": "OTP sent successfully"}

@router.post("/verify-otp")
def verify_otp_endpoint(data: VerifyOTPInput):
    """Verify OTP and determine user role for login."""
    try:
        print("VERIFY OTP INPUT:", data.model_dump() if hasattr(data, "model_dump") else data.dict())
        email = data.email.strip().lower()
        otp = data.otp.strip()
        
        now = datetime.now(timezone.utc)
        
        # 1. Check if email is currently blocked
        with _lock:
            record = _verify_attempts.get(email)
            if record and record.get("blocked_until") and now < record["blocked_until"]:
                block_remaining = int((record["blocked_until"] - now).total_seconds())
                raise HTTPException(
                    status_code=429,
                    detail=f"Account temporarily locked. Please request a new OTP in {block_remaining} seconds."
                )
        
        # 2. Verify OTP in database
        is_valid = verify_otp_in_db(email, otp)
        if not is_valid:
            with _lock:
                record = _verify_attempts.setdefault(email, {"count": 0, "blocked_until": None})
                record["count"] += 1
                attempts_left = 5 - record["count"]
                
                if record["count"] >= 5:
                    record["blocked_until"] = now + timedelta(minutes=15)
                    # Force delete/invalidate OTP in database
                    with get_db_cursor(commit=True) as cur:
                        cur.execute("DELETE FROM otps WHERE email = %s", (email,))
                    
                    raise HTTPException(
                        status_code=429,
                        detail="Too many failed attempts. OTP has been invalidated. Please request a new OTP."
                    )
                else:
                    raise HTTPException(
                        status_code=401,
                        detail=f"Invalid or expired OTP. {attempts_left} attempts remaining."
                    )
                    
        # On success, clear verification attempts
        with _lock:
            if email in _verify_attempts:
                _verify_attempts.pop(email)
                
        # Determine role and return signed JWT
        # Check if NGO
        ngo = get_ngo_by_email(email)
        if ngo:
            ngo_name = ngo.get("ngo_name") or ngo.get("organization_name") or ngo.get("organization") or "Unnamed NGO"
            owner_name = ngo.get("owner_name") or ngo.get("name") or "Owner"
            jwt_token = generate_token(ngo["id"], "ngo", email)
            return {
                "token": jwt_token,
                "role": "ngo",
                "id": ngo["id"],
                "ngo_name": ngo_name,
                "owner_name": owner_name,
                "email": ngo.get("email", email),
                "verified": ngo.get("verified", False),
                "description": ngo.get("description", "")
            }
            
        # Check if Volunteer
        # 🔍 Fetch volunteer from volunteers_auth table
        with get_db_cursor(commit=False) as cur:
            cur.execute("SELECT id FROM volunteers_auth WHERE email = %s", (email,))
            auth_vol = cur.fetchone()

        volunteer_id = None
        if auth_vol:
            volunteer_id = auth_vol.get("id")
            print("VOLUNTEERS_AUTH QUERY RESULT: 1")
        else:
            print("VOLUNTEERS_AUTH QUERY RESULT: 0")
            # 🔁 Fallback: check volunteers table
            with get_db_cursor(commit=False) as cur:
                cur.execute("SELECT id FROM volunteers WHERE email = %s", (email,))
                form_vol = cur.fetchone()
            if form_vol:
                volunteer_id = form_vol.get("id")
                print("VOLUNTEERS (FORM) QUERY RESULT: 1")
            else:
                print("VOLUNTEERS (FORM) QUERY RESULT: 0")

        print("VOLUNTEER ID:", volunteer_id)

        if not volunteer_id:
            return {
                "ok": False,
                "role": "new_user",
                "message": "Email not registered as a volunteer. Please register first."
            }

        jwt_token = generate_token(volunteer_id, "volunteer", email)
        return {
            "token": jwt_token,
            "role": "volunteer",
            "id": volunteer_id,
            "volunteer_id": volunteer_id,
            "email": email
        }

    except HTTPException:
        raise
    except Exception as e:
        print("VERIFY OTP ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Internal server error")

