from fastapi import FastAPI, Request

# Routers
from backend.routes.need import router as need_router, create_need
from backend.routes.volunteer import router as volunteer_router
from backend.routes.match import router as match_router
from backend.routes.dashboard import router as dashboard_router

# Models
from backend.models import NeedInput

app = FastAPI()


# 🏠 Home Route
@app.get("/")
def home():
    return {"message": "Backend is running"}


# 💚 Health Check
@app.get("/health")
def health():
    return {"status": "ok"}


# 🔗 WEBHOOK (Google Form → Backend)
@app.post("/webhook")
async def webhook(request: Request):
    try:
        data = await request.json()

        # 🧩 Map incoming form data → NeedInput
        mapped_data = NeedInput(
            reporter_name=data.get("name", "Unknown Form User"),
            reporter_phone=data.get("phone", "0000000000"),
            description=data.get("description", ""),
            location=data.get("address", "Unknown Location"),
            disaster_type=data.get("disaster_type", "Not Specified"),
            help_needed=data.get("help_needed", "Not Specified")
        )

        # 🚀 Call main pipeline (/need logic)
        response = create_need(mapped_data, token=None)

        return {
            "message": "Webhook processed successfully",
            "data": response
        }

    except Exception as e:
        return {"error": str(e)}


# 📦 Include All Routes
app.include_router(need_router)
app.include_router(volunteer_router)
app.include_router(match_router)
app.include_router(dashboard_router)