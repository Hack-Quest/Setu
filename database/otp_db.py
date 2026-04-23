from database.firestore_client import db
from google.cloud.firestore_v1.base_query import FieldFilter
from datetime import datetime, timezone, timedelta

def save_otp(email: str, otp: str, expires_in_minutes: int = 10) -> bool:
    """Save the OTP for an email with an expiration time."""
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    
    # Store in "otps" collection, using email as the document ID for simplicity 
    # (or generating a new doc). Let's use the email so it overwrites previous OTPs.
    doc_ref = db.collection("otps").document(email)
    doc_ref.set({
        "otp": otp,
        "expires_at": expires_at.isoformat(),
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    print(f"🔑 OTP saved for {email}")
    return True

def verify_otp_in_db(email: str, otp: str) -> bool:
    """Check if the given OTP is valid and not expired."""
    doc_ref = db.collection("otps").document(email)
    doc = doc_ref.get()
    
    if not doc.exists:
        return False
        
    data = doc.to_dict()
    stored_otp = data.get("otp")
    expires_at_str = data.get("expires_at")
    
    if stored_otp != otp:
        return False
        
    if expires_at_str:
        try:
            expires_at = datetime.fromisoformat(expires_at_str)
            if datetime.now(timezone.utc) > expires_at:
                print(f"⚠️ OTP for {email} expired.")
                return False
        except ValueError:
            pass
            
    # Valid OTP, delete it so it cannot be reused
    doc_ref.delete()
    print(f"✅ OTP verified and deleted for {email}")
    return True