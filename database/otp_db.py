import logging
from database.postgres_client import get_db_cursor
from datetime import datetime, timezone, timedelta

def save_otp(email: str, otp: str, expires_in_minutes: int = 10) -> bool:
    """Save the OTP for an email with an expiration time."""
    email_clean = email.strip().lower()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    created_at = datetime.now(timezone.utc)

    with get_db_cursor(commit=True) as cur:
        cur.execute(
            """
            INSERT INTO otps (email, otp, expires_at, created_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (email) DO UPDATE SET 
                otp = EXCLUDED.otp,
                expires_at = EXCLUDED.expires_at,
                created_at = EXCLUDED.created_at
            """,
            (email_clean, otp, expires_at, created_at)
        )
    print(f"[INFO] OTP saved for {email_clean}")
    return True


def verify_otp_in_db(email: str, otp: str) -> bool:
    """Check if the given OTP is valid and not expired."""
    email_clean = email.strip().lower()
    
    with get_db_cursor(commit=False) as cur:
        cur.execute("SELECT * FROM otps WHERE email = %s", (email_clean,))
        row = cur.fetchone()
        
    if not row:
        return False
        
    stored_otp = row.get("otp")
    expires_at = row.get("expires_at")
    
    if stored_otp != otp:
        return False
        
    if expires_at:
        # If it's a string, try parsing it, though psycopg2 returns datetime objects for TIMESTAMPTZ
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except ValueError:
                logging.warning(
                    f"OTP for {email_clean} has a malformed expires_at value: {expires_at!r}. "
                    "Treating as expired."
                )
                return False
                
        # Normalise naive datetimes to UTC
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
            
        if datetime.now(timezone.utc) > expires_at:
            print(f"[WARN] OTP for {email_clean} expired.")
            return False
            
    # Valid OTP, delete it so it cannot be reused (single-use behavior)
    with get_db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM otps WHERE email = %s", (email_clean,))
        
    print(f"[OK] OTP verified and deleted for {email_clean}")
    return True