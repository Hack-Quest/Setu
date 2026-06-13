import sys
import io
import traceback

# Force UTF-8 stdout/stderr on Windows to prevent UnicodeEncodeError with emojis
if sys.platform == "win32" and type(sys.stdout).__name__ == "TextIOWrapper":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.platform == "win32" and type(sys.stderr).__name__ == "TextIOWrapper":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from typing import List, Dict
import os
import firebase_admin
from firebase_admin import credentials
from fastapi import (
    FastAPI, Request, BackgroundTasks, WebSocket, WebSocketDisconnect
)
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

# Routers
from backend.routes.need import router as need_router, process_and_save_need
from backend.models import NeedInput
from backend.routes.volunteer import router as volunteer_router
from backend.routes.volunteer_auth import router as volunteer_auth_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.assignment import router as assignment_router
from backend.routes.ngo import router as ngo_router
from backend.routes.stats import router as stats_router

# Helpers
from database.volunteers_db import save_volunteer
from database.geocoding import get_coordinates
from database.ngos_db import get_ngo

load_dotenv(dotenv_path="config/.env")

# 🔌 WebSocket Manager
class WebSocketManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast_json(self, data: dict):
        stale_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception as e:
                stale_connections.append(connection)
        for stale in stale_connections:
            self.disconnect(stale)

manager = WebSocketManager()
app = FastAPI()

# 🔒 Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 🔥 CORS - Allows your local frontend to talk to this live backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔌 WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# 🏠 Health Checks
from fastapi.responses import FileResponse

@app.get("/")
def home(request: Request):
    if "text/html" in request.headers.get("accept", ""):
        if os.path.exists("frontendnew/landing.html"):
            return FileResponse("frontendnew/landing.html")
    return {"message": "Setu Backend Active", "env": "Cloud Run"}

@app.get("/health")
def health():
    return {"status": "ok", "database": "connected"}


@app.get("/config/public")
def public_config():
    google_maps_api_key = (
        os.getenv("GOOGLE_MAPS_KEY", "").strip()
        or os.getenv("GOOGLE_MAPS_API_KEY", "").strip()
    )

    if not google_maps_api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "Google Maps API key is not configured"}
        )

    return {"google_maps_api_key": google_maps_api_key}

# 🔗 NEED WEBHOOK
@app.post("/webhook")
@limiter.limit("5/minute")
async def webhook(request: Request, payload: Dict, background_tasks: BackgroundTasks):
    try:
        print(f"📥 RAW Need Webhook payload: {payload}", flush=True)
        
        def safe_float(val):
            try:
                if val is None or str(val).strip() == "":
                    return 0.0
                return float(val)
            except (ValueError, TypeError):
                return 0.0

        # Concatenate everything into description so the AI doesn't miss the full story
        # if the user typed their emergency into the wrong box.
        full_desc = f"Report: {payload.get('description', '')} | Details: {payload.get('location', '')} | Help: {payload.get('help_needed', '')}"

        mapped_data = {
            "reporter_name": payload.get("reporter_name", "Unknown"),
            "reporter_phone": payload.get("reporter_phone", "0000000000"),
            "description": full_desc,
            # Fallback to help_needed if location is a huge paragraph or empty
            "location_text": payload.get("location") or payload.get("help_needed") or payload.get("address") or "Unknown Location",
            "lat": safe_float(payload.get("lat") or payload.get("Latitude") or payload.get("latitude")),
            "lng": safe_float(payload.get("lng") or payload.get("Longitude") or payload.get("longitude")),
            "disaster_type": payload.get("disaster_type", "Not Specified"),
            "help_needed": payload.get("help_needed", "Not Specified"),
        }
        need_input = NeedInput(**mapped_data)
        print("🚀 Routing to AI Engine...", flush=True)
        result = process_and_save_need(need_input, background_tasks)
        return {"message": "Webhook processed", "data": result}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# 🔗 VOLUNTEER WEBHOOK (Updated to capture Email)
@app.post("/volunteer_webhook")
@limiter.limit("5/minute")
async def webhook_ngo_register_alias(request: Request, payload: Dict, background_tasks: BackgroundTasks):
    # If a form hits this accidentally, we still process it as an SOS/Need
    try:
        mapped_volunteer = {
            "name": payload.get("volunteer_name", "Unknown"),
            "email": payload.get("email", "no-email@setu.com"),  # ✅ Field added to fix the "test" email issue
            "phone": payload.get("phone", "0000000000"),
            "skills": (
                [skill.strip().lower() for skill in payload.get("skills", "").split(",")]
                if payload.get("skills")
                else []
            ),
            "location": payload.get("location", ""),
            "ngo_id": payload.get("ngo_id", None),
            "available": True,
            "active_assignments": 0
        }

        # NGO verification
        if mapped_volunteer.get("ngo_id"):
            ngo = get_ngo(mapped_volunteer["ngo_id"])
            if ngo and ngo.get("verified"):
                mapped_volunteer["ngo_verified"] = True

        print(f"📥 Incoming Volunteer: {mapped_volunteer['email']}", flush=True)

        doc_id = save_volunteer(mapped_volunteer)

        # 🔥 Broadcast update via WebSocket
        await manager.broadcast_json({
            "type": "NEW_VOLUNTEER",
            "data": mapped_volunteer
        })

        return {"message": "Volunteer registered", "id": doc_id}

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# 📦 Include all specialized routers
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(volunteer_auth_router, prefix="/auth")
app.include_router(match_router)
app.include_router(dashboard_router)
app.include_router(assignment_router)
app.include_router(ngo_router)
app.include_router(stats_router)

from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory="frontendnew", html=True), name="static")