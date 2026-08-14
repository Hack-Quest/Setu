import os
from datetime import datetime, timezone, timedelta
import jwt
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load from shared config folder
load_dotenv(dotenv_path="config/.env")

SECRET_TOKEN = os.getenv("SECRET_TOKEN")
if not SECRET_TOKEN:
    raise RuntimeError("SECRET_TOKEN is not set. Add it to config/.env.")

JWT_SECRET = os.getenv("JWT_SECRET", SECRET_TOKEN)
JWT_ALGORITHM = "HS256"

# Single shared security scheme for all routers
security = HTTPBearer(auto_error=False)


def generate_token(user_id: str, role: str, email: str) -> str:
    """
    Generate a signed JWT token for a user session.
    Expires in 24 hours.
    """
    payload = {
        "sub": user_id,
        "uid": user_id,
        "role": role,
        "email": email,
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    """
    FastAPI dependency — enforces Bearer token auth on any route.
    Supports standard JWT user sessions and static system SECRET_TOKEN.
    Raises 401 if token is missing or incorrect.
    """
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authentication credentials.")

    token = credentials.credentials

    # 1. Fallback for testing / system cron matching (using static SECRET_TOKEN)
    if token == SECRET_TOKEN:
        return {
            "uid": "system",
            "role": "system",
            "email": "system@setu.org"
        }

    # 2. Verify and decode standard JWT user session
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired. Please login again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Access denied.")

