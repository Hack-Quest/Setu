from fastapi import FastAPI, Request, BackgroundTasks
import requests
import os

# Routers
from backend.routes.need import router as need_router, process_and_save_need
from backend.models import NeedInput
from backend.routes.volunteer import router as volunteer_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.assignment import router as assignment_router

# Volunteer helpers
from database.volunteers_db import save_volunteer
from database.geocoding import get_coordinates

app = FastAPI()


# 🏠 Home
@app.get("/")
def home():
    return {"message": "Backend is running"}


# 💚 Health
@app.get("/health")
def health():
    return {"status": "ok"}


# 🔗 NEED WEBHOOK (FIXED)
@app.post("/webhook")
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()

        mapped_data = {
            "reporter_name": data.get("name", "Unknown"),
            "reporter_phone": data.get("phone", "0000000000"),
            "description": data.get("description", ""),
            "location": data.get("address", "Unknown Location"),
            "disaster_type": data.get("disaster_type", "Not Specified"),
            "help_needed": data.get("help_needed", "Not Specified")
        }

        # ✅ CORRECT: Call service logic directly instead of HTTP self-calling
        need_input = NeedInput(**mapped_data)
        result = process_and_save_need(need_input, background_tasks)

        return {
            "message": "Webhook processed successfully",
            "data": result
        }

    except Exception as e:
        print("❌ Webhook Error:", e)
        return {"error": str(e)}


# 🔗 VOLUNTEER WEBHOOK (FIXED)
@app.post("/volunteer_webhook")
async def volunteer_webhook(request: Request):
    try:
        data = await request.json()

        coords = get_coordinates(data.get("location", "")) or {"lat": 0, "lng": 0}

        mapped_volunteer = {
            "name": data.get("volunteer_name", "Unknown"),
            "phone": data.get("phone", "0000000000"),
            "skills": [
                skill.strip().lower()
                for skill in data.get("skills", "").split(",")
            ] if data.get("skills") else [],
            "lat": coords["lat"],
            "lng": coords["lng"]
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


# 📦 Routers
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(match_router)
app.include_router(dashboard_router)
app.include_router(assignment_router)