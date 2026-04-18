from fastapi import FastAPI, Request, BackgroundTasks  # ✅ FIX 1: Added BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import requests
import os

# Routers
from backend.routes.need import router as need_router, create_need
from backend.models import NeedInput
from backend.routes.volunteer import router as volunteer_router
from backend.routes.volunteer_auth import router as volunteer_auth_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.assignment import router as assignment_router
from backend.routes.ngo import router as ngo_router

# Volunteer helpers
from database.volunteers_db import save_volunteer
from database.geocoding import get_coordinates

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
@limiter.limit("5/minute")
def webhook(request: Request, payload: dict, background_tasks: BackgroundTasks):  # ✅ Removed 'async', changed Request to dict
    try:
        # ✅ No more 'await request.json()' needed! FastAPI parses it automatically.
        mapped_data = {
            "reporter_name": payload.get("name", "Unknown"),
            "reporter_phone": payload.get("phone", "0000000000"),
            "description": payload.get("description", ""),
            "location": payload.get("address", "Unknown Location"),
            "disaster_type": payload.get("disaster_type", "Not Specified"),
            "help_needed": payload.get("help_needed", "Not Specified"),
        }

        # Direct function call
        need_input = NeedInput(**mapped_data)
        
        # Adding flush=True to force Python to print immediately before moving on
        print("🚀 [SYSTEM] Routing to Core AI Engine...", flush=True) 
        
        result = create_need(data=need_input, background_tasks=background_tasks, token="webhook_override")

        return {"message": "Webhook processed successfully", "data": result}

    except Exception as e:
        print("❌ Webhook Error:", e, flush=True)
        return {"error": str(e)}

# 🔗 VOLUNTEER WEBHOOK (FIXED)
@app.post("/volunteer_webhook")
@limiter.limit("5/minute")
def volunteer_webhook(request: Request, payload: dict):  # ✅ Removed 'async'
    try:
        coords = get_coordinates(payload.get("location", "")) or {"lat": 0, "lng": 0}

        mapped_volunteer = {
            "name": payload.get("volunteer_name", "Unknown"),
            "phone": payload.get("phone", "0000000000"),
            "skills": (
                [skill.strip().lower() for skill in payload.get("skills", "").split(",")]
                if payload.get("skills")
                else []
            ),
            "lat": coords["lat"],
            "lng": coords["lng"],
            "ngo_id": payload.get("ngo_id", None)
        }

        # Validate NGO and grant Tier 1 status if verified
        if mapped_volunteer.get("ngo_id"):
            from database.ngos_db import get_ngo
            ngo = get_ngo(mapped_volunteer["ngo_id"])
            if ngo and ngo.get("verified") is True:
                mapped_volunteer["ngo_verified"] = True

        print("📥 Incoming Volunteer:", mapped_volunteer, flush=True)

        doc_id = save_volunteer(mapped_volunteer)

        return {"message": "Volunteer registered successfully", "id": doc_id}

    except Exception as e:
        print("❌ Volunteer Webhook Error:", e, flush=True)
        return {"error": str(e)}


# 📦 Routers
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(volunteer_auth_router)
app.include_router(match_router)
app.include_router(dashboard_router)
app.include_router(assignment_router)  # ✅ FIX 3: Added missing router
app.include_router(ngo_router)