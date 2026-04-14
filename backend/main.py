from fastapi import FastAPI, Request
import requests

# Routers
from backend.routes.need import router as need_router
from backend.routes.volunteer import router as volunteer_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router

# Models
from backend.models import NeedInput

# Volunteer helpers
from database.volunteers_db import save_volunteer
from database.geocoding import get_coordinates

app = FastAPI()


# 🏠 Home Route
@app.get("/")
def home():
    return {"message": "Backend is running"}


# 💚 Health Check
@app.get("/health")
def health():
    return {"status": "ok"}


# 🔗 WEBHOOK (Google Form → Need)
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        mapped_data = {
            "reporter_name": data.get("name", "Unknown Form User"),
            "reporter_phone": data.get("phone", "0000000000"),
            "description": data.get("description", ""),
            "location": data.get("address", "Unknown Location"),
            "disaster_type": data.get("disaster_type", "Not Specified"),
            "help_needed": data.get("help_needed", "Not Specified")
        }

        # 🔥 Proper API call to /need
        response = requests.post(
            "http://127.0.0.1:8000/need",
            json=mapped_data,
            headers={"Authorization": "Bearer hackathon-secret"}
        )

        return {
            "message": "Webhook processed successfully",
            "data": response.json()
        }

    except Exception as e:
        print("❌ Webhook Error:", e)
        return {"error": str(e)}


# 🔗 VOLUNTEER WEBHOOK (Google Form → Volunteer DB)
@app.post("/volunteer_webhook")
async def volunteer_webhook(request: Request):
    try:
        data = await request.json()

        # 🌍 Safe geocoding
        coords = get_coordinates(data.get("location", "")) or {"lat": 0, "lng": 0}

        mapped_volunteer = {
            "name": data.get("volunteer_name", "Unknown Form Volunteer"),
            "phone": data.get("phone", "0000000000"),
            "skills": [
                skill.strip().lower()
                for skill in data.get("skills", "").split(",")
            ] if data.get("skills") else [],
            "lat": coords.get("lat", 0),
            "lng": coords.get("lng", 0)
        }

        print("📥 Incoming Volunteer:", mapped_volunteer)

        doc_id = save_volunteer(mapped_volunteer)

        return {
            "message": "Volunteer registered successfully",
            "id": doc_id
        }

    except Exception as e:
        print("❌ Volunteer Webhook Error:", e)
        return {"error": str(e)}


# 📦 Include Routers
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(match_router)
app.include_router(dashboard_router)


