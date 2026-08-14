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
- 📥 Captures emergency reports via Google Forms / webhook  
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

### 🔐 OTP Authentication
- Volunteers and NGOs log in via email OTP (no password required for OTP flow)  
- OTPs are stored in Supabase PostgreSQL, expire after **10 minutes**, and are **single-use** (deleted on first successful verification)  

---

## 🛠️ Technology Stack

### 💾 Database
- Supabase PostgreSQL (hosted relational database and connection pooling)

### ☁️ Integration & Geocoding
- Google Maps API (Geocoding)  
- Google Forms (Data Ingestion)  

### ⚙️ Backend
- Python 3.11+  
- FastAPI  
- Uvicorn  

### 🤖 AI & Processing
- Gemini AI (classification + trust scoring)  
- Custom validation logic  

### 🌐 Frontend
- HTML / CSS / JavaScript (served from `new_frontend/`)  

### 🧪 Testing
- Pytest  

---

## 📁 Project Structure

```
Setu/
├── backend/               # FastAPI application
│   ├── main.py            # App entry point, CORS, WebSocket, webhooks
│   ├── auth.py            # Bearer token authentication dependency
│   ├── email_utils.py     # Gmail SMTP OTP sender
│   ├── models.py          # Pydantic request/response models
│   └── routes/            # Feature routers (need, volunteer, match, ngo, …)
├── database/              # PostgreSQL database access layer
│   ├── postgres_client.py # Threaded Connection pool and cursor management
│   ├── schema.sql         # SQL schema definitions for tables
│   ├── init_schema.py     # Database schema deployment script
│   ├── reset_db.py        # Helper to truncate tables during tests
│   ├── otp_db.py          # OTP save / verify (with expiry enforcement)
│   ├── volunteers_db.py
│   ├── needs_db.py
│   └── ngos_db.py
├── ai_processing/         # Gemini-powered need classification
├── notifications/         # Gmail alert dispatcher
├── new_frontend/          # Web UI (HTML/CSS/JS)
├── tests/                 # Pytest test suite
├── config/
│   ├── .env               # Your local secrets (gitignored — never commit)
│   └── .env.example       # Template — copy this to config/.env
├── setu_cli.py            # Command-line management tool
└── requirements.txt
```

---

## ⚙️ Setup & Installation

### Prerequisites

- Python 3.11+
- A Supabase account and project with a PostgreSQL database instance

---

### 1. Clone the Repository

```bash
git clone https://github.com/Hack-Quest/Setu.git
cd Setu
```

---

### 2. Create a Virtual Environment & Install Dependencies

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

---

### 3. Configure Environment Variables

Copy the example file and fill in your credentials:

```bash
# Windows
copy config\.env.example config\.env

# macOS / Linux
cp config/.env.example config/.env
```

Then open `config/.env` and replace every placeholder value. See the comments inside the file for where to obtain each key. The required variables are:

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini API key for AI processing |
| `GROQ_API_KEY` | Groq API key (optional fallback LLM) |
| `GOOGLE_MAPS_KEY` | Google Maps Platform key (Geocoding API) |
| `SUPABASE_DB_URL` | PostgreSQL connection string for Supabase |
| `GMAIL_SENDER` | Gmail address used to send OTP emails |
| `GMAIL_APP_PASSWORD` | Gmail App Password (requires 2FA) |
| `WEATHER_API` | OpenWeatherMap API key (optional) |
| `SECRET_TOKEN` | Shared Bearer token for API auth |
| `SETU_BASE_URL` | Backend base URL (e.g. `http://127.0.0.1:8080/`) |

---

### 4. Deploy Database Schema

Initialize the Supabase database with the required tables by running:

```bash
python database/init_schema.py
```

This connects to your PostgreSQL server and creates all table structures defined in `database/schema.sql`.

---

### 5. Run the Backend

> ⚠️ **Important:** The `uvicorn` command must be run from the **repository root** (`Setu/`), not from inside the `backend/` folder. The code uses package-relative imports (`from backend.routes…`).

```bash
# From the repo root:
uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
```

The API will be available at `http://127.0.0.1:8080`. Visit the interactive docs at:
- **Swagger UI:** http://127.0.0.1:8080/docs  
- **ReDoc:** http://127.0.0.1:8080/redoc  

---

### 6. Serve the Frontend

The frontend is a static HTML/CSS/JS site located in `new_frontend/`. Serve it with any static file server:

```bash
# Using Python's built-in server (from repo root):
python -m http.server 3000 --directory new_frontend

# Or with Node.js npx serve:
npx serve new_frontend -p 3000
```

Then open `http://localhost:3000` in your browser.

> The frontend fetches the Google Maps API key dynamically from the backend endpoint `GET /config/public`. Make sure the backend is running before opening the frontend.

---

### 7. Run the CLI (Optional)

The CLI provides a management interface without needing the web frontend:

```bash
python setu_cli.py
```

From the CLI you can:
- Register NGOs
- Create needs
- Trigger the matching engine
- Simulate disaster scenarios

---

### 8. Run Tests

```bash
# Clear database state first
python database/reset_db.py

# Run unit tests
pytest database/test_database.py backend/test_backend.py -v

# Run integration tests (with live backend running)
python tests/test_ngo.py
python test.py
```

> **Note:** Integration tests require the backend to be running and `SETU_BASE_URL` / `SECRET_TOKEN` to be set in `config/.env`.

---

## 🔐 OTP Authentication — Behavior Notes

The OTP flow works as follows:

1. **`POST /auth/send-otp`** — generates a 6-digit OTP, saves it to database (`otps` table), and emails it via Gmail SMTP.
2. **`POST /auth/verify-otp`** — checks the OTP against the stored record:
   - Returns `401` if the OTP does not match.
   - Returns `401` if the OTP has **expired** (default TTL: **10 minutes**).
   - Deletes the OTP from database on success (**single-use enforcement**).
3. On success, the endpoint returns the user's role (`ngo` or `volunteer`) and the `SECRET_TOKEN` for subsequent API calls.

---

## 🏗️ Production Hardening Suggestions

- **JWT Authentication:** Replace the shared `SECRET_TOKEN` with individual user JWT tokens.
- **Role-Based Access Control:** Distinguish permission actions dynamically based on JWT claims.
- **CORS Hardening:** Restrict `allow_origins` to explicit staging/production origins.
- **OTP Rate Limiting:** Enforce a limit of OTP requests per recipient email to prevent email flooding.
