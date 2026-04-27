# 🚨 SETU — Smart Emergency Response System

> Smarter Decisions. Stronger Response.

SETU is an AI-powered emergency response platform that connects distress signals to verified responders in seconds. It transforms scattered disaster data into real-time, actionable coordination—ensuring the right help reaches the right place at the right time.

---

## 🌍 Problem

In disaster scenarios, response delays are often caused by:
- ❌ Fake or duplicate distress reports  
- ❌ Unverified volunteers  
- ❌ Manual coordination and communication gaps  

These inefficiencies waste critical time—time that can cost lives.

---

## 💡 Solution

SETU automates the entire disaster response pipeline:
- 📥 Captures emergency reports via Google Forms  
- 🧠 Processes them using AI (severity + trust scoring)  
- 📍 Matches them with the nearest, most suitable volunteers  
- ⚡ Dispatches responders automatically in seconds  

---


## ⚙️ How It Works

1. User submits a distress report via Google Forms  
2. AI processes the request (severity classification + trust scoring)  
3. Matching engine finds the best-fit volunteer  
4. Assignment is created instantly  
5. Dashboard updates in real-time  

---

## 🚀 Key Features

### 🔍 AI-Powered Validation
- Classifies emergencies  
- Assigns severity levels  
- Generates Trust Score to filter unreliable reports  

### 🧑‍🚒 Tiered Volunteer System
- **Tier 1** → NGO-verified responders  
- **Tier 2** → Community volunteers  
- Priority-based dispatch for critical cases  

### 📍 Smart Matching Engine
- Uses geospatial proximity (Haversine distance)  
- Considers skills, availability, and trust score  
- Assigns best-fit volunteer instantly  

### 📊 Real-Time Dashboard
- Live updates of needs and responders  
- Assignment tracking  
- NGO-specific views  

### 📦 Bulk Volunteer Onboarding
- Upload Excel files to onboard multiple volunteers instantly  

---

## 🛠️ Technology Stack

### ☁️ Google Cloud
- Cloud Run (Backend Deployment)  
- Firestore (Database)  
- Google Maps API (Geocoding)  
- Google Forms (Data Ingestion)  

### ⚙️ Backend
- Python 3  
- FastAPI  
- Uvicorn  

### 🤖 AI & Processing
- Gemini AI (classification + trust scoring)  
- Custom validation logic  

### 🌐 Frontend
- HTML  
- CSS  
- JavaScript  

### 🧪 Testing
- Pytest  

---

## 📁 Project Structure

The repository is modularized into distinct backend, frontend, and database components:

*   **`new_frontend/`**: The complete web user interface (HTML/CSS/JS).
*   **`backend/`**: The FastAPI server (`main.py`, routes, models).
*   **`database/`**: Firebase integration and database access layer.
*   **`ai_processing/`**: Logic for extracting structured data using Google GenAI.
*   **`tests/`**: Comprehensive test suite using Pytest.
*   **`setu_cli.py`**: Command-line interface for managing the backend directly.
*   **`config/`**: Configuration and environment variables.

---

## 🌐 Live Demo

- 🌍 **Main App:** [https://setu-api-949977701091.asia-south1.run.app/](https://setu-api-949977701091.asia-south1.run.app/)  
- 📊 **Dashboard:** `/dashboard`  
- 🗺️ **Map View:** `/map`  

---


## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/Hack-Quest/Setu.git
cd Setu
```

### 2. Environment Variables
Create a `config/.env` file:
```ini
SETU_API_BASE_URL=http://localhost:8000
SECRET_TOKEN=your_secure_token
```
> **Note:** Ensure Google Cloud Application Default Credentials (ADC) are configured for Firebase access.

### 3. Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

### 4. Run CLI (Optional)
```bash
python setu_cli.py
```

From the CLI you can:
- Register NGOs
- Create needs
- Trigger matching engine
- Simulate disaster scenarios

---

## 🔮 Future Scope
- 📱 Mobile application
- 🔔 SMS / WhatsApp alerts
- 🤖 Advanced AI validation (LLMs + anomaly detection)
- 🌍 Multi-region disaster integration
- 🛰️ Satellite & weather data fusion
