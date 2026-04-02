from fastapi import FastAPI

from backend.routes.need import router as need_router
from backend.routes.volunteer import router as volunteer_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router

app = FastAPI()

@app.get("/")
def home():
    return {"message": "Backend is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(match_router)
app.include_router(dashboard_router)