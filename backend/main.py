from fastapi import FastAPI
from pydantic import BaseModel

# Create FastAPI app
app = FastAPI()


# 📦 Request Schema
class RequestData(BaseModel):
    description: str
    address: str


# 🧠 Mock AI Processing Function
def process_with_ai(description):
    description = description.lower()

    if "food" in description:
        return {"category": "food", "severity": "high"}
    elif "medical" in description:
        return {"category": "medical", "severity": "high"}
    elif "water" in description:
        return {"category": "water", "severity": "medium"}
    else:
        return {"category": "general", "severity": "medium"}


# 🏠 Test Route
@app.get("/")
def home():
    return {"message": "Server is running"}


# 🔥 Webhook (MAIN API)
@app.post("/webhook")
async def webhook(data: RequestData):
    
    # ✅ Step 1: Extract data
    description = data.description
    address = data.address

    # ✅ Step 2: Process using AI logic
    ai_result = process_with_ai(description)

    # Debug prints
    print("Description:", description)
    print("Address:", address)
    print("AI Result:", ai_result)

    # ✅ Step 3: Return processed response
    return {
        "description": description,
        "address": address,
        "category": ai_result["category"],
        "severity": ai_result["severity"]
    }
