from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.models import NeedInput

# 🔥 Import Coder's function
from ai_processing.gemini_processor import process_need_text

router = APIRouter()

# 🧠 In-memory storage
needs_storage = []

# 🔐 Security
SECRET_TOKEN = "hackathon-secret"
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if credentials.credentials != SECRET_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return credentials.credentials


# 🔴 TEMP (until Animesh ready)
def get_coordinates(location):
    return {"lat": 28.61, "lng": 77.20}

def save_need(data):
    print("Mock DB Save:", data)


# 🔥 MAIN ROUTE
@router.post("/need")
def create_need(data: NeedInput, token: str = Depends(verify_token)):

    try:
        print("Incoming Data:", data)

        # 🧠 STEP 1 — AI PROCESSING (Gemini)
        ai_result = process_need_text(data.description)

        # ⚠️ SAFETY CHECK (VERY IMPORTANT)
        if not isinstance(ai_result, dict):
            raise Exception("AI did not return JSON")

        category = ai_result.get("category", "general")
        severity = ai_result.get("severity", "low")

        # 🌍 STEP 2 — LOCATION (mock for now)
        coords = get_coordinates(data.location)

        # 🧩 STEP 3 — FINAL DATA
        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": category,
            "severity": severity,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "pending"
        }

        # 💾 STEP 4 — SAVE
        save_need(final_data)
        needs_storage.append(final_data)

        print("Final Data:", final_data)

        return final_data

    except Exception as e:
        print("Error:", e)

        # 🔴 FALLBACK (important for demo safety)
        return {
            "error": str(e),
            "message": "Fallback: using default values",
            "category": "general",
            "severity": "low"
        }