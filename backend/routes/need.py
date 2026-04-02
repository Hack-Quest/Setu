from fastapi import APIRouter, Header, HTTPException
from backend.models import NeedInput

router = APIRouter()

# 🧠 In-memory storage
needs_storage = []

# 🔐 Security
SECRET_TOKEN = "hackathon-secret"

def verify_token(auth: str):
    if auth != f"Bearer {SECRET_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")

# 🔴 MOCK FUNCTIONS (temporary)

def process_text(description):
    desc = description.lower()

    if "food" in desc:
        return {"category": "food", "severity": "high"}
    elif "medical" in desc:
        return {"category": "medical", "severity": "high"}
    elif "water" in desc:
        return {"category": "water", "severity": "medium"}
    else:
        return {"category": "general", "severity": "low"}


def get_coordinates(location):
    return {"lat": 28.61, "lng": 77.20}


def save_need(data):
    print("Mock DB Save:", data)


# 🔥 MAIN ROUTE
@router.post("/need")
def create_need(data: NeedInput, authorization: str = Header(None)):

    verify_token(authorization)

    try:
        print("Incoming Data:", data)

        ai_result = process_text(data.description)
        coords = get_coordinates(data.location)

        final_data = {
            "id": len(needs_storage) + 1,
            "description": data.description,
            "category": ai_result["category"],
            "severity": ai_result["severity"],
            "lat": coords["lat"],
            "lng": coords["lng"],
            "disaster_type": data.disaster_type,
            "help_needed": data.help_needed,
            "status": "pending"
        }

        save_need(final_data)
        needs_storage.append(final_data)

        print("Final Data:", final_data)

        return final_data

    except Exception as e:
        return {"error": str(e)}