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
@app.get("/")
def home():
    return {"message": "Setu Backend Active", "env": "Cloud Run"}

@app.get("/health")
def health():
    return {"status": "ok", "database": "connected"}

# 🔗 DISASTER WEBHOOK (Primary SOS entry point)
@app.post("/webhook")
@limiter.limit("5/minute")
async def webhook(request: Request, payload: Dict, background_tasks: BackgroundTasks):
    try:
        mapped_data = {
            "reporter_name": payload.get("reporter_name", "Unknown"),
            "reporter_phone": payload.get("reporter_phone", "0000000000"),
            "description": payload.get("description", ""),
            "location": payload.get("location", "Unknown Location"),
            "disaster_type": payload.get("disaster_type", "Not Specified"),
            "help_needed": payload.get("help_needed", "Not Specified"),
        }
        need_input = NeedInput(**mapped_data)
        result = process_and_save_need(need_input, background_tasks)
        return {"message": "SOS Report Saved", "data": result}
    except Exception as e:
        return {"error": str(e)}

# 🔗 ALIAS (Matches your 200 OK log path)
@app.post("/webhook/ngo-register")
@limiter.limit("5/minute")
async def webhook_ngo_register_alias(request: Request, payload: Dict, background_tasks: BackgroundTasks):
    # If a form hits this accidentally, we still process it as an SOS/Need
    try:
        mapped_data = {
            "reporter_name": payload.get("reporter_name", payload.get("name", "Unknown")),
            "reporter_phone": payload.get("reporter_phone", payload.get("phone", "0000000000")),
            "description": payload.get("description", ""),
            "location": payload.get("location", payload.get("address", "Unknown Location")),
            "disaster_type": payload.get("disaster_type", "Not Specified"),
            "help_needed": payload.get("help_needed", "Not Specified"),
        }
        need_input = NeedInput(**mapped_data)
        result = process_and_save_need(need_input, background_tasks)
        return {"message": "Legacy Alias processed", "data": result}
    except Exception as e:
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