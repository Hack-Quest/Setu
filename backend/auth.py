import os
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv

# Load from shared config folder
load_dotenv(dotenv_path="config/.env")

SECRET_TOKEN = os.getenv("SECRET_TOKEN", "hackathon-secret")

# Single shared security scheme for all routers
security = HTTPBearer(auto_error=False)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    FastAPI dependency — enforces Bearer token auth on any route.
    Raises 401 if token is missing or incorrect.
    """
    if not credentials or credentials.credentials != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid or missing token.")
    return credentials.credentials
