from typing import List, Dict
import os
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
from backend.routes.need import router as need_router, create_need
from backend.models import NeedInput
from backend.routes.volunteer import router as volunteer_router
from backend.routes.volunteer_auth import router as volunteer_auth_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.assignment import router as assignment_router
from backend.routes.ngo import router as ngo_router

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
                print(f"WebSocket Error: {e}", flush=True)
                stale_connections.append(connection)
        
        for stale in stale_connections:
            self.disconnect(stale)


manager = WebSocketManager()

app = FastAPI()

# 🔒 Rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

DEFAULT_ALLOWED_ORIGINS = [
    "http://127.0.0.1:5500",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

raw_allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
if raw_allowed_origins.strip():
    allowed_origins = [
        origin.strip()
        for origin in raw_allowed_origins.split(",")
        if origin.strip()
    ]
else:
    allowed_origins = DEFAULT_ALLOWED_ORIGINS

# 🔥 CORS (hardened defaults)
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

# 🏠 Home
@app.get("/")
def home():
    return {"message": "Backend is running"}

# 💚 Health
@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/config/public")
def public_config():
    google_maps_api_key = os.getenv("GOOGLE_MAPS_API_KEY", "").strip()

    if not google_maps_api_key:
        return JSONResponse(
            status_code=503,
            content={"error": "GOOGLE_MAPS_API_KEY is not configured on server"}
        )

    return {"google_maps_api_key": google_maps_api_key}

# 🔗 NEED WEBHOOK
@app.post("/webhook")
@limiter.limit("5/minute")
async def webhook(
    request: Request,
    payload: Dict,
    background_tasks: BackgroundTasks
):
    try:
        mapped_data = {
            "reporter_name": payload.get("name", "Unknown"),
            "reporter_phone": payload.get("phone", "0000000000"),
            "description": payload.get("description", ""),
            "location": payload.get("address", "Unknown Location"),
            "disaster_type": payload.get("disaster_type", "Not Specified"),
            "help_needed": payload.get("help_needed", "Not Specified"),
        }

        need_input = NeedInput(**mapped_data)

        print("🚀 Routing to AI Engine...", flush=True)

        result = await create_need(
            data=need_input,
            background_tasks=background_tasks,
            token="webhook_override"
        )

        return {"message": "Webhook processed", "data": result}

    except Exception as e:
        print("❌ Webhook Error:", e, flush=True)
        return {"error": str(e)}

# 🔗 VOLUNTEER WEBHOOK
@app.post("/volunteer_webhook")
@limiter.limit("5/minute")
async def volunteer_webhook(request: Request, payload: Dict):
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

        # NGO verification
        if mapped_volunteer.get("ngo_id"):
            ngo = get_ngo(mapped_volunteer["ngo_id"])
            if ngo and ngo.get("verified"):
                mapped_volunteer["ngo_verified"] = True

        print("📥 Incoming Volunteer:", mapped_volunteer, flush=True)

        doc_id = save_volunteer(mapped_volunteer)

        # 🔥 Broadcast update via WebSocket
        await manager.broadcast_json({
            "type": "NEW_VOLUNTEER",
            "data": mapped_volunteer
        })

        return {"message": "Volunteer registered", "id": doc_id}

    except Exception as e:
        print("❌ Volunteer Error:", e, flush=True)
        return {"error": str(e)}

# 📦 Routers
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(volunteer_auth_router, prefix="/auth")
app.include_router(match_router)
app.include_router(dashboard_router)
app.include_router(assignment_router)
app.include_router(ngo_router)